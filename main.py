import flet as ft

from app.components.common import update_control
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
    MOBILE_BREAKPOINT,
)

from app.views.borrow_flow import BorrowFlowView
from app.views.dashboard import DashboardView
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
        {"label": "Dashboard", "icon": ft.Icons.DASHBOARD_OUTLINED},
        {"label": "อุปกรณ์", "icon": ft.Icons.INVENTORY_2_OUTLINED},
        {"label": "คนในระบบ", "icon": ft.Icons.PEOPLE_OUTLINED},
        {"label": "ทำรายการยืม", "icon": ft.Icons.ASSIGNMENT_OUTLINED},
        {"label": "คืนอุปกรณ์", "icon": ft.Icons.RECEIPT_LONG_OUTLINED},
        {"label": "ประวัติ", "icon": ft.Icons.HISTORY_OUTLINED},
    ]


def build_screen(
    content: ft.Control,
) -> ft.Control:

    return ft.Container(
        expand=True,
        padding=32,
        alignment=ft.Alignment.TOP_LEFT,
        bgcolor=COLOR_BG,
        content=content,
    )


def build_app_shell(
    services=None,
    *,
    width: float | None = None,
) -> ft.Control:

    service = get_service(services)
    mobile = width is not None and width <= MOBILE_BREAKPOINT

    # ========================================================
    # CONTENT AREA
    # ========================================================

    content_area = ft.Container(
        expand=True,
        padding=0,
        alignment=ft.Alignment.TOP_LEFT,
        bgcolor=COLOR_BG,
        content=build_screen(
            DashboardView(service, mobile=mobile)
        ),
    )

    # ========================================================
    # SIDEBAR BRAND HEADER
    # ========================================================

    brand_header = ft.Container(
        padding=ft.Padding.only(left=8, right=8, top=16, bottom=16),
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.INVENTORY_2_ROUNDED, color=ft.Colors.WHITE, size=20),
                    bgcolor=ft.Colors.BLUE_600,
                    padding=8,
                    border_radius=8,
                ),
                ft.Column(
                    controls=[
                        ft.Text("ระบบยืม–คืนอุปกรณ์", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE),
                        ft.Text("รองรับอุปกรณ์ทุกประเภท", size=11, color=COLOR_SIDEBAR_TEXT),
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
    # SIDEBAR NAVIGATION
    # ========================================================

    menu_tiles: list[ft.ListTile] = []

    # ========================================================
    # NAVIGATION EVENT
    # ========================================================

    def navigate_to(index: int) -> None:
        is_mobile = mobile_navigation.visible
        mobile_navigation.selected_index = index

        for tile_index, tile in enumerate(menu_tiles):
            is_selected = tile_index == index
            tile.selected = is_selected
            tile.leading.icon = NAVIGATION_ITEMS[tile_index].get(
                "selected_icon" if is_selected else "icon",
                NAVIGATION_ITEMS[tile_index]["icon"],
            )
            tile.title.weight = ft.FontWeight.BOLD if is_selected else ft.FontWeight.W_500

        if index == 0:
            content_area.content = build_screen(
                DashboardView(service, mobile=is_mobile)
            )

        elif index == 1:
            content_area.content = build_screen(
                build_inventory_view(service, mobile=is_mobile)
            )

        elif index == 2:
            content_area.content = build_screen(
                StaffBorrowersView(service, mobile=is_mobile)
            )

        elif index == 3:
            content_area.content = build_screen(
                BorrowFlowView(service)
            )

        elif index == 4:
            content_area.content = build_screen(
                LoansView(service, mobile=is_mobile)
            )

        elif index == 5:
            content_area.content = build_screen(
                build_history_view(service, mobile=is_mobile)
            )

        else:
            content_area.content = build_screen(
                DashboardView(service, mobile=is_mobile)
            )

        update_control(navigation_menu)
        update_control(content_area)

    menu_tiles.extend(
        ft.ListTile(
            leading=ft.Icon(
                item.get("selected_icon", item["icon"]) if index == 0 else item["icon"],
                size=20,
            ),
            title=ft.Text(
                item["label"],
                size=13,
                weight=ft.FontWeight.BOLD if index == 0 else ft.FontWeight.W_500,
            ),
            selected=index == 0,
            selected_color=COLOR_SIDEBAR_ACTIVE,
            selected_tile_color=ft.Colors.with_opacity(0.12, COLOR_SIDEBAR_ACTIVE),
            icon_color=COLOR_SIDEBAR_TEXT,
            text_color=COLOR_SIDEBAR_TEXT,
            hover_color=ft.Colors.with_opacity(0.08, COLOR_SIDEBAR_ACTIVE),
            shape=ft.RoundedRectangleBorder(radius=12),
            content_padding=ft.Padding.symmetric(horizontal=12),
            horizontal_spacing=12,
            min_leading_width=20,
            min_height=48,
            on_click=lambda e, index=index: navigate_to(index),
        )
        for index, item in enumerate(NAVIGATION_ITEMS)
    )

    navigation_menu = ft.Column(
        controls=menu_tiles,
        spacing=4,
        tight=True,
    )

    mobile_navigation = ft.NavigationBar(
        selected_index=0,
        visible=mobile,
        label_behavior=ft.NavigationBarLabelBehavior.ONLY_SHOW_SELECTED,
        destinations=[
            ft.NavigationBarDestination(
                icon=item["icon"],
                selected_icon=item.get("selected_icon", item["icon"]),
                label=item["label"],
            )
            for item in NAVIGATION_ITEMS
        ],
        on_change=lambda e: navigate_to(e.control.selected_index),
    )

    # ========================================================
    # SIDEBAR
    # ========================================================

    sidebar = ft.Container(
        width=NAV_WIDTH,
        padding=12,
        bgcolor=COLOR_SIDEBAR_BG,
        alignment=ft.Alignment.TOP_LEFT,
        content=ft.Column(
            controls=[brand_header, navigation_menu],
            spacing=8,
            tight=True,
        ),
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
        content=ft.Column(
            controls=[row, mobile_navigation],
            spacing=0,
            expand=True,
        ),
    )


def apply_shell_width(shell: ft.Container, width: float | None) -> None:
    """Switch between desktop rail and mobile bottom navigation."""
    if width is None:
        return
    row, mobile_navigation = shell.content.controls
    is_mobile = width <= MOBILE_BREAKPOINT
    row.controls[0].visible = not is_mobile
    row.controls[1].visible = not is_mobile
    row.controls[2].content.padding = 20 if is_mobile else 32
    mobile_navigation.visible = is_mobile
    update_control(shell)


def build_home(services=None) -> ft.SafeArea:
    return ft.SafeArea(
        content=build_app_shell(services),
        expand=True,
    )


def main(
    page: ft.Page,
) -> None:

    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE_600)
    page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE_400)
    page.padding = 0
    page.bgcolor = COLOR_BG

    services = create_app_services()

    shell = build_app_shell(services, width=page.width)
    apply_shell_width(shell, page.width)
    page.on_resize = lambda _: apply_shell_width(shell, page.width)
    page.add(ft.Container(expand=True, content=shell))


if __name__ == "__main__":
    ft.run(main)
