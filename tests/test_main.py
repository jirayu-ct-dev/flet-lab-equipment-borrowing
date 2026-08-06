import flet as ft

from main import APP_TITLE, build_app_shell, build_home, get_navigation_items
from app.components.common import build_state_view


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
    assert "History" in labels


def test_state_view_renders_title_and_message() -> None:
    view = build_state_view("Loading", "Preparing data...")

    assert isinstance(view, ft.Container)
    assert view.content is not None


def test_app_title_is_defined() -> None:
    assert APP_TITLE == "Lab Equipment Borrowing"
