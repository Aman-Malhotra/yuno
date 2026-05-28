"""Workflow executor — walks ``compiled_graph`` and drives each node.

Not langgraph-backed for v1: a simple in-process walker is easier to
debug and gives us everything the seeded workflows need (linear flow +
conditional edges). Swap in langgraph's ``StateGraph`` later when we
need parallel branches, durable checkpoints, or sub-graphs.

The executor is one-shot — instantiate per ``WorkflowRun``, call
``run()`` once. It owns side effects on the run row (status, started_at,
completed_at, totals, output) and writes all per-step state via
``RunPersistence``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agents.service import AgentService
from app.modules.memory.service import MemoryService
from app.modules.messages.repository import AgentMessageRepository
from app.modules.runs.models import WorkflowRun
from app.modules.runtime.conditions import matches
from app.modules.runtime import memory_hooks
from app.modules.runtime.events import RunPersistence
from app.modules.runtime.nodes import (
    NodeContext,
    NodeResult,
    NodeRunnerError,
    run_agent,
    run_passthrough,
    run_tool,
)
from app.modules.runtime.state import RunState
from app.modules.tools.executor import ToolExecutor
from app.modules.tools.repository import ToolRepository
from app.modules.workflows.models import Workflow

log = structlog.get_logger("runtime.executor")

# Hard ceiling so a cyclic graph or runaway condition can't burn a worker.
MAX_NODE_VISITS = 200


class ExecutorError(Exception):
    """Structural issue that prevents the executor from running at all
    (missing entry, unknown node id, etc). Distinct from per-node failures."""


class Executor:
    def __init__(
        self,
        db: AsyncSession,
        run: WorkflowRun,
        workflow: Workflow,
        *,
        agent_service: AgentService,
        tool_executor: ToolExecutor,
        tool_repository: ToolRepository,
        memory_service: MemoryService | None = None,
        message_repository: AgentMessageRepository | None = None,
    ) -> None:
        self.db = db
        # ``run`` is the table row, ``run()`` is the executor's entry method
        # — store the row under ``workflow_run`` to avoid the name collision.
        self.workflow_run = run
        self.workflow = workflow
        self.agent_service = agent_service
        self.tool_executor = tool_executor
        self.tool_repository = tool_repository
        # Memory wiring is optional so test runs / unit fixtures don't need
        # to spin up mem0. When omitted, agent nodes skip the hooks entirely.
        self.memory_service = memory_service
        self.message_repository = message_repository or AgentMessageRepository(db)
        self.state = RunState(run.input or {})
        self.persistence = RunPersistence(db, run)

    async def run(self) -> None:
        compiled: dict[str, Any] = self.workflow.compiled_graph or {}
        nodes_by_id: dict[str, dict[str, Any]] = {n["id"]: n for n in compiled.get("nodes", [])}
        entry = compiled.get("entry")
        if not entry or entry not in nodes_by_id:
            raise ExecutorError("workflow has no start node — refusing to run")

        await self.persistence.emit(
            "run.started",
            payload={"input": self.state.as_dict()},
        )

        current: str | None = entry
        visited = 0
        while current is not None:
            if visited >= MAX_NODE_VISITS:
                raise ExecutorError(f"exceeded {MAX_NODE_VISITS} node visits — likely a cycle")
            visited += 1

            node = nodes_by_id.get(current)
            if node is None:
                raise ExecutorError(f"unknown node id in compiled_graph: {current!r}")

            await self._execute_node(node)

            if node.get("type") == "end":
                break

            current = self._next_node(current, compiled)

        await self._finalize_success()

    # ──────────────────────────────────────────────────────────────────
    # Single-node execution + persistence
    # ──────────────────────────────────────────────────────────────────

    async def _execute_node(self, node: dict[str, Any]) -> None:
        node_id: str = node["id"]
        node_type: str = node.get("type", "unknown")
        label = node.get("label")
        snapshot = self.state.as_dict()

        row = await self.persistence.start_node(
            node_id=node_id,
            node_type=node_type,
            node_label=label,
            agent_id=_as_uuid(node.get("agent_id")),
            tool_id=_as_uuid(node.get("tool_id")),
            input_state=snapshot,
        )
        await self.persistence.emit(
            "node.started",
            node_id=node_id,
            run_node_id=row.id,
            agent_id=row.agent_id,
            tool_id=row.tool_id,
            payload={"node_type": node_type},
        )

        ctx = NodeContext(
            db=self.db,
            workspace_id=self.workflow_run.workspace_id,
            run_id=self.workflow_run.id,
            run_node_id=row.id,
            state=self.state,
            graph_node_id=node_id,
        )

        try:
            result = await self._dispatch(node, ctx)
        except NodeRunnerError as err:
            # Carry whatever the runner managed to collect before failing
            # (e.g. partial tool_call_log from an agent that hit hop limit).
            await self._record_failure(row, node_id, str(err), partial_output=err.partial_output)
            raise
        except Exception as exc:
            log.exception(
                "runtime.node.unhandled", node_id=node_id, run_id=str(self.workflow_run.id)
            )
            await self._record_failure(row, node_id, f"unhandled: {exc}")
            raise

        # Merge the node's output back into state under its id and roll up tokens.
        self.state.set(node_id, result.output)
        self.workflow_run.total_input_tokens += result.tokens.input_tokens
        self.workflow_run.total_output_tokens += result.tokens.output_tokens
        await self.db.commit()

        await self.persistence.complete_node(row, status="completed", output=result.output)
        await self.persistence.emit(
            "node.completed",
            node_id=node_id,
            run_node_id=row.id,
            agent_id=row.agent_id,
            tool_id=row.tool_id,
            payload={
                "output": result.output,
                "tokens": {
                    "input": result.tokens.input_tokens,
                    "output": result.tokens.output_tokens,
                },
            },
        )

    async def _dispatch(self, node: dict[str, Any], ctx: NodeContext) -> NodeResult:
        node_type = node.get("type")
        if node_type == "agent":
            return await run_agent(
                node,
                ctx,
                agent_service=self.agent_service,
                tool_executor=self.tool_executor,
                tool_repository=self.tool_repository,
                persistence=self.persistence,
                memory_service=self.memory_service,
                message_repository=self.message_repository,
                workflow_id=self.workflow.id,
            )
        if node_type == "tool":
            return await run_tool(node, ctx, tool_executor=self.tool_executor)
        if node_type in ("start", "end", "condition"):
            # Condition nodes are markers — the real branching happens at
            # the source's outgoing ``conditional_edges`` (see _next_node).
            return await run_passthrough(node, ctx)
        raise NodeRunnerError(f"unsupported node type: {node_type!r}")

    async def _record_failure(
        self,
        row: Any,
        node_id: str,
        error_message: str,
        *,
        partial_output: dict[str, Any] | None = None,
    ) -> None:
        await self.persistence.complete_node(
            row,
            status="failed",
            output=partial_output,
            error_message=error_message,
            error_details={"node_id": node_id},
        )
        await self.persistence.emit(
            "node.failed",
            node_id=node_id,
            run_node_id=row.id,
            payload={"error": error_message},
        )
        self.workflow_run.status = "failed"
        self.workflow_run.error_message = error_message
        self.workflow_run.completed_at = datetime.now(UTC)
        self.workflow_run.output = self.state.as_dict()
        await self.db.commit()
        await self.persistence.emit(
            "run.failed",
            payload={"error": error_message, "failed_node": node_id},
        )

    async def _finalize_success(self) -> None:
        self.workflow_run.status = "completed"
        self.workflow_run.completed_at = datetime.now(UTC)
        self.workflow_run.output = self.state.as_dict()
        await self.db.commit()
        await self.persistence.emit(
            "run.completed",
            payload={"output": self.state.as_dict()},
        )

        # Single mem0 extraction per run, AFTER everything else commits.
        # Per-agent persistence would push N memories for one user turn —
        # this hook collapses to one (first inbound + last outbound).
        # Failures are swallowed inside the hook; the run already
        # succeeded and shouldn't be retroactively marked failed.
        if self.memory_service is not None:
            await memory_hooks.persist_to_memory_once(
                state=self.state,
                workspace_id=self.workflow_run.workspace_id,
                workflow_id=self.workflow.id,
                run_id=self.workflow_run.id,
                message_repository=self.message_repository,
                memory_service=self.memory_service,
            )

    # ──────────────────────────────────────────────────────────────────
    # Routing — pick the next node from outgoing edges
    # ──────────────────────────────────────────────────────────────────

    def _next_node(self, source: str, compiled: dict[str, Any]) -> str | None:
        # Conditional first — branches are an ordered list; first match wins.
        for ce in compiled.get("conditional_edges", []):
            if ce.get("source") != source:
                continue
            for branch in ce.get("branches", []):
                if matches(branch.get("condition"), self.state):
                    target = branch.get("target")
                    return str(target) if target is not None else None
            # No branch matched — dead end. The run completes here.
            return None

        # Simple edges — first one wins. Parallel fan-out is not supported in v1.
        for edge in compiled.get("edges", []):
            if edge.get("source") == source:
                target = edge.get("target")
                return str(target) if target is not None else None

        return None


def _as_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None
