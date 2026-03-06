import os
import sys
import asyncio
import re
import time
import json
from typing import Any, Optional
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from aiogram import Bot, Dispatcher, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ForceReply,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.exceptions import TelegramBadRequest

import html
from datetime import timedelta

from src.backend_posts import (
    extract_image_url,
    extract_post_id,
    extract_signal_fields,
    fetch_unpublished_posts,
    format_channel_post_text,
)
from src.config import Settings, load_settings
from src.follow_orders_api import fetch_follow_order_view
from src.db_handler_aio import (
    add_balance,
    create_copy_order,
    delete_expired_announced_posts,
    get_announced_post,
    get_balance,
    get_user_binding,
    init_db,
    init_storage,
    is_post_announced,
    save_announced_post,
    set_balance,
    upsert_user_binding,
    update_copy_order_status,
)
from src.loguru_logger import logger
from src.order_integration import place_order_async
from src.i18n import all_button_texts, t
from src.db_handler_aio import ensure_user_language, get_user_language, set_user_language
from src.binding_api import fetch_binding_status
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP
from src.platform_errors import platform_error_text

from src.platform_api import (
    fetch_account_balance,
    pick_available_balance_usdt,
    fetch_exchange_info,
    set_trade_leverage,
    fetch_open_orders,
    cancel_order,
    batch_cancel_orders,
    fetch_positions,
    fetch_plan_orders,
    fetch_trade_leverage,
    place_trade_order,
)
from src.db_handler_aio import upsert_contract_infos, get_contract_info


class CopyFlow(StatesGroup):
    waiting_entry = State()
    waiting_amount = State()
    waiting_leverage = State()
    waiting_leverage_custom = State()
    waiting_submit = State()


router = Router()

APP_SETTINGS: Optional[Settings] = None
MAX_LEVERAGE = 200
OPEN_ORDERS_SOFT_TTL_SECONDS = 60

SUPPORTED_LANGS: list[tuple[str, str]] = [
    ("zh-TW", "繁體中文"),
    ("zh-CN", "简体中文"),
    ("en", "English"),
]

def _ilog(event: str, **fields: Any) -> None:
    """
    用戶交互日誌：統一輸出到 logs/main.log
    """
    safe = " ".join([f"{k}={fields[k]!r}" for k in sorted(fields.keys())])
    logger.info(f"[interaction] {event} {safe}".strip())


def _mk_kb(*rows: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[list(r) for r in rows])

_B36_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


def _b36(n: int) -> str:
    n = int(n)
    if n <= 0:
        return "0"
    out: list[str] = []
    while n:
        n, r = divmod(n, 36)
        out.append(_B36_ALPHABET[r])
    return "".join(reversed(out))


def _b36_decode(s: str) -> Optional[int]:
    try:
        return int(str(s).strip().lower(), 36)
    except Exception:
        return None


def _b36_ts() -> str:
    return _b36(int(time.time()))

def _home_reply_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t(lang, "btn_orders")),
                KeyboardButton(text=t(lang, "btn_positions")),
                KeyboardButton(text=t(lang, "btn_balance")),
            ],
            [KeyboardButton(text=t(lang, "btn_language"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder=t(lang, "menu_prompt"),
    )


def _infer_lang_from_tg(language_code: Optional[str]) -> str:
    """
    將 Telegram language_code 映射到本專案語言代碼。
    只在「第一次互動初始化」時使用，不會覆蓋使用者已手動選擇的語言。
    """
    if not language_code:
        return "zh-TW"
    code = str(language_code).strip().lower().replace("_", "-")
    if code.startswith("zh"):
        # 常見：zh-hans / zh-cn / zh-sg -> 简体；zh-hant / zh-tw / zh-hk / zh-mo -> 繁體
        if "hant" in code or code.endswith("-tw") or code.endswith("-hk") or code.endswith("-mo"):
            return "zh-TW"
        if "hans" in code or code.endswith("-cn") or code.endswith("-sg"):
            return "zh-CN"
        return "zh-TW"
    if code.startswith("en"):
        return "en"
    # 其他語言暫時回落英文
    return "en"


async def _init_user_lang(user_id: str, tg_language_code: Optional[str]) -> str:
    """
    第一次互動：用 TG language_code 推斷預設語言並寫入 DB（若已存在則不覆蓋）。
    """
    try:
        uid = str(user_id).strip()
        if not uid or uid == "0":
            return "zh-TW"
        preferred = _infer_lang_from_tg(tg_language_code)
        return await ensure_user_language(uid, preferred)
    except Exception:
        return "zh-TW"


async def _get_lang(user_id: str) -> str:
    """
    後續所有文案一律以 DB 內的使用者偏好為準，避免同一畫面混雜多語言。
    """
    try:
        uid = str(user_id).strip()
        if not uid or uid == "0":
            return "zh-TW"
        # 若不存在就建立一筆預設（不再用 TG 語言覆蓋）
        return await ensure_user_language(uid, "zh-TW")
    except Exception:
        return "zh-TW"


async def _ensure_bound_or_prompt(message: types.Message, user_id: str, lang: str, state: Optional[FSMContext] = None) -> bool:
    """
    若設定 REQUIRE_BINDING=1，則檢查使用者是否已綁定平台帳號。
    未綁定則提示「BYDFi 驗證」並中止後續流程。
    """
    if APP_SETTINGS is None:
        return True
    if not APP_SETTINGS.require_binding:
        return True
    if not APP_SETTINGS.bind_status_url:
        # 設定要求綁定但沒配置 API，保守起見：視為未綁定
        await message.answer(t(lang, "bind_required"))
        return False

    # 先讀 DB 快取，避免每一步都打 API
    try:
        row = await get_user_binding(user_id)
        if row and int(getattr(row, "is_bound", 0)) == 1:
            # 快取命中也把 platform_uid 放進 state，避免後續流程拿不到
            if state is not None:
                try:
                    puid = getattr(row, "platform_user_id", None)
                    if puid:
                        await state.update_data(platform_uid=str(puid))
                except Exception:
                    pass
            if APP_SETTINGS.bind_cache_seconds <= 0:
                return True
            age = (datetime.now(timezone.utc) - row.updated_at).total_seconds()
            if age < float(APP_SETTINGS.bind_cache_seconds):
                return True
    except Exception:
        row = None

    is_bound, platform_uid, verify_url = await _get_binding_status(user_id)
    if is_bound:
        if state is not None and platform_uid:
            await state.update_data(platform_uid=str(platform_uid))
        return True

    # 非 callback 場景：用訊息提示並附上兩個按鈕
    await message.answer(t(lang, "bind_required"), reply_markup=_kb_entry(lang, is_bound=False, verify_url=verify_url))
    return False


async def _get_binding_status(user_id: str) -> tuple[bool, Optional[str], Optional[str]]:
    """
    回傳 (is_bound, platform_uid, verify_url)
    """
    if APP_SETTINGS is None or not APP_SETTINGS.require_binding:
        _ilog("binding_disabled", user_id=str(user_id))
        return True, None, None
    if not APP_SETTINGS.bind_status_url:
        _ilog("binding_misconfigured", user_id=str(user_id), reason="missing_bind_status_url")
        return False, None, None

    # DB 快取
    try:
        row = await get_user_binding(user_id)
        if row and int(getattr(row, "is_bound", 0)) == 1:
            if APP_SETTINGS.bind_cache_seconds <= 0:
                _ilog("binding_cache_hit", user_id=str(user_id), is_bound=True, cache_seconds=int(APP_SETTINGS.bind_cache_seconds))
                return True, (str(getattr(row, "platform_user_id", "") or "") or None), None
            age = (datetime.now(timezone.utc) - row.updated_at).total_seconds()
            if age < float(APP_SETTINGS.bind_cache_seconds):
                _ilog("binding_cache_hit", user_id=str(user_id), is_bound=True, age_seconds=age, cache_seconds=int(APP_SETTINGS.bind_cache_seconds))
                return True, (str(getattr(row, "platform_user_id", "") or "") or None), None
    except Exception:
        pass

    _ilog("binding_api_check", user_id=str(user_id))
    is_bound, platform_user_id, verify_url = await fetch_binding_status(
        APP_SETTINGS.bind_status_url,
        APP_SETTINGS.bind_headers,
        user_id,
        APP_SETTINGS.bind_third_type,
        APP_SETTINGS.bind_brand,
    )
    _ilog(
        "binding_api_result",
        user_id=str(user_id),
        is_bound=bool(is_bound),
        platform_user_id=str(platform_user_id) if platform_user_id is not None else None,
        has_verify_url=bool(verify_url),
    )
    try:
        await upsert_user_binding(user_id, is_bound=is_bound, platform_user_id=platform_user_id)
    except Exception as e:  # noqa: BLE001
        logger.error(f"upsert user binding failed: {e}")

    if not verify_url and APP_SETTINGS.bind_verify_url_template:
        try:
            verify_url = APP_SETTINGS.bind_verify_url_template.format(tg_user_id=user_id)
        except Exception:
            verify_url = None

    return bool(is_bound), (str(platform_user_id) if platform_user_id else None), (str(verify_url) if verify_url else None)


async def _get_platform_uid(user_id: str, state: Optional[FSMContext] = None) -> Optional[str]:
    if state is not None:
        data = await state.get_data()
        v = data.get("platform_uid")
        if v:
            return str(v)
    try:
        row = await get_user_binding(user_id)
        if row and int(getattr(row, "is_bound", 0)) == 1:
            uid = getattr(row, "platform_user_id", None)
            return str(uid) if uid else None
    except Exception:
        return None
    return None


async def _get_available_balance_usdt(user_id: str, state: Optional[FSMContext] = None) -> Optional[float]:
    """
    以平台 account/balance 為準（POST + params），回傳 USDT availableBalance。
    若未配置平台 API，回退到本地 DB balance（舊測試邏輯）。
    """
    if APP_SETTINGS is None or not APP_SETTINGS.platform_api_base_url:
        try:
            return float(await get_balance(user_id))
        except Exception:
            return None

    platform_uid = await _get_platform_uid(user_id, state=state)
    if not platform_uid:
        return None

    items = await fetch_account_balance(
        base_url=str(APP_SETTINGS.platform_api_base_url),
        headers=APP_SETTINGS.platform_api_headers,
        uid=str(platform_uid),
        wallet=str(APP_SETTINGS.platform_wallet),
        brand=str(APP_SETTINGS.platform_brand),
    )
    if items is None:
        return None
    return pick_available_balance_usdt(items)


async def _set_symbol_leverage(
    *,
    user_id: str,
    state: FSMContext,
    lang: str,
    symbol: str,
    leverage: int,
) -> tuple[bool, Optional[str]]:
    """
    呼叫 /trade/leverage 設定槓桿。成功會把 maxNotionalValue 存到 state。
    回傳 (ok, error_message)
    """
    if APP_SETTINGS is None or not APP_SETTINGS.platform_api_base_url:
        return False, "missing PLATFORM_API_BASE_URL"
    platform_uid = await _get_platform_uid(user_id, state=state)
    if not platform_uid:
        return False, "missing platform uid"

    _ilog("leverage_set_attempt", user_id=user_id, symbol=symbol, leverage=int(leverage))
    ok, resp_json, err = await set_trade_leverage(
        base_url=str(APP_SETTINGS.platform_api_base_url),
        headers=APP_SETTINGS.platform_api_headers,
        uid=str(platform_uid),
        wallet=str(APP_SETTINGS.platform_wallet),
        symbol=str(symbol),
        leverage=int(leverage),
        brand=str(APP_SETTINGS.platform_brand),
    )
    _ilog("leverage_set_result", user_id=user_id, symbol=symbol, leverage=int(leverage), ok=bool(ok), error=str(err) if err else None)
    if not ok:
        return False, platform_error_text(lang, resp_json, err)

    # 解析 maxNotionalValue
    max_notional = None
    try:
        if isinstance(resp_json, dict):
            data = resp_json.get("data") if isinstance(resp_json.get("data"), dict) else None
            if isinstance(data, dict) and data.get("maxNotionalValue") is not None:
                max_notional = str(data.get("maxNotionalValue"))
    except Exception:
        pass

    await state.update_data(leverage=int(leverage), leverage_set_ok=True, leverage_max_notional=max_notional)
    return True, None

def _kb_entry(lang: str, is_bound: bool, verify_url: Optional[str]) -> InlineKeyboardMarkup:
    if is_bound:
        return _mk_kb([_btn(t(lang, "entry_one_click_btn"), "flow:begin_copy")])
    return _mk_kb(
        [InlineKeyboardButton(text=t(lang, "bind_jump_btn"), url="https://www.bydfi.com")],
        [_btn(t(lang, "bind_refresh_btn"), "bind:refresh")],
    )


def _oo_side_label(lang: str, side: Any) -> str:
    try:
        v = int(side)
    except Exception:
        v = 0
    if lang == "en":
        return "BUY" if v == 1 else ("SELL" if v == 2 else "-")
    return "多" if v == 1 else ("空" if v == 2 else "-")


def _pos_side_label(lang: str, side: Any) -> str:
    s = str(side or "").strip().upper()
    if s in {"BUY", "LONG", "1"}:
        return "BUY" if lang == "en" else "多"
    if s in {"SELL", "SHORT", "2"}:
        return "SELL" if lang == "en" else "空"
    return s or "-"


def _norm_symbol_for_match(s: str) -> str:
    """統一樣式以比對持倉與 planOrder 的 symbol（例：0G-USDT 與 0GUSDT 視為同一）"""
    return str(s or "").strip().upper().replace("-", "")


def _volume_to_contracts(volume: Any, contract_factor: Any) -> int:
    """持倉 volume（面值×張數）換算為張數，向下取整"""
    v = _dec(volume)
    cf = _dec(contract_factor)
    if v is None or v <= 0 or cf is None or cf <= 0:
        return 1
    q = v / cf
    if q <= 0:
        return 1
    return int(q.to_integral_value(rounding=ROUND_DOWN)) or 1


def _build_close_position_body(
    symbol: str, position_side: str, contracts: int
) -> dict[str, Any]:
    """
    組裝平倉單 body：
    - 做多(LONG) → side=SELL；做空(SHORT) → side=BUY
    - quantity=張數（整數），reduceOnly=true, closePosition=true
    - 不附帶 positionSide
    """
    side = "SELL" if position_side == "LONG" else "BUY"
    qty = max(1, int(contracts))
    return {
        "symbol": str(symbol).strip().upper(),
        "side": side,
        "type": "MARKET",
        "quantity": str(qty),
        "reduceOnly": True,
        "closePosition": True,
        "source": "10",
    }


def _position_side_from_api(p: dict[str, Any]) -> str:
    """持倉 API 回傳的 positionSide 或 side 轉為 LONG/SHORT"""
    ps = str(p.get("positionSide") or "").strip().upper()
    if ps in {"LONG", "SHORT"}:
        return ps
    s = str(p.get("side") or "").strip().upper()
    if s in {"BUY", "LONG", "1"}:
        return "LONG"
    if s in {"SELL", "SHORT", "2"}:
        return "SHORT"
    return "LONG"


def _kb_positions(
    lang: str,
    positions: list[dict[str, Any]],
    page: int,
    page_size: int,
    snapshot_token: str = "",
    *,
    confirm_close_all: bool = False,
) -> InlineKeyboardMarkup:
    total = len(positions)
    pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, pages - 1))
    start = page * page_size
    chunk = positions[start : start + page_size]

    rows: list[list[InlineKeyboardButton]] = []
    for p in chunk:
        sym = str(p.get("symbol") or "").strip()
        pos_side = _position_side_from_api(p)
        if sym:
            key = f"{sym}:{pos_side}:{page}:{snapshot_token}"
            rows.append([_btn(t(lang, "positions_close_btn", symbol=sym), f"pos:close:{key}")])

    if total > 0:
        if confirm_close_all:
            rows.append(
                [
                    _btn(t(lang, "positions_close_all_confirm_btn"), f"pos:close_all_confirm:{page}:{snapshot_token}"),
                    _btn(t(lang, "positions_close_all_back_btn"), f"pos:close_all_back:{page}:{snapshot_token}"),
                ]
            )
        else:
            rows.append([_btn(t(lang, "positions_close_all_btn"), f"pos:close_all:{page}:{snapshot_token}")])

    rows.append([_btn(t(lang, "positions_refresh"), f"pos:page:{page}")])
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(_btn(t(lang, "positions_prev"), f"pos:page:{page-1}"))
    if page < pages - 1:
        nav.append(_btn(t(lang, "positions_next"), f"pos:page:{page+1}"))
    if nav:
        rows.append(nav)
    return _mk_kb(*rows)


