from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.contracts import (
    AcquireUnit,
    CreateBorrower,
    CreateDraftLoan,
    CreateEquipment,
    CreateLocation,
    CreateStaff,
    LoanQueryFilter,
    LoanQueryState,
    RecordReturn,
    ReturnItemCommand,
    ReturnOutcome,
)
from app.database import initialize_database
from app.errors import ValidationError
from app.services import (
    SQLiteBorrowerService,
    SQLiteEquipmentService,
    SQLiteLoanQueryService,
    SQLiteLoanService,
    SQLiteLocationService,
    SQLiteReturnService,
    SQLiteStaffService,
    SQLiteUnitService,
)


BANGKOK_AUGUST_10 = datetime(2026, 8, 9, 17, 30, tzinfo=timezone.utc)


@pytest.fixture
def query_context(tmp_path):
    database_path = tmp_path / "queries.sqlite3"
    initialize_database(database_path)
    location_service = SQLiteLocationService(database_path)
    equipment_service = SQLiteEquipmentService(database_path)
    staff_service = SQLiteStaffService(database_path)
    borrower_service = SQLiteBorrowerService(database_path)
    unit_service = SQLiteUnitService(database_path)
    loan_service = SQLiteLoanService(database_path)
    return_service = SQLiteReturnService(database_path)

    location = location_service.create(CreateLocation("LAB-1", "101"))
    microscope = equipment_service.create(
        CreateEquipment("MIC", "Research Microscope", category="Optics")
    )
    centrifuge = equipment_service.create(
        CreateEquipment("CEN", "High-speed Centrifuge", category="Separation")
    )
    staff = staff_service.create(CreateStaff("ST-1", "Lab Staff"))
    alice = borrower_service.create(CreateBorrower("BR-A", "Alice Student"))
    bob = borrower_service.create(CreateBorrower("BR-B", "Bob Researcher"))

    unit_number = 0

    def create_unit(equipment=microscope):
        nonlocal unit_number
        unit_number += 1
        return unit_service.acquire(
            AcquireUnit(
                asset_code=f"ASSET-{unit_number:02d}",
                equipment_id=equipment.id,
                acquired_at=date(2026, 7, 1),
                current_location_id=location.id,
                recorded_by_staff_id=staff.id,
                reason="Initial acquisition",
            )
        )

    def create_loan(
        code: str,
        due_date: date,
        *,
        borrower=alice,
        equipment=microscope,
        item_count: int = 1,
        borrow_date: date = date(2026, 8, 1),
    ):
        units = tuple(create_unit(equipment) for _ in range(item_count))
        draft = loan_service.create_draft(
            CreateDraftLoan(
                transaction_code=code,
                borrower_id=borrower.id,
                recorded_by_staff_id=staff.id,
                borrow_date=borrow_date,
                due_date=due_date,
                unit_ids=tuple(unit.id for unit in units),
            )
        )
        return loan_service.confirm_loan(draft.id)

    loans = {
        "overdue": create_loan("LOAN-OVERDUE", date(2026, 8, 9)),
        "today": create_loan(
            "LOAN-TODAY",
            date(2026, 8, 10),
            borrower=bob,
            equipment=centrifuge,
        ),
        "soon_1": create_loan("LOAN-SOON-1", date(2026, 8, 11)),
        "partial": create_loan(
            "LOAN-PARTIAL", date(2026, 8, 12), item_count=2
        ),
        "soon_3": create_loan("LOAN-SOON-3", date(2026, 8, 13)),
        "far": create_loan(
            "LOAN-FAR", date(2026, 8, 14), borrow_date=date(2026, 8, 2)
        ),
        "completed": create_loan("LOAN-COMPLETED", date(2026, 8, 9)),
    }
    return_service.record_return(
        RecordReturn(
            loan_id=loans["partial"].id,
            returned_at=datetime(2026, 8, 9, 4, 0, tzinfo=timezone.utc),
            received_by_staff_id=staff.id,
            items=(
                ReturnItemCommand(
                    loans["partial"].items[0].id,
                    ReturnOutcome.AVAILABLE,
                    location.id,
                ),
            ),
        )
    )
    return_service.record_return(
        RecordReturn(
            loan_id=loans["completed"].id,
            returned_at=datetime(2026, 8, 9, 5, 0, tzinfo=timezone.utc),
            received_by_staff_id=staff.id,
            items=(
                ReturnItemCommand(
                    loans["completed"].items[0].id,
                    ReturnOutcome.AVAILABLE,
                    location.id,
                ),
            ),
        )
    )
    return {
        "service": SQLiteLoanQueryService(
            database_path, clock=lambda: BANGKOK_AUGUST_10
        ),
        "loans": loans,
    }


def _codes(results):
    return {result.transaction_code for result in results}


def test_due_boundaries_use_bangkok_business_date(query_context) -> None:
    service = query_context["service"]

    assert _codes(service.search(LoanQueryFilter(state=LoanQueryState.DUE_TODAY))) == {
        "LOAN-TODAY"
    }
    assert _codes(service.search(LoanQueryFilter(state=LoanQueryState.DUE_SOON))) == {
        "LOAN-SOON-1",
        "LOAN-PARTIAL",
        "LOAN-SOON-3",
    }
    assert _codes(service.search(LoanQueryFilter(state=LoanQueryState.OVERDUE))) == {
        "LOAN-OVERDUE"
    }


def test_three_days_is_inclusive_and_four_days_is_excluded(query_context) -> None:
    due_soon = query_context["service"].search(
        LoanQueryFilter(state=LoanQueryState.DUE_SOON)
    )

    assert "LOAN-SOON-3" in _codes(due_soon)
    assert "LOAN-FAR" not in _codes(due_soon)


def test_partial_and_active_filters_use_resolved_item_counts(query_context) -> None:
    service = query_context["service"]
    partial = service.search(LoanQueryFilter(state=LoanQueryState.PARTIAL))
    active = service.search(LoanQueryFilter(state=LoanQueryState.ACTIVE))

    assert _codes(partial) == {"LOAN-PARTIAL"}
    assert partial[0].item_count == 2
    assert partial[0].resolved_item_count == 1
    assert partial[0].outstanding_item_count == 1
    assert "LOAN-COMPLETED" not in _codes(active)
    assert len(active) == 6


def test_searches_borrower_equipment_asset_and_date_range(query_context) -> None:
    service = query_context["service"]
    today_loan = query_context["loans"]["today"]
    far_loan = query_context["loans"]["far"]

    assert _codes(service.search(LoanQueryFilter(borrower_query="Bob"))) == {
        "LOAN-TODAY"
    }
    assert _codes(service.search(LoanQueryFilter(borrower_query="BR-B"))) == {
        "LOAN-TODAY"
    }
    assert _codes(service.search(LoanQueryFilter(equipment_query="Centrifuge"))) == {
        "LOAN-TODAY"
    }
    assert _codes(
        service.search(LoanQueryFilter(asset_code=today_loan.items[0].asset_code))
    ) == {"LOAN-TODAY"}
    assert _codes(
        service.search(
            LoanQueryFilter(
                borrow_date_from=date(2026, 8, 2),
                borrow_date_to=date(2026, 8, 2),
            )
        )
    ) == {far_loan.transaction_code}


def test_invalid_date_range_is_rejected(query_context) -> None:
    with pytest.raises(ValidationError) as captured:
        query_context["service"].search(
            LoanQueryFilter(
                borrow_date_from=date(2026, 8, 3),
                borrow_date_to=date(2026, 8, 2),
            )
        )

    assert captured.value.field == "borrow_date_from"
