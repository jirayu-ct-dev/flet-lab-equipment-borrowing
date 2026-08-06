import flet as ft

from app.services.fake_services import FakeInventoryService


class BorrowFlowView(ft.Container):
    def __init__(self, service: FakeInventoryService | None = None) -> None:
        super().__init__(expand=True, padding=8)
        self.service = service or FakeInventoryService()
        self.borrower_dropdown = ft.Dropdown(label="Borrower", options=[ft.dropdown.Option(item.borrower_code, item.full_name) for item in self.service.list_borrowers(include_inactive=True)], value=None)
        self.staff_dropdown = ft.Dropdown(label="Staff", options=[ft.dropdown.Option(item.staff_code, item.full_name) for item in self.service.list_staff(include_inactive=True)], value=None)
        self.unit_dropdown = ft.Dropdown(label="Unit", options=[ft.dropdown.Option(unit.id, f"{unit.asset_code} - {unit.status}") for unit in self.service.search_units(status="available")], value=None)
        self.borrow_date = ft.TextField(label="Borrow date")
        self.due_date = ft.TextField(label="Due date")
        self.purpose = ft.TextField(label="Purpose")
        self.note = ft.TextField(label="Note")
        self.summary = ft.Text("", size=13, color=ft.Colors.GREY_700)
        self._build_view()

    def _build_view(self) -> None:
        self.content = ft.Column(
            controls=[
                ft.Text("Borrow flow", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Create a basic borrow draft for a borrower, staff, and available units.", size=14, color=ft.Colors.GREY_700),
                self.borrower_dropdown,
                self.staff_dropdown,
                self.unit_dropdown,
                self.borrow_date,
                self.due_date,
                self.purpose,
                self.note,
                ft.Row(
                    controls=[
                        ft.Button("Create draft", on_click=self._handle_create_draft),
                        ft.OutlinedButton("Confirm", on_click=self._handle_confirm_draft),
                    ],
                    spacing=12,
                ),
                self.summary,
            ],
            spacing=12,
            expand=True,
        )
        self.content.scroll = ft.ScrollMode.AUTO

    def _handle_create_draft(self, e: ft.ControlEvent) -> None:
        borrower_code = self.borrower_dropdown.value or ""
        staff_code = self.staff_dropdown.value or ""
        unit_id = self.unit_dropdown.value or ""
        borrow_date = self.borrow_date.value or ""
        due_date = self.due_date.value or ""
        purpose = self.purpose.value or ""
        if not borrower_code or not staff_code or not unit_id or not borrow_date or not due_date or not purpose:
            self.summary.value = "Please fill in borrower, staff, unit, dates, and purpose."
            self.summary.color = ft.Colors.RED_700
            self.update()
            return

        draft = self.service.create_borrow_draft(
            borrower_code=borrower_code,
            staff_code=staff_code,
            unit_ids=[unit_id],
            borrow_date=borrow_date,
            due_date=due_date,
            purpose=purpose,
        )
        if draft is None:
            self.summary.value = "Unable to create draft."
            self.summary.color = ft.Colors.RED_700
            self.update()
            return

        self.summary.value = f"Draft created for {borrower_code} with unit {unit_id}."
        self.summary.color = ft.Colors.GREEN_700
        self.update()

    def _handle_confirm_draft(self, e: ft.ControlEvent) -> None:
        if not self.service._borrow_drafts:
            self.summary.value = "Create a draft before confirming."
            self.summary.color = ft.Colors.RED_700
            self.update()
            return

        draft = self.service.confirm_borrow_draft(self.service._borrow_drafts[-1].id)
        if draft is None:
            self.summary.value = "Could not confirm the borrow draft."
            self.summary.color = ft.Colors.RED_700
            self.update()
            return

        self.summary.value = f"Confirmed loan for draft {draft.id}."
        self.summary.color = ft.Colors.GREEN_700
        self.update()
