from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone

import pytest

from app.contracts import (
    AcquireUnit,
    CreateBorrower,
    CreateDraftLoan,
    CreateEquipment,
    CreateLocation,
    CreateStaff,
    LoanStatus,
    RecordReturn,
    ReturnItemCommand,
    ReturnOutcome,
    UnitStatus,
)
from app.database import connect, initialize_database
from app.errors import ReturnAlreadyRecorded, UnitNotAvailable, ValidationError
from app.services import (
    SQLiteBorrowerService,
    SQLiteEquipmentService,
    SQLiteLoanService,
    SQLiteLocationService,
    SQLiteReturnService,
    SQLiteStaffService,
    SQLiteUnitService,
)


@pytest.fixture
def return_context(tmp_path):
    database_path = tmp_path / "returns.sqlite3"
    initialize_database(database_path)
    location_service = SQLiteLocationService(database_path)
    equipment_service = SQLiteEquipmentService(database_path)
    staff_service = SQLiteStaffService(database_path)
    borrower_service = SQLiteBorrowerService(database_path)
    unit_service = SQLiteUnitService(database_path)
    loan_service = SQLiteLoanService(database_path)

    location = location_service.create(CreateLocation("LAB-1", "101"))
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
        for number in (1, 2, 3)
    )
    draft = loan_service.create_draft(
        CreateDraftLoan(
            transaction_code="LOAN-1",
            borrower_id=borrower.id,
            recorded_by_staff_id=staff.id,
            borrow_date=date(2026, 8, 7),
            due_date=date(2026, 8, 10),
            unit_ids=tuple(unit.id for unit in units),
        )
    )
    loan = loan_service.confirm_loan(draft.id)
    return {
        "path": database_path,
        "location": location,
        "staff": staff,
        "loan": loan,
        "loans": loan_service,
        "returns": SQLiteReturnService(database_path),
    }


def _record(context, *items: ReturnItemCommand, note: str | None = None):
    return context["returns"].record_return(
        RecordReturn(
            loan_id=context["loan"].id,
            returned_at=datetime(2026, 8, 8, 3, 0, tzinfo=timezone.utc),
            received_by_staff_id=context["staff"].id,
            items=tuple(items),
            note=note,
        )
    )


def test_partial_returns_create_distinct_events_and_complete_when_all_resolved(
    return_context,
) -> None:
    first, second, third = return_context["loan"].items
    first_event = _record(
        return_context,
        ReturnItemCommand(
            first.id, ReturnOutcome.AVAILABLE, return_context["location"].id
        ),
        note="First batch",
    )
    second_event = _record(
        return_context,
        ReturnItemCommand(
            second.id,
            ReturnOutcome.MAINTENANCE,
            return_context["location"].id,
            "Lens damaged",
        ),
        note="Second batch",
    )

    assert first_event.id != second_event.id
    assert return_context["loans"].get(return_context["loan"].id).status is LoanStatus.ACTIVE

    third_event = _record(
        return_context,
        ReturnItemCommand(
            third.id, ReturnOutcome.AVAILABLE, return_context["location"].id
        ),
        note="Final batch",
    )
    events = return_context["returns"].list_for_loan(return_context["loan"].id)

    assert [event.id for event in events] == [
        first_event.id,
        second_event.id,
        third_event.id,
    ]
    assert [event.note for event in events] == [
        "First batch",
        "Second batch",
        "Final batch",
    ]
    assert return_context["loans"].get(return_context["loan"].id).status is LoanStatus.COMPLETED

    with connect(return_context["path"]) as database:
        statuses = database.execute(
            "SELECT status FROM equipment_units ORDER BY id"
        ).fetchall()
    assert [row[0] for row in statuses] == [
        UnitStatus.AVAILABLE.value,
        UnitStatus.MAINTENANCE.value,
        UnitStatus.AVAILABLE.value,
    ]


def test_duplicate_return_is_rejected_without_overwriting_event(return_context) -> None:
    first = return_context["loan"].items[0]
    original = _record(
        return_context,
        ReturnItemCommand(
            first.id,
            ReturnOutcome.MAINTENANCE,
            return_context["location"].id,
            "Original condition",
        ),
        note="Original event",
    )

    with pytest.raises(ReturnAlreadyRecorded):
        _record(
            return_context,
            ReturnItemCommand(
                first.id,
                ReturnOutcome.AVAILABLE,
                return_context["location"].id,
            ),
            note="Overwrite attempt",
        )

    events = return_context["returns"].list_for_loan(return_context["loan"].id)
    assert events == [original]
    assert events[0].items[0].condition_note == "Original condition"


