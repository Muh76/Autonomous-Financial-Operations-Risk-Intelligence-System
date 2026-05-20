from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.investigations import Base


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(tz=UTC)


class InvestigationMemorySummary(Base):
    """Durable summarized memory for long-running investigations and agent context windows."""

    __tablename__ = "investigation_memory_summaries"
    __table_args__ = (
        Index("ix_memory_summaries_tenant_case", "tenant_id", "case_id"),
        Index("ix_memory_summaries_type", "summary_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("investigation_runs.id"))
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    investigation_id: Mapped[str | None] = mapped_column(String(128), index=True)
    summary_type: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    summary_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
    )


class RelatedTransactionMemory(Base):
    """Persistent related-transaction memory for cross-case and graph-style retrieval."""

    __tablename__ = "related_transaction_memory"
    __table_args__ = (
        Index("ix_related_tx_tenant_case", "tenant_id", "case_id"),
        Index("ix_related_tx_transaction", "transaction_id"),
        Index("ix_related_tx_counterparty", "counterparty_id"),
        Index("ix_related_tx_relationship", "relationship_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("investigation_runs.id"))
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(128), nullable=False)
    related_transaction_id: Mapped[str | None] = mapped_column(String(128), index=True)
    counterparty_id: Mapped[str | None] = mapped_column(String(128))
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_signal: Mapped[str | None] = mapped_column(String(128))
    amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str | None] = mapped_column(String(16))
    transaction_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    memory_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class EvidenceMemoryItem(Base):
    """Durable evidence registry entry with storage references and integrity metadata."""

    __tablename__ = "evidence_memory_items"
    __table_args__ = (
        Index("ix_evidence_memory_tenant_case", "tenant_id", "case_id"),
        Index("ix_evidence_memory_type", "evidence_type"),
        Index("ix_evidence_memory_source", "source_system", "source_reference"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("investigation_runs.id"))
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_system: Mapped[str] = mapped_column(String(128), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(256))
    content_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    storage_uri: Mapped[str | None] = mapped_column(Text)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    evidence_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class EvidenceMemoryEvent(Base):
    """Append-only evidence lifecycle history."""

    __tablename__ = "evidence_memory_events"
    __table_args__ = (
        Index("ix_evidence_memory_events_evidence", "evidence_id", "created_at"),
        Index("ix_evidence_memory_events_type", "event_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence_memory_items.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_name: Mapped[str | None] = mapped_column(String(128))
    notes: Mapped[str | None] = mapped_column(Text)
    event_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class EscalationMemory(Base):
    """Prior escalation memory for repeat-review and human oversight decisions."""

    __tablename__ = "escalation_memory"
    __table_args__ = (
        Index("ix_escalation_memory_tenant_case", "tenant_id", "case_id"),
        Index("ix_escalation_memory_type", "escalation_type"),
        Index("ix_escalation_memory_severity", "severity"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("investigation_runs.id"))
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    escalation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[str | None] = mapped_column(String(64))
    escalated_by: Mapped[str | None] = mapped_column(String(128))
    assigned_to: Mapped[str | None] = mapped_column(String(128))
    resolution_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RetryMemoryEvent(Base):
    """Durable retry history for workflow, node, and agent reliability analysis."""

    __tablename__ = "retry_memory_events"
    __table_args__ = (
        Index("ix_retry_memory_tenant_case", "tenant_id", "case_id"),
        Index("ix_retry_memory_run_step", "run_id", "workflow_step"),
        Index("ix_retry_memory_agent", "agent_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("investigation_runs.id"))
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    workflow_step: Mapped[str] = mapped_column(String(128), nullable=False)
    agent_name: Mapped[str | None] = mapped_column(String(128))
    retry_number: Mapped[int] = mapped_column(Integer, nullable=False)
    failure_reason: Mapped[str] = mapped_column(Text, nullable=False)
    retry_strategy: Mapped[str] = mapped_column(String(128), nullable=False)
    previous_output: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CriticFeedbackMemory(Base):
    """Durable critic and QA feedback history for corrective agent loops."""

    __tablename__ = "critic_feedback_memory"
    __table_args__ = (
        Index("ix_critic_feedback_tenant_case", "tenant_id", "case_id"),
        Index("ix_critic_feedback_target", "target_agent"),
        Index("ix_critic_feedback_unresolved", "tenant_id", "case_id", "resolved_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("investigation_runs.id"))
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    workflow_step: Mapped[str | None] = mapped_column(String(128))
    critic_agent: Mapped[str] = mapped_column(String(128), nullable=False)
    target_agent: Mapped[str | None] = mapped_column(String(128))
    feedback_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    finding: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str | None] = mapped_column(Text)
    accepted: Mapped[bool | None] = mapped_column()
    feedback_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