def _build_tp_sl_for_position(
    lang: str,
    position: dict[str, Any],
    plan_orders: list[dict[str, Any]],
) -> str:
    """依持倉 symbol 比對 planOrder，組止盈止損字串（含比例）"""
    sn = _norm_symbol_for_match(str(position.get("symbol") or ""))
    if not sn:
        return ""
    try:
        pos_vol = float(position.get("volume") or 0)
    except Exception:
        pos_vol = 0
    tp_parts: list[str] = []
    sl_parts: list[str] = []
    for po in plan_orders:
        if not isinstance(po, dict):
            continue
        ps = _norm_symbol_for_match(str(po.get("symbol") or ""))
        if ps != sn:
            continue
        st = str(po.get("strategyType") or "").upper()
        px = po.get("stopPrice")
        if px is None or px == "":
            px = po.get("price")
        if px is None or px == "":
            continue
        vol = po.get("volume")
        close_pos = po.get("closePosition") is True
        if vol is None or close_pos:
            suffix = t(lang, "tp_sl_ratio_full")
        else:
            try:
                if pos_vol and pos_vol > 0:
                    pct = (float(vol) / pos_vol) * 100
                    suffix = t(lang, "tp_sl_ratio_partial", pct=f"{pct:.1f}")
                else:
                    suffix = t(lang, "tp_sl_ratio_partial", pct="?")
            except Exception:
                suffix = ""
        s = f"{px} ({suffix})" if suffix else str(px)
        if st == "TP":
            tp_parts.append(s)
        elif st == "SL":
            sl_parts.append(s)
    tp_str = ", ".join(tp_parts) if tp_parts else "-"
    sl_str = ", ".join(sl_parts) if sl_parts else "-"
    if tp_str == "-" and sl_str == "-":
        return ""
    return t(lang, "positions_tp_sl_line", tp=html.escape(tp_str), sl=html.escape(sl_str))


async def _render_positions_text(
    lang: str,
    positions: list[dict[str, Any]],
    page: int,
    page_size: int,
    *,
    plan_orders: Optional[list[dict[str, Any]]] = None,
    leverage_by_symbol: Optional[dict[str, Optional[int]]] = None,
) -> str:
    total = len(positions)
    pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, pages - 1))
    start = page * page_size
    chunk = positions[start : start + page_size]
    lev_map = leverage_by_symbol or {}

    lines: list[str] = []
    lines.append(t(lang, "positions_title"))
    lines.append(t(lang, "positions_page", page=page + 1, pages=pages, total=total))
    lines.append("")
    if not chunk:
        lines.append(t(lang, "positions_empty"))
        return "\n".join(lines)

    plan_list = plan_orders if isinstance(plan_orders, list) else []
    for p in chunk:
        sym = html.escape(str(p.get("symbol") or ""))
        side = html.escape(_pos_side_label(lang, p.get("side")))
        avg_price = html.escape(_fmt_price_2dp(p.get("avgPrice")))
        liq_price = html.escape(_fmt_price_2dp(p.get("liqPrice")))
        mark_price_raw = p.get("markPrice")
        mark_price = html.escape(_fmt_price_2dp(mark_price_raw))
        pnl = html.escape(_fmt_price_2dp(p.get("unPnl")))
        settle = html.escape(str(p.get("settleCoin") or "").strip() or "USDT")

        vol_raw = p.get("volume")
        holding_value = "-"
        try:
            v = float(vol_raw) if vol_raw is not None else None
            mp = float(mark_price_raw) if mark_price_raw is not None else None
            if v is not None and mp is not None and v > 0 and mp > 0:
                hv = Decimal(str(v)) * Decimal(str(mp))
                holding_value = f"{hv.quantize(Decimal('0.01')):f}"
        except Exception:
            pass

        sn = _norm_symbol_for_match(str(p.get("symbol") or ""))
        lev_val = lev_map.get(sn)
        lev = int(lev_val) if isinstance(lev_val, int) and lev_val > 0 else None
        margin_s = _position_margin_from_formula(vol_raw, mark_price_raw, int(lev) if lev else 0)
        margin = html.escape(margin_s) if margin_s else html.escape(str(p.get("positionMargin") or "-"))

        pnl_pct = "-"
        un_pnl_ratio_raw = p.get("unPnlRatio")
        if un_pnl_ratio_raw is not None and str(un_pnl_ratio_raw).strip():
            pnl_pct = str(un_pnl_ratio_raw).strip().rstrip("%").strip() or "-"
        if pnl_pct == "-":
            try:
                m = Decimal(str(p.get("positionMargin") or "0"))
                u = Decimal(str(p.get("unPnl") or "0"))
                if m and m != 0:
                    pct = (u / m) * Decimal(100)
                    pnl_pct = f"{pct.quantize(Decimal('0.01')):f}"
            except Exception:
                pass

        tp_sl_line = _build_tp_sl_for_position(lang, p, plan_list)

        lines.append(
            t(
                lang,
                "positions_item",
                symbol=sym,
                side=side,
                holding_value=holding_value,
                avg_price=avg_price,
                mark_price=mark_price,
                liq_price=liq_price,
                margin=margin,
                settle=settle,
                pnl=pnl,
                pnl_pct=pnl_pct,
                tp_sl_line=tp_sl_line,
            )
        )
        lines.append("")
    if positions:
        lines.append(t(lang, "positions_close_hint"))
    return "\n".join(lines).strip()


async def _edit_positions_message(
    msg: types.Message,
    state: FSMContext,
    user_id: str,
    lang: str,
    page: int,
    *,
    confirm_close_all: bool = False,
) -> bool:
    if APP_SETTINGS is None or not APP_SETTINGS.platform_api_base_url:
        await msg.answer(t(lang, "exinfo_unavailable"))
        return False
    platform_uid = await _get_platform_uid(user_id, state=state)
    if not platform_uid:
        await msg.answer(t(lang, "bind_alert"), reply_markup=_kb_entry(lang, is_bound=False, verify_url=None))
        return False
    items = await fetch_positions(
        base_url=str(APP_SETTINGS.platform_api_base_url),
        headers=APP_SETTINGS.platform_api_headers,
        contract_type=2,
        uid=str(platform_uid),
        brand=str(APP_SETTINGS.platform_brand),
        symbol=None,
    )
    if items is None:
        await msg.answer(t(lang, "exinfo_unavailable"))
        return False

    def _positions_sort_key(x: dict[str, Any]) -> Decimal:
        try:
            return Decimal(str(x.get("unPnl") or "0"))
        except Exception:
            return Decimal(0)

    items.sort(key=_positions_sort_key, reverse=True)
    page_size = 5
    start = page * page_size
    chunk = items[start : start + page_size]
    symbols: list[str] = []
    for p in chunk:
        s = str(p.get("symbol") or "").strip().upper()
        if s and s not in symbols:
            symbols.append(s)
    leverage_by_symbol: dict[str, Optional[int]] = {}
    for s in symbols:
        sn = _norm_symbol_for_match(s)
        ok_lev, lev_json, _ = await fetch_trade_leverage(
            base_url=str(APP_SETTINGS.platform_api_base_url),
            headers=APP_SETTINGS.platform_api_headers,
            uid=str(platform_uid),
            wallet=str(APP_SETTINGS.platform_wallet),
            symbol=s,
            brand=str(APP_SETTINGS.platform_brand),
        )
        lev_val: Optional[int] = None
        if ok_lev and isinstance(lev_json, dict):
            data = lev_json.get("data")
            if isinstance(data, dict) and data.get("leverage") is not None:
                try:
                    lev_val = int(data.get("leverage"))
                except Exception:
                    lev_val = None
        leverage_by_symbol[sn] = lev_val
    plans = await fetch_plan_orders(
        base_url=str(APP_SETTINGS.platform_api_base_url),
        headers=APP_SETTINGS.platform_api_headers,
        uid=str(platform_uid),
        wallet=str(APP_SETTINGS.platform_wallet),
        brand=str(APP_SETTINGS.platform_brand),
        body={},
    )
    text = await _render_positions_text(
        lang, items, page, page_size,
        plan_orders=plans,
        leverage_by_symbol=leverage_by_symbol,
    )
    token = _b36_ts()
    await state.update_data(positions_snapshot_ts=int(time.time()), positions_snapshot_token=str(token))
    kb = _kb_positions(lang, items, page, page_size, snapshot_token=token, confirm_close_all=confirm_close_all)
    try:
        await msg.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    return True


async def _show_positions(message: types.Message, state: FSMContext, user_id: str, lang: str, page: int) -> None:
    if APP_SETTINGS is None or not APP_SETTINGS.platform_api_base_url:
        await message.answer(t(lang, "exinfo_unavailable"))
        return
    platform_uid = await _get_platform_uid(user_id, state=state)
    if not platform_uid:
        await message.answer(t(lang, "bind_alert"), reply_markup=_kb_entry(lang, is_bound=False, verify_url=None))
        return
    items = await fetch_positions(
        base_url=str(APP_SETTINGS.platform_api_base_url),
        headers=APP_SETTINGS.platform_api_headers,
        contract_type=2,
        uid=str(platform_uid),
        brand=str(APP_SETTINGS.platform_brand),
        symbol=None,
    )
    if items is None:
        await message.answer(t(lang, "exinfo_unavailable"))
        return

    def _positions_sort_key(x: dict[str, Any]) -> Decimal:
        try:
            return Decimal(str(x.get("unPnl") or "0"))
        except Exception:
            return Decimal(0)

    items.sort(key=_positions_sort_key, reverse=True)
    page_size = 5
    start = page * page_size
    chunk = items[start : start + page_size]
    symbols = []
    for p in chunk:
        s = str(p.get("symbol") or "").strip().upper()
        if s and s not in symbols:
            symbols.append(s)
    leverage_by_symbol = {}
    for s in symbols:
        sn = _norm_symbol_for_match(s)
        ok_lev, lev_json, _ = await fetch_trade_leverage(
            base_url=str(APP_SETTINGS.platform_api_base_url),
            headers=APP_SETTINGS.platform_api_headers,
            uid=str(platform_uid),
            wallet=str(APP_SETTINGS.platform_wallet),
            symbol=s,
            brand=str(APP_SETTINGS.platform_brand),
        )
        lev_val = None
        if ok_lev and isinstance(lev_json, dict):
            data = lev_json.get("data")
            if isinstance(data, dict) and data.get("leverage") is not None:
                try:
                    lev_val = int(data.get("leverage"))
                except Exception:
                    lev_val = None
        leverage_by_symbol[sn] = lev_val
    plans = await fetch_plan_orders(
        base_url=str(APP_SETTINGS.platform_api_base_url),
        headers=APP_SETTINGS.platform_api_headers,
        uid=str(platform_uid),
        wallet=str(APP_SETTINGS.platform_wallet),
        brand=str(APP_SETTINGS.platform_brand),
        body={},
    )
    text = await _render_positions_text(
        lang, items, page, page_size,
        plan_orders=plans,
        leverage_by_symbol=leverage_by_symbol,
    )
    token = _b36_ts()
    await state.update_data(positions_snapshot_ts=int(time.time()), positions_snapshot_token=str(token))
    kb = _kb_positions(lang, items, page, page_size, snapshot_token=token, confirm_close_all=False)
    await message.answer(text, reply_markup=kb, disable_web_page_preview=True)

