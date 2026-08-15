import flet as ft

from app.components.common import update_control
from app.contracts import AppUser, Permission, Role, has_permission
from app.env import load_env_file
from app.services.container import create_app_services
from app.services.fake_services import FakeInventoryService
from app.services.line_login import get_line_provider, register_or_fetch_user

from app.theme import (
    APP_TITLE,
    NAV_WIDTH,
    COLOR_BG,
    COLOR_SIDEBAR_BG,
    COLOR_SIDEBAR_ACTIVE,
    COLOR_SIDEBAR_TEXT,
    MOBILE_BREAKPOINT,
    visible_navigation_items,
)

from app.views.borrow_flow import BorrowFlowView
from app.views.dashboard import DashboardView
from app.views.history import build_history_view
from app.views.inventory import build_inventory_view
from app.views.loans import LoansView
from app.views.my_loans import MyLoansView
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
        {"label": "ของฉัน", "icon": ft.Icons.ASSIGNMENT_IND_OUTLINED},
        {"label": "คนในระบบ", "icon": ft.Icons.PEOPLE_OUTLINED},
        {"label": "ทำรายการยืม", "icon": ft.Icons.ASSIGNMENT_OUTLINED},
        {"label": "คืนอุปกรณ์", "icon": ft.Icons.RECEIPT_LONG_OUTLINED},
        {"label": "ประวัติ", "icon": ft.Icons.HISTORY_OUTLINED},
    ]


