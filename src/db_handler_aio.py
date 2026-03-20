import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, Text, delete, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.loguru_logger import logger


class Base(DeclarativeBase):
    pass


class AnnouncedPost(Base):
    __tablename__ = "announced_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    announced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    channel_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class UserBalance(Base):
    __tablename__ = "user_balances"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserSetting(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserBinding(Base):
    __tablename__ = "user_bindings"

    tg_user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    platform_user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_bound: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0/1
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CopyOrder(Base):
    __tablename__ = "copy_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    post_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    leverage: Mapped[int] = mapped_column(Integer, nullable=False)
    # 除錯用：儲存使用者下單參數快照（JSON 字串）
    params_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")  # pending/submitted/cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ContractInfo(Base):
    __tablename__ = "contract_infos"

    symbol: Mapped[str] = mapped_column(String(64), primary_key=True)
    alias: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    base_symbol: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    settle_coin: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    price_symbol: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    contract_type: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    contract_factor: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    max_delegate_num: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_delegate_num: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_market_delegate_num: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_market_delegate_num: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price_precision: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    base_precision: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 價格展示用小數位數，來自 exchange_info.baseShowPrecision
    fee_rate_taker: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    fee_rate_maker: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    leverage_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # exchange_info.onlineTime 是毫秒時間戳（13 位），需要 BIGINT
    online_time: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # ms
    status: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)


def _json_loads(raw: str) -> Any:
    return json.loads(raw)


engine: Optional[AsyncEngine] = None
Session: Optional[async_sessionmaker] = None


def init_storage(database_url: str) -> None:
    """
    由主程式在啟動時呼叫，避免 import 階段就強制要求 .env 完整。
    """
    global engine, Session
    engine = create_async_engine(database_url, echo=False, future=True)
    Session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    if engine is None:
        raise RuntimeError("storage 尚未初始化：請先呼叫 init_storage(database_url)")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 兼容舊版資料表：online_time 若是 int4 會爆 (value out of int32 range)
        try:
            if getattr(conn.dialect, "name", "") in {"postgresql", "postgres"}:
                await conn.execute(
                    text(
                        "ALTER TABLE contract_infos "
                        "ALTER COLUMN online_time TYPE BIGINT "
                        "USING online_time::bigint"
                    )
                )
        except Exception as e:  # noqa: BLE001
            # 若欄位已是 BIGINT / 表不存在 / 權限不足，忽略並記錄
            logger.warning(f"DB migrate contract_infos.online_time skipped: {e}")

        # 兼容舊版資料表：contract_infos 補 base_precision（價格展示精度）
        try:
            name = getattr(conn.dialect, "name", "")
            if name in {"postgresql", "postgres"}:
                await conn.execute(text("ALTER TABLE contract_infos ADD COLUMN IF NOT EXISTS base_precision INTEGER"))
            elif name == "sqlite":
                await conn.execute(text("ALTER TABLE contract_infos ADD COLUMN base_precision INTEGER"))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"DB migrate contract_infos.base_precision skipped: {e}")

        # 兼容舊版資料表：copy_orders 補 params_json 欄位（存下單參數快照）
        try:
            name = getattr(conn.dialect, "name", "")
            if name in {"postgresql", "postgres"}:
                await conn.execute(text("ALTER TABLE copy_orders ADD COLUMN IF NOT EXISTS params_json TEXT"))
            elif name == "sqlite":
                # sqlite 舊版不一定支援 IF NOT EXISTS；用 try/except 忽略重覆添加
                await conn.execute(text("ALTER TABLE copy_orders ADD COLUMN params_json TEXT"))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"DB migrate copy_orders.params_json skipped: {e}")
    logger.info("DB initialized")


async def is_post_announced(post_id: str) -> bool:
    if Session is None:
        raise RuntimeError("storage 尚未初始化：請先呼叫 init_storage(database_url)")
    async with Session() as session:
        result = await session.execute(select(AnnouncedPost.post_id).where(AnnouncedPost.post_id == post_id))
        return result.scalar_one_or_none() is not None


