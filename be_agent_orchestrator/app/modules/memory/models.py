"""Memory module — no SQLAlchemy models live here anymore.

The original ``AgentMemory`` table (``agent_memories``) was dropped in
migration 0008. Long-term memory is now managed entirely by mem0 in the
``agent_memories_mem0`` pgvector collection; mem0 owns that schema.

The module entry-point (``app/db/models.py`` + ``alembic/env.py``) still
imports this file so SQLAlchemy's metadata stays consistent across the
codebase — keeping the file as an empty placeholder is cheaper than
hunting down every importer.
"""
