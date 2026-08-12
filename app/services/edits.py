from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.contracts import (
    AuditLog,
    ChangeLoanBorrower,
    EditLoanDetails,
    Loan,
    LoanStatus,
    RecordStatus,
    ReplaceLoanUnit,
    UnitStatus,
)
from app.database import connection, utc_now
from app.errors import (
    BorrowItemNotInLoan,
    InactiveRecordError,
    LoanNotActive,
    NotFoundError,
    ReturnAlreadyRecorded,
    UnitNotAvailable,
    ValidationError,
)
from app.repositories import (
    AuditLogRepository,
    LoanEditRepository,
    LoanRepository,
    MasterDataRepository,
    ReturnRepository,
)


class SQLiteLoanEditService:
    def __init__(
        self,
        database_path: str | Path,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.database_path = database_path
        self.clock = clock

    @contextmanager
    def _write(
        self,
    ) -> Iterator[
        tuple[
            LoanEditRepository,
            AuditLogRepository,
            LoanRepository,
            MasterDataRepository,
            ReturnRepository,
        ]
    ]:
        with connection(self.database_path) as database:
            database.execute("BEGIN IMMEDIATE")
            try:
                yield (
                    LoanEditRepository(database),
                    AuditLogRepository(database),
                    LoanRepository(database),
                    MasterDataRepository(database),
                    ReturnRepository(database),
                )
                database.commit()
            except Exception:
                database.rollback()
                raise

    def edit_details(self, loan_id: int, command: EditLoanDetails) -> Loan:
        reason = self._reason(command.reason)
        timestamp = self._timestamp()
        with self._write() as (edits, audit, loans, master_data, _):
            loan = self._active_loan(loans, loan_id)
            self._active_staff(master_data, command.performed_by_staff_id)
            if command.due_date < loan.borrow_date:
                raise ValidationError(
                    "due_date must not be before borrow_date", field="due_date"
                )
            before = {
                "due_date": loan.due_date.isoformat(),
                "purpose": loan.purpose,
                "note": loan.note,
            }
            if not edits.edit_details(
                loan_id,
                due_date=command.due_date,
                purpose=command.purpose,
                note=command.note,
                updated_at=timestamp,
            ):
                raise LoanNotActive(loan_id, loan.status.value)
            after = {
                "due_date": command.due_date.isoformat(),
                "purpose": command.purpose,
                "note": command.note,
            }
            audit.append(
                entity_type="borrow_transaction",
                entity_id=loan_id,
                action="edit_details",
                before=before,
                after=after,
                reason=reason,
                staff_id=command.performed_by_staff_id,
                created_at=timestamp,
            )
            updated = loans.get(loan_id)
            assert updated is not None
            return updated

    def change_borrower(
        self, loan_id: int, command: ChangeLoanBorrower
    ) -> Loan:
        reason = self._reason(command.reason)
        timestamp = self._timestamp()
        with self._write() as (edits, audit, loans, master_data, _):
            loan = self._active_loan(loans, loan_id)
            self._active_staff(master_data, command.performed_by_staff_id)
            borrower = master_data.get_borrower(command.borrower_id)
            if borrower is None:
                raise NotFoundError("borrower", command.borrower_id)
            if borrower.status is not RecordStatus.ACTIVE:
                raise InactiveRecordError("borrower", borrower.id)
            if not edits.change_borrower(loan_id, borrower.id, timestamp):
                raise LoanNotActive(loan_id, loan.status.value)
            audit.append(
                entity_type="borrow_transaction",
                entity_id=loan_id,
                action="change_borrower",
                before={"borrower_id": loan.borrower_id},
                after={"borrower_id": borrower.id},
                reason=reason,
                staff_id=command.performed_by_staff_id,
                created_at=timestamp,
            )
            updated = loans.get(loan_id)
            assert updated is not None
            return updated

    def replace_unit(self, loan_id: int, command: ReplaceLoanUnit) -> Loan:
        reason = self._reason(command.reason)
        timestamp = self._timestamp()
        with self._write() as (edits, audit, loans, master_data, returns):
            loan = self._active_loan(loans, loan_id)
            self._active_staff(master_data, command.performed_by_staff_id)
            self._active_location(master_data, command.returned_location_id)

            borrow_item = returns.get_borrow_item(command.borrow_item_id)
            if borrow_item is None or borrow_item.loan_id != loan_id:
                raise BorrowItemNotInLoan(command.borrow_item_id, loan_id)
            if borrow_item.return_item_id is not None:
                raise ReturnAlreadyRecorded(command.borrow_item_id)
            old_unit = master_data.get_unit(borrow_item.equipment_unit_id)
            assert old_unit is not None
            if old_unit.status is not UnitStatus.BORROWED:
                raise UnitNotAvailable(old_unit.id, old_unit.status.value)

            new_unit = master_data.get_unit(command.new_unit_id)
            if new_unit is None:
                raise NotFoundError("equipment_unit", command.new_unit_id)
            if new_unit.status is not UnitStatus.AVAILABLE:
                raise UnitNotAvailable(new_unit.id, new_unit.status.value)
            if not loans.mark_unit_borrowed_if_available(new_unit.id):
                current = master_data.get_unit(new_unit.id)
                raise UnitNotAvailable(
                    new_unit.id, current.status.value if current else "not_found"
                )

            master_data.transition_unit(
                old_unit.id, UnitStatus.AVAILABLE, command.returned_location_id
            )
            if not edits.replace_borrow_item_unit(command.borrow_item_id, new_unit.id):
                raise BorrowItemNotInLoan(command.borrow_item_id, loan_id)
            audit.append(
                entity_type="borrow_transaction",
                entity_id=loan_id,
                action="replace_unit",
                before={
                    "borrow_item_id": command.borrow_item_id,
                    "equipment_unit_id": old_unit.id,
                    "asset_code": old_unit.asset_code,
                },
                after={
                    "borrow_item_id": command.borrow_item_id,
                    "equipment_unit_id": new_unit.id,
                    "asset_code": new_unit.asset_code,
                },
                reason=reason,
                staff_id=command.performed_by_staff_id,
                created_at=timestamp,
            )
            updated = loans.get(loan_id)
            assert updated is not None
            return updated

    @staticmethod
    def _active_loan(repository: LoanRepository, loan_id: int) -> Loan:
        loan = repository.get(loan_id)
        if loan is None:
            raise NotFoundError("loan", loan_id)
        if loan.status is not LoanStatus.ACTIVE:
            raise LoanNotActive(loan_id, loan.status.value)
        return loan

    @staticmethod
    def _active_staff(repository: MasterDataRepository, staff_id: int) -> None:
        staff = repository.get_staff(staff_id)
        if staff is None:
            raise NotFoundError("staff", staff_id)
        if staff.status is not RecordStatus.ACTIVE:
            raise InactiveRecordError("staff", staff_id)

    @staticmethod
    def _active_location(
        repository: MasterDataRepository, location_id: int
    ) -> None:
        location = repository.get_location(location_id)
        if location is None:
            raise NotFoundError("location", location_id)
        if location.status is not RecordStatus.ACTIVE:
            raise InactiveRecordError("location", location_id)

    @staticmethod
    def _reason(value: str) -> str:
        reason = value.strip()
        if not reason:
            raise ValidationError("reason is required", field="reason")
        return reason

    def _timestamp(self) -> str:
        value = self.clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError("clock must return an aware datetime")
        return (
            value.astimezone(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )


class SQLiteAuditLogService:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = database_path

    def list_for_entity(self, entity_type: str, entity_id: int) -> list[AuditLog]:
        if not entity_type.strip():
            raise ValidationError("entity_type is required", field="entity_type")
        with connection(self.database_path) as database:
            return AuditLogRepository(database).list_for_entity(entity_type, entity_id)
