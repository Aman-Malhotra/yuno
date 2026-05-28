"""Re-derive ``workflows.compiled_graph`` from ``graph_json`` for every row.

The SQL seed (`scripts/seed_demo.sql`) inserts each workflow with
``compiled_graph = '{}'`` because the langgraph-shape normalization is
Python (`app.modules.workflows.compiler.compile_graph`), not SQL. The
runtime executor needs a populated ``compiled_graph`` — without it, every
run dies with "workflow has no start node".

Run after `seed_demo.sql`:

    uv run python scripts/recompile_workflows.py

Or wired together via `make seed` (calls the SQL seed and then this).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running as `python scripts/recompile_workflows.py` from project root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import select  # noqa: E402

# Importing the aggregator populates Base.metadata with every module's
# tables — needed so SQLAlchemy can resolve the cross-table FKs on
# ``workflows`` (workspaces, users, …) when we commit.
import app.db.models  # noqa: E402, F401
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.modules.workflows.compiler import compile_graph  # noqa: E402
from app.modules.workflows.models import Workflow  # noqa: E402
from app.modules.workflows.schemas import WorkflowGraph  # noqa: E402


async def main() -> None:
    touched = 0
    async with AsyncSessionLocal() as db:
        workflows = (
            await db.execute(select(Workflow).where(Workflow.deleted_at.is_(None)))
        ).scalars().all()
        for workflow in workflows:
            try:
                graph = WorkflowGraph.model_validate(
                    workflow.graph_json or {"nodes": [], "edges": []}
                )
            except Exception as exc:
                print(f"  ✗ {workflow.slug}: graph_json invalid ({exc})")
                continue
            workflow.compiled_graph = compile_graph(graph)
            touched += 1
            print(
                f"  ✓ {workflow.slug}: "
                f"{len(graph.nodes)} nodes, {len(graph.edges)} edges, "
                f"entry={workflow.compiled_graph.get('entry')!r}"
            )
        await db.commit()
    print(f"recompiled {touched} workflow(s)")


if __name__ == "__main__":
    asyncio.run(main())
