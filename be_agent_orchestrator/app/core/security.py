import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
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
        "exp": datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("invalid_token", "Invalid or expired token") from exc


def new_refresh_token() -> str:
    """384 bits of entropy from the OS CSPRNG, URL-safe base64."""

    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hex of the refresh token.

    Refresh tokens are high-entropy random already, so the slow / salted
    hashing used for user passwords is unnecessary and harmful here —
    we need deterministic lookup by hash and the brute-force attack model
    doesn't apply to 384-bit secrets.
    """

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_refresh_token(token: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_refresh_token(token), hashed)
