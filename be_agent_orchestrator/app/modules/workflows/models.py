from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, IdMixin, SoftDeleteMixin, TimestampMixin


class Workflow(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "workflows"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_workflows_workspace_slug"),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_workflows_status",
        ),
        Index("idx_workflows_workspace_id", "workspace_id"),
        Index("idx_workflows_status", "status"),
        Index("idx_workflows_graph_json_gin", "graph_json", postgresql_using="gin"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")

    graph_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    compiled_graph: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    published_version_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)


class WorkflowVersion(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "workflow_versions"
    __table_args__ = (
        UniqueConstraint(
            "workflow_id", "version_number", name="uq_workflow_versions_workflow_version"
        ),
        Index("idx_workflow_versions_workflow_id", "workflow_id"),
    )

    workflow_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    graph_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    compiled_graph: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    created_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class WorkflowTemplate(Base, IdMixin, TimestampMixin):
    __tablename__ = "workflow_templates"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    category: Mapped[str] = mapped_column(String(64), nullable=False)

    graph_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    required_agents: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    required_tools: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    is_system_template: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
