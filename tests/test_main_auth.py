from datetime import datetime, timezone

from app.contracts import AppUser, Permission, RecordStatus, Role
from app.views.history import HistoryView
from app.views.inventory import InventoryView
from app.views.my_loans import MyLoansView
from main import build_app_shell
from tests.test_auth_fixtures import admin_user, borrower_user


def _shell_menu(shell):
    sidebar = shell.content.controls[0].controls[0]
    return sidebar.content.controls[1]


def _shell_content_area(shell):
    return shell.content.controls[0].controls[2]


def test_borrower_shell_shows_only_permitted_menu_items() -> None:
    shell = build_app_shell(current_user=borrower_user())

    labels = [tile.title.value for tile in _shell_menu(shell).controls]
    assert labels == ["อุปกรณ์", "ของฉัน", "ประวัติ"]

    assert isinstance(_shell_content_area(shell).content.content, InventoryView)


def test_admin_shell_shows_all_seven_menu_items() -> None:
    shell = build_app_shell(current_user=admin_user())

    assert len(_shell_menu(shell).controls) == 7


def test_shell_without_user_keeps_legacy_full_menu() -> None:
    shell = build_app_shell()

    assert len(_shell_menu(shell).controls) == 7


def test_admin_can_navigate_between_tiles() -> None:
    shell = build_app_shell(current_user=admin_user())
    navigation_menu = _shell_menu(shell)
    content_area = _shell_content_area(shell)

    navigation_menu.controls[1].on_click(None)

    assert isinstance(content_area.content.content, InventoryView)
    assert navigation_menu.controls[1].selected is True
    assert navigation_menu.controls[0].selected is False


def test_borrower_can_navigate_permitted_tiles() -> None:
    shell = build_app_shell(current_user=borrower_user())
    navigation_menu = _shell_menu(shell)
    content_area = _shell_content_area(shell)

    navigation_menu.controls[1].on_click(None)

    assert isinstance(content_area.content.content, MyLoansView)
    assert shell._nav_feedback.value == ""

    navigation_menu.controls[2].on_click(None)

    assert isinstance(content_area.content.content, HistoryView)
    assert shell._nav_feedback.value == ""


def test_my_loans_guard_blocks_user_without_linked_borrower() -> None:
    unlinked_user = AppUser(
        id=3,
        role=Role.USER,
        display_name="ผู้ใช้ที่ไม่มีข้อมูลผู้ยืม",
        email="ghost@lab.local",
        staff_id=None,
        borrower_id=None,
        status=RecordStatus.ACTIVE,
        must_change_password=False,
        last_login_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
    )
    shell = build_app_shell(current_user=unlinked_user)
    content_area = _shell_content_area(shell)
    before = content_area.content

    shell.navigate_to(
        {"label": "ของฉัน", "route": "my_loans", "permission": Permission.VIEW_MY_LOANS}
    )

    assert shell._nav_feedback.value == "ไม่พบข้อมูลผู้ยืมที่เชื่อมโยงกับบัญชีนี้"
    assert content_area.content is before


def test_navigate_to_guard_blocks_forbidden_route_for_borrower() -> None:
    shell = build_app_shell(current_user=borrower_user())
    content_area = _shell_content_area(shell)
    before = content_area.content

    forged_item = {"permission": Permission.MANAGE_LOANS, "route": "returns"}
    shell.navigate_to(forged_item)

    assert shell._nav_feedback.value == "คุณไม่มีสิทธิ์เข้าถึงหน้านี้"
    assert content_area.content is before


def test_borrower_mobile_navigation_has_only_permitted_destinations() -> None:
    shell = build_app_shell(width=430, current_user=borrower_user())

    mobile_navigation = shell.content.controls[1]
    assert len(mobile_navigation.destinations) == 3
    assert [d.label for d in mobile_navigation.destinations] == ["อุปกรณ์", "ของฉัน", "ประวัติ"]
