from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen

from flet.auth import OAuthProvider

from app.models import LineMessage


AUTHORIZATION_URL = "https://access.line.me/oauth2/v2.1/authorize"
TOKEN_URL = "https://api.line.me/oauth2/v2.1/token"
PROFILE_URL = "https://api.line.me/v2/profile"


def provider() -> OAuthProvider | None:
    client_id = os.getenv("LINE_CLIENT_ID", "").strip()
    secret = os.getenv("LINE_CLIENT_SECRET", "").strip()
    redirect = os.getenv("LINE_REDIRECT_URL", "").strip()
    if not all((client_id, secret, redirect)):
        return None
    return OAuthProvider(
        client_id=client_id,
        client_secret=secret,
        authorization_endpoint=AUTHORIZATION_URL,
        token_endpoint=TOKEN_URL,
        redirect_url=redirect,
        scopes=["profile", "openid"],
        user_scopes=["profile"],
        user_endpoint=PROFILE_URL,
        user_id_fn=lambda data: data["userId"],
    )


class LineMessenger:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.getenv("LINE_MESSAGING_CHANNEL_ACCESS_TOKEN", "").strip()

    @property
    def configured(self) -> bool:
        return bool(self.token)

    def send(self, message: LineMessage) -> bool:
        if not self.token or not message.line_user_id:
            return False
        request = Request(
            "https://api.line.me/v2/bot/message/push",
            data=json.dumps({"to": message.line_user_id, "messages": [{"type": "text", "text": message.text}]}).encode(),
            method="POST",
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=10):
                return True
        except Exception:
            return False
