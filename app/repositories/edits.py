from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime

from app.contracts import AuditLog


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class LoanEditRepository:
    def __init__(self, database: sqlite3.Connection) -> None:
        self.database = database

    def edit_details(
        self,
        loan_id: int,
        *,
        due_date: date,
        purpose: str | None,
        note: str | None,
        updated_at: str,
    ) -> bool:
        cursor = self.database.execute(
            """
            UPDATE borrow_transactions
            SET due_date = ?, purpose = ?, note = ?, updated_at = ?
            WHERE id = ? AND status = 'active'
            """,
            (due_date.isoformat(), purpose, note, updated_at, loan_id),
        )
        return cursor.rowcount == 1

    def change_borrower(
        self, loan_id: int, borrower_id: int, updated_at: str
    ) -> bool:
        cursor = self.database.execute(
            """
            UPDATE borrow_transactions
            SET borrower_id = ?, updated_at = ?
            WHERE id = ? AND status = 'active'
            """,
            (borrower_id, updated_at, loan_id),
        )
        return cursor.rowcount == 1

    def replace_borrow_item_unit(self, borrow_item_id: int, new_unit_id: int) -> bool:
        cursor = self.database.execute(
            """
            UPDATE borrow_items SET equipment_unit_id = ? WHERE id = ?
            """,
            (new_unit_id, borrow_item_id),
        )
        return cursor.rowcount == 1


class AuditLogRepository:
    def __init__(self, database: sqlite3.Connection) -> None:
        self.database = database

    def append(
        self,
        *,
        entity_type: str,
        entity_id: int,
        action: str,
        before: dict[str, object] | None,
        after: dict[str, object] | None,
        reason: str,
        staff_id: int,
        created_at: str,
    ) -> None:
        self.database.execute(
            """
            INSERT INTO audit_logs(
                entity_type, entity_id, action, before_json, after_json,
                reason, staff_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity_type,
                entity_id,
                action,
                json.dumps(before, sort_keys=True) if before is not None else None,
                json.dumps(after, sort_keys=True) if after is not None else None,
                reason,
                staff_id,
                created_at,
            ),
        )

    def list_for_entity(self, entity_type: str, entity_id: int) -> list[AuditLog]:
        rows = self.database.execute(
            """
            SELECT * FROM audit_logs
            WHERE entity_type = ? AND entity_id = ?
            ORDER BY created_at, id
            """,
            (entity_type, entity_id),
        ).fetchall()
        return [
            AuditLog(
                id=row["id"],
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                action=row["action"],
                before=json.loads(row["before_json"]) if row["before_json"] else None,
                after=json.loads(row["after_json"]) if row["after_json"] else None,
                reason=row["reason"],
                staff_id=row["staff_id"],
                created_at=_timestamp(row["created_at"]),
            )
            for row in rows
        ]
