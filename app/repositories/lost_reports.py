from __future__ import annotations

import sqlite3
from datetime import datetime

from app.contracts import CreateLostReport, LostReport, LostReportStatus


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _optional_timestamp(value: str | None) -> datetime | None:
    return _timestamp(value) if value else None


def _lost_report(row: sqlite3.Row) -> LostReport:
    return LostReport(
        id=row["id"],
        borrower_id=row["borrower_id"],
        equipment_unit_id=row["equipment_unit_id"],
        reported_at=_timestamp(row["reported_at"]),
        lost_date=row["lost_date"],
        location=row["location"],
        description=row["description"],
        status=LostReportStatus(row["status"]),
        reviewed_by_staff_id=row["reviewed_by_staff_id"],
        reviewed_at=_optional_timestamp(row["reviewed_at"]),
        review_note=row["review_note"],
        created_at=_timestamp(row["created_at"]),
    )


class LostReportRepository:
    def __init__(self, database: sqlite3.Connection) -> None:
        self.database = database

    def create(self, command: CreateLostReport, reported_at: str) -> LostReport:
        cursor = self.database.execute(
            """
            INSERT INTO lost_reports(
                borrower_id, equipment_unit_id, reported_at,
                lost_date, location, description
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                command.borrower_id,
                command.equipment_unit_id,
                reported_at,
                command.lost_date,
                command.location,
                command.description,
            ),
        )
        report = self.get(cursor.lastrowid)
        assert report is not None
        return report

    def get(self, report_id: int) -> LostReport | None:
        row = self.database.execute(
            "SELECT * FROM lost_reports WHERE id = ?", (report_id,)
        ).fetchone()
        return _lost_report(row) if row is not None else None

    def list_pending(self) -> list[LostReport]:
        rows = self.database.execute(
            """
            SELECT * FROM lost_reports
            WHERE status = 'pending'
            ORDER BY reported_at, id
            """
        ).fetchall()
        return [_lost_report(row) for row in rows]

    def list_for_borrower(self, borrower_id: int) -> list[LostReport]:
        rows = self.database.execute(
            """
            SELECT * FROM lost_reports
            WHERE borrower_id = ?
            ORDER BY reported_at DESC, id DESC
            """,
            (borrower_id,),
        ).fetchall()
        return [_lost_report(row) for row in rows]

    def review(
        self,
        report_id: int,
        *,
        status: LostReportStatus,
        reviewed_by_staff_id: int,
        reviewed_at: str,
        review_note: str | None,
    ) -> bool:
        cursor = self.database.execute(
            """
            UPDATE lost_reports SET
                status = ?, reviewed_by_staff_id = ?, reviewed_at = ?,
                review_note = ?
            WHERE id = ? AND status = 'pending'
            """,
            (status.value, reviewed_by_staff_id, reviewed_at, review_note, report_id),
        )
        return cursor.rowcount == 1

    def open_borrow_item_id(self, equipment_unit_id: int) -> int | None:
        row = self.database.execute(
            """
            SELECT bi.id
            FROM borrow_items bi
            JOIN borrow_transactions bt ON bt.id = bi.transaction_id
            LEFT JOIN return_items ri ON ri.borrow_item_id = bi.id
            WHERE bi.equipment_unit_id = ?
              AND bt.status IN ('draft','active')
              AND ri.id IS NULL
            LIMIT 1
            """,
            (equipment_unit_id,),
        ).fetchone()
        return row[0] if row else None
