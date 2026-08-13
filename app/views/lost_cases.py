from __future__ import annotations

import flet as ft

from app.components.common import (
    build_alert_banner,
    build_card,
    build_page_header,
    build_state_view,
    build_status_chip,
    update_control,
)
from app.services.fake_services import FakeInventoryService
from app.theme import COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY


RESOLUTION_LABELS = {
    "recovered": "พบอุปกรณ์แล้ว",
    "replaced": "ชดใช้เป็นอุปกรณ์ทดแทน",
    "compensated": "ชดใช้เป็นเงิน",
    "waived": "ยกเว้นการชดใช้",
}


class LostCasesView(ft.Container):
    def __init__(self, service: FakeInventoryService | None = None) -> None:
        super().__init__(expand=True, padding=0)
        self.service = service or FakeInventoryService()
        self.selected_case_id: str | None = None

        self.search_field = ft.TextField(
            label="ค้นหาเคส",
            hint_text="รหัสสินทรัพย์ อุปกรณ์ หรือผู้ยืม",
            prefix_icon=ft.Icons.SEARCH,
            height=52,
            on_submit=self._handle_filter,
        )
        self.status_filter = ft.Dropdown(
            label="สถานะ",
            value="open",
            height=52,
            options=[
                ft.DropdownOption(key="all", text="ทั้งหมด"),
                ft.DropdownOption(key="open", text="รอดำเนินการ"),
                ft.DropdownOption(key="resolved", text="ปิดเคสแล้ว"),
            ],
            on_select=self._handle_filter,
        )
        self.feedback_container = ft.Container()
        self.list_container = ft.Container()
        self.form_container = ft.Container(visible=False)

        self.resolution = ft.Dropdown(
            label="ผลการดำเนินการ (จำเป็น)",
            value="compensated",
            height=52,
            options=[ft.DropdownOption(key=key, text=label) for key, label in RESOLUTION_LABELS.items()],
            on_select=self._handle_resolution_change,
        )
        self.assessed_value = ft.TextField(label="มูลค่าประเมิน (บาท) (จำเป็น)", height=52, keyboard_type=ft.KeyboardType.NUMBER)
        self.compensation = ft.TextField(label="ยอดชดใช้ที่อนุมัติ (บาท) (จำเป็น)", height=52, keyboard_type=ft.KeyboardType.NUMBER)
        self.staff = ft.Dropdown(label="ผู้อนุมัติ (จำเป็น)", height=52)
        self.reason = ft.TextField(label="เหตุผลการตัดสินใจ (จำเป็น)", min_lines=2, max_lines=3)
        self.note = ft.TextField(label="หมายเหตุ", min_lines=2, max_lines=3)
        self.recovered_outcome = ft.Dropdown(
            label="สถานะหลังพบอุปกรณ์",
            value="available",
            height=52,
            options=[
                ft.DropdownOption(key="available", text="พร้อมใช้งาน"),
                ft.DropdownOption(key="maintenance", text="ส่งซ่อมบำรุง"),
            ],
        )
        self.location = ft.Dropdown(label="ตำแหน่งจัดเก็บ", height=52)
        self.replacement_asset_code = ft.TextField(label="รหัสสินทรัพย์ทดแทน", height=52)
        self.replacement_serial = ft.TextField(label="Serial number", height=52)
        self.replacement_price = ft.TextField(label="ราคาซื้ออุปกรณ์ทดแทน", height=52, keyboard_type=ft.KeyboardType.NUMBER)
        self.recovery_fields = ft.ResponsiveRow(
            controls=[
                ft.Container(content=self.recovered_outcome, col={"sm": 12, "md": 6}),
                ft.Container(content=self.location, col={"sm": 12, "md": 6}),
            ],
            visible=False,
        )
        self.replacement_fields = ft.ResponsiveRow(
            controls=[
                ft.Container(content=self.replacement_asset_code, col={"sm": 12, "md": 4}),
                ft.Container(content=self.replacement_serial, col={"sm": 12, "md": 4}),
                ft.Container(content=self.replacement_price, col={"sm": 12, "md": 4}),
            ],
            visible=False,
        )
        self._build_view()

    def _build_view(self) -> None:
        self.staff.options = [
            ft.DropdownOption(key=item.staff_code, text=f"{item.staff_code} — {item.full_name}")
            for item in self.service.list_staff()
        ]
        self.location.options = [
            ft.DropdownOption(key=item.id, text=f"{item.location_code} — {item.label}")
            for item in self.service.list_locations()
        ]
        toolbar = build_card(
            ft.ResponsiveRow(
                controls=[
                    ft.Container(content=self.search_field, col={"sm": 12, "md": 8}),
                    ft.Container(content=self.status_filter, col={"sm": 12, "md": 4}),
                ]
            ),
            padding=16,
        )
        self.content = ft.Column(
            controls=[
                build_page_header(
                    "กรณีอุปกรณ์สูญหาย",
                    "ประเมินมูลค่า บันทึกการอนุมัติ และปิดเคสด้วยหลักฐานที่ตรวจสอบย้อนหลังได้",
                    icon=ft.Icons.REPORT_PROBLEM_OUTLINED,
                ),
                toolbar,
                self.feedback_container,
                self.form_container,
                self.list_container,
            ],
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        self._render_cases()

    def _render_cases(self) -> None:
        try:
            cases = self.service.list_lost_cases(
                query=self.search_field.value or None,
                status=None if self.status_filter.value == "all" else self.status_filter.value,
            )
        except Exception as error:
            self.list_container.content = build_state_view("โหลดกรณีสูญหายไม่สำเร็จ", str(error), icon=ft.Icons.ERROR_OUTLINE)
            return
        if not cases:
            self.list_container.content = build_state_view(
                "ไม่พบกรณีสูญหาย",
                "ไม่มีเคสในสถานะหรือตัวกรองที่เลือก",
                icon=ft.Icons.INVENTORY_2_OUTLINED,
            )
            return
        self.list_container.content = ft.Column(
            controls=[self._build_case_card(case) for case in cases], spacing=12
        )

    def _build_case_card(self, case) -> ft.Control:
        is_open = case.resolution is None
        details = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(case.asset_code, size=16, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY),
                        build_status_chip("open" if is_open else "resolved"),
                    ],
                    spacing=10,
                    wrap=True,
                ),
                ft.Text(case.equipment_name, size=14, color=COLOR_TEXT_PRIMARY),
                ft.Text(
                    f"ผู้ยืม {case.borrower_code} • แจ้งเมื่อ {case.reported_at}",
                    size=13,
                    color=COLOR_TEXT_SECONDARY,
                ),
                *(
                    [ft.Text(
                        f"ผล: {RESOLUTION_LABELS.get(case.resolution, case.resolution)} • ชดใช้ {case.approved_compensation or '0'} บาท",
                        size=13,
                        color=COLOR_TEXT_SECONDARY,
                    )]
                    if not is_open else []
                ),
            ],
            spacing=5,
            expand=True,
        )
        controls: list[ft.Control] = [details]
        if is_open:
            controls.append(
                ft.Button(
                    "ดำเนินการปิดเคส",
                    icon=ft.Icons.FACT_CHECK_OUTLINED,
                    height=44,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE),
                    on_click=lambda _, case_id=case.id: self._select_case(case_id),
                )
            )
        return build_card(ft.Row(controls=controls, alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True), padding=20)

    def _select_case(self, case_id: str) -> None:
        self.selected_case_id = case_id
        self.form_container.content = self._build_resolution_form()
        self.form_container.visible = True
        self.feedback_container.content = None
        update_control(self)

    def _build_resolution_form(self) -> ft.Control:
        return build_card(
            ft.Column(
                controls=[
                    ft.Text("บันทึกผลการดำเนินการ", size=18, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY),
                    ft.Text("จำนวนเงินใช้หน่วยบาท และต้องมีเจ้าหน้าที่ผู้อนุมัติพร้อมเหตุผล", size=13, color=COLOR_TEXT_SECONDARY),
                    ft.ResponsiveRow(controls=[
                        ft.Container(content=self.resolution, col={"sm": 12, "md": 4}),
                        ft.Container(content=self.assessed_value, col={"sm": 12, "md": 4}),
                        ft.Container(content=self.compensation, col={"sm": 12, "md": 4}),
                    ]),
                    self.recovery_fields,
                    self.replacement_fields,
                    self.staff,
                    self.reason,
                    self.note,
                    ft.Row(
                        controls=[
                            ft.Button("ยืนยันการปิดเคส", icon=ft.Icons.CHECK, height=44, on_click=self._submit_resolution),
                            ft.OutlinedButton("ยกเลิก", height=44, on_click=self._cancel_resolution),
                        ],
                        wrap=True,
                    ),
                ],
                spacing=12,
            ),
            padding=24,
            border_color=ft.Colors.BLUE_300,
        )

    def _handle_filter(self, _: ft.ControlEvent | None) -> None:
        self._render_cases()
        update_control(self)

    def _handle_resolution_change(self, _: ft.ControlEvent | None) -> None:
        self.recovery_fields.visible = self.resolution.value == "recovered"
        self.replacement_fields.visible = self.resolution.value == "replaced"
        update_control(self.form_container)

    def _cancel_resolution(self, _: ft.ControlEvent | None) -> None:
        self.selected_case_id = None
        self.form_container.visible = False
        update_control(self)

    def _submit_resolution(self, _: ft.ControlEvent | None) -> None:
        missing = [
            label
            for label, value in [
                ("มูลค่าประเมิน", self.assessed_value.value),
                ("ยอดชดใช้", self.compensation.value),
                ("ผู้อนุมัติ", self.staff.value),
                ("เหตุผล", self.reason.value),
            ]
            if not value
        ]
        if self.resolution.value in {"recovered", "replaced"} and not self.location.value:
            missing.append("ตำแหน่งจัดเก็บ")
        if self.resolution.value == "replaced" and not self.replacement_asset_code.value:
            missing.append("รหัสสินทรัพย์ทดแทน")
        if missing:
            self.feedback_container.content = build_alert_banner(
                "กรุณากรอก: " + ", ".join(missing), "warning"
            )
            update_control(self)
            return
        result = self.service.resolve_lost_case(
            self.selected_case_id or "",
            resolution=self.resolution.value,
            assessed_value=self.assessed_value.value,
            approved_compensation=self.compensation.value,
            staff_code=self.staff.value,
            reason=self.reason.value,
            note=self.note.value or None,
            recovered_outcome=self.recovered_outcome.value if self.resolution.value == "recovered" else None,
            location_id=self.location.value if self.resolution.value in {"recovered", "replaced"} else None,
            replacement_asset_code=self.replacement_asset_code.value or None,
            replacement_serial_number=self.replacement_serial.value or None,
            replacement_purchase_price=self.replacement_price.value or None,
        )
        if result is None:
            self.feedback_container.content = build_alert_banner(
                "บันทึกไม่สำเร็จ โปรดตรวจสอบจำนวนเงิน สถานะ และข้อมูลอุปกรณ์ทดแทน", "error"
            )
            update_control(self)
            return
        self.form_container.visible = False
        self.selected_case_id = None
        self.feedback_container.content = build_alert_banner("ปิดกรณีสูญหายเรียบร้อยแล้ว", "success")
        self._render_cases()
        update_control(self)
