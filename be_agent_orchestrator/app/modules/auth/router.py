"""Auth endpoints — signup, login, refresh, logout, me."""

from fastapi import APIRouter, Depends, status

from app.api.deps import get_auth_service, get_current_user
from app.core.openapi import auth_required_responses, public_responses
from app.modules.auth.service import AuthService
from app.modules.users.models import User

from .schemas import (
    CurrentUserResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
    description=(
        "Creates a new user and returns access + refresh tokens (auto-login). "
        "Email must be unique; password must be at least 8 characters."
    ),
    operation_id="auth_post_signup",
    responses=public_responses(409),
)
async def signup(
    payload: SignupRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    _, tokens = await service.signup(payload)
    return tokens


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in with email + password",
    description=(
        "Exchanges email + password for an access token (12h) and a refresh token (30d). "
        "Send the access token as `Authorization: Bearer <token>` on every protected request. "
        "Rotate via `POST /auth/refresh` before the access token expires."
    ),
    operation_id="auth_post_login",
    responses=public_responses(401),
)
async def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return await service.login(payload)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange a refresh token for a new pair",
    description=(
        "Returns a freshly issued access + refresh token pair. The presented refresh "
        "token is revoked atomically — clients must store the new one and discard the old."
    ),
    operation_id="auth_post_refresh",
    responses=public_responses(401),
)
async def refresh(
    payload: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return await service.refresh(payload.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a refresh token",
    description=(
        "Revokes the presented refresh token immediately. The corresponding access token "
        "expires naturally (no server-side revocation list for access tokens — keep TTL short). "
        "Idempotent: revoking an already-invalid token returns 204."
    ),
    operation_id="auth_post_logout",
    responses=public_responses(),
)
async def logout(
    payload: LogoutRequest,
    service: AuthService = Depends(get_auth_service),
) -> None:
    await service.logout(payload.refresh_token)


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the currently authenticated user",
    description="Returns the user identified by the bearer access token.",
    operation_id="auth_get_me",
    responses=auth_required_responses(),
)
async def me(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(current_user)
