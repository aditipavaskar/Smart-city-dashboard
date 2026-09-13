"""
Demo auth: issues an opaque token for a chosen role and looks it up again
on REST/WebSocket requests. This is intentionally NOT a real auth system —
there's no password, no expiry, no signature. It exists purely to let the
frontend demonstrate role-based dashboards (different users, different
widgets/topics) without dragging in a full identity provider.

Swap-in point for production: replace `issue_token` / `resolve_token` with
real JWT verification (e.g. against your SSO), keeping the same two-function
interface so main.py and websocket_manager.py don't change.
"""
from __future__ import annotations

import secrets

from app.config import ROLES

_SESSIONS: dict[str, str] = {}  # token -> role


def issue_token(role: str) -> str:
    if role not in ROLES:
        raise ValueError(f"unknown role: {role}")
    token = secrets.token_urlsafe(18)
    _SESSIONS[token] = role
    return token


def resolve_token(token: str) -> str | None:
    return _SESSIONS.get(token)
