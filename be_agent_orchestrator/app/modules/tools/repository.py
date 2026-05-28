"""DB access for the tool registry.

Repositories are intentionally thin — every method maps to one or two
SQL statements and never reaches across modules. The service layer is
responsible for stitching tools + agents + workspaces together.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agents.models import AgentTool
from app.modules.tools.models import (
    Tool,
    ToolApproval,
    ToolExecution,
    ToolExecutionLog,
    ToolVersion,
)


class ToolRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Tools ────────────────────────────────────────────────────────

    async def create(self, **kwargs: Any) -> Tool:
        tool = Tool(**kwargs)
        self.db.add(tool)
        await self.db.commit()
        await self.db.refresh(tool)
        return tool

    async def get(self, tool_id: UUID) -> Tool | None:
        stmt = select(Tool).where(Tool.id == tool_id, Tool.deleted_at.is_(None))
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_in_workspace(self, workspace_id: UUID, tool_id: UUID) -> Tool | None:
        """Return the tool if it's a workspace-scoped tool *or* a global builtin."""

        stmt = select(Tool).where(
            Tool.id == tool_id,
            Tool.deleted_at.is_(None),
            or_(Tool.workspace_id == workspace_id, Tool.workspace_id.is_(None)),
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_by_slug(self, workspace_id: UUID, slug: str) -> Tool | None:
        """Resolve a tool slug to a row. Prefers workspace-scoped over global
        when both exist (agent overrides win)."""

        stmt = (
            select(Tool)
            .where(
                Tool.slug == slug,
                Tool.deleted_at.is_(None),
                or_(Tool.workspace_id == workspace_id, Tool.workspace_id.is_(None)),
            )
            # workspace_id NULLs sort last with NULLS LAST, so the workspace
            # row comes first when both exist.
            .order_by(Tool.workspace_id.is_(None))
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def list_in_workspace(
        self,
        workspace_id: UUID,
        *,
        page: int,
        page_size: int,
        type_filter: str | None = None,
        category: str | None = None,
        status_filter: str | None = None,
        include_global: bool = True,
    ) -> tuple[list[Tool], int]:
        """Paginated list. Includes global builtins (workspace_id IS NULL)
        unless ``include_global=False``."""

        offset = (page - 1) * page_size

        scope_clause = (
            or_(Tool.workspace_id == workspace_id, Tool.workspace_id.is_(None))
            if include_global
            else Tool.workspace_id == workspace_id
        )

        where = [Tool.deleted_at.is_(None), scope_clause]
        if type_filter:
            where.append(Tool.type == type_filter)
        if category:
            where.append(Tool.category == category)
        if status_filter:
            where.append(Tool.status == status_filter)

        items_q = (
            select(Tool)
            .where(*where)
            .order_by(desc(Tool.created_at))
            .offset(offset)
            .limit(page_size)
        )
        total_q = select(func.count(Tool.id)).where(*where)

        items = list((await self.db.execute(items_q)).scalars())
        total = (await self.db.execute(total_q)).scalar_one()
        return items, total

    async def update(self, tool: Tool, **fields: Any) -> Tool:
        for key, value in fields.items():
            setattr(tool, key, value)
        await self.db.commit()
        await self.db.refresh(tool)
        return tool

    async def soft_delete(self, tool: Tool) -> None:
        from datetime import UTC, datetime

        tool.deleted_at = datetime.now(UTC)
        tool.status = "archived"
        await self.db.commit()

    async def slug_exists(self, workspace_id: UUID | None, slug: str) -> bool:
        scope = (
            Tool.workspace_id == workspace_id
            if workspace_id is not None
            else Tool.workspace_id.is_(None)
        )
        stmt = select(func.count(Tool.id)).where(
            scope,
            Tool.slug == slug,
            Tool.deleted_at.is_(None),
        )
        count: int = (await self.db.execute(stmt)).scalar_one()
        return count > 0

    # ── Versions ─────────────────────────────────────────────────────

    async def create_version(self, **kwargs: Any) -> ToolVersion:
        version = ToolVersion(**kwargs)
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        return version

    async def list_versions(self, tool_id: UUID) -> list[ToolVersion]:
        stmt = (
            select(ToolVersion)
            .where(ToolVersion.tool_id == tool_id)
            .order_by(desc(ToolVersion.version_number))
        )
        return list((await self.db.execute(stmt)).scalars())

    async def get_version(self, tool_id: UUID, version_number: int) -> ToolVersion | None:
        stmt = select(ToolVersion).where(
            ToolVersion.tool_id == tool_id,
            ToolVersion.version_number == version_number,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    # ── Executions ───────────────────────────────────────────────────

    async def create_execution(self, **kwargs: Any) -> ToolExecution:
        execution = ToolExecution(**kwargs)
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def update_execution(self, execution: ToolExecution, **fields: Any) -> ToolExecution:
        for key, value in fields.items():
            setattr(execution, key, value)
        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def get_execution(self, execution_id: UUID) -> ToolExecution | None:
        stmt = select(ToolExecution).where(ToolExecution.id == execution_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_executions_for_tool(
        self,
        tool_id: UUID,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[ToolExecution], int]:
        offset = (page - 1) * page_size
        items_q = (
            select(ToolExecution)
            .where(ToolExecution.tool_id == tool_id)
            .order_by(desc(ToolExecution.started_at))
            .offset(offset)
            .limit(page_size)
        )
        total_q = select(func.count(ToolExecution.id)).where(ToolExecution.tool_id == tool_id)

        items = list((await self.db.execute(items_q)).scalars())
        total = (await self.db.execute(total_q)).scalar_one()
        return items, total

    # ── Logs ─────────────────────────────────────────────────────────

    async def append_log(
        self,
        execution_id: UUID,
        *,
        level: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> ToolExecutionLog:
        log = ToolExecutionLog(
            execution_id=execution_id,
            level=level,
            message=message,
            log_metadata=metadata or {},
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def list_logs(self, execution_id: UUID) -> list[ToolExecutionLog]:
        stmt = (
            select(ToolExecutionLog)
            .where(ToolExecutionLog.execution_id == execution_id)
            .order_by(ToolExecutionLog.created_at.asc())
        )
        return list((await self.db.execute(stmt)).scalars())

    # ── Approvals ────────────────────────────────────────────────────

    async def create_approval(self, **kwargs: Any) -> ToolApproval:
        approval = ToolApproval(**kwargs)
        self.db.add(approval)
        await self.db.commit()
        await self.db.refresh(approval)
        return approval

    async def get_approval(self, approval_id: UUID) -> ToolApproval | None:
        stmt = select(ToolApproval).where(ToolApproval.id == approval_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_approval_for_execution(self, execution_id: UUID) -> ToolApproval | None:
        stmt = select(ToolApproval).where(ToolApproval.execution_id == execution_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def update_approval(self, approval: ToolApproval, **fields: Any) -> ToolApproval:
        for key, value in fields.items():
            setattr(approval, key, value)
        await self.db.commit()
        await self.db.refresh(approval)
        return approval

    async def list_pending_approvals(self, workspace_id: UUID) -> list[ToolApproval]:
        stmt = (
            select(ToolApproval)
            .where(
                ToolApproval.workspace_id == workspace_id,
                ToolApproval.status == "pending",
            )
            .order_by(desc(ToolApproval.created_at))
        )
        return list((await self.db.execute(stmt)).scalars())

    # ── Agent ↔ Tool ─────────────────────────────────────────────────

    async def attach_tool(
        self,
        *,
        agent_id: UUID,
        tool_id: UUID,
        is_enabled: bool,
        config: dict[str, Any],
    ) -> AgentTool:
        link = AgentTool(
            agent_id=agent_id,
            tool_id=tool_id,
            is_enabled=is_enabled,
            config=config,
        )
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def detach_tool(self, agent_id: UUID, tool_id: UUID) -> int:
        from sqlalchemy import delete
        from sqlalchemy.engine import CursorResult

        result = await self.db.execute(
            delete(AgentTool).where(AgentTool.agent_id == agent_id, AgentTool.tool_id == tool_id)
        )
        await self.db.commit()
        # DML statements return CursorResult; narrowing is for mypy --strict.
        rowcount = getattr(result, "rowcount", 0) if isinstance(result, CursorResult) else 0
        return int(rowcount or 0)

    async def list_agent_tools(self, agent_id: UUID) -> list[AgentTool]:
        stmt = select(AgentTool).where(AgentTool.agent_id == agent_id)
        return list((await self.db.execute(stmt)).scalars())

    async def get_agent_tool(self, agent_id: UUID, tool_id: UUID) -> AgentTool | None:
        stmt = select(AgentTool).where(AgentTool.agent_id == agent_id, AgentTool.tool_id == tool_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()
