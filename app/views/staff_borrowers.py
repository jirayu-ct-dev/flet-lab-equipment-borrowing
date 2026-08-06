import flet as ft

from app.components.common import build_state_view
from app.services.fake_services import FakeInventoryService


class StaffBorrowersView(ft.Container):
    def __init__(self, service: FakeInventoryService | None = None) -> None:
        super().__init__(expand=True, padding=8)
        self.service = service or FakeInventoryService()
        self.selected_mode = "staff"
        self.staff_search = ft.TextField(label="Search staff")
        self.borrower_search = ft.TextField(label="Search borrowers")
        self.staff_name = ft.TextField(label="Full name")
        self.staff_code = ft.TextField(label="Staff code")
        self.staff_email = ft.TextField(label="Email")
        self.borrower_name = ft.TextField(label="Full name")
        self.borrower_code = ft.TextField(label="Borrower code")
        self.borrower_department = ft.TextField(label="Department")
        self.borrower_email = ft.TextField(label="Email")
        self.feedback = ft.Text("", size=13, color=ft.Colors.GREY_700)
        self.staff_container = ft.Container(expand=True)
        self.borrower_container = ft.Container(expand=True)
        self.mode_container = ft.Container(expand=True)
        self._build_view()

    def _build_view(self) -> None:
        self.content = ft.Column(
            controls=[
                ft.Text("Staff & Borrowers", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Search, add, and edit staff or borrowers. Inactive records remain visible for history and review.", size=14, color=ft.Colors.GREY_700),
                ft.Row(
                    controls=[
                        ft.Button("Staff", on_click=self._switch_to_staff),
                        ft.OutlinedButton("Borrowers", on_click=self._switch_to_borrowers),
                    ],
                    spacing=12,
                ),
                self.mode_container,
            ],
            spacing=12,
            expand=True,
        )
        self.content.scroll = ft.ScrollMode.AUTO
        self._refresh_mode_content()
        self._render_staff()
        self._render_borrowers()

    def _build_staff_tab(self) -> ft.Control:
        return ft.Column(
            controls=[
                self.staff_search,
                ft.Row(
                    controls=[
                        ft.Button("Search", on_click=self._handle_staff_search),
                        ft.OutlinedButton("Reset", on_click=self._handle_staff_reset),
                    ],
                    spacing=12,
                ),
                ft.Column(
                    controls=[
                        ft.Text("Add / edit staff", size=18, weight=ft.FontWeight.BOLD),
                        self.staff_code,
                        self.staff_name,
                        self.staff_email,
                        ft.Button("Save staff", on_click=self._handle_save_staff),
                    ],
                    spacing=8,
                ),
                self.feedback,
                self.staff_container,
            ],
            spacing=12,
        )

    def _build_borrower_tab(self) -> ft.Control:
        return ft.Column(
            controls=[
                self.borrower_search,
                ft.Row(
                    controls=[
                        ft.Button("Search", on_click=self._handle_borrower_search),
                        ft.OutlinedButton("Reset", on_click=self._handle_borrower_reset),
                    ],
                    spacing=12,
                ),
                ft.Column(
                    controls=[
                        ft.Text("Add / edit borrowers", size=18, weight=ft.FontWeight.BOLD),
                        self.borrower_code,
                        self.borrower_name,
                        self.borrower_department,
                        self.borrower_email,
                        ft.Button("Save borrower", on_click=self._handle_save_borrower),
                    ],
                    spacing=8,
                ),
                self.feedback,
                self.borrower_container,
            ],
            spacing=12,
        )

    def _refresh_mode_content(self) -> None:
        if self.selected_mode == "staff":
            self.mode_container.content = self._build_staff_tab()
        else:
            self.mode_container.content = self._build_borrower_tab()

    def _switch_to_staff(self, e: ft.ControlEvent) -> None:
        self.selected_mode = "staff"
        self._refresh_mode_content()
        self.update()

    def _switch_to_borrowers(self, e: ft.ControlEvent) -> None:
        self.selected_mode = "borrowers"
        self._refresh_mode_content()
        self.update()

    def _render_staff(self) -> None:
        keyword = (self.staff_search.value or "").strip().lower()
        staff = self.service.list_staff(include_inactive=True)
        if keyword:
            staff = [item for item in staff if keyword in item.full_name.lower() or keyword in item.staff_code.lower()]
        if not staff:
            self.staff_container.content = build_state_view("No staff", "No staff records match the current search.", icon=ft.Icons.PEOPLE_OUTLINED)
            return
        cards = [
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(item.full_name, weight=ft.FontWeight.BOLD),
                        ft.Text(item.staff_code, size=13, color=ft.Colors.GREY_700),
                        ft.Text(item.status.title(), size=12, color=ft.Colors.BLUE_700),
                        ft.Text(item.email or "No email", size=12, color=ft.Colors.GREY_600),
                    ],
                    spacing=4,
                    tight=True,
                ),
                padding=12,
                border=ft.border.Border(
                    left=ft.border.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                    right=ft.border.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                    top=ft.border.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                    bottom=ft.border.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                ),
                border_radius=8,
                width=220,
            ) for item in staff[:6]
        ]
        self.staff_container.content = ft.Row(controls=cards, wrap=True, spacing=12, run_spacing=12)

    def _render_borrowers(self) -> None:
        keyword = (self.borrower_search.value or "").strip().lower()
        borrowers = self.service.list_borrowers(include_inactive=True)
        if keyword:
            borrowers = [item for item in borrowers if keyword in item.full_name.lower() or keyword in item.borrower_code.lower()]
        if not borrowers:
            self.borrower_container.content = build_state_view("No borrowers", "No borrower records match the current search.", icon=ft.Icons.PERSON_OUTLINED)
            return
        cards = [
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(item.full_name, weight=ft.FontWeight.BOLD),
                        ft.Text(item.borrower_code, size=13, color=ft.Colors.GREY_700),
                        ft.Text(item.status.title(), size=12, color=ft.Colors.BLUE_700),
                        ft.Text(item.department or "No department", size=12, color=ft.Colors.GREY_600),
                    ],
                    spacing=4,
                    tight=True,
                ),
                padding=12,
                border=ft.border.Border(
                    left=ft.border.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                    right=ft.border.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                    top=ft.border.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                    bottom=ft.border.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                ),
                border_radius=8,
                width=220,
            ) for item in borrowers[:6]
        ]
        self.borrower_container.content = ft.Row(controls=cards, wrap=True, spacing=12, run_spacing=12)

    def _handle_staff_search(self, e: ft.ControlEvent) -> None:
        self._render_staff()

    def _handle_staff_reset(self, e: ft.ControlEvent) -> None:
        self.staff_search.value = ""
        self._render_staff()

    def _handle_borrower_search(self, e: ft.ControlEvent) -> None:
        self._render_borrowers()

    def _handle_borrower_reset(self, e: ft.ControlEvent) -> None:
        self.borrower_search.value = ""
        self._render_borrowers()

    def _handle_save_staff(self, e: ft.ControlEvent) -> None:
        code = (self.staff_code.value or "").strip()
        name = (self.staff_name.value or "").strip()
        email = (self.staff_email.value or "").strip() or None
        if not code or not name:
            self.feedback.value = "Please enter staff code and name."
            self.feedback.color = ft.Colors.RED_700
            self.update()
            return
        existing = self.service.get_staff(code)
        if existing is None:
            self.service.create_staff(code, name, email=email)
        else:
            self.service.update_staff(code, full_name=name, email=email)
        self.feedback.value = f"Saved staff {code}."
        self.feedback.color = ft.Colors.GREEN_700
        self.staff_code.value = ""
        self.staff_name.value = ""
        self.staff_email.value = ""
        self._render_staff()
        self.update()

    def _handle_save_borrower(self, e: ft.ControlEvent) -> None:
        code = (self.borrower_code.value or "").strip()
        name = (self.borrower_name.value or "").strip()
        department = (self.borrower_department.value or "").strip() or None
        email = (self.borrower_email.value or "").strip() or None
        if not code or not name:
            self.feedback.value = "Please enter borrower code and name."
            self.feedback.color = ft.Colors.RED_700
            self.update()
            return
        existing = self.service.get_borrower(code)
        if existing is None:
            self.service.create_borrower(code, name, department=department, email=email)
        else:
            self.service.update_borrower(code, full_name=name, department=department, email=email)
        self.feedback.value = f"Saved borrower {code}."
        self.feedback.color = ft.Colors.GREEN_700
        self.borrower_code.value = ""
        self.borrower_name.value = ""
        self.borrower_department.value = ""
        self.borrower_email.value = ""
        self._render_borrowers()
        self.update()
