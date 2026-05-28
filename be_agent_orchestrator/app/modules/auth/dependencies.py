from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import PermissionDeniedError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    if credentials is None:
        raise UnauthorizedError("missing_token", "Authentication required.")

    payload = decode_access_token(credentials.credentials)

    if payload.get("type") != "access":
        raise UnauthorizedError("invalid_token", "Not an access token.")

    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise UnauthorizedError("invalid_token", "Token missing subject.")
    try:
        user_id = UUID(sub)
    except ValueError as exc:
        raise UnauthorizedError("invalid_token", "Token subject is not a UUID.") from exc

    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("user_not_found", "User no longer exists or is inactive.")

    return user


async def require_verified(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_verified:
        raise PermissionDeniedError(
            "email_not_verified", "Verify your email before using this endpoint."
        )
    return current_user
