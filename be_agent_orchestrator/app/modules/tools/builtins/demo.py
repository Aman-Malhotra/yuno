"""Demo builtin handlers for the two showcase workflows.

These mock back-office systems (CRM, content pipeline) so the demo can run
end-to-end without external dependencies. State is in-memory and per-process —
fine for a single-instance demo, not production.

Two state stores:
- ``_TICKETS`` — keyed by ticket_id; used by the Support Triage workflow
- ``_DRAFTS``, ``_CAMPAIGNS``, ``_SCHEDULES`` — used by the Content workflow

Importing this module registers all handlers; that import is done from
``app.modules.tools.builtins.__init__`` so the registry stays auto-populated.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.modules.tools.builtins import BuiltinContext, BuiltinResult, register

# ──────────────────────────────────────────────────────────────────────
# In-memory mock stores
# ──────────────────────────────────────────────────────────────────────

_CUSTOMERS: dict[str, dict[str, Any]] = {
    "aman@example.com": {
        "id": "cus_aman_001",
        "email": "aman@example.com",
        "name": "Aman Malhotra",
        "plan": "pro",
        "joined_at": "2024-09-12",
    },
    "sara@example.com": {
        "id": "cus_sara_002",
        "email": "sara@example.com",
        "name": "Sara Iyer",
        "plan": "starter",
        "joined_at": "2025-01-04",
    },
    "demo@example.com": {
        "id": "cus_demo_003",
        "email": "demo@example.com",
        "name": "Demo User",
        "plan": "free",
        "joined_at": "2026-04-30",
    },
}

_PAYMENTS: dict[str, list[dict[str, Any]]] = {
    "cus_aman_001": [
        {
            "id": "pay_789",
            "amount_inr": 4999,
            "status": "captured",
            "method": "upi",
            "created_at": "2026-05-23T11:02:17Z",
            "refund_eligible": True,
        },
        {
            "id": "pay_654",
            "amount_inr": 499,
            "status": "captured",
            "method": "card",
            "created_at": "2026-04-23T10:00:00Z",
            "refund_eligible": False,
        },
    ],
    "cus_sara_002": [
        {
            "id": "pay_222",
            "amount_inr": 1499,
            "status": "failed",
            "method": "card",
            "created_at": "2026-05-22T08:11:09Z",
            "refund_eligible": False,
        },
    ],
}

_REFUND_POLICY = {
    "window_days": 7,
    "covers": ["payment_failed_money_deducted", "duplicate_charge", "unauthorized"],
    "excludes": ["consumed_credits", "manual_cancel_after_use"],
    "method": "auto_to_source",
    "sla_hours": 24,
    "url": "https://example.com/refund-policy",
}

_TICKETS: dict[str, dict[str, Any]] = {}
_CAMPAIGNS: dict[str, dict[str, Any]] = {}
_DRAFTS: dict[str, dict[str, Any]] = {}
_SCHEDULES: dict[str, dict[str, Any]] = {}
_APPROVALS: dict[str, dict[str, Any]] = {}

_KNOWLEDGE_BASE: list[dict[str, str]] = [
    {
        "title": "Why multi-agent workflows beat one-shot LLM calls",
        "snippet": (
            "Specialised agents — researcher, writer, reviewer — cut error rates "
            "by ~38% over single-prompt setups in customer-facing automation."
        ),
        "source": "internal:product-research/2026-Q1.md",
    },
    {
        "title": "Async tool calls keep long workflows alive",
        "snippet": (
            "Queue-backed tool execution lets workflows survive restarts, retries, "
            "and human approval pauses without rerunning earlier steps."
        ),
        "source": "internal:engineering/async-patterns.md",
    },
    {
        "title": "Brand voice cheat-sheet",
        "snippet": (
            "Tone: direct, warm, low-jargon. Avoid superlatives. Lead with the "
            "concrete benefit. End with one specific call-to-action."
        ),
        "source": "internal:brand/voice.md",
    },
]


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ──────────────────────────────────────────────────────────────────────
# Workflow 1 — Support Triage & Resolution
# ──────────────────────────────────────────────────────────────────────


@register(
    "create_ticket",
    description=(
        "Create a new support ticket from an inbound message. Returns a "
        "`ticket_id` the rest of the workflow uses. Use right after the Intake "
        "Agent has parsed the user's message."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "intent": {"type": "string"},
            "priority": {"type": "string", "enum": ["low", "medium", "high"]},
            # Nullable + optional: a user may chat the bot without ever
            # supplying their email / order id. Required string here would
            # force the model to invent placeholders.
            "customer_identifier": {"type": ["string", "null"]},
            "channel": {"type": "string", "enum": ["slack", "telegram", "web", "whatsapp"]},
            "summary": {"type": "string"},
        },
        "required": ["intent"],
    },
    category="support",
)
async def _create_ticket(inputs: dict[str, Any], _ctx: BuiltinContext) -> BuiltinResult:
    ticket_id = f"tkt_{uuid4().hex[:8]}"
    ticket = {
        "id": ticket_id,
        "intent": inputs["intent"],
        "priority": inputs.get("priority") or "medium",
        "customer_identifier": inputs.get("customer_identifier"),
        "channel": inputs.get("channel") or "web",
        "summary": inputs.get("summary"),
        "status": "open",
        "category": None,
        "enrichment": None,
        "response": None,
        "created_at": _now(),
        "updated_at": _now(),
    }
    _TICKETS[ticket_id] = ticket
    return BuiltinResult(success=True, data={"ticket": ticket})


@register(
    "update_ticket_status",
    description=(
        "Update fields on an existing ticket (status, category, priority, "
        "enrichment, response). Use after triage, after data lookup, and after "
        "the response is approved."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "ticket_id": {"type": "string"},
            "status": {
                "type": "string",
                "enum": [
                    "open",
                    "triaged",
                    "enriched",
                    "pending_approval",
                    "resolved",
                    "rejected",
                ],
            },
            "category": {
                "type": "string",
                "enum": ["billing", "technical", "refund", "account", "escalation"],
            },
            "priority": {"type": "string", "enum": ["low", "medium", "high"]},
            "enrichment": {"type": "object"},
            "response": {"type": "string"},
        },
        "required": ["ticket_id"],
    },
    category="support",
)
async def _update_ticket_status(inputs: dict[str, Any], _ctx: BuiltinContext) -> BuiltinResult:
    ticket_id = inputs["ticket_id"]
    ticket = _TICKETS.get(ticket_id)
    if ticket is None:
        return BuiltinResult(success=False, error=f"unknown ticket: {ticket_id}")
    for key in ("status", "category", "priority", "enrichment", "response"):
        if inputs.get(key) is not None:
            ticket[key] = inputs[key]
    ticket["updated_at"] = _now()
    return BuiltinResult(success=True, data={"ticket": ticket})


@register(
    "get_customer",
    description=(
        "Look up a customer by email. Returns name, plan, join date, and "
        "customer_id used by `get_payment_status`."
    ),
    input_schema={
        "type": "object",
        "properties": {"email": {"type": "string"}},
        "required": ["email"],
    },
    category="support",
)
async def _get_customer(inputs: dict[str, Any], _ctx: BuiltinContext) -> BuiltinResult:
    email = (inputs.get("email") or "").lower().strip()
    customer = _CUSTOMERS.get(email)
    if customer is None:
        return BuiltinResult(success=False, error=f"customer not found: {email}")
    return BuiltinResult(success=True, data={"customer": customer})


@register(
    "get_payment_status",
    description=(
        "Get a customer's recent payments. Returns each payment's id, amount, "
        "status (captured/failed/refunded), method, and `refund_eligible` flag. "
        "Use to verify the user's claim that money was deducted."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "customer_id": {"type": "string"},
            "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 25},
        },
        "required": ["customer_id"],
    },
    category="support",
)
async def _get_payment_status(inputs: dict[str, Any], _ctx: BuiltinContext) -> BuiltinResult:
    customer_id = inputs["customer_id"]
    limit = int(inputs.get("limit") or 5)
    payments = _PAYMENTS.get(customer_id, [])[:limit]
    return BuiltinResult(success=True, data={"customer_id": customer_id, "payments": payments})


@register(
    "get_refund_policy",
    description=(
        "Return the company refund policy: window, which intents qualify, and "
        "which don't. Use before drafting a refund reply so the response is "
        "always policy-aligned."
    ),
    input_schema={"type": "object", "properties": {}},
    category="support",
)
async def _get_refund_policy(_inputs: dict[str, Any], _ctx: BuiltinContext) -> BuiltinResult:
    return BuiltinResult(success=True, data={"policy": _REFUND_POLICY})


@register(
    "request_human_approval",
    description=(
        "Open a human-approval request for a sensitive action (refund, "
        "destructive update, customer-facing reply). Returns an `approval_id`. "
        "The workflow should pause until the operator approves or rejects."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "context": {"type": "object"},
            "channel": {"type": "string", "default": "slack"},
        },
        "required": ["subject", "body"],
    },
    category="approval",
)
async def _request_human_approval(inputs: dict[str, Any], ctx: BuiltinContext) -> BuiltinResult:
    approval_id = f"appr_{uuid4().hex[:8]}"
    _APPROVALS[approval_id] = {
        "id": approval_id,
        "subject": inputs["subject"],
        "body": inputs["body"],
        "context": inputs.get("context") or {},
        "channel": inputs.get("channel") or "slack",
        "status": "pending",
        "requested_by_agent_id": str(ctx.agent_id) if ctx.agent_id else None,
        "created_at": _now(),
    }
    return BuiltinResult(
        success=True,
        data={
            "approval_id": approval_id,
            "status": "pending",
            "instructions": "Reply Approve/Reject in the operator channel.",
        },
    )


# ──────────────────────────────────────────────────────────────────────
# Workflow 2 — Content Research → Draft → Schedule → Publish
# ──────────────────────────────────────────────────────────────────────


@register(
    "create_campaign",
    description=(
        "Open a content campaign. Returns a `campaign_id` the rest of the "
        "workflow keys research, drafts, and schedules off of."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "platform": {"type": "string", "enum": ["linkedin", "twitter", "blog", "email"]},
            "format": {"type": "string"},
            "schedule_time": {"type": "string", "description": "ISO 8601 or free-text."},
            "approval_required": {"type": "boolean", "default": True},
        },
        "required": ["topic", "platform"],
    },
    category="content",
)
async def _create_campaign(inputs: dict[str, Any], _ctx: BuiltinContext) -> BuiltinResult:
    campaign_id = f"cmp_{uuid4().hex[:8]}"
    campaign = {
        "id": campaign_id,
        "topic": inputs["topic"],
        "platform": inputs["platform"],
        "format": inputs.get("format") or "short_post",
        "schedule_time": inputs.get("schedule_time"),
        "approval_required": inputs.get("approval_required", True),
        "research_notes": [],
        "draft_id": None,
        "status": "open",
        "created_at": _now(),
    }
    _CAMPAIGNS[campaign_id] = campaign
    return BuiltinResult(success=True, data={"campaign": campaign})


@register(
    "search_knowledge_base",
    description=(
        "Search the internal knowledge base for relevant snippets. Returns up "
        "to N items with title + snippet + source. Use before writing so the "
        "draft is grounded in company-approved material."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "default": 3, "minimum": 1, "maximum": 10},
        },
        "required": ["query"],
    },
    category="research",
)
async def _search_knowledge_base(inputs: dict[str, Any], _ctx: BuiltinContext) -> BuiltinResult:
    query = (inputs.get("query") or "").lower()
    top_k = int(inputs.get("top_k") or 3)
    scored = [
        (
            sum(
                word in item["title"].lower() or word in item["snippet"].lower()
                for word in query.split()
            ),
            item,
        )
        for item in _KNOWLEDGE_BASE
    ]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return BuiltinResult(
        success=True,
        data={"query": query, "results": [item for _, item in scored[:top_k]]},
    )


@register(
    "save_research_notes",
    description=(
        "Persist research notes onto a campaign so downstream agents (Writer, "
        "Reviewer) can read them. Pass `campaign_id` and a list of `notes`."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "campaign_id": {"type": "string"},
            "notes": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["campaign_id", "notes"],
    },
    category="content",
)
async def _save_research_notes(inputs: dict[str, Any], _ctx: BuiltinContext) -> BuiltinResult:
    campaign = _CAMPAIGNS.get(inputs["campaign_id"])
    if campaign is None:
        return BuiltinResult(success=False, error=f"unknown campaign: {inputs['campaign_id']}")
    campaign["research_notes"] = list(inputs["notes"])
    return BuiltinResult(success=True, data={"campaign": campaign})


@register(
    "create_draft",
    description=(
        "Create the first draft of a piece of content. Returns a `draft_id`. "
        "Use after research is saved. Body should already reflect the platform "
        "(LinkedIn voice ≠ Twitter voice)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "campaign_id": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["campaign_id", "body"],
    },
    category="content",
)
async def _create_draft(inputs: dict[str, Any], _ctx: BuiltinContext) -> BuiltinResult:
    campaign = _CAMPAIGNS.get(inputs["campaign_id"])
    if campaign is None:
        return BuiltinResult(success=False, error=f"unknown campaign: {inputs['campaign_id']}")
    draft_id = f"drft_{uuid4().hex[:8]}"
    draft = {
        "id": draft_id,
        "campaign_id": campaign["id"],
        "body": inputs["body"],
        "revision": 1,
        "status": "drafted",
        "feedback": None,
        "created_at": _now(),
    }
    _DRAFTS[draft_id] = draft
    campaign["draft_id"] = draft_id
    return BuiltinResult(success=True, data={"draft": draft})


@register(
    "update_draft",
    description=(
        "Apply a revision to an existing draft. Increments `revision`. Use when "
        "the Brand Review Agent sends feedback and the Writer rewrites."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "draft_id": {"type": "string"},
            "body": {"type": "string"},
            "feedback_applied": {"type": "string"},
        },
        "required": ["draft_id", "body"],
    },
    category="content",
)
async def _update_draft(inputs: dict[str, Any], _ctx: BuiltinContext) -> BuiltinResult:
    draft = _DRAFTS.get(inputs["draft_id"])
    if draft is None:
        return BuiltinResult(success=False, error=f"unknown draft: {inputs['draft_id']}")
    draft["body"] = inputs["body"]
    draft["revision"] += 1
    draft["status"] = "revised"
    if inputs.get("feedback_applied") is not None:
        draft["feedback"] = inputs["feedback_applied"]
    return BuiltinResult(success=True, data={"draft": draft})


@register(
    "brand_check",
    description=(
        "Run a brand-voice review on a draft body. Returns `verdict` "
        "('approved'|'needs_revision'), a `score` 0–100, and (when needs_revision) "
        "specific `feedback` for the Writer."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "body": {"type": "string"},
            "platform": {"type": "string", "default": "linkedin"},
        },
        "required": ["body"],
    },
    category="content",
)
async def _brand_check(inputs: dict[str, Any], _ctx: BuiltinContext) -> BuiltinResult:
    body = (inputs.get("body") or "").strip()
    word_count = len(body.split())
    superlatives = sum(
        body.lower().count(word)
        for word in (" best ", " ultimate ", " revolutionary ", " game-changing ")
    )
    too_generic = "agents are great" in body.lower() or "ai is the future" in body.lower()

    if word_count < 20:
        return BuiltinResult(
            success=True,
            data={
                "verdict": "needs_revision",
                "score": 35,
                "feedback": "Too short — expand with one concrete benefit and a closing CTA.",
            },
        )
    if superlatives >= 2:
        return BuiltinResult(
            success=True,
            data={
                "verdict": "needs_revision",
                "score": 55,
                "feedback": "Tone-down superlatives; pick one concrete metric instead.",
            },
        )
    if too_generic:
        return BuiltinResult(
            success=True,
            data={
                "verdict": "needs_revision",
                "score": 50,
                "feedback": "Too generic. Add a specific business outcome (revenue, time saved, retention).",
            },
        )
    return BuiltinResult(success=True, data={"verdict": "approved", "score": 88, "feedback": None})


@register(
    "schedule_post",
    description=(
        "Schedule an approved draft for publishing at a future timestamp. "
        "Accepts ISO 8601 or natural relative time ('tomorrow 10am'). Returns "
        "a `post_id` and resolved `scheduled_for`."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "draft_id": {"type": "string"},
            "scheduled_for": {"type": "string"},
            "platform": {"type": "string", "default": "linkedin"},
        },
        "required": ["draft_id", "scheduled_for"],
    },
    category="content",
)
async def _schedule_post(inputs: dict[str, Any], _ctx: BuiltinContext) -> BuiltinResult:
    draft = _DRAFTS.get(inputs["draft_id"])
    if draft is None:
        return BuiltinResult(success=False, error=f"unknown draft: {inputs['draft_id']}")
    raw = (inputs.get("scheduled_for") or "").strip().lower()
    when: datetime
    if "tomorrow" in raw:
        base = datetime.now(UTC) + timedelta(days=1)
        when = base.replace(hour=10, minute=0, second=0, microsecond=0)
    else:
        try:
            when = datetime.fromisoformat(raw.replace("z", "+00:00"))
        except ValueError:
            when = datetime.now(UTC) + timedelta(hours=12)
    post_id = f"post_{uuid4().hex[:8]}"
    schedule = {
        "id": post_id,
        "draft_id": draft["id"],
        "platform": inputs.get("platform") or "linkedin",
        "scheduled_for": when.isoformat(),
        "status": "scheduled",
        "created_at": _now(),
    }
    _SCHEDULES[post_id] = schedule
    draft["status"] = "scheduled"
    return BuiltinResult(success=True, data={"post": schedule})


@register(
    "publish_post",
    description=(
        "Publish a scheduled post immediately (simulated). Flips the scheduled "
        "row to `published` and returns the public-facing URL stub. Demo button "
        "uses this to bypass the scheduled wait."
    ),
    input_schema={
        "type": "object",
        "properties": {"post_id": {"type": "string"}},
        "required": ["post_id"],
    },
    category="content",
)
async def _publish_post(inputs: dict[str, Any], _ctx: BuiltinContext) -> BuiltinResult:
    schedule = _SCHEDULES.get(inputs["post_id"])
    if schedule is None:
        return BuiltinResult(success=False, error=f"unknown post: {inputs['post_id']}")
    schedule["status"] = "published"
    schedule["published_at"] = _now()
    schedule["public_url"] = f"https://example.com/p/{schedule['id']}"
    return BuiltinResult(success=True, data={"post": schedule})


__all__: list[str] = []
