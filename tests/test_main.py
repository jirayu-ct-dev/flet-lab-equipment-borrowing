import flet as ft

from main import APP_TITLE, apply_shell_width, build_app_shell, build_home, get_navigation_items
from app.components.common import build_state_view
from app.views.staff_borrowers import StaffBorrowersView


def test_build_home_returns_safe_area() -> None:
    home = build_home()

    assert isinstance(home, ft.SafeArea)
    assert home.expand is True


def test_build_app_shell_returns_container() -> None:
    shell = build_app_shell()

    assert isinstance(shell, ft.Container)


def test_app_shell_builds_views_in_mobile_mode_from_width() -> None:
    mobile_shell = build_app_shell(width=430)
    mobile_dashboard = mobile_shell.content.controls[0].controls[2].content.content
    assert mobile_dashboard.mobile is True

    desktop_shell = build_app_shell(width=1440)
    desktop_dashboard = desktop_shell.content.controls[0].controls[2].content.content
    assert desktop_dashboard.mobile is False


def test_desktop_navigation_uses_horizontal_icon_and_label_layout() -> None:
    shell = build_app_shell()
    sidebar_content = shell.content.controls[0].controls[0].content
    navigation_menu = sidebar_content.controls[1]
    first_item = navigation_menu.controls[0]

    assert isinstance(first_item, ft.ListTile)
    assert isinstance(first_item.leading, ft.Icon)
    assert isinstance(first_item.title, ft.Text)
    assert first_item.horizontal_spacing == 12
    assert first_item.selected is True


def test_navigation_items_include_expected_sections() -> None:
    items = get_navigation_items()
    labels = [item["label"] for item in items]

    assert labels == ["Dashboard", "อุปกรณ์", "คนในระบบ", "ทำรายการยืม", "คืนอุปกรณ์", "ประวัติ"]


def test_build_app_shell_switches_content_on_navigation_change() -> None:
    shell = build_app_shell()
    row = shell.content.controls[0]
    navigation_menu = row.controls[0].content.controls[1]
    content_area = row.controls[2]

    navigation_menu.controls[2].on_click(None)

    assert isinstance(content_area.content.content, StaffBorrowersView)
    assert navigation_menu.controls[2].selected is True
    assert navigation_menu.controls[0].selected is False


def test_app_shell_switches_to_mobile_navigation() -> None:
    shell = build_app_shell()
    row, mobile_navigation = shell.content.controls

    apply_shell_width(shell, 430)

    assert row.controls[0].visible is False
    assert mobile_navigation.visible is True
    assert row.controls[2].content.padding == 20

    apply_shell_width(shell, 1440)
    assert row.controls[0].visible is True
    assert mobile_navigation.visible is False
    assert row.controls[2].content.padding == 32


def test_state_view_renders_title_and_message() -> None:
    view = build_state_view("Loading", "Preparing data...")

    assert isinstance(view, ft.Container)
    assert view.content is not None


def test_app_title_is_defined() -> None:
    assert APP_TITLE == "ระบบยืม–คืนอุปกรณ์"