def _kb_open_orders(
    lang: str,
    orders: list[dict[str, Any]],
    page: int,
    page_size: int,
    snapshot_token: str,
    *,
    confirm_cancel_all: bool = False,
) -> InlineKeyboardMarkup:
    total = len(orders)
    pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, pages - 1))
    start = page * page_size
    chunk = orders[start : start + page_size]

    rows: list[list[InlineKeyboardButton]] = []
    for o in chunk:
        oid = str(o.get("orderId") or "").strip()
        sym = str(o.get("symbol") or "").strip().upper()
        if oid:
            rows.append([_btn(f"ID:{oid}", f"oo:cancel:{oid}:{page}:{snapshot_token}")])

    if total > 0:
        if confirm_cancel_all:
            rows.append(
                [
                    _btn(t(lang, "orders_cancel_all_confirm_btn"), f"oo:cancel_all_confirm:{page}:{snapshot_token}"),
                    _btn(t(lang, "orders_cancel_all_back_btn"), f"oo:cancel_all_back:{page}:{snapshot_token}"),
                ]
            )
        else:
            rows.append([_btn(t(lang, "orders_cancel_all_btn"), f"oo:cancel_all:{page}:{snapshot_token}")])

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(_btn(t(lang, "orders_prev"), f"oo:page:{page-1}"))
    nav.append(_btn(t(lang, "orders_refresh"), f"oo:page:{page}"))
    if page < pages - 1:
        nav.append(_btn(t(lang, "orders_next"), f"oo:page:{page+1}"))
    rows.append(nav)
    return _mk_kb(*rows)


async def _render_open_orders_text(
    lang: str,
    orders: list[dict[str, Any]],
    page: int,
    page_size: int,
    *,
    leverage_by_symbol: dict[str, Optional[int]],
    market_info_by_symbol: Optional[dict[str, tuple[Any, Any]]] = None,
) -> str:
    total = len(orders)
    pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, pages - 1))
    start = page * page_size
    chunk = orders[start : start + page_size]
    market_info = market_info_by_symbol or {}

    lines: list[str] = []
    lines.append(t(lang, "orders_title"))
    lines.append(t(lang, "orders_page", page=page + 1, pages=pages, total=total))
    lines.append("")
    if not chunk:
        lines.append(t(lang, "orders_empty"))
        return "\n".join(lines)

    for o in chunk:
        oid = html.escape(str(o.get("orderId") or ""))
        sym_raw = str(o.get("symbol") or "")
        sym_key = _norm_symbol_for_match(sym_raw)
        sym = html.escape(sym_raw)
        price_val = o.get("price")
        price = html.escape(str(price_val or "-"))
        ct = html.escape(_fmt_order_time(o.get("createTime") or o.get("updateTime")))
        side_label = html.escape(_oo_side_label(lang, o.get("side")))
        lev = leverage_by_symbol.get(sym_key)
        lev_s = str(int(lev)) if isinstance(lev, int) and lev > 0 else "-"
        cf, fee = market_info.get(sym_key, (None, None))
        margin_s = _volume_to_margin(
            o.get("volume"),
            int(lev) if isinstance(lev, int) and lev > 0 else 0,
            price_val,
            fee_rate_taker=fee,
            contract_factor=cf,
        )
        margin = html.escape(margin_s) if margin_s else "-"
        lines.append(
            t(
                lang,
                "orders_item",
                order_id=oid,
                symbol=sym,
                side=side_label,
                leverage=lev_s,
                price=price,
                margin=margin,
                create_time=ct,
            )
        )
        lines.append("")
    lines.append(t(lang, "orders_cancel_hint"))
    return "\n".join(lines).strip()


async def _edit_open_orders_message(
    msg: types.Message,
    state: FSMContext,
    user_id: str,
    lang: str,
    page: int,
    *,
    confirm_cancel_all: bool = False,
) -> bool:
    """
    重新拉 openOrder 並更新同一則訊息。成功回傳 True。
    """
    if APP_SETTINGS is None or not APP_SETTINGS.platform_api_base_url:
        await msg.answer(t(lang, "exinfo_unavailable"))
        return False
    platform_uid = await _get_platform_uid(user_id, state=state)
    if not platform_uid:
        await msg.answer(t(lang, "bind_alert"), reply_markup=_kb_entry(lang, is_bound=False, verify_url=None))
        return False
    items = await fetch_open_orders(
        base_url=str(APP_SETTINGS.platform_api_base_url),
        headers=APP_SETTINGS.platform_api_headers,
        uid=str(platform_uid),
        wallet=str(APP_SETTINGS.platform_wallet),
        brand=str(APP_SETTINGS.platform_brand),
        body={},
    )
    if items is None:
        await msg.answer(t(lang, "exinfo_unavailable"))
        return False

    def _orders_sort_key(x: dict[str, Any]) -> str:
        return str(x.get("updateTime") or x.get("createTime") or "")

    items.sort(key=_orders_sort_key, reverse=True)
    page_size = 5
    start = max(0, int(page)) * page_size
    chunk = items[start : start + page_size]
    symbols: list[str] = []
    for o in chunk:
        s = str(o.get("symbol") or "").strip().upper()
        if s and s not in symbols:
            symbols.append(s)
    leverage_by_symbol: dict[str, Optional[int]] = {}
    market_info_by_symbol: dict[str, tuple[Any, Any]] = {}

    for s in symbols:
        sn = _norm_symbol_for_match(s)
        ci = await get_contract_info(s) if s else None
        if ci:
            market_info_by_symbol[sn] = (
                getattr(ci, "contract_factor", None),
                getattr(ci, "fee_rate_taker", None),
            )
        ok_lev, lev_json, lev_err = await fetch_trade_leverage(
            base_url=str(APP_SETTINGS.platform_api_base_url),
            headers=APP_SETTINGS.platform_api_headers,
            uid=str(platform_uid),
            wallet=str(APP_SETTINGS.platform_wallet),
            symbol=s,
            brand=str(APP_SETTINGS.platform_brand),
        )
        lev_val: Optional[int] = None
        if ok_lev and isinstance(lev_json, dict):
            data = lev_json.get("data") if isinstance(lev_json.get("data"), dict) else None
            if isinstance(data, dict) and data.get("leverage") is not None:
                try:
                    lev_val = int(data.get("leverage"))
                except Exception:
                    lev_val = None
        leverage_by_symbol[sn] = lev_val

    text = await _render_open_orders_text(
        lang,
        items,
        page,
        page_size,
        leverage_by_symbol=leverage_by_symbol,
        market_info_by_symbol=market_info_by_symbol,
    )
    token = _b36_ts()
    await state.update_data(open_orders_snapshot_ts=int(time.time()), open_orders_snapshot_token=str(token))
    kb = _kb_open_orders(lang, items, page, page_size, snapshot_token=token, confirm_cancel_all=confirm_cancel_all)
    try:
        await msg.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    return True

async def _show_open_orders(message: types.Message, state: FSMContext, user_id: str, lang: str, page: int) -> None:
    if APP_SETTINGS is None or not APP_SETTINGS.platform_api_base_url:
        await message.answer(t(lang, "exinfo_unavailable"))
        return
    platform_uid = await _get_platform_uid(user_id, state=state)
    if not platform_uid:
        await message.answer(t(lang, "bind_alert"), reply_markup=_kb_entry(lang, is_bound=False, verify_url=None))
        return
    items = await fetch_open_orders(
        base_url=str(APP_SETTINGS.platform_api_base_url),
        headers=APP_SETTINGS.platform_api_headers,
        uid=str(platform_uid),
        wallet=str(APP_SETTINGS.platform_wallet),
        brand=str(APP_SETTINGS.platform_brand),
        body={},
    )
    if items is None:
        await message.answer(t(lang, "exinfo_unavailable"))
        return

    def _orders_sort_key(x: dict[str, Any]) -> str:
        return str(x.get("updateTime") or x.get("createTime") or "")

    items.sort(key=_orders_sort_key, reverse=True)
    page_size = 5
    start = max(0, int(page)) * page_size
    chunk = items[start : start + page_size]
    symbols: list[str] = []
    for o in chunk:
        s = str(o.get("symbol") or "").strip().upper()
        if s and s not in symbols:
            symbols.append(s)
    leverage_by_symbol: dict[str, Optional[int]] = {}
    market_info_by_symbol: dict[str, tuple[Any, Any]] = {}

    for s in symbols:
        sn = _norm_symbol_for_match(s)
        ci = await get_contract_info(s) if s else None
        if ci:
            market_info_by_symbol[sn] = (
                getattr(ci, "contract_factor", None),
                getattr(ci, "fee_rate_taker", None),
            )
        ok_lev, lev_json, _ = await fetch_trade_leverage(
            base_url=str(APP_SETTINGS.platform_api_base_url),
            headers=APP_SETTINGS.platform_api_headers,
            uid=str(platform_uid),
            wallet=str(APP_SETTINGS.platform_wallet),
            symbol=s,
            brand=str(APP_SETTINGS.platform_brand),
        )
        lev_val: Optional[int] = None
        if ok_lev and isinstance(lev_json, dict):
            data = lev_json.get("data") if isinstance(lev_json.get("data"), dict) else None
            if isinstance(data, dict) and data.get("leverage") is not None:
                try:
                    lev_val = int(data.get("leverage"))
                except Exception:
                    lev_val = None
        leverage_by_symbol[sn] = lev_val

    text = await _render_open_orders_text(
        lang,
        items,
        page,
        page_size,
        leverage_by_symbol=leverage_by_symbol,
        market_info_by_symbol=market_info_by_symbol,
    )
    token = _b36_ts()
    await state.update_data(open_orders_snapshot_ts=int(time.time()), open_orders_snapshot_token=str(token))
    kb = _kb_open_orders(lang, items, page, page_size, snapshot_token=token, confirm_cancel_all=False)
    await message.answer(text, reply_markup=kb, disable_web_page_preview=True)


async def _show_home_menu(message: types.Message, *, user_id: Optional[str] = None) -> None:
    uid = user_id or (str(message.from_user.id) if message.from_user else "0")
    lang = await _get_lang(uid)
    await message.answer(t(lang, "menu_prompt"), reply_markup=_home_reply_kb(lang))
    _ilog("show_home_menu", user_id=uid, lang=lang)


def _parse_amount(text: str) -> Optional[float]:
    t = text.strip().replace(",", "")
    if not re.fullmatch(r"\d+(\.\d+)?", t):
        return None
    try:
        v = float(t)
    except ValueError:
        return None
    return v if v > 0 else None


def _parse_leverage(text: str) -> Optional[int]:
    t = text.strip()
    if not re.fullmatch(r"\d+", t):
        return None
    try:
        v = int(t)
    except ValueError:
        return None
    if v < 1 or v > MAX_LEVERAGE:
        return None
    return v


async def _get_symbol_max_leverage(payload: dict[str, Any]) -> int:
    """取得交易對允許的最大槓桿，無則回傳 MAX_LEVERAGE。"""
    sym_key = _norm_symbol_for_exinfo(extract_signal_fields(payload).get("symbol"))
    ci = await get_contract_info(sym_key) if sym_key else None
    max_lev = int(getattr(ci, "leverage_level", 0) or 0) if ci else 0
    return max_lev if max_lev > 0 else MAX_LEVERAGE


def _norm_symbol_for_exinfo(symbol: Optional[str]) -> str:
    s = str(symbol or "").strip().upper()
    for ch in ("-", "_", "/", " "):
        s = s.replace(ch, "")
    return s


def _symbol_for_backend(payload_symbol: Optional[str], ci: Any) -> str:
    """
    中心後端交易對格式：BASE-QUOTE，例如 BTC-USDT。
    優先使用 contract_infos 的 base/settle 組合，其次用原始字串推斷。
    """
    base = getattr(ci, "base_symbol", None) if ci else None
    quote = getattr(ci, "settle_coin", None) if ci else None
    if base and quote:
        return f"{str(base).strip().upper()}-{str(quote).strip().upper()}"
    raw = str(payload_symbol or "").strip().upper().replace("_", "-").replace("/", "-")
    raw = re.sub(r"-+", "-", raw)
    if "-" in raw:
        parts = [p for p in raw.split("-") if p]
        if len(parts) >= 2:
            return f"{parts[0]}-{parts[-1]}"
    # fallback: BTCUSDT -> BTC-USDT
    for q in ("USDT", "USDC", "USD"):
        if raw.endswith(q) and len(raw) > len(q):
            return f"{raw[:-len(q)]}-{q}"
    return raw


