import flet as ft

from app.components.common import (
    build_card,
    build_card_list,
    build_data_card,
    build_filter_bar,
    build_page_header,
    build_state_view,
    build_status_chip,
    build_table_surface,
    handle_mobile_resize,
)
from app.contracts import AppUser
from app.services.fake_services import FakeInventoryService
from app.theme import COLOR_TEXT_PRIMARY, CONTROL_RADIUS

_LOAN_STATUS_LABELS = {
    "active": "กำลังยืม",
    "overdue": "เกินกำหนด",
    "partial": "คืนบางส่วน",
    "closed": "ปิดสัญญา",
}


class MyLoansView(ft.Container):
    """Read-only list of the signed-in borrower's own loans."""

    def __init__(
        self,
        service: FakeInventoryService | None = None,
        *,
        current_user: AppUser | None = None,
        mobile: bool = False,
    ) -> None:
        super().__init__(expand=True, padding=0)
        self.service = service or FakeInventoryService()
        self.mobile = mobile
        self.current_user = current_user
        self._table_width: float | None = None
        self._surface_width: float | None = None

        self.search_field = ft.TextField(
            label="ค้นหารายการยืม",
            hint_text="เช่น loan-1",
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
        self._build_view()
        self.on_size_change = self._handle_resize

    def _build_view(self) -> None:
        header = build_page_header(
            title="ของฉัน",
            subtitle="รายการยืมและกำหนดการคืนของฉัน",
            icon=ft.Icons.ASSIGNMENT_IND_OUTLINED,
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
                            controls=[self.filter_dropdown],
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
                action_controls=[self.filter_dropdown],
            )

        self.content = ft.Column(
            controls=[
                header,
                filter_bar,
                self.loan_container,
            ],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        self._render_loans()

    @staticmethod
    def _translate_loan_status(status: str) -> str:
        return _LOAN_STATUS_LABELS.get(status, status.title())

    def _render_loans(self) -> None:
        borrower_id = (
            self.current_user.borrower_id
            if self.current_user is not None
            else None
        )
        loans = (
            self.service.list_loans_for_borrower(
                borrower_id, filter_type=self.filter_dropdown.value
            )
            if borrower_id is not None
            else []
        )
        query = (self.search_field.value or "").strip().lower()
        if query:
            loans = [
                loan
                for loan in loans
                if query in loan.id.lower() or query in loan.borrower_code.lower()
            ]
        if not loans:
            self.loan_container.content = build_state_view(
                "ไม่พบรายการยืม",
                "คุณยังไม่มีรายการยืมในขณะนี้",
                icon=ft.Icons.ASSIGNMENT_IND_OUTLINED,
            )
            return

        if self.mobile:
            self.loan_container.content = build_card_list(
                [
                    build_data_card(
                        title=f"รายการยืม {loan.id}",
                        icon=ft.Icons.ASSIGNMENT_IND_OUTLINED,
                        status=(loan.status, self._translate_loan_status(loan.status)),
                        fields=[
                            ("ครบกำหนด", loan.due_date),
                            ("คืนแล้ว", f"{len(loan.returned_unit_ids)} / {len(loan.unit_ids)} ชิ้น"),
                            ("ผู้บันทึก", loan.staff_code),
                        ],
                    )
                    for loan in loans
                ]
            )
            return

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("รายการ"), expand=2),
                ft.DataColumn(ft.Text("ครบกำหนด"), expand=2),
                ft.DataColumn(ft.Text("สถานะ"), expand=2),
                ft.DataColumn(ft.Text("คืนแล้ว"), expand=2),
                ft.DataColumn(ft.Text("ผู้บันทึก"), expand=2),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(f"รายการยืม {loan.id}", weight=ft.FontWeight.W_600)),
                        ft.DataCell(
                            ft.Text(
                                loan.due_date,
                                color=ft.Colors.RED_700 if loan.status == "overdue" else COLOR_TEXT_PRIMARY,
                                weight=ft.FontWeight.W_600 if loan.status == "overdue" else ft.FontWeight.NORMAL,
                            )
                        ),
                        ft.DataCell(build_status_chip(loan.status, self._translate_loan_status(loan.status))),
                        ft.DataCell(ft.Text(f"{len(loan.returned_unit_ids)} / {len(loan.unit_ids)} ชิ้น")),
                        ft.DataCell(ft.Text(loan.staff_code)),
                    ]
                )
                for loan in loans
            ],
            column_spacing=24,
            horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_200),
        )
        self.loan_container.content = build_table_surface(
            table,
            table_width=1000,
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

    def _handle_filter_change(self, e: ft.ControlEvent) -> None:
        self._render_loans()

    def _handle_search(self, e: ft.ControlEvent | None) -> None:
        self._render_loans()
