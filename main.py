import flet as ft

from app.components.common import build_state_view
from app.services.container import create_app_services
from app.theme import APP_TITLE, NAVIGATION_ITEMS, NAV_WIDTH, PAGE_PADDING


def get_navigation_items() -> list[dict[str, object]]:
    return NAVIGATION_ITEMS


def build_home(services=None) -> ft.Control:
    inventory_service = services.inventory_service if services is not None else None
    units = inventory_service.list_units() if inventory_service is not None else []

    status_summary = ft.Column(
        controls=[
            ft.Text("Inventory overview", size=24, weight=ft.FontWeight.BOLD),
            ft.Text("Demo data is sourced from the frontend service container.", size=14, color=ft.Colors.GREY_700),
        ],
        spacing=4,
        tight=True,
    )

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
        for unit in units[:4]
    ]

    return ft.SafeArea(
        ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.SCIENCE_OUTLINED, size=64, color=ft.Colors.BLUE_700),
                    ft.Text(
                        APP_TITLE,
                        size=32,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Flet Web foundation is running.",
                        size=16,
                        color=ft.Colors.GREY_700,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    status_summary,
                    ft.Row(
                        controls=unit_cards,
                        wrap=True,
                        spacing=12,
                        run_spacing=12,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
                tight=True,
            ),
            alignment=ft.Alignment.CENTER,
            expand=True,
            padding=24,
        ),
        expand=True,
    )


def build_app_shell(services=None) -> ft.Container:
    nav = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=NAV_WIDTH,
        min_extended_width=NAV_WIDTH + 40,
        destinations=[
            ft.NavigationRailDestination(
                icon=item["icon"],
                label=item["label"],
            )
            for item in NAVIGATION_ITEMS
        ],
        on_change=lambda e: None,
    )

    content_area = ft.Container(
        content=build_home(services),
        expand=True,
        padding=PAGE_PADDING,
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=nav,
                    width=NAV_WIDTH,
                    padding=ft.padding.Padding(top=12, left=12, bottom=12, right=0),
                    bgcolor=ft.Colors.BLUE_50,
                ),
                ft.VerticalDivider(width=1),
                content_area,
            ],
            expand=True,
        ),
        expand=True,
        padding=0,
    )


def main(page: ft.Page) -> None:
    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    services = create_app_services()
    page.add(build_app_shell(services))


if __name__ == "__main__":
    ft.run(main)
