from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.contracts import (
    AcquireUnit,
    CreateBorrower,
    CreateDraftLoan,
    CreateEquipment,
    CreateLocation,
    CreateStaff,
    LoanStatus,
    LostResolution,
    RecordReturn,
    ReplacementUnit,
    ResolveLostCase,
    ReturnItemCommand,
    ReturnOutcome,
    UnitStatus,
)
from app.database import connect, initialize_database
from app.errors import DuplicateCodeError, LostCaseAlreadyResolved, ValidationError
from app.services import (
    SQLiteBorrowerService,
    SQLiteEquipmentService,
    SQLiteLoanService,
    SQLiteLocationService,
    SQLiteLostCaseService,
    SQLiteReturnService,
    SQLiteStaffService,
    SQLiteUnitService,
)


FIXED_NOW = datetime(2026, 8, 9, 4, 30, tzinfo=timezone.utc)


def _build_lost_context(tmp_path, name: str):
    database_path = tmp_path / f"{name}.sqlite3"
    initialize_database(database_path)
    locations = SQLiteLocationService(database_path)
    equipment_service = SQLiteEquipmentService(database_path)
    staff_service = SQLiteStaffService(database_path)
    borrower_service = SQLiteBorrowerService(database_path)
    unit_service = SQLiteUnitService(database_path)
    loan_service = SQLiteLoanService(database_path)

    location = locations.create(CreateLocation("LAB-1", "101"))
    equipment = equipment_service.create(CreateEquipment("EQ-1", "Microscope"))
    staff = staff_service.create(CreateStaff("ST-1", "Approver"))
    borrower = borrower_service.create(CreateBorrower("BR-1", "Student"))
    unit = unit_service.acquire(
        AcquireUnit(
            asset_code="UNIT-1",
            equipment_id=equipment.id,
            acquired_at=date(2026, 8, 7),
            current_location_id=location.id,
            recorded_by_staff_id=staff.id,
            reason="Initial acquisition",
        )
    )
    draft = loan_service.create_draft(
        CreateDraftLoan(
            transaction_code="LOAN-1",
            borrower_id=borrower.id,
            recorded_by_staff_id=staff.id,
            borrow_date=date(2026, 8, 7),
            due_date=date(2026, 8, 10),
            unit_ids=(unit.id,),
        )
    )
    loan = loan_service.confirm_loan(draft.id)
    SQLiteReturnService(database_path).record_return(
        RecordReturn(
            loan_id=loan.id,
            returned_at=datetime(2026, 8, 8, 3, 0, tzinfo=timezone.utc),
            received_by_staff_id=staff.id,
            items=(
                ReturnItemCommand(
                    loan.items[0].id,
                    ReturnOutcome.REPORTED_LOST,
                    condition_note="Missing",
                ),
            ),
        )
    )
    with connect(database_path) as database:
        case_id = database.execute("SELECT id FROM lost_cases").fetchone()[0]
    return {
        "path": database_path,
        "case_id": case_id,
        "location": location,
        "equipment": equipment,
        "staff": staff,
        "unit": unit,
        "loan": loan,
        "loans": loan_service,
        "lost_cases": SQLiteLostCaseService(
            database_path, clock=lambda: FIXED_NOW
        ),
    }


def _resolution_command(context, resolution: LostResolution) -> ResolveLostCase:
    return ResolveLostCase(
        resolution=resolution,
        assessed_value=Decimal("1000"),
        approved_compensation=Decimal("750"),
        approved_by_staff_id=context["staff"].id,
        reason=f"Approved {resolution.value}",
        note="Resolution recorded",
    )


def _assert_single_audit(context, resolution: LostResolution) -> None:
    with connect(context["path"]) as database:
        rows = database.execute(
            """
            SELECT action, before_json, after_json, reason, staff_id, created_at
            FROM audit_logs WHERE entity_type = 'lost_case' AND entity_id = ?
            """,
            (context["case_id"],),
        ).fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert row["action"] == "resolve"
    assert json.loads(row["before_json"])["resolution"] is None
    assert json.loads(row["after_json"])["resolution"] == resolution.value
    assert row["reason"] == f"Approved {resolution.value}"
    assert row["staff_id"] == context["staff"].id
    assert row["created_at"] == "2026-08-09T04:30:00.000Z"


def test_recovered_restores_original_unit_and_completes_loan(tmp_path) -> None:
    context = _build_lost_context(tmp_path, "recovered")
    command = ResolveLostCase(
        resolution=LostResolution.RECOVERED,
        assessed_value=Decimal("1000"),
        approved_compensation=Decimal("750"),
        approved_by_staff_id=context["staff"].id,
        reason="Approved recovered",
        note="Resolution recorded",
        recovered_outcome=ReturnOutcome.AVAILABLE,
        location_id=context["location"].id,
    )

    resolved = context["lost_cases"].resolve_lost_case(context["case_id"], command)

    assert resolved.resolution is LostResolution.RECOVERED
    assert resolved.resolved_at == FIXED_NOW
    with connect(context["path"]) as database:
        unit_row = database.execute(
            "SELECT status, current_location_id FROM equipment_units WHERE id = ?",
            (context["unit"].id,),
        ).fetchone()
    assert tuple(unit_row) == (UnitStatus.AVAILABLE.value, context["location"].id)
    assert context["loans"].get(context["loan"].id).status is LoanStatus.COMPLETED
    _assert_single_audit(context, LostResolution.RECOVERED)


