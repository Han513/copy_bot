import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from dotenv import load_dotenv


load_dotenv()


def _getenv(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def _parse_headers_json(raw: Optional[str]) -> Dict[str, str]:
    if not raw:
        return {}
    try:
        data: Any = json.loads(raw)
    except Exception as e:  # noqa: BLE001 - 這裡要把錯誤訊息帶出來
        raise ValueError("HEADERS_JSON 不是合法 JSON") from e
    if not isinstance(data, dict):
        raise ValueError("HEADERS_JSON 必須是 JSON object，例如 {\"Authorization\":\"Bearer xxx\"}")
    headers: Dict[str, str] = {}
    for k, v in data.items():
        if v is None:
            continue
        headers[str(k)] = str(v)
    return headers


def _parse_bool(raw: Optional[str], default: bool = False) -> bool:
    if raw is None:
        return default
    v = str(raw).strip().lower()
    if v in {"1", "true", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "no", "n", "off"}:
        return False
    return default


@dataclass(frozen=True)
class Settings:
    # Telegram
    telegram_bot_token: str
    public_channel_id: int

    # Backend posts polling（可選）
    posts_url: Optional[str]
    posts_headers: Dict[str, str]
    poll_interval_seconds: int

    # Follow order view（必填，用於 deep-link copy_<id>）
    follow_order_view_url: str
    follow_order_headers: Dict[str, str]

    # User binding（可選；REQUIRE_BINDING=1 時會強制檢查）
    require_binding: bool
    bind_status_url: Optional[str]
    bind_headers: Dict[str, str]
    bind_third_type: str
    bind_brand: str
    bind_verify_url_template: Optional[str]
    bind_cache_seconds: int

    # Platform API base（餘額/下單/撤單/查委託等共用）
    platform_api_base_url: Optional[str]
    platform_api_headers: Dict[str, str]
    platform_wallet: str
    platform_brand: str
    platform_cancel_order_path: str

    exchange_info_refresh_seconds: int

    # Signal TTL
    signal_ttl_seconds: int

    # Storage
    database_url: str

    # Telegram 代理（可選；無法直連 api.telegram.org 時設定）
    telegram_proxy: Optional[str] = None


def load_settings() -> Settings:
    """
    所有設定一律從環境變數/.env 讀取，避免把敏感資訊寫入程式碼。

    必要變數：
    - TELEGRAM_BOT_TOKEN
    - PUBLIC_CHANNEL_ID（頻道 chat_id，如 -100xxxxxxxxxx）
    - FOLLOW_ORDER_VIEW_URL（/bot/follow_orders/view 完整 URL）
    - DATABASE_URL（可選；不填預設 sqlite）

    可選變數：
    - POSTS_HEADERS_JSON（可選，JSON 字串）
    - POLL_INTERVAL_SECONDS（預設 15）
    - SIGNAL_TTL_SECONDS（預設 86400；信號互動有效期，秒）
    - REQUIRE_BINDING（預設 0；設 1 則必須先綁定才能跟單/下單）
    - BIND_STATUS_URL（綁定狀態 API URL）
    - BIND_HEADERS_JSON（可選，JSON 字串）
    - BIND_THIRD_TYPE / BIND_TYPE（預設 telegram；對應 API 參數 type）
    - BIND_BRAND（預設 BYD；對應 API 參數 brand）
    - BIND_VERIFY_URL_TEMPLATE（可選，例如 https://xxx/verify?tg_user_id={tg_user_id}）
    - BIND_CACHE_SECONDS（預設 300；綁定狀態快取秒數）
    - PLATFORM_API_BASE_URL（例如 nlb-xxx:8122；餘額/下單/撤單/查委託共用）
    - PLATFORM_API_HEADERS_JSON（可選，JSON 字串）
    - PLATFORM_WALLET（預設 W001）
    - PLATFORM_BRAND（預設 BYD）
    - PLATFORM_CANCEL_ORDER_PATH（預設 /trade/batch_cancel_orders；撤單接口路徑）
    - EXCHANGE_INFO_REFRESH_SECONDS（預設 3600；定時刷新交易對信息）
    - TELEGRAM_PROXY（可選；若伺服器無法直連 api.telegram.org，設定代理，如 socks5://host:port 或 http://user:pass@host:port）
    """
    token = _getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("缺少 TELEGRAM_BOT_TOKEN，請在 .env 設定")

    channel_id_raw = _getenv("PUBLIC_CHANNEL_ID")
    if not channel_id_raw:
        raise RuntimeError("缺少 PUBLIC_CHANNEL_ID，請在 .env 設定（例如 -100xxxxxxxxxx）")
    try:
        channel_id = int(channel_id_raw)
    except ValueError as e:
        raise RuntimeError("PUBLIC_CHANNEL_ID 必須是整數（Telegram chat_id）") from e

    follow_view_url = _getenv("FOLLOW_ORDER_VIEW_URL")
    if not follow_view_url:
        raise RuntimeError("缺少 FOLLOW_ORDER_VIEW_URL，請在 .env 設定（例如 http://host:port/bot/follow_orders/view）")

    # posts polling 變成可選：若未設定 POSTS_URL 就不啟用輪巡
    posts_url = _getenv("POSTS_URL")

    poll_interval_raw = _getenv("POLL_INTERVAL_SECONDS", "15")
    try:
        poll_interval = int(poll_interval_raw)  # type: ignore[arg-type]
    except ValueError as e:
        raise RuntimeError("POLL_INTERVAL_SECONDS 必須是整數") from e
    if poll_interval < 3:
        raise RuntimeError("POLL_INTERVAL_SECONDS 建議 >= 3 秒，避免過度頻繁")

    ttl_raw = _getenv("SIGNAL_TTL_SECONDS", "86400")
    try:
        ttl_seconds = int(ttl_raw)  # type: ignore[arg-type]
    except ValueError as e:
        raise RuntimeError("SIGNAL_TTL_SECONDS 必須是整數") from e
    if ttl_seconds < 60:
        raise RuntimeError("SIGNAL_TTL_SECONDS 建議 >= 60 秒")

    # 兼容舊變數名（原專案用 DATABASE_URI_SWAP）
    database_url = (
        _getenv("DATABASE_URL")
        or _getenv("DATABASE_URI_SWAP")
        or "sqlite+aiosqlite:///./bot.db"
    )

    posts_headers = _parse_headers_json(_getenv("POSTS_HEADERS_JSON"))
    follow_headers = _parse_headers_json(_getenv("FOLLOW_ORDER_HEADERS_JSON") or _getenv("POSTS_HEADERS_JSON"))

    require_binding = _parse_bool(_getenv("REQUIRE_BINDING", "0"), default=False)
    bind_status_url = _getenv("BIND_STATUS_URL")
    bind_headers = _parse_headers_json(_getenv("BIND_HEADERS_JSON"))
    bind_third_type = _getenv("BIND_THIRD_TYPE") or _getenv("BIND_TYPE") or "telegram"
    bind_brand = _getenv("BIND_BRAND", "BYD") or "BYD"
    bind_verify_tpl = _getenv("BIND_VERIFY_URL_TEMPLATE")
    bind_cache_raw = _getenv("BIND_CACHE_SECONDS", "300")
    try:
        bind_cache_seconds = int(bind_cache_raw)  # type: ignore[arg-type]
    except Exception:
        bind_cache_seconds = 300
    if bind_cache_seconds < 0:
        bind_cache_seconds = 0

    platform_api_base_url = _getenv("PLATFORM_API_BASE_URL")
    platform_api_headers = _parse_headers_json(_getenv("PLATFORM_API_HEADERS_JSON"))
    platform_wallet = _getenv("PLATFORM_WALLET", "W001") or "W001"
    platform_brand = _getenv("PLATFORM_BRAND", bind_brand) or bind_brand
    platform_cancel_order_path = _getenv("PLATFORM_CANCEL_ORDER_PATH", "/trade/batch_cancel_orders") or "/trade/batch_cancel_orders"

    telegram_proxy = _getenv("TELEGRAM_PROXY")

    refresh_raw = _getenv("EXCHANGE_INFO_REFRESH_SECONDS", "3600")
    try:
        exchange_info_refresh_seconds = int(refresh_raw)  # type: ignore[arg-type]
    except Exception:
        exchange_info_refresh_seconds = 3600
    if exchange_info_refresh_seconds < 60:
        exchange_info_refresh_seconds = 60

    return Settings(
        telegram_bot_token=token,
        public_channel_id=channel_id,
        telegram_proxy=telegram_proxy,
        posts_url=posts_url,
        posts_headers=posts_headers,
        poll_interval_seconds=poll_interval,
        follow_order_view_url=follow_view_url,
        follow_order_headers=follow_headers,
        require_binding=require_binding,
        bind_status_url=bind_status_url,
        bind_headers=bind_headers,
        bind_third_type=str(bind_third_type),
        bind_brand=str(bind_brand),
        bind_verify_url_template=bind_verify_tpl,
        bind_cache_seconds=bind_cache_seconds,
        platform_api_base_url=platform_api_base_url,
        platform_api_headers=platform_api_headers,
        platform_wallet=str(platform_wallet),
        platform_brand=str(platform_brand),
        platform_cancel_order_path=str(platform_cancel_order_path),
        exchange_info_refresh_seconds=int(exchange_info_refresh_seconds),
        signal_ttl_seconds=ttl_seconds,
        database_url=database_url,
    )