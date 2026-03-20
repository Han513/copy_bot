from __future__ import annotations

from typing import Any, Optional

import aiohttp

from src.loguru_logger import logger


def _normalize_base_url(base_url: str) -> str:
    url = str(base_url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    return url.rstrip("/")


def build_platform_url(base_url: str, path: str) -> str:
    base = _normalize_base_url(base_url)
    p = (path or "").strip()
    if not p.startswith("/"):
        p = "/" + p
    return base + p

async def fetch_exchange_info(
    base_url: str,
    headers: dict[str, str],
    brand: str,
) -> Optional[list[dict[str, Any]]]:
    """
    市场交易对信息：
    - POST /market/exchange_info
    - Params: brand
    回傳 data list；若錯誤回傳 None。
    """
    url = build_platform_url(base_url, "/market/exchange_info")
    try:
        async with aiohttp.ClientSession() as session:
            params = {"brand": str(brand)}
            async with session.post(url, headers=headers, params=params) as resp:
                http_status = int(resp.status)
                data: Any = await resp.json()
                if http_status != 200:
                    logger.error(f"market/exchange_info http_status={http_status} body={data}")
                    return None
        if not isinstance(data, dict):
            return None
        code = data.get("code")
        if code != 200:
            logger.error(f"market/exchange_info code!=200: {code} msg={data.get('message')} body={data}")
            return None
        items = data.get("data")
        if isinstance(items, list):
            out: list[dict[str, Any]] = []
            for x in items:
                if isinstance(x, dict):
                    out.append(x)
            return out
        logger.error(f"market/exchange_info malformed data field: {items!r} body={data}")
        return []
    except Exception as e:  # noqa: BLE001
        logger.error(f"market/exchange_info exception: {e}")
        return None


async def set_trade_leverage(
    base_url: str,
    headers: dict[str, str],
    uid: str,
    wallet: str,
    symbol: str,
    leverage: int,
    brand: str,
) -> tuple[bool, Optional[dict[str, Any]], Optional[str]]:
    """
    設定杠杆：
    - POST /trade/leverage
    - Params: uid / wallet / symbol / leverage / brand
    回傳 (ok, response_json, error_message)
    """
    uid = str(uid).strip()
    sym = str(symbol or "").strip().upper()
    if not uid:
        return False, None, "missing uid"
    if not sym:
        return False, None, "missing symbol"
    url = build_platform_url(base_url, "/trade/leverage")
    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "uid": uid,
                "wallet": str(wallet),
                "symbol": sym,
                "leverage": int(leverage),
                "brand": str(brand),
            }
            async with session.post(url, headers=headers, params=params) as resp:
                http_status = int(resp.status)
                data: Any = await resp.json()
                if http_status != 200:
                    logger.error(f"trade/leverage http_status={http_status} body={data}")
                    return False, (data if isinstance(data, dict) else None), f"http_status={http_status}"
        if not isinstance(data, dict):
            return False, None, "invalid json"
        code = data.get("code")
        if code not in (200, "200"):
            logger.error(f"trade/leverage code!=200: {code} msg={data.get('message')} body={data}")
            return False, data, str(data.get("message") or f"code={code}")
        return True, data, None
    except Exception as e:  # noqa: BLE001
        logger.error(f"trade/leverage exception: {e}")
        return False, None, str(e)


async def place_trade_order(
    base_url: str,
    headers: dict[str, str],
    uid: str,
    wallet: str,
    brand: str,
    body: dict[str, Any],
) -> tuple[bool, Optional[dict[str, Any]], Optional[str]]:
    """
    下委託單（主單 + subOrders 止盈止損）：
    - POST /trade/order
    - Query params: uid / wallet / brand
    - JSON body: 主單欄位 + subOrders（otoco 子單陣列）
    回傳 (ok, response_json, error_message)
    """
    uid = str(uid).strip()
    if not uid:
        return False, None, "missing uid"
    url = build_platform_url(base_url, "/trade/order")
    try:
        async with aiohttp.ClientSession() as session:
            params = {"uid": uid, "wallet": str(wallet), "brand": str(brand)}
            async with session.post(
                url,
                headers={**headers, "Content-Type": "application/json"},
                params=params,
                json=body,
            ) as resp:
                http_status = int(resp.status)
                data: Any = await resp.json()
                if http_status != 200:
                    logger.error(f"trade/order http_status={http_status} body={data}")
                    return False, (data if isinstance(data, dict) else None), f"http_status={http_status}"
        if not isinstance(data, dict):
            return False, None, "invalid json"
        code = data.get("code")
        if code not in (200, "200"):
            logger.error(f"trade/order code!=200: {code} msg={data.get('message')} request_body={body} response={data}")
            return False, data, str(data.get("message") or f"code={code}")
        return True, data, None
    except Exception as e:  # noqa: BLE001
        logger.error(f"trade/order exception: {e}")
        return False, None, str(e)


