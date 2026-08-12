from __future__ import annotations

import sqlite3
from datetime import datetime
from decimal import Decimal

from app.contracts import LostCase, LostResolution


def _decimal(value: object | None) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def _timestamp(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


class LostCaseRepository:
    def __init__(self, database: sqlite3.Connection) -> None:
        self.database = database

    def get(self, case_id: int) -> LostCase | None:
        row = self.database.execute(
            "SELECT * FROM lost_cases WHERE id = ?", (case_id,)
        ).fetchone()
        if row is None:
            return None
        reported_at = _timestamp(row["reported_at"])
        assert reported_at is not None
        return LostCase(
            id=row["id"],
            equipment_unit_id=row["equipment_unit_id"],
            borrow_item_id=row["borrow_item_id"],
            reported_at=reported_at,
            assessed_value=_decimal(row["assessed_value"]),
            approved_compensation=_decimal(row["approved_compensation"]),
            resolution=(
                LostResolution(row["resolution"]) if row["resolution"] else None
            ),
            approved_by_staff_id=row["approved_by_staff_id"],
            resolved_at=_timestamp(row["resolved_at"]),
            replacement_unit_id=row["replacement_unit_id"],
            note=row["note"],
        )

    def loan_id_for_case(self, case_id: int) -> int | None:
        row = self.database.execute(
            """
            SELECT bi.transaction_id
            FROM lost_cases AS lc
            JOIN borrow_items AS bi ON bi.id = lc.borrow_item_id
            WHERE lc.id = ?
            """,
            (case_id,),
        ).fetchone()
        return row[0] if row else None

    def resolve(
        self,
        case_id: int,
        *,
        assessed_value: Decimal,
        approved_compensation: Decimal,
        resolution: LostResolution,
        approved_by_staff_id: int,
        resolved_at: str,
        replacement_unit_id: int | None,
        note: str | None,
    ) -> bool:
        cursor = self.database.execute(
            """
            UPDATE lost_cases SET
                assessed_value = ?, approved_compensation = ?, resolution = ?,
                approved_by_staff_id = ?, resolved_at = ?,
                replacement_unit_id = ?, note = ?
            WHERE id = ? AND resolution IS NULL
            """,
            (
                str(assessed_value),
                str(approved_compensation),
                resolution.value,
                approved_by_staff_id,
                resolved_at,
                replacement_unit_id,
                note,
                case_id,
            ),
        )
        return cursor.rowcount == 1

    def add_audit_log(
        self,
        case_id: int,
        *,
        before_json: str,
        after_json: str,
        reason: str,
        staff_id: int,
        created_at: str,
    ) -> None:
        self.database.execute(
            """
            INSERT INTO audit_logs(
                entity_type, entity_id, action, before_json, after_json,
                reason, staff_id, created_at
            ) VALUES ('lost_case', ?, 'resolve', ?, ?, ?, ?, ?)
            """,
            (case_id, before_json, after_json, reason, staff_id, created_at),
        )
