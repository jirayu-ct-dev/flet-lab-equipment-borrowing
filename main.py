import flet as ft

from app.services.container import create_app_services
from app.services.fake_services import FakeInventoryService

from app.theme import (
    APP_TITLE,
    NAVIGATION_ITEMS,
    NAV_WIDTH,
    COLOR_BG,
    COLOR_SIDEBAR_BG,
    COLOR_SIDEBAR_ACTIVE,
    COLOR_SIDEBAR_TEXT,
)

from app.views.borrow_flow import BorrowFlowView
from app.views.history import build_history_view
from app.views.inventory import build_inventory_view
from app.views.loans import LoansView
from app.views.staff_borrowers import StaffBorrowersView


def get_service(services=None):
    if services is not None:
        service = getattr(
            services,
            "inventory_service",
            None,
        )

        if service is not None:
            return service

    return FakeInventoryService()


def get_navigation_items():
    return [
        {"label": "Inventory", "icon": ft.Icons.INVENTORY_2_OUTLINED},
        {"label": "Staff", "icon": ft.Icons.PEOPLE_OUTLINED},
        {"label": "Borrowers", "icon": ft.Icons.PERSON_OUTLINED},
        {"label": "Loans", "icon": ft.Icons.RECEIPT_LONG_OUTLINED},
        {"label": "History", "icon": ft.Icons.HISTORY_OUTLINED},
    ]


def build_screen(
    content: ft.Control,
) -> ft.Control:

    return ft.Container(
        expand=True,
        padding=24,
        alignment=ft.Alignment.TOP_LEFT,
        bgcolor=COLOR_BG,
        content=content,
    )


def build_app_shell(
    services=None,
) -> ft.Control:

    service = get_service(services)

    # ========================================================
    # CONTENT AREA
    # ========================================================

    content_area = ft.Container(
        expand=True,
        padding=0,
        alignment=ft.Alignment.TOP_LEFT,
        bgcolor=COLOR_BG,
        content=build_screen(
            build_inventory_view(service)
        ),
    )

    # ========================================================
    # SIDEBAR BRAND HEADER
    # ========================================================

    brand_header = ft.Container(
        padding=ft.padding.only(left=8, right=8, top=16, bottom=16),
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.SCIENCE_ROUNDED, color=ft.Colors.WHITE, size=20),
                    bgcolor=ft.Colors.BLUE_600,
                    padding=8,
                    border_radius=8,
                ),
                ft.Column(
                    controls=[
                        ft.Text("LabEquip", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text("ระบบยืมอุปกรณ์", size=11, color=COLOR_SIDEBAR_TEXT),
                    ],
                    spacing=1,
                    tight=True,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    # ========================================================
    # NAVIGATION RAIL
    # ========================================================

    navigation = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=180,
        min_extended_width=220,
        bgcolor=COLOR_SIDEBAR_BG,
        leading=brand_header,
        indicator_color=ft.Colors.with_opacity(0.15, COLOR_SIDEBAR_ACTIVE),
        selected_label_style=ft.TextStyle(
            color=COLOR_SIDEBAR_ACTIVE,
            weight=ft.FontWeight.BOLD,
            size=12,
        ),
        unselected_label_style=ft.TextStyle(
            color=COLOR_SIDEBAR_TEXT,
            weight=ft.FontWeight.W_500,
            size=12,
        ),
        destinations=[
            ft.NavigationRailDestination(
                icon=item["icon"],
                selected_icon=item.get("selected_icon", item["icon"]),
                label=item["label"],
            )
            for item in NAVIGATION_ITEMS
        ],
    )

    # ========================================================
    # NAVIGATION EVENT
    # ========================================================

    def on_navigation_change(
        e: ft.ControlEvent,
    ) -> None:

        index = e.control.selected_index

        if index == 0:
            content_area.content = build_screen(
                build_inventory_view(service)
            )

        elif index == 1:
            content_area.content = build_screen(
                StaffBorrowersView(service)
            )

        elif index == 2:
            content_area.content = build_screen(
                BorrowFlowView(service)
            )

        elif index == 3:
            content_area.content = build_screen(
                LoansView(service)
            )

        elif index == 4:
            content_area.content = build_screen(
                build_history_view()
            )

        else:
            content_area.content = build_screen(
                build_inventory_view(service)
            )

        content_area.update()

    navigation.on_change = on_navigation_change

    # ========================================================
    # SIDEBAR
    # ========================================================

    sidebar = ft.Container(
        width=NAV_WIDTH,
        padding=12,
        bgcolor=COLOR_SIDEBAR_BG,
        alignment=ft.Alignment.TOP_CENTER,
        content=navigation,
    )

    # ========================================================
    # MAIN LAYOUT
    # ========================================================

    row = ft.Row(
        expand=True,
        spacing=0,
        controls=[
            sidebar,

            ft.VerticalDivider(
                width=1,
                color=ft.Colors.TRANSPARENT,
            ),

            content_area,
        ],
    )

    return ft.Container(
        expand=True,
        padding=0,
        content=row,
    )


def build_home(services=None) -> ft.SafeArea:
    return ft.SafeArea(
        content=build_app_shell(services),
        expand=True,
    )


def main(
    page: ft.Page,
) -> None:

    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.bgcolor = COLOR_BG

    services = create_app_services()

    page.add(
        ft.Container(
            expand=True,
            content=build_app_shell(
                services
            ),
        )
    )


if __name__ == "__main__":
    ft.run(main)
