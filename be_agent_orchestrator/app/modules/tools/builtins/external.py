"""External-service builtins: real network calls, not mock data.

- ``web_search`` — Tavily API (https://tavily.com). Free tier ~1k queries/mo.
- ``telegram_send`` — Telegram Bot API ``sendMessage``.

Credentials are **strictly per-tool** — read from ``ctx.auth`` (populated
from the tool row's ``auth_config`` JSONB by the executor). There is no
env fallback: if the tool has no key, the step fails. Same rule as agents'
LLM keys living only on ``agents.provider_credentials``.

Importing this module registers all handlers with the builtin registry.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.modules.tools.builtins import BuiltinContext, BuiltinResult, register

log = structlog.get_logger("tools.external")

TAVILY_SEARCH_URL = "https://api.tavily.com/search"
TELEGRAM_API_BASE = "https://api.telegram.org"
GITHUB_API_BASE = "https://api.github.com"
HN_API_BASE = "https://hacker-news.firebaseio.com/v0"


def _github_headers(token: str | None) -> dict[str, str]:
    """Required headers per GitHub REST API docs.

    User-Agent is mandatory or GitHub returns 403. Authorization upgrades
    the rate limit from 60/hr (unauth) to 5000/hr.
    """

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "yuno-agent-orchestrator",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


@register(
    "web_search",
    description=(
        "Search the public web for up-to-date information. Returns the top "
        "results as a list of {title, url, snippet}. Use when the user asks "
        "for current facts, news, or anything the model wouldn't know from "
        "training data."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "max_results": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": 5,
                "description": "How many results to return.",
            },
        },
        "required": ["query"],
    },
    category="research",
)
async def _web_search(inputs: dict[str, Any], ctx: BuiltinContext) -> BuiltinResult:
    # Strict per-tool BYOK. No env fallback; step fails if missing.
    api_key = ctx.auth.get("api_key")
    if not api_key:
        return BuiltinResult(
            success=False,
            error="`auth_config.api_key` is required on this tool. Get one at https://tavily.com",
        )

    query = (inputs.get("query") or "").strip()
    if not query:
        return BuiltinResult(success=False, error="query is required")

    max_results = max(1, min(int(inputs.get("max_results") or 5), 10))
    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        # Plain results without Tavily's own LLM-generated answer — we let
        # the calling agent synthesize. Includes snippets, which is what
        # the agent needs to ground a response.
        "include_answer": False,
        "search_depth": "basic",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(TAVILY_SEARCH_URL, json=payload)
        if response.status_code >= 400:
            return BuiltinResult(
                success=False,
                error=f"tavily {response.status_code}: {response.text[:200]}",
            )
        body = response.json()
    except httpx.HTTPError as exc:
        return BuiltinResult(success=False, error=f"tavily request failed: {exc}")

    raw_results = body.get("results") or []
    results = [
        {
            "title": r.get("title"),
            "url": r.get("url"),
            "snippet": r.get("content"),
        }
        for r in raw_results
    ]
    return BuiltinResult(success=True, data={"query": query, "results": results})


@register(
    "telegram_send",
    description=(
        "Send a Telegram message via the bot. Use to reply to a user who "
        "messaged the bot. Pass `chat_id` (the id you received with the "
        "inbound message) and `text`. Markdown is supported."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "chat_id": {
                # Single primitive type — Gemini's FunctionDeclaration rejects
                # JSON-Schema unions like `["string", "integer"]` even though
                # OpenAI / Groq accept them. Telegram chat ids are always
                # signed 64-bit ints (negative for groups/channels).
                "type": "integer",
                "description": "Telegram chat id from the inbound message.",
            },
            "text": {
                "type": "string",
                "description": "Message body. Plain text or Telegram Markdown.",
            },
            "parse_mode": {
                "type": "string",
                "enum": ["Markdown", "MarkdownV2", "HTML"],
                "default": "Markdown",
            },
        },
        "required": ["chat_id", "text"],
    },
    category="messaging",
)
async def _telegram_send(inputs: dict[str, Any], ctx: BuiltinContext) -> BuiltinResult:
    # Strict per-tool BYOK. No env fallback; step fails if missing.
    token = ctx.auth.get("bot_token")
    if not token:
        return BuiltinResult(
            success=False,
            error="`auth_config.bot_token` is required on this tool.",
        )

    chat_id = inputs.get("chat_id")
    text = (inputs.get("text") or "").strip()
    if chat_id in (None, "") or not text:
        return BuiltinResult(success=False, error="chat_id and text are required")

    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    body = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": inputs.get("parse_mode") or "Markdown",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=body)
        data = response.json()
    except httpx.HTTPError as exc:
        return BuiltinResult(success=False, error=f"telegram request failed: {exc}")

    if not data.get("ok"):
        return BuiltinResult(
            success=False,
            error=f"telegram error: {data.get('description') or response.status_code}",
        )

    msg = data.get("result") or {}
    return BuiltinResult(
        success=True,
        data={
            "message_id": msg.get("message_id"),
            "chat_id": (msg.get("chat") or {}).get("id"),
            "date": msg.get("date"),
        },
    )


# ──────────────────────────────────────────────────────────────────────
# GitHub Concierge — real public-API tools (no mocks)
# ──────────────────────────────────────────────────────────────────────
#
# All five tools share the same auth shape: optional ``token`` in
# ``auth_config`` upgrades the rate limit from 60 to 5000 req/hr. Without
# a token they still work for public repos at the lower limit.
#
# Output shape is intentionally uniform across tools — ``{items: [...]}``
# of {title, url, ...} — so the synthesizer agent can treat them
# interchangeably.


@register(
    "github_list_prs",
    description=(
        "List recent pull requests on a public GitHub repo. Use when the user "
        "asks about active or recent PRs. Returns title + url + state + "
        "author + created_at for the top results."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "owner": {"type": "string", "description": "GitHub org or user, e.g. `facebook`."},
            "repo": {"type": "string", "description": "Repo name, e.g. `react`."},
            "state": {
                "type": "string",
                "enum": ["open", "closed", "all"],
                "default": "open",
                "description": "Filter by PR state.",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 30,
                "default": 10,
            },
        },
        "required": ["owner", "repo"],
    },
    category="research",
)
async def _github_list_prs(inputs: dict[str, Any], ctx: BuiltinContext) -> BuiltinResult:
    owner = (inputs.get("owner") or "").strip()
    repo = (inputs.get("repo") or "").strip()
    if not owner or not repo:
        return BuiltinResult(success=False, error="owner and repo are required")

    state = inputs.get("state") or "open"
    limit = max(1, min(int(inputs.get("limit") or 10), 30))
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls"
    params = {"state": state, "per_page": limit, "sort": "updated", "direction": "desc"}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=_github_headers(ctx.auth.get("token")), params=params)
    except httpx.HTTPError as exc:
        return BuiltinResult(success=False, error=f"github request failed: {exc}")

    if response.status_code >= 400:
        return BuiltinResult(
            success=False,
            error=f"github {response.status_code}: {response.text[:200]}",
        )

    raw = response.json() or []
    items = [
        {
            "title": pr.get("title"),
            "url": pr.get("html_url"),
            "number": pr.get("number"),
            "state": pr.get("state"),
            "author": (pr.get("user") or {}).get("login"),
            "created_at": pr.get("created_at"),
            "updated_at": pr.get("updated_at"),
            "draft": pr.get("draft", False),
        }
        for pr in raw[:limit]
    ]
    return BuiltinResult(success=True, data={"owner": owner, "repo": repo, "items": items})


@register(
    "github_list_issues",
    description=(
        "List issues on a public GitHub repo, optionally filtered by label "
        "(e.g. `good first issue`, `help wanted`). Use when the user asks "
        "for things to work on or for open bugs."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "owner": {"type": "string"},
            "repo": {"type": "string"},
            "labels": {
                "type": "string",
                "description": "Comma-separated label filter, e.g. `good first issue,help wanted`.",
            },
            "state": {
                "type": "string",
                "enum": ["open", "closed", "all"],
                "default": "open",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 30,
                "default": 10,
            },
        },
        "required": ["owner", "repo"],
    },
    category="research",
)
async def _github_list_issues(inputs: dict[str, Any], ctx: BuiltinContext) -> BuiltinResult:
    owner = (inputs.get("owner") or "").strip()
    repo = (inputs.get("repo") or "").strip()
    if not owner or not repo:
        return BuiltinResult(success=False, error="owner and repo are required")

    state = inputs.get("state") or "open"
    labels = (inputs.get("labels") or "").strip()
    limit = max(1, min(int(inputs.get("limit") or 10), 30))
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues"
    params: dict[str, Any] = {"state": state, "per_page": limit, "sort": "updated"}
    if labels:
        params["labels"] = labels

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=_github_headers(ctx.auth.get("token")), params=params)
    except httpx.HTTPError as exc:
        return BuiltinResult(success=False, error=f"github request failed: {exc}")

    if response.status_code >= 400:
        return BuiltinResult(
            success=False,
            error=f"github {response.status_code}: {response.text[:200]}",
        )

    raw = response.json() or []
    # GitHub's /issues endpoint returns PRs too; filter them out so the
    # caller only sees real issues. PRs have `pull_request` set.
    items = [
        {
            "title": it.get("title"),
            "url": it.get("html_url"),
            "number": it.get("number"),
            "state": it.get("state"),
            "labels": [lbl.get("name") for lbl in it.get("labels") or []],
            "comments": it.get("comments"),
            "created_at": it.get("created_at"),
        }
        for it in raw
        if "pull_request" not in it
    ][:limit]
    return BuiltinResult(success=True, data={"owner": owner, "repo": repo, "items": items})


@register(
    "github_list_releases",
    description=(
        "List recent releases (tags + release notes) for a public GitHub repo. "
        "Use when the user asks 'what's new' / 'changelog' / 'latest version'."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "owner": {"type": "string"},
            "repo": {"type": "string"},
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": 5,
            },
        },
        "required": ["owner", "repo"],
    },
    category="research",
)
async def _github_list_releases(inputs: dict[str, Any], ctx: BuiltinContext) -> BuiltinResult:
    owner = (inputs.get("owner") or "").strip()
    repo = (inputs.get("repo") or "").strip()
    if not owner or not repo:
        return BuiltinResult(success=False, error="owner and repo are required")

    limit = max(1, min(int(inputs.get("limit") or 5), 10))
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases"
    params = {"per_page": limit}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=_github_headers(ctx.auth.get("token")), params=params)
    except httpx.HTTPError as exc:
        return BuiltinResult(success=False, error=f"github request failed: {exc}")

    if response.status_code >= 400:
        return BuiltinResult(
            success=False,
            error=f"github {response.status_code}: {response.text[:200]}",
        )

    raw = response.json() or []
    items = [
        {
            "title": rel.get("name") or rel.get("tag_name"),
            "tag": rel.get("tag_name"),
            "url": rel.get("html_url"),
            # Body can be huge; truncate so the LLM context stays reasonable.
            "summary": (rel.get("body") or "")[:600],
            "published_at": rel.get("published_at"),
            "prerelease": rel.get("prerelease", False),
        }
        for rel in raw[:limit]
    ]
    return BuiltinResult(success=True, data={"owner": owner, "repo": repo, "items": items})


@register(
    "github_search_repos",
    description=(
        "Search GitHub for repositories matching a query. Use when the user "
        "asks 'find me repos about X' or doesn't know the exact owner/repo. "
        "Sorts by stars by default."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query. Use GitHub search qualifiers like `language:python` for filters.",
            },
            "sort": {
                "type": "string",
                "enum": ["stars", "updated", "forks"],
                "default": "stars",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "default": 10,
            },
        },
        "required": ["query"],
    },
    category="research",
)
async def _github_search_repos(inputs: dict[str, Any], ctx: BuiltinContext) -> BuiltinResult:
    query = (inputs.get("query") or "").strip()
    if not query:
        return BuiltinResult(success=False, error="query is required")

    sort = inputs.get("sort") or "stars"
    limit = max(1, min(int(inputs.get("limit") or 10), 20))
    url = f"{GITHUB_API_BASE}/search/repositories"
    params = {"q": query, "sort": sort, "order": "desc", "per_page": limit}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=_github_headers(ctx.auth.get("token")), params=params)
    except httpx.HTTPError as exc:
        return BuiltinResult(success=False, error=f"github request failed: {exc}")

    if response.status_code >= 400:
        return BuiltinResult(
            success=False,
            error=f"github {response.status_code}: {response.text[:200]}",
        )

    raw = response.json() or {}
    items = [
        {
            "title": r.get("full_name"),
            "url": r.get("html_url"),
            "description": r.get("description"),
            "stars": r.get("stargazers_count"),
            "forks": r.get("forks_count"),
            "language": r.get("language"),
            "updated_at": r.get("updated_at"),
        }
        for r in (raw.get("items") or [])[:limit]
    ]
    return BuiltinResult(success=True, data={"query": query, "items": items})


# ──────────────────────────────────────────────────────────────────────
# Hacker News pulse — public read-only API, no auth
# ──────────────────────────────────────────────────────────────────────


@register(
    "hn_top_stories",
    description=(
        "Fetch the current top stories from Hacker News. Use when the user "
        "asks 'what's trending', 'top on HN', or wants tech industry pulse. "
        "Returns title + url + score + comment count."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "default": 10,
                "description": "How many top stories to fetch.",
            },
            "min_score": {
                "type": "integer",
                "minimum": 0,
                "default": 0,
                "description": "Drop stories below this karma score.",
            },
        },
    },
    category="research",
)
async def _hn_top_stories(inputs: dict[str, Any], ctx: BuiltinContext) -> BuiltinResult:  # noqa: ARG001
    limit = max(1, min(int(inputs.get("limit") or 10), 20))
    min_score = max(0, int(inputs.get("min_score") or 0))

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Step 1: list of top story ids (sorted by HN's ranking algo).
            ids_resp = await client.get(f"{HN_API_BASE}/topstories.json")
            ids_resp.raise_for_status()
            ids: list[int] = (ids_resp.json() or [])[: limit * 2]  # over-fetch for min_score filter

            # Step 2: hydrate each id in parallel.
            async def _fetch_item(item_id: int) -> dict[str, Any] | None:
                r = await client.get(f"{HN_API_BASE}/item/{item_id}.json")
                if r.status_code != 200:
                    return None
                return r.json()  # type: ignore[no-any-return]

            import asyncio  # noqa: PLC0415 — local import keeps the module load light

            items_raw = await asyncio.gather(*[_fetch_item(i) for i in ids])
    except httpx.HTTPError as exc:
        return BuiltinResult(success=False, error=f"hackernews request failed: {exc}")

    items = []
    for it in items_raw:
        if not it or it.get("score", 0) < min_score:
            continue
        items.append(
            {
                "title": it.get("title"),
                "url": it.get("url") or f"https://news.ycombinator.com/item?id={it.get('id')}",
                "score": it.get("score"),
                "comments": it.get("descendants"),
                "author": it.get("by"),
                "time": it.get("time"),
            }
        )
        if len(items) >= limit:
            break

    return BuiltinResult(success=True, data={"items": items})


__all__: list[str] = []
