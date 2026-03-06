from __future__ import annotations

from typing import Any, Optional

from src.i18n import t


def _extract_code_msg(resp_json: Optional[dict[str, Any]], fallback_err: Optional[str]) -> tuple[Optional[int], str]:
    code: Optional[int] = None
    msg = ""
    if isinstance(resp_json, dict):
        raw_code = resp_json.get("code")
        try:
            code = int(raw_code) if raw_code is not None else None
        except Exception:
            code = None
        raw_msg = resp_json.get("message")
        if raw_msg is not None:
            msg = str(raw_msg)
    if not msg and fallback_err:
        msg = str(fallback_err)
    msg = msg.strip()
    return code, msg


# 常用錯誤碼 → i18n key（覆蓋最常見/高頻的；其餘走 generic）
_CODE_TO_I18N_KEY: dict[int, str] = {
    401: "api_err_401",
    500: "api_err_500",
    501: "api_err_501",
    506: "api_err_506",
    510: "api_err_510",
    511: "api_err_511",
    513: "api_err_513",
    514: "api_err_514",
    515: "api_err_515",
    600: "api_err_600",
    1002: "api_err_1002",
    1003: "api_err_1003",
    1005: "api_err_1005",
    2001: "api_err_2001",
    2021: "api_err_2021",
    2022: "api_err_2022",
    2023: "api_err_2023",
    100012: "api_err_100012",
    100014: "api_err_100014",
    100019: "api_err_100019",
    100051: "api_err_100051",
    200008: "api_err_200008",
    200009: "api_err_200009",
    200014: "api_err_200014",
    200015: "api_err_200015",
}


def platform_error_text(lang: str, resp_json: Optional[dict[str, Any]], fallback_err: Optional[str] = None) -> str:
    """
    把平台 API 的 (code,message) 翻成用戶可讀、多語言的錯誤訊息。
    - 若 code 在白名單，回傳固定文案（必要時帶入 message/code）
    - 否則回傳 generic：包含 code + message（便於除錯）
    """
    code, msg = _extract_code_msg(resp_json, fallback_err)
    if code is None:
        # 不展示 code；若有 message 就用 message，否則給通用文案
        return (msg or t(lang, "api_err_unknown")).strip()
    key = _CODE_TO_I18N_KEY.get(int(code))
    if key:
        # 不展示 code；固定輸出該錯誤碼對應原因
        return t(lang, key).strip()
    # 未收錄的錯誤碼：只顯示 message（若沒有就用通用文案）
    return (msg or t(lang, "api_err_unknown")).strip()

