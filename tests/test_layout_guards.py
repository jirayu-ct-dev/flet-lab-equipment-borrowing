import dataclasses

import flet as ft

from app.services.fake_services import FakeInventoryService
from app.views.borrow_flow import BorrowFlowView
from app.views.dashboard import DashboardView
from app.views.history import build_history_view
from app.views.inventory import build_inventory_view
from app.views.loans import LoansView
from app.views.staff_borrowers import StaffBorrowersView
from main import apply_shell_width, build_app_shell

_SKIP_FIELDS = {"_values", "_dirty", "_i", "_c", "_internals"}


def iter_controls(root: ft.Control):
    stack = [root]
    while stack:
        ctrl = stack.pop()
        yield ctrl
        for field in dataclasses.fields(ctrl):
            if field.name in _SKIP_FIELDS:
                continue
            value = getattr(ctrl, field.name, None)
            items = value if isinstance(value, (list, tuple)) else [value]
            for item in items:
                if isinstance(item, ft.Control):
                    stack.append(item)


def build_views(service: FakeInventoryService, *, mobile: bool) -> list[ft.Control]:
    return [
        DashboardView(service, mobile=mobile),
        build_inventory_view(service, mobile=mobile),
        StaffBorrowersView(service, mobile=mobile),
        LoansView(service, mobile=mobile),
        build_history_view(service, mobile=mobile),
    ]


def assert_no_layout_killers(root: ft.Control) -> None:
    controls = list(iter_controls(root))
    # flet 0.86 renderer bug: expand=False corrupts the whole Row/ResponsiveRow.
    bad_expand = [c for c in controls if getattr(c, "expand", None) is False]
    assert not bad_expand, f"expand=False found (use expand=None): {[type(c).__name__ for c in bad_expand]}"
    # Non-flex child with width=inf inside a Row claims the full row and overlaps siblings.
    for control in controls:
        if isinstance(control, ft.Row) and not control.wrap:
            for child in control.controls:
                assert not (
                    getattr(child, "width", None) == float("inf")
                    and not getattr(child, "expand", None)
                ), f"width=inf non-flex child inside Row: {type(child).__name__}"


def test_views_avoid_expand_false_and_inf_width_in_rows() -> None:
    service = FakeInventoryService()
    for mobile in (False, True):
        for view in build_views(service, mobile=mobile):
            assert_no_layout_killers(view)
    assert_no_layout_killers(BorrowFlowView(service))


def test_app_shell_avoids_layout_killers_in_both_modes() -> None:
    service = FakeInventoryService()
    for width in (430, 1440):
        shell = build_app_shell(service, width=width)
        apply_shell_width(shell, width)
        assert_no_layout_killers(shell)


def test_navigation_builds_views_with_current_window_mode() -> None:
    shell = build_app_shell()
    row, _mobile_navigation = shell.content.controls
    content_area = row.controls[2]
    inventory_tile = row.controls[0].content.controls[1].controls[1]

    apply_shell_width(shell, 430)
    inventory_tile.on_click(None)
    assert content_area.content.content.mobile is True

    apply_shell_width(shell, 1440)
    inventory_tile.on_click(None)
    assert content_area.content.content.mobile is False
