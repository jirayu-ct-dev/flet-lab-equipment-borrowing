from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from app.contracts import LoanQueryFilter, LoanStatus


@dataclass(frozen=True, slots=True)
class LoanQueryRecord:
    id: int
    transaction_code: str
    borrower_id: int
    borrower_code: str
    borrower_name: str
    borrow_date: date
    due_date: date
    status: LoanStatus
    item_count: int
    resolved_item_count: int
    outstanding_item_count: int


class LoanQueryRepository:
    def __init__(self, database: sqlite3.Connection) -> None:
        self.database = database

    def search(self, filters: LoanQueryFilter) -> list[LoanQueryRecord]:
        clauses: list[str] = []
        values: list[object] = []
        if filters.borrower_query:
            clauses.append("(b.borrower_code LIKE ? OR b.full_name LIKE ?)")
            pattern = f"%{filters.borrower_query}%"
            values.extend([pattern, pattern])
        if filters.equipment_query:
            clauses.append(
                """
                EXISTS (
                    SELECT 1 FROM borrow_items AS search_bi
                    JOIN equipment_units AS search_eu
                      ON search_eu.id = search_bi.equipment_unit_id
                    JOIN equipment AS search_e
                      ON search_e.id = search_eu.equipment_id
                    WHERE search_bi.transaction_id = bt.id
                      AND (
                          search_e.equipment_code LIKE ?
                          OR search_e.name LIKE ?
                          OR search_e.category LIKE ?
                          OR search_e.model LIKE ?
                      )
                )
                """
            )
            pattern = f"%{filters.equipment_query}%"
            values.extend([pattern] * 4)
        if filters.asset_code:
            clauses.append(
                """
                EXISTS (
                    SELECT 1 FROM borrow_items AS asset_bi
                    JOIN equipment_units AS asset_eu
                      ON asset_eu.id = asset_bi.equipment_unit_id
                    WHERE asset_bi.transaction_id = bt.id
                      AND asset_eu.asset_code LIKE ?
                )
                """
            )
            values.append(f"%{filters.asset_code}%")
        if filters.borrow_date_from:
            clauses.append("bt.borrow_date >= ?")
            values.append(filters.borrow_date_from.isoformat())
        if filters.borrow_date_to:
            clauses.append("bt.borrow_date <= ?")
            values.append(filters.borrow_date_to.isoformat())
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        rows = self.database.execute(
            f"""
            SELECT
                bt.id,
                bt.transaction_code,
                bt.borrower_id,
                b.borrower_code,
                b.full_name AS borrower_name,
                bt.borrow_date,
                bt.due_date,
                bt.status,
                COUNT(bi.id) AS item_count,
                COALESCE(SUM(
                    CASE
                        WHEN ri.id IS NOT NULL
                         AND (ri.outcome <> 'reported_lost' OR lc.resolution IS NOT NULL)
                        THEN 1 ELSE 0
                    END
                ), 0) AS resolved_item_count
            FROM borrow_transactions AS bt
            JOIN borrowers AS b ON b.id = bt.borrower_id
            LEFT JOIN borrow_items AS bi ON bi.transaction_id = bt.id
            LEFT JOIN return_items AS ri ON ri.borrow_item_id = bi.id
            LEFT JOIN lost_cases AS lc ON lc.borrow_item_id = bi.id
            {where}
            GROUP BY bt.id
            ORDER BY bt.due_date, bt.id
            """,
            values,
        ).fetchall()
        records: list[LoanQueryRecord] = []
        for row in rows:
            item_count = row["item_count"]
            resolved_count = row["resolved_item_count"]
            records.append(
                LoanQueryRecord(
                    id=row["id"],
                    transaction_code=row["transaction_code"],
                    borrower_id=row["borrower_id"],
                    borrower_code=row["borrower_code"],
                    borrower_name=row["borrower_name"],
                    borrow_date=date.fromisoformat(row["borrow_date"]),
                    due_date=date.fromisoformat(row["due_date"]),
                    status=LoanStatus(row["status"]),
                    item_count=item_count,
                    resolved_item_count=resolved_count,
                    outstanding_item_count=item_count - resolved_count,
                )
            )
        return records
