import argparse
import asyncio
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.config import load_settings
from src.db_handler_aio import init_db, init_storage, save_announced_post
from src.loguru_logger import logger
from src.backend_posts import format_channel_post_text


def _now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _mk_kb(button: InlineKeyboardButton) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


async def publish_fake_post(title: str, summary: str) -> None:
    settings = load_settings()

    init_storage(settings.database_url)
    await init_db()

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    me = await bot.get_me()
    bot_username = (me.username or "").strip()
    if not bot_username:
        raise RuntimeError("無法取得 bot username（bot.get_me() 回傳空 username）")

    post_id = f"test_{_now_tag()}"
    payload = {
        "id": post_id,
        "title": title,
        "summary": summary,
        # 原型图字段（方便你本地端直接看卡片效果）
        "symbol": "BTCUSDT",
        "direction": "long",
        "entry_price": 84200,
        "tp_price": 88000,
        "sl_price": 80000,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_test": True,
    }

    deep_link = f"https://t.me/{bot_username}?start=copy_{post_id}"
    kb = _mk_kb(InlineKeyboardButton(text="一鍵跟單", url=deep_link))

    text = format_channel_post_text(payload)
    msg = await bot.send_message(
        chat_id=settings.public_channel_id,
        text=text,
        reply_markup=kb,
        disable_web_page_preview=True,
    )

    await save_announced_post(post_id=post_id, payload=payload, channel_message_id=msg.message_id)

    logger.info(f"已發送測試信號到頻道，post_id={post_id} message_id={msg.message_id}")
    print("=== 測試信號已發佈 ===")
    print(f"post_id: {post_id}")
    print(f"deep link: {deep_link}")
    print("接下來請到公開頻道點擊「一鍵跟單」，並在私訊中完成流程。")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="發送假文案到頻道（測試一鍵跟單流程）")
    p.add_argument("--title", default="測試文案：BTC 方向信號", help="假文章標題")
    p.add_argument("--summary", default="這是一則本地測試信號，用於驗證一鍵跟單私訊流程。", help="假文章摘要/內容")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(publish_fake_post(title=args.title, summary=args.summary))


if __name__ == "__main__":
    main()

