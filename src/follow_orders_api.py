from __future__ import annotations

from typing import Any, Optional

import aiohttp

from src.loguru_logger import logger


async def fetch_follow_order_view(
    view_url: str,
    headers: dict[str, str],
    follow_order_id: int,
) -> Optional[dict[str, Any]]:
    """
    呼叫 /bot/follow_orders/view?id=xxx 取得帶單信號詳情。

    期待回傳格式：
    {
      "code": 0,
      "data": { "item": { ... } },
      "message": "Success"
    }
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(view_url, headers=headers, params={"id": int(follow_order_id)}) as resp:
                if resp.status != 200:
                    logger.error(f"follow_orders/view 失败，status={resp.status}")
                    return None
                data: Any = await resp.json()
                if not isinstance(data, dict):
                    return None
                if data.get("code") != 0:
                    logger.error(f"follow_orders/view code!=0: {data.get('code')} msg={data.get('message')}")
                    return None
                item = (data.get("data") or {}).get("item")
                if isinstance(item, dict):
                    return item
                return None
    except Exception as e:  # noqa: BLE001
        logger.error(f"调用 follow_orders/view 失败: {e}")
        return None

