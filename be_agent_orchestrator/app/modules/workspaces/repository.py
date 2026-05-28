from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import Workspace, WorkspaceMember


class WorkspaceRepository:
    """All workspace + membership queries.

    Listing always joins through ``workspace_members`` so a user only
    ever sees workspaces they belong to.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[Workspace, str]], int]:
        """Return ``(workspace, member_role)`` pairs + total count."""

        offset = (page - 1) * page_size

        items_q = (
            select(Workspace, WorkspaceMember.role)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(
                WorkspaceMember.user_id == user_id,
                Workspace.deleted_at.is_(None),
            )
            .order_by(Workspace.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        total_q = (
            select(func.count(Workspace.id))
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(
                WorkspaceMember.user_id == user_id,
                Workspace.deleted_at.is_(None),
            )
        )

        items_result = await self.db.execute(items_q)
        items: list[tuple[Workspace, str]] = [(ws, role) for ws, role in items_result.all()]
        total = (await self.db.execute(total_q)).scalar_one()
        return items, total

    async def get_member_role(self, workspace_id: UUID, user_id: UUID) -> str | None:
        """Return the user's role in this workspace, or None if not a member.

        Joins to ``workspaces`` and filters ``deleted_at IS NULL`` so a
        soft-deleted workspace behaves as if it no longer exists for ACL
        purposes — nested endpoints (workflows, agents, …) auto-403 after
        the workspace is deleted, without each one needing its own check.
        """

        stmt = (
            select(WorkspaceMember.role)
            .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
                Workspace.deleted_at.is_(None),
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def soft_delete(self, workspace_id: UUID) -> None:
        """Mark a workspace deleted (sets ``deleted_at = now()``).

        The caller is expected to have already established the workspace
        exists + the user owns it via ``get_member_role``, so we don't
        need to inspect rowcount here — a no-op UPDATE is harmless.
        """

        stmt = (
            update(Workspace)
            .where(
                Workspace.id == workspace_id,
                Workspace.deleted_at.is_(None),
            )
            .values(deleted_at=func.now())
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def create(
        self,
        *,
        name: str,
        slug: str,
        owner_user_id: UUID,
    ) -> Workspace:
        """Create a workspace and add the owner as the first member.

        Same session, two inserts, one commit at the end. The previous
        repository call already committed and closed its transaction, so a
        new ``begin()`` here would conflict with the session's autobegin —
        plain add → flush → add → commit is the safe pattern.
        """

        workspace = Workspace(name=name, slug=slug)
        self.db.add(workspace)
        await self.db.flush()

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=owner_user_id,
            role="owner",
        )
        self.db.add(member)

        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace
