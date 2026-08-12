import flet as ft

from app.components.common import (
    build_card,
    build_page_header,
    build_state_view,
    build_status_chip,
    update_control,
)
from app.services.fake_services import FakeInventoryService
from app.theme import COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY


class InventoryView(ft.Container):
    def __init__(self, service: FakeInventoryService | None = None) -> None:
        super().__init__(expand=True, padding=0)
        self.service = service or FakeInventoryService()

        self.search_field = ft.TextField(
            label="ค้นหาด้วยรหัสสินทรัพย์หรืออุปกรณ์",
            hint_text="ลอง 'microscope' หรือ 'AST-001'",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
        )

        self.status_dropdown = ft.Dropdown(
            label="สถานะ",
            options=[
                ft.dropdown.Option("all", "ทั้งหมด"),
                ft.dropdown.Option("available", "พร้อมใช้งาน"),
                ft.dropdown.Option("borrowed", "ถูกยืม"),
                ft.dropdown.Option("maintenance", "กำลังบำรุงรักษา"),
                ft.dropdown.Option("reported_lost", "แจ้งหาย"),
                ft.dropdown.Option("retired", "ปลดระวาง"),
            ],
            value="all",
            width=180,
        )

        self.equipment_name_field = ft.TextField(label="ชื่ออุปกรณ์", hint_text="เช่น Microscope X-200", expand=True)
        self.equipment_code_field = ft.TextField(label="รหัสอุปกรณ์", hint_text="เช่น EQ-300", expand=True)
        self.category_field = ft.TextField(label="หมวดหมู่", hint_text="เช่น Research / IT", expand=True)

        self.asset_code_field = ft.TextField(label="รหัสสินทรัพย์", hint_text="เช่น AST-010", expand=True)
        self.location_field = ft.TextField(label="สถานที่", hint_text="เช่น Lab A - Shelf 2", expand=True)

        self.reason_field = ft.TextField(label="เหตุผล / หมายเหตุ", hint_text="รายละเอียดการอัปเดต", expand=True)
        self.status_action_dropdown = ft.Dropdown(
            label="การดำเนินการ",
            options=[
                ft.dropdown.Option("relocate", "ย้ายตำแหน่ง"),
                ft.dropdown.Option("maintenance", "ซ่อมเสร็จ"),
                ft.dropdown.Option("retired", "ปลดระวาง"),
            ],
            value="relocate",
            width=200,
        )

        self.feedback_text = ft.Text("", size=13, color=ft.Colors.GREY_700, weight=ft.FontWeight.W_500)
        self.unit_cards_container = ft.Container(expand=True)
        self.count_badge = ft.Text("", size=13, color=COLOR_TEXT_SECONDARY, weight=ft.FontWeight.W_500)

        self._build_view()

    def _build_view(self) -> None:
        header = build_page_header(
            title="คลังอุปกรณ์ห้องปฏิบัติการ",
            subtitle="ค้นหา ตรวจสอบ และจัดการข้อมูลอุปกรณ์ในคลัง",
            icon=ft.Icons.INVENTORY_2,
        )

        search_bar = build_card(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[self.search_field, self.status_dropdown],
                        spacing=12,
                    ),
                    ft.Row(
                        controls=[
                            ft.ElevatedButton(
                                "ค้นหา",
                                icon=ft.Icons.SEARCH,
                                style=ft.ButtonStyle(
                                    color=ft.Colors.WHITE,
                                    bgcolor=ft.Colors.BLUE_600,
                                    padding=ft.Padding.symmetric(horizontal=20, vertical=12),
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                ),
                                on_click=self._handle_search,
                            ),
                            ft.OutlinedButton(
                                "รีเซ็ต",
                                icon=ft.Icons.REFRESH,
                                style=ft.ButtonStyle(
                                    padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                ),
                                on_click=self._handle_reset,
                            ),
                            ft.Container(expand=True),
                            self.count_badge,
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=12,
            ),
            padding=16,
        )

        management_content = ft.Column(
            controls=[
                build_card(
                    content=ft.Column(
                        controls=[
                            ft.Text("เพิ่มอุปกรณ์ใหม่", weight=ft.FontWeight.BOLD),
                            ft.Row(
                                controls=[
                                    self.equipment_name_field,
                                    self.equipment_code_field,
                                    self.category_field,
                                ],
                                spacing=12,
                            ),
                            ft.Row(
                                controls=[
                                    ft.ElevatedButton(
                                        "บันทึกอุปกรณ์",
                                        icon=ft.Icons.SAVE,
                                        style=ft.ButtonStyle(
                                            color=ft.Colors.WHITE,
                                            bgcolor=ft.Colors.GREEN_600,
                                        ),
                                        on_click=self._handle_create_equipment,
                                    ),
                                ],
                            ),
                        ],
                        spacing=12,
                    ),
                ),
                build_card(
                    content=ft.Column(
                        controls=[
                            ft.Text("เพิ่มหน่วยสินทรัพย์", weight=ft.FontWeight.BOLD),
                            ft.Row(
                                controls=[self.asset_code_field, self.location_field],
                                spacing=12,
                            ),
                            ft.Row(
                                controls=[
                                    ft.ElevatedButton(
                                        "บันทึกหน่วยสินทรัพย์",
                                        icon=ft.Icons.SAVE,
                                        style=ft.ButtonStyle(
                                            color=ft.Colors.WHITE,
                                            bgcolor=ft.Colors.GREEN_600,
                                        ),
                                        on_click=self._handle_create_unit,
                                    ),
                                ],
                            ),
                        ],
                        spacing=12,
                    ),
                ),
                build_card(
                    content=ft.Column(
                        controls=[
                            ft.Text("อัปเดตสถานะหน่วย", weight=ft.FontWeight.BOLD),
                            ft.Row(
                                controls=[self.status_action_dropdown, self.reason_field],
                                spacing=12,
                            ),
                            ft.Row(
                                controls=[
                                    ft.ElevatedButton(
                                        "ดำเนินการอัปเดต",
                                        icon=ft.Icons.CHECK,
                                        style=ft.ButtonStyle(
                                            color=ft.Colors.WHITE,
                                            bgcolor=ft.Colors.BLUE_600,
                                        ),
                                        on_click=self._handle_update_unit,
                                    ),
                                ],
                            ),
                        ],
                        spacing=12,
                    ),
                ),
            ],
            spacing=12,
        )

        self.content = ft.Column(
            controls=[
                header,
                search_bar,
                management_content,
                self.feedback_text,
                self.unit_cards_container,
            ],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        self._render_units()

    def _render_units(self) -> None:
        units = self.service.search_units(
            self.search_field.value or "",
            self.status_dropdown.value if self.status_dropdown.value != "all" else None,
        )

        self.count_badge.value = f"พบทั้งหมด {len(units)} รายการ"

        if not units:
            self.unit_cards_container.content = build_state_view(
                "ไม่พบผลลัพธ์การค้นหา",
                "ลองเปลี่ยนคำค้นหาหรือเลือกตัวกรองสถานะเป็น 'ทั้งหมด'",
                icon=ft.Icons.INVENTORY_2_OUTLINED,
            )
            return

        cards = []
        for unit in units:
            unit_icon = (
                ft.Icons.LAPTOP_MAC
                if "laptop" in unit.equipment_name.lower()
                else ft.Icons.BIOTECH
                if "microscope" in unit.equipment_name.lower()
                else ft.Icons.DEVICES
            )

            card_content = ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Icon(unit_icon, size=20, color=ft.Colors.BLUE_600),
                                padding=8,
                                border_radius=8,
                                bgcolor=ft.Colors.BLUE_50,
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text(
                                        unit.asset_code,
                                        weight=ft.FontWeight.BOLD,
                                        size=15,
                                        color=COLOR_TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        unit.equipment_name,
                                        size=13,
                                        color=COLOR_TEXT_SECONDARY,
                                    ),
                                ],
                                spacing=1,
                                tight=True,
                                expand=True,
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Divider(height=12, color=ft.Colors.GREY_200),
                    ft.Row(
                        controls=[
                            build_status_chip(unit.status, self._translate_status(unit.status)),
                        ],
                    ),
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=14, color=COLOR_TEXT_SECONDARY),
                            ft.Text(
                                unit.location,
                                size=12,
                                color=COLOR_TEXT_SECONDARY,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                expand=True,
                            ),
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=8,
                tight=True,
            )

            card = build_card(
                content=card_content,
                padding=14,
                width=240,
                on_click=lambda e, code=unit.asset_code: self._handle_card_click(code),
            )
            cards.append(card)

        self.unit_cards_container.content = ft.Row(
            controls=cards,
            wrap=True,
            spacing=12,
            run_spacing=12,
        )

    def _handle_card_click(self, asset_code: str) -> None:
        self.asset_code_field.value = asset_code
        self.feedback_text.value = f"เลือกหน่วย {asset_code} แล้ว"
        self.feedback_text.color = ft.Colors.BLUE_700
        update_control(self)

    def _handle_search(self, e: ft.ControlEvent) -> None:
        self._render_units()

    def _handle_reset(self, e: ft.ControlEvent) -> None:
        self.search_field.value = ""
        self.status_dropdown.value = "all"
        self._render_units()

    def _handle_create_equipment(self, e: ft.ControlEvent) -> None:
        name = self.equipment_name_field.value or ""
        code = self.equipment_code_field.value or ""
        category = self.category_field.value or ""
        if not name or not code or not category:
            self.feedback_text.value = "กรุณากรอกฟอร์มอุปกรณ์ให้ครบก่อนบันทึก"
            self.feedback_text.color = ft.Colors.RED_700
            update_control(self)
            return

        self.service.create_equipment(name, code, category)
        self.feedback_text.value = f"สร้างอุปกรณ์ {code} แล้ว"
        self.feedback_text.color = ft.Colors.GREEN_700
        self.equipment_name_field.value = ""
        self.equipment_code_field.value = ""
        self.category_field.value = ""
        update_control(self)

    def _handle_create_unit(self, e: ft.ControlEvent) -> None:
        asset_code = self.asset_code_field.value or ""
        location = self.location_field.value or ""
        if not asset_code or not location:
            self.feedback_text.value = "กรุณาใส่รหัสสินทรัพย์และสถานที่"
            self.feedback_text.color = ft.Colors.RED_700
            update_control(self)
            return

        created = self.service.create_unit(asset_code=asset_code, equipment_id="eq-1", location=location)
        if created is None:
            self.feedback_text.value = "รหัสสินทรัพย์ซ้ำ"
            self.feedback_text.color = ft.Colors.RED_700
            update_control(self)
            return

        self.feedback_text.value = f"สร้างหน่วย {asset_code} แล้ว"
        self.feedback_text.color = ft.Colors.GREEN_700
        self.asset_code_field.value = ""
        self.location_field.value = ""
        self._render_units()
        update_control(self)

    def _translate_status(self, status: str) -> str:
        return {
            "available": "พร้อมใช้งาน",
            "borrowed": "ถูกยืม",
            "maintenance": "กำลังบำรุงรักษา",
            "reported_lost": "แจ้งหาย",
            "retired": "ปลดระวาง",
        }.get(status, status.title())

    def _handle_update_unit(self, e: ft.ControlEvent) -> None:
        asset_code = self.asset_code_field.value or ""
        reason = self.reason_field.value or ""
        if not asset_code or not reason:
            self.feedback_text.value = "กรุณาใส่รหัสสินทรัพย์และเหตุผลสำหรับการอัปเดต"
            self.feedback_text.color = ft.Colors.RED_700
            update_control(self)
            return

        unit = self.service.get_unit(asset_code)
        if unit is None:
            self.feedback_text.value = "ไม่พบรหัสสินทรัพย์"
            self.feedback_text.color = ft.Colors.RED_700
            update_control(self)
            return

        status = self.status_action_dropdown.value or "relocate"
        if status == "maintenance":
            target_status = "available"
        else:
            target_status = status

        self.service.update_unit_status(unit.id, target_status, location=self.location_field.value or unit.location, reason=reason)
        self.feedback_text.value = f"อัปเดตหน่วย {asset_code} แล้ว"
        self.feedback_text.color = ft.Colors.GREEN_700
        self.asset_code_field.value = ""
        self.location_field.value = ""
        self.reason_field.value = ""
        self._render_units()
        update_control(self)


def build_inventory_view(service: FakeInventoryService | None = None) -> ft.Container:
    return InventoryView(service)
