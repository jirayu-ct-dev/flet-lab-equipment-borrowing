from datetime import date, timedelta
import flet as ft

from app.components.common import build_card, build_page_header, update_control
from app.contracts import AppUser, Permission, has_permission
from app.database import bangkok_today
from app.services.fake_services import FakeInventoryService
from app.theme import COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY


class BorrowFlowView(ft.Container):
    def __init__(
        self,
        service: FakeInventoryService | None = None,
        *,
        current_user: AppUser | None = None,
    ) -> None:
        super().__init__(
            expand=True,
            padding=0,
        )

        self.service = service or FakeInventoryService()
        self.current_user = current_user

        borrowers = self.service.list_borrowers(include_inactive=False)
        staff = self.service.list_staff(include_inactive=False)
        units = self.service.search_units(status="available")

        self.borrower_dropdown = ft.Dropdown(
            label="ผู้ยืม",
            hint_text="เลือกผู้ยืม",
            expand=True,
            options=[
                ft.DropdownOption(
                    key=item.borrower_code,
                    text=f"{item.borrower_code} — {item.full_name}",
                )
                for item in borrowers
            ],
        )

        self.staff_dropdown = ft.Dropdown(
            label="ผู้บันทึกรายการ",
            hint_text="เลือกชื่อผู้บันทึก",
            expand=True,
            options=[
                ft.DropdownOption(
                    key=item.staff_code,
                    text=f"{item.staff_code} — {item.full_name}",
                )
                for item in staff
            ],
        )

        self.unit_dropdown = ft.Dropdown(
            label="อุปกรณ์ที่ต้องการยืม",
            hint_text="เลือกอุปกรณ์ที่พร้อมให้ยืม",
            expand=True,
            options=[
                ft.DropdownOption(
                    key=unit.id,
                    text=(
                        f"{unit.asset_code} - "
                        f"{unit.equipment_name} ("
                        f"{self._translate_unit_status(unit.status)})"
                    ),
                )
                for unit in units
            ],
        )

        self.borrow_date = ft.TextField(
            label="วันที่ยืม",
            hint_text="YYYY-MM-DD",
            prefix_icon=ft.Icons.CALENDAR_TODAY,
            value=bangkok_today().isoformat(),
            expand=True,
        )

        self.due_date = ft.TextField(
            label="วันที่ครบกำหนดคืน",
            hint_text="YYYY-MM-DD",
            prefix_icon=ft.Icons.EVENT_REPEAT,
            value=(bangkok_today() + timedelta(days=3)).isoformat(),
            expand=True,
        )

        self.purpose = ft.TextField(
            label="วัตถุประสงค์การยืม",
            hint_text="ระบุวัตถุประสงค์การยืม เช่น เพื่อใช้ในห้องปฏิบัติการวิจัย...",
            prefix_icon=ft.Icons.SUBTITLES,
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True,
        )

        self.note = ft.TextField(
            label="หมายเหตุเพิ่มเติม",
            hint_text="รายละเอียดเพิ่มเติม (ถ้ามี)",
            prefix_icon=ft.Icons.NOTE_ALT_OUTLINED,
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True,
        )

        self.summary = ft.Text(
            "กรอกข้อมูลให้ครบ แล้วกดบันทึกการยืม",
            size=13,
            color=COLOR_TEXT_SECONDARY,
        )

        self.create_button = ft.Button(
            "บันทึกการยืม",
            icon=ft.Icons.CHECK_CIRCLE,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
                padding=ft.Padding.symmetric(horizontal=20, vertical=12),
            ),
            on_click=self._handle_borrow,
        )

        self._build_view()

    def _translate_unit_status(self, status: str) -> str:
        return {
            "available": "พร้อมใช้งาน",
            "borrowed": "ถูกยืม",
            "maintenance": "กำลังบำรุงรักษา",
            "reported_lost": "แจ้งหาย",
            "retired": "ปลดระวาง",
        }.get(status, status)

    def _set_due_date_days(self, days: int) -> None:
        today_str = self.borrow_date.value or bangkok_today().isoformat()
        try:
            start = date.fromisoformat(today_str)
        except Exception:
            start = bangkok_today()
        self.due_date.value = (start + timedelta(days=days)).isoformat()
        update_control(self)

    def _build_view(self) -> None:
        header = build_page_header(
            title="ทำรายการยืม",
            subtitle="เลือกผู้ยืม อุปกรณ์ และวันที่ต้องคืน",
            icon=ft.Icons.ASSIGNMENT,
        )

        step1_card = build_card(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.LOOKS_ONE_ROUNDED, color=ft.Colors.BLUE_600, size=20),
                            ft.Text("1. เลือกผู้ยืมและผู้บันทึก", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                        ],
                        spacing=8,
                    ),
                    ft.ResponsiveRow(
                        controls=[
                            ft.Container(content=self.borrower_dropdown, col={"sm": 12, "md": 6}),
                            ft.Container(content=self.staff_dropdown, col={"sm": 12, "md": 6}),
                        ],
                        spacing=12,
                    ),
                ],
                spacing=12,
            ),
        )

        step2_card = build_card(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.LOOKS_TWO_ROUNDED, color=ft.Colors.BLUE_600, size=20),
                            ft.Text("2. เลือกอุปกรณ์", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                        ],
                        spacing=8,
                    ),
                    self.unit_dropdown,
                ],
                spacing=12,
            ),
        )

        date_preset_buttons = ft.Row(
            controls=[
                ft.Text("ปุ่มลัดวันคืน:", size=12, color=COLOR_TEXT_SECONDARY, weight=ft.FontWeight.W_500),
                ft.OutlinedButton(
                    "+3 วัน",
                    style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=10, vertical=4)),
                    on_click=lambda e: self._set_due_date_days(3),
                ),
                ft.OutlinedButton(
                    "+7 วัน (1 สัปดาห์)",
                    style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=10, vertical=4)),
                    on_click=lambda e: self._set_due_date_days(7),
                ),
                ft.OutlinedButton(
                    "+14 วัน (2 สัปดาห์)",
                    style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=10, vertical=4)),
                    on_click=lambda e: self._set_due_date_days(14),
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
            run_spacing=8,
        )

        step3_card = build_card(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.LOOKS_3_ROUNDED, color=ft.Colors.BLUE_600, size=20),
                            ft.Text("3. กำหนดวันคืนและรายละเอียด", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                        ],
                        spacing=8,
                    ),
                    ft.ResponsiveRow(
                        controls=[
                            ft.Container(content=self.borrow_date, col={"sm": 12, "md": 6}),
                            ft.Container(content=self.due_date, col={"sm": 12, "md": 6}),
                        ],
                        spacing=12,
                    ),
                    date_preset_buttons,
                    self.purpose,
                    self.note,
                ],
                spacing=12,
            ),
        )

        action_row = ft.Row(
            controls=[
                self.create_button,
            ],
            spacing=12,
            wrap=True,
            run_spacing=8,
        )

        summary_card = build_card(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.RECEIPT_LONG, size=18, color=ft.Colors.BLUE_600),
                            ft.Text("สรุปผลการทำรายการ", size=14, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                        ],
                        spacing=8,
                    ),
                    self.summary,
                ],
                spacing=8,
            ),
            bgcolor=ft.Colors.BLUE_50,
            border_color=ft.Colors.BLUE_200,
        )

        self.content = ft.Column(
            controls=[
                header,
                step1_card,
                step2_card,
                step3_card,
                action_row,
                summary_card,
            ],
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def _handle_borrow(
        self,
        e: ft.ControlEvent,
    ) -> None:
        if not has_permission(self.current_user, Permission.MANAGE_LOANS):
            self._show_error("คุณไม่มีสิทธิ์ทำรายการนี้")
            update_control(self)
            return

        borrower_code = self.borrower_dropdown.value or ""
        staff_code = self.staff_dropdown.value or ""
        unit_id = self.unit_dropdown.value or ""
        borrow_date = self.borrow_date.value or ""
        due_date = self.due_date.value or ""
        purpose = self.purpose.value or ""

        if not borrower_code:
            self._show_error("กรุณาเลือกผู้ยืม")
            return

        if not staff_code:
            self._show_error("กรุณาเลือกผู้บันทึกรายการ")
            return

        if not unit_id:
            self._show_error("กรุณาเลือกอุปกรณ์")
            return

        if not borrow_date:
            self._show_error("กรุณาระบุวันที่ยืม")
            return

        if not due_date:
            self._show_error("กรุณาระบุวันที่ครบกำหนด")
            return

        if not purpose:
            self._show_error("กรุณาระบุวัตถุประสงค์")
            return

        try:
            confirmed = self.service.create_and_confirm_borrow(
                borrower_code=borrower_code,
                staff_code=staff_code,
                unit_ids=[unit_id],
                borrow_date=borrow_date,
                due_date=due_date,
                purpose=purpose,
            )

            if confirmed is None:
                self._show_error("บันทึกไม่ได้ อุปกรณ์อาจไม่พร้อมให้ยืม")
                return

            self.summary.value = (
                f"บันทึกการยืมเรียบร้อย\n"
                f"• ผู้ยืม: {borrower_code}\n"
                f"• รหัสอุปกรณ์: {unit_id}\n"
                f"• กำหนดคืน: {due_date}"
            )
            self.summary.color = ft.Colors.GREEN_800
            self._refresh_units()

        except Exception as exc:
            self._show_error(str(exc))

        update_control(self)

    def _refresh_units(self) -> None:
        units = self.service.search_units(
            status="available"
        )

        self.unit_dropdown.options = [
            ft.DropdownOption(
                key=unit.id,
                text=(
                    f"{unit.asset_code} - "
                    f"{unit.equipment_name} ("
                    f"{self._translate_unit_status(unit.status)})"
                ),
            )
            for unit in units
        ]

        self.unit_dropdown.value = None

    def _show_error(self, message: str) -> None:
        self.summary.value = message
        self.summary.color = ft.Colors.RED_700
