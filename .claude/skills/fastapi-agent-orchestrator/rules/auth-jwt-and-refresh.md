---
title: JWT Access + Opaque Refresh Token
impact: CRITICAL
impactDescription: Short-lived JWT for routes; revocable refresh in DB — simple, stateless API, still revocable on logout
tags: auth, jwt, refresh-token
---

## JWT Access + Opaque Refresh Token

Two tokens, two roles:

- **Access token** — JWT, ~30 min TTL, sent on every protected request
- **Refresh token** — opaque (random bytes), ~7 day TTL, stored hashed in DB, swappable on `POST /auth/refresh`

### Schemas

```python
# app/modules/auth/schemas.py
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None = None
    role: str
```

### Token creation + validation

```python
# app/core/security.py
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import settings
from app.core.errors import UnauthorizedError


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(user_id: str) -> str:
    payload: dict[str, Any] = {
        "sub": user_id,
        "type": "access",
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("invalid_token", "Invalid or expired token") from exc


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    # Use the same password hasher — argon2id is fine for opaque tokens too
    return password_hash.hash(token)


def verify_refresh_token(token: str, hashed: str) -> bool:
    return password_hash.verify(token, hashed)
```

### Refresh token model

```python
# app/modules/auth/models.py
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class RefreshToken(Base, IdMixin, TimestampMixin):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

### Service flow

```python
# app/modules/auth/service.py
class AuthService:
    def __init__(self, users: UserRepository, tokens: RefreshTokenRepository):
        self.users = users
        self.tokens = tokens

    async def register(self, payload: RegisterRequest) -> User:
        if await self.users.get_by_email(payload.email):
            raise ConflictError("email_taken", "Email already registered")
        return await self.users.create(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            role="user",
        )

    async def login(self, payload: LoginRequest) -> TokenResponse:
        user = await self.users.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedError("invalid_credentials", "Invalid email or password")
        return await self._issue_tokens(user.id)

    async def refresh(self, raw_refresh: str) -> TokenResponse:
        record = await self.tokens.find_active_for_token(raw_refresh)
        if not record:
            raise UnauthorizedError("invalid_refresh", "Refresh token invalid or expired")
        await self.tokens.revoke(record.id)
        return await self._issue_tokens(record.user_id)

    async def logout(self, raw_refresh: str) -> None:
        record = await self.tokens.find_active_for_token(raw_refresh)
        if record:
            await self.tokens.revoke(record.id)

    async def _issue_tokens(self, user_id: str) -> TokenResponse:
        access = create_access_token(user_id)
        raw_refresh = new_refresh_token()
        await self.tokens.create(
            user_id=user_id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
        )
        return TokenResponse(access_token=access, refresh_token=raw_refresh)
```

### Endpoints

```python
# app/modules/auth/router.py
router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=CurrentUserResponse, status_code=201)
async def register(payload: RegisterRequest, service: AuthService = Depends(get_auth_service)):
    user = await service.register(payload)
    return CurrentUserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, service: AuthService = Depends(get_auth_service)):
    return await service.login(payload)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, service: AuthService = Depends(get_auth_service)):
    return await service.refresh(payload.refresh_token)


@router.post("/logout", status_code=204)
async def logout(payload: RefreshRequest, service: AuthService = Depends(get_auth_service)):
    await service.logout(payload.refresh_token)


@router.get("/me", response_model=CurrentUserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return CurrentUserResponse.model_validate(current_user)
```

### Bad — long-lived JWT, no refresh

```python
# ❌ 30-day JWT with no revocation; a stolen token is good for a month
create_access_token(user_id, expires=timedelta(days=30))
```

### Bad — storing refresh tokens in plaintext

```python
# ❌ DB breach = every refresh token usable
RefreshToken(user_id=..., token=raw_refresh, ...)
```

### Rules

- Access token TTL: 15–60 min
- Refresh TTL: 7–30 days
- Refresh tokens stored **hashed**, never plaintext
- Refresh rotates on every `/auth/refresh` (old one revoked, new one issued)
- Logout revokes the presented refresh token
- For the assignment, JSON-body refresh is fine; production-style would set the refresh as an `HttpOnly` cookie

See: [[auth-password-hashing]], [[auth-current-user-dep]], [[api-error-handling]]
