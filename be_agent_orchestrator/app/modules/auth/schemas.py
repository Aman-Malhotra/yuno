from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ──────────────────────────────────────────────────────────────────────
# Requests
# ──────────────────────────────────────────────────────────────────────


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=512)
    full_name: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "demo@yuno.ai",
                    "password": "correct-horse-battery-staple",
                    "full_name": "Demo User",
                }
            ]
        }
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=512)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"email": "demo@yuno.ai", "password": "correct-horse-battery-staple"}]
        }
    )


class RefreshRequest(BaseModel):
    refresh_token: str = Field(
        min_length=1,
        description="Opaque refresh token issued by /login or a previous /refresh.",
    )


class LogoutRequest(BaseModel):
    refresh_token: str = Field(
        min_length=1,
        description="Refresh token to revoke. The matching access token expires naturally.",
    )


# ──────────────────────────────────────────────────────────────────────
# Responses
# ──────────────────────────────────────────────────────────────────────


class TokenResponse(BaseModel):
    access_token: str = Field(
        description="JWT access token. Send as `Authorization: Bearer <token>`."
    )
    refresh_token: str = Field(description="Opaque refresh token. Store securely; do not log.")
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Access token TTL in seconds (12h = 43200).")
    refresh_expires_in: int = Field(description="Refresh token TTL in seconds (30d = 2592000).")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "xQ7aD2...long-opaque-string...",
                    "token_type": "bearer",
                    "expires_in": 43200,
                    "refresh_expires_in": 2592000,
                }
            ]
        }
    )


class CurrentUserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str | None = None
    avatar_url: str | None = None
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
