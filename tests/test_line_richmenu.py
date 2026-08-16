import pytest

from app.line_richmenu import get_richmenu_for_user
from app.services import line_messaging
from app.services.line_messaging import LineMessagingService, sync_richmenu
from tests.test_auth_fixtures import admin_user, borrower_user


@pytest.fixture(autouse=True)
def _clear_richmenu_env(monkeypatch) -> None:
    for name in (
        "LINE_MESSAGING_CHANNEL_ACCESS_TOKEN",
        "LINE_RICHMENU_ADMIN_ID",
        "LINE_RICHMENU_USER_ID",
    ):
        monkeypatch.delenv(name, raising=False)


class _FakeResponse:
    def __init__(self, body: bytes = b"{}") -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _Recorder:
    def __init__(self) -> None:
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        return _FakeResponse()


@pytest.fixture
def recorder(monkeypatch) -> _Recorder:
    rec = _Recorder()
    monkeypatch.setattr(line_messaging, "urlopen", rec)
    return rec


class _StubService:
    def __init__(self, *, configured: bool = True, error: Exception | None = None):
        self.configured = configured
        self.error = error
        self.linked: list[tuple[str, str]] = []

    def is_configured(self) -> bool:
        return self.configured

    def link_richmenu_to_user(self, line_user_id: str, richmenu_id: str) -> None:
        if self.error is not None:
            raise self.error
        self.linked.append((line_user_id, richmenu_id))


def test_get_richmenu_for_user_none_without_user() -> None:
    assert get_richmenu_for_user(None) is None


def test_get_richmenu_for_user_picks_admin_menu(monkeypatch) -> None:
    monkeypatch.setenv("LINE_RICHMENU_ADMIN_ID", "richmenu-admin")

    assert get_richmenu_for_user(admin_user()) == "richmenu-admin"


def test_get_richmenu_for_user_picks_user_menu(monkeypatch) -> None:
    monkeypatch.setenv("LINE_RICHMENU_USER_ID", "richmenu-user")

    assert get_richmenu_for_user(borrower_user()) == "richmenu-user"


def test_get_richmenu_for_user_none_when_env_missing() -> None:
    assert get_richmenu_for_user(admin_user()) is None
    assert get_richmenu_for_user(borrower_user()) is None


def test_service_unconfigured_skips_http(recorder) -> None:
    service = LineMessagingService()

    assert service.is_configured() is False
    service.link_richmenu_to_user("u-1", "richmenu-1")
    service.unlink_richmenu_from_user("u-1")

    assert recorder.requests == []


def test_link_richmenu_posts_correct_request(monkeypatch, recorder) -> None:
    monkeypatch.setenv("LINE_MESSAGING_CHANNEL_ACCESS_TOKEN", "token-1")
    service = LineMessagingService()

    service.link_richmenu_to_user("u-1", "richmenu-1")

    (request,) = recorder.requests
    assert request.full_url == (
        "https://api.line.me/v2/bot/user/u-1/richmenu/richmenu-1"
    )
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == "Bearer token-1"


def test_unlink_richmenu_deletes_correct_request(monkeypatch, recorder) -> None:
    monkeypatch.setenv("LINE_MESSAGING_CHANNEL_ACCESS_TOKEN", "token-1")
    service = LineMessagingService()

    service.unlink_richmenu_from_user("u-1")

    (request,) = recorder.requests
    assert request.full_url == "https://api.line.me/v2/bot/user/u-1/richmenu"
    assert request.get_method() == "DELETE"


def test_sync_richmenu_links_menu_for_role(monkeypatch) -> None:
    monkeypatch.setenv("LINE_RICHMENU_USER_ID", "richmenu-user")
    stub = _StubService()

    sync_richmenu("u-1", borrower_user(), service=stub)

    assert stub.linked == [("u-1", "richmenu-user")]


def test_sync_richmenu_skips_when_menu_not_configured(monkeypatch) -> None:
    stub = _StubService()

    sync_richmenu("u-1", borrower_user(), service=stub)

    assert stub.linked == []


def test_sync_richmenu_skips_when_service_unconfigured(monkeypatch) -> None:
    monkeypatch.setenv("LINE_RICHMENU_USER_ID", "richmenu-user")
    stub = _StubService(configured=False)

    sync_richmenu("u-1", borrower_user(), service=stub)

    assert stub.linked == []


def test_sync_richmenu_never_raises(monkeypatch) -> None:
    monkeypatch.setenv("LINE_RICHMENU_USER_ID", "richmenu-user")
    stub = _StubService(error=RuntimeError("LINE down"))

    sync_richmenu("u-1", borrower_user(), service=stub)
