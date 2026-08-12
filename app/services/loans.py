from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.contracts import (
    CreateDraftLoan,
    EquipmentUnit,
    Loan,
    LoanStatus,
    RecordStatus,
    UnitStatus,
)
from app.database import connection
from app.errors import (
    DuplicateCodeError,
    InactiveRecordError,
    LoanNotDraft,
    NotFoundError,
    UnitNotAvailable,
    ValidationError,
)
from app.repositories import LoanRepository, MasterDataRepository


class SQLiteLoanService:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = database_path

    @contextmanager
    def _write(self) -> Iterator[tuple[LoanRepository, MasterDataRepository]]:
        with connection(self.database_path) as database:
            database.execute("BEGIN IMMEDIATE")
            try:
                yield LoanRepository(database), MasterDataRepository(database)
                database.commit()
            except Exception:
                database.rollback()
                raise

    def create_draft(self, command: CreateDraftLoan) -> Loan:
        transaction_code = command.transaction_code.strip()
        if not transaction_code:
            raise ValidationError(
                "transaction_code is required", field="transaction_code"
            )
        if command.due_date < command.borrow_date:
            raise ValidationError(
                "due_date must not be before borrow_date", field="due_date"
            )
        if not command.unit_ids:
            raise ValidationError("At least one unit is required", field="unit_ids")
        if len(set(command.unit_ids)) != len(command.unit_ids):
            raise ValidationError("unit_ids must not contain duplicates", field="unit_ids")

        try:
            with self._write() as (loans, master_data):
                self._require_active_borrower(master_data, command.borrower_id)
                self._require_active_staff(master_data, command.recorded_by_staff_id)
                for unit_id in command.unit_ids:
                    self._require_available_unit(master_data, unit_id)
                return loans.create_draft(command)
        except sqlite3.IntegrityError as error:
            if ".transaction_code" in str(error):
                raise DuplicateCodeError(
                    "transaction_code", command.transaction_code
                ) from error
            raise

    def get(self, loan_id: int) -> Loan:
        with connection(self.database_path) as database:
            loan = LoanRepository(database).get(loan_id)
        if loan is None:
            raise NotFoundError("loan", loan_id)
        return loan

    def confirm_loan(self, loan_id: int) -> Loan:
        with self._write() as (loans, master_data):
            loan = loans.get(loan_id)
            if loan is None:
                raise NotFoundError("loan", loan_id)
            if loan.status is not LoanStatus.DRAFT:
                raise LoanNotDraft(loan_id, loan.status.value)

            self._require_active_borrower(master_data, loan.borrower_id)
            self._require_active_staff(master_data, loan.recorded_by_staff_id)
            for item in loan.items:
                unit = self._require_available_unit(
                    master_data, item.equipment_unit_id
                )
                if not loans.mark_unit_borrowed_if_available(unit.id):
                    current = master_data.get_unit(unit.id)
                    current_status = (
                        current.status.value if current else "not_found"
                    )
                    raise UnitNotAvailable(unit.id, current_status)

            if not loans.activate_if_draft(loan_id):
                raise LoanNotDraft(loan_id, LoanStatus.DRAFT.value)
            confirmed = loans.get(loan_id)
            assert confirmed is not None
            return confirmed

    @staticmethod
    def _require_active_borrower(
        repository: MasterDataRepository, borrower_id: int
    ) -> None:
        borrower = repository.get_borrower(borrower_id)
        if borrower is None:
            raise NotFoundError("borrower", borrower_id)
        if borrower.status is not RecordStatus.ACTIVE:
            raise InactiveRecordError("borrower", borrower_id)

    @staticmethod
    def _require_active_staff(repository: MasterDataRepository, staff_id: int) -> None:
        staff = repository.get_staff(staff_id)
        if staff is None:
            raise NotFoundError("staff", staff_id)
        if staff.status is not RecordStatus.ACTIVE:
            raise InactiveRecordError("staff", staff_id)

    @staticmethod
    def _require_available_unit(
        repository: MasterDataRepository, unit_id: int
    ) -> EquipmentUnit:
        unit = repository.get_unit(unit_id)
        if unit is None:
            raise NotFoundError("equipment_unit", unit_id)
        if unit.status is not UnitStatus.AVAILABLE:
            raise UnitNotAvailable(unit_id, unit.status.value)
        return unit
