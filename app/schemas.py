from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    role: str


class LoginResponse(BaseModel):
    token: str
    role: str
    label: str
    domains: list[str]
