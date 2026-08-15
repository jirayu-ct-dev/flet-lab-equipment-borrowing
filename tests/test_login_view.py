import flet as ft

from app.contracts import LoginCommand, RecordStatus, Role
from app.services.fake_services import FakeAuthService
from app.views.login import LoginView


class SpyAuthService:
    def __init__(self) -> None:
        self.inner = FakeAuthService()
        self.authenticate_calls: list[LoginCommand] = []

    def authenticate(self, command: LoginCommand):
        self.authenticate_calls.append(command)
        return self.inner.authenticate(command)


def build_login_view(
    *, auth: FakeAuthService | SpyAuthService | None = None, on_line_login=None
):
    successes = []
    view = LoginView(
        auth or FakeAuthService(),
        on_success=lambda user: successes.append(user),
        on_line_login=on_line_login,
    )
    return view, successes


def test_login_view_structure() -> None:
    view, _ = build_login_view(on_line_login=lambda: None)

    assert isinstance(view, ft.Container)
    assert view.expand is True
    assert view.padding == 0
    assert isinstance(view.email_field, ft.TextField)
    assert view.email_field.height == 52
    assert view.email_field.border_radius == 12
    assert view.email_field.autofocus is True
    assert isinstance(view.password_field, ft.TextField)
    assert view.password_field.password is True
    assert view.password_field.can_reveal_password is True
    assert view.password_field.height == 52
    assert view.password_field.border_radius == 12
    assert isinstance(view.feedback, ft.Text)
    assert view.feedback.size == 13
    assert isinstance(view.login_button, ft.FilledButton)
    assert view.login_button.height == 52
    assert view.login_button.style.shape.radius == 12
    assert isinstance(view.line_button, ft.FilledButton)
    assert view.line_button.height == 52
    assert view.line_button.bgcolor == "#06C755"
    assert view.line_button.width == float("inf")
    card_column = view.content.content
    assert card_column.controls[1] is view.line_button
    divider = card_column.controls[2]
    assert isinstance(divider, ft.Row)
    assert any(
        isinstance(child, ft.Text) and child.value == "หรือ" for child in divider.controls
    )


def test_login_wrong_password_shows_error_and_blocks_success() -> None:
    view, successes = build_login_view()
    view.email_field.value = "admin@lab.local"
    view.password_field.value = "not-the-password"

    view._handle_login(None)

    assert view.feedback.value == "อีเมลหรือรหัสผ่านไม่ถูกต้อง"
    assert view.feedback.color == ft.Colors.RED_700
    assert successes == []


def test_login_unknown_email_shows_same_error() -> None:
    view, successes = build_login_view()
    view.email_field.value = "ghost@lab.local"
    view.password_field.value = "whatever123"

    view._handle_login(None)

    assert view.feedback.value == "อีเมลหรือรหัสผ่านไม่ถูกต้อง"
    assert successes == []


def test_login_empty_fields_show_validation_without_authenticate() -> None:
    spy = SpyAuthService()
    view, successes = build_login_view(auth=spy)
    view.email_field.value = "   "
    view.password_field.value = ""

    view._handle_login(None)

    assert view.feedback.value == "กรุณากรอกอีเมลและรหัสผ่าน"
    assert view.feedback.color == ft.Colors.RED_700
    assert spy.authenticate_calls == []
    assert successes == []


def test_login_success_is_case_insensitive_and_returns_admin() -> None:
    view, successes = build_login_view()
    view.email_field.value = "  ADMIN@LAB.LOCAL "
    view.password_field.value = "admin123"

    view._handle_login(None)

    assert len(successes) == 1
    assert successes[0].role is Role.ADMIN
    assert view.feedback.value == ""


def test_login_inactive_user_gets_inactive_message() -> None:
    auth = FakeAuthService()
    admin = auth.authenticate(LoginCommand("admin@lab.local", "admin123"))
    auth.set_user_status(2, RecordStatus.INACTIVE, actor=admin)
    view, successes = build_login_view(auth=auth)
    view.email_field.value = "borrower@lab.local"
    view.password_field.value = "borrow123"

    view._handle_login(None)

    assert view.feedback.value == "บัญชีถูกปิดใช้งาน กรุณาติดต่อผู้ดูแลระบบ"
    assert successes == []


def test_login_line_button_present_when_callback_provided() -> None:
    line_calls = []
    view, _ = build_login_view(on_line_login=lambda: line_calls.append(True))

    assert isinstance(view.line_button, ft.FilledButton)
    assert view.line_button.bgcolor == "#06C755"
    content_row = view.line_button.content
    assert isinstance(content_row, ft.Row)
    assert content_row.spacing == 8
    logo = content_row.controls[0]
    assert isinstance(logo, ft.Container)
    assert logo.width == 24
    assert logo.height == 24
    assert logo.border_radius == 6
    assert logo.expand is None
    view.line_button.on_click(None)

    assert line_calls == [True]


def test_login_line_button_absent_without_callback() -> None:
    view, _ = build_login_view()

    assert view.line_button is None
