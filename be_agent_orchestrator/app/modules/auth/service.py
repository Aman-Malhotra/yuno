from datetime import UTC, datetime, timedelta

import structlog

from app.core.config import settings
from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.modules.auth.repository import RefreshTokenRepository
from app.modules.auth.schemas import LoginRequest, SignupRequest, TokenResponse
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.workspaces.service import WorkspaceService

log = structlog.get_logger("auth")


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        tokens: RefreshTokenRepository,
        workspaces: WorkspaceService,
    ) -> None:
        self.users = users
        self.tokens = tokens
        self.workspaces = workspaces

    # ──────────────────────────────────────────────────────────────────
    # Public flows
    # ──────────────────────────────────────────────────────────────────

    async def signup(self, payload: SignupRequest) -> tuple[User, TokenResponse]:
        existing = await self.users.get_by_email(payload.email)
        if existing is not None:
            log.warning("auth.signup.failed", reason="email_taken", email=payload.email)
            raise ConflictError(
                "email_taken",
                "An account with this email already exists.",
                {"email": payload.email},
            )

        user = await self.users.create(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
        )
        log.info("auth.signup", user_id=str(user.id), email=user.email)

        # Personal workspace so the user has somewhere to create workflows
        # immediately. Failure here is a hard signup failure — better to
        # have the user retry than land in a half-provisioned state.
        await self.workspaces.create_personal(
            owner_user_id=user.id,
            owner_display_name=user.full_name,
        )

        tokens = await self._issue_tokens(user)
        return user, tokens

    async def login(self, payload: LoginRequest) -> TokenResponse:
        user = await self.users.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            # Same error for "no such user" and "wrong password" to prevent
            # enumeration of registered emails.
            log.warning(
                "auth.login.failed",
                reason="invalid_credentials",
                email=payload.email,
                user_known=user is not None,
            )
            raise UnauthorizedError("invalid_credentials", "Invalid email or password.")
        if not user.is_active:
            log.warning(
                "auth.login.failed",
                reason="user_inactive",
                user_id=str(user.id),
                email=user.email,
            )
            raise UnauthorizedError("user_inactive", "This account is deactivated.")

        log.info("auth.login", user_id=str(user.id), email=user.email)
        return await self._issue_tokens(user)

    async def refresh(self, raw_refresh: str) -> TokenResponse:
        record = await self.tokens.get_active_by_hash(hash_refresh_token(raw_refresh))
        if record is None:
            log.warning("auth.refresh.failed", reason="invalid_or_expired")
            raise UnauthorizedError(
                "invalid_refresh_token", "Refresh token is invalid, expired or revoked."
            )
        user = await self.users.get_by_id(record.user_id)
        if user is None or not user.is_active:
            await self.tokens.revoke(record.id)
            log.warning(
                "auth.refresh.failed",
                reason="user_inactive",
                user_id=str(record.user_id),
            )
            raise UnauthorizedError("user_inactive", "Account is no longer active.")

        # Rotate: revoke the presented token before issuing a new pair.
        await self.tokens.revoke(record.id)
        log.info(
            "auth.refresh",
            user_id=str(user.id),
            rotated_token_id=str(record.id),
        )
        return await self._issue_tokens(user)

    async def logout(self, raw_refresh: str) -> None:
        record = await self.tokens.get_active_by_hash(hash_refresh_token(raw_refresh))
        if record is not None:
            await self.tokens.revoke(record.id)
            log.info(
                "auth.logout",
                user_id=str(record.user_id),
                revoked_token_id=str(record.id),
            )
        else:
            log.info("auth.logout.noop", reason="unknown_token")

    # ──────────────────────────────────────────────────────────────────
    # Token issuance
    # ──────────────────────────────────────────────────────────────────

    async def _issue_tokens(self, user: User) -> TokenResponse:
        access_token = create_access_token(str(user.id))

        raw_refresh = new_refresh_token()
        refresh_expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
        await self.tokens.create(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=refresh_expires_at,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.access_token_expire_minutes * 60,
            refresh_expires_in=settings.refresh_token_expire_days * 24 * 3600,
        )
