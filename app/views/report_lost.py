from datetime import datetime

import flet as ft

from app.components.common import (
    build_card_list,
    build_data_card,
    build_form_dialog,
    build_page_header,
    build_state_view,
    build_status_chip,
    build_table_surface,
    close_dialog,
    handle_mobile_resize,
    open_dialog,
    update_control,
)
from app.contracts import AppUser, CreateLostReport, Permission, has_permission
from app.errors import DomainError
from app.services.fake_services import FakeInventoryService
from app.theme import COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY

_UNIT_STATUS_LABELS = {
    "available": "พร้อมใช้งาน",
    "borrowed": "ถูกยืม",
    "maintenance": "กำลังบำรุงรักษา",
    "reported_lost": "แจ้งหาย",
    "retired": "ปลดระวาง",
}

_LOST_REPORT_STATUS_THEME = {
    "pending": "open",
    "approved": "resolved",
    "rejected": "inactive",
}

_LOST_REPORT_STATUS_LABELS = {
    "pending": "รอตรวจสอบ",
    "approved": "อนุมัติแล้ว",
    "rejected": "ไม่อนุมัติ",
}


def _status_value(status: object) -> str:
    return getattr(status, "value", status)


def _format_datetime(value: datetime | str | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


class ReportLostView(ft.Container):
    """Borrower self-service: report borrowed units as lost and track reviews."""

    def __init__(
        self,
        service: FakeInventoryService | None = None,
        *,
        current_user: AppUser | None = None,
        mobile: bool = False,
    ) -> None:
        super().__init__(expand=True, padding=0)
        self.service = service or FakeInventoryService()
        self.mobile = mobile
        self.current_user = current_user
        self._table_width: float | None = None
        self._surface_width: float | None = None

        self.feedback = ft.Text(
            "", size=13, color=COLOR_TEXT_SECONDARY, weight=ft.FontWeight.W_500
        )
        self.form_feedback = ft.Text(
            "", size=13, color=COLOR_TEXT_SECONDARY, weight=ft.FontWeight.W_500
        )
        self.borrowed_container = ft.Container(expand=True)
        self.reports_container = ft.Container(expand=True)

        self._dialog_unit_id: str | None = None
        self.dialog_unit_text = ft.Text(
            "", size=13, color=COLOR_TEXT_SECONDARY, weight=ft.FontWeight.W_500
        )
        self.lost_date_field = ft.TextField(
            label="วันที่หาย (YYYY-MM-DD)",
            hint_text="เช่น 2026-08-10",
            prefix_icon=ft.Icons.DATE_RANGE,
        )
        self.location_field = ft.TextField(
            label="สถานที่ (ถ้าทราบ)",
            hint_text="เช่น ห้องเรียน 402",
        )
        self.description_field = ft.TextField(
            label="รายละเอียด",
            hint_text="อธิบายเหตุการณ์ที่เกิดขึ้น...",
            multiline=True,
            min_lines=3,
            max_lines=5,
        )
        self.lost_report_dialog = build_form_dialog(
            title="แจ้งอุปกรณ์หาย",
            icon=ft.Icons.REPORT_PROBLEM_OUTLINED,
            content=ft.Column(
                controls=[
                    self.dialog_unit_text,
                    self.lost_date_field,
                    self.location_field,
                    self.description_field,
                    self.form_feedback,
                ],
                spacing=12,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            save_label="ส่งรายงาน",
            on_save=self._handle_submit_report,
            on_cancel=lambda e: close_dialog(self, self.lost_report_dialog),
        )

        self._build_view()
        self.on_size_change = self._handle_resize

    def _build_view(self) -> None:
        if (
            not has_permission(self.current_user, Permission.VIEW_MY_LOANS)
            or self.current_user is None
        ):
            self.content = build_state_view(
                "ไม่มีสิทธิ์ใช้งานหน้านี้",
                "กรุณาติดต่อเจ้าหน้าที่สาขา",
                icon=ft.Icons.LOCK_OUTLINE,
            )
            return

        header = build_page_header(
            title="แจ้งอุปกรณ์หาย",
            subtitle="แจ้งอุปกรณ์ที่ยืมแล้วสูญหาย เพื่อให้เจ้าหน้าที่ตรวจสอบ",
            icon=ft.Icons.REPORT_PROBLEM_OUTLINED,
        )
        self.content = ft.Column(
            controls=[
                header,
                self.feedback,
                ft.Text(
                    "อุปกรณ์ที่ยืมอยู่",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=COLOR_TEXT_PRIMARY,
                ),
                self.borrowed_container,
                ft.Text(
                    "รายการที่เคยแจ้ง",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=COLOR_TEXT_PRIMARY,
                ),
                self.reports_container,
            ],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        self._render_borrowed_units()
        self._render_reports()

    def _render_borrowed_units(self) -> None:
        borrower_id = (
            self.current_user.borrower_id
            if self.current_user is not None
            else None
        )
        if borrower_id is None:
            self.borrowed_container.content = build_state_view(
                "ไม่มีอุปกรณ์ที่ยืมอยู่",
                "เมื่อคุณยืมอุปกรณ์แล้ว รายการจะแสดงที่นี่",
                icon=ft.Icons.REPORT_PROBLEM_OUTLINED,
            )
            return

        borrowed: list[tuple[object | None, str, str]] = []
        for loan in self.service.list_loans_for_borrower(borrower_id):
            for unit_id in loan.unit_ids:
                if unit_id not in loan.returned_unit_ids:
                    borrowed.append(
                        (self.service.get_unit_by_id(unit_id), unit_id, loan.due_date)
                    )

        if not borrowed:
            self.borrowed_container.content = build_state_view(
                "ไม่มีอุปกรณ์ที่ยืมอยู่",
                "เมื่อคุณยืมอุปกรณ์แล้ว รายการจะแสดงที่นี่",
                icon=ft.Icons.REPORT_PROBLEM_OUTLINED,
            )
            return

        if self.mobile:
            self.borrowed_container.content = build_card_list(
                [
                    build_data_card(
                        title=unit.asset_code if unit is not None else unit_id,
                        icon=ft.Icons.REPORT_PROBLEM_OUTLINED,
                        status=(
                            unit.status if unit is not None else "borrowed",
                            self._translate_unit_status(
                                unit.status if unit is not None else "borrowed"
                            ),
                        ),
                        fields=[
                            (
                                "ชื่ออุปกรณ์",
                                unit.equipment_name if unit is not None else "-",
                            ),
                            ("ครบกำหนดคืน", due_date),
                        ],
                        actions=[
                            ft.Button(
                                "แจ้งหาย",
                                icon=ft.Icons.REPORT_PROBLEM_OUTLINED,
                                color=ft.Colors.WHITE,
                                bgcolor=ft.Colors.RED_600,
                                expand=True,
                                on_click=lambda e, unit_id=unit_id: self._open_lost_dialog(
                                    e, unit_id
                                ),
                            )
                        ],
                    )
                    for unit, unit_id, due_date in borrowed
                ]
            )
            return

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("รหัส"), expand=2),
                ft.DataColumn(ft.Text("ชื่ออุปกรณ์"), expand=3),
                ft.DataColumn(ft.Text("ครบกำหนดคืน"), expand=2),
                ft.DataColumn(ft.Text("สถานะ"), expand=2),
                ft.DataColumn(ft.Text("การแจ้ง"), expand=2),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Text(
                                unit.asset_code if unit is not None else unit_id,
                                weight=ft.FontWeight.W_600,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(unit.equipment_name if unit is not None else "-")
                        ),
                        ft.DataCell(ft.Text(due_date)),
                        ft.DataCell(
                            build_status_chip(
                                unit.status if unit is not None else "borrowed",
                                self._translate_unit_status(
                                    unit.status if unit is not None else "borrowed"
                                ),
                            )
                        ),
                        ft.DataCell(
                            ft.Button(
                                "แจ้งหาย",
                                icon=ft.Icons.REPORT_PROBLEM_OUTLINED,
                                color=ft.Colors.WHITE,
                                bgcolor=ft.Colors.RED_600,
                                on_click=lambda e, unit_id=unit_id: self._open_lost_dialog(
                                    e, unit_id
                                ),
                            )
                        ),
                    ]
                )
                for unit, unit_id, due_date in borrowed
            ],
            column_spacing=24,
            horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_200),
        )
        self.borrowed_container.content = build_table_surface(
            table,
            table_width=1000,
            initial_width=(
                self._surface_width
                if self._surface_width is not None
                else self._table_width
            ),
            on_resized=self._record_surface_width,
        )

    def _render_reports(self) -> None:
        borrower_id = (
            self.current_user.borrower_id
            if self.current_user is not None
            else None
        )
        if borrower_id is None:
            self.reports_container.content = build_state_view(
                "ยังไม่มีรายการที่เคยแจ้ง",
                "รายการแจ้งอุปกรณ์หายที่เคยส่งจะแสดงที่นี่",
                icon=ft.Icons.REPORT_PROBLEM_OUTLINED,
            )
            return

        reports = self.service.list_lost_reports_for_borrower(borrower_id)
        if not reports:
            self.reports_container.content = build_state_view(
                "ยังไม่มีรายการที่เคยแจ้ง",
                "รายการแจ้งอุปกรณ์หายที่เคยส่งจะแสดงที่นี่",
                icon=ft.Icons.REPORT_PROBLEM_OUTLINED,
            )
            return

        if self.mobile:
            self.reports_container.content = build_card_list(
                [
                    build_data_card(
                        title=self._asset_code_for(report.equipment_unit_id),
                        icon=ft.Icons.REPORT_PROBLEM_OUTLINED,
                        status=(
                            self._report_theme_key(report.status),
                            self._translate_report_status(report.status),
                        ),
                        fields=[
                            ("วันที่แจ้ง", _format_datetime(report.reported_at)),
                            ("วันที่หาย", report.lost_date or "-"),
                            ("สถานที่", report.location or "-"),
                            ("รายละเอียด", report.description or "-"),
                            ("หมายเหตุผลการตรวจ", report.review_note or "-"),
                        ],
                        full_width_fields=["รายละเอียด", "หมายเหตุผลการตรวจ"],
                    )
                    for report in reports
                ]
            )
            return

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("วันที่แจ้ง"), expand=2),
                ft.DataColumn(ft.Text("อุปกรณ์"), expand=2),
                ft.DataColumn(ft.Text("สถานะ"), expand=2),
                ft.DataColumn(ft.Text("หมายเหตุผลการตรวจ"), expand=4),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(_format_datetime(report.reported_at))),
                        ft.DataCell(
                            ft.Text(
                                self._asset_code_for(report.equipment_unit_id),
                                weight=ft.FontWeight.W_600,
                            )
                        ),
                        ft.DataCell(
                            build_status_chip(
                                self._report_theme_key(report.status),
                                self._translate_report_status(report.status),
                            )
                        ),
                        ft.DataCell(ft.Text(report.review_note or "-")),
                    ]
                )
                for report in reports
            ],
            column_spacing=24,
            horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_200),
        )
        self.reports_container.content = build_table_surface(
            table,
            table_width=1000,
            initial_width=(
                self._surface_width
                if self._surface_width is not None
                else self._table_width
            ),
            on_resized=self._record_surface_width,
        )

    def _asset_code_for(self, unit_id: object) -> str:
        for candidate in (unit_id, f"unit-{unit_id}"):
            unit = self.service.get_unit_by_id(candidate)
            if unit is not None:
                return unit.asset_code
        return str(unit_id)

    @staticmethod
    def _translate_unit_status(status: str) -> str:
        return _UNIT_STATUS_LABELS.get(status, status.title())

    @staticmethod
    def _translate_report_status(status: object) -> str:
        value = _status_value(status)
        return _LOST_REPORT_STATUS_LABELS.get(value, value.title())

    @staticmethod
    def _report_theme_key(status: object) -> str:
        value = _status_value(status)
        return _LOST_REPORT_STATUS_THEME.get(value, value)

    def _open_lost_dialog(self, e: ft.ControlEvent, unit_id: str) -> None:
        self._dialog_unit_id = unit_id
        unit = self.service.get_unit_by_id(unit_id)
        self.dialog_unit_text.value = (
            f"อุปกรณ์: {unit.asset_code} — {unit.equipment_name}"
            if unit is not None
            else f"อุปกรณ์: {unit_id}"
        )
        self.lost_date_field.value = ""
        self.location_field.value = ""
        self.description_field.value = ""
        self.form_feedback.value = ""
        self.form_feedback.color = COLOR_TEXT_SECONDARY
        open_dialog(self, self.lost_report_dialog)
        update_control(self)

    def _handle_submit_report(self, e: ft.ControlEvent) -> None:
        if (
            not has_permission(self.current_user, Permission.VIEW_MY_LOANS)
            or self.current_user is None
            or self.current_user.borrower_id is None
        ):
            self._set_form_feedback("คุณไม่มีสิทธิ์ทำรายการนี้")
            return

        if self._dialog_unit_id is None:
            self._set_form_feedback("กรุณาเลือกอุปกรณ์ที่ต้องการแจ้ง")
            return

        try:
            report = self.service.create_lost_report(
                CreateLostReport(
                    borrower_id=self.current_user.borrower_id,
                    equipment_unit_id=int(
                        str(self._dialog_unit_id).removeprefix("unit-")
                    ),
                    lost_date=(self.lost_date_field.value or "").strip() or None,
                    location=(self.location_field.value or "").strip() or None,
                    description=(self.description_field.value or "").strip() or None,
                )
            )
        except DomainError as error:
            self._set_form_feedback(error.message)
            return

        if report is None:
            self._set_form_feedback("แจ้งอุปกรณ์หายไม่สำเร็จ กรุณาลองใหม่อีกครั้ง")
            return

        self.form_feedback.value = ""
        self.feedback.value = "แจ้งอุปกรณ์หายเรียบร้อย รอเจ้าหน้าที่ตรวจสอบ"
        self.feedback.color = ft.Colors.GREEN_700
        close_dialog(self, self.lost_report_dialog)
        self._render_borrowed_units()
        self._render_reports()
        update_control(self)

    def _set_form_feedback(self, message: str) -> None:
        self.form_feedback.value = message
        self.form_feedback.color = ft.Colors.RED_700
        update_control(self)

    def _record_surface_width(self, width: float) -> None:
        self._surface_width = width

    def _handle_resize(self, e: ft.LayoutSizeChangeEvent) -> None:
        self._table_width = e.width
        handle_mobile_resize(self, self._build_view, e)
