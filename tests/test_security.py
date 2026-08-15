from app.security import (
    ALGORITHM,
    PBKDF2_ITERATIONS,
    hash_password,
    new_session_token,
    validate_password_strength,
    verify_password,
)


def test_hash_and_verify_roundtrip() -> None:
    hashed = hash_password("s3cret-pass")

    assert hashed.startswith(f"{ALGORITHM}${PBKDF2_ITERATIONS}$")
    assert verify_password("s3cret-pass", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_hashes_are_salted_and_unique() -> None:
    assert hash_password("same-password") != hash_password("same-password")


def test_verify_password_tolerates_malformed_stored_hashes() -> None:
    malformed = (
        "",
        "not-a-hash",
        "pbkdf2_sha256$wrong$iterations",
        "pbkdf2_sha256$260000$!!!$!!!",
        f"{ALGORITHM}$0$YWJj$YWJj",
        "md5$abc$def",
    )
    for stored in malformed:
        assert verify_password("anything", stored) is False


def test_password_strength_validation_message_is_thai() -> None:
    message = validate_password_strength("short")

    assert message is not None
    assert "รหัสผ่าน" in message
    assert validate_password_strength("12345678") is None


def test_session_tokens_are_long_and_unique() -> None:
    token = new_session_token()

    assert len(token) == 64
    assert token != new_session_token()
    assert new_session_token() != new_session_token()
