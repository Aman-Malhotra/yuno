"""Workspace-scoped cost / token usage endpoint.

GET /workspaces/{ws}/costs/agents — per-agent token roll-up.

Lives in ``runs/`` because the data comes from ``runtime_events`` (the
event stream produced by the workflow executor). If we add per-day or
per-model breakouts later, those endpoints belong here too.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, get_workspace_service
from app.core.openapi import auth_required_responses
from app.modules.runs.costs_repository import CostsRepository
from app.modules.runs.costs_schemas import AgentCostRow, CostsResponse
from app.modules.users.models import User
from app.modules.workspaces.service import WorkspaceService

router = APIRouter(prefix="/workspaces/{workspace_id}/costs", tags=["costs"])


@router.get(
    "/agents",
    response_model=CostsResponse,
    status_code=status.HTTP_200_OK,
    summary="Per-agent token usage roll-up",
    description=(
        "Aggregates token usage from `runtime_events` (event_type = "
        "`node.completed`) grouped by agent. Includes deleted agents — "
        "their tokens are still counted, with `name='deleted-agent'`. "
        "Optionally pass `since=<ISO8601>` to scope to a recent window."
    ),
    operation_id="costs_get_per_agent",
    responses=auth_required_responses(404),
)
async def get_per_agent_costs(
    workspace_id: UUID = Path(description="Workspace UUID."),
    since: datetime | None = Query(
        default=None,
        description="ISO timestamp; only events at/after this point are counted.",
    ),
    current_user: User = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    db: AsyncSession = Depends(get_db_session),
) -> CostsResponse:
    await workspace_service.get_role_or_403(workspace_id, current_user.id)

    repo = CostsRepository(db)
    raw_rows = await repo.per_agent_token_usage(workspace_id, since=since)

    items: list[AgentCostRow] = []
    total_in = 0
    total_out = 0
    for r in raw_rows:
        input_tokens = int(r["input_tokens"] or 0)
        output_tokens = int(r["output_tokens"] or 0)
        items.append(
            AgentCostRow(
                agent_id=r["agent_id"],
                name=r["name"],
                slug=r["slug"],
                model_provider=r["model_provider"],
                model_name=r["model_name"],
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                run_count=int(r["run_count"] or 0),
                last_seen_at=r["last_seen_at"],
            )
        )
        total_in += input_tokens
        total_out += output_tokens

    return CostsResponse(
        items=items,
        total_input_tokens=total_in,
        total_output_tokens=total_out,
        total_tokens=total_in + total_out,
    )