def _dec(v: Any) -> Optional[Decimal]:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


def _fmt_price_2dp(v: Any) -> str:
    """數值四捨五入到小數第二位；非數值或空回傳 '-'"""
    if v is None or v == "":
        return "-"
    try:
        d = Decimal(str(v))
        return f"{d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):f}"
    except (InvalidOperation, ValueError, TypeError):
        return "-"


def _compute_qty(
    amount: float,
    leverage: int,
    entry_price: Any,
    *,
    fee_rate_taker: Any,
    contract_factor: Any,
    best_bid_price: Any = None,
) -> Optional[Decimal]:
    """
    quantity（張數）計算：

    - 訂單成本 = 保證金（amount）
    - 起始保證金率 = 1 / 槓桿（leverage）
    - taker 費率 = fee_rate_taker（由 exchange_info/market_info 取得）
    - 合約面值 = contract_factor（由 exchange_info/market_info 取得）
    - 委託價格 = entry_price
    - 若提供 best_bid_price（買一價），則使用 max(entry_price, best_bid_price)

    公式（依保證金下單）：
      張數 = 訂單成本 / (起始保證金率 + taker費率) / 合約面值 / 參考價格
    """
    a = _dec(amount)
    l = _dec(leverage)
    p = _dec(entry_price)
    fee = _dec(fee_rate_taker)
    cf = _dec(contract_factor)
    bid1 = _dec(best_bid_price)
    if a is None or l is None or p is None or p <= 0 or cf is None or cf <= 0 or fee is None:
        return None
    if l <= 0:
        return None
    ref_price = p
    if bid1 is not None and bid1 > 0:
        ref_price = max(p, bid1)
    imr = Decimal(1) / l  # 起始保證金率
    denom = imr + fee
    if denom <= 0:
        return None
    q = a / denom / cf / ref_price
    if q <= 0:
        return None
    # 張數：向下取整
    return q.to_integral_value(rounding=ROUND_DOWN)


def _position_margin_from_formula(volume: Any, mark_price: Any, leverage: int) -> Optional[str]:
    """
    持倉保證金：volume（已為面值×張數）× 標記價格 / 槓桿倍數
    """
    v = _dec(volume)
    mp = _dec(mark_price)
    l = _dec(leverage) if leverage else None
    if v is None or v <= 0 or mp is None or mp <= 0 or l is None or l <= 0:
        return None
    m = v * mp / l
    if m <= 0:
        return None
    return f"{m.quantize(Decimal('0.01')):f}"


def _volume_to_margin(
    volume: Any,
    leverage: int,
    price: Any,
    *,
    fee_rate_taker: Any,
    contract_factor: Any,
) -> Optional[str]:
    """
    由張數（volume）反推保證金：margin = volume * (1/leverage + fee) * contract_factor * price
    """
    q = _dec(volume)
    l = _dec(leverage) if leverage else None
    p = _dec(price)
    fee = _dec(fee_rate_taker)
    cf = _dec(contract_factor)
    if q is None or q <= 0 or l is None or l <= 0 or p is None or p <= 0 or cf is None or cf <= 0 or fee is None:
        return None
    imr = Decimal(1) / l
    m = q * (imr + fee) * cf * p
    if m <= 0:
        return None
    return f"{m.quantize(Decimal('0.01')):f}"


async def _refresh_exchange_info_once(settings: Settings) -> None:
    if not settings.platform_api_base_url:
        return
    items = await fetch_exchange_info(
        base_url=str(settings.platform_api_base_url),
        headers=settings.platform_api_headers,
        brand=str(settings.platform_brand),
    )
    if items is None:
        logger.error("exchange_info refresh failed")
        return
    n = await upsert_contract_infos(items)
    logger.info(f"exchange_info refreshed count={n}")


async def periodic_refresh_exchange_info(settings: Settings) -> None:
    # 啟動先拉一次
    try:
        await _refresh_exchange_info_once(settings)
    except Exception as e:  # noqa: BLE001
        logger.error(f"exchange_info initial refresh error: {e}")
    while True:
        await asyncio.sleep(int(settings.exchange_info_refresh_seconds))
        try:
            await _refresh_exchange_info_once(settings)
        except Exception as e:  # noqa: BLE001
            logger.error(f"exchange_info refresh error: {e}")


def _copy_start_param(post_id: str) -> str:
    # start 參數建議保持短且安全
    return f"copy_{post_id}"

def _extract_follow_order_id_from_start_args(args: str) -> Optional[int]:
    """
    Telegram deep-link /start payload 解析。

    支援格式：
    - copy_<id>（既有格式）
    - id_<id> / id-<id> / id:<id> / id=<id>（兼容新格式）
    - <id>（純數字）
    """
    raw = (args or "").strip()
    if not raw:
        return None

    if raw.startswith("copy_"):
        raw = raw.removeprefix("copy_").strip()

    m = re.fullmatch(r"(?:id[_:=\-])?(\d+)", raw)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _btn_to_private(bot_username: str, post_id: str) -> InlineKeyboardButton:
    url = f"https://t.me/{bot_username}?start={_copy_start_param(post_id)}"
    return InlineKeyboardButton(text="一鍵跟單", url=url)


def _btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


async def poll_unpublished_posts(bot: Bot, settings: Settings, bot_username: str) -> None:
    """
    輪巡後端 posts_url，將未公告文章發佈到公開頻道。
    """
    logger.info("Poller started")
    while True:
        try:
            if not settings.posts_url:
                await asyncio.sleep(60)
                continue
            items = await fetch_unpublished_posts(settings.posts_url, settings.posts_headers)
            for item in items:
                post_id = extract_post_id(item)
                if not post_id:
                    continue
                if await is_post_announced(post_id):
                    continue

                text = format_channel_post_text(item)
                kb = _mk_kb([_btn_to_private(bot_username, post_id)])
                image_url = extract_image_url(item)
                if image_url:
                    msg = await bot.send_photo(
                        chat_id=settings.public_channel_id,
                        photo=image_url,
                        caption=text,
                        reply_markup=kb,
                    )
                else:
                    msg = await bot.send_message(
                        chat_id=settings.public_channel_id,
                        text=text,
                        reply_markup=kb,
                        disable_web_page_preview=True,
                    )
                await save_announced_post(post_id=post_id, payload=item, channel_message_id=msg.message_id)
                await asyncio.sleep(0)  # 讓出事件迴圈
        except Exception as e:  # noqa: BLE001
            logger.exception(f"Poller error: {e}")

        await asyncio.sleep(settings.poll_interval_seconds)


