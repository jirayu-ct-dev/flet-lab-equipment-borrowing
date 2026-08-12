from __future__ import annotations

import sqlite3
from datetime import date, datetime

from app.contracts import CreateDraftLoan, Loan, LoanItem, LoanStatus, UnitStatus


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class LoanRepository:
    """SQL persistence for loan drafts and confirmation."""

    def __init__(self, database: sqlite3.Connection) -> None:
        self.database = database

    def create_draft(self, command: CreateDraftLoan) -> Loan:
        cursor = self.database.execute(
            """
            INSERT INTO borrow_transactions(
                transaction_code, borrower_id, borrow_date, due_date, purpose,
                recorded_by_staff_id, status, note
            ) VALUES (?, ?, ?, ?, ?, ?, 'draft', ?)
            """,
            (
                command.transaction_code,
                command.borrower_id,
                command.borrow_date.isoformat(),
                command.due_date.isoformat(),
                command.purpose,
                command.recorded_by_staff_id,
                command.note,
            ),
        )
        loan_id = cursor.lastrowid
        self.database.executemany(
            """
            INSERT INTO borrow_items(transaction_id, equipment_unit_id)
            VALUES (?, ?)
            """,
            [(loan_id, unit_id) for unit_id in command.unit_ids],
        )
        loan = self.get(loan_id)
        assert loan is not None
        return loan

    def get(self, loan_id: int) -> Loan | None:
        row = self.database.execute(
            "SELECT * FROM borrow_transactions WHERE id = ?", (loan_id,)
        ).fetchone()
        if row is None:
            return None
        item_rows = self.database.execute(
            """
            SELECT bi.id, eu.id AS equipment_unit_id, eu.asset_code,
                   eu.status AS unit_status
            FROM borrow_items AS bi
            JOIN equipment_units AS eu ON eu.id = bi.equipment_unit_id
            WHERE bi.transaction_id = ?
            ORDER BY bi.id
            """,
            (loan_id,),
        ).fetchall()
        return Loan(
            id=row["id"],
            transaction_code=row["transaction_code"],
            borrower_id=row["borrower_id"],
            borrow_date=date.fromisoformat(row["borrow_date"]),
            due_date=date.fromisoformat(row["due_date"]),
            purpose=row["purpose"],
            recorded_by_staff_id=row["recorded_by_staff_id"],
            status=LoanStatus(row["status"]),
            note=row["note"],
            items=tuple(
                LoanItem(
                    id=item["id"],
                    equipment_unit_id=item["equipment_unit_id"],
                    asset_code=item["asset_code"],
                    unit_status=UnitStatus(item["unit_status"]),
                )
                for item in item_rows
            ),
            created_at=_timestamp(row["created_at"]),
            updated_at=_timestamp(row["updated_at"]),
        )

    def mark_unit_borrowed_if_available(self, unit_id: int) -> bool:
        cursor = self.database.execute(
            """
            UPDATE equipment_units
            SET status = 'borrowed', current_location_id = NULL,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ? AND status = 'available'
            """,
            (unit_id,),
        )
        return cursor.rowcount == 1

    def activate_if_draft(self, loan_id: int) -> bool:
        cursor = self.database.execute(
            """
            UPDATE borrow_transactions
            SET status = 'active',
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ? AND status = 'draft'
            """,
            (loan_id,),
        )
        return cursor.rowcount == 1
