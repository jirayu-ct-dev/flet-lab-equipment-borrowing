from datetime import date, timedelta
import flet as ft

from app.components.common import build_card, build_page_header
from app.services.fake_services import FakeInventoryService
from app.theme import COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY


class BorrowFlowView(ft.Container):
    def __init__(
        self,
        service: FakeInventoryService | None = None,
    ) -> None:
        super().__init__(
            expand=True,
            padding=0,
        )

        self.service = service or FakeInventoryService()

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
            label="เจ้าหน้าที่ผู้ดำเนินการ",
            hint_text="เลือกเจ้าหน้าที่",
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
            label="หน่วยอุปกรณ์ (พร้อมใช้งาน)",
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
            value=date.today().isoformat(),
            expand=True,
        )

        self.due_date = ft.TextField(
            label="วันที่ครบกำหนดคืน",
            hint_text="YYYY-MM-DD",
            prefix_icon=ft.Icons.EVENT_REPEAT,
            value=(date.today() + timedelta(days=7)).isoformat(),
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
            "กรุณากรอกข้อมูลและกกด 'สร้างร่าง' เพื่อตรวจสอบรายการ",
            size=13,
            color=COLOR_TEXT_SECONDARY,
        )

        self.create_button = ft.ElevatedButton(
            "1. สร้างร่างรายการยืม",
            icon=ft.Icons.NOTE_ADD,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
                padding=ft.padding.symmetric(horizontal=20, vertical=12),
            ),
            on_click=self._handle_create_draft,
        )

        self.confirm_button = ft.OutlinedButton(
            "2. ยืนยันการยืม",
            icon=ft.Icons.CHECK_CIRCLE,
            style=ft.ButtonStyle(
                padding=ft.padding.symmetric(horizontal=20, vertical=12),
            ),
            on_click=self._handle_confirm_draft,
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
        today_str = self.borrow_date.value or date.today().isoformat()
        try:
            start = date.fromisoformat(today_str)
        except Exception:
            start = date.today()
        self.due_date.value = (start + timedelta(days=days)).isoformat()
        self.update()

    def _build_view(self) -> None:
        header = build_page_header(
            title="สร้างรายการยืมอุปกรณ์",
            subtitle="เลือกผู้ยืม เจ้าหน้าที่ และอุปกรณ์ พร้อมกำหนดวันและวัตถุประสงค์",
            icon=ft.Icons.ASSIGNMENT,
        )

        step1_card = build_card(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.LOOKS_ONE_ROUNDED, color=ft.Colors.BLUE_600, size=20),
                            ft.Text("ข้อมูลผู้เกี่ยวข้อง", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        controls=[
                            self.borrower_dropdown,
                            self.staff_dropdown,
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
                            ft.Text("เลือกอุปกรณ์ที่ต้องการยืม", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
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
                    style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=10, vertical=4)),
                    on_click=lambda e: self._set_due_date_days(3),
                ),
                ft.OutlinedButton(
                    "+7 วัน (1 สัปดาห์)",
                    style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=10, vertical=4)),
                    on_click=lambda e: self._set_due_date_days(7),
                ),
                ft.OutlinedButton(
                    "+14 วัน (2 สัปดาห์)",
                    style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=10, vertical=4)),
                    on_click=lambda e: self._set_due_date_days(14),
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        step3_card = build_card(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.LOOKS_3_ROUNDED, color=ft.Colors.BLUE_600, size=20),
                            ft.Text("ระยะเวลา และ วัตถุประสงค์", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        controls=[
                            self.borrow_date,
                            self.due_date,
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
                self.confirm_button,
            ],
            spacing=12,
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

    def _handle_create_draft(
        self,
        e: ft.ControlEvent,
    ) -> None:
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
            self._show_error("กรุณาเลือกเจ้าหน้าที่")
            return

        if not unit_id:
            self._show_error("กรุณาเลือกหน่วยอุปกรณ์")
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
            draft = self.service.create_borrow_draft(
                borrower_code=borrower_code,
                staff_code=staff_code,
                unit_ids=[unit_id],
                borrow_date=borrow_date,
                due_date=due_date,
                purpose=purpose,
            )

            if draft is None:
                self._show_error(
                    "ไม่สามารถสร้างร่างรายการยืมได้"
                )
                return

            self.summary.value = (
                f"สร้างร่างสำเร็จ!\n"
                f"• ผู้ยืม: {borrower_code}\n"
                f"• เจ้าหน้าที่: {staff_code}\n"
                f"• รหัสหน่วย: {unit_id}\n"
                f"• วันครบกำหนด: {due_date}\n\n"
                f"กดยืนยันการยืมด้านบนเพื่อเสร็จสิ้นกระบวนการ"
            )
            self.summary.color = ft.Colors.GREEN_800

        except Exception as exc:
            self._show_error(str(exc))

        self.update()

    def _handle_confirm_draft(
        self,
        e: ft.ControlEvent,
    ) -> None:
        drafts = getattr(
            self.service,
            "_borrow_drafts",
            [],
        )

        if not drafts:
            self._show_error(
                "กรุณาสร้างร่างรายการยืมก่อนยืนยัน"
            )
            return

        try:
            draft = self.service.confirm_borrow_draft(
                drafts[-1].id
            )

            if draft is None:
                self._show_error(
                    "ไม่สามารถยืนยันรายการยืมได้"
                )
                return

            self.summary.value = (
                f"ยืนยันการยืมสำเร็จ!\n"
                f"• เลขที่ร่างสัญญายืม: {draft.id}\n"
                f"• สถานะ: ดำเนินการยืมเรียบร้อยแล้ว"
            )
            self.summary.color = ft.Colors.GREEN_800

            # refresh available units
            self._refresh_units()

        except Exception as exc:
            self._show_error(str(exc))

        self.update()

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