import os

from app.env import load_env_file


def test_load_env_file_reads_values_without_overriding(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        """
# comment line
APP_DB_PATH=data/test.db
LINE_CLIENT_ID="abc123"
LINE_REDIRECT_URL='https://example.com/callback'
IGNORED = because no equals
LINE_CLIENT_SECRET=
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("LINE_CLIENT_ID", "from-shell")

    loaded = load_env_file(env_file)

    assert loaded == env_file
    assert os.environ["APP_DB_PATH"] == "data/test.db"
    assert os.environ["LINE_REDIRECT_URL"] == "https://example.com/callback"
    # existing env must win
    assert os.environ["LINE_CLIENT_ID"] == "from-shell"
    # empty value is still loaded
    assert os.environ["LINE_CLIENT_SECRET"] == ""


def test_load_env_file_missing_returns_none(tmp_path) -> None:
    assert load_env_file(tmp_path / "not-there.env") is None