async def save_announced_post(post_id: str, payload: Any, channel_message_id: Optional[int] = None) -> None:
    if Session is None:
        raise RuntimeError("storage 尚未初始化：請先呼叫 init_storage(database_url)")
    async with Session() as session:
        async with session.begin():
            ap = AnnouncedPost(
                post_id=post_id,
                payload_json=_json_dumps(payload),
                announced_at=_now_utc(),
                channel_message_id=channel_message_id,
            )
            session.add(ap)


async def get_announced_post_payload(post_id: str) -> Optional[Any]:
    if Session is None:
        raise RuntimeError("storage 尚未初始化：請先呼叫 init_storage(database_url)")
    async with Session() as session:
        result = await session.execute(select(AnnouncedPost).where(AnnouncedPost.post_id == post_id))
        row = result.scalars().first()
        if not row:
            return None
        try:
            return _json_loads(row.payload_json)
        except Exception:
            return None


async def get_announced_post(post_id: str) -> Optional[tuple[Any, datetime]]:
    """
    取得信號 payload 與 announced_at（用於有效期檢查）。
    """
    if Session is None:
        raise RuntimeError("storage 尚未初始化：請先呼叫 init_storage(database_url)")
    async with Session() as session:
        result = await session.execute(select(AnnouncedPost).where(AnnouncedPost.post_id == post_id))
        row = result.scalars().first()
        if not row:
            return None
        try:
            payload = _json_loads(row.payload_json)
        except Exception:
            payload = None
        return payload, row.announced_at


async def delete_expired_announced_posts(max_age_seconds: int) -> int:
    """
    刪除超過有效期的信號資料（只刪 announced_posts，不動 copy_orders）。
    回傳刪除筆數（不同 DB driver 可能回傳 0 但仍成功執行）。
    """
    if Session is None:
        raise RuntimeError("storage 尚未初始化：請先呼叫 init_storage(database_url)")
    cutoff = _now_utc()
    cutoff = cutoff.replace(microsecond=0)  # 避免某些 DB 比較時的精度問題
    cutoff = cutoff - timedelta(seconds=int(max_age_seconds))  # type: ignore[name-defined]
    async with Session() as session:
        async with session.begin():
            res = await session.execute(delete(AnnouncedPost).where(AnnouncedPost.announced_at < cutoff))
            try:
                return int(res.rowcount or 0)
            except Exception:
                return 0


async def get_balance(user_id: str) -> float:
    if Session is None:
        raise RuntimeError("storage 尚未初始化：請先呼叫 init_storage(database_url)")
    async with Session() as session:
        result = await session.execute(select(UserBalance).where(UserBalance.user_id == user_id))
        ub = result.scalars().first()
        return float(ub.balance) if ub else 0.0


async def get_user_language(user_id: str, default: str = "en") -> str:
    if Session is None:
        raise RuntimeError("storage 尚未初始化：請先呼叫 init_storage(database_url)")
    async with Session() as session:
        result = await session.execute(select(UserSetting).where(UserSetting.user_id == user_id))
        us = result.scalars().first()
        return str(us.language) if us and us.language else default


async def set_user_language(user_id: str, language: str) -> str:
    if Session is None:
        raise RuntimeError("storage 尚未初始化：請先呼叫 init_storage(database_url)")
    language = str(language).strip()
    if not language:
        language = "en"
    async with Session() as session:
        async with session.begin():
            result = await session.execute(select(UserSetting).where(UserSetting.user_id == user_id))
            us = result.scalars().first()
            if us:
                us.language = language
                us.updated_at = _now_utc()
            else:
                session.add(UserSetting(user_id=user_id, language=language, updated_at=_now_utc()))
    return language


