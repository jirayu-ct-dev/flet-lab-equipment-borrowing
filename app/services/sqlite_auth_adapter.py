from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from app.contracts import (
    AppUser,
    ChangePasswordCommand,
    CreateUserCommand,
    LoginCommand,
    RecordStatus,
    RegisterLineUser,
    Role,
)
from app.database import connection, initialize_database, utc_now
from app.errors import (
    AuthenticationError,
    DuplicateCodeError,
    NotFoundError,
    ValidationError,
)
from app.repositories import auth_repository
from app.security import hash_password, validate_password_strength
from app.services.auth_service import (
    INACTIVE_USER_MESSAGE,
    WRONG_CREDENTIALS_MESSAGE,
    apply_change_password,
    check_manage_users,
    verify_login,
)

DatabasePath = str | Path


def _timestamp(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def _app_user(row: dict) -> AppUser:
    return AppUser(
        id=row["id"],
        role=Role(row["role"]),
        display_name=row["display_name"],
        email=row["email"],
        staff_id=row["staff_id"],
        borrower_id=row["borrower_id"],
        status=RecordStatus(row["status"]),
        must_change_password=bool(row["must_change_password"]),
        last_login_at=_timestamp(row["last_login_at"]),
        line_sub=row.get("line_sub"),
    )


class SQLiteAuthAdapter:
    """Persistent AuthService backed by raw-SQL auth_repository functions."""

    def __init__(self, database_path: DatabasePath) -> None:
        self.database_path = Path(database_path)
        initialize_database(self.database_path)

    def authenticate(self, command: LoginCommand) -> AppUser:
        row = auth_repository.find_user_by_email(self.database_path, command.identity)
        if row is None:
            raise AuthenticationError(WRONG_CREDENTIALS_MESSAGE)
        verify_login(command.password, row["password_hash"])
        if row["status"] != RecordStatus.ACTIVE.value:
            raise AuthenticationError(INACTIVE_USER_MESSAGE)
        auth_repository.update_last_login(self.database_path, row["id"], utc_now())
        return self._get_required(row["id"])

    def get(self, user_id: int) -> AppUser | None:
        row = auth_repository.get_user(self.database_path, user_id)
        return _app_user(row) if row is not None else None

    def find_by_line_sub(self, line_sub: str) -> AppUser | None:
        row = auth_repository.find_user_by_line_sub(self.database_path, line_sub)
        return _app_user(row) if row is not None else None

    def list_users(self) -> list[AppUser]:
        return [
            _app_user(row) for row in auth_repository.list_users(self.database_path)
        ]

    def create_user(self, command: CreateUserCommand, *, actor: AppUser) -> AppUser:
        check_manage_users(actor)
        password_hash = hash_password(command.password) if command.password else None
        email = command.email.strip() if command.email else None
        if email is not None and (
            auth_repository.find_user_by_email(self.database_path, email) is not None
        ):
            raise DuplicateCodeError("email", email)
        try:
            user_id = auth_repository.create_user(
                self.database_path,
                role=command.role.value,
                display_name=command.display_name.strip(),
                email=email,
                password_hash=password_hash,
                staff_id=command.staff_id,
                borrower_id=command.borrower_id,
                must_change_password=password_hash is None,
            )
        except sqlite3.IntegrityError as error:
            self._translate_duplicate(error, email=email)
            raise
        return self._get_required(user_id)

    def set_user_status(
        self, user_id: int, status: RecordStatus, *, actor: AppUser
    ) -> None:
        check_manage_users(actor)
        if auth_repository.get_user(self.database_path, user_id) is None:
            raise NotFoundError("user", user_id)
        auth_repository.update_status(self.database_path, user_id, status.value)

    def set_user_role(
        self, user_id: int, new_role: Role, *, actor: AppUser
    ) -> AppUser:
        check_manage_users(actor)
        if auth_repository.get_user(self.database_path, user_id) is None:
            raise NotFoundError("user", user_id)
        auth_repository.update_role(self.database_path, user_id, new_role.value)
        return self._get_required(user_id)

    def set_user_borrower(
        self, user_id: int, borrower_id: int | None, *, actor: AppUser
    ) -> AppUser:
        check_manage_users(actor)
        if auth_repository.get_user(self.database_path, user_id) is None:
            raise NotFoundError("user", user_id)
        if borrower_id is not None:
            borrower = auth_repository.find_borrower_by_id(
                self.database_path, borrower_id
            )
            if borrower is None:
                raise NotFoundError("borrower", borrower_id)
        auth_repository.update_user_borrower(
            self.database_path, user_id, borrower_id
        )
        return self._get_required(user_id)

    def set_user_staff(
        self, user_id: int, staff_id: int | None, *, actor: AppUser
    ) -> AppUser:
        check_manage_users(actor)
        if auth_repository.get_user(self.database_path, user_id) is None:
            raise NotFoundError("user", user_id)
        if staff_id is not None:
            with connection(self.database_path) as database:
                staff = database.execute("SELECT id FROM staff WHERE id = ?", (staff_id,)).fetchone()
            if staff is None:
                raise NotFoundError("staff", staff_id)
        try:
            auth_repository.update_user_staff(self.database_path, user_id, staff_id)
        except sqlite3.IntegrityError as error:
            self._translate_duplicate(error, staff_id=str(staff_id) if staff_id is not None else None)
            raise
        return self._get_required(user_id)

    def change_password(self, user_id: int, command: ChangePasswordCommand) -> None:
        row = auth_repository.get_user(self.database_path, user_id)
        if row is None:
            raise NotFoundError("user", user_id)
        new_hash = apply_change_password(row["password_hash"], command)
        auth_repository.update_password(
            self.database_path, user_id, new_hash, must_change_password=False
        )

    def admin_reset_password(
        self, user_id: int, new_password: str, *, actor: AppUser
    ) -> None:
        check_manage_users(actor)
        if auth_repository.get_user(self.database_path, user_id) is None:
            raise NotFoundError("user", user_id)
        error = validate_password_strength(new_password)
        if error is not None:
            raise ValidationError(error, field="new_password")
        auth_repository.update_password(
            self.database_path,
            user_id,
            hash_password(new_password),
            must_change_password=True,
        )

    def register_line_user(self, command: RegisterLineUser) -> AppUser:
        if (
            auth_repository.find_user_by_line_sub(
                self.database_path, command.line_sub
            )
            is not None
        ):
            raise DuplicateCodeError("line_sub", command.line_sub)
        borrower_id = None
        if command.borrower_code:
            borrower_code = command.borrower_code.strip()
            borrower = auth_repository.find_borrower_by_code(
                self.database_path, borrower_code
            )
            if borrower is None:
                borrower_id = auth_repository.create_borrower(
                    self.database_path,
                    borrower_code=borrower_code,
                    full_name=command.display_name.strip(),
                    department=command.department,
                    email=command.email,
                )
            else:
                borrower_id = borrower["id"]
        try:
            user_id = auth_repository.create_user(
                self.database_path,
                role=Role.USER.value,
                display_name=command.display_name.strip(),
                email=command.email,
                line_sub=command.line_sub,
                borrower_id=borrower_id,
                must_change_password=False,
            )
        except sqlite3.IntegrityError as error:
            self._translate_duplicate(error, line_sub=command.line_sub)
            raise
        return self._get_required(user_id)

    def create_session(self, *, token: str, user_id: int, expires_at: str) -> None:
        auth_repository.create_session(
            self.database_path, token=token, user_id=user_id, expires_at=expires_at
        )

    def get_session(self, token: str) -> dict | None:
        return auth_repository.get_session(self.database_path, token)

    def delete_session(self, token: str) -> None:
        auth_repository.delete_session(self.database_path, token)

    def delete_expired_sessions(self, now: datetime) -> int:
        return auth_repository.delete_expired_sessions(self.database_path, now)

    def _get_required(self, user_id: int) -> AppUser:
        user = self.get(user_id)
        if user is None:
            raise NotFoundError("user", user_id)
        return user

    @staticmethod
    def _translate_duplicate(
        error: sqlite3.IntegrityError, **values: str | None
    ) -> None:
        message = str(error)
        for field, value in values.items():
            if value is not None and f"app_users.{field}" in message:
                raise DuplicateCodeError(field, value) from error
        raise error
