from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest

from app.contracts import (
    AcquireUnit,
    CreateBorrower,
    CreateDraftLoan,
    CreateEquipment,
    CreateLocation,
    CreateStaff,
    LoanStatus,
    RecordStatus,
    UnitStatus,
    UpdateBorrower,
    UpdateStaff,
)
from app.database import connect, initialize_database
from app.errors import (
    DuplicateCodeError,
    InactiveRecordError,
    LoanNotDraft,
    UnitNotAvailable,
)
from app.services import (
    SQLiteBorrowerService,
    SQLiteEquipmentService,
    SQLiteLoanService,
    SQLiteLocationService,
    SQLiteStaffService,
    SQLiteUnitService,
)
from app.repositories import LoanRepository


@pytest.fixture
def loan_context(tmp_path):
    database_path = tmp_path / "loans.sqlite3"
    initialize_database(database_path)
    locations = SQLiteLocationService(database_path)
    equipment_service = SQLiteEquipmentService(database_path)
    staff_service = SQLiteStaffService(database_path)
    borrower_service = SQLiteBorrowerService(database_path)
    unit_service = SQLiteUnitService(database_path)

    location = locations.create(CreateLocation("LAB-1", "101"))
    equipment = equipment_service.create(CreateEquipment("EQ-1", "Microscope"))
    staff = staff_service.create(CreateStaff("ST-1", "Lab Staff"))
    borrower = borrower_service.create(CreateBorrower("BR-1", "Student One"))
    units = tuple(
        unit_service.acquire(
            AcquireUnit(
                asset_code=f"UNIT-{number}",
                equipment_id=equipment.id,
                acquired_at=date(2026, 8, 7),
                current_location_id=location.id,
                recorded_by_staff_id=staff.id,
                reason="Initial acquisition",
            )
        )
        for number in (1, 2)
    )
    return {
        "path": database_path,
        "loans": SQLiteLoanService(database_path),
        "borrowers": borrower_service,
        "staff": staff,
        "borrower": borrower,
        "units": units,
    }


def _draft(context, transaction_code: str, unit_ids: tuple[int, ...]):
    return context["loans"].create_draft(
        CreateDraftLoan(
            transaction_code=transaction_code,
            borrower_id=context["borrower"].id,
            recorded_by_staff_id=context["staff"].id,
            borrow_date=date(2026, 8, 7),
            due_date=date(2026, 8, 10),
            unit_ids=unit_ids,
            purpose="Lab class",
        )
    )


def test_create_and_confirm_multi_unit_loan_atomically(loan_context) -> None:
    unit_ids = tuple(unit.id for unit in loan_context["units"])
    draft = _draft(loan_context, "LOAN-1", unit_ids)

    confirmed = loan_context["loans"].confirm_loan(draft.id)

    assert draft.status is LoanStatus.DRAFT
    assert confirmed.status is LoanStatus.ACTIVE
    assert len(confirmed.items) == 2
    assert all(item.unit_status is UnitStatus.BORROWED for item in confirmed.items)
    with connect(loan_context["path"]) as database:
        locations = database.execute(
            "SELECT current_location_id FROM equipment_units ORDER BY id"
        ).fetchall()
    assert [row[0] for row in locations] == [None, None]


def test_create_and_confirm_rolls_back_new_loan_when_activation_fails(
    loan_context, monkeypatch
) -> None:
    command = CreateDraftLoan(
        transaction_code="LOAN-ATOMIC",
        borrower_id=loan_context["borrower"].id,
        recorded_by_staff_id=loan_context["staff"].id,
        borrow_date=date(2026, 8, 7),
        due_date=date(2026, 8, 10),
        unit_ids=tuple(unit.id for unit in loan_context["units"]),
        purpose="Lab class",
    )
    original = LoanRepository.mark_unit_borrowed_if_available
    calls = 0

    def fail_on_second_unit(repository, unit_id):
        nonlocal calls
        calls += 1
        if calls == 2:
            return False
        return original(repository, unit_id)

    monkeypatch.setattr(
        LoanRepository, "mark_unit_borrowed_if_available", fail_on_second_unit
    )

    with pytest.raises(UnitNotAvailable):
        loan_context["loans"].create_and_confirm(command)

    with connect(loan_context["path"]) as database:
        assert database.execute(
            "SELECT COUNT(*) FROM borrow_transactions"
        ).fetchone()[0] == 0
        statuses = database.execute(
            "SELECT status FROM equipment_units ORDER BY id"
        ).fetchall()
    assert [row[0] for row in statuses] == ["available", "available"]


def test_duplicate_transaction_code_is_domain_error(loan_context) -> None:
    first_unit, second_unit = loan_context["units"]
    _draft(loan_context, "LOAN-1", (first_unit.id,))

    with pytest.raises(DuplicateCodeError) as captured:
        _draft(loan_context, "LOAN-1", (second_unit.id,))

    assert captured.value.field == "transaction_code"