def _normalize_dt(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _is_expired(announced_at: datetime, ttl_seconds: int) -> bool:
    announced_at = _normalize_dt(announced_at)
    age = (datetime.now(timezone.utc) - announced_at).total_seconds()
    return age > float(ttl_seconds)


async def _ensure_signal_alive(state: FSMContext) -> tuple[bool, Optional[str]]:
    """
    檢查 state 中的信號是否仍在有效期內。
    回傳 (ok, reason_message)。
    """
    if APP_SETTINGS is None:
        return False, "系統尚未完成初始化，請稍後再試。"
    data = await state.get_data()
    post_id = data.get("post_id")
    announced_at = data.get("announced_at")
    if not post_id or not announced_at:
        return False, "狀態已失效，請回到頻道重新點擊『一鍵跟單』。"
    try:
        announced_dt = datetime.fromisoformat(str(announced_at))
    except Exception:
        return False, "狀態已失效，請回到頻道重新點擊『一鍵跟單』。"
    if _is_expired(announced_dt, APP_SETTINGS.signal_ttl_seconds):
        return False, "当前信号已失效（超过有效期），无法继续操作。请回到频道查看最新信号。"
    return True, None


async def periodic_cleanup(ttl_seconds: int) -> None:
    """
    定期清除超過有效期的信號資料，確保最多只保留一天。
    """
    while True:
        try:
            deleted = await delete_expired_announced_posts(ttl_seconds)
            if deleted:
                logger.info(f"cleanup: deleted announced_posts={deleted}")
        except Exception as e:  # noqa: BLE001
            logger.exception(f"cleanup error: {e}")
        await asyncio.sleep(3600)  # 每小時清理一次


def _tz8() -> timezone:
    return timezone(timedelta(hours=8))


def _fmt_order_time(raw: Any) -> str:
    """將 createTime/updateTime 轉為 UTC+8 可讀格式（支援毫秒時間戳或 ISO 字串）"""
    if raw is None or raw == "":
        return "-"
    try:
        if isinstance(raw, (int, float)):
            ts_ms = int(float(raw))
            dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
        elif isinstance(raw, str):
            s = str(raw).strip()
            if s.isdigit():
                ts_ms = int(s)
                dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
            else:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
        else:
            return str(raw)
        return dt.astimezone(_tz8()).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(raw)


def _fmt_dt(dt: datetime) -> str:
    return _normalize_dt(dt).astimezone(_tz8()).strftime("%Y-%m-%d %H:%M")


def _fmt_signal_card_html(payload: dict[str, Any], post_id: str, announced_at: datetime, ttl_seconds: int) -> str:
    f = extract_signal_fields(payload)
    expire_at = _normalize_dt(announced_at) + timedelta(seconds=int(ttl_seconds))

    title = str(payload.get("title") or payload.get("name") or payload.get("symbol") or "交易信号").strip()
    title = html.escape(title)

    lines: list[str] = []
    lines.append(f"<b>{title}</b>")
    lines.append("──────────")
    lines.append(f"<b>信号ID</b>：<code>{html.escape(post_id)}</code>")
    if f.get("symbol"):
        lines.append(f"<b>交易对</b>：<code>{html.escape(str(f['symbol']))}</code>")
    if f.get("direction"):
        lines.append(f"<b>方向</b>：{html.escape(str(f['direction']))}")
    if f.get("entry") is not None:
        lines.append(f"<b>进场价格</b>：{html.escape(str(f['entry']))}")
    if f.get("tp") is not None:
        lines.append(f"<b>止盈价格</b>：{html.escape(str(f['tp']))}")
    if f.get("sl") is not None:
        lines.append(f"<b>止损价格</b>：{html.escape(str(f['sl']))}")

    if ttl_seconds % 3600 == 0:
        ttl_label = f"{ttl_seconds // 3600}小时"
    else:
        ttl_label = f"{ttl_seconds}秒"
    lines.append(f"<b>有效期</b>：{html.escape(ttl_label)}（截止 {html.escape(_fmt_dt(expire_at))}）")
    return "\n".join(lines)


def _kb_amount() -> InlineKeyboardMarkup:
    return _mk_kb(
        [_btn("100", "flow:amt:100"), _btn("500", "flow:amt:500"), _btn("1000", "flow:amt:1000")],
        [_btn("取消下单", "flow:cancel")],
    )


def _kb_leverage() -> InlineKeyboardMarkup:
    return _mk_kb(
        [_btn("5x", "flow:lev:5"), _btn("10x", "flow:lev:10"), _btn("20x", "flow:lev:20")],
        [_btn("50x", "flow:lev:50"), _btn("100x", "flow:lev:100")],
        [_btn("自定义杠杆", "flow:lev_custom")],
        [_btn("修改金额", "flow:edit_amount"), _btn("取消下单", "flow:cancel")],
    )


def _kb_confirm() -> InlineKeyboardMarkup:
    return _mk_kb(
        [_btn("确认下单", "flow:submit"), _btn("取消下单", "flow:cancel")],
        [_btn("修改金额", "flow:edit_amount"), _btn("修改杠杆", "flow:edit_leverage")],
    )


def _kb_leverage_i18n(lang: str) -> InlineKeyboardMarkup:
    return _mk_kb(
        [_btn("5x", "flow:lev:5"), _btn("10x", "flow:lev:10"), _btn("20x", "flow:lev:20")],
        [_btn("50x", "flow:lev:50"), _btn("100x", "flow:lev:100")],
        [_btn(t(lang, "flow_btn_custom_leverage"), "flow:lev_custom")],
        [_btn(t(lang, "flow_btn_edit_amount"), "flow:edit_amount"), _btn(t(lang, "flow_btn_cancel"), "flow:cancel")],
    )


def _kb_confirm_i18n(lang: str) -> InlineKeyboardMarkup:
    return _mk_kb(
        [_btn(t(lang, "flow_btn_submit"), "flow:submit"), _btn(t(lang, "flow_btn_cancel"), "flow:cancel")],
        [_btn(t(lang, "flow_btn_edit_amount"), "flow:edit_amount"), _btn(t(lang, "flow_btn_edit_leverage"), "flow:edit_leverage")],
    )


async def _prompt_amount(message: types.Message, state: FSMContext, lang: str, balance: Optional[float] = None) -> None:
    bal_line = t(lang, "flow_balance_line", balance=f"{balance:g}") if balance is not None else ""
    msg = await message.answer(
        t(lang, "flow_amount_prompt", bal_line=bal_line),
        reply_markup=ForceReply(selective=True, input_field_placeholder=t(lang, "flow_amount_force_reply_placeholder")),
    )
    await state.update_data(amount_prompt_message_id=msg.message_id)


async def _set_amount_and_ask_leverage(chat: types.Message, state: FSMContext, user_id: str, amount: float) -> None:
    ok, reason = await _ensure_signal_alive(state)
    if not ok:
        await state.clear()
        await chat.answer(reason or "当前信号失效，无法操作。")
        return

    balance = await _get_available_balance_usdt(user_id, state=state)
    if balance is None:
        await chat.answer(t(await _get_lang(user_id), "bind_alert"))
        return
    lang = await _get_lang(user_id)
    if balance < amount:
        kb = _mk_kb([[_btn(t(lang, "flow_btn_cancel"), "flow:cancel")]])
        await chat.answer("下单失败：余额不足，请充值。", reply_markup=kb)
        return

    await state.update_data(amount=amount)
    await state.set_state(CopyFlow.waiting_leverage)
    data = await state.get_data()
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    max_lev = await _get_symbol_max_leverage(payload) if payload else MAX_LEVERAGE
    await chat.answer(t(lang, "flow_leverage_select_prompt", max_lev=max_lev))
    await chat.answer(t(lang, "flow_leverage_quick_select"), reply_markup=_kb_leverage_i18n(lang))


async def _set_leverage_and_show_confirm(chat: types.Message, state: FSMContext, user_id: str, lev: int) -> None:
    ok, reason = await _ensure_signal_alive(state)
    if not ok:
        await state.clear()
        await chat.answer(reason or "当前信号失效，无法操作。")
        return

    data = await state.get_data()
    post_id = str(data.get("post_id") or "").strip()
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    amount = data.get("amount")
    if not post_id or amount is None:
        await state.clear()
        await chat.answer("状态已失效，请回到频道重新点击「一键跟单」。")
        return

    await state.update_data(leverage=lev)
    await state.set_state(CopyFlow.waiting_submit)

    announced_at = datetime.fromisoformat(str(data.get("announced_at")))
    signal_card = _fmt_signal_card_html(payload, post_id, announced_at, APP_SETTINGS.signal_ttl_seconds if APP_SETTINGS else 86400)
    confirm_text = (
        "请确认订单信息：\n\n"
        f"{signal_card}\n\n"
        f"<b>跟单金额</b>：<code>{float(amount):g}</code> USDT\n"
        f"<b>杠杆倍数</b>：<code>{lev}</code>x"
    )
    lang = await _get_lang(user_id)

    # 校驗 quantity 是否落在交易對限制內（LIMIT 走 maxDelegateNum/minDelegateNum）
    sym = _norm_symbol_for_exinfo(extract_signal_fields(payload).get("symbol"))
    ci = await get_contract_info(sym) if sym else None
    if ci and getattr(ci, "min_delegate_num", None) is not None and getattr(ci, "max_delegate_num", None) is not None:
        qty = _compute_qty(
            float(amount),
            int(lev),
            extract_signal_fields(payload).get("entry"),
            fee_rate_taker=getattr(ci, "fee_rate_taker", None),
            contract_factor=getattr(ci, "contract_factor", None),
        )
        if qty is None:
            await chat.answer(t(lang, "exinfo_unavailable"))
            return
        min_q = Decimal(int(getattr(ci, "min_delegate_num") or 0))
        max_q = Decimal(int(getattr(ci, "max_delegate_num") or 0))
        if min_q > 0 and max_q > 0 and (qty < min_q or qty > max_q):
            await chat.answer(t(lang, "qty_out_of_range", min_qty=str(min_q), max_qty=str(max_q)))
            return

    msg = await chat.answer(confirm_text, reply_markup=_kb_confirm_i18n(lang))
    await state.update_data(confirm_message_id=msg.message_id)


@router.message(CommandStart())
async def start(message: types.Message, state: FSMContext, command: CommandObject) -> None:
    # 深連結必須在私訊完成互動
    if message.chat.type != "private":
        await message.reply("請點擊頻道訊息中的按鈕，並在與機器人的私訊中完成跟單流程。")
        return

    await state.clear()
    # 第一次互動：初始化使用者語言設定到 DB（若已存在則不覆蓋）
    if message.from_user:
        await _init_user_lang(str(message.from_user.id), message.from_user.language_code)

    args = (command.args or "").strip()
    _ilog(
        "start_received",
        user_id=str(message.from_user.id) if message.from_user else "0",
        chat_type=str(message.chat.type),
        args=args,
    )

    follow_id = _extract_follow_order_id_from_start_args(args)
    if follow_id is not None:
        if APP_SETTINGS is None:
            await message.reply("系统尚未完成初始化，请稍后再试。")
            return

        user_id = str(message.from_user.id) if message.from_user else "0"
        lang = await _get_lang(user_id)

        _ilog(
            "start_deeplink",
            user_id=str(message.from_user.id) if message.from_user else "0",
            follow_order_id=str(follow_id),
        )

        item = await fetch_follow_order_view(
            APP_SETTINGS.follow_order_view_url,
            APP_SETTINGS.follow_order_headers,
            follow_id,
        )
        if item is None:
            await message.reply("获取信号详情失败（可能已过期或不存在）。请回到频道查看最新信号。")
            return

        ts = item.get("update_time") or item.get("create_time")
        try:
            announced_at = datetime.fromtimestamp(int(ts), tz=timezone.utc) if ts is not None else datetime.now(timezone.utc)
        except Exception:
            announced_at = datetime.now(timezone.utc)

        if _is_expired(announced_at, APP_SETTINGS.signal_ttl_seconds):
            await message.reply("当前信号已失效（超过有效期），无法跟单。请回到频道查看最新信号。")
            return

        post_id = str(item.get("id") or follow_id)
        payload: dict[str, Any] = item

        await state.update_data(
            post_id=post_id,
            payload=payload,
            announced_at=_normalize_dt(announced_at).isoformat(),
        )
        await state.set_state(CopyFlow.waiting_entry)

        signal_card = _fmt_signal_card_html(payload, post_id, announced_at, APP_SETTINGS.signal_ttl_seconds)
        image_url = extract_image_url(payload)
        # 入口：先檢查是否綁定，直接把按鈕附在信號卡片訊息上
        is_bound, _platform_uid, verify_url = await _get_binding_status(user_id)
        kb = _kb_entry(lang, is_bound=is_bound, verify_url=verify_url)
        if image_url:
            await message.answer_photo(photo=image_url, caption=signal_card, reply_markup=kb)
        else:
            await message.reply(signal_card, disable_web_page_preview=True, reply_markup=kb)
        return

    await message.reply(
        "已啟動。請到公開頻道點擊『一鍵跟單』按鈕開始。\n\n"
        "指令：/balance 查詢餘額"
    )
    await _show_home_menu(message, user_id=str(message.from_user.id) if message.from_user else "0")


@router.message(lambda m: bool(m.text) and m.text in all_button_texts())
async def handle_home_buttons(message: types.Message, state: FSMContext) -> None:
    if message.chat.type != "private":
        return

    user_id = str(message.from_user.id)
    lang = await _get_lang(user_id)
    text = (message.text or "").strip()
    _ilog("home_button", user_id=user_id, text=text, state=str(await state.get_state()))

    if text == t(lang, "btn_balance") or text in {t("zh-TW", "btn_balance"), t("zh-CN", "btn_balance"), t("en", "btn_balance")}:
        bal = await _get_available_balance_usdt(user_id, state=state)
        if bal is None:
            await message.answer(t(lang, "bind_alert"), reply_markup=_kb_entry(lang, is_bound=False, verify_url=None))
            return
        await message.answer(t(lang, "balance", balance=f"{bal:g}"), reply_markup=_home_reply_kb(lang))
        return

    if text == t(lang, "btn_orders") or text in {t("zh-TW", "btn_orders"), t("zh-CN", "btn_orders"), t("en", "btn_orders")}:
        loading = await message.answer(t(lang, "orders_loading"))
        try:
            await _show_open_orders(message, state, user_id, lang, page=0)
        finally:
            try:
                await loading.delete()
            except Exception:
                pass
        return

    if text == t(lang, "btn_positions") or text in {t("zh-TW", "btn_positions"), t("zh-CN", "btn_positions"), t("en", "btn_positions")}:
        loading = await message.answer(t(lang, "positions_loading"))
        try:
            await _show_positions(message, state, user_id, lang, page=0)
        finally:
            try:
                await loading.delete()
            except Exception:
                pass
        return

    if text == t(lang, "btn_language") or text in {t("zh-TW", "btn_language"), t("zh-CN", "btn_language"), t("en", "btn_language")}:
        kb = _mk_kb(
            *[
                [_btn(label, f"lang:set:{code}")]
                for code, label in SUPPORTED_LANGS
            ]
        )
        await message.answer(t(lang, "choose_language"), reply_markup=kb)
        return


@router.callback_query(lambda c: bool(c.data) and c.data.startswith("lang:set:"))
async def cb_set_language(callback: types.CallbackQuery) -> None:
    if callback.message.chat.type != "private":
        await callback.answer("請在私訊操作", show_alert=True)
        return
    code = callback.data.split(":")[-1].strip()
    if code not in {x[0] for x in SUPPORTED_LANGS}:
        await callback.answer("不支援的語言", show_alert=True)
        return
    user_id = str(callback.from_user.id)
    await set_user_language(user_id, code)
    await callback.message.answer(t(code, "lang_switched"), reply_markup=_home_reply_kb(code))
    _ilog("set_language", user_id=user_id, lang=code)
    await callback.answer()


@router.callback_query(lambda c: c.data == "bind:refresh")
async def cb_bind_refresh(callback: types.CallbackQuery, state: FSMContext) -> None:
    if callback.message.chat.type != "private":
        await callback.answer(t("zh-TW", "flow_private_only"), show_alert=True)
        return
    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)
    _ilog("binding_refresh_clicked", user_id=user_id)
    is_bound, platform_uid, verify_url = await _get_binding_status(user_id)
    _ilog("binding_refresh_result", user_id=user_id, is_bound=bool(is_bound))
    try:
        await callback.bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            reply_markup=_kb_entry(lang, is_bound=is_bound, verify_url=verify_url),
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            logger.error(f"edit_message_reply_markup failed: {e}")
    except Exception as e:  # noqa: BLE001
        logger.error(f"edit_message_reply_markup failed: {e}")

    if not is_bound:
        await callback.answer(t(lang, "bind_alert"), show_alert=True)
        return

    ok, reason = await _ensure_signal_alive(state)
    if not ok:
        await state.clear()
        await callback.message.answer(reason or "当前信号已失效，无法操作。")
        await callback.answer()
        return

    await state.set_state(CopyFlow.waiting_amount)
    balance = await _get_available_balance_usdt(user_id, state=state)
    await callback.message.answer(t(lang, "bind_refresh_bound_ok"))
    if platform_uid:
        await state.update_data(platform_uid=str(platform_uid))
    await _prompt_amount(callback.message, state, lang, balance=balance)
    await callback.answer()


@router.callback_query(lambda c: c.data == "flow:begin_copy")
async def cb_begin_copy(callback: types.CallbackQuery, state: FSMContext) -> None:
    if callback.message.chat.type != "private":
        await callback.answer(t("zh-TW", "flow_private_only"), show_alert=True)
        return
    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)

    # 再次確認綁定（避免剛刷新前後狀態變動）
    ok_bind = await _ensure_bound_or_prompt(callback.message, user_id, lang, state=state)
    if not ok_bind:
        # 用彈窗提示即可，並確保按鈕是未綁定狀態
        try:
            await callback.bot.edit_message_reply_markup(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                reply_markup=_kb_entry(lang, is_bound=False, verify_url=None),
            )
        except Exception:
            pass
        await callback.answer(t(lang, "bind_alert"), show_alert=True)
        return

    ok, reason = await _ensure_signal_alive(state)
    if not ok:
        await state.clear()
        await callback.message.answer(reason or "当前信号已失效，无法操作。")
        await callback.answer()
        return

    await state.set_state(CopyFlow.waiting_amount)
    balance = await _get_available_balance_usdt(user_id, state=state)
    await _prompt_amount(callback.message, state, lang, balance=balance)
    _ilog("begin_copy", user_id=user_id)
    await callback.answer()
@router.callback_query(lambda c: c.data == "flow:cancel")
async def cb_cancel(callback: types.CallbackQuery, state: FSMContext) -> None:
    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)
    data = await state.get_data()
    confirm_msg_id = data.get("confirm_message_id")
    if confirm_msg_id is None or callback.message.message_id != confirm_msg_id:
        await callback.answer(t(lang, "flow_button_expired"), show_alert=True)
        return
    await state.clear()
    await callback.message.answer(t(lang, "flow_cancelled"))
    await _show_home_menu(callback.message, user_id=user_id)
    _ilog("flow_cancel", user_id=str(callback.from_user.id))
    await callback.answer()


@router.callback_query(lambda c: bool(c.data) and c.data.startswith("oo:page:"))
async def cb_open_orders_page(callback: types.CallbackQuery, state: FSMContext) -> None:
    if callback.message.chat.type != "private":
        await callback.answer(t("zh-TW", "flow_private_only"), show_alert=True)
        return
    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)
    try:
        page = int(callback.data.split(":")[-1])
    except Exception:
        page = 0
    await _edit_open_orders_message(callback.message, state, user_id, lang, page, confirm_cancel_all=False)
    await callback.answer()


