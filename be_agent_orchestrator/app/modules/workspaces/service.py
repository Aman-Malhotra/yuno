import re
import secrets
from typing import cast
from uuid import UUID

import structlog

from app.core.errors import PermissionDeniedError
from app.modules.users.models import Workspace
from app.modules.workspaces.repository import WorkspaceRepository
from app.modules.workspaces.schemas import WorkspaceRole, WorkspaceSummary

log = structlog.get_logger("workspaces")


def _slugify(text: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return base[:100] or "workspace"


class WorkspaceService:
    def __init__(self, repository: WorkspaceRepository) -> None:
        self.repository = repository

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[WorkspaceSummary], int]:
        rows, total = await self.repository.list_for_user(user_id, page=page, page_size=page_size)
        items = [
            WorkspaceSummary(
                id=ws.id,
                name=ws.name,
                slug=ws.slug,
                # DB CHECK constraint keeps role in {owner, admin, member, viewer}.
                role=cast(WorkspaceRole, role),
                created_at=ws.created_at,
            )
            for ws, role in rows
        ]
        return items, total

    async def get_role_or_403(self, workspace_id: UUID, user_id: UUID) -> WorkspaceRole:
        """Return the user's role in the workspace, or raise 403."""

        role = await self.repository.get_member_role(workspace_id, user_id)
        if role is None:
            raise PermissionDeniedError(
                "workspace_forbidden",
                "You are not a member of this workspace.",
                {"workspace_id": str(workspace_id)},
            )
        return cast(WorkspaceRole, role)

    async def delete(self, workspace_id: UUID, user_id: UUID) -> None:
        """Soft-delete a workspace. Only the workspace owner may do this.

        After this returns, the workspace disappears from the user's
        dashboard list, and any nested ACL check (``get_role_or_403``)
        will treat the workspace as if it no longer exists.
        """

        role = await self.get_role_or_403(workspace_id, user_id)
        if role != "owner":
            raise PermissionDeniedError(
                "owner_required",
                "Only the workspace owner can delete this workspace.",
                {"workspace_id": str(workspace_id), "your_role": role},
            )

        await self.repository.soft_delete(workspace_id)
        log.info(
            "workspace.deleted",
            workspace_id=str(workspace_id),
            actor_user_id=str(user_id),
            mode="soft",
        )

    async def create(
        self,
        *,
        owner_user_id: UUID,
        name: str,
    ) -> WorkspaceSummary:
        """Create a workspace and make the caller its owner.

        Returns a ``WorkspaceSummary`` (same shape as list rows) so the
        client can drop the result straight into its workspace list.
        """

        slug = f"{_slugify(name)}-{secrets.token_hex(3)}"
        workspace = await self.repository.create(
            name=name,
            slug=slug,
            owner_user_id=owner_user_id,
        )
        log.info(
            "workspace.created",
            workspace_id=str(workspace.id),
            owner_user_id=str(owner_user_id),
            kind="explicit",
        )
        return WorkspaceSummary(
            id=workspace.id,
            name=workspace.name,
            slug=workspace.slug,
            role="owner",
            created_at=workspace.created_at,
        )

    async def create_personal(
        self,
        *,
        owner_user_id: UUID,
        owner_display_name: str | None,
    ) -> Workspace:
        """Auto-provision a personal workspace at signup time."""

        name = (owner_display_name or "Personal") + "'s Workspace"
        slug = f"{_slugify(owner_display_name or 'personal')}-{secrets.token_hex(3)}"
        workspace = await self.repository.create(
            name=name,
            slug=slug,
            owner_user_id=owner_user_id,
        )
        log.info(
            "workspace.created",
            workspace_id=str(workspace.id),
            owner_user_id=str(owner_user_id),
            kind="personal",
        )
        return workspace
