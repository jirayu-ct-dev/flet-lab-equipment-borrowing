from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.contracts import (
    AcquireUnit,
    CreateBorrower,
    CreateDraftLoan,
    CreateEquipment,
    CreateLocation,
    CreateLostReport,
    CreateStaff,
    LostReportStatus,
    RecordStatus,
    ReviewLostReport,
    UnitStatus,
    UpdateBorrower,
    UpdateStaff,
)
from app.database import connect, initialize_database
from app.errors import (
    InactiveRecordError,
    NotFoundError,
    ReportAlreadyReviewed,
)
from app.services import (
    SQLiteBorrowerService,
    SQLiteEquipmentService,
    SQLiteLoanService,
    SQLiteLocationService,
    SQLiteLostReportService,
    SQLiteStaffService,
    SQLiteUnitService,
)
from app.services.sqlite_adapter import SQLiteInventoryAdapter


FIXED_NOW = datetime(2026, 8, 9, 4, 30, tzinfo=timezone.utc)


def _build_context(tmp_path, name: str):
    database_path = tmp_path / f"{name}.sqlite3"
    initialize_database(database_path)
    locations = SQLiteLocationService(database_path)
    equipment_service = SQLiteEquipmentService(database_path)
    staff_service = SQLiteStaffService(database_path)
    borrower_service = SQLiteBorrowerService(database_path)
    unit_service = SQLiteUnitService(database_path)
    loan_service = SQLiteLoanService(database_path)

    location = locations.create(CreateLocation("LAB-1", "101"))
    equipment = equipment_service.create(CreateEquipment("EQ-1", "Laptop"))
    staff = staff_service.create(CreateStaff("ST-1", "Approver"))
    inactive_staff = staff_service.create(CreateStaff("ST-2", "Retired Staff"))
    staff_service.update(
        inactive_staff.id,
        UpdateStaff(
            full_name="Retired Staff",
            email=None,
            phone=None,
            status=RecordStatus.INACTIVE,
        ),
    )
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
    loan = loan_service.create_and_confirm(
        CreateDraftLoan(
            transaction_code="LOAN-1",
            borrower_id=borrower.id,
            recorded_by_staff_id=staff.id,
            borrow_date=date(2026, 8, 7),
            due_date=date(2026, 8, 10),
            unit_ids=(unit.id,),
        )
    )
    free_unit = unit_service.acquire(
        AcquireUnit(
            asset_code="UNIT-2",
            equipment_id=equipment.id,
            acquired_at=date(2026, 8, 7),
            current_location_id=location.id,
            recorded_by_staff_id=staff.id,
            reason="Initial acquisition",
        )
    )
    return {
        "path": database_path,
        "borrower": borrower,
        "staff": staff,
        "inactive_staff": inactive_staff,
        "unit": unit,
        "free_unit": free_unit,
        "loan": loan,
        "lost_reports": SQLiteLostReportService(
            database_path, clock=lambda: FIXED_NOW
        ),
    }


def _create_command(context, unit_id: int | None = None, **overrides: object) -> CreateLostReport:
    values: dict[str, object] = {
        "borrower_id": context["borrower"].id,
        "equipment_unit_id": unit_id if unit_id is not None else context["unit"].id,
        "lost_date": "2026-08-15",
        "location": "Lab A",
        "description": "Lost during field work",
    }
    values.update(overrides)
    return CreateLostReport(**values)  # type: ignore[arg-type]


def _approve(context, report_id: int) -> ReviewLostReport:
    return ReviewLostReport(
        approved=True, reviewed_by_staff_id=context["staff"].id, review_note="Confirmed"
    )


def test_migration_creates_lost_reports_table(tmp_path) -> None:
    context = _build_context(tmp_path, "migration")

    with connect(context["path"]) as database:
        versions = [
            row["version"]
            for row in database.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
        ]
        columns = {
            row["name"]
            for row in database.execute("PRAGMA table_info(lost_reports)")
        }
    assert versions == [1, 2, 3, 4, 5, 6, 7, 8]
    assert columns == {
        "id",
        "borrower_id",
        "equipment_unit_id",
        "reported_at",
        "lost_date",
        "location",
        "description",
        "status",
        "reviewed_by_staff_id",
        "reviewed_at",
        "review_note",
        "created_at",
    }


def test_create_report_persists_pending_and_lists(tmp_path) -> None:
    context = _build_context(tmp_path, "create")

    report = context["lost_reports"].create_report(_create_command(context))

    assert report.status is LostReportStatus.PENDING
    assert report.reported_at == FIXED_NOW
    assert report.lost_date == "2026-08-15"
    assert report.location == "Lab A"
    assert report.description == "Lost during field work"
    assert report.reviewed_by_staff_id is None
    assert report.reviewed_at is None
    assert context["lost_reports"].list_pending_reports() == [report]
    assert (
        context["lost_reports"].list_reports_for_borrower(context["borrower"].id)
        == [report]
    )
    assert context["lost_reports"].list_reports_for_borrower(999) == []


def test_create_report_rejects_unknown_or_inactive_borrower_and_unknown_unit(
    tmp_path,
) -> None:
    context = _build_context(tmp_path, "create-invalid")

    with pytest.raises(NotFoundError):
        context["lost_reports"].create_report(
            _create_command(context, borrower_id=999)
        )
    with pytest.raises(NotFoundError):
        context["lost_reports"].create_report(
            _create_command(context, equipment_unit_id=999)
        )
    borrower_service = SQLiteBorrowerService(context["path"])
    borrower = borrower_service.create(CreateBorrower("BR-2", "Inactive Student"))
    borrower_service.update(
        borrower.id,
        UpdateBorrower(
            full_name="Inactive Student",
            department=None,
            email=None,
            phone=None,
            note=None,
            status=RecordStatus.INACTIVE,
        ),
    )
    with pytest.raises(InactiveRecordError):
        context["lost_reports"].create_report(
            _create_command(context, borrower_id=borrower.id)
        )


