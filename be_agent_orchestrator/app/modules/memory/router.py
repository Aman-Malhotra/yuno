"""Memory module API — list, graph, delete long-term memories.

All endpoints are workspace-scoped (membership required). The mem0 store
itself is global to the deployment, but we treat memory entries as
visible only to the workspace whose runs produced them by metadata.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.api.deps import get_current_user, get_workspace_service
from app.core.openapi import auth_required_responses
from app.modules.memory.schemas import (
    MemoryGraph,
    MemoryListResponse,
)
from app.modules.memory.service import MemoryService
from app.modules.users.models import User
from app.modules.workspaces.service import WorkspaceService

router = APIRouter(prefix="/workspaces/{workspace_id}/memories", tags=["memories"])


async def _memory_service() -> MemoryService:
    """Single instance per process; mem0 client is lazy-loaded inside."""

    return MemoryService()


@router.get(
    "/",
    response_model=MemoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="List long-term memories for a channel user id",
    description=(
        "Returns every mem0 memory row tagged to `user_id`. The id is the "
        "channel-side stable id (Telegram numeric user id, e.g. `1340821010`). "
        "Optionally filter to a specific `username` so the UI can highlight "
        "renamed accounts without losing history."
    ),
    operation_id="memories_list",
    responses=auth_required_responses(404),
)
async def list_memories(
    workspace_id: UUID = Path(description="Workspace UUID."),
    user_id: str = Query(description="Channel-side stable id (e.g. Telegram user id)."),
    username: str | None = Query(
        default=None,
        description="Optional filter — exact match against `metadata.username`.",
    ),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    memory_service: MemoryService = Depends(_memory_service),
) -> MemoryListResponse:
    await workspace_service.get_role_or_403(workspace_id, current_user.id)

    items = await memory_service.list_for_user(user_id=user_id, limit=limit)
    if username:
        items = [e for e in items if (e.metadata or {}).get("username") == username]
    return MemoryListResponse(items=items, total=len(items))


@router.get(
    "/graph",
    response_model=MemoryGraph,
    status_code=status.HTTP_200_OK,
    summary="Entity-relation graph projection of long-term memories",
    description=(
        "Returns the graph mem0 built from this user's turns — nodes are "
        "entities (people, places, preferences), edges are relations "
        "extracted by the memory LLM. Empty arrays if graph memory is "
        "disabled or nothing has been extracted yet."
    ),
    operation_id="memories_graph",
    responses=auth_required_responses(404),
)
async def memory_graph(
    workspace_id: UUID = Path(description="Workspace UUID."),
    user_id: str = Query(description="Channel-side stable id (e.g. Telegram user id)."),
    current_user: User = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    memory_service: MemoryService = Depends(_memory_service),
) -> MemoryGraph:
    await workspace_service.get_role_or_403(workspace_id, current_user.id)
    return await memory_service.graph_for_user(user_id=user_id)


@router.delete(
    "/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete one long-term memory row",
    description=(
        "Permanently removes a single memory by its mem0 id. Use this when a "
        "memory is stale or wrong — the next turn won't recall it."
    ),
    operation_id="memories_delete",
    responses=auth_required_responses(404),
)
async def delete_memory(
    workspace_id: UUID = Path(description="Workspace UUID."),
    memory_id: str = Path(description="mem0 memory id."),
    current_user: User = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    memory_service: MemoryService = Depends(_memory_service),
) -> None:
    await workspace_service.get_role_or_403(workspace_id, current_user.id)
    ok = await memory_service.delete(memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="memory not found or backend rejected delete")