async def fetch_open_orders(
    base_url: str,
    headers: dict[str, str],
    uid: str,
    wallet: str,
    brand: str,
    body: Optional[dict[str, Any]] = None,
) -> Optional[list[dict[str, Any]]]:
    """
    查询当前委托：
    - POST /trade/openOrder
    - Query params: uid / wallet / brand
    - JSON body: { orderId?, clientOrderId?, symbol? }（可空）
    回傳 data list；若錯誤回傳 None。
    """
    uid = str(uid).strip()
    if not uid:
        return None
    url = build_platform_url(base_url, "/trade/openOrder")
    try:
        async with aiohttp.ClientSession() as session:
            params = {"uid": uid, "wallet": str(wallet), "brand": str(brand)}
            async with session.post(
                url,
                headers={**headers, "Content-Type": "application/json"},
                params=params,
                json=(body or {}),
            ) as resp:
                http_status = int(resp.status)
                data: Any = await resp.json()
                if http_status != 200:
                    logger.error(f"trade/openOrder http_status={http_status} body={data}")
                    return None
        if not isinstance(data, dict):
            return None
        code = data.get("code")
        if code != 200:
            logger.error(f"trade/openOrder code!=200: {code} msg={data.get('message')} body={data}")
            return None
        items = data.get("data")
        if isinstance(items, list):
            out: list[dict[str, Any]] = []
            for x in items:
                if isinstance(x, dict):
                    out.append(x)
            return out
        logger.error(f"trade/openOrder malformed data field: {items!r} body={data}")
        return []
    except Exception as e:  # noqa: BLE001
        logger.error(f"trade/openOrder exception: {e}")
        return None


async def fetch_positions(
    base_url: str,
    headers: dict[str, str],
    *,
    contract_type: int,
    uid: str,
    wallet: str,
    brand: str,
    symbol: Optional[str] = None,
    settle_coin: Optional[str] = None,
) -> Optional[list[dict[str, Any]]]:
    """
    查询当前持仓：
    - POST /trade/positions
    - Query params: contractType / uid / wallet / brand
    - JSON body: { symbol?, settleCoin? }（可空）
    回傳 data list；若錯誤回傳 None。
    """
    uid = str(uid).strip()
    if not uid:
        return None
    url = build_platform_url(base_url, "/trade/positions")
    body: dict[str, Any] = {}
    if symbol:
        body["symbol"] = str(symbol).strip()
    if settle_coin:
        body["settleCoin"] = str(settle_coin).strip()
    try:
        async with aiohttp.ClientSession() as session:
            params = {"contractType": int(contract_type), "uid": uid, "wallet": str(wallet).strip(), "brand": str(brand)}
            async with session.post(
                url,
                headers={**headers, "Content-Type": "application/json"},
                params=params,
                json=body,
            ) as resp:
                http_status = int(resp.status)
                data: Any = await resp.json()
                if http_status != 200:
                    logger.error(f"trade/positions http_status={http_status} body={data}")
                    return None
        if not isinstance(data, dict):
            return None
        code = data.get("code")
        if code != 200:
            logger.error(f"trade/positions code!=200: {code} msg={data.get('message')} body={data}")
            return None
        items = data.get("data")
        if isinstance(items, list):
            out: list[dict[str, Any]] = []
            for x in items:
                if isinstance(x, dict):
                    out.append(x)
            return out
        logger.error(f"trade/positions malformed data field: {items!r} body={data}")
        return []
    except Exception as e:  # noqa: BLE001
        logger.error(f"trade/positions exception: {e}")
        return None


