from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from app.contracts import RecordReturn, ReturnEvent, ReturnItem, ReturnOutcome, UnitStatus


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True, slots=True)
class BorrowItemRecord:
    id: int
    loan_id: int
    equipment_unit_id: int
    unit_status: UnitStatus
    return_item_id: int | None


class ReturnRepository:
    """Append-only persistence for return events and their items."""

    def __init__(self, database: sqlite3.Connection) -> None:
        self.database = database

    def get_borrow_item(self, borrow_item_id: int) -> BorrowItemRecord | None:
        row = self.database.execute(
            """
            SELECT bi.id, bi.transaction_id AS loan_id, bi.equipment_unit_id,
                   eu.status AS unit_status, ri.id AS return_item_id
            FROM borrow_items AS bi
            JOIN equipment_units AS eu ON eu.id = bi.equipment_unit_id
            LEFT JOIN return_items AS ri ON ri.borrow_item_id = bi.id
            WHERE bi.id = ?
            """,
            (borrow_item_id,),
        ).fetchone()
        if row is None:
            return None
        return BorrowItemRecord(
            id=row["id"],
            loan_id=row["loan_id"],
            equipment_unit_id=row["equipment_unit_id"],
            unit_status=UnitStatus(row["unit_status"]),
            return_item_id=row["return_item_id"],
        )

    def create_event(self, command: RecordReturn, returned_at: str) -> int:
        cursor = self.database.execute(
            """
            INSERT INTO returns(
                transaction_id, returned_at, received_by_staff_id, note
            ) VALUES (?, ?, ?, ?)
            """,
            (
                command.loan_id,
                returned_at,
                command.received_by_staff_id,
                command.note,
            ),
        )
        return cursor.lastrowid

    def add_item(
        self,
        return_id: int,
        borrow_item_id: int,
        outcome: ReturnOutcome,
        location_id: int | None,
        condition_note: str | None,
    ) -> None:
        self.database.execute(
            """
            INSERT INTO return_items(
                return_id, borrow_item_id, outcome, condition_note, location_id
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                return_id,
                borrow_item_id,
                outcome.value,
                condition_note,
                location_id,
            ),
        )

    def open_lost_case(
        self,
        equipment_unit_id: int,
        borrow_item_id: int,
        reported_at: str,
        note: str | None,
    ) -> None:
        self.database.execute(
            """
            INSERT INTO lost_cases(
                equipment_unit_id, borrow_item_id, reported_at, note
            ) VALUES (?, ?, ?, ?)
            """,
            (equipment_unit_id, borrow_item_id, reported_at, note),
        )

    def unresolved_item_count(self, loan_id: int) -> int:
        return self.database.execute(
            """
            SELECT COUNT(*)
            FROM borrow_items AS bi
            LEFT JOIN return_items AS ri ON ri.borrow_item_id = bi.id
            LEFT JOIN lost_cases AS lc ON lc.borrow_item_id = bi.id
            WHERE bi.transaction_id = ?
              AND (
                  ri.id IS NULL
                  OR (ri.outcome = 'reported_lost' AND lc.resolution IS NULL)
              )
            """,
            (loan_id,),
        ).fetchone()[0]

    def complete_loan(self, loan_id: int) -> None:
        self.database.execute(
            """
            UPDATE borrow_transactions
            SET status = 'completed',
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ? AND status = 'active'
            """,
            (loan_id,),
        )

    def list_for_loan(self, loan_id: int) -> list[ReturnEvent]:
        rows = self.database.execute(
            """
            SELECT * FROM returns
            WHERE transaction_id = ?
            ORDER BY returned_at, id
            """,
            (loan_id,),
        ).fetchall()
        events: list[ReturnEvent] = []
        for row in rows:
            item_rows = self.database.execute(
                """
                SELECT ri.id, ri.borrow_item_id, bi.equipment_unit_id,
                       eu.asset_code, ri.outcome, ri.location_id,
                       ri.condition_note
                FROM return_items AS ri
                JOIN borrow_items AS bi ON bi.id = ri.borrow_item_id
                JOIN equipment_units AS eu ON eu.id = bi.equipment_unit_id
                WHERE ri.return_id = ?
                ORDER BY ri.id
                """,
                (row["id"],),
            ).fetchall()
            events.append(
                ReturnEvent(
                    id=row["id"],
                    loan_id=row["transaction_id"],
                    returned_at=_timestamp(row["returned_at"]),
                    received_by_staff_id=row["received_by_staff_id"],
                    note=row["note"],
                    items=tuple(
                        ReturnItem(
                            id=item["id"],
                            borrow_item_id=item["borrow_item_id"],
                            equipment_unit_id=item["equipment_unit_id"],
                            asset_code=item["asset_code"],
                            outcome=ReturnOutcome(item["outcome"]),
                            location_id=item["location_id"],
                            condition_note=item["condition_note"],
                        )
                        for item in item_rows
                    ),
                )
            )
        return events
