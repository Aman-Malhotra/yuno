import re
import secrets
from uuid import UUID

import structlog
from sqlalchemy import select

from app.core.errors import NotFoundError, ValidationError
from app.modules.agents.models import Agent
from app.modules.workflows.compiler import compile_graph, validate_for_publish
from app.modules.workflows.models import Workflow
from app.modules.workflows.repository import WorkflowRepository
from app.modules.workflows.schemas import (
    CreateWorkflowRequest,
    UpdateWorkflowGraphRequest,
    UpdateWorkflowRequest,
    WorkflowGraph,
    WorkflowGraphNode,
)
from app.modules.workspaces.service import WorkspaceService

log = structlog.get_logger("workflows")


def _slugify(text: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return base[:100] or "workflow"


def _empty_graph() -> WorkflowGraph:
    """Default canvas: a single `start` node so the builder has somewhere to attach edges."""

    return WorkflowGraph(
        nodes=[
            WorkflowGraphNode(
                id="start",
                type="start",
                position={"x": 0.0, "y": 0.0},
                data={"label": "Start", "config": {}},
            )
        ],
        edges=[],
    )


class WorkflowService:
    def __init__(
        self,
        repository: WorkflowRepository,
        workspace_service: WorkspaceService,
    ) -> None:
        self.repository = repository
        self.workspace_service = workspace_service

    # ──────────────────────────────────────────────────────────────────
    # Read
    # ──────────────────────────────────────────────────────────────────

    async def list_in_workspace_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[Workflow], int]:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)
        return await self.repository.list_in_workspace(workspace_id, page=page, page_size=page_size)

    async def get_in_workspace_for_user(
        self,
        workspace_id: UUID,
        workflow_id: UUID,
        user_id: UUID,
    ) -> Workflow:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)
        workflow = await self.repository.get_in_workspace(workspace_id, workflow_id)
        if workflow is None:
            raise NotFoundError(
                "workflow_not_found",
                "Workflow does not exist in this workspace.",
                {"workspace_id": str(workspace_id), "workflow_id": str(workflow_id)},
            )
        return workflow

    # ──────────────────────────────────────────────────────────────────
    # Write
    # ──────────────────────────────────────────────────────────────────

    async def create_in_workspace_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
        payload: CreateWorkflowRequest,
    ) -> Workflow:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)

        graph = payload.graph or _empty_graph()
        await self._validate_agent_refs(workspace_id, graph)

        slug = f"{_slugify(payload.name)}-{secrets.token_hex(3)}"
        compiled = compile_graph(graph)

        workflow = await self.repository.create(
            workspace_id=workspace_id,
            created_by=user_id,
            name=payload.name,
            slug=slug,
            description=payload.description,
            graph_json=graph.model_dump(mode="json"),
            compiled_graph=compiled,
            settings=payload.settings,
        )
        log.info(
            "workflow.created",
            workflow_id=str(workflow.id),
            workspace_id=str(workspace_id),
            created_by=str(user_id),
            node_count=len(graph.nodes),
            edge_count=len(graph.edges),
        )
        return workflow

    async def update_in_workspace_for_user(
        self,
        workspace_id: UUID,
        workflow_id: UUID,
        user_id: UUID,
        payload: UpdateWorkflowRequest,
    ) -> Workflow:
        workflow = await self.get_in_workspace_for_user(workspace_id, workflow_id, user_id)

        updates: dict[str, object] = {}
        if payload.name is not None:
            updates["name"] = payload.name
        if payload.description is not None:
            updates["description"] = payload.description
        if payload.settings is not None:
            updates["settings"] = payload.settings

        if payload.status is not None:
            if payload.status == "published":
                # Strict structural checks gate the published state — autosave
                # can stay relaxed, but you can't ship a half-wired graph.
                current_graph = WorkflowGraph.model_validate(
                    workflow.graph_json or {"nodes": [], "edges": []}
                )
                issues = validate_for_publish(current_graph)
                if issues:
                    raise ValidationError(
                        "workflow_not_publishable",
                        "Workflow has structural issues that must be fixed before publishing.",
                        {"issues": [i.to_dict() for i in issues]},
                    )
            updates["status"] = payload.status

        if not updates:
            return workflow

        workflow = await self.repository.update(workflow, **updates)
        log.info(
            "workflow.updated",
            workflow_id=str(workflow.id),
            workspace_id=str(workspace_id),
            actor_user_id=str(user_id),
            fields=list(updates),
        )
        return workflow

    async def update_graph_in_workspace_for_user(
        self,
        workspace_id: UUID,
        workflow_id: UUID,
        user_id: UUID,
        payload: UpdateWorkflowGraphRequest,
    ) -> Workflow:
        """Autosave path — replaces the entire graph and re-compiles.

        Permissive: an in-progress graph (no end node, agent nodes without
        an `agentId`) is allowed here. Agent refs that *are* set must
        belong to this workspace — that's the only hard check, because a
        cross-workspace agent id is almost certainly stale state from a
        copy-pasted JSON, not user intent.
        """

        workflow = await self.get_in_workspace_for_user(workspace_id, workflow_id, user_id)

        graph = payload.graph
        await self._validate_agent_refs(workspace_id, graph)

        compiled = compile_graph(graph)
        workflow = await self.repository.update(
            workflow,
            graph_json=graph.model_dump(mode="json"),
            compiled_graph=compiled,
        )
        log.info(
            "workflow.graph_updated",
            workflow_id=str(workflow.id),
            workspace_id=str(workspace_id),
            actor_user_id=str(user_id),
            node_count=len(graph.nodes),
            edge_count=len(graph.edges),
        )
        return workflow

    async def soft_delete_in_workspace_for_user(
        self,
        workspace_id: UUID,
        workflow_id: UUID,
        user_id: UUID,
    ) -> None:
        workflow = await self.get_in_workspace_for_user(workspace_id, workflow_id, user_id)
        await self.repository.soft_delete(workflow)
        log.info(
            "workflow.deleted",
            workflow_id=str(workflow.id),
            workspace_id=str(workspace_id),
            actor_user_id=str(user_id),
            mode="soft",
        )

    # ──────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────

    async def _validate_agent_refs(self, workspace_id: UUID, graph: WorkflowGraph) -> None:
        """Reject saves that reference agents outside this workspace.

        Agent ids set to ``None`` are allowed — the builder commonly drops
        an empty agent node first and fills the reference later.
        """

        agent_ids: set[UUID] = set()
        for node in graph.nodes:
            if node.type != "agent":
                continue
            raw = (
                (node.data.get("config") or {}).get("agentId")
                if isinstance(node.data, dict)
                else None
            )
            if not raw:
                continue
            try:
                agent_ids.add(UUID(str(raw)))
            except ValueError as err:
                raise ValidationError(
                    "invalid_agent_ref",
                    f"Node {node.id!r} has a non-UUID agentId.",
                    {"node_id": node.id, "agent_id": raw},
                ) from err

        if not agent_ids:
            return

        stmt = select(Agent.id).where(
            Agent.workspace_id == workspace_id,
            Agent.id.in_(agent_ids),
            Agent.deleted_at.is_(None),
        )
        rows = (await self.repository.db.execute(stmt)).scalars().all()
        found = {a for a in rows}
        missing = agent_ids - found
        if missing:
            raise ValidationError(
                "unknown_agent_refs",
                "Workflow references agents that do not belong to this workspace.",
                {"missing_agent_ids": sorted(str(a) for a in missing)},
            )
