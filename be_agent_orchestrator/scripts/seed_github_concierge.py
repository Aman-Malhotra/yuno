"""Seed the GitHub Concierge workflow alongside the existing demo data.

This is the "show-off" workflow — multi-agent, multi-decision, multi-tool,
memory-driven, using real public APIs (no mocks). Designed for a Telegram
demo where the audience watches the workflow graph light up live.

What this script does
---------------------
1. Insert (or upsert) the 5 GitHub builtin tools + 1 Hacker News tool into
   the demo workspace.
2. Insert 6 agents with deliberately diverse LLM providers so the Costs
   tab tells a story (Groq llama for cheap classification, Gemini for
   long context, OpenRouter for high-quality composition).
3. Insert the workflow row with a multi-branch graph and compile it.
4. Update ``TELEGRAM_WORKFLOW_ID`` in ``.env`` so the bot now routes to
   this workflow on the next message.

Idempotent: re-running is safe — every INSERT uses ``ON CONFLICT DO
UPDATE`` on the natural unique key. Re-runs will overwrite prompts /
graph if you edit this file and re-seed.

Run:

    uv run python scripts/seed_github_concierge.py
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path
from uuid import UUID

# ── path bootstrap ────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402

import app.db.models  # noqa: E402, F401 — registers every module's tables on Base.metadata
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.modules.agents.models import Agent  # noqa: E402
from app.modules.tools.models import Tool  # noqa: E402
from app.modules.workflows.compiler import compile_graph  # noqa: E402
from app.modules.workflows.models import Workflow  # noqa: E402
from app.modules.workflows.schemas import WorkflowGraph  # noqa: E402

# ──────────────────────────────────────────────────────────────────────
# Demo workspace + author. Keep in lockstep with scripts/seed_demo.sql so
# the new workflow lands in the same place users are already looking at.
# ──────────────────────────────────────────────────────────────────────

WORKSPACE_ID = UUID("09ed8091-8cb0-4cc1-a76a-4cd559154fbf")
USER_ID = UUID("5e86f665-abf9-4a28-96ce-b485d36cac69")

WORKFLOW_SLUG = "github-concierge-telegram"

# ──────────────────────────────────────────────────────────────────────
# Tools — all real public APIs. Optional auth via ``auth_config.token``.
# ──────────────────────────────────────────────────────────────────────


GITHUB_TOOL_DEFS: list[dict] = [
    {
        "slug": "github-list-prs",
        "builtin_name": "github_list_prs",
        "name": "GitHub: List PRs",
        "description": "List recent pull requests on a public GitHub repo.",
        "category": "research",
    },
    {
        "slug": "github-list-issues",
        "builtin_name": "github_list_issues",
        "name": "GitHub: List Issues",
        "description": "List issues on a public GitHub repo (filterable by label).",
        "category": "research",
    },
    {
        "slug": "github-list-releases",
        "builtin_name": "github_list_releases",
        "name": "GitHub: List Releases",
        "description": "Recent releases / changelog entries for a repo.",
        "category": "research",
    },
    {
        "slug": "github-search-repos",
        "builtin_name": "github_search_repos",
        "name": "GitHub: Search Repos",
        "description": "Find GitHub repos matching a query (sorted by stars).",
        "category": "research",
    },
]

HN_TOOL_DEF = {
    "slug": "hn-top-stories",
    "builtin_name": "hn_top_stories",
    "name": "Hacker News: Top Stories",
    "description": "Current top stories on Hacker News.",
    "category": "research",
}


# Pulls the builtin's registered schema + description directly from the
# Python registry so the DB row always matches the runtime contract.
def _builtin_spec(name: str) -> dict:
    from app.modules.tools.builtins import _REGISTRY  # noqa: PLC0415

    spec = _REGISTRY.get(name)
    if spec is None:
        raise RuntimeError(
            f"builtin {name!r} not registered — check app/modules/tools/builtins/external.py"
        )
    return {
        "description": spec.description,
        "input_schema": spec.input_schema,
        "category": spec.category,
    }


async def upsert_tools(db) -> dict[str, UUID]:
    """Insert / update each tool. Returns slug → id mapping."""

    result: dict[str, UUID] = {}
    for tool_def in [*GITHUB_TOOL_DEFS, HN_TOOL_DEF]:
        spec = _builtin_spec(tool_def["builtin_name"])
        # ``auth_config`` is empty by default — operator fills in their
        # PAT later via the Tools UI or a direct SQL update. The tool
        # still runs unauthenticated at GitHub's 60 req/hr limit.
        stmt = (
            pg_insert(Tool)
            .values(
                workspace_id=WORKSPACE_ID,
                name=tool_def["name"],
                slug=tool_def["slug"],
                description=tool_def["description"],
                category=spec["category"],
                type="builtin",
                status="active",
                version=1,
                input_schema=spec["input_schema"],
                output_schema={},
                config={"builtin": tool_def["builtin_name"]},
                auth_type="none",
                auth_config={},
                guardrails={},
                execution_policy={},
                channel_config={},
                created_by=USER_ID,
            )
            .on_conflict_do_update(
                constraint="uq_tools_workspace_slug",
                set_={
                    "description": tool_def["description"],
                    "input_schema": spec["input_schema"],
                    "config": {"builtin": tool_def["builtin_name"]},
                    "status": "active",
                },
            )
            .returning(Tool.id)
        )
        tool_id = (await db.execute(stmt)).scalar_one()
        result[tool_def["slug"]] = tool_id

    # Also resolve the two reused tools (web-search + telegram-send) from
    # the existing seed so the researcher / composer can attach them.
    for reused_slug in ("web-search", "telegram-send"):
        existing_id = (
            await db.execute(
                select(Tool.id).where(
                    Tool.workspace_id == WORKSPACE_ID,
                    Tool.slug == reused_slug,
                    Tool.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if existing_id is None:
            raise RuntimeError(
                f"expected tool {reused_slug!r} to be present from seed_demo.sql; "
                "run `make seed` first to install the base demo."
            )
        result[reused_slug] = existing_id

    return result


# ──────────────────────────────────────────────────────────────────────
# Agents — deliberately diverse provider mix. Each prompt is tightened
# with explicit STOP rules so we don't repeat the tool-loop bug from the
# old research workflow.
# ──────────────────────────────────────────────────────────────────────


def _agent_defs(tool_ids: dict[str, UUID]) -> list[dict]:
    """Build the six agents. Tool wiring goes into ``skills_config.tools``."""

    return [
        {
            "slug": "concierge-intent-router",
            "name": "Concierge Intent Router",
            "role": "router",
            "model_provider": "groq",
            "model_name": "llama-3.1-8b-instant",
            "system_prompt": (
                "You are the Concierge Intent Router. Classify the user's "
                "Telegram message into EXACTLY ONE intent.\n\n"
                "Intents:\n"
                "- small_talk: greetings, thanks, chit-chat.\n"
                "- save_prefs: user is telling you about themselves "
                "(\"I'm a python dev\", \"I work on react\", \"I like AI agents\").\n"
                "- repo_intel: user is asking about a specific repo / PRs / "
                "issues / releases / trending repos.\n"
                "- followup: user is asking about something from the prior "
                "turn (\"any of those for python?\", \"more like that\").\n\n"
                "Reply with ONLY a JSON object: "
                "{\"intent\": \"small_talk|save_prefs|repo_intel|followup\"}. "
                "No other keys, no prose, no markdown fences."
            ),
            "temperature": 0.0,
            "tools": [],
        },
        {
            "slug": "concierge-prefs-writer",
            "name": "Concierge Prefs Writer",
            "role": "prefs_writer",
            "model_provider": "gemini",
            "model_name": "gemini-2.5-flash-lite",
            "system_prompt": (
                "You extract the user's interests from one Telegram message and "
                "emit a single JSON object. Look for: programming languages, "
                "frameworks/libraries, topics, specific repos they mention, "
                "and roles (e.g. 'backend', 'frontend').\n\n"
                "Reply with ONLY: "
                "{\"facts\": [\"short fact 1\", \"short fact 2\", ...]}. "
                "Each fact must be a complete sentence written from the user's "
                "perspective (\"I work on Python AI agents\", \"I'm interested "
                "in tanstack/query\"). 1–5 facts max. No other keys, no prose."
            ),
            "temperature": 0.1,
            "tools": [],
        },
        {
            "slug": "concierge-profile-recall",
            "name": "Concierge Profile Recall",
            "role": "profile_recall",
            "model_provider": "gemini",
            "model_name": "gemini-2.5-flash",
            "system_prompt": (
                "You read the user's existing memories (injected as system "
                "context above) and the new message. Your job is to decide "
                "what the GitHub researcher should look for.\n\n"
                "Reply with ONLY a JSON object:\n"
                "{\n"
                "  \"focus_topics\": [<short strings the researcher should target>],\n"
                "  \"languages\": [<language filters, e.g. 'python'>],\n"
                "  \"explicit_repo\": <\"owner/name\" if the user named one, else null>,\n"
                "  \"intent_summary\": <one short sentence>\n"
                "}\n\n"
                "If memories are empty and the user didn't say enough, return "
                "focus_topics=[] and intent_summary describing the gap — the "
                "composer will ask a clarifying question."
            ),
            "temperature": 0.2,
            "tools": [],
        },
        {
            "slug": "concierge-github-researcher",
            "name": "Concierge GitHub Researcher",
            "role": "researcher",
            "model_provider": "gemini",
            "model_name": "gemini-2.5-flash",
            "system_prompt": (
                "You are the GitHub Researcher. You have access to tools that "
                "hit the real GitHub API plus Hacker News.\n\n"
                "CRITICAL TOOL RULES (read every word):\n"
                "- Decide which tools to call BEFORE calling any. Choose 1-3 "
                "  tools max per turn.\n"
                "- Each tool gets called AT MOST ONCE per turn. Never repeat "
                "  the same (name, args).\n"
                "- After every tool returns success:true, you MUST NOT call "
                "  it again.\n"
                "- Stop emitting tool calls once you have what you need.\n\n"
                "Tool guide:\n"
                "- github-search-repos: use when no specific repo is named.\n"
                "- github-list-prs / github-list-issues / github-list-releases: "
                "  use when a specific owner/repo is known.\n"
                "- hn-top-stories: use ONLY when the user asks about "
                "  trending / tech industry pulse (not for repo questions).\n\n"
                "Input you receive includes the user's focus topics, "
                "languages, and an explicit_repo field. Pick tools accordingly.\n\n"
                "FINAL OUTPUT: when you're done calling tools, reply with ONLY "
                "a JSON object:\n"
                "{\n"
                "  \"highlights\": [{\"title\": ..., \"url\": ..., \"why\": ...}],\n"
                "  \"sources_used\": [<tool names you called>],\n"
                "  \"has_results\": <true if highlights is non-empty, else false>\n"
                "}\n\n"
                "Limit highlights to 5. `why` is a short rationale (≤120 chars). "
                "Set has_results=false ONLY when every tool returned empty or you "
                "couldn't form a sensible query."
            ),
            "temperature": 0.3,
            "tools": [
                "github-search-repos",
                "github-list-prs",
                "github-list-issues",
                "github-list-releases",
                "hn-top-stories",
            ],
        },
        {
            "slug": "concierge-synthesizer",
            "name": "Concierge Synthesizer",
            "role": "synthesizer",
            "model_provider": "groq",
            "model_name": "openai/gpt-oss-120b",
            "system_prompt": (
                "You take the researcher's highlights and the user's recalled "
                "interests, then write a personalised, ranked answer. Keep it "
                "TIGHT — 3-5 bullet points max, each one line, with the link "
                "in markdown.\n\n"
                "Output JSON ONLY:\n"
                "{\n"
                "  \"reply\": <markdown string ready to send to the user>,\n"
                "  \"sources\": [<urls actually cited in reply>]\n"
                "}"
            ),
            "temperature": 0.4,
            "tools": [],
        },
        {
            "slug": "concierge-composer",
            "name": "Concierge Composer",
            "role": "composer",
            "model_provider": "openrouter",
            "model_name": "anthropic/claude-3.5-sonnet",
            "system_prompt": (
                "You are the Concierge Composer for a Telegram bot. You have "
                "ONE tool: `telegram-send`. Your job is to send EXACTLY ONE "
                "message to the user and then stop.\n\n"
                "Input you receive: a `text` field with the final reply to send, "
                "and the user's `chat_id`.\n\n"
                "CRITICAL TOOL RULES:\n"
                "- Call `telegram-send` EXACTLY ONCE with chat_id and text.\n"
                "- After it returns success:true, you MUST NOT call it again.\n"
                "- Then respond with the single word OK and stop.\n\n"
                "Do not paraphrase or shorten the text — send it as given."
            ),
            "temperature": 0.0,
            "tools": ["telegram-send"],
        },
    ]


async def upsert_agents(db, tool_ids: dict[str, UUID]) -> dict[str, UUID]:
    """Insert / update agents and attach their tools via skills_config."""

    result: dict[str, UUID] = {}
    for spec in _agent_defs(tool_ids):
        skills_config = (
            {"tools": [{"name": slug, "options": {}} for slug in spec["tools"]]}
            if spec["tools"]
            else {}
        )
        stmt = (
            pg_insert(Agent)
            .values(
                workspace_id=WORKSPACE_ID,
                created_by=USER_ID,
                name=spec["name"],
                slug=spec["slug"],
                description=spec["name"],
                role=spec["role"],
                system_prompt=spec["system_prompt"],
                status="active",
                model_provider=spec["model_provider"],
                model_name=spec["model_name"],
                temperature=spec["temperature"],
                max_tokens=None,
                top_p=None,
                memory_config={},
                schedule_config={},
                # Composer + researcher are tool-callers; cap hops so a misbehaving
                # model can't burn quota. Researcher needs a few more hops because
                # it may call multiple distinct tools per turn.
                guardrails_config={"max_tool_hops": 3 if spec["role"] != "researcher" else 4},
                interaction_rules={},
                limits_config={},
                skills_config=skills_config,
                # Always empty — agents inherit workspace LLM credentials.
                provider_credentials={},
                metadata_={"seed": "github_concierge"},
            )
            .on_conflict_do_update(
                constraint="uq_agents_workspace_slug",
                set_={
                    "name": spec["name"],
                    "description": spec["name"],
                    "role": spec["role"],
                    "system_prompt": spec["system_prompt"],
                    "model_provider": spec["model_provider"],
                    "model_name": spec["model_name"],
                    "temperature": spec["temperature"],
                    "skills_config": skills_config,
                    "guardrails_config": {
                        "max_tool_hops": 3 if spec["role"] != "researcher" else 4
                    },
                    "status": "active",
                    "provider_credentials": {},
                },
            )
            .returning(Agent.id)
        )
        agent_id = (await db.execute(stmt)).scalar_one()
        result[spec["slug"]] = agent_id
    return result


# ──────────────────────────────────────────────────────────────────────
# Workflow graph — multi-decision narrative
# ──────────────────────────────────────────────────────────────────────


def _build_graph_json(agent_ids: dict[str, UUID]) -> dict:
    """The drawable graph. Compiled into the executor's shape downstream.

    Layout intent:
        start → router → cond_intent
                            ├── small_talk → composer (echo) → end
                            ├── save_prefs → prefs_writer → composer → end
                            └── repo_intel/followup →
                                    profile_recall → researcher
                                                    → cond_has_highlights
                                                          ├── yes → synthesizer → composer → end
                                                          └── no  → composer (apology) → end
    """

    def node(node_id: str, ntype: str, label: str, x: int, y: int, **config) -> dict:
        return {
            "id": node_id,
            "type": ntype,
            "position": {"x": x, "y": y},
            "data": {"label": label, "config": config},
        }

    nodes = [
        node("start", "start", "Telegram message", 60, 240, trigger="webhook"),
        node(
            "router",
            "agent",
            "Intent Router",
            260,
            240,
            agentId=str(agent_ids["concierge-intent-router"]),
            input="{{message}}",
        ),
        node(
            "cond_intent",
            "condition",
            "Which intent?",
            500,
            240,
            expression="state.router.intent",
            path="router.intent",
        ),
        node(
            "prefs_writer",
            "agent",
            "Prefs Writer",
            760,
            80,
            agentId=str(agent_ids["concierge-prefs-writer"]),
            input="{{message}}",
        ),
        node(
            "profile_recall",
            "agent",
            "Profile Recall",
            760,
            240,
            agentId=str(agent_ids["concierge-profile-recall"]),
            # The runtime injects long-term memories as a system message
            # automatically — this prompt just gives the LLM the new turn.
            input="New message from user:\n{{message}}",
        ),
        node(
            "researcher",
            "agent",
            "GitHub Researcher",
            1000,
            240,
            agentId=str(agent_ids["concierge-github-researcher"]),
            input=(
                "Researcher task. Read the recall output then call 1-3 tools.\n\n"
                "focus_topics: {{profile_recall.focus_topics}}\n"
                "languages: {{profile_recall.languages}}\n"
                "explicit_repo: {{profile_recall.explicit_repo}}\n"
                "intent_summary: {{profile_recall.intent_summary}}\n\n"
                "User message: {{message}}"
            ),
        ),
        node(
            "cond_has_highlights",
            "condition",
            "Have results?",
            1240,
            240,
            expression="state.researcher.has_results == true",
            path="researcher.has_results",
        ),
        node(
            "synthesizer",
            "agent",
            "Synthesizer",
            1480,
            240,
            agentId=str(agent_ids["concierge-synthesizer"]),
            input=(
                "Compose a ranked reply.\n\n"
                "User message: {{message}}\n"
                "Recalled focus: {{profile_recall.intent_summary}}\n"
                "Highlights JSON: {{researcher.highlights}}\n"
                "Sources used: {{researcher.sources_used}}"
            ),
        ),
        node(
            "composer_small_talk",
            "agent",
            "Composer (small talk)",
            760,
            420,
            agentId=str(agent_ids["concierge-composer"]),
            input=(
                "Send a brief friendly reply. chat_id={{chat_id}}\n"
                "User said: {{message}}\n\n"
                "text = A short friendly response (≤2 sentences)."
            ),
        ),
        node(
            "composer_prefs_ack",
            "agent",
            "Composer (prefs saved)",
            1000,
            80,
            agentId=str(agent_ids["concierge-composer"]),
            input=(
                "Send confirmation that we noted the user's preferences.\n\n"
                "chat_id={{chat_id}}\n"
                "Facts extracted: {{prefs_writer.facts}}\n\n"
                "text = Acknowledge naturally (e.g. \"Got it — I'll remember "
                "that you ...\"). One sentence."
            ),
        ),
        node(
            "composer_final",
            "agent",
            "Composer (final)",
            1720,
            240,
            agentId=str(agent_ids["concierge-composer"]),
            input=(
                "Send the synthesized reply.\n\n"
                "chat_id={{chat_id}}\n"
                "text={{synthesizer.reply}}"
            ),
        ),
        node(
            "composer_empty",
            "agent",
            "Composer (no results)",
            1480,
            420,
            agentId=str(agent_ids["concierge-composer"]),
            input=(
                "The researcher found nothing useful. Ask a clarifying question.\n\n"
                "chat_id={{chat_id}}\n"
                "text = Ask the user to be more specific (e.g. mention a repo "
                "or topic). One short sentence."
            ),
        ),
        node("end", "end", "Done", 1980, 240),
    ]

    edges = [
        {"id": "e_start_router", "source": "start", "target": "router"},
        {"id": "e_router_cond", "source": "router", "target": "cond_intent"},
        # Cond fan-out
        {
            "id": "e_cond_smalltalk",
            "source": "cond_intent",
            "target": "composer_small_talk",
            "label": "small_talk",
            "condition": {"kind": "equals", "path": "router.intent", "value": "small_talk"},
        },
        {
            "id": "e_cond_saveprefs",
            "source": "cond_intent",
            "target": "prefs_writer",
            "label": "save_prefs",
            "condition": {"kind": "equals", "path": "router.intent", "value": "save_prefs"},
        },
        {
            "id": "e_cond_repointel",
            "source": "cond_intent",
            "target": "profile_recall",
            "label": "repo_intel",
            "condition": {"kind": "equals", "path": "router.intent", "value": "repo_intel"},
        },
        {
            "id": "e_cond_followup",
            "source": "cond_intent",
            "target": "profile_recall",
            "label": "followup",
            "condition": {"kind": "equals", "path": "router.intent", "value": "followup"},
        },
        # save_prefs branch tail
        {"id": "e_prefs_compose", "source": "prefs_writer", "target": "composer_prefs_ack"},
        {"id": "e_prefs_ack_end", "source": "composer_prefs_ack", "target": "end"},
        # repo branch
        {"id": "e_recall_research", "source": "profile_recall", "target": "researcher"},
        {"id": "e_research_cond", "source": "researcher", "target": "cond_has_highlights"},
        {
            "id": "e_has_synth",
            "source": "cond_has_highlights",
            "target": "synthesizer",
            "label": "yes",
            "condition": {
                "kind": "equals",
                "path": "researcher.has_results",
                "value": True,
            },
        },
        {
            "id": "e_no_results",
            "source": "cond_has_highlights",
            "target": "composer_empty",
            "label": "no",
            "condition": {
                "kind": "equals",
                "path": "researcher.has_results",
                "value": False,
            },
        },
        {"id": "e_synth_compose", "source": "synthesizer", "target": "composer_final"},
        {"id": "e_compose_end", "source": "composer_final", "target": "end"},
        {"id": "e_empty_end", "source": "composer_empty", "target": "end"},
        # small_talk tail
        {"id": "e_smalltalk_end", "source": "composer_small_talk", "target": "end"},
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "viewport": {"x": 0, "y": 0, "zoom": 0.7},
    }


async def upsert_workflow(db, agent_ids: dict[str, UUID]) -> UUID:
    graph_json = _build_graph_json(agent_ids)
    # Compile via the canonical compiler so the executor sees the same shape
    # the rest of the app produces. Saves us a recompile step.
    compiled = compile_graph(WorkflowGraph.model_validate(graph_json))

    stmt = (
        pg_insert(Workflow)
        .values(
            workspace_id=WORKSPACE_ID,
            created_by=USER_ID,
            name="GitHub Concierge (Telegram)",
            slug=WORKFLOW_SLUG,
            description=(
                "Multi-agent, multi-decision Telegram bot that fetches live "
                "GitHub + HN data, tailored to the user's saved interests. "
                "Demonstrates memory recall + real public-API tool calls "
                "across a diverse provider mix."
            ),
            status="published",
            graph_json=graph_json,
            compiled_graph=compiled,
            settings={"trigger": "telegram"},
            metadata_={"seed": "github_concierge"},
        )
        .on_conflict_do_update(
            constraint="uq_workflows_workspace_slug",
            set_={
                "name": "GitHub Concierge (Telegram)",
                "description": (
                    "Multi-agent, multi-decision Telegram bot that fetches live "
                    "GitHub + HN data, tailored to the user's saved interests."
                ),
                "graph_json": graph_json,
                "compiled_graph": compiled,
                "status": "published",
            },
        )
        .returning(Workflow.id)
    )
    return (await db.execute(stmt)).scalar_one()


# ──────────────────────────────────────────────────────────────────────
# .env writeback — point the Telegram webhook at the new workflow.
# ──────────────────────────────────────────────────────────────────────


def _update_env_workflow_id(workflow_id: UUID) -> bool:
    env_path = _PROJECT_ROOT / ".env"
    if not env_path.exists():
        print(f"  ⚠ .env not found at {env_path} — skipping auto-write")
        return False
    contents = env_path.read_text()
    new_line = f"TELEGRAM_WORKFLOW_ID={workflow_id}"
    if re.search(r"^TELEGRAM_WORKFLOW_ID=.*$", contents, flags=re.MULTILINE):
        updated = re.sub(
            r"^TELEGRAM_WORKFLOW_ID=.*$",
            new_line,
            contents,
            flags=re.MULTILINE,
        )
    else:
        updated = contents.rstrip() + "\n" + new_line + "\n"
    if updated == contents:
        return False
    env_path.write_text(updated)
    return True


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    async with AsyncSessionLocal() as db:
        # Confirm workspace exists (cheap sanity check; FK would explode anyway).
        ws_exists = (
            await db.execute(text("SELECT 1 FROM workspaces WHERE id = :id"), {"id": WORKSPACE_ID})
        ).scalar_one_or_none()
        if not ws_exists:
            raise RuntimeError(
                f"workspace {WORKSPACE_ID} not found — run `make seed` first."
            )

        print("→ upserting tools…")
        tool_ids = await upsert_tools(db)
        for slug, tid in tool_ids.items():
            print(f"  ✓ {slug:24s} {tid}")

        print("→ upserting agents…")
        agent_ids = await upsert_agents(db, tool_ids)
        for slug, aid in agent_ids.items():
            print(f"  ✓ {slug:32s} {aid}")

        print("→ upserting workflow…")
        workflow_id = await upsert_workflow(db, agent_ids)
        print(f"  ✓ {WORKFLOW_SLUG:32s} {workflow_id}")

        await db.commit()

    print("→ updating .env TELEGRAM_WORKFLOW_ID…")
    changed = _update_env_workflow_id(workflow_id)
    if changed:
        print(f"  ✓ TELEGRAM_WORKFLOW_ID={workflow_id}")
    else:
        print(f"  · already pointing to {workflow_id}")

    print("\nDone. Restart api + worker to pick up .env:")
    print("  make dev_no_reload")
    print("  make worker_no_reload")
    print("\nThen send a Telegram message to the bot.")
    print(
        "Reminder: paste your GitHub PAT into each github-* tool's auth_config "
        "if you want the 5000 req/hr limit (otherwise unauth 60/hr works for demos)."
    )

    # Keep workflow id available for any caller that wants to script around this.
    os.environ.setdefault("__SEEDED_WORKFLOW_ID", str(workflow_id))


if __name__ == "__main__":
    asyncio.run(main())