def build_screen(
    content: ft.Control,
    *,
    logout_action=None,
) -> ft.Control:

    if logout_action is not None:
        content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.Icons.LOGOUT,
                            tooltip="ออกจากระบบ",
                            on_click=logout_action,
                        ),
                    ],
                    spacing=0,
                ),
                content,
            ],
            spacing=8,
            expand=True,
        )

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
    current_user: AppUser | None = None,
    on_logout=None,
) -> ft.Container:

    service = get_service(services)
    mobile = width is not None and width <= MOBILE_BREAKPOINT

    visible = visible_navigation_items(current_user)

    logout_callback = (lambda e: on_logout()) if on_logout is not None else None

    def render_view(item: dict, mobile: bool) -> ft.Control:
        route = item.get("route", "dashboard")

        if route == "dashboard":
            return DashboardView(service, mobile=mobile, current_user=current_user)

        if route == "inventory":
            return build_inventory_view(service, mobile=mobile)

        if route == "my_loans":
            return MyLoansView(service, current_user=current_user, mobile=mobile)

        if route == "people":
            return StaffBorrowersView(service, mobile=mobile, current_user=current_user)

        if route == "borrow":
            return BorrowFlowView(service, current_user=current_user)

        if route == "returns":
            return LoansView(service, mobile=mobile, current_user=current_user)

        if route == "history":
            return build_history_view(service, mobile=mobile)

        return DashboardView(service, mobile=mobile, current_user=current_user)

    # ========================================================
    # CONTENT AREA
    # ========================================================

    content_area = ft.Container(
        expand=True,
        padding=0,
        alignment=ft.Alignment.TOP_LEFT,
        bgcolor=COLOR_BG,
        content=build_screen(
            render_view(visible[0], mobile),
            logout_action=logout_callback if mobile else None,
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
                        ft.Text("ยืม-คืนครุภัณฑ์ BRU-CS", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE),
                        ft.Text("สาขาวิทยาการคอมพิวเตอร์", size=11, color=COLOR_SIDEBAR_TEXT),
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

    _nav_feedback = ft.Text(
        "",
        size=13,
        color=ft.Colors.RED_700,
        weight=ft.FontWeight.W_500,
    )

    # ========================================================
    # NAVIGATION EVENT
    # ========================================================

    def navigate_to(item: dict) -> None:
        is_mobile = mobile_navigation.visible

        if current_user is not None and not has_permission(current_user, item["permission"]):
            _nav_feedback.value = "คุณไม่มีสิทธิ์เข้าถึงหน้านี้"
            update_control(_nav_feedback)
            return

        if (
            item.get("route") == "my_loans"
            and current_user is not None
            and current_user.borrower_id is None
        ):
            _nav_feedback.value = "ไม่พบข้อมูลผู้ยืมที่เชื่อมโยงกับบัญชีนี้"
            update_control(_nav_feedback)
            return

        if _nav_feedback.value:
            _nav_feedback.value = ""
            update_control(_nav_feedback)

        index = next(
            i for i, candidate in enumerate(visible) if candidate is item
        )
        mobile_navigation.selected_index = index

        for tile_index, tile in enumerate(menu_tiles):
            is_selected = tile_index == index
            tile.selected = is_selected
            tile.leading.icon = visible[tile_index].get(
                "selected_icon" if is_selected else "icon",
                visible[tile_index]["icon"],
            )
            tile.title.weight = ft.FontWeight.BOLD if is_selected else ft.FontWeight.W_500

        content_area.content = build_screen(
            render_view(item, is_mobile),
            logout_action=logout_callback if is_mobile else None,
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
            on_click=lambda e, item=item: navigate_to(item),
        )
        for index, item in enumerate(visible)
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
            for item in visible
        ],
        on_change=lambda e: navigate_to(visible[e.control.selected_index]),
    )

    # ========================================================
    # SIDEBAR
    # ========================================================

    if current_user is None:
        display_name = "ยังไม่ได้เข้าสู่ระบบ"
        role_label = ""
    else:
        display_name = current_user.display_name
        role_label = "ผู้ดูแลระบบ" if current_user.role == Role.ADMIN else "ผู้ใช้ทั่วไป"

    logout_block = ft.Column(
        controls=[
            ft.Text(
                display_name,
                size=13,
                weight=ft.FontWeight.W_600,
                color=COLOR_SIDEBAR_TEXT,
            ),
            ft.Text(
                role_label,
                size=11,
                color=COLOR_SIDEBAR_TEXT,
            ),
            ft.OutlinedButton(
                "ออกจากระบบ",
                icon=ft.Icons.LOGOUT,
                height=40,
                visible=on_logout is not None,
                on_click=lambda e: on_logout() if on_logout is not None else None,
            ),
        ],
        spacing=8,
        tight=True,
    )

    sidebar = ft.Container(
        width=NAV_WIDTH,
        padding=12,
        bgcolor=COLOR_SIDEBAR_BG,
        alignment=ft.Alignment.TOP_LEFT,
        content=ft.Column(
            controls=[
                brand_header,
                navigation_menu,
                ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                logout_block,
                _nav_feedback,
            ],
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

    shell = ft.Container(
        expand=True,
        padding=0,
        content=ft.Column(
            controls=[row, mobile_navigation],
            spacing=0,
            expand=True,
        ),
    )

    # Testability hooks.
    shell.navigate_to = navigate_to
    shell._nav_feedback = _nav_feedback

    return shell


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

    load_env_file()

    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE_600)
    page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE_400)
    page.padding = 0
    page.bgcolor = COLOR_BG

    services = create_app_services()
    auth = services.auth_service

    root = ft.Container(expand=True)
    page.add(root)

    login_view = None

    def _set_login_feedback(message: str) -> None:
        if login_view is not None:
            login_view.feedback.value = message
            login_view.feedback.color = ft.Colors.RED_700
            update_control(login_view)

    def on_line_authorized(data: ft.LoginEvent) -> None:
        if data.error:
            _set_login_feedback("เข้าสู่ระบบด้วย LINE ไม่สำเร็จ กรุณาลองใหม่อีกครั้ง")
            return
        authorization = page.auth
        profile = (
            getattr(authorization, "user", None)
            if authorization is not None
            else None
        )
        if profile is None:
            _set_login_feedback("ไม่สามารถดึงข้อมูลผู้ใช้ LINE ได้ กรุณาลองใหม่อีกครั้ง")
            return
        display_name = profile.get("displayName") or "ผู้ใช้ LINE"
        handle_login_success(register_or_fetch_user(auth, profile.id, display_name))

    def start_line_login() -> None:
        provider = get_line_provider()
        if provider is None:
            _set_login_feedback("ยังไม่ได้ตั้งค่า LINE Login (ตรวจสอบการตั้งค่าระบบ)")
            return
        page.on_login = on_line_authorized
        page.run_task(page.login, provider)

    def show_login() -> None:
        nonlocal login_view
        try:
            page.session.store.remove("user_id")
        except Exception:
            pass
        try:
            from app.views.login import LoginView
        except ImportError:
            login_view = None
            root.content = ft.Container(
                expand=True,
                alignment=ft.Alignment.CENTER,
                content=ft.Text("กำลังโหลดหน้าเข้าสู่ระบบ..."),
            )
        else:
            login_view = LoginView(
                auth,
                on_success=handle_login_success,
                on_line_login=start_line_login,
            )
            root.content = ft.Container(expand=True, content=login_view)
        page.on_resize = lambda _: None

    def show_shell(user: AppUser) -> None:
        shell = build_app_shell(
            services,
            width=page.width,
            current_user=user,
            on_logout=show_login,
        )
        root.content = shell
        apply_shell_width(shell, page.width)
        page.on_resize = lambda _: apply_shell_width(shell, page.width)

    def handle_login_success(user: AppUser) -> None:
        page.session.store.set("user_id", user.id)
        if not user.must_change_password:
            show_shell(user)
            return
        try:
            from app.views.change_password import ChangePasswordView
        except ImportError:
            show_shell(user)
        else:
            root.content = ft.Container(
                expand=True,
                content=ChangePasswordView(
                    auth,
                    user,
                    on_done=lambda: show_shell(auth.get(user.id) or user),
                    on_cancel=None,
                ),
            )
            page.on_resize = lambda _: None

    uid = page.session.store.get("user_id")
    user = auth.get(uid) if uid else None
    if user is not None:
        show_shell(user)
    else:
        show_login()


if __name__ == "__main__":
    ft.run(main)
