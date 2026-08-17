import pytest

from app.contracts import (
    AppUser,
    AuthService,
    ChangePasswordCommand,
    CreateUserCommand,
    LoginCommand,
    Permission,
    RecordStatus,
    RegisterLineUser,
    Role,
    has_permission,
)
from app.errors import (
    AuthenticationError,
    DuplicateCodeError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from app.services.fake_services import FakeAuthService


@pytest.fixture
def service() -> FakeAuthService:
    return FakeAuthService()


def _admin(service: FakeAuthService) -> AppUser:
    return service.authenticate(LoginCommand("admin@lab.local", "admin123"))


def _borrower(service: FakeAuthService) -> AppUser:
    return service.authenticate(LoginCommand("borrower@lab.local", "borrow123"))


def test_fake_auth_service_satisfies_protocol() -> None:
    assert isinstance(FakeAuthService(), AuthService)


def test_authenticate_success_is_case_insensitive_and_updates_last_login(service) -> None:
    user = service.authenticate(LoginCommand("  Borrower@LAB.Local ", "borrow123"))

    assert user.role is Role.USER
    assert user.display_name == "ผู้ยืมทดสอบ"
    assert user.must_change_password is False
    assert user.last_login_at is not None
    assert service.get(user.id).last_login_at == user.last_login_at


def test_authenticate_rejects_wrong_password(service) -> None:
    with pytest.raises(AuthenticationError):
        service.authenticate(LoginCommand("admin@lab.local", "not-the-password"))


def test_authenticate_rejects_unknown_email(service) -> None:
    with pytest.raises(AuthenticationError):
        service.authenticate(LoginCommand("ghost@lab.local", "whatever123"))


def test_authenticate_rejects_inactive_user(service) -> None:
    admin = _admin(service)
    service.set_user_status(2, RecordStatus.INACTIVE, actor=admin)

    with pytest.raises(AuthenticationError):
        service.authenticate(LoginCommand("borrower@lab.local", "borrow123"))


def test_permission_matrix(service) -> None:
    admin = _admin(service)
    borrower = _borrower(service)

    assert has_permission(None, Permission.VIEW_INVENTORY) is False
    for permission in Permission:
        assert has_permission(admin, permission) is True
    assert has_permission(borrower, Permission.VIEW_INVENTORY) is True
    assert has_permission(borrower, Permission.VIEW_HISTORY) is True
    assert has_permission(borrower, Permission.VIEW_MY_LOANS) is True
    assert has_permission(borrower, Permission.VIEW_DASHBOARD) is False
    assert has_permission(borrower, Permission.MANAGE_LOANS) is False
    assert has_permission(borrower, Permission.MANAGE_USERS) is False


def test_create_user_requires_admin_actor(service) -> None:
    borrower = _borrower(service)

    with pytest.raises(PermissionDenied):
        service.create_user(
            CreateUserCommand(
                role=Role.USER, display_name="คนใหม่", email="new@lab.local",
                password="newpassword1",
            ),
            actor=borrower,
        )


def test_create_user_with_and_without_password(service) -> None:
    admin = _admin(service)
    created = service.create_user(
        CreateUserCommand(
            role=Role.USER, display_name="คนใหม่", email="new@lab.local",
            password="newpassword1",
        ),
        actor=admin,
    )
    assert created.role is Role.USER
    assert created.must_change_password is False
    assert service.authenticate(LoginCommand("new@lab.local", "newpassword1")).id == created.id

    no_password = service.create_user(
        CreateUserCommand(
            role=Role.USER, display_name="ยังไม่มีรหัส", email="pwless@lab.local"
        ),
        actor=admin,
    )
    assert no_password.must_change_password is True


def test_create_user_rejects_duplicate_email(service) -> None:
    admin = _admin(service)

    with pytest.raises(DuplicateCodeError):
        service.create_user(
            CreateUserCommand(
                role=Role.USER, display_name="ซ้ำ", email="ADMIN@LAB.LOCAL"
            ),
            actor=admin,
        )


def test_set_user_status_requires_admin_and_updates(service) -> None:
    borrower = _borrower(service)
    with pytest.raises(PermissionDenied):
        service.set_user_status(1, RecordStatus.INACTIVE, actor=borrower)

    admin = _admin(service)
    service.set_user_status(2, RecordStatus.INACTIVE, actor=admin)
    assert service.get(2).status is RecordStatus.INACTIVE

    with pytest.raises(NotFoundError):
        service.set_user_status(999, RecordStatus.ACTIVE, actor=admin)


def test_change_password_flow(service) -> None:
    admin = _admin(service)
    assert admin.must_change_password is True

    with pytest.raises(AuthenticationError):
        service.change_password(1, ChangePasswordCommand("wrong", "new-password-123"))
    with pytest.raises(NotFoundError):
        service.change_password(999, ChangePasswordCommand("admin123", "new-password-123"))

    service.change_password(1, ChangePasswordCommand("admin123", "new-password-123"))
    assert service.get(1).must_change_password is False
    service.authenticate(LoginCommand("admin@lab.local", "new-password-123"))
    with pytest.raises(AuthenticationError):
        service.authenticate(LoginCommand("admin@lab.local", "admin123"))


def test_change_password_enforces_minimum_length(service) -> None:
    _admin(service)

    with pytest.raises(ValidationError):
        service.change_password(1, ChangePasswordCommand("admin123", "short"))


def test_admin_reset_password_requires_admin(service) -> None:
    borrower = _borrower(service)
    with pytest.raises(PermissionDenied):
        service.admin_reset_password(2, "reset-password-1", actor=borrower)

    admin = _admin(service)
    service.admin_reset_password(2, "reset-password-1", actor=admin)
    assert service.get(2).must_change_password is True
    service.authenticate(LoginCommand("borrower@lab.local", "reset-password-1"))


def test_register_line_user_creates_once_and_duplicate_raises(service) -> None:
    command = RegisterLineUser(
        line_sub="line-sub-1", display_name="ผู้ใช้ไลน์", email="line@lab.local"
    )
    created = service.register_line_user(command)

    assert created.role is Role.USER
    assert created.borrower_id is None
    assert service.find_by_line_sub("line-sub-1").id == created.id
    assert service.get(created.id).id == created.id

    with pytest.raises(DuplicateCodeError):
        service.register_line_user(command)


def test_list_users_exposes_all_users(service) -> None:
    users = service.list_users()

    assert len(users) == 2
    assert {user.email for user in users} == {
        "admin@lab.local",
        "borrower@lab.local",
    }


def test_set_user_role_updates_role(service) -> None:
    admin = _admin(service)

    updated = service.set_user_role(2, Role.ADMIN, actor=admin)

    assert updated.id == 2
    assert updated.role is Role.ADMIN
    assert service.get(2).role is Role.ADMIN


def test_set_user_role_requires_manage_users(service) -> None:
    borrower = _borrower(service)

    with pytest.raises(PermissionDenied):
        service.set_user_role(2, Role.ADMIN, actor=borrower)


def test_set_user_role_unknown_user(service) -> None:
    admin = _admin(service)

    with pytest.raises(NotFoundError):
        service.set_user_role(999, Role.ADMIN, actor=admin)


def test_set_user_borrower_links_line_user(service) -> None:
    admin = _admin(service)
    line_user = service.register_line_user(
        RegisterLineUser(line_sub="line-sub-link", display_name="ผู้ใช้ไลน์ผูก")
    )
    assert line_user.borrower_id is None

    updated = service.set_user_borrower(line_user.id, 3, actor=admin)

    assert updated.borrower_id == 3
    assert service.get(line_user.id).borrower_id == 3


def test_set_user_borrower_requires_manage_people(service) -> None:
    borrower = _borrower(service)
    line_user = service.register_line_user(
        RegisterLineUser(line_sub="line-sub-no-perm", display_name="ผู้ใช้ไลน์")
    )

    with pytest.raises(PermissionDenied):
        service.set_user_borrower(line_user.id, 3, actor=borrower)


def test_set_user_borrower_unknown_user(service) -> None:
    admin = _admin(service)

    with pytest.raises(NotFoundError):
        service.set_user_borrower(999, 3, actor=admin)
