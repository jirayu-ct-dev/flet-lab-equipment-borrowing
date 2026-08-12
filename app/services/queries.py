from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from app.contracts import (
    LoanQueryFilter,
    LoanQueryState,
    LoanStatus,
    LoanSummary,
)
from app.database import bangkok_today, connection, utc_now
from app.errors import ValidationError
from app.repositories import LoanQueryRepository
from app.repositories.queries import LoanQueryRecord


class SQLiteLoanQueryService:
    def __init__(
        self,
        database_path: str | Path,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.database_path = database_path
        self.clock = clock

    def search(
        self, filters: LoanQueryFilter = LoanQueryFilter()
    ) -> list[LoanSummary]:
        if (
            filters.borrow_date_from is not None
            and filters.borrow_date_to is not None
            and filters.borrow_date_from > filters.borrow_date_to
        ):
            raise ValidationError(
                "borrow_date_from must not be after borrow_date_to",
                field="borrow_date_from",
            )
        today = bangkok_today(self.clock())
        with connection(self.database_path) as database:
            records = LoanQueryRepository(database).search(filters)

        summaries = [self._summary(record, today) for record in records]
        if filters.state is not None:
            summaries = [
                summary
                for summary in summaries
                if filters.state in summary.states
            ]
        return summaries

    @staticmethod
    def _summary(record: LoanQueryRecord, today: date) -> LoanSummary:
        states: list[LoanQueryState] = []
        is_active = (
            record.status is LoanStatus.ACTIVE
            and record.outstanding_item_count > 0
        )
        if is_active:
            states.append(LoanQueryState.ACTIVE)
            if record.resolved_item_count > 0:
                states.append(LoanQueryState.PARTIAL)
            days_until_due = (record.due_date - today).days
            if days_until_due == 0:
                states.append(LoanQueryState.DUE_TODAY)
            elif 1 <= days_until_due <= 3:
                states.append(LoanQueryState.DUE_SOON)
            elif days_until_due < 0:
                states.append(LoanQueryState.OVERDUE)

        return LoanSummary(
            id=record.id,
            transaction_code=record.transaction_code,
            borrower_id=record.borrower_id,
            borrower_code=record.borrower_code,
            borrower_name=record.borrower_name,
            borrow_date=record.borrow_date,
            due_date=record.due_date,
            status=record.status,
            item_count=record.item_count,
            resolved_item_count=record.resolved_item_count,
            outstanding_item_count=record.outstanding_item_count,
            states=tuple(states),
        )
