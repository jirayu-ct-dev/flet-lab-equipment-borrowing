import flet as ft

from app.components.common import (
    build_card,
    build_page_header,
    build_state_view,
    build_status_chip,
    update_control,
)
from app.services.fake_services import FakeInventoryService, LoanRecord
from app.theme import COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY


class LoansView(ft.Container):
    def __init__(self, service: FakeInventoryService | None = None) -> None:
        super().__init__(expand=True, padding=0)
        self.service = service or FakeInventoryService()

        self.filter_dropdown = ft.Dropdown(
            label="กรองสถานะสัญญายืม",
            options=[
                ft.dropdown.Option("all", "สัญญายืมทั้งหมด"),
                ft.dropdown.Option("today", "ครบกำหนดวันนี้"),
                ft.dropdown.Option("soon", "ใกล้ครบกำหนด (ใน 7 วัน)"),
                ft.dropdown.Option("overdue", "เกินกำหนดคืน"),
                ft.dropdown.Option("partial", "คืนบางส่วน"),
            ],
            value="all",
            width=220,
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
                ft.dropdown.Option("reported_lost", "แจ้งสูญหาย"),
            ],
            value="returned",
            expand=True,
        )
        self.return_action_dropdown.on_change = self._handle_return_action_change

        self.receiving_staff_dropdown = ft.Dropdown(
            label="เจ้าหน้าที่ผู้รับคืน",
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
            expand=True,
        )

        self.selected_units_container = ft.Container(expand=True)
        self.confirmation_summary = ft.Text("เลือกหน่วยและผลลัพธ์ก่อนยืนยัน", size=13, color=COLOR_TEXT_SECONDARY)
        self.feedback = ft.Text("", size=13, color=COLOR_TEXT_SECONDARY, weight=ft.FontWeight.W_500)

        self._build_view()

    def _build_view(self) -> None:
        header = build_page_header(
            title="สัญญายืม & คืนอุปกรณ์",
            subtitle="จัดการสัญญายืม และดำเนินการรับคืนอุปกรณ์ทั้งแบบบางส่วนหรือทั้งหมด",
            icon=ft.Icons.RECEIPT_LONG,
        )

        filter_bar = build_card(
            content=ft.Row(
                controls=[
                    self.filter_dropdown,
                    ft.OutlinedButton(
                        "รีเฟรชข้อมูล",
                        icon=ft.Icons.REFRESH,
                        on_click=self._handle_refresh,
                    ),
                ],
                spacing=12,
            ),
        )

        return_form_card = build_card(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.ASSIGNMENT_TURNED_IN, color=ft.Colors.BLUE_600, size=20),
                            ft.Text("ดำเนินการคืนอุปกรณ์", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                        ],
                        spacing=8,
                    ),
                    self.selected_units_container,
                    ft.Divider(height=12, color=ft.Colors.GREY_200),
                    ft.Row(
                        controls=[
                            self.return_action_dropdown,
                            self.return_notes,
                        ],
                        spacing=12,
                    ),
                    ft.Row(
                        controls=[self.receiving_staff_dropdown, self.return_location_dropdown],
                        spacing=12,
                    ),
                    ft.Row(
                        controls=[
                            ft.ElevatedButton(
                                "ยืนยันการรับคืน",
                                icon=ft.Icons.CHECK_CIRCLE,
                                style=ft.ButtonStyle(
                                    color=ft.Colors.WHITE,
                                    bgcolor=ft.Colors.GREEN_600,
                                    padding=ft.Padding.symmetric(horizontal=20, vertical=12),
                                ),
                                on_click=self._handle_confirm_return,
                            ),
                            self.confirmation_summary,
                        ],
                        spacing=16,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.feedback,
                ],
                spacing=12,
            ),
        )

        self.content = ft.Column(
            controls=[
                header,
                filter_bar,
                self.loan_container,
                return_form_card,
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
        if not loan_list:
            self.loan_container.content = build_state_view("ไม่มีสัญญายืม", "ไม่มีสัญญายืมที่ตรงกับตัวกรองนี้", icon=ft.Icons.RECEIPT_LONG_OUTLINED)
            self.selected_loan = None
            self.selected_unit_ids = []
            self._render_selected_units()
            self._update_confirmation_summary()
            return

        cards: list[ft.Container] = []
        for loan in loan_list:
            is_overdue = loan.status == "overdue"

            card_content = ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.RECEIPT, size=18, color=ft.Colors.RED_600 if is_overdue else ft.Colors.BLUE_600),
                            ft.Text(f"สัญญายืม {loan.id}", weight=ft.FontWeight.BOLD, size=15, color=COLOR_TEXT_PRIMARY),
                            ft.Container(expand=True),
                            build_status_chip(loan.status, self._translate_loan_status(loan.status)),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Divider(height=8, color=ft.Colors.GREY_200),
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.PERSON_OUTLINE, size=14, color=COLOR_TEXT_SECONDARY),
                            ft.Text(f"ผู้ยืม: {loan.borrower_code}", size=12, color=COLOR_TEXT_PRIMARY),
                            ft.Icon(ft.Icons.BADGE_OUTLINED, size=14, color=COLOR_TEXT_SECONDARY),
                            ft.Text(f"เจ้าหน้าที่: {loan.staff_code}", size=12, color=COLOR_TEXT_PRIMARY),
                        ],
                        spacing=12,
                    ),
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.ERROR_OUTLINE if is_overdue else ft.Icons.CALENDAR_MONTH,
                                size=14,
                                color=ft.Colors.RED_600 if is_overdue else COLOR_TEXT_SECONDARY,
                            ),
                            ft.Text(
                                f"ครบกำหนด: {loan.due_date}",
                                size=12,
                                weight=ft.FontWeight.BOLD if is_overdue else ft.FontWeight.NORMAL,
                                color=ft.Colors.RED_700 if is_overdue else COLOR_TEXT_PRIMARY,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, size=14, color=COLOR_TEXT_SECONDARY),
                            ft.Text(f"หน่วยในสัญญา: {', '.join(loan.unit_ids)}", size=12, color=COLOR_TEXT_SECONDARY),
                        ],
                        spacing=4,
                    ),
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=14, color=ft.Colors.GREEN_600),
                            ft.Text(f"คืนแล้ว: {', '.join(loan.returned_unit_ids) or 'ยังไม่มี'}", size=12, color=COLOR_TEXT_SECONDARY),
                        ],
                        spacing=4,
                    ),
                    ft.ElevatedButton(
                        "เลือกสัญญานี้เพื่อคืน",
                        icon=ft.Icons.CHECK_BOX,
                        style=ft.ButtonStyle(
                            color=ft.Colors.WHITE,
                            bgcolor=ft.Colors.BLUE_600 if self.selected_loan and self.selected_loan.id == loan.id else ft.Colors.GREY_700,
                            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                        ),
                        on_click=lambda e, loan=loan: self._select_loan(e, loan),
                    ),
                ],
                spacing=8,
                tight=True,
            )

            card = build_card(
                content=card_content,
                padding=14,
                width=340,
                border_color=ft.Colors.RED_300 if is_overdue else None,
                bgcolor=ft.Colors.RED_50 if is_overdue else ft.Colors.WHITE,
            )
            cards.append(card)

        self.loan_container.content = ft.Row(controls=cards, wrap=True, spacing=12, run_spacing=12)

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
                content=ft.Text("ขั้นตอนที่ 1: เลือกสัญญายืมจากรายการด้านบนเพื่อเลือกหน่วยที่จะคืน", size=13, color=COLOR_TEXT_SECONDARY),
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
                content=ft.Text("หน่วยทั้งหมดได้ถูกคืนแล้วสำหรับสัญญานี้ (สัญญาเสร็จสิ้น)", size=13, color=ft.Colors.GREEN_800),
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
                    f"เลือกหน่วยที่จะคืนสำหรับสัญญา {self.selected_loan.id}:",
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
            self.confirmation_summary.value = "เลือกสัญญายืมก่อนดำเนินการคืน"
            self.confirmation_summary.color = COLOR_TEXT_SECONDARY
            return

        if not self.selected_unit_ids:
            self.confirmation_summary.value = "เลือกอย่างน้อย 1 หน่วยอุปกรณ์ที่จะคืน"
            self.confirmation_summary.color = COLOR_TEXT_SECONDARY
            return

        if not self.receiving_staff_dropdown.value:
            self.feedback.value = "กรุณาเลือกเจ้าหน้าที่ผู้รับคืน"
            self.feedback.color = ft.Colors.RED_700
            update_control(self)
            return

        if self.return_action_dropdown.value != "reported_lost" and not self.return_location_dropdown.value:
            self.feedback.value = "กรุณาเลือกตำแหน่งจัดเก็บหลังคืน"
            self.feedback.color = ft.Colors.RED_700
            update_control(self)
            return

        action = self.return_action_dropdown.value or "returned"
        action_text = self._translate_return_action(action)
        self.confirmation_summary.value = (
            f"พร้อมคืน {len(self.selected_unit_ids)} หน่วย ในสถานะ '{action_text}'"
        )
        self.confirmation_summary.color = ft.Colors.BLUE_700

    def _select_loan(self, e: ft.ControlEvent, loan: LoanRecord) -> None:
        self.selected_loan = loan
        self.selected_unit_ids = list(
            unit_id for unit_id in loan.unit_ids if unit_id not in loan.returned_unit_ids
        )
        self.feedback.value = f"เลือกสัญญายืม {loan.id} แล้ว"
        self.feedback.color = ft.Colors.BLUE_700
        self._render_loans()
        self._render_selected_units()
        self._update_confirmation_summary()
        update_control(self)

    def _handle_filter_change(self, e: ft.ControlEvent) -> None:
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
        if self.selected_loan is None:
            self.feedback.value = "กรุณาเลือกสัญญายืมก่อน"
            self.feedback.color = ft.Colors.RED_700
            update_control(self)
            return

        if not self.selected_unit_ids:
            self.feedback.value = "กรุณาเลือกหน่วยอย่างน้อยหนึ่งหน่วยที่จะคืน"
            self.feedback.color = ft.Colors.RED_700
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
            self.feedback.value = "ไม่สามารถดำเนินการคืนได้ กรุณาตรวจสอบหน่วยและสถานะสัญญายืม"
            self.feedback.color = ft.Colors.RED_700
            update_control(self)
            return

        returned_count = len(self.selected_unit_ids)
        self.feedback.value = (
            f"Returned {returned_count} unit(s) for loan {result.id} "
            f"(คืนสำเร็จ {returned_count} หน่วย สถานะสัญญา: {self._translate_loan_status(result.status)})"
        )
        self.feedback.color = ft.Colors.GREEN_700
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
        update_control(self)
