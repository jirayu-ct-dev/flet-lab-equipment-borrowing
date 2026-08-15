import flet as ft

from app.components.common import (
    build_card,
    build_card_list,
    build_data_card,
    build_filter_bar,
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
from app.contracts import AppUser, Permission, has_permission
from app.services.fake_services import FakeInventoryService, LoanRecord
from app.theme import COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, CONTROL_RADIUS


class LoansView(ft.Container):
    def __init__(
        self,
        service: FakeInventoryService | None = None,
        *,
        mobile: bool = False,
        current_user: AppUser | None = None,
    ) -> None:
        super().__init__(expand=True, padding=0)
        self.service = service or FakeInventoryService()
        self.mobile = mobile
        self.current_user = current_user
        self._table_width: float | None = None
        self._surface_width: float | None = None

        self.search_field = ft.TextField(
            label="ค้นหารายการยืมหรือผู้ยืม",
            hint_text="เช่น loan-1 หรือ BR-001",
            prefix_icon=ft.Icons.SEARCH,
            width=float("inf"),
            height=52,
            border_radius=CONTROL_RADIUS,
            on_change=self._handle_search,
            on_submit=self._handle_search,
        )
        self.filter_dropdown = ft.Dropdown(
            label="กรองรายการยืม",
            options=[
                ft.dropdown.Option("all", "รายการทั้งหมด"),
                ft.dropdown.Option("today", "ครบกำหนดวันนี้"),
                ft.dropdown.Option("soon", "ใกล้ครบกำหนด (ใน 7 วัน)"),
                ft.dropdown.Option("overdue", "เกินกำหนดคืน"),
                ft.dropdown.Option("partial", "คืนบางส่วน"),
            ],
            value="all",
            expand=True,
            height=52,
            border_radius=CONTROL_RADIUS,
        )
        self.filter_dropdown.on_change = self._handle_filter_change

        self.loan_container = ft.Container(expand=True)
        self.selected_loan: LoanRecord | None = None
        self.selected_unit_ids: list[str] = []

        self.return_action_dropdown = ft.Dropdown(
            label="ผลลัพธ์การคืน",
            options=[
                ft.dropdown.Option("returned", "คืนแล้ว (สภาพสมบูรณ์)"),
                ft.dropdown.Option("maintenance", "ส่งซ่อมบำรุง"),
            ],
            value="returned",
            expand=True,
        )
        self.return_action_dropdown.on_change = self._handle_return_action_change

        self.receiving_staff_dropdown = ft.Dropdown(
            label="ผู้บันทึกการคืน",
            options=[ft.dropdown.Option(item.staff_code, f"{item.staff_code} — {item.full_name}") for item in self.service.list_staff()],
            expand=True,
        )
        self.return_location_dropdown = ft.Dropdown(
            label="ตำแหน่งจัดเก็บหลังคืน",
            options=[ft.dropdown.Option(item.id, item.label) for item in self.service.list_locations()],
            expand=True,
        )
        if self.receiving_staff_dropdown.options:
            self.receiving_staff_dropdown.value = self.receiving_staff_dropdown.options[0].key
        if self.return_location_dropdown.options:
            self.return_location_dropdown.value = self.return_location_dropdown.options[0].key

        self.return_notes = ft.TextField(
            label="สภาพอุปกรณ์ / หมายเหตุ",
            hint_text="ระบุสภาพของอุปกรณ์ที่นำมาคืน...",
            prefix_icon=ft.Icons.NOTE_ALT_OUTLINED,
        )
        self.return_action_row = ft.Row(
            controls=[self.return_action_dropdown], spacing=0, width=float("inf")
        )
        self.receiving_staff_row = ft.Row(
            controls=[self.receiving_staff_dropdown], spacing=0, width=float("inf")
        )
        self.return_location_row = ft.Row(
            controls=[self.return_location_dropdown], spacing=0, width=float("inf")
        )

        self.selected_units_container = ft.Container(expand=True)
        self.confirmation_summary = ft.Text("เลือกรายการและอุปกรณ์ที่จะคืน", size=13, color=COLOR_TEXT_SECONDARY)
        self.feedback = ft.Text("", size=13, color=COLOR_TEXT_SECONDARY, weight=ft.FontWeight.W_500)
        self.return_form_feedback = ft.Text("", size=13, color=COLOR_TEXT_SECONDARY, weight=ft.FontWeight.W_500)
        self.return_dialog = build_form_dialog(
            title="บันทึกการคืน",
            icon=ft.Icons.ASSIGNMENT_TURNED_IN,
            content=ft.Column(
                controls=[
                    self.selected_units_container,
                    ft.Divider(height=12, color=ft.Colors.GREY_200),
                    self.return_action_row,
                    self.return_notes,
                    self.receiving_staff_row,
                    self.return_location_row,
                    self.confirmation_summary,
                    self.return_form_feedback,
                ],
                spacing=12,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            save_label="ยืนยันการรับคืน",
            on_save=self._handle_confirm_return,
            on_cancel=lambda e: close_dialog(self, self.return_dialog),
        )

        self._build_view()
        self.on_size_change = self._handle_resize

    def _build_view(self) -> None:
        header = build_page_header(
            title="คืนอุปกรณ์",
            subtitle="เลือกรายการยืม แล้วบันทึกอุปกรณ์ที่นำมาคืน",
            icon=ft.Icons.RECEIPT_LONG,
        )

        refresh_button = ft.OutlinedButton(
            "รีเฟรช",
            icon=ft.Icons.REFRESH,
            height=52,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=CONTROL_RADIUS),
            ),
            on_click=self._handle_refresh,
        )
        if self.mobile:
            self.search_field.width = float("inf")
            self.filter_dropdown.width = None
            self.filter_dropdown.expand = True
            filter_bar = build_card(
                content=ft.Column(
                    controls=[
                        self.search_field,
                        ft.Row(
                            controls=[self.filter_dropdown, refresh_button],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=12,
                    tight=True,
                ),
                padding=16,
            )
        else:
            self.search_field.width = float("inf")
            self.filter_dropdown.width = 320
            self.filter_dropdown.expand = None
            filter_bar = build_filter_bar(
                search_control=self.search_field,
                action_controls=[self.filter_dropdown, refresh_button],
            )

        self.content = ft.Column(
            controls=[
                header,
                filter_bar,
                self.loan_container,
                self.feedback,
            ],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        self._render_loans()
        self._render_selected_units()

    def _translate_loan_status(self, status: str) -> str:
        return {
            "active": "กำลังยืม",
            "overdue": "เกินกำหนด",
            "partial": "คืนบางส่วน",
            "closed": "ปิดสัญญา",
        }.get(status, status.title())

    def _translate_return_action(self, action: str) -> str:
        return {
            "returned": "คืนแล้ว",
            "maintenance": "ซ่อมบำรุง",
            "reported_lost": "แจ้งหาย",
        }.get(action, action.title())

    def _render_loans(self) -> None:
        loan_list = self.service.list_loans(filter_type=self.filter_dropdown.value)
        query = (self.search_field.value or "").strip().lower()
        if query:
            loan_list = [
                loan
                for loan in loan_list
                if query in loan.id.lower() or query in loan.borrower_code.lower()
            ]
        if not loan_list:
            self.loan_container.content = build_state_view(
                "ไม่พบรายการยืม",
                "ลองเปลี่ยนคำค้นหาหรือตัวกรองรายการ",
                icon=ft.Icons.RECEIPT_LONG_OUTLINED,
            )
            self.selected_loan = None
            self.selected_unit_ids = []
            self._render_selected_units()
            self._update_confirmation_summary()
            return

        if self.mobile:
            self.loan_container.content = build_card_list(
                [
                    build_data_card(
                        title=f"รายการยืม {loan.id}",
                        icon=ft.Icons.RECEIPT_LONG_OUTLINED,
                        status=(loan.status, self._translate_loan_status(loan.status)),
                        fields=[
                            ("ครบกำหนด", loan.due_date),
                            ("คืนแล้ว", f"{len(loan.returned_unit_ids)} / {len(loan.unit_ids)} ชิ้น"),
                            ("ผู้ยืม", loan.borrower_code),
                            ("ผู้บันทึก", loan.staff_code),
                        ],
                        actions=[
                            ft.Button(
                                "บันทึกการคืน",
                                icon=ft.Icons.CHECK_BOX,
                                color=ft.Colors.WHITE,
                                bgcolor=ft.Colors.BLUE_600,
                                expand=True,
                                on_click=lambda e, loan=loan: self._open_return_dialog(e, loan),
                            )
                        ],
                    )
                    for loan in loan_list
                ]
            )
        else:
            table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("รายการ"), expand=2),
                    ft.DataColumn(ft.Text("ผู้ยืม"), expand=2),
                    ft.DataColumn(ft.Text("ผู้บันทึก"), expand=2),
                    ft.DataColumn(ft.Text("ครบกำหนด"), expand=2),
                    ft.DataColumn(ft.Text("สถานะ"), expand=2),
                    ft.DataColumn(ft.Text("คืนแล้ว"), expand=2),
                    ft.DataColumn(ft.Text("จัดการ"), expand=2),
                ],
                rows=[
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(f"รายการยืม {loan.id}", weight=ft.FontWeight.W_600)),
                            ft.DataCell(ft.Text(loan.borrower_code)),
                            ft.DataCell(ft.Text(loan.staff_code)),
                            ft.DataCell(
                                ft.Text(
                                    loan.due_date,
                                    color=ft.Colors.RED_700 if loan.status == "overdue" else COLOR_TEXT_PRIMARY,
                                    weight=ft.FontWeight.W_600 if loan.status == "overdue" else ft.FontWeight.NORMAL,
                                )
                            ),
                            ft.DataCell(build_status_chip(loan.status, self._translate_loan_status(loan.status))),
                            ft.DataCell(ft.Text(f"{len(loan.returned_unit_ids)} / {len(loan.unit_ids)} ชิ้น")),
                            ft.DataCell(
                                ft.Button(
                                    "บันทึกการคืน",
                                    icon=ft.Icons.CHECK_BOX,
                                    color=ft.Colors.WHITE,
                                    bgcolor=(
                                        ft.Colors.BLUE_600
                                        if self.selected_loan and self.selected_loan.id == loan.id
                                        else ft.Colors.GREY_700
                                    ),
                                    on_click=lambda e, loan=loan: self._open_return_dialog(e, loan),
                                )
                            ),
                        ]
                    )
                    for loan in loan_list
                ],
                column_spacing=24,
                horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_200),
            )
            self.loan_container.content = build_table_surface(
                table,
                table_width=1150,
                initial_width=(
                    self._surface_width
                    if self._surface_width is not None
                    else self._table_width
                ),
                on_resized=self._record_surface_width,
            )

        if self.selected_loan is not None:
            refreshed_loan = self.service.get_loan(self.selected_loan.id)
            if refreshed_loan is None or refreshed_loan.id not in [loan.id for loan in loan_list]:
                self.selected_loan = None
                self.selected_unit_ids = []

        self._render_selected_units()
        self._update_confirmation_summary()

    def _render_selected_units(self) -> None:
        if self.selected_loan is None:
            self.selected_units_container.content = ft.Container(
                padding=12,
                bgcolor=ft.Colors.GREY_100,
                border_radius=8,
                content=ft.Text("เลือกรายการยืมจากรายการด้านบนก่อน", size=13, color=COLOR_TEXT_SECONDARY),
            )
            return

        selectable_units = [
            unit_id for unit_id in self.selected_loan.unit_ids if unit_id not in self.selected_loan.returned_unit_ids
        ]
        if not selectable_units:
            self.selected_units_container.content = ft.Container(
                padding=12,
                bgcolor=ft.Colors.GREEN_50,
                border_radius=8,
                content=ft.Text("คืนอุปกรณ์ในรายการนี้ครบแล้ว", size=13, color=ft.Colors.GREEN_800),
            )
            self.selected_unit_ids = []
            return

        controls: list[ft.Checkbox] = []
        for unit_id in selectable_units:
            unit = self.service.get_unit_by_id(unit_id)
            label = unit.asset_code if unit is not None else unit_id
            if unit is not None:
                label = f"{unit.asset_code} — {unit.equipment_name}"
            controls.append(
                ft.Checkbox(
                    label=label,
                    value=unit_id in self.selected_unit_ids,
                    on_change=lambda e, unit_id=unit_id: self._toggle_selected_unit(e, unit_id),
                )
            )

        self.selected_units_container.content = ft.Column(
            controls=[
                ft.Text(
                    f"เลือกอุปกรณ์ที่จะคืนจากรายการ {self.selected_loan.id}:",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=COLOR_TEXT_PRIMARY,
                ),
                *controls,
            ],
            spacing=6,
        )

    def _toggle_selected_unit(self, e: ft.ControlEvent, unit_id: str) -> None:
        if unit_id in self.selected_unit_ids:
            self.selected_unit_ids.remove(unit_id)
        else:
            self.selected_unit_ids.append(unit_id)
        self._update_confirmation_summary()
        self._render_selected_units()
        update_control(self)

    def _update_confirmation_summary(self) -> None:
        if self.selected_loan is None:
            self.confirmation_summary.value = "เลือกรายการยืมก่อน"
            self.confirmation_summary.color = COLOR_TEXT_SECONDARY
            return

        if not self.selected_unit_ids:
            self.confirmation_summary.value = "เลือกอุปกรณ์ที่จะคืนอย่างน้อย 1 ชิ้น"
            self.confirmation_summary.color = COLOR_TEXT_SECONDARY
            return

        if not self.receiving_staff_dropdown.value:
            self.return_form_feedback.value = "กรุณาเลือกผู้บันทึกการคืน"
            self.return_form_feedback.color = ft.Colors.RED_700
            update_control(self)
            return

        if self.return_action_dropdown.value != "reported_lost" and not self.return_location_dropdown.value:
            self.return_form_feedback.value = "กรุณาเลือกตำแหน่งจัดเก็บหลังคืน"
            self.return_form_feedback.color = ft.Colors.RED_700
            update_control(self)
            return

        action = self.return_action_dropdown.value or "returned"
        action_text = self._translate_return_action(action)
        self.confirmation_summary.value = (
            f"พร้อมคืน {len(self.selected_unit_ids)} ชิ้น: {action_text}"
        )
        self.confirmation_summary.color = ft.Colors.BLUE_700

    def _open_return_dialog(self, e: ft.ControlEvent, loan: LoanRecord) -> None:
        self.return_form_feedback.value = ""
        self._select_loan(e, loan)
        self.feedback.value = ""
        open_dialog(self, self.return_dialog)
        update_control(self)

    def _select_loan(self, e: ft.ControlEvent, loan: LoanRecord) -> None:
        self.selected_loan = loan
        self.selected_unit_ids = list(
            unit_id for unit_id in loan.unit_ids if unit_id not in loan.returned_unit_ids
        )
        self.feedback.value = f"เลือกรายการยืม {loan.id} แล้ว"
        self.feedback.color = ft.Colors.BLUE_700
        self._render_loans()
        self._render_selected_units()
        self._update_confirmation_summary()
        update_control(self)

    def _record_surface_width(self, width: float) -> None:
        self._surface_width = width

    def _handle_resize(self, e: ft.LayoutSizeChangeEvent) -> None:
        self._table_width = e.width
        handle_mobile_resize(self, self._build_view, e)

    def _handle_filter_change(self, e: ft.ControlEvent) -> None:
        self._render_loans()
        update_control(self)

    def _handle_search(self, e: ft.ControlEvent | None) -> None:
        self._render_loans()
        update_control(self)

    def _handle_return_action_change(self, e: ft.ControlEvent) -> None:
        self._update_confirmation_summary()
        update_control(self)

    def _handle_refresh(self, e: ft.ControlEvent) -> None:
        self.selected_loan = None
        self.selected_unit_ids = []
        self.return_notes.value = ""
        self.feedback.value = ""
        self._render_loans()
        update_control(self)

    def _handle_confirm_return(self, e: ft.ControlEvent) -> None:
        if not has_permission(self.current_user, Permission.MANAGE_LOANS):
            self.return_form_feedback.value = "คุณไม่มีสิทธิ์ทำรายการนี้"
            self.return_form_feedback.color = ft.Colors.RED_700
            update_control(self)
            return

        if self.selected_loan is None:
            self.return_form_feedback.value = "กรุณาเลือกรายการยืมก่อน"
            self.return_form_feedback.color = ft.Colors.RED_700
            update_control(self)
            return

        if not self.selected_unit_ids:
            self.return_form_feedback.value = "กรุณาเลือกอุปกรณ์ที่จะคืนอย่างน้อย 1 ชิ้น"
            self.return_form_feedback.color = ft.Colors.RED_700
            update_control(self)
            return

        result = self.service.return_loan_units(
            self.selected_loan.id,
            self.selected_unit_ids,
            self.return_action_dropdown.value or "returned",
            condition=self.return_notes.value or None,
            staff_code=self.receiving_staff_dropdown.value,
            location_id=self.return_location_dropdown.value,
        )

        if result is None:
            self.return_form_feedback.value = "บันทึกการคืนไม่สำเร็จ กรุณาตรวจสอบรายการและลองใหม่"
            self.return_form_feedback.color = ft.Colors.RED_700
            update_control(self)
            return

        returned_count = len(self.selected_unit_ids)
        self.feedback.value = f"บันทึกการคืน {returned_count} ชิ้นเรียบร้อย"
        self.feedback.color = ft.Colors.GREEN_700
        self.return_form_feedback.value = ""
        self.return_notes.value = ""

        if result.status == "closed":
            self.selected_loan = None
            self.selected_unit_ids = []
        else:
            self.selected_loan = result
            self.selected_unit_ids = [
                unit_id
                for unit_id in result.unit_ids
                if unit_id not in result.returned_unit_ids
            ]

        self._render_loans()
        self._render_selected_units()
        self._update_confirmation_summary()
        close_dialog(self, self.return_dialog)
        update_control(self)
