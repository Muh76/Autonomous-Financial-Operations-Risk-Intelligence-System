from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investigations import InvestigationRun
from app.models.memory import (
    CriticFeedbackMemory,
    EscalationMemory,
    EvidenceMemoryEvent,
    EvidenceMemoryItem,
    InvestigationMemorySummary,
    RelatedTransactionMemory,
    RetryMemoryEvent,
)


def _now() -> datetime:
    return datetime.now(tz=UTC)


class WorkflowMemoryRepository:
    """PostgreSQL repository for durable enterprise workflow memory."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_run_id(self, *, tenant_id: str, case_id: str) -> str | None:
        result = await self._session.execute(
            select(InvestigationRun.id)
            .where(InvestigationRun.tenant_id == tenant_id)
            .where(InvestigationRun.case_id == case_id)
            .order_by(InvestigationRun.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def save_summary(
        self,
        *,
        tenant_id: str,
        case_id: str,
        summary_type: str,
        summary: str,
        investigation_id: str | None = None,
        run_id: str | None = None,
        source_refs: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> InvestigationMemorySummary:
        memory = InvestigationMemorySummary(
            tenant_id=tenant_id,
            case_id=case_id,
            investigation_id=investigation_id,
            run_id=run_id,
            summary_type=summary_type,
            summary=summary,
            source_refs=source_refs or [],
            summary_metadata=metadata or {},
        )
        self._session.add(memory)
        return memory

    async def list_summaries(
        self,
        *,
        tenant_id: str,
        case_id: str,
        summary_types: list[str] | None = None,
        limit: int = 20,
    ) -> list[InvestigationMemorySummary]:
        statement = (
            select(InvestigationMemorySummary)
            .where(InvestigationMemorySummary.tenant_id == tenant_id)
            .where(InvestigationMemorySummary.case_id == case_id)
            .order_by(InvestigationMemorySummary.updated_at.desc())
            .limit(limit)
        )
        if summary_types:
            statement = statement.where(InvestigationMemorySummary.summary_type.in_(summary_types))
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def add_related_transaction(
        self,
        *,
        tenant_id: str,
        case_id: str,
        transaction_id: str,
        relationship_type: str,
        run_id: str | None = None,
        related_transaction_id: str | None = None,
        counterparty_id: str | None = None,
        risk_signal: str | None = None,
        amount: float | None = None,
        currency: str | None = None,
        transaction_timestamp: datetime | None = None,
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RelatedTransactionMemory:
        memory = RelatedTransactionMemory(
            tenant_id=tenant_id,
            case_id=case_id,
            run_id=run_id,
            transaction_id=transaction_id,
            related_transaction_id=related_transaction_id,
            counterparty_id=counterparty_id,
            relationship_type=relationship_type,
            risk_signal=risk_signal,
            amount=amount,
            currency=currency,
            transaction_timestamp=transaction_timestamp,
            confidence=confidence,
            memory_metadata=metadata or {},
        )
        self._session.add(memory)
        return memory

    async def list_related_transactions(
        self,
        *,
        tenant_id: str,
        case_id: str,
        relationship_types: list[str] | None = None,
        limit: int = 100,
    ) -> list[RelatedTransactionMemory]:
        statement = (
            select(RelatedTransactionMemory)
            .where(RelatedTransactionMemory.tenant_id == tenant_id)
            .where(RelatedTransactionMemory.case_id == case_id)
            .order_by(RelatedTransactionMemory.created_at.desc())
            .limit(limit)
        )
        if relationship_types:
            statement = statement.where(
                RelatedTransactionMemory.relationship_type.in_(relationship_types)
            )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def add_evidence(
        self,
        *,
        tenant_id: str,
        case_id: str,
        evidence_type: str,
        source_system: str,
        run_id: str | None = None,
        source_reference: str | None = None,
        content_hash: str | None = None,
        storage_uri: str | None = None,
        extracted_text: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceMemoryItem:
        evidence = EvidenceMemoryItem(
            tenant_id=tenant_id,
            case_id=case_id,
            run_id=run_id,
            evidence_type=evidence_type,
            source_system=source_system,
            source_reference=source_reference,
            content_hash=content_hash,
            storage_uri=storage_uri,
            extracted_text=extracted_text,
            evidence_metadata=metadata or {},
        )
        self._session.add(evidence)
        await self._session.flush()
        await self.append_evidence_event(
            tenant_id=tenant_id,
            case_id=case_id,
            evidence_id=evidence.id,
            event_type="collected",
            agent_name=None,
            notes="Evidence memory item created.",
        )
        return evidence

    async def append_evidence_event(
        self,
        *,
        tenant_id: str,
        case_id: str,
        evidence_id: str,
        event_type: str,
        agent_name: str | None,
        notes: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> EvidenceMemoryEvent:
        event = EvidenceMemoryEvent(
            tenant_id=tenant_id,
            case_id=case_id,
            evidence_id=evidence_id,
            event_type=event_type,
            agent_name=agent_name,
            notes=notes,
            event_payload=payload or {},
        )
        self._session.add(event)
        return event

    async def list_evidence(
        self,
        *,
        tenant_id: str,
        case_id: str,
        evidence_types: list[str] | None = None,
        limit: int = 100,
    ) -> list[EvidenceMemoryItem]:
        statement = (
            select(EvidenceMemoryItem)
            .where(EvidenceMemoryItem.tenant_id == tenant_id)
            .where(EvidenceMemoryItem.case_id == case_id)
            .order_by(EvidenceMemoryItem.created_at.desc())
            .limit(limit)
        )
        if evidence_types:
            statement = statement.where(EvidenceMemoryItem.evidence_type.in_(evidence_types))
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def create_escalation(
        self,
        *,
        tenant_id: str,
        case_id: str,
        escalation_type: str,
        reason: str,
        severity: str,
        run_id: str | None = None,
        decision: str | None = None,
        escalated_by: str | None = None,
        assigned_to: str | None = None,
    ) -> EscalationMemory:
        escalation = EscalationMemory(
            tenant_id=tenant_id,
            case_id=case_id,
            run_id=run_id,
            escalation_type=escalation_type,
            reason=reason,
            severity=severity,
            decision=decision,
            escalated_by=escalated_by,
            assigned_to=assigned_to,
        )
        self._session.add(escalation)
        return escalation

    async def list_prior_escalations(
        self,
        *,
        tenant_id: str,
        case_id: str,
        limit: int = 50,
    ) -> list[EscalationMemory]:
        result = await self._session.execute(
            select(EscalationMemory)
            .where(EscalationMemory.tenant_id == tenant_id)
            .where(EscalationMemory.case_id == case_id)
            .order_by(EscalationMemory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def record_retry_event(
        self,
        *,
        tenant_id: str,
        case_id: str,
        workflow_step: str,
        retry_number: int,
        failure_reason: str,
        retry_strategy: str,
        run_id: str | None = None,
        agent_name: str | None = None,
        previous_output: dict[str, Any] | None = None,
    ) -> RetryMemoryEvent:
        retry = RetryMemoryEvent(
            tenant_id=tenant_id,
            case_id=case_id,
            run_id=run_id,
            workflow_step=workflow_step,
            agent_name=agent_name,
            retry_number=retry_number,
            failure_reason=failure_reason,
            retry_strategy=retry_strategy,
            previous_output=previous_output or {},
        )
        self._session.add(retry)
        return retry

    async def list_retry_history(
        self,
        *,
        tenant_id: str,
        case_id: str,
        workflow_step: str | None = None,
        limit: int = 100,
    ) -> list[RetryMemoryEvent]:
        statement = (
            select(RetryMemoryEvent)
            .where(RetryMemoryEvent.tenant_id == tenant_id)
            .where(RetryMemoryEvent.case_id == case_id)
            .order_by(RetryMemoryEvent.created_at.desc())
            .limit(limit)
        )
        if workflow_step is not None:
            statement = statement.where(RetryMemoryEvent.workflow_step == workflow_step)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def add_critic_feedback(
        self,
        *,
        tenant_id: str,
        case_id: str,
        critic_agent: str,
        feedback_type: str,
        severity: str,
        finding: str,
        run_id: str | None = None,
        workflow_step: str | None = None,
        target_agent: str | None = None,
        recommendation: str | None = None,
        accepted: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CriticFeedbackMemory:
        feedback = CriticFeedbackMemory(
            tenant_id=tenant_id,
            case_id=case_id,
            run_id=run_id,
            workflow_step=workflow_step,
            critic_agent=critic_agent,
            target_agent=target_agent,
            feedback_type=feedback_type,
            severity=severity,
            finding=finding,
            recommendation=recommendation,
            accepted=accepted,
            feedback_metadata=metadata or {},
        )
        self._session.add(feedback)
        return feedback

    async def list_unresolved_critic_feedback(
        self,
        *,
        tenant_id: str,
        case_id: str,
        limit: int = 50,
    ) -> list[CriticFeedbackMemory]:
        result = await self._session.execute(
            select(CriticFeedbackMemory)
            .where(CriticFeedbackMemory.tenant_id == tenant_id)
            .where(CriticFeedbackMemory.case_id == case_id)
            .where(CriticFeedbackMemory.resolved_at.is_(None))
            .order_by(CriticFeedbackMemory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def resolve_critic_feedback(self, *, feedback_id: str, accepted: bool) -> None:
        await self._session.execute(
            update(CriticFeedbackMemory)
            .where(CriticFeedbackMemory.id == feedback_id)
            .values(accepted=accepted, resolved_at=_now())
        )