async def fetch_plan_orders(
    base_url: str,
    headers: dict[str, str],
    uid: str,
    wallet: str,
    brand: str,
    body: Optional[dict[str, Any]] = None,
) -> Optional[list[dict[str, Any]]]:
    """
    查询计划委托：
    - POST /trade/planOrder
    - Query params: uid / wallet / brand
    - JSON body: 必須傳遞（後端要求空對象 {} 才會成功響應）；可選 {"symbol": "..."} 篩選
    回傳 data list；若錯誤回傳 None。
    """
    uid = str(uid).strip()
    if not uid:
        return None
    url = build_platform_url(base_url, "/trade/planOrder")
    payload: dict[str, Any] = {} if not body else dict(body)
    try:
        async with aiohttp.ClientSession() as session:
            params = {"uid": uid, "wallet": str(wallet), "brand": str(brand)}
            async with session.post(
                url,
                headers={**headers, "Content-Type": "application/json"},
                params=params,
                json=payload,
            ) as resp:
                http_status = int(resp.status)
                data: Any = await resp.json()
                if http_status != 200:
                    logger.error(f"trade/planOrder http_status={http_status} body={data}")
                    return None
        if not isinstance(data, dict):
            return None
        code = data.get("code")
        if code != 200:
            logger.error(f"trade/planOrder code!=200: {code} msg={data.get('message')} body={data}")
            return None
        items = data.get("data")
        if isinstance(items, list):
            out: list[dict[str, Any]] = []
            for x in items:
                if isinstance(x, dict):
                    out.append(x)
            return out
        logger.error(f"trade/planOrder malformed data field: {items!r} body={data}")
        return []
    except Exception as e:  # noqa: BLE001
        logger.error(f"trade/planOrder exception: {e}")
        return None


async def fetch_trade_leverage(
    base_url: str,
    headers: dict[str, str],
    uid: str,
    wallet: str,
    symbol: str,
    brand: str,
) -> tuple[bool, Optional[dict[str, Any]], Optional[str]]:
    """
    查询杠杆：
    - POST /trade/getLeverage
    - Params: uid / wallet / symbol / brand
    回傳 (ok, response_json, error_message)
    """
    uid = str(uid).strip()
    sym = str(symbol or "").strip().upper()
    if not uid:
        return False, None, "missing uid"
    if not sym:
        return False, None, "missing symbol"
    url = build_platform_url(base_url, "/trade/getLeverage")
    try:
        async with aiohttp.ClientSession() as session:
            params = {"uid": uid, "wallet": str(wallet), "symbol": sym, "brand": str(brand)}
            async with session.post(url, headers=headers, params=params) as resp:
                http_status = int(resp.status)
                data: Any = await resp.json()
                if http_status != 200:
                    logger.error(f"trade/getLeverage http_status={http_status} body={data}")
                    return False, (data if isinstance(data, dict) else None), f"http_status={http_status}"
        if not isinstance(data, dict):
            return False, None, "invalid json"
        code = data.get("code")
        if code not in (200, "200"):
            logger.error(f"trade/getLeverage code!=200: {code} msg={data.get('message')} body={data}")
            return False, data, str(data.get("message") or f"code={code}")
        return True, data, None
    except Exception as e:  # noqa: BLE001
        logger.error(f"trade/getLeverage exception: {e}")
        return False, None, str(e)


async def cancel_order(
    base_url: str,
    headers: dict[str, str],
    cancel_path: str,
    uid: str,
    wallet: str,
    brand: str,
    order_id: int,
    symbol: Optional[str] = None,
    client_order_id: Optional[str] = None,
) -> tuple[bool, Optional[dict[str, Any]], Optional[str]]:
    """
    撤單（路徑可配置，預設 /trade/batch_cancel_orders）：
    - POST <cancel_path>
    - Query params: uid / wallet / brand
    - JSON body: { orderIds?: [...], clientOrderIds?: [...], symbol? }
    回傳 (ok, response_json, error_message)
    """
    return await batch_cancel_orders(
        base_url=base_url,
        headers=headers,
        cancel_path=cancel_path,
        uid=uid,
        wallet=wallet,
        brand=brand,
        order_ids=[int(order_id)],
        client_order_ids=[str(client_order_id)] if client_order_id else None,
        symbol=symbol,
    )