def test_invalid_multi_item_return_rolls_back_event_and_all_units(return_context) -> None:
    first, second, _ = return_context["loan"].items

    with pytest.raises(ValidationError):
        _record(
            return_context,
            ReturnItemCommand(
                first.id, ReturnOutcome.AVAILABLE, return_context["location"].id
            ),
            ReturnItemCommand(second.id, ReturnOutcome.MAINTENANCE, None),
        )

    assert return_context["returns"].list_for_loan(return_context["loan"].id) == []
    with connect(return_context["path"]) as database:
        statuses = database.execute(
            "SELECT status FROM equipment_units ORDER BY id"
        ).fetchall()
    assert [row[0] for row in statuses] == ["borrowed", "borrowed", "borrowed"]


def test_database_failure_during_second_item_rolls_back_first_item(return_context) -> None:
    first, second, _ = return_context["loan"].items
    with connect(return_context["path"]) as database:
        database.execute(
            f"""
            CREATE TRIGGER fail_second_return_item
            BEFORE INSERT ON return_items
            WHEN NEW.borrow_item_id = {second.id}
            BEGIN
                SELECT RAISE(ABORT, 'injected return failure');
            END
            """
        )
        database.commit()

    with pytest.raises(sqlite3.IntegrityError, match="injected return failure"):
        _record(
            return_context,
            ReturnItemCommand(
                first.id, ReturnOutcome.AVAILABLE, return_context["location"].id
            ),
            ReturnItemCommand(
                second.id, ReturnOutcome.AVAILABLE, return_context["location"].id
            ),
        )

    with connect(return_context["path"]) as database:
        assert database.execute("SELECT COUNT(*) FROM returns").fetchone()[0] == 0
        assert database.execute("SELECT COUNT(*) FROM return_items").fetchone()[0] == 0
        statuses = database.execute(
            "SELECT status FROM equipment_units ORDER BY id"
        ).fetchall()
    assert [row[0] for row in statuses] == ["borrowed", "borrowed", "borrowed"]


def test_reported_lost_opens_case_and_keeps_loan_active(return_context) -> None:
    first, second, third = return_context["loan"].items
    event = _record(
        return_context,
        ReturnItemCommand(first.id, ReturnOutcome.REPORTED_LOST, None, "Not found"),
        ReturnItemCommand(
            second.id, ReturnOutcome.AVAILABLE, return_context["location"].id
        ),
        ReturnItemCommand(
            third.id, ReturnOutcome.AVAILABLE, return_context["location"].id
        ),
    )

    assert event.items[0].outcome is ReturnOutcome.REPORTED_LOST
    assert return_context["loans"].get(return_context["loan"].id).status is LoanStatus.ACTIVE
    with connect(return_context["path"]) as database:
        lost_case = database.execute(
            "SELECT equipment_unit_id, resolution FROM lost_cases"
        ).fetchone()
        lost_status = database.execute(
            "SELECT status FROM equipment_units WHERE id = ?",
            (event.items[0].equipment_unit_id,),
        ).fetchone()[0]
    assert tuple(lost_case) == (event.items[0].equipment_unit_id, None)
    assert lost_status == UnitStatus.REPORTED_LOST.value


def test_non_borrowed_unit_causes_return_rollback(return_context) -> None:
    first = return_context["loan"].items[0]
    with connect(return_context["path"]) as database:
        database.execute(
            "UPDATE equipment_units SET status = 'available' WHERE id = ?",
            (first.equipment_unit_id,),
        )
        database.commit()

    with pytest.raises(UnitNotAvailable):
        _record(
            return_context,
            ReturnItemCommand(
                first.id, ReturnOutcome.AVAILABLE, return_context["location"].id
            ),
        )

    assert return_context["returns"].list_for_loan(return_context["loan"].id) == []


def test_return_timestamp_must_be_timezone_aware(return_context) -> None:
    first = return_context["loan"].items[0]
    with pytest.raises(ValidationError) as captured:
        return_context["returns"].record_return(
            RecordReturn(
                loan_id=return_context["loan"].id,
                returned_at=datetime(2026, 8, 8, 10, 0),
                received_by_staff_id=return_context["staff"].id,
                items=(
                    ReturnItemCommand(
                        first.id,
                        ReturnOutcome.AVAILABLE,
                        return_context["location"].id,
                    ),
                ),
            )
        )

    assert captured.value.field == "returned_at"
