from datetime import datetime, timezone

import flet as ft

from app.contracts import AppUser, Permission, RecordStatus, Role, has_permission
from app.services.fake_services import FakeInventoryService
from app.views.rebuild import (
    HistoryWorkspaceView,
    InventoryWorkspaceView,
    QuickBorrowView,
    QuickReturnView,
    WorkspaceView,
)
from main import build_app_shell
from tests.test_auth_fixtures import admin_user


def test_workspace_prioritizes_the_return_queue() -> None:
    view = WorkspaceView(FakeInventoryService(), current_user=admin_user())

    assert any(
        isinstance(control, type(view.queue_container))
        for control in view.content.controls
    )
    assert len(view.metric_row.controls) == 4
    assert view.queue_container.content is not None


def test_app_shell_wires_the_rebuilt_views() -> None:
    shell = build_app_shell(current_user=admin_user())
    navigation = shell.content.controls[0].controls[0].content.controls[1]
    content_area = shell.content.controls[0].controls[2]

    assert isinstance(content_area.content.content, WorkspaceView)

    navigation.controls[1].on_click(None)
    assert isinstance(content_area.content.content, InventoryWorkspaceView)

    navigation.controls[2].on_click(None)
    assert isinstance(content_area.content.content, QuickBorrowView)

    navigation.controls[4].on_click(None)
    assert isinstance(content_area.content.content, QuickReturnView)


def test_quick_borrow_supports_multiple_units_in_one_transaction() -> None:
    service = FakeInventoryService()
    service.create_unit(asset_code="AST-006", equipment_id="eq-1", location="Lab A")
    view = QuickBorrowView(service, current_user=admin_user())

    view._select_borrower("BR-001")
    view._toggle_unit("unit-1")
    view._toggle_unit("unit-6")
    view._handle_borrow(None)

    assert "เรียบร้อยแล้ว" in view.feedback.value
    assert service.get_unit_by_id("unit-1").status == "borrowed"
    assert service.get_unit_by_id("unit-6").status == "borrowed"
    created = service.list_loans()[-1]
    assert created.unit_ids == ["unit-1", "unit-6"]


def test_quick_return_preselects_every_outstanding_unit() -> None:
    service = FakeInventoryService()
    view = QuickReturnView(service, current_user=admin_user())
    loan = service.get_loan("loan-1")

    view._select_loan(loan)

    assert view.selected_unit_ids == ["unit-2"]
    assert isinstance(view.detail_container.content, ft.Container)
    assert isinstance(view.detail_container.content.content, ft.Column)


def test_staff_linked_user_can_operate_without_being_admin() -> None:
    staff_user = AppUser(
        id=10,
        role=Role.USER,
        display_name="เจ้าหน้าที่ทดลอง",
        email="staff@example.com",
        staff_id=1,
        borrower_id=None,
        status=RecordStatus.ACTIVE,
        must_change_password=False,
        last_login_at=datetime.now(timezone.utc),
    )

    assert has_permission(staff_user, Permission.MANAGE_LOANS) is True
    assert has_permission(staff_user, Permission.MANAGE_USERS) is False


def test_history_search_uses_one_or_query_across_event_fields() -> None:
    view = HistoryWorkspaceView(FakeInventoryService())

    view.search_field.value = "ST-001"
    view._render()

    history = view.history_container.content
    assert isinstance(history, ft.Column)
    assert history.controls
