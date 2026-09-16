from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from app.security import hash_password


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "equipment_lending.db"
BANGKOK = ZoneInfo("Asia/Bangkok")


def database_path() -> Path:
    configured = os.getenv("APP_DB_PATH", "").strip()
    return Path(configured).expanduser().resolve() if configured else DEFAULT_DB_PATH


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_text(value: datetime | None = None) -> str:
    return (value or utc_now()).astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def bangkok_today(value: datetime | None = None) -> date:
    return (value or utc_now()).astimezone(BANGKOK).date()


@contextmanager
def connect(path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    target = Path(path) if path is not None else database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(target)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 5000")
    try:
        yield db
    finally:
        db.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS faculties (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive'))
);

CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY,
    faculty_id INTEGER NOT NULL REFERENCES faculties(id),
    name TEXT NOT NULL COLLATE NOCASE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    UNIQUE (faculty_id, name)
);

CREATE TABLE IF NOT EXISTS cohorts (
    id INTEGER PRIMARY KEY,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    name TEXT NOT NULL COLLATE NOCASE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    UNIQUE (department_id, name)
);

CREATE TABLE IF NOT EXISTS class_groups (
    id INTEGER PRIMARY KEY,
    cohort_id INTEGER NOT NULL REFERENCES cohorts(id),
    name TEXT NOT NULL COLLATE NOCASE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    UNIQUE (cohort_id, name)
);

CREATE TABLE IF NOT EXISTS equipment_categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive'))
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    backup_email TEXT,
    role TEXT NOT NULL DEFAULT 'borrower' CHECK (role IN ('admin', 'borrower')),
    user_type TEXT NOT NULL CHECK (user_type IN ('student', 'teacher', 'staff')),
    faculty_id INTEGER REFERENCES faculties(id),
    department_id INTEGER REFERENCES departments(id),
    cohort_id INTEGER REFERENCES cohorts(id),
    class_group_id INTEGER REFERENCES class_groups(id),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    must_change_password INTEGER NOT NULL DEFAULT 1,
    line_user_id TEXT UNIQUE,
    last_login_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    last_used_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS equipment_types (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE,
    category_id INTEGER NOT NULL REFERENCES equipment_categories(id),
    brand TEXT,
    model TEXT,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (category_id, name, brand, model)
);

CREATE TABLE IF NOT EXISTS equipment_units (
    id INTEGER PRIMARY KEY,
    equipment_type_id INTEGER NOT NULL REFERENCES equipment_types(id),
    asset_code TEXT NOT NULL COLLATE NOCASE UNIQUE,
    storage_location TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'borrowed', 'inactive')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    borrower_id INTEGER NOT NULL REFERENCES users(id),
    borrow_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    created_by_user_id INTEGER NOT NULL REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed')),
    reminder_3d_at TEXT,
    reminder_1d_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (due_date >= borrow_date)
);

CREATE TABLE IF NOT EXISTS loan_items (
    id INTEGER PRIMARY KEY,
    loan_id INTEGER NOT NULL REFERENCES loans(id),
    equipment_unit_id INTEGER NOT NULL REFERENCES equipment_units(id),
    returned_at TEXT,
    received_by_user_id INTEGER REFERENCES users(id),
    UNIQUE (loan_id, equipment_unit_id)
);

CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_expiry ON auth_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_units_status ON equipment_units(status);
CREATE INDEX IF NOT EXISTS idx_loans_borrower_status ON loans(borrower_id, status);
CREATE INDEX IF NOT EXISTS idx_loan_items_loan ON loan_items(loan_id);
"""


def initialize_database(path: str | Path | None = None) -> Path:
    target = Path(path) if path is not None else database_path()
    with connect(target) as db:
        db.executescript(SCHEMA)
        db.execute(
            """
            INSERT OR IGNORE INTO users(
                username, password_hash, full_name, role, user_type,
                status, must_change_password
            ) VALUES ('admin', ?, 'ผู้ดูแลระบบ', 'admin', 'staff', 'active', 1)
            """,
            (hash_password("admin1234"),),
        )
        db.commit()
    return target
