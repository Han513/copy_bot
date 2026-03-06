from __future__ import annotations

from typing import Any, Optional

import aiohttp

from src.loguru_logger import logger


async def fetch_binding_status(
    status_url: str,
    headers: dict[str, str],
    tg_user_id: str,
    third_type: str,
    brand: str,
) -> tuple[bool, Optional[str], Optional[str]]:
    """
    呼叫「是否已綁定」API。

    回傳 (is_bound, platform_user_id, verify_url)

    目前對接 BYDFi 綁定查詢：
    - POST
    - Params: thirdId / type / brand（注意不是 Body）
    - 未綁定：{ "code": 500, "message": "No user!" }
    - 已綁定：{ "code": 200, "message": "success", "data": { "uid": "...", "thirdId": "...", "type": "telegram" } }
    """
    tg_user_id = str(tg_user_id).strip()
    if not tg_user_id:
        return False, None, None

    url = str(status_url).strip()
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    try:
        async with aiohttp.ClientSession() as session:
            params = {"thirdId": tg_user_id, "type": str(third_type), "brand": str(brand)}
            async with session.post(url, headers=headers, params=params) as resp:
                http_status = int(resp.status)
                # 這個後端可能用 HTTP 500 回應「No user」；所以 200/500 都嘗試解析 JSON
                try:
                    data: Any = await resp.json()
                except Exception as e:  # noqa: BLE001
                    logger.error(f"bind status api invalid json, status={http_status} err={e}")
                    return False, None, None
                if http_status not in (200, 500):
                    logger.error(f"bind status api unexpected http_status={http_status} body={data}")
                    return False, None, None

        if not isinstance(data, dict):
            return False, None, None
        code = data.get("code")
        msg = str(data.get("message") or "")
        if code == 200:
            payload = data.get("data") or {}
            if isinstance(payload, dict):
                uid = payload.get("uid")
                if uid:
                    return True, str(uid), None
            logger.error(f"bind status api missing uid: {data}")
            return False, None, None
        if code == 500 and "No user" in msg:
            return False, None, None
        # 其他狀況保守視為未綁定，但記錄便於排查
        logger.error(f"bind status api unexpected response: {data}")
        return False, None, None
    except Exception as e:  # noqa: BLE001
        logger.error(f"bind status api exception: {e}")
        return False, None, None

