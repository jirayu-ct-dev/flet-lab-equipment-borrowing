import flet as ft

from app.components.common import (
    build_card,
    build_page_header,
    build_state_view,
    build_status_chip,
    build_table_surface,
    update_control,
)
from app.services.fake_services import FakeInventoryService
from app.theme import COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY


class HistoryView(ft.Container):
    def __init__(
        self,
        service: FakeInventoryService | None = None,
    ) -> None:
        super().__init__(
            expand=True,
            padding=0,
        )

        self.service = service or FakeInventoryService()

        # --------------------------------------------------
        # Search fields
        # --------------------------------------------------

        self.borrower_search = ft.TextField(
            label="ค้นหาผู้ยืม",
            hint_text="BR-001 หรือชื่อผู้ยืม",
            prefix_icon=ft.Icons.PERSON_SEARCH,
            expand=True,
        )

        self.equipment_search = ft.TextField(
            label="ค้นหาอุปกรณ์",
            hint_text="Laptop, Microscope",
            prefix_icon=ft.Icons.INVENTORY_2_OUTLINED,
            expand=True,
        )

        self.asset_search = ft.TextField(
            label="รหัสสินทรัพย์ / รหัสหน่วย",
            hint_text="AST-002 หรือ unit-2",
            prefix_icon=ft.Icons.QR_CODE_SCANNER,
            expand=True,
        )

        self.start_date = ft.TextField(
            label="วันที่เริ่มต้น",
            hint_text="YYYY-MM-DD",
            prefix_icon=ft.Icons.DATE_RANGE,
            expand=True,
        )

        self.end_date = ft.TextField(
            label="วันที่สิ้นสุด",
            hint_text="YYYY-MM-DD",
            prefix_icon=ft.Icons.EVENT,
            expand=True,
        )

        # --------------------------------------------------
        # Buttons
        # --------------------------------------------------

        self.search_button = ft.Button(
            "ค้นหาประวัติ",
            icon=ft.Icons.SEARCH,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
                padding=ft.Padding(left=20, top=12, right=20, bottom=12),
            ),
            on_click=self._handle_search,
        )

        self.clear_button = ft.OutlinedButton(
            "ล้างตัวกรอง",
            icon=ft.Icons.CLEAR_ALL,
            style=ft.ButtonStyle(
                padding=ft.Padding(left=16, top=12, right=16, bottom=12),
            ),
            on_click=self._handle_clear,
        )

        # --------------------------------------------------
        # State
        # --------------------------------------------------

        self.feedback = ft.Text(
            "",
            size=13,
            color=COLOR_TEXT_SECONDARY,
            weight=ft.FontWeight.W_500,
        )

        self.history_container = ft.Container(
            expand=True,
        )

        self._build_view()

    # ======================================================
    # BUILD
    # ======================================================

    def _build_view(self) -> None:
        header = build_page_header(
            title="ประวัติ",
            subtitle="ดูว่าอุปกรณ์ถูกเพิ่ม ยืม คืน หรือเปลี่ยนสถานะเมื่อใด",
            icon=ft.Icons.HISTORY,
        )

        search_card = build_card(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.FILTER_ALT,
                                size=18,
                                color=ft.Colors.BLUE_600,
                            ),
                            ft.Text(
                                "ค้นหาประวัติและกรองข้อมูล",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=COLOR_TEXT_PRIMARY,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.ResponsiveRow(
                        controls=[
                            ft.Container(
                                content=self.borrower_search,
                                col={"sm": 12, "md": 6},
                            ),
                            ft.Container(
                                content=self.equipment_search,
                                col={"sm": 12, "md": 6},
                            ),
                        ],
                    ),
                    ft.ResponsiveRow(
                        controls=[
                            ft.Container(
                                content=self.asset_search,
                                col={"sm": 12, "md": 4},
                            ),
                            ft.Container(
                                content=self.start_date,
                                col={"sm": 12, "md": 4},
                            ),
                            ft.Container(
                                content=self.end_date,
                                col={"sm": 12, "md": 4},
                            ),
                        ],
                    ),
                    ft.Row(
                        controls=[self.search_button, self.clear_button],
                        spacing=12,
                    ),
                ],
                spacing=12,
            ),
        )

        self.content = ft.Column(
            controls=[
                header,
                search_card,
                self.feedback,
                ft.Container(
                    expand=True,
                    content=self.history_container,
                ),
            ],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        self._render_history()

    # ======================================================
    # RENDER HISTORY
    # ======================================================

    def _render_history(self) -> None:
        try:
            events = self.service.list_history(
                borrower_query=(
                    self.borrower_search.value or None
                ),
                equipment_query=(
                    self.equipment_search.value or None
                ),
                asset_code=(
                    self.asset_search.value or None
                ),
                start_date=(
                    self.start_date.value or None
                ),
                end_date=(
                    self.end_date.value or None
                ),
            )
        except Exception as exc:
            self.history_container.content = build_state_view(
                "ไม่สามารถโหลดประวัติได้",
                str(exc),
                icon=ft.Icons.ERROR_OUTLINE,
            )
            return

        if not events:
            self.history_container.content = build_state_view(
                "ไม่พบประวัติการใช้งาน",
                "ลองปรับคำค้นหาหรือกดล้างตัวกรองเพื่อดูเหตุการณ์ทั้งหมด",
                icon=ft.Icons.HISTORY_TOGGLE_OFF,
            )
            return

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("วันที่"), expand=2),
                ft.DataColumn(ft.Text("เหตุการณ์"), expand=2),
                ft.DataColumn(ft.Text("รายละเอียด"), expand=4),
                ft.DataColumn(ft.Text("ผู้ยืม"), expand=2),
                ft.DataColumn(ft.Text("ผู้บันทึก"), expand=2),
                ft.DataColumn(ft.Text("อุปกรณ์"), expand=2),
                ft.DataColumn(ft.Text("รหัสอุปกรณ์"), expand=2),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(getattr(event, "event_date", "") or "-")),
                        ft.DataCell(
                            build_status_chip(
                                getattr(event, "event_type", ""),
                                self._translate_event_type(getattr(event, "event_type", "")),
                            )
                        ),
                        ft.DataCell(ft.Text(getattr(event, "description", "") or "-")),
                        ft.DataCell(ft.Text(getattr(event, "borrower_code", "") or "-")),
                        ft.DataCell(ft.Text(getattr(event, "staff_code", "") or "-")),
                        ft.DataCell(ft.Text(getattr(event, "equipment_name", "") or "-")),
                        ft.DataCell(ft.Text(getattr(event, "asset_code", "") or "-")),
                    ]
                )
                for event in events
            ],
            column_spacing=24,
            horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_200),
        )
        self.history_container.content = build_table_surface(table, table_width=1250)

    # ======================================================
    # TRANSLATE EVENT
    # ======================================================

    def _translate_event_type(
        self,
        event_type: str,
    ) -> str:

        return {
            "borrowed": "ยืมอุปกรณ์",
            "available": "พร้อมใช้งาน",
            "maintenance": "ส่งซ่อมบำรุง",
            "reported_lost": "แจ้งหาย",
            "inventory_added": "เพิ่มเข้าคลัง",
            "closed": "คืนครบแล้ว",
            "partial": "คืนบางส่วน",
            "returned": "คืนอุปกรณ์",
            "relocated": "ย้ายตำแหน่ง",
            "retired": "ปลดระวาง",
            "repaired": "ซ่อมเสร็จสิ้น",
            "acquire": "รับเข้าคลัง",
            "relocate": "ย้ายตำแหน่ง",
            "repair_complete": "ซ่อมเสร็จ",
            "lost_resolved": "ปิดกรณีสูญหาย",
        }.get(
            event_type,
            event_type or "เหตุการณ์",
        )

    # ======================================================
    # SEARCH
    # ======================================================

    def _handle_search(
        self,
        e: ft.ControlEvent,
    ) -> None:

        self.feedback.value = (
            "Filtered history records (แสดงประวัติที่ตรงกับตัวกรอง)"
        )

        self.feedback.color = ft.Colors.BLUE_700

        self._render_history()

        update_control(self)

    # ======================================================
    # CLEAR
    # ======================================================

    def _handle_clear(
        self,
        e: ft.ControlEvent,
    ) -> None:

        self.borrower_search.value = ""
        self.equipment_search.value = ""
        self.asset_search.value = ""
        self.start_date.value = ""
        self.end_date.value = ""

        self.feedback.value = ""

        self._render_history()

        update_control(self)


# ==========================================================
# FACTORY
# ==========================================================

def build_history_view(
    service: FakeInventoryService | None = None,
) -> ft.Control:

    return HistoryView(service)
