import flet as ft

from app.components.common import (
    build_card,
    build_form_dialog,
    close_dialog,
    open_dialog,
    update_control,
)
from app.services.fake_services import FakeInventoryService
from app.theme import COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY


class DashboardView(ft.Container):
    """Inventory overview with three direct management actions."""

    def __init__(self, service: FakeInventoryService | None = None) -> None:
        super().__init__(expand=True, padding=0)
        self.service = service or FakeInventoryService()

        self.metric_values = {
            status: ft.Text(
                "0", size=26, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY
            )
            for status in ("available", "borrowed", "maintenance", "reported_lost")
        }
        self.feedback = ft.Text("", size=13, color=COLOR_TEXT_SECONDARY)
        self.inventory_table: ft.DataTable | None = None
        self.table_container = ft.Container(on_size_change=self._handle_table_size)

        self.category_name = ft.TextField(
            label="ชื่อหมวดหมู่", hint_text="เช่น IT หรือ หนังสือวิทยาศาสตร์"
        )
        self.category_form_feedback = ft.Text("", size=12)

        self.equipment_name = ft.TextField(
            label="ชื่ออุปกรณ์", hint_text="เช่น จอคอม หรือ คีย์บอร์ด"
        )
        self.equipment_category = ft.Dropdown(
            label="หมวดหมู่",
            options=[],
            expand=True,
            menu_width=600,
            on_size_change=self._handle_category_dropdown_size,
        )
        self.equipment_category_row = ft.Row(
            controls=[self.equipment_category], spacing=0
        )
        self.equipment_asset_code = ft.TextField(
            label="รหัสอุปกรณ์", hint_text="เช่น MON-001"
        )
        self.equipment_location = ft.TextField(
            label="สถานที่เก็บ", hint_text="เช่น ห้อง Lab A ชั้น 2"
        )
        self.equipment_form_feedback = ft.Text("", size=12)

        self.manage_unit = ft.Dropdown(
            label="อุปกรณ์ที่ต้องการจัดการ",
            options=[],
            expand=True,
            menu_width=600,
            on_size_change=lambda e: self._handle_dropdown_size(self.manage_unit, e),
        )
        self.manage_unit_row = ft.Row(controls=[self.manage_unit], spacing=0)
        self.manage_action = ft.Dropdown(
            label="สิ่งที่ต้องการทำ",
            value="relocate",
            expand=True,
            menu_width=600,
            on_size_change=lambda e: self._handle_dropdown_size(self.manage_action, e),
            options=[
                ft.dropdown.Option("relocate", "ย้ายตำแหน่ง"),
                ft.dropdown.Option("maintenance", "บันทึกว่าซ่อมเสร็จ"),
                ft.dropdown.Option("retired", "เลิกใช้อุปกรณ์"),
                ft.dropdown.Option("lost_recovered", "พบอุปกรณ์ที่เคยแจ้งหาย"),
                ft.dropdown.Option("lost_closed", "ปิดข้อมูลแจ้งหายเดิม"),
            ],
        )
        self.manage_action_row = ft.Row(controls=[self.manage_action], spacing=0)
        self.manage_location = ft.TextField(
            label="สถานที่เก็บใหม่",
            hint_text="กรอกเมื่อย้าย ซ่อมเสร็จ หรือพบอุปกรณ์",
        )
        self.manage_reason = ft.TextField(label="เหตุผล / หมายเหตุ", multiline=True, min_lines=2)
        self.manage_form_feedback = ft.Text("", size=12)

        self._refresh_form_options()
        self._build_dialogs()
        self._build_view()
        self._refresh_metrics()
        self._refresh_table()

    def _build_dialogs(self) -> None:
        self.category_dialog = build_form_dialog(
            title="เพิ่มหมวดหมู่",
            icon=ft.Icons.CATEGORY_OUTLINED,
            content=ft.Column(
                controls=[
                    ft.Text(
                        "สร้างกลุ่มสำหรับจัดอุปกรณ์ เช่น IT หรือหนังสือวิทยาศาสตร์",
                        size=13,
                        color=COLOR_TEXT_SECONDARY,
                    ),
                    self.category_name,
                    self.category_form_feedback,
                ],
                spacing=12,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            save_label="บันทึกหมวดหมู่",
            on_save=self._save_category,
            on_cancel=lambda e: close_dialog(self, self.category_dialog),
        )
        self.equipment_dialog = build_form_dialog(
            title="เพิ่มอุปกรณ์",
            icon=ft.Icons.ADD_BOX_OUTLINED,
            content=ft.Column(
                controls=[
                    ft.Text(
                        "กรอกชื่ออุปกรณ์ แล้วเลือกหมวดหมู่ที่สร้างไว้",
                        size=13,
                        color=COLOR_TEXT_SECONDARY,
                    ),
                    self.equipment_asset_code,
                    self.equipment_name,
                    self.equipment_category_row,
                    self.equipment_location,
                    self.equipment_form_feedback,
                ],
                spacing=12,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            save_label="บันทึกอุปกรณ์",
            on_save=self._save_equipment,
            on_cancel=lambda e: close_dialog(self, self.equipment_dialog),
        )
        self.manage_dialog = build_form_dialog(
            title="จัดการสถานะและตำแหน่ง",
            icon=ft.Icons.TUNE,
            content=ft.Column(
                controls=[
                    self.manage_unit_row,
                    self.manage_action_row,
                    self.manage_location,
                    self.manage_reason,
                    self.manage_form_feedback,
                ],
                spacing=12,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            save_label="ยืนยันการเปลี่ยนแปลง",
            on_save=self._save_management,
            on_cancel=lambda e: close_dialog(self, self.manage_dialog),
        )

    def _build_view(self) -> None:
        top_actions = ft.Row(
            controls=[
                ft.OutlinedButton(
                    "เพิ่มหมวดหมู่",
                    icon=ft.Icons.CATEGORY_OUTLINED,
                    height=44,
                    on_click=self._open_category_dialog,
                ),
                ft.OutlinedButton(
                    "เพิ่มอุปกรณ์",
                    icon=ft.Icons.ADD_BOX_OUTLINED,
                    height=44,
                    on_click=self._open_equipment_dialog,
                ),
                ft.Button(
                    "เปลี่ยนสถานะ / ตำแหน่ง",
                    icon=ft.Icons.TUNE,
                    height=44,
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.BLUE_600,
                    on_click=self._open_manage_dialog,
                ),
            ],
            spacing=8,
            wrap=True,
            run_spacing=8,
            alignment=ft.MainAxisAlignment.END,
            tight=True,
        )
        header_left = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.DASHBOARD_OUTLINED, size=24, color=ft.Colors.BLUE_600),
                    padding=10,
                    border_radius=10,
                    bgcolor=ft.Colors.BLUE_50,
                ),
                ft.Column(
                    controls=[
                        ft.Text("Dashboard", size=22, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                        ft.Text("ดูภาพรวมและจัดการข้อมูลคลังจากจุดเดียว", size=13, color=COLOR_TEXT_SECONDARY),
                    ],
                    spacing=2,
                    tight=True,
                ),
            ],
            spacing=12,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        header = ft.Container(
            content=ft.ResponsiveRow(
                controls=[
                    ft.Container(content=header_left, col={"sm": 12, "md": 5}),
                    ft.Container(
                        content=top_actions,
                        col={"sm": 12, "md": 7},
                        alignment=ft.Alignment.CENTER_RIGHT,
                    ),
                ],
                spacing=12,
                run_spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=0, top=0, right=0, bottom=16),
            width=float("inf"),
        )
        summary = ft.ResponsiveRow(
            controls=[
                ft.Container(
                    col={"sm": 6, "md": 3},
                    content=build_card(
                        ft.Column(
                            controls=[
                                self.metric_values[status],
                                ft.Text(label, size=12, color=COLOR_TEXT_SECONDARY),
                            ],
                            spacing=2,
                        ),
                        padding=16,
                    ),
                )
                for status, label in [
                    ("available", "พร้อมใช้งาน"),
                    ("borrowed", "กำลังถูกยืม"),
                    ("maintenance", "อยู่ระหว่างซ่อม"),
                    ("reported_lost", "แจ้งสูญหาย"),
                ]
            ],
            spacing=12,
            run_spacing=12,
        )
        table_section = build_card(
            ft.Column(
                controls=[
                    ft.Text("รายการอุปกรณ์", size=18, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY),
                    ft.Text("ข้อมูลล่าสุดของอุปกรณ์ทุกชิ้นในคลัง", size=13, color=COLOR_TEXT_SECONDARY),
                    self.table_container,
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            padding=20,
        )
        table_section.width = float("inf")
        self.content = ft.Column(
            controls=[header, summary, table_section, self.feedback],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def _refresh_metrics(self) -> None:
        units = self.service.search_units()
        for status, control in self.metric_values.items():
            control.value = str(sum(unit.status == status for unit in units))

    def _refresh_table(self) -> None:
        units = self.service.search_units()
        if not units:
            self.inventory_table = None
            self.table_container.content = ft.Container(
                content=ft.Text("ยังไม่มีข้อมูลอุปกรณ์", color=COLOR_TEXT_SECONDARY),
                padding=24,
                alignment=ft.Alignment.CENTER,
            )
            return
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("รหัสอุปกรณ์"), expand=2),
                ft.DataColumn(ft.Text("ชื่ออุปกรณ์"), expand=3),
                ft.DataColumn(ft.Text("หมวดหมู่"), expand=2),
                ft.DataColumn(ft.Text("สถานะ"), expand=2),
                ft.DataColumn(ft.Text("ตำแหน่ง"), expand=3),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(unit.asset_code, weight=ft.FontWeight.W_600)),
                        ft.DataCell(ft.Text(unit.equipment_name)),
                        ft.DataCell(ft.Text(unit.category or "-")),
                        ft.DataCell(ft.Text(self._status_label(unit.status))),
                        ft.DataCell(ft.Text(unit.location)),
                    ]
                )
                for unit in units
            ],
            column_spacing=32,
            horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_200),
            width=self.inventory_table.width if self.inventory_table else 900,
        )
        self.inventory_table = table
        self.table_container.content = ft.Row(
            controls=[table],
            scroll=ft.ScrollMode.AUTO,
        )
        self.table_container.width = float("inf")

    def _handle_table_size(self, e: ft.LayoutSizeChangeEvent) -> None:
        if self.inventory_table is None:
            return
        self.inventory_table.width = max(e.width, 900)
        update_control(self.inventory_table)

    def _handle_category_dropdown_size(self, e: ft.LayoutSizeChangeEvent) -> None:
        self._handle_dropdown_size(self.equipment_category, e)

    @staticmethod
    def _handle_dropdown_size(
        dropdown: ft.Dropdown, e: ft.LayoutSizeChangeEvent
    ) -> None:
        dropdown.menu_width = e.width
        update_control(dropdown)

    def _refresh_form_options(self) -> None:
        categories = self.service.list_categories()
        self.equipment_category.options = [
            ft.dropdown.Option(item.id, item.name) for item in categories
        ]
        if categories and self.equipment_category.value not in {
            item.id for item in categories
        }:
            self.equipment_category.value = categories[0].id

        units = self.service.search_units()
        self.manage_unit.options = [
            ft.dropdown.Option(
                unit.id,
                f"{unit.asset_code} — {unit.equipment_name} ({self._status_label(unit.status)})",
            )
            for unit in units
        ]

    def _open_category_dialog(self, e: ft.ControlEvent | None) -> None:
        self.category_form_feedback.value = ""
        open_dialog(self, self.category_dialog)

    def _open_equipment_dialog(self, e: ft.ControlEvent | None) -> None:
        self._refresh_form_options()
        self.equipment_form_feedback.value = ""
        open_dialog(self, self.equipment_dialog)

    def _open_manage_dialog(self, e: ft.ControlEvent | None) -> None:
        self._refresh_form_options()
        self.manage_form_feedback.value = ""
        open_dialog(self, self.manage_dialog)

    def _save_category(self, e: ft.ControlEvent | None) -> None:
        name = (self.category_name.value or "").strip()
        if not name:
            self._form_error(self.category_form_feedback, "กรุณากรอกชื่อหมวดหมู่")
            return
        created = self.service.create_category(name)
        if created is None:
            self._form_error(
                self.category_form_feedback, "มีหมวดหมู่นี้อยู่แล้ว กรุณาใช้ชื่ออื่น"
            )
            return
        self.category_name.value = ""
        self._finish("เพิ่มหมวดหมู่เรียบร้อย", self.category_dialog)

    def _save_equipment(self, e: ft.ControlEvent | None) -> None:
        name = (self.equipment_name.value or "").strip()
        category_id = self.equipment_category.value or ""
        asset_code = (self.equipment_asset_code.value or "").strip()
        location = (self.equipment_location.value or "").strip()
        if not name or not category_id or not asset_code or not location:
            self._form_error(self.equipment_form_feedback, "กรุณากรอกข้อมูลให้ครบ")
            return
        created = self.service.create_inventory_item(
            name=name,
            category_id=category_id,
            asset_code=asset_code,
            location=location,
        )
        if created is None:
            self._form_error(
                self.equipment_form_feedback,
                "บันทึกไม่ได้ กรุณาตรวจสอบหมวดหมู่หรือรหัสอุปกรณ์ซ้ำ",
            )
            return
        self.equipment_name.value = ""
        self.equipment_asset_code.value = ""
        self.equipment_location.value = ""
        self._finish("เพิ่มอุปกรณ์เรียบร้อย", self.equipment_dialog)

    def _save_management(self, e: ft.ControlEvent | None) -> None:
        unit_id = self.manage_unit.value or ""
        action = self.manage_action.value or ""
        location = (self.manage_location.value or "").strip()
        reason = (self.manage_reason.value or "").strip()
        if not unit_id or not action or not reason:
            self._form_error(self.manage_form_feedback, "กรุณาเลือกอุปกรณ์ การดำเนินการ และระบุเหตุผล")
            return
        if action in {"relocate", "maintenance", "lost_recovered"} and not location:
            self._form_error(self.manage_form_feedback, "การดำเนินการนี้ต้องระบุตำแหน่งปลายทาง")
            return
        updated = self.service.update_unit_status(
            unit_id,
            action,
            location=location or None,
            reason=reason,
        )
        if updated is None:
            self._form_error(self.manage_form_feedback, "เปลี่ยนแปลงไม่ได้ กรุณาตรวจสอบสถานะปัจจุบัน")
            return
        self.manage_unit.value = None
        self.manage_location.value = ""
        self.manage_reason.value = ""
        self._finish("อัปเดตคลังเรียบร้อย", self.manage_dialog)

    def _finish(self, message: str, dialog: ft.AlertDialog) -> None:
        self.feedback.value = message
        self.feedback.color = ft.Colors.GREEN_700
        self._refresh_form_options()
        self._refresh_metrics()
        self._refresh_table()
        close_dialog(self, dialog)
        update_control(self)

    @staticmethod
    def _form_error(control: ft.Text, message: str) -> None:
        control.value = message
        control.color = ft.Colors.RED_700
        update_control(control)

    @staticmethod
    def _status_label(status: str) -> str:
        return {
            "available": "พร้อมใช้งาน",
            "borrowed": "ถูกยืม",
            "maintenance": "กำลังซ่อม",
            "reported_lost": "แจ้งหาย",
            "retired": "เลิกใช้",
        }.get(status, status)


def build_dashboard_view(service: FakeInventoryService | None = None) -> ft.Container:
    return DashboardView(service)
