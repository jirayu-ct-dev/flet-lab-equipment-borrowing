import flet as ft

from app.components.common import (
    build_card_list,
    build_data_card,
    build_page_header,
    build_state_view,
    build_table_surface,
    handle_mobile_resize,
)
from app.services.fake_services import FakeInventoryService


class ContactView(ft.Container):
    """Read-only contact details for branch staff."""

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
        self._surface_width: float | None = None
        self.staff_container = ft.Container(expand=True)
        self._build_view()
        self.on_size_change = self._handle_resize

    def _build_view(self) -> None:
        header = build_page_header(
            title="ติดต่อเจ้าหน้าที่",
            subtitle="ช่องทางติดต่อเจ้าหน้าที่สาขา",
            icon=ft.Icons.SUPPORT_AGENT_OUTLINED,
        )
        self.content = ft.Column(
            controls=[header, self.staff_container],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        self._render_staff()

    def _render_staff(self) -> None:
        staff = self.service.list_staff()
        if not staff:
            self.staff_container.content = build_state_view(
                "ไม่พบข้อมูลเจ้าหน้าที่",
                "ยังไม่มีข้อมูลเจ้าหน้าที่ในระบบ",
                icon=ft.Icons.SUPPORT_AGENT_OUTLINED,
            )
            return

        if self.mobile:
            self.staff_container.content = build_card_list(
                [
                    build_data_card(
                        title=member.full_name,
                        icon=ft.Icons.PERSON_OUTLINED,
                        fields=[
                            ("อีเมล", member.email or "-"),
                            ("โทรศัพท์", getattr(member, "phone", None) or "-"),
                        ],
                    )
                    for member in staff
                ]
            )
            return

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ชื่อ"), expand=3),
                ft.DataColumn(ft.Text("อีเมล"), expand=3),
                ft.DataColumn(ft.Text("โทรศัพท์"), expand=2),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Text(member.full_name, weight=ft.FontWeight.W_600)
                        ),
                        ft.DataCell(ft.Text(member.email or "-")),
                        ft.DataCell(
                            ft.Text(getattr(member, "phone", None) or "-")
                        ),
                    ]
                )
                for member in staff
            ],
            column_spacing=24,
            horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_200),
        )
        self.staff_container.content = build_table_surface(
            table,
            table_width=800,
            initial_width=(
                self._surface_width
                if self._surface_width is not None
                else self._table_width
            ),
            on_resized=self._record_surface_width,
        )

    def _record_surface_width(self, width: float) -> None:
        self._surface_width = width

    def _handle_resize(self, e: ft.LayoutSizeChangeEvent) -> None:
        self._table_width = e.width
        handle_mobile_resize(self, self._build_view, e)