@router.callback_query(lambda c: bool(c.data) and c.data.startswith("oo:cancel:"))
async def cb_open_orders_cancel(callback: types.CallbackQuery, state: FSMContext) -> None:
    if callback.message.chat.type != "private":
        await callback.answer(t("zh-TW", "flow_private_only"), show_alert=True)
        return
    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)
    parts = (callback.data or "").split(":")
    if len(parts) < 4:
        await callback.answer(t(lang, "orders_cancel_fail", reason="bad_callback"), show_alert=True)
        return
    order_id_raw = parts[2]
    try:
        page = int(parts[3])
    except Exception:
        page = 0
    token = parts[4] if len(parts) >= 5 else ""
    try:
        order_id = int(order_id_raw)
    except Exception:
        await callback.answer(t(lang, "orders_cancel_fail", reason="bad_order_id"), show_alert=True)
        return

    # 軟 TTL：超過 60 秒的列表，要求先刷新
    if token:
        ts = _b36_decode(token)
        now = int(time.time())
        if ts is None or now - int(ts) > int(OPEN_ORDERS_SOFT_TTL_SECONDS):
            await callback.answer(t(lang, "orders_snapshot_expired", ttl=OPEN_ORDERS_SOFT_TTL_SECONDS), show_alert=True)
            await _edit_open_orders_message(callback.message, state, user_id, lang, page, confirm_cancel_all=False)
            return

    if APP_SETTINGS is None or not APP_SETTINGS.platform_api_base_url:
        await callback.answer(t(lang, "exinfo_unavailable"), show_alert=True)
        return
    platform_uid = await _get_platform_uid(user_id, state=state)
    if not platform_uid:
        await callback.answer(t(lang, "bind_alert"), show_alert=True)
        return

    # 撤單前再拉一次 openOrder，避免取消到舊訂單
    items = await fetch_open_orders(
        base_url=str(APP_SETTINGS.platform_api_base_url),
        headers=APP_SETTINGS.platform_api_headers,
        uid=str(platform_uid),
        wallet=str(APP_SETTINGS.platform_wallet),
        brand=str(APP_SETTINGS.platform_brand),
        body={},
    )
    if items is None:
        await callback.answer(t(lang, "exinfo_unavailable"), show_alert=True)
        return
    target: Optional[dict[str, Any]] = None
    for o in items:
        try:
            if int(str(o.get("orderId") or "").strip()) == int(order_id):
                target = o
                break
        except Exception:
            continue
    if target is None:
        await callback.answer(t(lang, "orders_order_gone"), show_alert=True)
        await _edit_open_orders_message(callback.message, state, user_id, lang, page, confirm_cancel_all=False)
        return

    _ilog("open_order_cancel_attempt", user_id=user_id, order_id=order_id)
    ok, resp_json, err = await cancel_order(
        base_url=str(APP_SETTINGS.platform_api_base_url),
        headers=APP_SETTINGS.platform_api_headers,
        cancel_path=str(APP_SETTINGS.platform_cancel_order_path),
        uid=str(platform_uid),
        wallet=str(APP_SETTINGS.platform_wallet),
        brand=str(APP_SETTINGS.platform_brand),
        order_id=order_id,
        symbol=str(target.get("symbol") or "").strip() or None,
    )
    _ilog("open_order_cancel_result", user_id=user_id, order_id=order_id, ok=bool(ok), error=str(err) if err else None)
    if not ok:
        await callback.answer(t(lang, "orders_cancel_fail", reason=platform_error_text(lang, resp_json, err)), show_alert=True)
    else:
        await callback.answer(t(lang, "orders_cancel_ok"), show_alert=True)
    # 撤單後刷新當前頁（更新同一則訊息）
    await _edit_open_orders_message(callback.message, state, user_id, lang, page, confirm_cancel_all=False)


@router.callback_query(lambda c: bool(c.data) and c.data.startswith("oo:cancel_all:"))
async def cb_open_orders_cancel_all(callback: types.CallbackQuery, state: FSMContext) -> None:
    if callback.message.chat.type != "private":
        await callback.answer(t("zh-TW", "flow_private_only"), show_alert=True)
        return
    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)
    parts = (callback.data or "").split(":")
    page = 0
    if len(parts) >= 3:
        try:
            page = int(parts[2])
        except Exception:
            page = 0
    _ilog("open_order_cancel_all_clicked", user_id=user_id, page=page)
    await callback.answer(t(lang, "orders_cancel_all_alert"), show_alert=True)
    await _edit_open_orders_message(callback.message, state, user_id, lang, page, confirm_cancel_all=True)


@router.callback_query(lambda c: bool(c.data) and c.data.startswith("oo:cancel_all_back:"))
async def cb_open_orders_cancel_all_back(callback: types.CallbackQuery, state: FSMContext) -> None:
    if callback.message.chat.type != "private":
        await callback.answer(t("zh-TW", "flow_private_only"), show_alert=True)
        return
    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)
    parts = (callback.data or "").split(":")
    page = 0
    if len(parts) >= 3:
        try:
            page = int(parts[2])
        except Exception:
            page = 0
    _ilog("open_order_cancel_all_back", user_id=user_id, page=page)
    await callback.answer()
    await _edit_open_orders_message(callback.message, state, user_id, lang, page, confirm_cancel_all=False)


@router.callback_query(lambda c: bool(c.data) and c.data.startswith("oo:cancel_all_confirm:"))
async def cb_open_orders_cancel_all_confirm(callback: types.CallbackQuery, state: FSMContext) -> None:
    if callback.message.chat.type != "private":
        await callback.answer(t("zh-TW", "flow_private_only"), show_alert=True)
        return
    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)
    parts = (callback.data or "").split(":")
    page = 0
    if len(parts) >= 3:
        try:
            page = int(parts[2])
        except Exception:
            page = 0
    token = parts[3] if len(parts) >= 4 else ""

    # 軟 TTL：超過 60 秒的列表，要求先刷新
    if token:
        ts = _b36_decode(token)
        now = int(time.time())
        if ts is None or now - int(ts) > int(OPEN_ORDERS_SOFT_TTL_SECONDS):
            await callback.answer(t(lang, "orders_snapshot_expired", ttl=OPEN_ORDERS_SOFT_TTL_SECONDS), show_alert=True)
            await _edit_open_orders_message(callback.message, state, user_id, lang, page, confirm_cancel_all=False)
            return

    if APP_SETTINGS is None or not APP_SETTINGS.platform_api_base_url:
        await callback.answer(t(lang, "exinfo_unavailable"), show_alert=True)
        return
    platform_uid = await _get_platform_uid(user_id, state=state)
    if not platform_uid:
        await callback.answer(t(lang, "bind_alert"), show_alert=True)
        return

    items = await fetch_open_orders(
        base_url=str(APP_SETTINGS.platform_api_base_url),
        headers=APP_SETTINGS.platform_api_headers,
        uid=str(platform_uid),
        wallet=str(APP_SETTINGS.platform_wallet),
        brand=str(APP_SETTINGS.platform_brand),
        body={},
    )
    if items is None:
        await callback.answer(t(lang, "exinfo_unavailable"), show_alert=True)
        return

    order_ids: list[int] = []
    by_symbol: dict[str, list[int]] = {}
    for o in items:
        try:
            oid = int(str(o.get("orderId") or "").strip())
        except Exception:
            continue
        if oid > 0:
            order_ids.append(oid)
            sym_raw = str(o.get("symbol") or "").strip().upper()
            if sym_raw:
                by_symbol.setdefault(sym_raw, []).append(oid)

    if not order_ids:
        await callback.answer(t(lang, "orders_cancel_all_none"), show_alert=True)
        await _edit_open_orders_message(callback.message, state, user_id, lang, page, confirm_cancel_all=False)
        return

    _ilog("open_order_cancel_all_confirmed", user_id=user_id, count=len(order_ids))

    # 後端可能實際需要 symbol 才能批量撤單；按 symbol 分組逐批撤單更安全
    total = len(order_ids)
    ok_count = 0
    fail_reasons: list[str] = []
    if not by_symbol:
        by_symbol = {"": order_ids}

    for sym_raw, ids in by_symbol.items():
        ok, resp_json, err = await batch_cancel_orders(
            base_url=str(APP_SETTINGS.platform_api_base_url),
            headers=APP_SETTINGS.platform_api_headers,
            cancel_path=str(APP_SETTINGS.platform_cancel_order_path),
            uid=str(platform_uid),
            wallet=str(APP_SETTINGS.platform_wallet),
            brand=str(APP_SETTINGS.platform_brand),
            order_ids=ids,
            client_order_ids=None,
            symbol=(sym_raw or None),
        )
        _ilog(
            "open_order_cancel_all_group_result",
            user_id=user_id,
            symbol=sym_raw or None,
            ok=bool(ok),
            count=len(ids),
            error=str(err) if err else None,
        )
        if ok:
            ok_count += len(ids)
        else:
            fail_reasons.append(platform_error_text(lang, resp_json, err))

    _ilog(
        "open_order_cancel_all_result",
        user_id=user_id,
        ok=bool(ok_count == total),
        count=total,
        ok_count=ok_count,
        error=fail_reasons[0] if fail_reasons else None,
    )
    if ok_count <= 0:
        await callback.answer(t(lang, "orders_cancel_all_fail", reason=(fail_reasons[0] if fail_reasons else "failed")), show_alert=True)
    elif ok_count < total:
        await callback.answer(t(lang, "orders_cancel_all_partial", ok=ok_count, total=total), show_alert=True)
    else:
        await callback.answer(t(lang, "orders_cancel_all_done", count=total), show_alert=True)
    await _edit_open_orders_message(callback.message, state, user_id, lang, page, confirm_cancel_all=False)


@router.callback_query(lambda c: bool(c.data) and c.data.startswith("pos:page:"))
async def cb_positions_page(callback: types.CallbackQuery, state: FSMContext) -> None:
    if callback.message.chat.type != "private":
        await callback.answer(t("zh-TW", "flow_private_only"), show_alert=True)
        return
    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)
    try:
        page = int(callback.data.split(":")[-1])
    except Exception:
        page = 0
    await _edit_positions_message(callback.message, state, user_id, lang, page)
    await callback.answer()


@router.callback_query(lambda c: bool(c.data) and c.data.startswith("pos:close:"))
async def cb_position_close(callback: types.CallbackQuery, state: FSMContext) -> None:
    """單筆平倉"""
    if callback.message.chat.type != "private":
        await callback.answer(t("zh-TW", "flow_private_only"), show_alert=True)
        return
    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)
    platform_uid = await _get_platform_uid(user_id, state=state)
    if not platform_uid or not APP_SETTINGS or not APP_SETTINGS.platform_api_base_url:
        await callback.answer(t(lang, "exinfo_unavailable"), show_alert=True)
        return

    parts = callback.data.split(":")
    # pos:close:symbol:positionSide:page:token
    if len(parts) < 6:
        await callback.answer(t(lang, "positions_close_fail", reason="invalid data"), show_alert=True)
        return
    symbol, position_side, page_s, token = parts[2], parts[3], parts[4], parts[5]
    try:
        page = int(page_s)
    except Exception:
        page = 0

    items = await fetch_positions(
        base_url=str(APP_SETTINGS.platform_api_base_url),
        headers=APP_SETTINGS.platform_api_headers,
        contract_type=2,
        uid=str(platform_uid),
        brand=str(APP_SETTINGS.platform_brand),
        symbol=None,
    )
    if items is None:
        await callback.answer(t(lang, "exinfo_unavailable"), show_alert=True)
        return
    vol: Any = None
    sym_norm = _norm_symbol_for_match(symbol)
    for p in items:
        if _norm_symbol_for_match(str(p.get("symbol") or "")) == sym_norm and _position_side_from_api(p) == position_side:
            vol = p.get("volume")
            break
    ci = await get_contract_info(sym_norm) if sym_norm else None
    cf = getattr(ci, "contract_factor", None) if ci else None
    contracts = _volume_to_contracts(vol, cf)
    body = _build_close_position_body(symbol, position_side, contracts)
    ok, resp_json, err = await place_trade_order(
        base_url=str(APP_SETTINGS.platform_api_base_url),
        headers=APP_SETTINGS.platform_api_headers,
        uid=str(platform_uid),
        wallet=str(APP_SETTINGS.platform_wallet),
        brand=str(APP_SETTINGS.platform_brand),
        body=body,
    )
    if ok:
        await callback.answer(t(lang, "positions_close_ok"), show_alert=True)
    else:
        await callback.answer(t(lang, "positions_close_fail", reason=platform_error_text(lang, resp_json, err)), show_alert=True)
    await _edit_positions_message(callback.message, state, user_id, lang, page, confirm_close_all=False)


@router.callback_query(lambda c: bool(c.data) and c.data.startswith("pos:close_all:"))
async def cb_position_close_all(callback: types.CallbackQuery, state: FSMContext) -> None:
    """一鍵平倉：顯示二次確認"""
    if callback.message.chat.type != "private":
        await callback.answer(t("zh-TW", "flow_private_only"), show_alert=True)
        return
    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)
    parts = callback.data.split(":")
    if len(parts) < 4:
        await callback.answer()
        return
    try:
        page = int(parts[2])
    except Exception:
        page = 0
    await callback.answer(t(lang, "positions_close_all_alert"), show_alert=True)
    await _edit_positions_message(callback.message, state, user_id, lang, page, confirm_close_all=True)


