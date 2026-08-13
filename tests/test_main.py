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


def test_navigation_items_include_expected_sections() -> None:
    items = get_navigation_items()
    labels = [item["label"] for item in items]

    assert labels[0] == "Inventory"
    assert "Loans" in labels
    assert "Lost cases" in labels
    assert "History" in labels


def test_build_app_shell_switches_content_on_navigation_change() -> None:
    shell = build_app_shell()
    row = shell.content.controls[0]
    nav = row.controls[0].content
    content_area = row.controls[2]

    nav.selected_index = 1
    nav.on_change(type("Event", (), {"control": nav})())

    assert isinstance(content_area.content.content, StaffBorrowersView)


def test_app_shell_switches_to_mobile_navigation() -> None:
    shell = build_app_shell()
    row, mobile_navigation = shell.content.controls

    apply_shell_width(shell, 430)

    assert row.controls[0].visible is False
    assert mobile_navigation.visible is True

    apply_shell_width(shell, 1440)
    assert row.controls[0].visible is True
    assert mobile_navigation.visible is False


def test_state_view_renders_title_and_message() -> None:
    view = build_state_view("Loading", "Preparing data...")

    assert isinstance(view, ft.Container)
    assert view.content is not None


def test_app_title_is_defined() -> None:
    assert APP_TITLE == "Lab Equipment Borrowing"
