from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from app.database import (
    MIGRATIONS,
    bangkok_date,
    bangkok_today,
    connect,
    get_database_path,
    initialize_database,
)


def test_database_path_comes_from_environment(monkeypatch, tmp_path) -> None:
    expected = tmp_path / "configured.sqlite3"
    monkeypatch.setenv("APP_DB_PATH", str(expected))

    assert get_database_path() == expected


def test_initialize_is_idempotent_and_enables_foreign_keys(tmp_path) -> None:
    database_path = tmp_path / "database.sqlite3"

    initialize_database(database_path)
    initialize_database(database_path)

    with connect(database_path) as database:
        assert database.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        versions = database.execute(
            "SELECT version FROM schema_migrations"
        ).fetchall()
        assert [row["version"] for row in versions] == [1, 2, 3, 4, 5, 6]
        assert database.execute(
            "SELECT name FROM equipment_categories ORDER BY name"
        ).fetchall() == []

        with pytest.raises(sqlite3.IntegrityError):
            database.execute(
                """
                INSERT INTO equipment_units(asset_code, equipment_id, acquired_at)
                VALUES ('UNIT-001', 999, '2026-08-07')
                """
            )


def test_schema_constraints_are_enforced(tmp_path) -> None:
    database_path = tmp_path / "constraints.sqlite3"
    initialize_database(database_path)

    with connect(database_path) as database:
        database.execute(
            "INSERT INTO locations(location_code, room) VALUES ('LAB-1', '101')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            database.execute(
                "INSERT INTO locations(location_code, room) VALUES ('LAB-1', '102')"
            )
        with pytest.raises(sqlite3.IntegrityError):
            database.execute(
                "INSERT INTO locations(location_code, room, status) VALUES ('LAB-2', '102', 'deleted')"
            )


def test_data_persists_after_connection_restart(tmp_path) -> None:
    database_path = tmp_path / "persistent.sqlite3"
    initialize_database(database_path)

    with connect(database_path) as database:
        database.execute(
            "INSERT INTO locations(location_code, room) VALUES ('STORE', 'A1')"
        )
        database.commit()

    with connect(database_path) as database:
        row = database.execute(
            "SELECT room FROM locations WHERE location_code = 'STORE'"
        ).fetchone()

    assert database_path.is_file()
    assert row["room"] == "A1"


def test_timestamps_are_utc_and_business_dates_use_bangkok(tmp_path) -> None:
    database_path = tmp_path / "time.sqlite3"
    initialize_database(database_path)

    with connect(database_path) as database:
        database.execute(
            "INSERT INTO staff(staff_code, full_name) VALUES ('STAFF-1', 'Test Staff')"
        )
        created_at = database.execute(
            "SELECT created_at FROM staff WHERE staff_code = 'STAFF-1'"
        ).fetchone()[0]

    assert created_at.endswith("Z")
    assert bangkok_today(datetime(2026, 8, 7, 18, 0, tzinfo=timezone.utc)).isoformat() == "2026-08-08"
    assert bangkok_date("2026-08-07T18:00:00.000Z").isoformat() == "2026-08-08"


def test_existing_version_one_database_upgrades_through_all_migrations(tmp_path) -> None:
    database_path = tmp_path / "upgrade.sqlite3"
    with connect(database_path) as database:
        database.execute(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
            """
        )
        database.executescript(MIGRATIONS[0])
        database.execute("INSERT INTO schema_migrations(version) VALUES (1)")
        database.commit()

    initialize_database(database_path)

    with connect(database_path) as database:
        versions = database.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        return_item_columns = {
            row["name"] for row in database.execute("PRAGMA table_info(return_items)")
        }
        lost_case_columns = {
            row["name"] for row in database.execute("PRAGMA table_info(lost_cases)")
        }
        equipment_columns = {
            row["name"] for row in database.execute("PRAGMA table_info(equipment)")
        }
        audit_triggers = {
            row["name"]
            for row in database.execute(
                "SELECT name FROM sqlite_master WHERE type = 'trigger'"
            )
        }

    assert [row["version"] for row in versions] == [1, 2, 3, 4, 5, 6]
    assert "location_id" in return_item_columns
    assert "replacement_unit_id" in lost_case_columns
    assert "category_id" in equipment_columns
    assert audit_triggers == {"audit_logs_no_update", "audit_logs_no_delete"}