async def ensure_user_language(user_id: str, preferred_language: str = "en") -> str:
    """
    確保 user_settings 至少有一筆資料。
    - 若使用者已設定語言：回傳既有語言（不覆蓋）
    - 若尚未存在：以 preferred_language 建立並回傳
    """
    if Session is None:
        raise RuntimeError("storage 尚未初始化：請先呼叫 init_storage(database_url)")
    preferred_language = str(preferred_language).strip() or "en"
    async with Session() as session:
        result = await session.execute(select(UserSetting).where(UserSetting.user_id == str(user_id)))
        us = result.scalars().first()
        if us and us.language:
            return str(us.language)
    # 不存在就建立
    return await set_user_language(str(user_id), preferred_language)


async def get_user_binding(tg_user_id: str) -> Optional[UserBinding]:
    if Session is None:
        raise RuntimeError("storage 尚未初始化：請先呼叫 init_storage(database_url)")
    async with Session() as session:
        result = await session.execute(select(UserBinding).where(UserBinding.tg_user_id == str(tg_user_id)))
        return result.scalars().first()


async def upsert_user_binding(tg_user_id: str, is_bound: bool, platform_user_id: Optional[str] = None) -> None:
    if Session is None:
        raise RuntimeError("storage 尚未初始化：請先呼叫 init_storage(database_url)")
    async with Session() as session:
        async with session.begin():
            result = await session.execute(select(UserBinding).where(UserBinding.tg_user_id == str(tg_user_id)))
            row = result.scalars().first()
            if row:
                row.is_bound = 1 if is_bound else 0
                if platform_user_id is not None:
                    row.platform_user_id = str(platform_user_id)
                row.updated_at = _now_utc()
            else:
                session.add(
                    UserBinding(
                        tg_user_id=str(tg_user_id),
                        platform_user_id=str(platform_user_id) if platform_user_id is not None else None,
                        is_bound=1 if is_bound else 0,
                        updated_at=_now_utc(),
                    )
                )


async def set_balance(user_id: str, balance: float) -> float:
    balance = float(balance)
    if Session is None:
        raise RuntimeError("storage 尚未初始化：請先呼叫 init_storage(database_url)")
    async with Session() as session:
        async with session.begin():
            result = await session.execute(select(UserBalance).where(UserBalance.user_id == user_id))
            ub = result.scalars().first()
            if ub:
                ub.balance = balance
                ub.updated_at = _now_utc()
            else:
                session.add(UserBalance(user_id=user_id, balance=balance, updated_at=_now_utc()))
    return balance


async def add_balance(user_id: str, delta: float) -> float:
    current = await get_balance(user_id)
    return await set_balance(user_id, current + float(delta))


async def create_copy_order(
    user_id: str,
    post_id: str,
    amount: float,
    leverage: int,
    *,
    params: Optional[dict[str, Any]] = None,
) -> int:
    if Session is None:
        raise RuntimeError("storage 尚未初始化：請先呼叫 init_storage(database_url)")
    async with Session() as session:
        async with session.begin():
            order = CopyOrder(
                user_id=str(user_id),
                post_id=str(post_id),
                amount=float(amount),
                leverage=int(leverage),
                status="pending",
                created_at=_now_utc(),
                params_json=_json_dumps(params) if isinstance(params, dict) else None,
            )
            session.add(order)
            await session.flush()
            return int(order.id)


async def update_copy_order_status(order_id: int, status: str) -> None:
    if Session is None:
        raise RuntimeError("storage 尚未初始化：請先呼叫 init_storage(database_url)")
    async with Session() as session:
        async with session.begin():
            result = await session.execute(select(CopyOrder).where(CopyOrder.id == int(order_id)))
            order = result.scalars().first()
            if order:
                order.status = status


