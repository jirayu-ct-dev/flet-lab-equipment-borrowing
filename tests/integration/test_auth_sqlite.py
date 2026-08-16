from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.contracts import (
    AppUser,
    ChangePasswordCommand,
    CreateUserCommand,
    LoginCommand,
    RecordStatus,
    RegisterLineUser,
    Role,
)
from app.database import connect, initialize_database
from app.errors import (
    AuthenticationError,
    DuplicateCodeError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from app.repositories import auth_repository
from app.security import hash_password, new_session_token
from app.services.sqlite_auth_adapter import SQLiteAuthAdapter


def _iso(instant: datetime) -> str:
    return instant.isoformat(timespec="milliseconds").replace("+00:00", "Z")


@pytest.fixture
def auth(tmp_path):
    database_path = tmp_path / "auth.sqlite3"
    adapter = SQLiteAuthAdapter(database_path)
    auth_repository.create_user(
        database_path,
        role="admin",
        display_name="ผู้ดูแลระบบ",
        email="admin@lab.local",
        password_hash=hash_password("admin123"),
    )
    auth_repository.create_user(
        database_path,
        role="user",
        display_name="ผู้ยืมทดสอบ",
        email="borrower@lab.local",
        password_hash=hash_password("borrow123"),
    )
    return adapter


def _admin(auth: SQLiteAuthAdapter) -> AppUser:
    return auth.authenticate(LoginCommand("admin@lab.local", "admin123"))


def _borrower(auth: SQLiteAuthAdapter) -> AppUser:
    return auth.authenticate(LoginCommand("borrower@lab.local", "borrow123"))


def test_initialize_applies_auth_migration(tmp_path) -> None:
    database_path = tmp_path / "migration.sqlite3"
    initialize_database(database_path)

    with connect(database_path) as database:
        versions = [
            row["version"]
            for row in database.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
        ]
        tables = {
            row["name"]
            for row in database.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert versions == [1, 2, 3, 4, 5, 6, 7, 8]
    assert {"app_users", "app_sessions"} <= tables


def test_authenticate_success_updates_last_login(auth) -> None:
    user = auth.authenticate(LoginCommand("  Borrower@LAB.local ", "borrow123"))

    assert user.role is Role.USER
    assert user.last_login_at is not None
    assert auth.get(user.id).last_login_at is not None


def test_authenticate_rejects_wrong_password_and_unknown_email(auth) -> None:
    with pytest.raises(AuthenticationError):
        auth.authenticate(LoginCommand("admin@lab.local", "nope-nope-1"))
    with pytest.raises(AuthenticationError):
        auth.authenticate(LoginCommand("ghost@lab.local", "whatever123"))


def test_authenticate_rejects_inactive_user(auth) -> None:
    admin = _admin(auth)
    auth.set_user_status(2, RecordStatus.INACTIVE, actor=admin)

    with pytest.raises(AuthenticationError):
        auth.authenticate(LoginCommand("borrower@lab.local", "borrow123"))


def test_user_crud_and_duplicate_email(auth) -> None:
    admin = _admin(auth)
    created = auth.create_user(
        CreateUserCommand(
            role=Role.USER,
            display_name="สมาชิกใหม่",
            email="member@lab.local",
            password="member-password-1",
        ),
        actor=admin,
    )

    assert created.id > 0
    assert created.must_change_password is False
    assert auth.get(created.id).display_name == "สมาชิกใหม่"
    assert len(auth.list_users()) == 3

    with pytest.raises(DuplicateCodeError):
        auth.create_user(
            CreateUserCommand(
                role=Role.USER, display_name="ซ้ำ", email="MEMBER@LAB.LOCAL"
            ),
            actor=admin,
        )


def test_create_user_requires_manage_users_permission(auth) -> None:
    borrower = _borrower(auth)

    with pytest.raises(PermissionDenied):
        auth.create_user(
            CreateUserCommand(
                role=Role.USER, display_name="ไม่ควรสร้าง", email="x@lab.local"
            ),
            actor=borrower,
        )


def test_set_user_status_roundtrip(auth) -> None:
    admin = _admin(auth)
    with pytest.raises(PermissionDenied):
        auth.set_user_status(1, RecordStatus.INACTIVE, actor=_borrower(auth))

    auth.set_user_status(2, RecordStatus.INACTIVE, actor=admin)
    assert auth.get(2).status is RecordStatus.INACTIVE

    with pytest.raises(NotFoundError):
        auth.set_user_status(999, RecordStatus.ACTIVE, actor=admin)


def test_change_password_updates_hash_and_clears_flag(auth) -> None:
    borrower = _borrower(auth)

    with pytest.raises(AuthenticationError):
        auth.change_password(
            2, ChangePasswordCommand("wrong-password", "new-password-123")
        )
    with pytest.raises(ValidationError):
        auth.change_password(2, ChangePasswordCommand("borrow123", "short"))

    auth.change_password(2, ChangePasswordCommand("borrow123", "new-password-123"))

    assert auth.get(2).must_change_password is False
    auth.authenticate(LoginCommand("borrower@lab.local", "new-password-123"))
    with pytest.raises(AuthenticationError):
        auth.authenticate(LoginCommand("borrower@lab.local", "borrow123"))


def test_admin_reset_password_sets_must_change(auth) -> None:
    borrower = _borrower(auth)
    with pytest.raises(PermissionDenied):
        auth.admin_reset_password(2, "reset-password-1", actor=borrower)

    admin = _admin(auth)
    auth.admin_reset_password(2, "reset-password-1", actor=admin)

    assert auth.get(2).must_change_password is True
    auth.authenticate(LoginCommand("borrower@lab.local", "reset-password-1"))

    with pytest.raises(NotFoundError):
        auth.admin_reset_password(999, "reset-password-1", actor=admin)


def test_register_line_user_creates_borrower_and_user(auth) -> None:
    created = auth.register_line_user(
        RegisterLineUser(
            line_sub="line-sub-1",
            display_name="ผู้ใช้ไลน์",
            email="line@lab.local",
            borrower_code="BR-LINE-001",
            department="ฝ่ายไอที",
        )
    )

    assert created.role is Role.USER
    assert created.borrower_id is not None
    assert created.must_change_password is False
    assert auth.find_by_line_sub("line-sub-1").id == created.id

    with connect(auth.database_path) as database:
        borrower = database.execute(
            "SELECT id, department FROM borrowers WHERE borrower_code = 'BR-LINE-001'"
        ).fetchone()
    assert borrower["id"] == created.borrower_id
    assert borrower["department"] == "ฝ่ายไอที"

    with pytest.raises(DuplicateCodeError):
        auth.register_line_user(
            RegisterLineUser(line_sub="line-sub-1", display_name="ซ้ำ")
        )


def test_register_line_user_reuses_existing_borrower(auth) -> None:
    with connect(auth.database_path) as database:
        database.execute(
            "INSERT INTO borrowers(borrower_code, full_name) VALUES ('BR-EXIST', 'มีอยู่แล้ว')"
        )
        database.commit()
        borrower_id = database.execute(
            "SELECT id FROM borrowers WHERE borrower_code = 'BR-EXIST'"
        ).fetchone()["id"]

    created = auth.register_line_user(
        RegisterLineUser(
            line_sub="line-sub-2",
            display_name="ผู้ใช้ไลน์สอง",
            borrower_code="BR-EXIST",
        )
    )
    assert created.borrower_id == borrower_id


def test_register_line_user_without_borrower_code(auth) -> None:
    created = auth.register_line_user(
        RegisterLineUser(line_sub="line-sub-3", display_name="ไม่มีรหัสผู้ยืม")
    )

    assert created.role is Role.USER
    assert created.borrower_id is None


def test_sessions_lifecycle_and_expiry(auth) -> None:
    admin = _admin(auth)
    now = datetime.now(timezone.utc)

    valid_token = new_session_token()
    expired_token = new_session_token()
    auth.create_session(
        token=valid_token,
        user_id=admin.id,
        expires_at=_iso(now + timedelta(hours=1)),
    )
    auth.create_session(
        token=expired_token,
        user_id=admin.id,
        expires_at=_iso(now - timedelta(minutes=5)),
    )

    session = auth.get_session(valid_token)
    assert session is not None
    assert session["user_id"] == admin.id

    removed = auth.delete_expired_sessions(now)
    assert removed == 1
    assert auth.get_session(expired_token) is None
    assert auth.get_session(valid_token) is not None

    auth.delete_session(valid_token)
    assert auth.get_session(valid_token) is None


def test_set_user_role_updates_role(auth) -> None:
    admin = _admin(auth)

    updated = auth.set_user_role(2, Role.ADMIN, actor=admin)

    assert updated.id == 2
    assert updated.role is Role.ADMIN
    assert auth.get(2).role is Role.ADMIN


def test_set_user_role_requires_manage_users(auth) -> None:
    borrower = _borrower(auth)

    with pytest.raises(PermissionDenied):
        auth.set_user_role(2, Role.ADMIN, actor=borrower)


def test_set_user_role_unknown_user(auth) -> None:
    admin = _admin(auth)

    with pytest.raises(NotFoundError):
        auth.set_user_role(999, Role.ADMIN, actor=admin)
