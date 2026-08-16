from __future__ import annotations

import pytest

from app.contracts import (
    CreateLostReport,
    LostReportStatus,
    ReviewLostReport,
)
from app.errors import (
    InactiveRecordError,
    NotFoundError,
    ReportAlreadyReviewed,
    ValidationError,
)
from app.services.fake_services import FakeInventoryService


@pytest.fixture
def service() -> FakeInventoryService:
    return FakeInventoryService()


def _create_command(**overrides: object) -> CreateLostReport:
    values: dict[str, object] = {
        "borrower_id": 1,
        "equipment_unit_id": 2,
        "lost_date": "2026-08-15",
        "location": "Lab A",
        "description": "Lost during field work",
    }
    values.update(overrides)
    return CreateLostReport(**values)  # type: ignore[arg-type]


def test_create_lost_report_stores_fields_and_is_pending(service) -> None:
    report = service.create_lost_report(_create_command())

    assert report.id == 1
    assert report.borrower_id == 1
    assert report.equipment_unit_id == 2
    assert report.lost_date == "2026-08-15"
    assert report.location == "Lab A"
    assert report.description == "Lost during field work"
    assert report.status is LostReportStatus.PENDING
    assert report.reviewed_by_staff_id is None
    assert report.reviewed_at is None
    assert report.review_note is None
    assert report.reported_at == report.created_at
    assert service.list_pending_lost_reports() == [report]


def test_create_lost_report_with_unknown_borrower_raises(service) -> None:
    with pytest.raises(NotFoundError):
        service.create_lost_report(_create_command(borrower_id=99))


def test_create_lost_report_with_inactive_borrower_raises(service) -> None:
    with pytest.raises(InactiveRecordError):
        service.create_lost_report(_create_command(borrower_id=2))


def test_create_lost_report_with_unit_not_borrowed_raises(service) -> None:
    with pytest.raises(ValidationError) as captured:
        service.create_lost_report(_create_command(equipment_unit_id=1))

    assert captured.value.field == "equipment_unit_id"


def test_list_lost_reports_for_borrower_filters(service) -> None:
    first = service.create_lost_report(_create_command())
    second = service.create_lost_report(_create_command(lost_date="2026-08-16"))

    assert service.list_lost_reports_for_borrower(1) == [first, second]
    assert service.list_lost_reports_for_borrower(2) == []


def test_review_reject_updates_report_and_leaves_unit(service) -> None:
    report = service.create_lost_report(_create_command())

    reviewed = service.review_lost_report(
        report.id, ReviewLostReport(approved=False, reviewed_by_staff_id=1, review_note="Duplicate")
    )

    assert reviewed.status is LostReportStatus.REJECTED
    assert reviewed.reviewed_by_staff_id == 1
    assert reviewed.reviewed_at is not None
    assert reviewed.review_note == "Duplicate"
    assert service.get_unit_by_id("unit-2").status == "borrowed"
    assert service.list_lost_cases() == service._lost_cases
    assert service.list_pending_lost_reports() == []


def test_review_approve_marks_unit_lost_and_opens_lost_case(service) -> None:
    report = service.create_lost_report(_create_command())
    cases_before = len(service._lost_cases)

    reviewed = service.review_lost_report(
        report.id, ReviewLostReport(approved=True, reviewed_by_staff_id=1, review_note="Confirmed")
    )

    assert reviewed.status is LostReportStatus.APPROVED
    assert reviewed.reviewed_by_staff_id == 1
    unit = service.get_unit_by_id("unit-2")
    assert unit.status == "reported_lost"
    assert len(service._lost_cases) == cases_before + 1
    case = service._lost_cases[-1]
    assert case.asset_code == "AST-002"
    assert case.equipment_name == "Laptop"
    assert case.borrower_code == "BR-001"
    assert case.resolution is None
    assert service.list_pending_lost_reports() == []


def test_review_rejected_report_twice_raises(service) -> None:
    report = service.create_lost_report(_create_command())
    service.review_lost_report(
        report.id, ReviewLostReport(approved=False, reviewed_by_staff_id=1)
    )

    with pytest.raises(ReportAlreadyReviewed):
        service.review_lost_report(
            report.id, ReviewLostReport(approved=True, reviewed_by_staff_id=1)
        )


def test_review_unknown_report_raises(service) -> None:
    with pytest.raises(NotFoundError):
        service.review_lost_report(
            999, ReviewLostReport(approved=True, reviewed_by_staff_id=1)
        )


def test_review_with_unknown_staff_raises(service) -> None:
    report = service.create_lost_report(_create_command())

    with pytest.raises(NotFoundError):
        service.review_lost_report(
            report.id, ReviewLostReport(approved=True, reviewed_by_staff_id=99)
        )


def test_review_with_inactive_staff_raises(service) -> None:
    report = service.create_lost_report(_create_command())

    with pytest.raises(InactiveRecordError):
        service.review_lost_report(
            report.id, ReviewLostReport(approved=True, reviewed_by_staff_id=2)
        )