@router.callback_query(lambda c: bool(c.data) and c.data.startswith("pos:close_all_back:"))
async def cb_position_close_all_back(callback: types.CallbackQuery, state: FSMContext) -> None:
    """一鍵平倉：返回"""
    if callback.message.chat.type != "private":
        await callback.answer(t("zh-TW", "flow_private_only"), show_alert=True)
        return
    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)
    parts = callback.data.split(":")
    try:
        page = int(parts[2])
    except Exception:
        page = 0
    await _edit_positions_message(callback.message, state, user_id, lang, page, confirm_close_all=False)
    await callback.answer()


@router.callback_query(lambda c: bool(c.data) and c.data.startswith("pos:close_all_confirm:"))
async def cb_position_close_all_confirm(callback: types.CallbackQuery, state: FSMContext) -> None:
    """一鍵平倉：確認執行"""
    if callback.message.chat.type != "private":
        await callback.answer(t("zh-TW", "flow_private_only"), show_alert=True)
        return
    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)
    platform_uid = await _get_platform_uid(user_id, state=state)
    if not platform_uid or not APP_SETTINGS or not APP_SETTINGS.platform_api_base_url:
        await callback.answer(t(lang, "exinfo_unavailable"), show_alert=True)
        return

    parts = callback.data.split(":")
    try:
        page = int(parts[2])
    except Exception:
        page = 0

    items = await fetch_positions(
        base_url=str(APP_SETTINGS.platform_api_base_url),
        headers=APP_SETTINGS.platform_api_headers,
        contract_type=2,
        uid=str(platform_uid),
        brand=str(APP_SETTINGS.platform_brand),
        symbol=None,
    )
    if items is None:
        await callback.answer(t(lang, "exinfo_unavailable"), show_alert=True)
        await _edit_positions_message(callback.message, state, user_id, lang, page, confirm_close_all=False)
        return

    positions_to_close: list[tuple[str, str, Any, Any]] = []
    for p in items:
        sym = str(p.get("symbol") or "").strip().upper()
        if sym:
            pos_side = _position_side_from_api(p)
            vol = p.get("volume")
            sn = _norm_symbol_for_match(sym)
            ci = await get_contract_info(sn) if sn else None
            cf = getattr(ci, "contract_factor", None) if ci else None
            positions_to_close.append((sym, pos_side, vol, cf))

    if not positions_to_close:
        await callback.answer(t(lang, "positions_close_all_none"), show_alert=True)
        await _edit_positions_message(callback.message, state, user_id, lang, page, confirm_close_all=False)
        return

    total = len(positions_to_close)
    ok_count = 0
    fail_reasons: list[str] = []
    for symbol, position_side, volume, contract_factor in positions_to_close:
        contracts = _volume_to_contracts(volume, contract_factor)
        body = _build_close_position_body(symbol, position_side, contracts)
        ok, resp_json, err = await place_trade_order(
            base_url=str(APP_SETTINGS.platform_api_base_url),
            headers=APP_SETTINGS.platform_api_headers,
            uid=str(platform_uid),
            wallet=str(APP_SETTINGS.platform_wallet),
            brand=str(APP_SETTINGS.platform_brand),
            body=body,
        )
        if ok:
            ok_count += 1
        else:
            fail_reasons.append(platform_error_text(lang, resp_json, err))

    if ok_count <= 0:
        await callback.answer(t(lang, "positions_close_all_fail", reason=(fail_reasons[0] if fail_reasons else "failed")), show_alert=True)
    elif ok_count < total:
        await callback.answer(t(lang, "positions_close_all_partial", ok=ok_count, total=total), show_alert=True)
    else:
        await callback.answer(t(lang, "positions_close_all_done", count=total), show_alert=True)
    await _edit_positions_message(callback.message, state, user_id, lang, page, confirm_close_all=False)


@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext) -> None:
    if message.chat.type != "private":
        return
    await state.clear()
    user_id = str(message.from_user.id) if message.from_user else "0"
    lang = await _get_lang(user_id)
    await message.answer(t(lang, "flow_cancelled"))
    await _show_home_menu(message, user_id=user_id)
    _ilog("flow_cancel_cmd", user_id=str(message.from_user.id) if message.from_user else "0")


@router.callback_query(lambda c: bool(c.data) and c.data.startswith("flow:amt:"))
async def cb_amount_preset(callback: types.CallbackQuery, state: FSMContext) -> None:
    # 金额统一走回覆框手动输入，避免聊天里多次操作造成错乱
    ok, reason = await _ensure_signal_alive(state)
    if not ok:
        await state.clear()
        await callback.message.answer(reason or "当前信号已失效，无法操作。")
        await callback.answer()
        return
    await state.set_state(CopyFlow.waiting_amount)
    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)
    balance = await _get_available_balance_usdt(user_id, state=state)
    await _prompt_amount(callback.message, state, lang, balance=balance)
    _ilog("amount_preset_blocked", user_id=str(callback.from_user.id), data=str(callback.data))
    await callback.answer(t(lang, "flow_use_reply_amount_alert"), show_alert=True)


@router.callback_query(lambda c: bool(c.data) and c.data.startswith("flow:lev:"))
async def cb_leverage_preset(callback: types.CallbackQuery, state: FSMContext) -> None:
    lev_raw = callback.data.split(":")[-1]
    try:
        lev = int(lev_raw)
    except ValueError:
        await callback.answer("槓桿不正確", show_alert=True)
        return
    # 依交易對限制校驗槓桿上限
    data = await state.get_data()
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    sym_key = _norm_symbol_for_exinfo(extract_signal_fields(payload).get("symbol"))
    ci = await get_contract_info(sym_key) if sym_key else None
    sym_api = _symbol_for_backend(extract_signal_fields(payload).get("symbol"), ci)
    max_lev = int(getattr(ci, "leverage_level", 0) or 0) if ci else 0
    if max_lev and lev > max_lev:
        lang = await _get_lang(str(callback.from_user.id))
        await callback.answer(t(lang, "lev_too_high", max_lev=max_lev), show_alert=True)
        return
    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)
    # 設定槓桿（後端以該值下單）
    ok_set, err = await _set_symbol_leverage(
        user_id=user_id,
        state=state,
        lang=lang,
        symbol=sym_api,
        leverage=lev,
    )
    if not ok_set:
        await callback.answer(t(lang, "lev_set_failed"), show_alert=True)
        return

    # 檢查 maxNotionalValue（若後端回傳）
    data2 = await state.get_data()
    max_notional = data2.get("leverage_max_notional")
    amt = data2.get("amount")
    if max_notional is not None and amt is not None:
        try:
            notional = Decimal(str(amt)) * Decimal(str(lev))
            if notional > Decimal(str(max_notional)):
                await callback.answer(t(lang, "notional_too_high", max_notional=str(max_notional)), show_alert=True)
                return
        except Exception:
            pass

    await _set_leverage_and_show_confirm(callback.message, state, user_id, lev)
    _ilog("leverage_preset", user_id=str(callback.from_user.id), leverage=lev)
    await callback.answer()


@router.callback_query(lambda c: c.data == "flow:lev_custom")
async def cb_leverage_custom(callback: types.CallbackQuery, state: FSMContext) -> None:
    if callback.message.chat.type != "private":
        user_id = str(callback.from_user.id)
        lang = await _get_lang(user_id)
        await callback.answer(t(lang, "flow_private_only"), show_alert=True)
        return
    ok, reason = await _ensure_signal_alive(state)
    if not ok:
        await state.clear()
        await callback.message.answer(reason or "当前信号已失效，无法操作。")
        await callback.answer()
        return
    await state.set_state(CopyFlow.waiting_leverage_custom)
    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)
    # 自訂槓桿屬於下單流程的一部分，未綁定不允許繼續
    if callback.message:
        ok = await _ensure_bound_or_prompt(callback.message, user_id, lang, state=state)
        if not ok:
            await callback.answer(t(lang, "bind_alert"), show_alert=True)
            return
    data = await state.get_data()
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    max_lev = await _get_symbol_max_leverage(payload) if payload else MAX_LEVERAGE
    msg = await callback.message.answer(
        t(lang, "flow_leverage_custom_prompt", max_lev=max_lev),
        reply_markup=ForceReply(selective=True, input_field_placeholder=t(lang, "flow_leverage_placeholder")),
    )
    await state.update_data(leverage_prompt_message_id=msg.message_id)
    _ilog("leverage_custom_prompt", user_id=str(callback.from_user.id), prompt_id=msg.message_id)
    await callback.answer()


@router.callback_query(lambda c: c.data == "flow:edit_amount")
async def cb_edit_amount(callback: types.CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    post_id = str(data.get("post_id") or "").strip()
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    if not post_id or not payload:
        user_id = str(callback.from_user.id)
        lang = await _get_lang(user_id)
        await callback.answer(t(lang, "flow_button_expired"), show_alert=True)
        return
    # 若使用者在「確認頁」點擊修改金額，修改完成後應直接回到確認頁（保留既有槓桿）
    return_confirm = data.get("leverage") is not None
    await state.set_state(CopyFlow.waiting_amount)
    await state.update_data(edit_amount_return_confirm=bool(return_confirm))
    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)
    balance = await _get_available_balance_usdt(user_id, state=state)
    await _prompt_amount(callback.message, state, lang, balance=balance)
    await callback.answer()


@router.callback_query(lambda c: c.data == "flow:edit_leverage")
async def cb_edit_leverage(callback: types.CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    post_id = str(data.get("post_id") or "").strip()
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    if not post_id or not payload:
        user_id = str(callback.from_user.id)
        lang = await _get_lang(user_id)
        await callback.answer(t(lang, "flow_button_expired"), show_alert=True)
        return
    await state.set_state(CopyFlow.waiting_leverage)
    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)
    max_lev = await _get_symbol_max_leverage(payload)
    await callback.message.answer(t(lang, "flow_leverage_select_prompt", max_lev=max_lev))
    await callback.message.answer(t(lang, "flow_leverage_quick_select"), reply_markup=_kb_leverage_i18n(lang))
    await callback.answer()


@router.message(CopyFlow.waiting_amount)
async def on_amount(message: types.Message, state: FSMContext) -> None:
    ok, reason = await _ensure_signal_alive(state)
    if not ok:
        await state.clear()
        await message.reply(reason or "当前信号已失效，无法操作。")
        return
    data = await state.get_data()
    prompt_id = data.get("amount_prompt_message_id")
    if not isinstance(prompt_id, int) or not message.reply_to_message or message.reply_to_message.message_id != prompt_id:
        user_id = str(message.from_user.id)
        lang = await _get_lang(user_id)
        balance = await _get_available_balance_usdt(user_id, state=state)
        await message.reply(t(lang, "flow_amount_reply_mismatch"))
        await _prompt_amount(message, state, lang, balance=balance)
        return

    amount = _parse_amount(message.text or "")
    if amount is None:
        user_id = str(message.from_user.id)
        lang = await _get_lang(user_id)
        balance = await _get_available_balance_usdt(user_id, state=state)
        await message.reply(t(lang, "flow_amount_invalid"))
        await _prompt_amount(message, state, lang, balance=balance)
        return

    user_id = str(message.from_user.id)
    lang = await _get_lang(user_id)
    _ilog("amount_input", user_id=user_id, amount=amount)

    # 若是從確認頁進來的修改金額：修改後直接回確認頁，保留原本槓桿
    if bool(data.get("edit_amount_return_confirm")) and data.get("leverage") is not None:
        balance = await _get_available_balance_usdt(user_id, state=state)
        if balance is None:
            await message.reply(t(lang, "bind_alert"))
            return
        if balance < float(amount):
            kb = _mk_kb([[_btn(t(lang, "flow_btn_cancel"), "flow:cancel")]])
            await message.reply("下单失败：余额不足，请充值。", reply_markup=kb)
            return
        await state.update_data(amount=float(amount), edit_amount_return_confirm=False)
        await _set_leverage_and_show_confirm(message, state, user_id, int(data.get("leverage")))
        return

    # 其他情況（首次輸入金額等）：維持既有流程，進入選擇槓桿
    await _set_amount_and_ask_leverage(message, state, user_id, amount)


@router.message(CopyFlow.waiting_leverage)
async def on_leverage(message: types.Message, state: FSMContext) -> None:
    ok, reason = await _ensure_signal_alive(state)
    if not ok:
        await state.clear()
        await message.reply(reason or "当前信号已失效，无法操作。")
        return
    user_id = str(message.from_user.id) if message.from_user else "0"
    lang = await _get_lang(user_id)
    lev = _parse_leverage(message.text or "")
    if lev is None:
        data = await state.get_data()
        payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
        max_lev = await _get_symbol_max_leverage(payload) if payload else MAX_LEVERAGE
        await message.reply(
            t(lang, "flow_leverage_invalid", max_lev=max_lev),
            reply_markup=ForceReply(selective=True, input_field_placeholder=t(lang, "flow_leverage_placeholder")),
        )
        return
    data = await state.get_data()
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    sym_key = _norm_symbol_for_exinfo(extract_signal_fields(payload).get("symbol"))
    ci = await get_contract_info(sym_key) if sym_key else None
    sym_api = _symbol_for_backend(extract_signal_fields(payload).get("symbol"), ci)
    max_lev = int(getattr(ci, "leverage_level", 0) or 0) if ci else 0
    if max_lev and lev > max_lev:
        await message.reply(t(lang, "lev_too_high", max_lev=max_lev))
        return
    ok_set, err = await _set_symbol_leverage(
        user_id=user_id, state=state, lang=lang, symbol=sym_api, leverage=lev,
    )
    if not ok_set:
        await message.reply(t(lang, "lev_set_failed"))
        return
    data2 = await state.get_data()
    max_notional = data2.get("leverage_max_notional")
    amt = data2.get("amount")
    if max_notional is not None and amt is not None:
        try:
            notional = Decimal(str(amt)) * Decimal(str(lev))
            if notional > Decimal(str(max_notional)):
                await message.reply(t(lang, "notional_too_high", max_notional=str(max_notional)))
                return
        except Exception:
            pass
    await _set_leverage_and_show_confirm(message, state, user_id, lev)
    _ilog("leverage_input", user_id=user_id, leverage=lev)


