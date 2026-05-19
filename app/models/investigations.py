from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(tz=UTC)


class Base(DeclarativeBase):
    """Base class for investigation persistence models."""


class InvestigationRun(Base):
    """Current business state for one resumable investigation workflow run."""

    __tablename__ = "investigation_runs"
    __table_args__ = (
        Index("ix_investigation_runs_tenant_status", "tenant_id", "status"),
        Index("ix_investigation_runs_thread_id", "thread_id", unique=True),
        Index("ix_investigation_runs_transaction_id", "transaction_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(128), index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    thread_id: Mapped[str] = mapped_column(String(256), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(128), nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_band: Mapped[str | None] = mapped_column(String(32))
    escalation_level: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[float | None] = mapped_column(Float)
    latest_snapshot_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
    )

    snapshots: Mapped[list["WorkflowSnapshot"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    events: Mapped[list["WorkflowHistoryEvent"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    checkpoints: Mapped[list["WorkflowCheckpointRef"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class WorkflowSnapshot(Base):
    """Serialized workflow state snapshot for resume, inspection, and audit exports."""

    __tablename__ = "workflow_snapshots"
    __table_args__ = (
        Index("ix_workflow_snapshots_run_step", "run_id", "step_number"),
        Index("ix_workflow_snapshots_thread_id", "thread_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("investigation_runs.id"), nullable=False)
    thread_id: Mapped[str] = mapped_column(String(256), nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    node_name: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    state_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    run: Mapped[InvestigationRun] = relationship(back_populates="snapshots")


class WorkflowHistoryEvent(Base):
    """Append-only investigation workflow history event."""

    __tablename__ = "workflow_history_events"
    __table_args__ = (
        Index("ix_workflow_history_events_run_time", "run_id", "created_at"),
        Index("ix_workflow_history_events_node", "node_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("investigation_runs.id"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    node_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    event_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    run: Mapped[InvestigationRun] = relationship(back_populates="events")


class WorkflowCheckpointRef(Base):
    """Metadata pointer to LangGraph checkpointer storage for a thread/namespace/checkpoint."""

    __tablename__ = "workflow_checkpoint_refs"
    __table_args__ = (
        Index("ix_workflow_checkpoint_refs_thread_ns", "thread_id", "checkpoint_namespace"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("investigation_runs.id"), nullable=False)
    thread_id: Mapped[str] = mapped_column(String(256), nullable=False)
    checkpoint_namespace: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    checkpoint_id: Mapped[str] = mapped_column(String(256), nullable=False)
    checkpoint_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    run: Mapped[InvestigationRun] = relationship(back_populates="checkpoints")
