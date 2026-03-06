import time
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from dataclasses import dataclass
from typing import Any, Optional

from src.backend_posts import extract_signal_fields
from src.platform_api import place_trade_order
from src.loguru_logger import logger
from src.platform_errors import platform_error_text


@dataclass(frozen=True)
class PlaceOrderAck:
    ok: bool
    request_id: Optional[str] = None
    error: Optional[str] = None
    response_data: Optional[dict[str, Any]] = None


def _norm_symbol(symbol: str) -> str:
    s = str(symbol or "").strip().upper()
    tokens: list[str] = []
    cur = ""
    for ch in s:
        if ch.isalnum():
            cur += ch
        else:
            if cur:
                tokens.append(cur)
                cur = ""
    if cur:
        tokens.append(cur)

    if len(tokens) >= 2:
        return f"{tokens[0]}-{tokens[-1]}"

    known_quotes = ("USDT", "USDC", "USD")
    for q in known_quotes:
        if s.endswith(q) and len(s) > len(q):
            return f"{s[:-len(q)]}-{q}"
    return s


def _to_decimal(v: Any) -> Optional[Decimal]:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


def _fmt_qty(v: Decimal, max_dp: int = 8) -> str:
    q = Decimal(10) ** (-max_dp)
    return str(v.quantize(q, rounding=ROUND_DOWN).normalize())

def _fmt_contracts(v: Decimal) -> str:
    return str(v.to_integral_value(rounding=ROUND_DOWN))


def _map_direction(direction: Any) -> tuple[str, str]:
    d = str(direction or "").strip().lower()
    if d in {"多", "long", "buy", "up"}:
        return "BUY", "LONG"
    if d in {"空", "short", "sell", "down"}:
        return "SELL", "SHORT"
    return "BUY", "LONG"


async def place_order_async(
    signal: dict[str, Any],
    amount: float,
    leverage: int,
    *,
    lang: str,
    platform_uid: str,
    base_url: str,
    headers: dict[str, str],
    wallet: str,
    brand: str,
    fee_rate_taker: Any = None,
    contract_factor: Any = None,
    best_bid_price: Any = None,
) -> PlaceOrderAck:
    """
    下單接口（異步）：
    - 先下主委託單（LIMIT / MARKET）
    - 若 signal 有 TP/SL，則補下條件單（TAKE_PROFIT_MARKET / STOP_MARKET）
    """
    f = extract_signal_fields(signal if isinstance(signal, dict) else {})
    symbol = _norm_symbol(str(f.get("symbol") or signal.get("symbol") or ""))
    side, position_side = _map_direction(f.get("direction"))
    entry = _to_decimal(f.get("entry"))
    tp = _to_decimal(f.get("tp"))
    sl = _to_decimal(f.get("sl"))

    if not symbol:
        return PlaceOrderAck(ok=False, error="missing symbol")

    amt = _to_decimal(amount)
    lev = _to_decimal(leverage)
    if amt is None or lev is None:
        return PlaceOrderAck(ok=False, error="invalid amount/leverage")
    if entry is None or entry <= 0:
        return PlaceOrderAck(ok=False, error="missing entry price (cannot compute quantity)")

    fee = _to_decimal(fee_rate_taker)
    cf = _to_decimal(contract_factor)
    if fee is None or cf is None or cf <= 0:
        return PlaceOrderAck(ok=False, error="missing market info (fee_rate_taker/contract_factor)")
    if lev <= 0:
        return PlaceOrderAck(ok=False, error="invalid leverage")
    imr = Decimal(1) / lev
    denom = imr + fee
    if denom <= 0:
        return PlaceOrderAck(ok=False, error="invalid (imr+fee)")
    ref_price = entry
    bid1 = _to_decimal(best_bid_price)
    if bid1 is not None and bid1 > 0:
        ref_price = max(entry, bid1)
    contracts = amt / denom / cf / ref_price
    if contracts <= 0:
        return PlaceOrderAck(ok=False, error="quantity <= 0")
    contracts_int = contracts.to_integral_value(rounding=ROUND_DOWN)
    if contracts_int <= 0:
        return PlaceOrderAck(ok=False, error="quantity < 1")

    client_order_id = f"tg_{int(time.time())}_{symbol}_{side}"
    source = "10"

    main_order: dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "positionSide": position_side,
        "type": "LIMIT",
        "price": str(entry),
        "quantity": _fmt_contracts(contracts_int),
        "clientOrderId": f"{client_order_id}_main",
        "source": source,
    }

    opp_side = "SELL" if side == "BUY" else "BUY"
    opp_position_side = "SHORT" if position_side == "LONG" else "LONG"
    sub_orders: list[dict[str, Any]] = []
    if tp is not None and tp > 0:
        sub_orders.append(
            {
                "symbol": symbol,
                "side": opp_side,
                "positionSide": opp_position_side,
                "type": "TAKE_PROFIT_MARKET",
                "clientOrderId": f"{client_order_id}_tp",
                "stopPrice": float(tp),
                "workingType": "MARK_PRICE",
                "source": source,
            }
        )
    if sl is not None and sl > 0:
        sub_orders.append(
            {
                "symbol": symbol,
                "side": opp_side,
                "positionSide": opp_position_side,
                "type": "STOP_MARKET",
                "clientOrderId": f"{client_order_id}_sl",
                "stopPrice": float(sl),
                "workingType": "MARK_PRICE",
                "source": source,
            }
        )

    body: dict[str, Any] = {**main_order}
    if sub_orders:
        body["subOrders"] = sub_orders

    ok, resp_json, err = await place_trade_order(
        base_url=base_url,
        headers=headers,
        uid=str(platform_uid),
        wallet=str(wallet),
        brand=str(brand),
        body=body,
    )
    if not ok:
        logger.error(f"place main order failed: err={err} resp={resp_json}")
        return PlaceOrderAck(ok=False, error=platform_error_text(lang, resp_json, err))

    data = isinstance(resp_json, dict) and resp_json.get("data") or {}
    return PlaceOrderAck(
        ok=True,
        request_id=client_order_id,
        error=None,
        response_data=data if isinstance(data, dict) else {},
    )


