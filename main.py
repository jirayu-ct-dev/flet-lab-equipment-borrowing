import flet as ft

from app.components.common import build_state_view
from app.theme import APP_TITLE, NAVIGATION_ITEMS, NAV_WIDTH, PAGE_PADDING


def get_navigation_items() -> list[dict[str, object]]:
    return NAVIGATION_ITEMS


def build_home() -> ft.Control:
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


def build_app_shell() -> ft.Container:
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
        content=build_home(),
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
    page.add(build_app_shell())


if __name__ == "__main__":
    ft.run(main)
