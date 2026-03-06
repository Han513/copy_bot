from __future__ import annotations

from typing import Any, Optional

import aiohttp

from src.loguru_logger import logger


def _norm_direction(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip().lower()
    if not s:
        return None
    if s in {"long", "buy", "up", "bull", "多", "做多"}:
        return "多"
    if s in {"short", "sell", "down", "bear", "空", "做空"}:
        return "空"
    return str(v).strip()


def _pick_first(item: dict[str, Any], keys: tuple[str, ...]) -> Optional[Any]:
    for k in keys:
        if k in item and item.get(k) not in (None, ""):
            return item.get(k)
    return None


def extract_signal_fields(item: dict[str, Any]) -> dict[str, Any]:
    symbol = _pick_first(item, ("symbol", "pair", "trading_pair", "name"))
    direction = _norm_direction(_pick_first(item, ("direction", "side", "trend")))
    # follow_orders/view: order_price / take_profit_price / stop_loss_price
    entry = _pick_first(item, ("entry", "entry_price", "entryPrice", "open_price", "price", "order_price"))
    tp = _pick_first(item, ("tp", "take_profit", "takeProfit", "tp_price", "take_profit_price"))
    sl = _pick_first(item, ("sl", "stop_loss", "stopLoss", "sl_price", "stop_loss_price"))
    return {
        "symbol": str(symbol).strip() if symbol else None,
        "direction": direction,
        "entry": entry,
        "tp": tp,
        "sl": sl,
    }


def extract_image_url(item: dict[str, Any]) -> Optional[str]:
    v = _pick_first(item, ("image_url", "imageUrl", "cover", "pic", "image", "banner"))
    if not v:
        return None
    s = str(v).strip()
    if not s:
        return None
    # 只做最基本的判斷，避免把非 URL 當成 photo
    if s.startswith("http://") or s.startswith("https://"):
        return s
    return None


async def fetch_unpublished_posts(posts_url: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    """
    调用 /posts/list 接口，检查未发布的文章
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(posts_url, headers=headers) as response:
                if response.status == 200:
                    posts_data = await response.json()
                    items = posts_data.get("data", {}).get("items", [])
                    if isinstance(items, list):
                        return [x for x in items if isinstance(x, dict)]
                    return []
                else:
                    logger.error(f"获取文章列表失败，状态码: {response.status}")
                    return []
    except Exception as e:  # noqa: BLE001
        logger.error(f"调用 /posts/list 接口失败: {e}")
        return []


def extract_post_id(item: dict[str, Any]) -> Optional[str]:
    """
    從後端 item 盡可能抽出唯一 ID。你後端欄位名若不同，這裡再補上即可。
    """
    for key in ("id", "post_id", "postId", "uuid", "_id"):
        v = item.get(key)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return None


def format_channel_post_text(item: dict[str, Any]) -> str:
    """
    公開頻道訊息內容（可依你後端字段再美化）。
    """
    f = extract_signal_fields(item)
    title = (item.get("title") or item.get("name") or item.get("symbol") or "").strip()

    # 原型圖風格：卡片化字段
    lines: list[str] = []
    lines.append(f"【{title or '交易信号'}】")
    if f.get("symbol"):
        lines.append(f"交易对：{f['symbol']}")
    if f.get("direction"):
        lines.append(f"方向：{f['direction']}")
    if f.get("entry") is not None:
        lines.append(f"进场价格：{f['entry']}")
    if f.get("tp") is not None:
        lines.append(f"止盈价格：{f['tp']}")
    if f.get("sl") is not None:
        lines.append(f"止损价格：{f['sl']}")

    summary = (item.get("summary") or item.get("content") or item.get("text") or "").strip()
    if summary:
        if len(summary) > 300:
            summary = summary[:300] + "…"
        lines.append("")
        lines.append(summary)

    lines.append("")
    lines.append("点击下方「一键跟单」，跳转私讯完成下单。")
    return "\n".join(lines)