async def upsert_contract_infos(items: list[dict[str, Any]]) -> int:
    """
    批量寫入/更新交易對信息，回傳處理筆數。
    """
    if Session is None:
        raise RuntimeError("storage 尚未初始化：請先呼叫 init_storage(database_url)")
    n = 0
    async with Session() as session:
        async with session.begin():
            for it in items:
                if not isinstance(it, dict):
                    continue
                sym = str(it.get("symbol") or "").strip().upper()
                if not sym:
                    continue
                variants = _contract_symbol_variants(sym)
                result = await session.execute(select(ContractInfo).where(ContractInfo.symbol.in_(variants)))
                row = result.scalars().first()
                if not row:
                    row = ContractInfo(symbol=sym, updated_at=_now_utc())
                    session.add(row)
                row.alias = (str(it.get("alias")) if it.get("alias") is not None else None)
                row.base_symbol = (str(it.get("baseSymbol")) if it.get("baseSymbol") is not None else None)
                row.settle_coin = (str(it.get("settleCoin")) if it.get("settleCoin") is not None else None)
                row.price_symbol = (str(it.get("priceSymbol")) if it.get("priceSymbol") is not None else None)
                row.contract_type = (int(it.get("contractType")) if it.get("contractType") is not None else None)
                row.contract_factor = (str(it.get("contractFactor")) if it.get("contractFactor") is not None else None)
                row.max_delegate_num = (int(it.get("maxDelegateNum")) if it.get("maxDelegateNum") is not None else None)
                row.min_delegate_num = (int(it.get("minDelegateNum")) if it.get("minDelegateNum") is not None else None)
                row.max_market_delegate_num = (int(it.get("maxMarketDelegateNum")) if it.get("maxMarketDelegateNum") is not None else None)
                row.min_market_delegate_num = (int(it.get("minMarketDelegateNum")) if it.get("minMarketDelegateNum") is not None else None)
                row.price_precision = (int(it.get("pricePrecision")) if it.get("pricePrecision") is not None else None)
                row.base_precision = (int(it.get("baseShowPrecision")) if it.get("baseShowPrecision") is not None else None)
                row.fee_rate_taker = (str(it.get("feeRateTaker")) if it.get("feeRateTaker") is not None else None)
                row.fee_rate_maker = (str(it.get("feeRateMaker")) if it.get("feeRateMaker") is not None else None)
                row.leverage_level = (int(it.get("leverageLevel")) if it.get("leverageLevel") is not None else None)
                row.online_time = (int(it.get("onlineTime")) if it.get("onlineTime") is not None else None)
                row.status = (str(it.get("status")) if it.get("status") is not None else None)
                row.updated_at = _now_utc()
                n += 1
    return n


def _contract_symbol_variants(symbol: str) -> list[str]:
    """
    兼容不同 symbol 格式（例如 BTCUSDT / BTC-USDT / BTC_USDT / BTC/USDT）。
    contract_infos.symbol 可能隨 API 版本帶不帶 '-' 不一致，因此查詢/更新需同時嘗試多種變體。
    """
    raw = str(symbol or "").strip().upper()
    if not raw:
        return []
    out: list[str] = []
    def _add(v: str) -> None:
        v = str(v or "").strip().upper()
        if v and v not in out:
            out.append(v)

    _add(raw)
    dash = re.sub(r"[-_/\s]+", "-", raw).strip("-")
    _add(dash)
    compact = re.sub(r"[-_/\s]+", "", raw)
    _add(compact)
    if "-" not in dash:
        for q in ("USDT", "USDC", "USD"):
            if compact.endswith(q) and len(compact) > len(q):
                _add(f"{compact[:-len(q)]}-{q}")
                break
    return out


async def get_contract_info(symbol: str) -> Optional[ContractInfo]:
    if Session is None:
        raise RuntimeError("storage 尚未初始化：請先呼叫 init_storage(database_url)")
    sym = str(symbol or "").strip().upper()
    if not sym:
        return None
    async with Session() as session:
        variants = _contract_symbol_variants(sym)
        if not variants:
            return None
        result = await session.execute(select(ContractInfo).where(ContractInfo.symbol.in_(variants)))
        return result.scalars().first()