def test_approve_with_open_loan_marks_unit_and_opens_lost_case(tmp_path) -> None:
    context = _build_context(tmp_path, "approve-open")

    report = context["lost_reports"].create_report(_create_command(context))
    reviewed = context["lost_reports"].review_report(report.id, _approve(context, report.id))

    assert reviewed.status is LostReportStatus.APPROVED
    assert reviewed.reviewed_by_staff_id == context["staff"].id
    assert reviewed.reviewed_at == FIXED_NOW
    with connect(context["path"]) as database:
        unit_status = database.execute(
            "SELECT status FROM equipment_units WHERE id = ?",
            (context["unit"].id,),
        ).fetchone()[0]
        lost_cases = database.execute(
            "SELECT equipment_unit_id, borrow_item_id, note FROM lost_cases"
        ).fetchall()
    assert unit_status == UnitStatus.REPORTED_LOST.value
    assert [tuple(row) for row in lost_cases] == [
        (context["unit"].id, context["loan"].items[0].id, "Lost during field work")
    ]


def test_approve_without_open_loan_skips_lost_case(tmp_path) -> None:
    context = _build_context(tmp_path, "approve-free")

    report = context["lost_reports"].create_report(
        _create_command(context, unit_id=context["free_unit"].id)
    )
    reviewed = context["lost_reports"].review_report(report.id, _approve(context, report.id))

    assert reviewed.status is LostReportStatus.APPROVED
    with connect(context["path"]) as database:
        unit_status = database.execute(
            "SELECT status FROM equipment_units WHERE id = ?",
            (context["free_unit"].id,),
        ).fetchone()[0]
        lost_case_count = database.execute(
            "SELECT COUNT(*) FROM lost_cases"
        ).fetchone()[0]
    assert unit_status == UnitStatus.REPORTED_LOST.value
    assert lost_case_count == 0


def test_reject_leaves_unit_unchanged(tmp_path) -> None:
    context = _build_context(tmp_path, "reject")

    report = context["lost_reports"].create_report(_create_command(context))
    reviewed = context["lost_reports"].review_report(
        report.id,
        ReviewLostReport(
            approved=False,
            reviewed_by_staff_id=context["staff"].id,
            review_note="Duplicate report",
        ),
    )

    assert reviewed.status is LostReportStatus.REJECTED
    assert reviewed.review_note == "Duplicate report"
    assert reviewed.reviewed_at == FIXED_NOW
    with connect(context["path"]) as database:
        unit_status = database.execute(
            "SELECT status FROM equipment_units WHERE id = ?",
            (context["unit"].id,),
        ).fetchone()[0]
        lost_case_count = database.execute(
            "SELECT COUNT(*) FROM lost_cases"
        ).fetchone()[0]
    assert unit_status == UnitStatus.BORROWED.value
    assert lost_case_count == 0
    assert context["lost_reports"].list_pending_reports() == []


def test_pending_list_excludes_reviewed_reports(tmp_path) -> None:
    context = _build_context(tmp_path, "lists")

    first = context["lost_reports"].create_report(_create_command(context))
    context["lost_reports"].review_report(
        first.id,
        ReviewLostReport(
            approved=False, reviewed_by_staff_id=context["staff"].id
        ),
    )
    second = context["lost_reports"].create_report(
        _create_command(context, unit_id=context["free_unit"].id)
    )

    assert context["lost_reports"].list_pending_reports() == [second]
    assert len(
        context["lost_reports"].list_reports_for_borrower(context["borrower"].id)
    ) == 2


def test_review_twice_raises(tmp_path) -> None:
    context = _build_context(tmp_path, "review-twice")

    report = context["lost_reports"].create_report(_create_command(context))
    context["lost_reports"].review_report(report.id, _approve(context, report.id))

    with pytest.raises(ReportAlreadyReviewed):
        context["lost_reports"].review_report(
            report.id, _approve(context, report.id)
        )


def test_review_unknown_report_raises(tmp_path) -> None:
    context = _build_context(tmp_path, "review-unknown")

    with pytest.raises(NotFoundError):
        context["lost_reports"].review_report(999, _approve(context, 999))


def test_review_with_inactive_staff_raises(tmp_path) -> None:
    context = _build_context(tmp_path, "review-inactive-staff")

    report = context["lost_reports"].create_report(_create_command(context))

    with pytest.raises(InactiveRecordError):
        context["lost_reports"].review_report(
            report.id,
            ReviewLostReport(
                approved=True,
                reviewed_by_staff_id=context["inactive_staff"].id,
            ),
        )
    assert context["lost_reports"].list_pending_reports() == [report]


def test_adapter_facade_exposes_lost_report_methods(tmp_path) -> None:
    context = _build_context(tmp_path, "facade")
    adapter = SQLiteInventoryAdapter(context["path"])

    report = adapter.create_lost_report(_create_command(context))

    assert adapter.list_pending_lost_reports() == [report]
    assert adapter.list_lost_reports_for_borrower(context["borrower"].id) == [report]
    reviewed = adapter.review_lost_report(report.id, _approve(context, report.id))
    assert reviewed.status is LostReportStatus.APPROVED
    assert adapter.list_pending_lost_reports() == []
