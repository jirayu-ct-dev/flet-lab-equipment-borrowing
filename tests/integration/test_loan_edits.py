from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone

import pytest

from app.contracts import (
    AcquireUnit,
    ChangeLoanBorrower,
    CreateBorrower,
    CreateDraftLoan,
    CreateEquipment,
    CreateLocation,
    CreateStaff,
    EditLoanDetails,
    RecordStatus,
    ReplaceLoanUnit,
    UnitStatus,
    UpdateBorrower,
)
from app.database import connect, initialize_database
from app.errors import InactiveRecordError, UnitNotAvailable, ValidationError
from app.services import (
    SQLiteAuditLogService,
    SQLiteBorrowerService,
    SQLiteEquipmentService,
    SQLiteLoanEditService,
    SQLiteLoanService,
    SQLiteLocationService,
    SQLiteStaffService,
    SQLiteUnitService,
)


FIXED_NOW = datetime(2026, 8, 9, 5, 45, tzinfo=timezone.utc)


@pytest.fixture
def edit_context(tmp_path):
    database_path = tmp_path / "loan-edits.sqlite3"
    initialize_database(database_path)
    location_service = SQLiteLocationService(database_path)
    equipment_service = SQLiteEquipmentService(database_path)
    staff_service = SQLiteStaffService(database_path)
    borrower_service = SQLiteBorrowerService(database_path)
    unit_service = SQLiteUnitService(database_path)
    loan_service = SQLiteLoanService(database_path)

    location = location_service.create(CreateLocation("LAB-1", "101"))
    equipment = equipment_service.create(CreateEquipment("EQ-1", "Microscope"))
    staff = staff_service.create(CreateStaff("ST-1", "Editor"))
    borrower = borrower_service.create(CreateBorrower("BR-1", "Student One"))
    second_borrower = borrower_service.create(CreateBorrower("BR-2", "Student Two"))
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
            unit_ids=(units[0].id, units[1].id),
            purpose="Original purpose",
            note="Original note",
        )
    )
    loan = loan_service.confirm_loan(draft.id)
    return {
        "path": database_path,
        "location": location,
        "staff": staff,
        "borrower_service": borrower_service,
        "second_borrower": second_borrower,
        "units": units,
        "loan": loan,
        "loans": loan_service,
        "edits": SQLiteLoanEditService(database_path, clock=lambda: FIXED_NOW),
        "audit": SQLiteAuditLogService(database_path),
    }


def test_each_edit_action_records_before_after_reason_staff_and_timestamp(
    edit_context,
) -> None:
    loan = edit_context["loan"]
    staff = edit_context["staff"]
    first_item = loan.items[0]
    replacement = edit_context["units"][2]

    edited = edit_context["edits"].edit_details(
        loan.id,
        EditLoanDetails(
            due_date=date(2026, 8, 12),
            purpose="Updated purpose",
            note="Updated note",
            reason="Schedule changed",
            performed_by_staff_id=staff.id,
        ),
    )
    changed = edit_context["edits"].change_borrower(
        loan.id,
        ChangeLoanBorrower(
            borrower_id=edit_context["second_borrower"].id,
            reason="Correct borrower",
            performed_by_staff_id=staff.id,
        ),
    )
    replaced = edit_context["edits"].replace_unit(
        loan.id,
        ReplaceLoanUnit(
            borrow_item_id=first_item.id,
            new_unit_id=replacement.id,
            returned_location_id=edit_context["location"].id,
            reason="Correct selected asset",
            performed_by_staff_id=staff.id,
        ),
    )

    assert edited.due_date == date(2026, 8, 12)
    assert changed.borrower_id == edit_context["second_borrower"].id
    assert replaced.items[0].equipment_unit_id == replacement.id
    logs = edit_context["audit"].list_for_entity("borrow_transaction", loan.id)
    assert [log.action for log in logs] == [
        "edit_details",
        "change_borrower",
        "replace_unit",
    ]
    assert logs[0].before == {
        "due_date": "2026-08-10",
        "purpose": "Original purpose",
        "note": "Original note",
    }
    assert logs[0].after == {
        "due_date": "2026-08-12",
        "purpose": "Updated purpose",
        "note": "Updated note",
    }
    assert logs[1].before == {"borrower_id": loan.borrower_id}
    assert logs[1].after == {"borrower_id": edit_context["second_borrower"].id}
    assert logs[2].before["equipment_unit_id"] == edit_context["units"][0].id
    assert logs[2].after["equipment_unit_id"] == replacement.id
    assert [log.reason for log in logs] == [
        "Schedule changed",
        "Correct borrower",
        "Correct selected asset",
    ]
    assert all(log.staff_id == staff.id for log in logs)
    assert all(log.created_at == FIXED_NOW for log in logs)

    with connect(edit_context["path"]) as database:
        statuses = database.execute(
            "SELECT id, status, current_location_id FROM equipment_units ORDER BY id"
        ).fetchall()
    assert tuple(statuses[0]) == (
        edit_context["units"][0].id,
        UnitStatus.AVAILABLE.value,
        edit_context["location"].id,
    )
    assert tuple(statuses[2]) == (
        replacement.id,
        UnitStatus.BORROWED.value,
        None,
    )


