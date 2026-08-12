from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import timezone
from pathlib import Path
from typing import Iterator

from app.contracts import (
    LoanStatus,
    RecordReturn,
    RecordStatus,
    ReturnEvent,
    ReturnOutcome,
    UnitStatus,
)
from app.database import connection
from app.errors import (
    BorrowItemNotInLoan,
    InactiveRecordError,
    LoanNotActive,
    NotFoundError,
    ReturnAlreadyRecorded,
    UnitNotAvailable,
    ValidationError,
)
from app.repositories import LoanRepository, MasterDataRepository, ReturnRepository


class SQLiteReturnService:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = database_path

    @contextmanager
    def _write(
        self,
    ) -> Iterator[tuple[ReturnRepository, LoanRepository, MasterDataRepository]]:
        with connection(self.database_path) as database:
            database.execute("BEGIN IMMEDIATE")
            try:
                yield (
                    ReturnRepository(database),
                    LoanRepository(database),
                    MasterDataRepository(database),
                )
                database.commit()
            except Exception:
                database.rollback()
                raise

    def record_return(self, command: RecordReturn) -> ReturnEvent:
        if command.returned_at.tzinfo is None or command.returned_at.utcoffset() is None:
            raise ValidationError(
                "returned_at must be timezone-aware", field="returned_at"
            )
        if not command.items:
            raise ValidationError("At least one return item is required", field="items")
        item_ids = [item.borrow_item_id for item in command.items]
        if len(set(item_ids)) != len(item_ids):
            raise ValidationError(
                "items must not contain duplicate borrow_item_id values", field="items"
            )
        returned_at = (
            command.returned_at.astimezone(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )

        try:
            with self._write() as (returns, loans, master_data):
                loan = loans.get(command.loan_id)
                if loan is None:
                    raise NotFoundError("loan", command.loan_id)
                if loan.status is not LoanStatus.ACTIVE:
                    raise LoanNotActive(command.loan_id, loan.status.value)
                self._require_active_staff(master_data, command.received_by_staff_id)

                validated_items = []
                for item in command.items:
                    borrow_item = returns.get_borrow_item(item.borrow_item_id)
                    if borrow_item is None or borrow_item.loan_id != command.loan_id:
                        raise BorrowItemNotInLoan(
                            item.borrow_item_id, command.loan_id
                        )
                    if borrow_item.return_item_id is not None:
                        raise ReturnAlreadyRecorded(item.borrow_item_id)
                    if borrow_item.unit_status is not UnitStatus.BORROWED:
                        raise UnitNotAvailable(
                            borrow_item.equipment_unit_id,
                            borrow_item.unit_status.value,
                        )
                    if item.outcome is ReturnOutcome.REPORTED_LOST:
                        if item.location_id is not None:
                            raise ValidationError(
                                "reported_lost items must not have a location",
                                field="location_id",
                            )
                    else:
                        if item.location_id is None:
                            raise ValidationError(
                                "location_id is required for returned items",
                                field="location_id",
                            )
                        self._require_active_location(master_data, item.location_id)
                    validated_items.append((item, borrow_item))

                return_id = returns.create_event(command, returned_at)
                for item, borrow_item in validated_items:
                    returns.add_item(
                        return_id,
                        item.borrow_item_id,
                        item.outcome,
                        item.location_id,
                        item.condition_note,
                    )
                    master_data.transition_unit(
                        borrow_item.equipment_unit_id,
                        UnitStatus(item.outcome.value),
                        item.location_id,
                    )
                    if item.outcome is ReturnOutcome.REPORTED_LOST:
                        returns.open_lost_case(
                            borrow_item.equipment_unit_id,
                            item.borrow_item_id,
                            returned_at,
                            item.condition_note,
                        )

                if returns.unresolved_item_count(command.loan_id) == 0:
                    returns.complete_loan(command.loan_id)
                events = returns.list_for_loan(command.loan_id)
                return next(event for event in events if event.id == return_id)
        except sqlite3.IntegrityError as error:
            if "return_items.borrow_item_id" in str(error):
                raise ReturnAlreadyRecorded(item_ids[0]) from error
            raise

    def list_for_loan(self, loan_id: int) -> list[ReturnEvent]:
        with connection(self.database_path) as database:
            loans = LoanRepository(database)
            if loans.get(loan_id) is None:
                raise NotFoundError("loan", loan_id)
            return ReturnRepository(database).list_for_loan(loan_id)

    @staticmethod
    def _require_active_staff(
        repository: MasterDataRepository, staff_id: int
    ) -> None:
        staff = repository.get_staff(staff_id)
        if staff is None:
            raise NotFoundError("staff", staff_id)
        if staff.status is not RecordStatus.ACTIVE:
            raise InactiveRecordError("staff", staff_id)

    @staticmethod
    def _require_active_location(
        repository: MasterDataRepository, location_id: int
    ) -> None:
        location = repository.get_location(location_id)
        if location is None:
            raise NotFoundError("location", location_id)
        if location.status is not RecordStatus.ACTIVE:
            raise InactiveRecordError("location", location_id)
