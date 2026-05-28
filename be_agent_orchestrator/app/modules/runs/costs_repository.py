"""Per-agent token aggregation for the Costs tab.

Reads ``runtime_events`` rather than ``workflow_run_nodes`` because the
node row doesn't carry token columns — the executor stamps tokens onto
each ``node.completed`` event payload instead. One source of truth.

The query is intentionally a single roll-up across the whole workspace.
Per-agent breakouts in the UI come from the GROUP BY agent_id; per-day
or per-model splits are out-of-scope for v1 and can be added by tweaking
the SELECT later.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


class CostsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def per_agent_token_usage(
        self,
        workspace_id: UUID,
        *,
        since: datetime | None = None,
    ) -> list[dict[str, object]]:
        """Aggregate input/output tokens + run count for every agent that
        has produced at least one ``node.completed`` event in this workspace.

        Output rows include agent metadata (name/provider/model) joined from
        ``agents`` — agents that have since been soft-deleted still appear
        in the totals (their id stays in events), with name pulled best-effort.
        """

        stmt = text(
            """
            SELECT
              e.agent_id                                                AS agent_id,
              COALESCE(a.name, 'deleted-agent')                         AS name,
              COALESCE(a.slug, '')                                      AS slug,
              COALESCE(a.model_provider, '')                            AS model_provider,
              COALESCE(a.model_name, '')                                AS model_name,
              SUM(COALESCE((e.payload->'tokens'->>'input')::bigint, 0)) AS input_tokens,
              SUM(COALESCE((e.payload->'tokens'->>'output')::bigint, 0))AS output_tokens,
              COUNT(*)                                                  AS run_count,
              MAX(e.created_at)                                         AS last_seen_at
            FROM runtime_events e
            LEFT JOIN agents a ON a.id = e.agent_id
            WHERE
              e.workspace_id = :workspace_id
              AND e.event_type = 'node.completed'
              AND e.agent_id IS NOT NULL
              AND (:since IS NULL OR e.created_at >= :since)
            GROUP BY e.agent_id, a.name, a.slug, a.model_provider, a.model_name
            ORDER BY (
              SUM(COALESCE((e.payload->'tokens'->>'input')::bigint, 0))
              + SUM(COALESCE((e.payload->'tokens'->>'output')::bigint, 0))
            ) DESC
            """
        ).bindparams(
            # Explicit types — asyncpg can't infer them when `since` is None,
            # which is the common case (the UI defaults to "all time").
            bindparam("workspace_id", value=workspace_id, type_=sa.Uuid()),
            bindparam("since", value=since, type_=sa.DateTime(timezone=True)),
        )

        rows = (await self.db.execute(stmt)).mappings().all()
        return [dict(r) for r in rows]
