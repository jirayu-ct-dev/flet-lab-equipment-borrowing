from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


DEFAULT_DB_PATH = Path("data/lab_equipment.db")
BANGKOK_TIMEZONE = ZoneInfo("Asia/Bangkok")


def utc_now() -> datetime:
    """Return an aware UTC timestamp for persisted event times."""
    return datetime.now(timezone.utc)


def bangkok_today(now: datetime | None = None) -> date:
    """Return the current Bangkok business date."""
    instant = now or utc_now()
    if instant.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return instant.astimezone(BANGKOK_TIMEZONE).date()


def bangkok_date(timestamp: str | datetime) -> date:
    """Convert a persisted UTC timestamp to its Bangkok calendar date."""
    instant = (
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if isinstance(timestamp, str)
        else timestamp
    )
    return bangkok_today(instant)


def get_database_path() -> Path:
    """Resolve the database path from APP_DB_PATH or the project default."""
    configured_path = os.getenv("APP_DB_PATH")
    return Path(configured_path) if configured_path else DEFAULT_DB_PATH


def connect(database_path: str | Path | None = None) -> sqlite3.Connection:
    """Open a configured SQLite connection with referential integrity enabled."""
    path = Path(database_path) if database_path is not None else get_database_path()
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def connection(database_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    """Yield a connection and always close it after use."""
    database = connect(database_path)
    try:
        yield database
    finally:
        database.close()


MIGRATIONS: tuple[str, ...] = (
    """
    CREATE TABLE locations (
        id INTEGER PRIMARY KEY,
        location_code TEXT NOT NULL UNIQUE,
        building TEXT,
        room TEXT NOT NULL,
        cabinet TEXT,
        shelf TEXT,
        status TEXT NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'inactive'))
    );

    CREATE TABLE equipment (
        id INTEGER PRIMARY KEY,
        equipment_code TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        category TEXT,
        manufacturer TEXT,
        model TEXT,
        default_location_id INTEGER REFERENCES locations(id),
        purchase_price NUMERIC CHECK (purchase_price IS NULL OR purchase_price >= 0),
        status TEXT NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'inactive')),
        description TEXT,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    );

    CREATE TABLE equipment_units (
        id INTEGER PRIMARY KEY,
        asset_code TEXT NOT NULL UNIQUE,
        equipment_id INTEGER NOT NULL REFERENCES equipment(id),
        serial_number TEXT UNIQUE,
        current_location_id INTEGER REFERENCES locations(id),
        status TEXT NOT NULL DEFAULT 'available'
            CHECK (status IN ('available', 'borrowed', 'maintenance', 'reported_lost', 'retired')),
        acquired_at TEXT NOT NULL,
        purchase_price NUMERIC CHECK (purchase_price IS NULL OR purchase_price >= 0),
        note TEXT,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    );

    CREATE TABLE staff (
        id INTEGER PRIMARY KEY,
        staff_code TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        status TEXT NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'inactive')),
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    );

    CREATE TABLE borrowers (
        id INTEGER PRIMARY KEY,
        borrower_code TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL,
        department TEXT,
        email TEXT,
        phone TEXT,
        note TEXT,
        status TEXT NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'inactive')),
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    );

    CREATE TABLE borrow_transactions (
        id INTEGER PRIMARY KEY,
        transaction_code TEXT NOT NULL UNIQUE,
        borrower_id INTEGER NOT NULL REFERENCES borrowers(id),
        borrow_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        purpose TEXT,
        recorded_by_staff_id INTEGER NOT NULL REFERENCES staff(id),
        status TEXT NOT NULL DEFAULT 'draft'
            CHECK (status IN ('draft', 'active', 'completed', 'cancelled')),
        note TEXT,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        CHECK (due_date >= borrow_date)
    );

    CREATE TABLE borrow_items (
        id INTEGER PRIMARY KEY,
        transaction_id INTEGER NOT NULL REFERENCES borrow_transactions(id),
        equipment_unit_id INTEGER NOT NULL REFERENCES equipment_units(id),
        UNIQUE (transaction_id, equipment_unit_id)
    );

    CREATE TABLE returns (
        id INTEGER PRIMARY KEY,
        transaction_id INTEGER NOT NULL REFERENCES borrow_transactions(id),
        returned_at TEXT NOT NULL,
        received_by_staff_id INTEGER NOT NULL REFERENCES staff(id),
        note TEXT
    );

    CREATE TABLE return_items (
        id INTEGER PRIMARY KEY,
        return_id INTEGER NOT NULL REFERENCES returns(id),
        borrow_item_id INTEGER NOT NULL UNIQUE REFERENCES borrow_items(id),
        outcome TEXT NOT NULL
            CHECK (outcome IN ('available', 'maintenance', 'reported_lost')),
        condition_note TEXT
    );

    CREATE TABLE lost_cases (
        id INTEGER PRIMARY KEY,
        equipment_unit_id INTEGER NOT NULL REFERENCES equipment_units(id),
        borrow_item_id INTEGER NOT NULL UNIQUE REFERENCES borrow_items(id),
        reported_at TEXT NOT NULL,
        assessed_value NUMERIC CHECK (assessed_value IS NULL OR assessed_value >= 0),
        approved_compensation NUMERIC
            CHECK (approved_compensation IS NULL OR approved_compensation >= 0),
        resolution TEXT
            CHECK (resolution IS NULL OR resolution IN ('recovered', 'replaced', 'compensated', 'waived')),
        approved_by_staff_id INTEGER REFERENCES staff(id),
        resolved_at TEXT,
        note TEXT
    );

    CREATE TABLE inventory_adjustments (
        id INTEGER PRIMARY KEY,
        equipment_unit_id INTEGER NOT NULL REFERENCES equipment_units(id),
        action TEXT NOT NULL
            CHECK (action IN ('acquire', 'retire', 'relocate', 'repair_complete')),
        reason TEXT NOT NULL,
        staff_id INTEGER NOT NULL REFERENCES staff(id),
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    );

    CREATE TABLE audit_logs (
        id INTEGER PRIMARY KEY,
        entity_type TEXT NOT NULL,
        entity_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        before_json TEXT,
        after_json TEXT,
        reason TEXT NOT NULL,
        staff_id INTEGER NOT NULL REFERENCES staff(id),
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    );
    """,
    """
    ALTER TABLE return_items
    ADD COLUMN location_id INTEGER REFERENCES locations(id);
    """,
    """
    ALTER TABLE lost_cases
    ADD COLUMN replacement_unit_id INTEGER REFERENCES equipment_units(id);
    """,
    """
    CREATE TRIGGER audit_logs_no_update
    BEFORE UPDATE ON audit_logs
    BEGIN
        SELECT RAISE(ABORT, 'audit logs are append-only');
    END;

    CREATE TRIGGER audit_logs_no_delete
    BEFORE DELETE ON audit_logs
    BEGIN
        SELECT RAISE(ABORT, 'audit logs are append-only');
    END;
    """,
    """
    CREATE TABLE equipment_categories (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL COLLATE NOCASE UNIQUE,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    );

    INSERT OR IGNORE INTO equipment_categories(name)
    SELECT DISTINCT TRIM(category)
    FROM equipment
    WHERE category IS NOT NULL AND TRIM(category) <> '';

    ALTER TABLE equipment
    ADD COLUMN category_id INTEGER REFERENCES equipment_categories(id);

    UPDATE equipment
    SET category_id = (
        SELECT id
        FROM equipment_categories
        WHERE name = equipment.category COLLATE NOCASE
    )
    WHERE category IS NOT NULL AND TRIM(category) <> '';
    """,
)


def initialize_database(database_path: str | Path | None = None) -> None:
    """Apply each pending schema migration exactly once."""
    with connection(database_path) as database:
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
            """
        )
        applied_versions = {
            row["version"]
            for row in database.execute("SELECT version FROM schema_migrations")
        }

        for version, migration in enumerate(MIGRATIONS, start=1):
            if version in applied_versions:
                continue
            try:
                database.executescript("BEGIN IMMEDIATE;\n" + migration)
                database.execute(
                    "INSERT INTO schema_migrations(version) VALUES (?)", (version,)
                )
                database.commit()
            except Exception:
                database.rollback()
                raise