@pytest.mark.parametrize("resolution", [LostResolution.COMPENSATED, LostResolution.WAIVED])
def test_financial_or_waived_resolution_retires_unit_and_audits(
    tmp_path, resolution
) -> None:
    context = _build_lost_context(tmp_path, resolution.value)

    resolved = context["lost_cases"].resolve_lost_case(
        context["case_id"], _resolution_command(context, resolution)
    )

    assert resolved.resolution is resolution
    with connect(context["path"]) as database:
        status = database.execute(
            "SELECT status FROM equipment_units WHERE id = ?", (context["unit"].id,)
        ).fetchone()[0]
    assert status == UnitStatus.RETIRED.value
    assert context["loans"].get(context["loan"].id).status is LoanStatus.COMPLETED
    _assert_single_audit(context, resolution)


def test_replacement_creates_new_identity_and_retires_original(tmp_path) -> None:
    context = _build_lost_context(tmp_path, "replaced")
    base = _resolution_command(context, LostResolution.REPLACED)
    command = ResolveLostCase(
        resolution=base.resolution,
        assessed_value=base.assessed_value,
        approved_compensation=base.approved_compensation,
        approved_by_staff_id=base.approved_by_staff_id,
        reason=base.reason,
        note=base.note,
        replacement=ReplacementUnit(
            asset_code="UNIT-REPLACEMENT",
            acquired_at=date(2026, 8, 9),
            location_id=context["location"].id,
            serial_number="SERIAL-NEW",
        ),
    )

    resolved = context["lost_cases"].resolve_lost_case(context["case_id"], command)

    assert resolved.replacement_unit_id is not None
    assert resolved.replacement_unit_id != context["unit"].id
    with connect(context["path"]) as database:
        original = database.execute(
            "SELECT asset_code, status FROM equipment_units WHERE id = ?",
            (context["unit"].id,),
        ).fetchone()
        replacement = database.execute(
            """
            SELECT asset_code, equipment_id, status FROM equipment_units
            WHERE id = ?
            """,
            (resolved.replacement_unit_id,),
        ).fetchone()
        adjustment = database.execute(
            """
            SELECT action FROM inventory_adjustments
            WHERE equipment_unit_id = ?
            """,
            (resolved.replacement_unit_id,),
        ).fetchone()[0]
    assert tuple(original) == ("UNIT-1", UnitStatus.RETIRED.value)
    assert tuple(replacement) == (
        "UNIT-REPLACEMENT",
        context["equipment"].id,
        UnitStatus.AVAILABLE.value,
    )
    assert adjustment == "acquire"
    _assert_single_audit(context, LostResolution.REPLACED)


@pytest.mark.parametrize(
    "missing_field",
    ["assessed_value", "approved_compensation", "approved_by_staff_id"],
)
def test_incomplete_approval_cannot_close_case(tmp_path, missing_field) -> None:
    context = _build_lost_context(tmp_path, f"missing-{missing_field}")
    values = {
        "resolution": LostResolution.COMPENSATED,
        "assessed_value": Decimal("1000"),
        "approved_compensation": Decimal("750"),
        "approved_by_staff_id": context["staff"].id,
        "reason": "Approval",
    }
    values[missing_field] = None

    with pytest.raises(ValidationError) as captured:
        context["lost_cases"].resolve_lost_case(
            context["case_id"], ResolveLostCase(**values)
        )

    assert captured.value.field == missing_field
    assert context["lost_cases"].get(context["case_id"]).resolution is None
    with connect(context["path"]) as database:
        assert database.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0] == 0


def test_duplicate_replacement_code_rolls_back_resolution(tmp_path) -> None:
    context = _build_lost_context(tmp_path, "replacement-rollback")
    command = _resolution_command(context, LostResolution.REPLACED)
    command = ResolveLostCase(
        resolution=command.resolution,
        assessed_value=command.assessed_value,
        approved_compensation=command.approved_compensation,
        approved_by_staff_id=command.approved_by_staff_id,
        reason=command.reason,
        replacement=ReplacementUnit(
            asset_code="UNIT-1",
            acquired_at=date(2026, 8, 9),
            location_id=context["location"].id,
        ),
    )

    with pytest.raises(DuplicateCodeError):
        context["lost_cases"].resolve_lost_case(context["case_id"], command)

    assert context["lost_cases"].get(context["case_id"]).resolution is None
    with connect(context["path"]) as database:
        assert database.execute("SELECT COUNT(*) FROM equipment_units").fetchone()[0] == 1
        assert database.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0] == 0
        status = database.execute("SELECT status FROM equipment_units").fetchone()[0]
    assert status == UnitStatus.REPORTED_LOST.value


def test_resolved_case_cannot_be_resolved_twice(tmp_path) -> None:
    context = _build_lost_context(tmp_path, "resolve-twice")
    command = _resolution_command(context, LostResolution.WAIVED)
    context["lost_cases"].resolve_lost_case(context["case_id"], command)

    with pytest.raises(LostCaseAlreadyResolved):
        context["lost_cases"].resolve_lost_case(context["case_id"], command)

    _assert_single_audit(context, LostResolution.WAIVED)
