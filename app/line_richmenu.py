from __future__ import annotations

import os

from app.contracts import AppUser, Role

RICHMENU_ENV_KEYS = {
    Role.ADMIN: "LINE_RICHMENU_ADMIN_ID",
    Role.USER: "LINE_RICHMENU_USER_ID",
}


def get_richmenu_for_user(user: AppUser | None) -> str | None:
    """เลือก richmenu ID ตาม role ของผู้ใช้ (อ่าน env ตอนเรียกใช้)"""
    if user is None:
        return None
    return os.getenv(RICHMENU_ENV_KEYS[user.role]) or None
