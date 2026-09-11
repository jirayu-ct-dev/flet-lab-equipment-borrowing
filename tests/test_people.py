import flet as ft

from app.contracts import CreateUserCommand, RecordStatus, RegisterLineUser, Role
from app.services.fake_services import FakeAuthService, FakeInventoryService
from app.views.people import PeopleDirectoryView
from tests.test_auth_fixtures import admin_user


def _view() -> PeopleDirectoryView:
    return PeopleDirectoryView(
        FakeInventoryService(),
        current_user=admin_user(),
        auth_service=FakeAuthService(),
    )


def test_people_directory_combines_profiles_and_unlinked_accounts() -> None:
    view = _view()
    table = view.people_container.content.content.controls[0]

    assert isinstance(table, ft.DataTable)
    assert len(table.rows) == len(view._rows())
    assert any(row.kind == "account" for row in view._rows())
    assert any(cell.content.value == "ยังไม่มีบัญชี" for row in table.rows for cell in row.cells)


def test_people_directory_filters_by_type_and_unlinked_status() -> None:
    view = _view()

    view.kind_filter.value = "borrower"
    view._handle_filter(None)
    assert all(row.kind == "borrower" for row in view._filtered_rows())

    view.kind_filter.value = "all"
    view.status_filter.value = "unlinked"
    view._handle_filter(None)
    assert all(row.account is None for row in view._filtered_rows())


def test_people_directory_renders_cards_on_mobile() -> None:
    view = PeopleDirectoryView(
        FakeInventoryService(),
        mobile=True,
        current_user=admin_user(),
        auth_service=FakeAuthService(),
    )

    assert isinstance(view.people_container.content, ft.Column)
    assert all(isinstance(card, ft.Container) for card in view.people_container.content.controls)


def test_adding_person_links_existing_account_with_same_email() -> None:
    auth = FakeAuthService()
    auth.create_user(
        CreateUserCommand(role=Role.USER, display_name="บัญชีใหม่", email="new@example.com"),
        actor=admin_user(),
    )
    view = PeopleDirectoryView(
        FakeInventoryService(), current_user=admin_user(), auth_service=auth
    )

    view._open_new_profile(None)
    view.profile_name.value = "คนใหม่"
    view.profile_email.value = "new@example.com"
    view._save_profile(None)

    account = next(user for user in auth.list_users() if user.email == "new@example.com")
    assert account.borrower_id == 3


def test_account_editor_can_link_staff_and_change_status() -> None:
    auth = FakeAuthService()
    account = auth.register_line_user(RegisterLineUser(line_sub="line-1", display_name="LINE คนใหม่"))
    view = PeopleDirectoryView(
        FakeInventoryService(), current_user=admin_user(), auth_service=auth
    )

    view._open_account(account)
    view.account_staff.value = "1"
    view.account_status.value = RecordStatus.INACTIVE.value
    view._save_account(None)

    updated = auth.get(account.id)
    assert updated.staff_id == 1
    assert updated.status is RecordStatus.INACTIVE


def test_account_editor_rejects_weak_reset_password() -> None:
    auth = FakeAuthService()
    account = auth.register_line_user(RegisterLineUser(line_sub="line-2", display_name="LINE คนใหม่"))
    view = PeopleDirectoryView(
        FakeInventoryService(), current_user=admin_user(), auth_service=auth
    )

    view._open_account(account)
    view.account_password.value = "short"
    view._save_account(None)

    assert "อย่างน้อย" in view.feedback.value
    assert view.account_dialog.open is True


def test_account_editor_cannot_disable_current_admin() -> None:
    view = _view()

    view._open_account(view.auth_service.get(1))
    view.account_status.value = RecordStatus.INACTIVE.value
    view._save_account(None)

    assert "ตัวเอง" in view.feedback.value
