from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agents.models import Agent


class AgentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        workspace_id: UUID,
        created_by: UUID,
        name: str,
        slug: str,
        role: str,
        system_prompt: str,
        model_provider: str,
        model_name: str,
        description: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        memory_config: dict[str, Any] | None = None,
        schedule_config: dict[str, Any] | None = None,
        guardrails_config: dict[str, Any] | None = None,
        interaction_rules: dict[str, Any] | None = None,
        limits_config: dict[str, Any] | None = None,
        skills_config: dict[str, Any] | None = None,
        provider_credentials: dict[str, Any] | None = None,
    ) -> Agent:
        agent = Agent(
            workspace_id=workspace_id,
            created_by=created_by,
            name=name,
            slug=slug,
            description=description,
            role=role,
            system_prompt=system_prompt,
            status="draft",
            model_provider=model_provider,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            memory_config=memory_config or {},
            schedule_config=schedule_config or {},
            guardrails_config=guardrails_config or {},
            interaction_rules=interaction_rules or {},
            limits_config=limits_config or {},
            skills_config=skills_config or {},
            provider_credentials=provider_credentials or {},
        )
        self.db.add(agent)
        await self.db.commit()
        await self.db.refresh(agent)
        return agent

    async def list_in_workspace(
        self,
        workspace_id: UUID,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[Agent], int]:
        """Paginated workspace-scoped agent list, newest first.

        Excludes soft-deleted agents. Permission check (workspace
        membership) lives in the service layer.
        """

        offset = (page - 1) * page_size

        items_q = (
            select(Agent)
            .where(
                Agent.workspace_id == workspace_id,
                Agent.deleted_at.is_(None),
            )
            .order_by(Agent.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        total_q = select(func.count(Agent.id)).where(
            Agent.workspace_id == workspace_id,
            Agent.deleted_at.is_(None),
        )

        items = list((await self.db.execute(items_q)).scalars())
        total = (await self.db.execute(total_q)).scalar_one()
        return items, total

    async def get_in_workspace(
        self,
        workspace_id: UUID,
        agent_id: UUID,
    ) -> Agent | None:
        """Return the agent iff it lives in the given workspace and is live."""

        stmt = select(Agent).where(
            Agent.id == agent_id,
            Agent.workspace_id == workspace_id,
            Agent.deleted_at.is_(None),
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def update(self, agent: Agent, **fields: Any) -> Agent:
        """Partial update. Only sets keys explicitly passed in."""

        for key, value in fields.items():
            setattr(agent, key, value)
        await self.db.commit()
        await self.db.refresh(agent)
        return agent
