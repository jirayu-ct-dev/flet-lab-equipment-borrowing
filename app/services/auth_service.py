from __future__ import annotations

from app.contracts import AppUser, ChangePasswordCommand, Permission, has_permission
from app.errors import AuthenticationError, PermissionDenied, ValidationError
from app.security import hash_password, validate_password_strength, verify_password

WRONG_CREDENTIALS_MESSAGE = "อีเมลหรือรหัสผ่านไม่ถูกต้อง"
INACTIVE_USER_MESSAGE = "บัญชีนี้ถูกปิดใช้งาน"
NO_PASSWORD_MESSAGE = "บัญชีนี้ยังไม่มีการตั้งรหัสผ่าน"


def verify_login(password: str, stored: str | None) -> None:
    if stored is None or not verify_password(password, stored):
        raise AuthenticationError(WRONG_CREDENTIALS_MESSAGE)


def check_manage_users(actor: AppUser | None) -> None:
    if not has_permission(actor, Permission.MANAGE_USERS):
        raise PermissionDenied("คุณไม่มีสิทธิ์จัดการบัญชีผู้ใช้")


def apply_change_password(stored: str | None, command: ChangePasswordCommand) -> str:
    """Verify the current password, validate the new one, return its hash."""
    if stored is None:
        raise AuthenticationError(NO_PASSWORD_MESSAGE)
    verify_login(command.current_password, stored)
    error = validate_password_strength(command.new_password)
    if error is not None:
        raise ValidationError(error, field="new_password")
    return hash_password(command.new_password)
