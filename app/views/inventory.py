import flet as ft

from app.components.common import build_state_view
from app.services.fake_services import FakeInventoryService


class InventoryView(ft.Container):
    def __init__(self, service: FakeInventoryService | None = None) -> None:
        super().__init__(expand=True, padding=8)
        self.service = service or FakeInventoryService()
        self.search_field = ft.TextField(label="Search by asset code or equipment", hint_text="Try 'microscope'")
        self.status_dropdown = ft.Dropdown(
            label="Status",
            options=[
                ft.dropdown.Option("all", "All"),
                ft.dropdown.Option("available", "Available"),
                ft.dropdown.Option("borrowed", "Borrowed"),
                ft.dropdown.Option("maintenance", "Maintenance"),
                ft.dropdown.Option("reported_lost", "Reported lost"),
                ft.dropdown.Option("retired", "Retired"),
            ],
            value="all",
        )
        self.equipment_name_field = ft.TextField(label="Equipment name")
        self.equipment_code_field = ft.TextField(label="Equipment code")
        self.category_field = ft.TextField(label="Category")
        self.asset_code_field = ft.TextField(label="Asset code")
        self.location_field = ft.TextField(label="Location")
        self.reason_field = ft.TextField(label="Reason")
        self.status_action_dropdown = ft.Dropdown(
            label="Action",
            options=[
                ft.dropdown.Option("relocate", "Relocate"),
                ft.dropdown.Option("maintenance", "Repair complete"),
                ft.dropdown.Option("retired", "Retire"),
            ],
            value="relocate",
        )
        self.feedback_text = ft.Text("", size=13, color=ft.Colors.GREY_700)
        self.unit_cards_container = ft.Container(expand=True)
        self._build_view()

    def _build_view(self) -> None:
        self.content = ft.Column(
            controls=[
                ft.Text("Inventory", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Search, manage, and review equipment units.", size=14, color=ft.Colors.GREY_700),
                ft.Row(controls=[self.search_field, self.status_dropdown], spacing=12),
                ft.Row(
                    controls=[
                        ft.Button("Search", on_click=self._handle_search),
                        ft.OutlinedButton("Reset", on_click=self._handle_reset),
                    ],
                    spacing=12,
                ),
                ft.Column(
                    controls=[
                        ft.Text("Add equipment", size=18, weight=ft.FontWeight.BOLD),
                        self.equipment_name_field,
                        self.equipment_code_field,
                        self.category_field,
                        ft.Button("Save equipment", on_click=self._handle_create_equipment),
                    ],
                    spacing=8,
                ),
                ft.Column(
                    controls=[
                        ft.Text("Add unit", size=18, weight=ft.FontWeight.BOLD),
                        self.asset_code_field,
                        self.location_field,
                        ft.Button("Save unit", on_click=self._handle_create_unit),
                    ],
                    spacing=8,
                ),
                ft.Column(
                    controls=[
                        ft.Text("Update unit", size=18, weight=ft.FontWeight.BOLD),
                        self.status_action_dropdown,
                        self.reason_field,
                        ft.Button("Apply action", on_click=self._handle_update_unit),
                    ],
                    spacing=8,
                ),
                self.feedback_text,
                self.unit_cards_container,
            ],
            spacing=12,
            expand=True,
        )
        self.content.scroll = ft.ScrollMode.AUTO
        self._render_units()

    def _render_units(self) -> None:
        units = self.service.search_units(self.search_field.value or "", self.status_dropdown.value if self.status_dropdown.value != "all" else None)
        if not units:
            self.unit_cards_container.content = build_state_view("No results", "Try another search or status filter.", icon=ft.Icons.INVENTORY_2_OUTLINED)
            return

        cards = [
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(unit.asset_code, weight=ft.FontWeight.BOLD),
                        ft.Text(unit.equipment_name, size=13, color=ft.Colors.GREY_700),
                        ft.Text(unit.status.title(), size=12, color=ft.Colors.BLUE_700),
                        ft.Text(unit.location, size=12, color=ft.Colors.GREY_600),
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
            )
            for unit in units[:6]
        ]
        self.unit_cards_container.content = ft.Row(controls=cards, wrap=True, spacing=12, run_spacing=12)

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
            self.feedback_text.value = "Please complete the equipment form before saving."
            self.feedback_text.color = ft.Colors.RED_700
            self.update()
            return

        self.service.create_equipment(name, code, category)
        self.feedback_text.value = f"Created equipment {code}."
        self.feedback_text.color = ft.Colors.GREEN_700
        self.equipment_name_field.value = ""
        self.equipment_code_field.value = ""
        self.category_field.value = ""
        self.update()

    def _handle_create_unit(self, e: ft.ControlEvent) -> None:
        asset_code = self.asset_code_field.value or ""
        location = self.location_field.value or ""
        if not asset_code or not location:
            self.feedback_text.value = "Please enter an asset code and location."
            self.feedback_text.color = ft.Colors.RED_700
            self.update()
            return

        created = self.service.create_unit(asset_code=asset_code, equipment_id="eq-1", location=location)
        if created is None:
            self.feedback_text.value = "Asset code already exists."
            self.feedback_text.color = ft.Colors.RED_700
            self.update()
            return

        self.feedback_text.value = f"Created unit {asset_code}."
        self.feedback_text.color = ft.Colors.GREEN_700
        self.asset_code_field.value = ""
        self.location_field.value = ""
        self._render_units()
        self.update()

    def _handle_update_unit(self, e: ft.ControlEvent) -> None:
        asset_code = self.asset_code_field.value or ""
        reason = self.reason_field.value or ""
        if not asset_code or not reason:
            self.feedback_text.value = "Please provide an asset code and reason for the update."
            self.feedback_text.color = ft.Colors.RED_700
            self.update()
            return

        unit = self.service.get_unit(asset_code)
        if unit is None:
            self.feedback_text.value = "Asset code not found."
            self.feedback_text.color = ft.Colors.RED_700
            self.update()
            return

        status = self.status_action_dropdown.value or "relocate"
        if status == "maintenance":
            target_status = "available"
        else:
            target_status = status

        self.service.update_unit_status(unit.id, target_status, location=self.location_field.value or unit.location, reason=reason)
        self.feedback_text.value = f"Updated unit {asset_code}."
        self.feedback_text.color = ft.Colors.GREEN_700
        self.asset_code_field.value = ""
        self.location_field.value = ""
        self.reason_field.value = ""
        self._render_units()
        self.update()


def build_inventory_view(service: FakeInventoryService | None = None) -> ft.Container:
    return InventoryView(service)
