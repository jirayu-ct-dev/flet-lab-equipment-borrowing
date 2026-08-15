import flet as ft
import pytest

from app.contracts import LoginCommand, Role
from app.errors import AuthenticationError
from app.services.fake_services import FakeAuthService
from app.views.change_password import ChangePasswordView
from tests.test_auth_fixtures import admin_user


def build_change_password_view(*, on_cancel=None):
    auth = FakeAuthService()
    done_calls = []
    cancel_calls = []
    view = ChangePasswordView(
        auth,
        admin_user(),
        on_done=lambda: done_calls.append(True),
        on_cancel=(lambda: cancel_calls.append(True)) if on_cancel is not None else None,
    )
    return view, auth, done_calls, cancel_calls


def fill(view, *, current="admin123", new="", confirm="") -> None:
    view.current_password_field.value = current
    view.new_password_field.value = new
    view.confirm_password_field.value = confirm


def test_change_password_view_structure() -> None:
    view, _, _, _ = build_change_password_view()

    assert isinstance(view, ft.Container)
    assert view.expand is True
    assert view.padding == 0
    header = view.content.content.controls[0]
    assert header.content.controls[1].controls[0].value == "เปลี่ยนรหัสผ่าน"
    assert header.content.controls[1].controls[1].value == f"บัญชี: {admin_user().display_name}"
    for field in (
        view.current_password_field,
        view.new_password_field,
        view.confirm_password_field,
    ):
        assert isinstance(field, ft.TextField)
        assert field.password is True
        assert field.can_reveal_password is True
        assert field.height == 52
        assert field.border_radius == 12
    assert isinstance(view.feedback, ft.Text)
    assert view.feedback.size == 13
    assert isinstance(view.submit_button, ft.FilledButton)
    assert view.submit_button.height == 52
    assert view.submit_button.style.shape.radius == 12


def test_change_password_mismatch_confirm_shows_message_and_keeps_password() -> None:
    view, auth, done_calls, _ = build_change_password_view()
    fill(view, new="new-password-1", confirm="different-123")

    view._handle_submit(None)

    assert view.feedback.value == "รหัสผ่านใหม่ไม่ตรงกัน"
    assert view.feedback.color == ft.Colors.RED_700
    assert done_calls == []
    auth.authenticate(LoginCommand("admin@lab.local", "admin123"))
    with pytest.raises(AuthenticationError):
        auth.authenticate(LoginCommand("admin@lab.local", "new-password-1"))


def test_change_password_weak_new_password_shows_strength_message() -> None:
    view, auth, done_calls, _ = build_change_password_view()
    fill(view, new="short", confirm="short")

    view._handle_submit(None)

    assert view.feedback.value == "รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร"
    assert done_calls == []
    auth.authenticate(LoginCommand("admin@lab.local", "admin123"))


def test_change_password_wrong_current_password_shows_error() -> None:
    view, auth, done_calls, _ = build_change_password_view()
    fill(view, current="not-current", new="new-password-1", confirm="new-password-1")

    view._handle_submit(None)

    assert view.feedback.value == "รหัสผ่านปัจจุบันไม่ถูกต้อง"
    assert done_calls == []
    auth.authenticate(LoginCommand("admin@lab.local", "admin123"))
    with pytest.raises(AuthenticationError):
        auth.authenticate(LoginCommand("admin@lab.local", "new-password-1"))


def test_change_password_success_calls_on_done_and_updates_password() -> None:
    view, auth, done_calls, _ = build_change_password_view()
    fill(view, current="admin123", new="new-password-1", confirm="new-password-1")

    view._handle_submit(None)

    assert done_calls == [True]
    assert view.feedback.value == ""
    with pytest.raises(AuthenticationError):
        auth.authenticate(LoginCommand("admin@lab.local", "admin123"))
    user = auth.authenticate(LoginCommand("admin@lab.local", "new-password-1"))
    assert user.role is Role.ADMIN


def test_change_password_cancel_button_absent_without_callback() -> None:
    view, _, _, _ = build_change_password_view()

    assert view.cancel_button is None


def test_change_password_cancel_button_present_and_invokes_callback() -> None:
    view, _, _, cancel_calls = build_change_password_view(on_cancel=True)

    assert isinstance(view.cancel_button, ft.OutlinedButton)
    assert view.cancel_button.height == 52
    view.cancel_button.on_click(None)

    assert cancel_calls == [True]
