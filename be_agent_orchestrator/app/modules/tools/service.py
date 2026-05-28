"""Tool registry service.

Stitches together:
- workspace ACL (via `WorkspaceService.get_role_or_403`)
- the tool repository
- the executor (used by the test console and the runtime)

All HTTP-facing entrypoints land here. The router stays thin and only
shapes request/response.
"""

from __future__ import annotations

import re
import secrets as _secrets
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog

from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.modules.agents.models import Agent, AgentTool
from app.modules.agents.repository import AgentRepository
from app.modules.tools.builtins import get_builtin
from app.modules.tools.executor import DispatchContext, ToolExecutor
from app.modules.tools.models import Tool, ToolApproval, ToolExecution, ToolVersion
from app.modules.tools.repository import ToolRepository
from app.modules.tools.schemas import (
    AgentToolPermissionConfig,
    AttachToolRequest,
    CreateToolRequest,
    ExecuteToolRequest,
    UpdateToolRequest,
)
from app.modules.workspaces.service import WorkspaceService

log = structlog.get_logger("tools")


def _slugify(text: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return base[:100] or "tool"


class ToolService:
    def __init__(
        self,
        repository: ToolRepository,
        workspace_service: WorkspaceService,
        executor: ToolExecutor,
        agent_repository: AgentRepository,
    ) -> None:
        self.repository = repository
        self.workspace_service = workspace_service
        self.executor = executor
        self.agent_repository = agent_repository

    # ── Tools — CRUD ────────────────────────────────────────────────

    async def list_in_workspace(
        self,
        workspace_id: UUID,
        user_id: UUID,
        *,
        page: int,
        page_size: int,
        type_filter: str | None = None,
        category: str | None = None,
        status_filter: str | None = None,
    ) -> tuple[list[Tool], int]:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)
        return await self.repository.list_in_workspace(
            workspace_id,
            page=page,
            page_size=page_size,
            type_filter=type_filter,
            category=category,
            status_filter=status_filter,
        )

    async def get_in_workspace(self, workspace_id: UUID, tool_id: UUID, user_id: UUID) -> Tool:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)
        tool = await self.repository.get_in_workspace(workspace_id, tool_id)
        if tool is None:
            raise NotFoundError(
                "tool_not_found",
                "Tool does not exist in this workspace.",
                {"workspace_id": str(workspace_id), "tool_id": str(tool_id)},
            )
        return tool

    async def create(
        self,
        workspace_id: UUID,
        user_id: UUID,
        payload: CreateToolRequest,
    ) -> Tool:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)

        # Builtin tools must reference a registered handler.
        if payload.type == "builtin":
            handler_name = (payload.config or {}).get("handler")
            if not handler_name or get_builtin(handler_name) is None:
                raise ValidationError(
                    "builtin_handler_unknown",
                    "config.handler must reference a registered builtin tool.",
                    {"handler": handler_name},
                )

        slug = f"{_slugify(payload.name)}-{_secrets.token_hex(3)}"
        if await self.repository.slug_exists(workspace_id, slug):
            raise ConflictError(
                "tool_slug_conflict",
                "A tool with the same slug already exists in this workspace.",
                {"slug": slug},
            )

        tool = await self.repository.create(
            workspace_id=workspace_id,
            created_by=user_id,
            name=payload.name,
            slug=slug,
            description=payload.description,
            type=payload.type,
            category=payload.category,
            icon=payload.icon,
            status=payload.status,
            version=1,
            input_schema=payload.input_schema,
            output_schema=payload.output_schema,
            config=payload.config,
            auth_type=payload.auth.type,
            auth_config=payload.auth.model_dump(exclude={"type"}),
            secret_refs=payload.auth.secret_refs,
            guardrails=payload.guardrails.model_dump(),
            execution_policy=payload.execution_policy.model_dump(),
            channel_config=payload.channels.model_dump(),
        )

        # First version snapshot.
        await self._snapshot_version(tool, user_id)
        log.info(
            "tool.created",
            tool_id=str(tool.id),
            workspace_id=str(workspace_id),
            type=tool.type,
            created_by=str(user_id),
        )
        return tool

    async def update(
        self,
        workspace_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        payload: UpdateToolRequest,
    ) -> Tool:
        tool = await self.get_in_workspace(workspace_id, tool_id, user_id)
        if tool.workspace_id is None:
            raise PermissionDeniedError(
                "tool_global_readonly",
                "Built-in global tools cannot be edited.",
                {"tool_id": str(tool.id)},
            )

        updates: dict[str, Any] = {}
        if payload.name is not None:
            updates["name"] = payload.name
        if payload.description is not None:
            updates["description"] = payload.description
        if payload.category is not None:
            updates["category"] = payload.category
        if payload.icon is not None:
            updates["icon"] = payload.icon
        if payload.input_schema is not None:
            updates["input_schema"] = payload.input_schema
        if payload.output_schema is not None:
            updates["output_schema"] = payload.output_schema
        if payload.config is not None:
            updates["config"] = payload.config
        if payload.auth is not None:
            updates["auth_type"] = payload.auth.type
            updates["auth_config"] = payload.auth.model_dump(exclude={"type"})
            updates["secret_refs"] = payload.auth.secret_refs
        if payload.guardrails is not None:
            updates["guardrails"] = payload.guardrails.model_dump()
        if payload.execution_policy is not None:
            updates["execution_policy"] = payload.execution_policy.model_dump()
        if payload.channels is not None:
            updates["channel_config"] = payload.channels.model_dump()
        if payload.status is not None:
            updates["status"] = payload.status

        if payload.publish_new_version:
            updates["version"] = tool.version + 1

        tool = await self.repository.update(tool, **updates)

        if payload.publish_new_version:
            await self._snapshot_version(tool, user_id)

        log.info(
            "tool.updated",
            tool_id=str(tool.id),
            version=tool.version,
            actor_user_id=str(user_id),
            new_version=payload.publish_new_version,
        )
        return tool

    async def delete(self, workspace_id: UUID, tool_id: UUID, user_id: UUID) -> None:
        tool = await self.get_in_workspace(workspace_id, tool_id, user_id)
        if tool.workspace_id is None:
            raise PermissionDeniedError(
                "tool_global_readonly",
                "Built-in global tools cannot be deleted.",
                {"tool_id": str(tool.id)},
            )
        await self.repository.soft_delete(tool)
        log.info("tool.deleted", tool_id=str(tool_id), actor_user_id=str(user_id))

    # ── Versions ─────────────────────────────────────────────────────

    async def list_versions(
        self, workspace_id: UUID, tool_id: UUID, user_id: UUID
    ) -> list[ToolVersion]:
        await self.get_in_workspace(workspace_id, tool_id, user_id)
        return await self.repository.list_versions(tool_id)

    async def _snapshot_version(self, tool: Tool, user_id: UUID | None) -> ToolVersion:
        return await self.repository.create_version(
            tool_id=tool.id,
            version_number=tool.version,
            name=tool.name,
            description=tool.description,
            type=tool.type,
            input_schema=tool.input_schema,
            output_schema=tool.output_schema,
            config=tool.config,
            guardrails=tool.guardrails,
            execution_policy=tool.execution_policy,
            snapshot={
                "auth_type": tool.auth_type,
                "auth_config": tool.auth_config,
                "channel_config": tool.channel_config,
                "category": tool.category,
                "icon": tool.icon,
            },
            created_by=user_id,
        )

    # ── Test console ────────────────────────────────────────────────

    async def execute_for_test(
        self,
        workspace_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        payload: ExecuteToolRequest,
    ) -> ToolExecution | dict[str, Any]:
        tool = await self.get_in_workspace(workspace_id, tool_id, user_id)
        ctx = DispatchContext(
            workspace_id=workspace_id,
            agent_id=payload.agent_id,
            user_id=user_id,
            secrets={},  # secrets module wires real values in here.
        )
        return await self.executor.execute(
            tool, payload.input, ctx, record=True, dry_run=payload.dry_run
        )

    # ── Execution listing ───────────────────────────────────────────

    async def list_executions(
        self,
        workspace_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[ToolExecution], int]:
        await self.get_in_workspace(workspace_id, tool_id, user_id)
        return await self.repository.list_executions_for_tool(
            tool_id, page=page, page_size=page_size
        )

    async def get_execution(
        self, workspace_id: UUID, execution_id: UUID, user_id: UUID
    ) -> tuple[ToolExecution, list[Any]]:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)
        execution = await self.repository.get_execution(execution_id)
        if execution is None or execution.workspace_id != workspace_id:
            raise NotFoundError(
                "tool_execution_not_found",
                "Tool execution does not exist in this workspace.",
                {"execution_id": str(execution_id)},
            )
        logs = await self.repository.list_logs(execution_id)
        return execution, logs

    # ── Approvals ────────────────────────────────────────────────────

    async def list_pending_approvals(self, workspace_id: UUID, user_id: UUID) -> list[ToolApproval]:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)
        return await self.repository.list_pending_approvals(workspace_id)

    async def decide_approval(
        self,
        workspace_id: UUID,
        approval_id: UUID,
        user_id: UUID,
        *,
        decision: str,
        reason: str | None,
    ) -> ToolApproval:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)
        approval = await self.repository.get_approval(approval_id)
        if approval is None or approval.workspace_id != workspace_id:
            raise NotFoundError(
                "tool_approval_not_found",
                "Approval does not exist in this workspace.",
                {"approval_id": str(approval_id)},
            )
        if approval.status != "pending":
            raise ConflictError(
                "tool_approval_already_decided",
                "Approval has already been resolved.",
                {"status": approval.status},
            )

        if decision == "approve":
            updated = await self.repository.update_approval(
                approval,
                status="approved",
                approved_by=user_id,
                approved_at=datetime.now(UTC),
            )
            # Flip the gated execution back into the runnable queue. The
            # runtime worker picks it up; we don't dispatch synchronously
            # here because the original caller may have moved on.
            execution = await self.repository.get_execution(approval.execution_id)
            if execution is not None and execution.status == "pending_approval":
                await self.repository.update_execution(execution, status="queued")
            return updated

        if decision == "reject":
            updated = await self.repository.update_approval(
                approval,
                status="rejected",
                approved_by=user_id,
                approved_at=datetime.now(UTC),
                rejection_reason=reason,
            )
            execution = await self.repository.get_execution(approval.execution_id)
            if execution is not None and execution.status == "pending_approval":
                await self.repository.update_execution(
                    execution,
                    status="cancelled",
                    error_message="approval_rejected",
                    completed_at=datetime.now(UTC),
                )
            return updated

        raise ValidationError(
            "approval_decision_invalid",
            "decision must be 'approve' or 'reject'.",
            {"decision": decision},
        )

    # ── Agent ↔ Tool ─────────────────────────────────────────────────

    async def list_agent_tools(
        self, workspace_id: UUID, agent_id: UUID, user_id: UUID
    ) -> list[AgentTool]:
        await self._authorize_agent(workspace_id, agent_id, user_id)
        return await self.repository.list_agent_tools(agent_id)

    async def attach_tool(
        self,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: UUID,
        payload: AttachToolRequest,
    ) -> AgentTool:
        await self._authorize_agent(workspace_id, agent_id, user_id)
        # Tool must be visible to the workspace (own or global).
        tool = await self.repository.get_in_workspace(workspace_id, payload.tool_id)
        if tool is None:
            raise NotFoundError(
                "tool_not_found",
                "Tool does not exist in this workspace.",
                {"tool_id": str(payload.tool_id)},
            )
        existing = await self.repository.get_agent_tool(agent_id, payload.tool_id)
        if existing is not None:
            raise ConflictError(
                "agent_tool_already_attached",
                "This tool is already attached to the agent.",
                {"agent_id": str(agent_id), "tool_id": str(payload.tool_id)},
            )
        return await self.repository.attach_tool(
            agent_id=agent_id,
            tool_id=payload.tool_id,
            is_enabled=payload.is_enabled,
            config=payload.permission.model_dump(),
        )

    async def detach_tool(
        self,
        workspace_id: UUID,
        agent_id: UUID,
        tool_id: UUID,
        user_id: UUID,
    ) -> None:
        await self._authorize_agent(workspace_id, agent_id, user_id)
        removed = await self.repository.detach_tool(agent_id, tool_id)
        if removed == 0:
            raise NotFoundError(
                "agent_tool_not_found",
                "Tool is not attached to this agent.",
                {"agent_id": str(agent_id), "tool_id": str(tool_id)},
            )

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def agent_tool_permission(link: AgentTool) -> AgentToolPermissionConfig:
        return AgentToolPermissionConfig(**(link.config or {}))

    async def _authorize_agent(self, workspace_id: UUID, agent_id: UUID, user_id: UUID) -> Agent:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)
        agent = await self.agent_repository.get_in_workspace(workspace_id, agent_id)
        if agent is None:
            raise NotFoundError(
                "agent_not_found",
                "Agent does not exist in this workspace.",
                {"workspace_id": str(workspace_id), "agent_id": str(agent_id)},
            )
        return agent
