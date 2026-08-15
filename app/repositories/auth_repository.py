from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from app.database import connection

DatabasePath = str | Path

USER_COLUMNS = """
    id, role, email, password_hash, line_sub, display_name, staff_id,
    borrower_id, status, must_change_password, last_login_at,
    created_at, updated_at
"""


def _iso(instant: datetime) -> str:
    return instant.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _write(
    database_path: DatabasePath, statement: str, params: tuple[object, ...] = ()
) -> sqlite3.Cursor:
    with connection(database_path) as database:
        cursor = database.execute(statement, params)
        database.commit()
        return cursor


def create_user(
    database_path: DatabasePath,
    *,
    role: str,
    display_name: str,
    email: str | None = None,
    password_hash: str | None = None,
    line_sub: str | None = None,
    staff_id: int | None = None,
    borrower_id: int | None = None,
    status: str = "active",
    must_change_password: bool = False,
) -> int:
    cursor = _write(
        database_path,
        """
        INSERT INTO app_users(
            role, email, password_hash, line_sub, display_name, staff_id,
            borrower_id, status, must_change_password
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            role,
            email,
            password_hash,
            line_sub,
            display_name,
            staff_id,
            borrower_id,
            status,
            int(must_change_password),
        ),
    )
    return cursor.lastrowid


def get_user(database_path: DatabasePath, user_id: int) -> dict | None:
    with connection(database_path) as database:
        row = database.execute(
            f"SELECT {USER_COLUMNS} FROM app_users WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row is not None else None


def find_user_by_email(database_path: DatabasePath, email: str) -> dict | None:
    with connection(database_path) as database:
        row = database.execute(
            f"SELECT {USER_COLUMNS} FROM app_users WHERE email = ? COLLATE NOCASE",
            (email.strip(),),
        ).fetchone()
    return dict(row) if row is not None else None


def find_user_by_line_sub(database_path: DatabasePath, line_sub: str) -> dict | None:
    with connection(database_path) as database:
        row = database.execute(
            f"SELECT {USER_COLUMNS} FROM app_users WHERE line_sub = ?",
            (line_sub,),
        ).fetchone()
    return dict(row) if row is not None else None


def list_users(database_path: DatabasePath) -> list[dict]:
    with connection(database_path) as database:
        rows = database.execute(
            f"SELECT {USER_COLUMNS} FROM app_users ORDER BY id"
        ).fetchall()
    return [dict(row) for row in rows]


def update_password(
    database_path: DatabasePath,
    user_id: int,
    password_hash: str,
    *,
    must_change_password: bool = False,
) -> None:
    _write(
        database_path,
        """
        UPDATE app_users
        SET password_hash = ?, must_change_password = ?,
            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        WHERE id = ?
        """,
        (password_hash, int(must_change_password), user_id),
    )


def update_status(database_path: DatabasePath, user_id: int, status: str) -> None:
    _write(
        database_path,
        """
        UPDATE app_users
        SET status = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        WHERE id = ?
        """,
        (status, user_id),
    )


def update_last_login(database_path: DatabasePath, user_id: int, now: datetime) -> None:
    _write(
        database_path,
        """
        UPDATE app_users
        SET last_login_at = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        WHERE id = ?
        """,
        (_iso(now), user_id),
    )


def find_borrower_by_code(database_path: DatabasePath, borrower_code: str) -> dict | None:
    with connection(database_path) as database:
        row = database.execute(
            """
            SELECT id, borrower_code, full_name, department, email, phone, note,
                   status, created_at, updated_at
            FROM borrowers
            WHERE borrower_code = ?
            """,
            (borrower_code,),
        ).fetchone()
    return dict(row) if row is not None else None


def create_borrower(
    database_path: DatabasePath,
    *,
    borrower_code: str,
    full_name: str,
    department: str | None = None,
    email: str | None = None,
) -> int:
    cursor = _write(
        database_path,
        """
        INSERT INTO borrowers(borrower_code, full_name, department, email)
        VALUES (?, ?, ?, ?)
        """,
        (borrower_code, full_name, department, email),
    )
    return cursor.lastrowid


def create_session(
    database_path: DatabasePath, *, token: str, user_id: int, expires_at: str
) -> None:
    _write(
        database_path,
        "INSERT INTO app_sessions(token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires_at),
    )


def get_session(database_path: DatabasePath, token: str) -> dict | None:
    with connection(database_path) as database:
        row = database.execute(
            """
            SELECT token, user_id, created_at, expires_at
            FROM app_sessions
            WHERE token = ?
            """,
            (token,),
        ).fetchone()
    return dict(row) if row is not None else None


def delete_session(database_path: DatabasePath, token: str) -> None:
    _write(database_path, "DELETE FROM app_sessions WHERE token = ?", (token,))


def delete_expired_sessions(database_path: DatabasePath, now: datetime) -> int:
    cursor = _write(
        database_path,
        "DELETE FROM app_sessions WHERE expires_at <= ?",
        (_iso(now),),
    )
    return cursor.rowcount
