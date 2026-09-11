from __future__ import annotations

import os
import re

from flet.auth import OAuthProvider

from app.contracts import AppUser, AuthService, RegisterLineUser

LINE_AUTHORIZATION_ENDPOINT = "https://access.line.me/oauth2/v2.1/authorize"
LINE_TOKEN_ENDPOINT = "https://api.line.me/oauth2/v2.1/token"
LINE_PROFILE_ENDPOINT = "https://api.line.me/v2/profile"


def line_user_id(data: dict) -> str:
    return data["userId"]


def get_line_provider() -> OAuthProvider | None:
    """Build the LINE OAuth provider from env config; None when unconfigured."""
    client_id = os.getenv("LINE_CLIENT_ID")
    client_secret = os.getenv("LINE_CLIENT_SECRET")
    redirect_url = os.getenv("LINE_REDIRECT_URL")
    if not client_id or not client_secret or not redirect_url:
        return None
    return OAuthProvider(
        client_id=client_id,
        client_secret=client_secret,
        authorization_endpoint=LINE_AUTHORIZATION_ENDPOINT,
        token_endpoint=LINE_TOKEN_ENDPOINT,
        redirect_url=redirect_url,
        scopes=["profile", "openid"],
        user_scopes=["profile"],
        user_endpoint=LINE_PROFILE_ENDPOINT,
        user_id_fn=line_user_id,
    )


def register_or_fetch_user(
    auth: AuthService,
    user_id: str,
    display_name: str,
    *,
    auto_create_borrower: bool = False,
) -> AppUser:
    existing = auth.find_by_line_sub(user_id)
    if existing is not None:
        return existing

    # A LINE profile is a login identity, not a reliable borrower code.  For a
    # first-time login we create a clearly named borrower profile so the user
    # can immediately see their own loans.  Staff can later edit the profile
    # or link it to an existing borrower record from the people directory.
    borrower_code = None
    if auto_create_borrower:
        safe_id = re.sub(r"[^A-Za-z0-9]", "-", user_id[-12:]).strip("-").upper()
        borrower_code = f"LINE-{safe_id or 'USER'}"
    return auth.register_line_user(
        RegisterLineUser(
            line_sub=user_id,
            display_name=display_name,
            borrower_code=borrower_code,
            department="ผู้ใช้ LINE" if borrower_code else None,
        )
    )
