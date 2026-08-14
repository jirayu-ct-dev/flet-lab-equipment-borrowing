import flet as ft

from app.components.common import (
    build_card,
    build_card_list,
    build_data_card,
    build_page_header,
    build_state_view,
    build_status_chip,
    build_table_surface,
    handle_mobile_resize,
)
from app.services.fake_services import FakeInventoryService
from app.theme import CONTROL_RADIUS


class InventoryView(ft.Container):
    """Searchable inventory list; management actions live on Dashboard."""

    def __init__(
        self,
        service: FakeInventoryService | None = None,
        *,
        mobile: bool = False,
    ) -> None:
        super().__init__(expand=True, padding=0)
        self.service = service or FakeInventoryService()
        self.mobile = mobile
        self._table_width: float | None = None
        self.search_field = ft.TextField(
            label="ค้นหารหัสหรือชื่ออุปกรณ์",
            hint_text="เช่น Microscope หรือ AST-001",
            prefix_icon=ft.Icons.SEARCH,
            width=float("inf"),
            height=52,
            border_radius=CONTROL_RADIUS,
            on_change=self._handle_search,
            on_submit=self._handle_search,
        )
        self.status_dropdown = ft.Dropdown(
            label="สถานะ",
            value="all",
            width=180,
            height=52,
            border_radius=CONTROL_RADIUS,
            options=[
                ft.dropdown.Option("all", "ทั้งหมด"),
                ft.dropdown.Option("available", "พร้อมใช้งาน"),
                ft.dropdown.Option("borrowed", "ถูกยืม"),
                ft.dropdown.Option("maintenance", "กำลังบำรุงรักษา"),
                ft.dropdown.Option("reported_lost", "แจ้งหาย"),
                ft.dropdown.Option("retired", "เลิกใช้"),
            ],
            on_select=self._handle_search,
        )
        self.category_dropdown = ft.Dropdown(
            label="หมวดหมู่",
            value="all",
            width=180,
            height=52,
            border_radius=CONTROL_RADIUS,
            options=[ft.dropdown.Option("all", "ทุกหมวดหมู่")]
            + [
                ft.dropdown.Option(name, name)
                for name in sorted(
                    {
                        unit.category
                        for unit in self.service.search_units()
                        if unit.category
                    }
                )
            ],
            on_select=self._handle_search,
        )
        self.reset_button = ft.OutlinedButton(
            "รีเฟรช",
            icon=ft.Icons.REFRESH,
            height=52,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=CONTROL_RADIUS),
            ),
            on_click=self._handle_reset,
        )
        self.unit_table_container = ft.Container(expand=True)
        self._build_view()
        self.on_size_change = self._handle_resize

    def _build_view(self) -> None:
        header = build_page_header(
            title="อุปกรณ์",
            subtitle="ค้นหาและตรวจสอบสถานะอุปกรณ์ในคลัง",
            icon=ft.Icons.INVENTORY_2,
        )
        search = self._build_filter_bar()
        self.content = ft.Column(
            controls=[header, search, self.unit_table_container],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        self._render_units()

    def _build_filter_bar(self) -> ft.Control:
        self.search_field.width = None
        self.search_field.expand = True
        self.reset_button.expand = False
        self.reset_button.icon = None
        self.reset_button.style = ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=CONTROL_RADIUS),
            padding=ft.Padding.symmetric(horizontal=12),
        )
        if self.mobile:
            self.status_dropdown.width = None
            self.category_dropdown.width = None
            self.status_dropdown.expand = True
            self.category_dropdown.expand = True
        else:
            self.status_dropdown.width = 180
            self.category_dropdown.width = 180
            self.status_dropdown.expand = False
            self.category_dropdown.expand = False
        return build_card(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[self.search_field, self.reset_button],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        controls=[self.status_dropdown, self.category_dropdown],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=12,
                tight=True,
            ),
            padding=16,
        )

    def _render_units(self) -> None:
        units = self.service.search_units(
            self.search_field.value or "",
            self.status_dropdown.value if self.status_dropdown.value != "all" else None,
            self.category_dropdown.value
            if self.category_dropdown.value != "all"
            else None,
        )
        if not units:
            self.unit_table_container.content = build_state_view(
                "ไม่พบอุปกรณ์",
                "ลองเปลี่ยนคำค้นหาหรือเลือกสถานะทั้งหมด",
                icon=ft.Icons.INVENTORY_2_OUTLINED,
            )
            return

        if self.mobile:
            self.unit_table_container.content = build_card_list(
                [
                    build_data_card(
                        title=unit.asset_code,
                        icon=ft.Icons.INVENTORY_2_OUTLINED,
                        status=(unit.status, self._status_label(unit.status)),
                        fields=[
                            ("ชื่ออุปกรณ์", unit.equipment_name),
                            ("หมวดหมู่", unit.category or "-"),
                            ("ตำแหน่ง", unit.location),
                        ],
                    )
                    for unit in units
                ]
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
                        ft.DataCell(build_status_chip(unit.status, self._status_label(unit.status))),
                        ft.DataCell(ft.Text(unit.location)),
                    ]
                )
                for unit in units
            ],
            column_spacing=28,
            horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_200),
        )
        self.unit_table_container.content = build_table_surface(
            table, initial_width=self._table_width
        )

    def _handle_search(self, e: ft.ControlEvent | None) -> None:
        self._render_units()

    def _handle_resize(self, e: ft.LayoutSizeChangeEvent) -> None:
        self._table_width = e.width
        handle_mobile_resize(self, self._build_view, e)

    def _handle_reset(self, e: ft.ControlEvent | None) -> None:
        self.search_field.value = ""
        self.status_dropdown.value = "all"
        self.category_dropdown.value = "all"
        self._render_units()

    @staticmethod
    def _status_label(status: str) -> str:
        return {
            "available": "พร้อมใช้งาน",
            "borrowed": "ถูกยืม",
            "maintenance": "กำลังบำรุงรักษา",
            "reported_lost": "แจ้งหาย",
            "retired": "เลิกใช้",
        }.get(status, status)


def build_inventory_view(
    service: FakeInventoryService | None = None,
    *,
    mobile: bool = False,
) -> ft.Container:
    return InventoryView(service, mobile=mobile)