@router.message(CopyFlow.waiting_leverage_custom)
async def on_leverage_custom(message: types.Message, state: FSMContext) -> None:
    ok, reason = await _ensure_signal_alive(state)
    if not ok:
        await state.clear()
        await message.reply(reason or "当前信号已失效，无法操作。")
        return
    data = await state.get_data()
    prompt_id = data.get("leverage_prompt_message_id")
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    max_lev = await _get_symbol_max_leverage(payload) if payload else MAX_LEVERAGE
    if not isinstance(prompt_id, int) or not message.reply_to_message or message.reply_to_message.message_id != prompt_id:
        user_id = str(message.from_user.id) if message.from_user else "0"
        lang = await _get_lang(user_id)
        msg = await message.reply(
            t(lang, "flow_leverage_reply_mismatch", max_lev=max_lev),
            reply_markup=ForceReply(selective=True, input_field_placeholder=t(lang, "flow_leverage_placeholder")),
        )
        await state.update_data(leverage_prompt_message_id=msg.message_id)
        return
    lev = _parse_leverage(message.text or "")
    if lev is None:
        user_id = str(message.from_user.id) if message.from_user else "0"
        lang = await _get_lang(user_id)
        msg = await message.reply(
            t(lang, "flow_leverage_invalid", max_lev=max_lev),
            reply_markup=ForceReply(selective=True, input_field_placeholder=t(lang, "flow_leverage_placeholder")),
        )
        await state.update_data(leverage_prompt_message_id=msg.message_id)
        return
    # 依交易對限制校驗槓桿上限
    data = await state.get_data()
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    sym_key = _norm_symbol_for_exinfo(extract_signal_fields(payload).get("symbol"))
    ci = await get_contract_info(sym_key) if sym_key else None
    sym_api = _symbol_for_backend(extract_signal_fields(payload).get("symbol"), ci)
    max_lev = int(getattr(ci, "leverage_level", 0) or 0) if ci else 0
    if max_lev and lev > max_lev:
        user_id = str(message.from_user.id) if message.from_user else "0"
        lang = await _get_lang(user_id)
        await message.reply(t(lang, "lev_too_high", max_lev=max_lev))
        return

    user_id = str(message.from_user.id) if message.from_user else "0"
    lang = await _get_lang(user_id)
    ok_set, err = await _set_symbol_leverage(
        user_id=user_id,
        state=state,
        lang=lang,
        symbol=sym_api,
        leverage=lev,
    )
    if not ok_set:
        await message.reply(t(lang, "lev_set_failed"))
        return

    data2 = await state.get_data()
    max_notional = data2.get("leverage_max_notional")
    amt = data2.get("amount")
    if max_notional is not None and amt is not None:
        try:
            notional = Decimal(str(amt)) * Decimal(str(lev))
            if notional > Decimal(str(max_notional)):
                await message.reply(t(lang, "notional_too_high", max_notional=str(max_notional)))
                return
        except Exception:
            pass
    await _set_leverage_and_show_confirm(message, state, str(message.from_user.id) if message.from_user else "0", lev)
    _ilog("leverage_custom_input", user_id=str(message.from_user.id), leverage=lev)


@router.callback_query(lambda c: c.data == "flow:submit")
async def cb_submit(callback: types.CallbackQuery, state: FSMContext) -> None:
    if callback.message.chat.type != "private":
        await callback.answer("請在私訊完成操作", show_alert=True)
        return

    user_id = str(callback.from_user.id)
    lang = await _get_lang(user_id)
    data = await state.get_data()
    confirm_msg_id = data.get("confirm_message_id")
    if confirm_msg_id is None or callback.message.message_id != confirm_msg_id:
        await callback.answer(t(lang, "flow_button_expired"), show_alert=True)
        return

    ok, reason = await _ensure_signal_alive(state)
    if not ok:
        await state.clear()
        await callback.message.answer(reason or "当前信号已失效，无法操作。")
        await callback.answer()
        return

    data = await state.get_data()
    post_id = str(data.get("post_id") or "").strip()
    amount = data.get("amount")
    leverage = data.get("leverage")
    if not post_id or amount is None or leverage is None:
        await state.clear()
        await callback.message.answer("状态已失效，请回到频道重新点击「一键跟单」。")
        await callback.answer()
        return

    ok_bind = await _ensure_bound_or_prompt(callback.message, user_id, lang, state=state)
    if not ok_bind:
        await callback.answer(t(lang, "bind_alert"), show_alert=True)
        return
    balance = await _get_available_balance_usdt(user_id, state=state)
    if balance is None:
        await callback.answer(t(lang, "bind_alert"), show_alert=True)
        return
    if balance < float(amount):
        await callback.message.answer("下单失败：余额不足，请充值。")
        await callback.answer()
        return

    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    if APP_SETTINGS is None or not APP_SETTINGS.platform_api_base_url:
        await callback.message.answer("系统未配置 PLATFORM_API_BASE_URL，无法下单。")
        await callback.answer()
        return

    # 以 DB/狀態取得 platform_uid（不要只依賴 state 內的舊值）
    platform_uid = await _get_platform_uid(user_id, state=state)
    if platform_uid:
        await state.update_data(platform_uid=str(platform_uid))
        payload["_platform_uid"] = str(platform_uid)
    if not platform_uid:
        _ilog("submit_platform_uid_missing", user_id=user_id, post_id=post_id)
        await callback.answer(t(lang, "bind_alert"), show_alert=True)
        return

    # 下單 quantity 需用「張數」計算，依交易對 market_info（exchange_info）欄位：
    # fee_rate_taker / contract_factor
    sig = extract_signal_fields(payload)
    sym = _norm_symbol_for_exinfo(sig.get("symbol"))
    ci = await get_contract_info(sym) if sym else None
    fee_rate_taker = getattr(ci, "fee_rate_taker", None) if ci else None
    contract_factor = getattr(ci, "contract_factor", None) if ci else None
    if fee_rate_taker is None or contract_factor is None:
        _ilog(
            "submit_missing_market_info",
            user_id=user_id,
            post_id=post_id,
            symbol=str(sym),
            has_fee=fee_rate_taker is not None,
            has_cf=contract_factor is not None,
        )
        await callback.message.answer(t(lang, "exinfo_unavailable"))
        await callback.answer()
        return

    # 組裝下單參數快照（用於日誌/DB 除錯）
    lev_int = int(leverage)
    contracts = None
    try:
        contracts = _compute_qty(
            float(amount),
            lev_int,
            sig.get("entry"),
            fee_rate_taker=fee_rate_taker,
            contract_factor=contract_factor,
        )
    except Exception:
        contracts = None
    params_snapshot: dict[str, Any] = {
        "user_id": user_id,
        "post_id": post_id,
        "platform_uid": str(platform_uid),
        "amount": float(amount),
        "leverage": lev_int,
        "symbol_raw": sig.get("symbol"),
        "symbol_norm": sym,
        "direction": sig.get("direction"),
        "entry": sig.get("entry"),
        "tp": sig.get("tp"),
        "sl": sig.get("sl"),
        "fee_rate_taker": fee_rate_taker,
        "contract_factor": contract_factor,
        "quantity_contracts": int(contracts) if contracts is not None else None,
    }
    # 日誌只輸出精簡版（避免過長）；DB 會存完整 JSON
    try:
        logger.info(f"[order_params] {json.dumps(params_snapshot, ensure_ascii=False, separators=(',', ':'), default=str)}")
    except Exception:
        pass

    # 先扣款（后续可调整为：下单成功后再扣）
    await set_balance(user_id, balance - float(amount))
    order_id = await create_copy_order(
        user_id=user_id,
        post_id=post_id,
        amount=float(amount),
        leverage=int(leverage),
        params=params_snapshot,
    )
    _ilog(
        "submit_clicked",
        user_id=user_id,
        post_id=post_id,
        amount=float(amount),
        leverage=int(leverage),
        order_id=order_id,
        platform_uid=str(platform_uid),
    )

    msg_progress = await callback.message.answer(t(lang, "order_delegating"))

    ack = await place_order_async(
        payload,
        float(amount),
        int(leverage),
        lang=lang,
        platform_uid=str(platform_uid),
        base_url=str(APP_SETTINGS.platform_api_base_url),
        headers=APP_SETTINGS.platform_api_headers,
        wallet=str(APP_SETTINGS.platform_wallet),
        brand=str(APP_SETTINGS.platform_brand),
        fee_rate_taker=fee_rate_taker,
        contract_factor=contract_factor,
    )
    if not ack.ok or not ack.request_id:
        await update_copy_order_status(order_id, "rejected")
        await set_balance(user_id, balance)
        await state.clear()
        reason = (ack.error or t(lang, "unknown_error")).strip()
        try:
            await callback.bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=msg_progress.message_id,
                text=f"{t(lang, 'order_failed')}\n{t(lang, 'reason_line', reason=html.escape(reason))}",
                parse_mode=ParseMode.HTML,
            )
        except TelegramBadRequest:
            await callback.message.answer(f"{t(lang, 'order_failed')}\n{t(lang, 'reason_line', reason=reason)}")
        await callback.answer()
        return

    await update_copy_order_status(order_id, "submitted")
    resp = ack.response_data or {}
    api_order_id = resp.get("orderId") or resp.get("clientOrderId") or order_id
    volume_raw = resp.get("volume")
    price_raw = resp.get("markPrice") or resp.get("lastPrice") or resp.get("price")
    cf = _dec(contract_factor)
    position_value_s = "-"
    try:
        v = float(volume_raw) if volume_raw is not None else None
        p = float(price_raw) if price_raw is not None else None
        if v is not None and p is not None and v > 0 and p > 0 and cf is not None and cf > 0:
            pv = Decimal(str(v)) * cf * Decimal(str(p))
            position_value_s = f"{pv.quantize(Decimal('0.01')):f}"
    except Exception:
        pass
    delegated_text = t(lang, "order_delegated_ok", order_id=html.escape(str(api_order_id)), position_value=html.escape(position_value_s))
    try:
        await callback.bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=msg_progress.message_id,
            text=delegated_text,
            parse_mode=ParseMode.HTML,
        )
    except TelegramBadRequest:
        await callback.message.answer(delegated_text)
    await callback.bot.send_message(chat_id=callback.message.chat.id, text="\u200b", reply_markup=_home_reply_kb(lang))

    await callback.answer()
    await state.clear()


@router.message(Command("balance"))
async def cmd_balance(message: types.Message) -> None:
    if message.chat.type != "private":
        await message.reply("請在私訊使用此指令。")
        return
    user_id = str(message.from_user.id)
    lang = await _get_lang(user_id)
    balance = await _get_available_balance_usdt(user_id)
    if balance is None:
        await message.reply(t(lang, "bind_alert"))
        return
    await message.reply(t(lang, "balance", balance=f"{balance:g}"))


async def main() -> None:
    settings = load_settings()
    global APP_SETTINGS
    APP_SETTINGS = settings

    logger.info(
        "Settings: require_binding={} bind_status_url={} bind_cache_seconds={}",
        bool(settings.require_binding),
        str(settings.bind_status_url),
        int(settings.bind_cache_seconds),
    )
    logger.info("Settings: bind_third_type={} bind_brand={}", str(settings.bind_third_type), str(settings.bind_brand))
    logger.info(
        "Settings: platform_api_base_url={} wallet={} brand={}",
        str(settings.platform_api_base_url),
        str(settings.platform_wallet),
        str(settings.platform_brand),
    )

    init_storage(settings.database_url)
    await init_db()

    session: Optional[AiohttpSession] = None
    proxy_url = (settings.telegram_proxy or "").strip()
    if proxy_url and "proxy-host" not in proxy_url.lower():
        session = AiohttpSession(proxy=proxy_url)
        disp = proxy_url.split("@")[-1] if "@" in proxy_url else proxy_url
        logger.info("Telegram Bot 使用代理: {}", disp)
    elif proxy_url and "proxy-host" in proxy_url.lower():
        logger.warning("TELEGRAM_PROXY 為範例佔位符 (proxy-host)，已略過。請改為實際代理位址或清空此變數。")

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )

    me = await bot.get_me()
    bot_username = (me.username or "").strip()
    if not bot_username:
        raise RuntimeError("無法取得 bot username（bot.get_me() 回傳空 username）")

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    asyncio.create_task(poll_unpublished_posts(bot, settings, bot_username))
    asyncio.create_task(periodic_cleanup(settings.signal_ttl_seconds))
    asyncio.create_task(periodic_refresh_exchange_info(settings))

    logger.info("Bot polling started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