async def batch_cancel_orders(
    base_url: str,
    headers: dict[str, str],
    cancel_path: str,
    uid: str,
    wallet: str,
    brand: str,
    order_ids: Optional[list[int]] = None,
    client_order_ids: Optional[list[str]] = None,
    symbol: Optional[str] = None,
) -> tuple[bool, Optional[dict[str, Any]], Optional[str]]:
    """
    批量撤單（接口：/trade/batch_cancel_orders）：
    - POST <cancel_path>
    - Query params: uid / wallet / brand
    - JSON body: { orderIds?: [...], clientOrderIds?: [...], symbol? }
      orderIds 或 clientOrderIds 必填其一
    回傳 (ok, response_json, error_message)
    """
    uid = str(uid).strip()
    if not uid:
        return False, None, "missing uid"

    ids: list[int] = []
    if order_ids:
        for x in order_ids:
            try:
                ids.append(int(x))
            except Exception:
                continue

    cids: list[str] = []
    if client_order_ids:
        for x in client_order_ids:
            s = str(x).strip()
            if s:
                cids.append(s)

    if not ids and not cids:
        return False, None, "missing orderIds/clientOrderIds"

    url = build_platform_url(base_url, cancel_path)
    body: dict[str, Any] = {}
    if ids:
        body["orderIds"] = ids
    if cids:
        body["clientOrderIds"] = cids
    if symbol:
        body["symbol"] = str(symbol)

    try:
        async with aiohttp.ClientSession() as session:
            params = {"uid": uid, "wallet": str(wallet), "brand": str(brand)}
            async with session.post(
                url,
                headers={**headers, "Content-Type": "application/json"},
                params=params,
                json=body,
            ) as resp:
                http_status = int(resp.status)
                data: Any = await resp.json()
                if http_status != 200:
                    logger.error(f"batch cancel orders http_status={http_status} body={data}")
                    return False, (data if isinstance(data, dict) else None), f"http_status={http_status}"
        if not isinstance(data, dict):
            return False, None, "invalid json"
        code = data.get("code")
        if code != 200:
            logger.error(f"batch cancel orders code!=200: {code} msg={data.get('message')} body={data}")
            return False, data, str(data.get("message") or f"code={code}")
        return True, data, None
    except Exception as e:  # noqa: BLE001
        logger.error(f"batch cancel orders exception: {e}")
        return False, None, str(e)

async def fetch_account_balance(
    base_url: str,
    headers: dict[str, str],
    uid: str,
    wallet: str,
    brand: str,
) -> Optional[list[dict[str, Any]]]:
    """
    BYDFi 餘額查詢：
    - POST
    - Params: uid / wallet / brand（不是 body）
    回傳 data list；若錯誤回傳 None。
    """
    uid = str(uid).strip()
    if not uid:
        return None
    url = build_platform_url(base_url, "/account/balance")
    try:
        async with aiohttp.ClientSession() as session:
            params = {"uid": uid, "wallet": str(wallet), "brand": str(brand)}
            async with session.post(url, headers=headers, params=params) as resp:
                http_status = int(resp.status)
                data: Any = await resp.json()
                if http_status != 200:
                    logger.error(f"account/balance http_status={http_status} body={data}")
                    return None
        if not isinstance(data, dict):
            return None
        code = data.get("code")
        if code != 200:
            logger.error(f"account/balance code!=200: {code} msg={data.get('message')} body={data}")
            return None
        items = data.get("data")
        if isinstance(items, list):
            out: list[dict[str, Any]] = []
            for x in items:
                if isinstance(x, dict):
                    out.append(x)
            if not out:
                # 成功但沒有任何資產資料：視為 0（但保留一筆 info 便於排查）
                logger.info(f"account/balance success but empty data uid={uid} wallet={wallet} brand={brand}")
            return out
        # 成功但 data 欄位不是 list：記錄，並保守回傳空 list 讓上層顯示 0
        logger.error(f"account/balance malformed data field: {items!r} body={data}")
        return []
    except Exception as e:  # noqa: BLE001
        logger.error(f"account/balance exception: {e}")
        return None


def pick_available_balance_usdt(items: list[dict[str, Any]]) -> Optional[float]:
    """
    從 account/balance 的 data list 挑出 USDT 的 availableBalance。
    """
    for it in items:
        if str(it.get("currency") or "").upper() != "USDT":
            continue
        raw = it.get("availableBalance")
        if raw is None:
            return 0.0
        try:
            return float(str(raw))
        except Exception:
            return 0.0
    # 沒有 USDT 項目視為 0
    return 0.0

