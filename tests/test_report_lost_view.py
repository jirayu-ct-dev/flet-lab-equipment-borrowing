from datetime import datetime, timezone

import flet as ft

from app.contracts import (
    AppUser,
    CreateLostReport,
    LostReport,
    LostReportStatus,
    RecordStatus,
    ReviewLostReport,
    Role,
)
from app.services.fake_services import FakeInventoryService
from app.views.report_lost import ReportLostView
from tests.test_auth_fixtures import borrower_user


class SpyLostReportService(FakeInventoryService):
    def __init__(self) -> None:
        super().__init__()
        self.created: list[CreateLostReport] = []
        self.reports: list[LostReport] = []

    def create_lost_report(self, command: CreateLostReport) -> LostReport:
        self.created.append(command)
        report = LostReport(
            id=len(self.reports) + 1,
            borrower_id=command.borrower_id,
            equipment_unit_id=command.equipment_unit_id,
            reported_at=datetime.now(timezone.utc),
            lost_date=command.lost_date,
            location=command.location,
            description=command.description,
            status=LostReportStatus.PENDING,
            reviewed_by_staff_id=None,
            reviewed_at=None,
            review_note=None,
            created_at=datetime.now(timezone.utc),
        )
        self.reports.append(report)
        return report

    def list_lost_reports_for_borrower(self, borrower_id: int) -> list[LostReport]:
        return [report for report in self.reports if report.borrower_id == borrower_id]

    def list_pending_lost_reports(self) -> list[LostReport]:
        return [report for report in self.reports if report.status == LostReportStatus.PENDING]

    def review_lost_report(self, report_id: int, command: ReviewLostReport) -> LostReport:
        raise NotImplementedError


class NoLoansService(FakeInventoryService):
    def list_loans_for_borrower(
        self, borrower_id: int, *, filter_type: str | None = None
    ):
        return []


def _user_without_borrower() -> AppUser:
    return AppUser(
        id=3,
        role=Role.USER,
        display_name="ผู้ใช้ที่ไม่มีข้อมูลผู้ยืม",
        email="ghost@lab.local",
        staff_id=None,
        borrower_id=None,
        status=RecordStatus.ACTIVE,
        must_change_password=False,
        last_login_at=None,
    )


def _pending_report() -> LostReport:
    now = datetime(2026, 8, 10, 9, 30, tzinfo=timezone.utc)
    return LostReport(
        id=1,
        borrower_id=1,
        equipment_unit_id=2,
        reported_at=now,
        lost_date="2026-08-09",
        location="ห้องเรียน 402",
        description="ทำหายระหว่างเดินทาง",
        status=LostReportStatus.PENDING,
        reviewed_by_staff_id=None,
        reviewed_at=None,
        review_note=None,
        created_at=now,
    )


def test_report_lost_renders_permission_state_for_no_user() -> None:
    view = ReportLostView(FakeInventoryService())

    assert "ไม่มีสิทธิ์ใช้งานหน้านี้" in view.content.content.controls[1].value
    assert "กรุณาติดต่อเจ้าหน้าที่สาขา" in view.content.content.controls[2].value


def test_report_lost_renders_permission_state_without_borrower_id() -> None:
    view = ReportLostView(
        FakeInventoryService(), current_user=_user_without_borrower()
    )

    assert "ไม่มีสิทธิ์ใช้งานหน้านี้" in view.content.content.controls[1].value


def test_report_lost_desktop_table_lists_borrowed_units() -> None:
    view = ReportLostView(FakeInventoryService(), current_user=borrower_user())

    surface = view.borrowed_container.content
    table = surface.content.controls[0]
    assert isinstance(table, ft.DataTable)
    assert [column.label.value for column in table.columns] == [
        "รหัส",
        "ชื่ออุปกรณ์",
        "ครบกำหนดคืน",
        "สถานะ",
        "การแจ้ง",
    ]
    assert len(table.rows) == 1
    assert table.rows[0].cells[0].content.value == "AST-002"
    assert table.rows[0].cells[1].content.value == "Laptop"
    assert isinstance(table.rows[0].cells[4].content, ft.Button)


def test_report_lost_renders_empty_state_without_loans() -> None:
    view = ReportLostView(NoLoansService(), current_user=borrower_user())

    state = view.borrowed_container.content
    assert "ไม่มีอุปกรณ์ที่ยืมอยู่" in state.content.controls[1].value


def test_report_button_opens_dialog_with_form_fields() -> None:
    view = ReportLostView(FakeInventoryService(), current_user=borrower_user())

    table = view.borrowed_container.content.content.controls[0]
    button = table.rows[0].cells[4].content
    button.on_click(None)

    assert view.lost_report_dialog.open is True
    dialog_controls = view.lost_report_dialog.content.content.controls
    assert view.lost_date_field in dialog_controls
    assert view.location_field in dialog_controls
    assert view.description_field in dialog_controls


def test_submit_creates_lost_report_with_correct_ids() -> None:
    spy = SpyLostReportService()
    view = ReportLostView(spy, current_user=borrower_user())

    view._open_lost_dialog(None, "unit-2")
    view.lost_date_field.value = "2026-08-10"
    view.location_field.value = "ห้องเรียน 402"
    view.description_field.value = "ทำหายระหว่างเดินทาง"
    view._handle_submit_report(None)

    assert len(spy.created) == 1
    command = spy.created[0]
    assert command.borrower_id == 1
    assert command.equipment_unit_id == 2
    assert command.lost_date == "2026-08-10"
    assert command.location == "ห้องเรียน 402"
    assert command.description == "ทำหายระหว่างเดินทาง"
    assert view.lost_report_dialog.open is False
    assert view.feedback.value == "แจ้งอุปกรณ์หายเรียบร้อย รอเจ้าหน้าที่ตรวจสอบ"
    assert view.feedback.color == ft.Colors.GREEN_700


def test_past_reports_show_with_thai_status_labels() -> None:
    spy = SpyLostReportService()
    spy.reports.append(_pending_report())
    view = ReportLostView(spy, current_user=borrower_user())

    surface = view.reports_container.content
    table = surface.content.controls[0]
    assert isinstance(table, ft.DataTable)
    assert [column.label.value for column in table.columns] == [
        "วันที่แจ้ง",
        "อุปกรณ์",
        "สถานะ",
        "หมายเหตุผลการตรวจ",
    ]
    assert len(table.rows) == 1
    assert table.rows[0].cells[0].content.value == "2026-08-10 09:30"
    assert table.rows[0].cells[1].content.value == "AST-002"
    chip = table.rows[0].cells[2].content
    assert chip.content.controls[1].value == "รอตรวจสอบ"
    assert table.rows[0].cells[3].content.value == "-"


def test_report_lost_renders_cards_on_mobile() -> None:
    view = ReportLostView(
        FakeInventoryService(), current_user=borrower_user(), mobile=True
    )

    content = view.borrowed_container.content
    assert isinstance(content, ft.Column)
    assert isinstance(content.controls[0], ft.Container)
    header = content.controls[0].content.controls[0]
    assert isinstance(header, ft.Row)
    assert header.controls[1].value == "AST-002"
    action_rows = [
        control
        for control in content.controls[0].content.controls
        if isinstance(control, ft.Row)
        and any(isinstance(item, ft.Button) for item in control.controls)
    ]
    assert action_rows, "การ์ดมือถือควรมีปุ่มแจ้งหาย"
    assert action_rows[0].controls[0].content == "แจ้งหาย"
