---
title: OpenAPI Spec Standard
impact: CRITICAL
impactDescription: One consistent spec across every endpoint = frontend codegen works, /docs is self-describing, future contributors copy a known pattern
tags: api, openapi, swagger, contract
---

## OpenAPI Spec Standard

FastAPI auto-generates OpenAPI from the routes, but a *generated* spec is only useful if every route declares the same things in the same way. The project enforces a single shape so the resulting spec is stable, codegen-friendly, and self-documenting.

### Every route must declare

```python
@router.<verb>(
    "<path>",
    response_model=<Pydantic schema>,             # 1
    status_code=status.HTTP_<code>,               # 2
    summary="<one short sentence>",               # 3
    description="<longer markdown explanation>",  # 4 — or rich docstring
    operation_id="<tag>_<verb>_<noun>",           # 5
    tags=["<tag from TAGS_METADATA>"],            # 6 (usually on the APIRouter)
    responses=auth_required_responses(...) | {...per-route extras...},  # 7
)
async def handler(...) -> <ResponseModel>:
    ...
```

| # | Field             | Why                                                            |
|---|-------------------|----------------------------------------------------------------|
| 1 | `response_model`  | Drives the success schema in OpenAPI; prunes extras on the wire |
| 2 | `status_code`     | Explicit, not implicit 200                                     |
| 3 | `summary`         | Renders as the route title in `/docs`                          |
| 4 | `description`     | Renders as the route body — explain auth, side effects, errors |
| 5 | `operation_id`    | Stable, `<tag>_<verb>_<noun>` so codegen names are readable    |
| 6 | `tags`            | Group in `/docs`; one canonical list (see `TAGS_METADATA`)     |
| 7 | `responses`       | Document error shapes — frontend switches on `error.code`      |

### Error envelope is a real schema

Every non-2xx response is the `ErrorEnvelope` from `app/core/schemas.py`:

```json
{
  "error": {
    "code": "AGENT_NOT_FOUND",
    "message": "Agent not found",
    "details": { "agent_id": "01HZ..." }
  }
}
```

This shape lives in OpenAPI **components/schemas** — the global exception handler emits it, and every route's `responses=` references it via `COMMON_ERROR_RESPONSES`. Wire format == OpenAPI schema, byte for byte.

### Reusable error response sets

Defined once in `app/core/openapi.py`:

```python
COMMON_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorEnvelope, "description": "Bad request — malformed input"},
    401: {"model": ErrorEnvelope, "description": "Missing or invalid bearer token"},
    403: {"model": ErrorEnvelope, "description": "Authenticated but not allowed"},
    404: {"model": ErrorEnvelope, "description": "Resource not found"},
    409: {"model": ErrorEnvelope, "description": "Conflict with existing state"},
    422: {"model": ErrorEnvelope, "description": "Validation error on request payload"},
    500: {"model": ErrorEnvelope, "description": "Internal server error"},
}

def auth_required_responses(*extra_codes: int) -> dict[int | str, dict[str, Any]]: ...
def public_responses(*extra_codes: int) -> dict[int | str, dict[str, Any]]: ...
```

Use them via merge:

```python
responses=auth_required_responses(404, 409)   # 401/403/422/500 + 404 + 409
responses=public_responses(401)               # 400/422/500 + 401
```

### Bearer auth as a global security scheme

`customize_openapi` injects:

```yaml
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

Routes that use `Depends(get_current_user)` automatically pick up the security requirement. Public routes (login, refresh, health) don't.

### Tag metadata is a single source of truth

```python
TAGS_METADATA: list[dict[str, str]] = [
    {"name": "auth", "description": "Login, refresh, logout, and current-user lookup."},
    {"name": "agents", "description": "Agent CRUD and per-agent test runs."},
    # ...
]
```

Add a new tag here before using it in any router. No free-text tags — they fragment `/docs` and break codegen.

### Pydantic models carry examples

Add `model_config = ConfigDict(json_schema_extra={"examples": [...]})` to every request/response schema. They show up in `/docs` and make the spec usable as a contract.

```python
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    refresh_expires_in: int

    model_config = ConfigDict(
        json_schema_extra={"examples": [{
            "access_token": "eyJhbGc...",
            "refresh_token": "xQ7aD2...",
            "token_type": "bearer",
            "expires_in": 43200,
            "refresh_expires_in": 2592000,
        }]}
    )
```

### Operation IDs — codegen-friendly naming

Pattern: `<tag>_<http_verb_lowercase>_<noun_or_action>`.

| Route                                | operation_id          |
|--------------------------------------|-----------------------|
| `POST /auth/login`                   | `auth_post_login`     |
| `POST /auth/refresh`                 | `auth_post_refresh`   |
| `GET  /auth/me`                      | `auth_get_me`         |
| `POST /agents`                       | `agents_post_create`  |
| `GET  /agents/{agent_id}`            | `agents_get_by_id`    |
| `POST /agents/{agent_id}/test`       | `agents_post_test`    |
| `POST /workflows/{wid}/validate`     | `workflows_post_validate` |

Stable IDs mean the auto-generated TS client doesn't churn on every route rename.

### Export the spec to disk

`make openapi` runs `scripts/export_openapi.py` which writes `docs/openapi.json`. CI / the frontend codegen consume that file — they don't need a live server.

### Bad — missing metadata, implicit 200, no error responses

```python
# ❌ No status_code, no summary, no responses, no operation_id, no description
@router.post("/")
async def create_agent(payload: CreateAgentRequest):
    ...
```

`/docs` will show "POST /" with no title, no error documentation, and an opaque generated `operation_id`. Frontend codegen produces `createAgentApiV1AgentsPost`.

### Bad — bespoke error response shape per route

```python
# ❌ Three routes, three error shapes — UI can't reuse parsing
return JSONResponse(status_code=404, content={"message": "not found"})
return JSONResponse(status_code=404, content={"err": "missing", "agent_id": id_})
raise HTTPException(404, "agent gone")
```

Always raise an `AppError` subclass and let the global handler emit `ErrorEnvelope`.

### Bad — `responses=` with raw dicts

```python
# ❌ Loses the schema reference; frontend gets `application/json` with no model
responses={404: {"description": "not found"}}
```

Use the helpers — they attach `model=ErrorEnvelope` so the OpenAPI consumer sees the full structure.

### Checklist for every new endpoint

- [ ] `response_model=` set (or `status_code=204` with `None` return)
- [ ] `status_code=` explicit
- [ ] `summary=` (≤ 1 sentence) + `description=` (markdown ok)
- [ ] `operation_id=` follows `<tag>_<verb>_<noun>` convention
- [ ] `tags=` from `TAGS_METADATA`
- [ ] `responses=` from `auth_required_responses(...)` or `public_responses(...)` with per-route additions
- [ ] Pydantic request/response models have `json_schema_extra={"examples": [...]}`
- [ ] Domain errors raised as `AppError` subclasses (never `HTTPException`)
- [ ] `make openapi` regenerated and committed if the contract changed

See: [[api-response-shapes]], [[api-error-handling]], [[api-versioning-router]]
