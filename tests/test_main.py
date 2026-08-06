import flet as ft

from main import APP_TITLE, build_home


def test_build_home_returns_safe_area() -> None:
    home = build_home()

    assert isinstance(home, ft.SafeArea)
    assert home.expand is True


def test_app_title_is_defined() -> None:
    assert APP_TITLE == "Lab Equipment Borrowing"
