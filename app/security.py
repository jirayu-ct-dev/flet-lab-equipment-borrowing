from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 260_000
PASSWORD_MIN_LENGTH = 8


def hash_password(password: str) -> str:
    """Hash with PBKDF2-SHA256 into 'pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>'."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return "$".join(
        (
            ALGORITHM,
            str(PBKDF2_ITERATIONS),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(digest).decode("ascii"),
        )
    )


def verify_password(password: str, stored: str) -> bool:
    """Constant-time comparison; returns False for malformed stored hashes."""
    try:
        algorithm, iterations_text, salt_b64, hash_b64 = stored.split("$")
        if algorithm != ALGORITHM:
            return False
        iterations = int(iterations_text)
        if iterations <= 0:
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
    except (TypeError, ValueError):
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(digest, expected)


def validate_password_strength(password: str) -> str | None:
    """Return a Thai validation message or None when the password is acceptable."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"รหัสผ่านต้องมีความยาวอย่างน้อย {PASSWORD_MIN_LENGTH} ตัวอักษร"
    return None


def new_session_token() -> str:
    return secrets.token_hex(32)
