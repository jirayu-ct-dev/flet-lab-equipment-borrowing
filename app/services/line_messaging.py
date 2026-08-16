from __future__ import annotations

import os
from urllib.request import Request, urlopen

from app.contracts import AppUser
from app.line_richmenu import get_richmenu_for_user

LINE_API_BASE = "https://api.line.me"
_TIMEOUT_SECONDS = 10


def api_request(
    method: str,
    url: str,
    *,
    token: str,
    body: bytes | None = None,
    content_type: str | None = None,
) -> bytes:
    """Call the LINE Messaging API and return the raw response body."""
    request = Request(url, data=body, method=method)
    request.add_header("Authorization", f"Bearer {token}")
    if content_type is not None:
        request.add_header("Content-Type", content_type)
    with urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
        return response.read()


class LineMessagingService:
    """Thin LINE Messaging API client for richmenu linking."""

    def __init__(self, access_token: str | None = None) -> None:
        self.token = access_token or os.getenv(
            "LINE_MESSAGING_CHANNEL_ACCESS_TOKEN"
        )

    def is_configured(self) -> bool:
        """เช็คว่า Messaging API ถูกตั้งค่าแล้ว"""
        return bool(self.token)

    def link_richmenu_to_user(self, line_user_id: str, richmenu_id: str) -> None:
        """เชื่อมโยง richmenu กับผู้ใช้ (idempotent)"""
        if not self.is_configured() or not richmenu_id or not line_user_id:
            return
        api_request(
            "POST",
            f"{LINE_API_BASE}/v2/bot/user/{line_user_id}/richmenu/{richmenu_id}",
            token=self.token,
        )

    def unlink_richmenu_from_user(self, line_user_id: str) -> None:
        """ยกเลิก richmenu ที่ผูกกับผู้ใช้ (กลับไปใช้ default)"""
        if not self.is_configured() or not line_user_id:
            return
        api_request(
            "DELETE",
            f"{LINE_API_BASE}/v2/bot/user/{line_user_id}/richmenu",
            token=self.token,
        )


def sync_richmenu(
    line_user_id: str | None,
    user: AppUser | None,
    service: LineMessagingService | None = None,
) -> None:
    """Best-effort richmenu switch — ไม่เคย raise ไปบล็อก login flow"""
    richmenu_id = get_richmenu_for_user(user)
    if not richmenu_id or not line_user_id:
        return
    messaging = service or LineMessagingService()
    if not messaging.is_configured():
        return
    try:
        messaging.link_richmenu_to_user(line_user_id, richmenu_id)
    except Exception:
        return
