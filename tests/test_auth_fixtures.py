from datetime import datetime, timezone

from app.contracts import AppUser, RecordStatus, Role


def admin_user() -> AppUser:
    return AppUser(
        id=1,
        role=Role.ADMIN,
        display_name="ผู้ดูแลระบบ",
        email="admin@lab.local",
        staff_id=1,
        borrower_id=1,
        status=RecordStatus.ACTIVE,
        must_change_password=False,
        last_login_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
    )


def borrower_user() -> AppUser:
    return AppUser(
        id=2,
        role=Role.USER,
        display_name="ผู้ยืมทดสอบ",
        email="borrower@lab.local",
        staff_id=None,
        borrower_id=1,
        status=RecordStatus.ACTIVE,
        must_change_password=False,
        last_login_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
    )
