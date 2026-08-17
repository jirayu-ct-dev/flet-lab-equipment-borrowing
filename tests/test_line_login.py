import pytest

from app.contracts import Role
from app.services.fake_services import FakeAuthService
from app.services.line_login import (
    LINE_AUTHORIZATION_ENDPOINT,
    LINE_PROFILE_ENDPOINT,
    LINE_TOKEN_ENDPOINT,
    get_line_provider,
    line_user_id,
    register_or_fetch_user,
)


@pytest.fixture(autouse=True)
def _clear_line_env(monkeypatch) -> None:
    for name in ("LINE_CLIENT_ID", "LINE_CLIENT_SECRET", "LINE_REDIRECT_URL"):
        monkeypatch.delenv(name, raising=False)


def test_get_line_provider_returns_none_when_env_missing() -> None:
    assert get_line_provider() is None


def test_get_line_provider_returns_none_when_env_partial(monkeypatch) -> None:
    monkeypatch.setenv("LINE_CLIENT_ID", "client-id")

    assert get_line_provider() is None


def test_get_line_provider_builds_configured_provider(monkeypatch) -> None:
    monkeypatch.setenv("LINE_CLIENT_ID", "client-id")
    monkeypatch.setenv("LINE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("LINE_REDIRECT_URL", "https://lab.local/line/callback")

    provider = get_line_provider()

    assert provider is not None
    assert provider.client_id == "client-id"
    assert provider.client_secret == "client-secret"
    assert provider.authorization_endpoint == LINE_AUTHORIZATION_ENDPOINT
    assert provider.token_endpoint == LINE_TOKEN_ENDPOINT
    assert provider.redirect_url == "https://lab.local/line/callback"
    assert provider.scopes == ["profile", "openid"]
    assert provider.user_scopes == ["profile"]
    assert provider.user_endpoint == LINE_PROFILE_ENDPOINT
    assert provider.user_id_fn({"userId": "u-123", "displayName": "ผู้ใช้ไลน์"}) == "u-123"


def test_line_user_id_extracts_user_id() -> None:
    assert line_user_id({"userId": "u-42"}) == "u-42"


def test_register_or_fetch_user_creates_once_and_reuses() -> None:
    auth = FakeAuthService()

    created = register_or_fetch_user(auth, "line-sub-1", "ผู้ใช้ไลน์")

    assert created.role is Role.USER
    assert created.borrower_id is None
    assert auth.find_by_line_sub("line-sub-1").id == created.id

    again = register_or_fetch_user(auth, "line-sub-1", "ชื่อใหม่")

    assert again.id == created.id
    assert len(auth.list_users()) == 3