def test_stale_selection_cannot_create_two_active_loans(loan_context) -> None:
    unit_id = loan_context["units"][0].id
    first = _draft(loan_context, "LOAN-1", (unit_id,))
    stale = _draft(loan_context, "LOAN-2", (unit_id,))

    loan_context["loans"].confirm_loan(first.id)
    with pytest.raises(UnitNotAvailable):
        loan_context["loans"].confirm_loan(stale.id)

    assert loan_context["loans"].get(stale.id).status is LoanStatus.DRAFT
    with connect(loan_context["path"]) as database:
        active_count = database.execute(
            """
            SELECT COUNT(*) FROM borrow_items AS bi
            JOIN borrow_transactions AS bt ON bt.id = bi.transaction_id
            WHERE bi.equipment_unit_id = ? AND bt.status = 'active'
            """,
            (unit_id,),
        ).fetchone()[0]
    assert active_count == 1


def test_concurrent_confirmation_serializes_unit_claim(loan_context) -> None:
    unit_id = loan_context["units"][0].id
    first = _draft(loan_context, "LOAN-1", (unit_id,))
    second = _draft(loan_context, "LOAN-2", (unit_id,))
    barrier = Barrier(2)

    def confirm(loan_id: int):
        barrier.wait()
        try:
            return loan_context["loans"].confirm_loan(loan_id).status
        except UnitNotAvailable:
            return "unavailable"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(confirm, (first.id, second.id)))

    assert results.count(LoanStatus.ACTIVE) == 1
    assert results.count("unavailable") == 1
    with connect(loan_context["path"]) as database:
        assert database.execute(
            "SELECT COUNT(*) FROM borrow_transactions WHERE status = 'active'"
        ).fetchone()[0] == 1


def test_multi_unit_failure_rolls_back_all_changes(loan_context) -> None:
    first_unit, second_unit = loan_context["units"]
    draft = _draft(loan_context, "LOAN-1", (first_unit.id, second_unit.id))
    with connect(loan_context["path"]) as database:
        database.execute(
            "UPDATE equipment_units SET status = 'borrowed' WHERE id = ?",
            (second_unit.id,),
        )
        database.commit()

    with pytest.raises(UnitNotAvailable):
        loan_context["loans"].confirm_loan(draft.id)

    assert loan_context["loans"].get(draft.id).status is LoanStatus.DRAFT
    with connect(loan_context["path"]) as database:
        statuses = database.execute(
            "SELECT status FROM equipment_units ORDER BY id"
        ).fetchall()
    assert [row[0] for row in statuses] == ["available", "borrowed"]


def test_inactive_borrower_blocks_confirmation_and_rolls_back(loan_context) -> None:
    unit_id = loan_context["units"][0].id
    draft = _draft(loan_context, "LOAN-1", (unit_id,))
    borrower = loan_context["borrower"]
    loan_context["borrowers"].update(
        borrower.id,
        UpdateBorrower(
            full_name=borrower.full_name,
            department=borrower.department,
            email=borrower.email,
            phone=borrower.phone,
            note=borrower.note,
            status=RecordStatus.INACTIVE,
        ),
    )

    with pytest.raises(InactiveRecordError):
        loan_context["loans"].confirm_loan(draft.id)

    assert loan_context["loans"].get(draft.id).status is LoanStatus.DRAFT
    assert loan_context["units"][0].status is UnitStatus.AVAILABLE
    with connect(loan_context["path"]) as database:
        assert database.execute(
            "SELECT status FROM equipment_units WHERE id = ?", (unit_id,)
        ).fetchone()[0] == "available"


def test_inactive_staff_blocks_confirmation(loan_context) -> None:
    unit_id = loan_context["units"][0].id
    draft = _draft(loan_context, "LOAN-1", (unit_id,))
    staff = loan_context["staff"]
    SQLiteStaffService(loan_context["path"]).update(
        staff.id,
        UpdateStaff(
            full_name=staff.full_name,
            email=staff.email,
            phone=staff.phone,
            status=RecordStatus.INACTIVE,
        ),
    )

    with pytest.raises(InactiveRecordError):
        loan_context["loans"].confirm_loan(draft.id)

    assert loan_context["loans"].get(draft.id).status is LoanStatus.DRAFT


def test_confirmed_loan_cannot_be_confirmed_again(loan_context) -> None:
    draft = _draft(loan_context, "LOAN-1", (loan_context["units"][0].id,))
    loan_context["loans"].confirm_loan(draft.id)

    with pytest.raises(LoanNotDraft):
        loan_context["loans"].confirm_loan(draft.id)
