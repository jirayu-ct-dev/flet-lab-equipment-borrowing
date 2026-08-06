import flet as ft

from app.services.container import create_app_services
from app.services.fake_services import FakeInventoryService
from app.theme import APP_TITLE, NAVIGATION_ITEMS, NAV_WIDTH, PAGE_PADDING
from app.views.borrow_flow import BorrowFlowView
from app.views.inventory import build_inventory_view
from app.views.staff_borrowers import StaffBorrowersView


def get_navigation_items() -> list[dict[str, object]]:
    return NAVIGATION_ITEMS


def build_home(services=None) -> ft.Control:
    inventory_service = services.inventory_service if services is not None else None
    if inventory_service is None:
        inventory_service = FakeInventoryService()

    return ft.SafeArea(
        ft.Container(
            content=build_inventory_view(inventory_service),
            alignment=ft.Alignment.TOP_LEFT,
            expand=True,
            padding=24,
        ),
        expand=True,
    )


def build_staff_borrowers_view(services=None) -> ft.Control:
    service = services.inventory_service if services is not None else None
    if service is None:
        service = FakeInventoryService()
    return StaffBorrowersView(service)


def build_borrow_flow_view(services=None) -> ft.Control:
    service = services.inventory_service if services is not None else None
    if service is None:
        service = FakeInventoryService()
    return ft.SafeArea(
        ft.Container(
            content=BorrowFlowView(service),
            alignment=ft.Alignment.TOP_LEFT,
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
    )

    content_area = ft.Container(
        content=ft.Container(content=build_home(services), expand=True, padding=PAGE_PADDING),
        expand=True,
        padding=0,
    )
    content_area.content.expand = True
    content_area.content.scroll = ft.ScrollMode.AUTO

    def handle_navigation_change(e: ft.ControlEvent) -> None:
        selected_index = getattr(e.control, "selected_index", 0)
        if selected_index == 0:
            content_area.content.content = build_home(services)
        elif selected_index == 1:
            content_area.content.content = build_staff_borrowers_view(services)
        elif selected_index == 2:
            content_area.content.content = build_borrow_flow_view(services)
        else:
            content_area.content.content = build_home(services)

        try:
            content_area.update()
        except RuntimeError:
            pass

    nav.on_change = handle_navigation_change
    nav.expand = True

    nav_container = ft.Container(
        content=nav,
        width=NAV_WIDTH,
        padding=ft.padding.Padding(top=12, left=12, bottom=12, right=0),
        bgcolor=ft.Colors.BLUE_50,
        alignment=ft.Alignment.TOP_LEFT,
    )
    nav_container.height = 900

    return ft.Container(
        content=ft.Row(
            controls=[
                nav_container,
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
    page.scroll = ft.ScrollMode.AUTO
    page.vertical_alignment = ft.MainAxisAlignment.START
    services = create_app_services()
    page.add(build_app_shell(services))


if __name__ == "__main__":
    ft.run(main)
