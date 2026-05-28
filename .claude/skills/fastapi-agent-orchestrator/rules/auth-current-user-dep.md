---
title: One `get_current_user` Dependency on Every Protected Route
impact: CRITICAL
impactDescription: Centralising auth means there is exactly one place to audit — easy to verify no endpoint leaks
tags: auth, dependencies, fastapi
---

## One `get_current_user` Dependency on Every Protected Route

All authenticated routes pull the current user from a single dependency. No bespoke "check the token here" code in route bodies.

### The dependency

```python
# app/modules/auth/dependencies.py
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.modules.users.models import User
from app.modules.users.repository import UserRepository


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    if credentials is None:
        raise UnauthorizedError("missing_token", "Authentication required")

    payload = decode_access_token(credentials.credentials)
    if payload.get("type") != "access":
        raise UnauthorizedError("invalid_token", "Not an access token")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("invalid_token", "Token missing subject")

    user = await UserRepository(db).get_by_id(user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("user_not_found", "User no longer exists")

    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise PermissionDeniedError("admin_required", "Admin role required")
    return current_user
```

### Usage on routes

```python
@router.get("/", response_model=PageResponse[AgentResponse])
async def list_agents(
    current_user: User = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
):
    items, total = await service.list_agents(current_user.id, page=1, page_size=20)
    return PageResponse(items=[...], total=total, page=1, page_size=20)
```

For admin-only routes:

```python
@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    current_user: User = Depends(require_admin),
    service: AgentService = Depends(get_agent_service),
):
    await service.delete(current_user.id, agent_id)
```

### WebSocket auth

WebSockets don't use the `Authorization` header naturally. Pass the JWT as a query param or a subprotocol; decode it manually in the handler.

```python
# app/modules/monitoring/router.py
@router.websocket("/runs/{run_id}")
async def run_events_ws(
    websocket: WebSocket,
    run_id: str,
    token: str = Query(...),
    manager: ConnectionManager = Depends(get_connection_manager),
    run_service: RunService = Depends(get_run_service),
):
    try:
        payload = decode_access_token(token)
        user_id = payload["sub"]
    except Exception:
        await websocket.close(code=4401)
        return

    run = await run_service.get_run(user_id, run_id)   # permission-checked
    await manager.connect(websocket, run_id)
    try:
        await manager.broadcast_loop(websocket, run_id)
    except WebSocketDisconnect:
        await manager.disconnect(websocket, run_id)
```

### Bad — decoding the JWT inline in each route

```python
# ❌ Repeats logic, easy to forget on a new endpoint
@router.get("/agents")
async def list_agents(authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    payload = jwt.decode(token, ...)
    ...
```

### Bad — pulling user by email from the request body

```python
# ❌ Spoofable; anyone can claim to be anyone
@router.get("/me")
async def me(email: str):
    ...
```

### Rules

- Exactly one `get_current_user` and one `require_admin` in `app/modules/auth/dependencies.py`
- Every protected route has `Depends(get_current_user)` or `Depends(require_admin)`
- WebSockets accept the token as a query param + close with `4401` on auth failure
- Services receive `user_id`, not the full `User`, when only the id is needed — keeps services testable

See: [[auth-jwt-and-refresh]], [[api-dependency-injection]], [[realtime-websocket-redis-pubsub]]