def test_unavailable_replacement_rolls_back_original_unit_and_item(edit_context) -> None:
    loan = edit_context["loan"]
    first_item = loan.items[0]
    replacement = edit_context["units"][2]
    with connect(edit_context["path"]) as database:
        database.execute(
            "UPDATE equipment_units SET status = 'maintenance' WHERE id = ?",
            (replacement.id,),
        )
        database.commit()

    with pytest.raises(UnitNotAvailable):
        edit_context["edits"].replace_unit(
            loan.id,
            ReplaceLoanUnit(
                borrow_item_id=first_item.id,
                new_unit_id=replacement.id,
                returned_location_id=edit_context["location"].id,
                reason="Invalid replacement",
                performed_by_staff_id=edit_context["staff"].id,
            ),
        )

    with connect(edit_context["path"]) as database:
        item_unit_id = database.execute(
            "SELECT equipment_unit_id FROM borrow_items WHERE id = ?",
            (first_item.id,),
        ).fetchone()[0]
        old_status = database.execute(
            "SELECT status FROM equipment_units WHERE id = ?",
            (first_item.equipment_unit_id,),
        ).fetchone()[0]
    assert item_unit_id == first_item.equipment_unit_id
    assert old_status == UnitStatus.BORROWED.value
    assert edit_context["audit"].list_for_entity("borrow_transaction", loan.id) == []


def test_replace_unit_database_failure_rolls_back_both_unit_statuses(edit_context) -> None:
    loan = edit_context["loan"]
    first_item = loan.items[0]
    replacement = edit_context["units"][2]
    with connect(edit_context["path"]) as database:
        database.execute(
            f"""
            CREATE TRIGGER fail_borrow_item_replacement
            BEFORE UPDATE ON borrow_items
            WHEN OLD.id = {first_item.id}
            BEGIN
                SELECT RAISE(ABORT, 'injected edit failure');
            END
            """
        )
        database.commit()

    with pytest.raises(sqlite3.IntegrityError, match="injected edit failure"):
        edit_context["edits"].replace_unit(
            loan.id,
            ReplaceLoanUnit(
                borrow_item_id=first_item.id,
                new_unit_id=replacement.id,
                returned_location_id=edit_context["location"].id,
                reason="Replacement",
                performed_by_staff_id=edit_context["staff"].id,
            ),
        )

    with connect(edit_context["path"]) as database:
        rows = database.execute(
            "SELECT id, status FROM equipment_units ORDER BY id"
        ).fetchall()
        item_unit_id = database.execute(
            "SELECT equipment_unit_id FROM borrow_items WHERE id = ?",
            (first_item.id,),
        ).fetchone()[0]
        audit_count = database.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
    assert [tuple(row) for row in rows] == [
        (edit_context["units"][0].id, UnitStatus.BORROWED.value),
        (edit_context["units"][1].id, UnitStatus.BORROWED.value),
        (replacement.id, UnitStatus.AVAILABLE.value),
    ]
    assert item_unit_id == first_item.equipment_unit_id
    assert audit_count == 0


def test_inactive_borrower_change_is_rejected_without_audit(edit_context) -> None:
    borrower = edit_context["second_borrower"]
    edit_context["borrower_service"].update(
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
        edit_context["edits"].change_borrower(
            edit_context["loan"].id,
            ChangeLoanBorrower(
                borrower_id=borrower.id,
                reason="Invalid borrower",
                performed_by_staff_id=edit_context["staff"].id,
            ),
        )

    assert edit_context["audit"].list_for_entity(
        "borrow_transaction", edit_context["loan"].id
    ) == []


def test_reason_is_required_for_every_edit(edit_context) -> None:
    with pytest.raises(ValidationError) as captured:
        edit_context["edits"].edit_details(
            edit_context["loan"].id,
            EditLoanDetails(
                due_date=date(2026, 8, 11),
                purpose=None,
                note=None,
                reason="   ",
                performed_by_staff_id=edit_context["staff"].id,
            ),
        )

    assert captured.value.field == "reason"


def test_database_enforces_append_only_audit_logs(edit_context) -> None:
    edit_context["edits"].edit_details(
        edit_context["loan"].id,
        EditLoanDetails(
            due_date=date(2026, 8, 11),
            purpose=None,
            note=None,
            reason="Required update",
            performed_by_staff_id=edit_context["staff"].id,
        ),
    )

    with connect(edit_context["path"]) as database:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            database.execute("UPDATE audit_logs SET reason = 'changed'")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            database.execute("DELETE FROM audit_logs")

    assert len(
        edit_context["audit"].list_for_entity(
            "borrow_transaction", edit_context["loan"].id
        )
    ) == 1
