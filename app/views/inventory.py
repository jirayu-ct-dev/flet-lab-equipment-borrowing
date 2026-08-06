import flet as ft

from app.components.common import build_state_view
from app.services.fake_services import FakeInventoryService


def build_inventory_view(service: FakeInventoryService) -> ft.Container:
    units = service.list_units()

    if not units:
        return build_state_view("No inventory", "No inventory items are available yet.", icon=ft.Icons.INVENTORY_2_OUTLINED)

    unit_cards = [
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

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Inventory", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Search, manage, and review equipment units.", size=14, color=ft.Colors.GREY_700),
                ft.TextField(label="Search by asset code or equipment", hint_text="Try 'microscope'"),
                ft.Row(
                    controls=[
                        ft.ElevatedButton("Add equipment", icon=ft.Icons.ADD),
                        ft.OutlinedButton("Add unit", icon=ft.Icons.QR_CODE_2),
                    ],
                    spacing=12,
                ),
                ft.Row(
                    controls=unit_cards,
                    wrap=True,
                    spacing=12,
                    run_spacing=12,
                ),
            ],
            spacing=12,
            expand=True,
        ),
        expand=True,
        padding=8,
    )
