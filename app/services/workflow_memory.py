from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.cache.redis import RedisStore
from app.repositories.memory import WorkflowMemoryRepository


def _model_dict(model: Any, fields: list[str]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field in fields:
        value = getattr(model, field)
        if isinstance(value, datetime):
            payload[field] = value.isoformat()
        elif isinstance(value, Decimal):
            payload[field] = float(value)
        else:
            payload[field] = value
    return payload


@dataclass(slots=True)
class AgentMemoryRequest:
    tenant_id: str
    case_id: str
    workflow_id: str
    agent_name: str
    summary_types: list[str] | None = None
    include_related_transactions: bool = True
    include_evidence: bool = True
    include_prior_escalations: bool = True
    include_retry_history: bool = True
    include_critic_feedback: bool = True


class WorkflowMemoryService:
    """Coordinates Redis working memory and PostgreSQL durable memory for agents."""

    def __init__(
        self,
        *,
        repository: WorkflowMemoryRepository,
        redis_store: RedisStore,
    ) -> None:
        self._repository = repository
        self._redis = redis_store

    async def build_agent_context(self, request: AgentMemoryRequest) -> dict[str, Any]:
        active_memory = await self._redis.get_active_workflow_memory(request.workflow_id)
        scratchpad = await self._redis.get_agent_scratchpad(
            request.workflow_id,
            request.agent_name,
        )
        handoffs = await self._redis.get_agent_handoffs(request.workflow_id)
        summaries = await self._repository.list_summaries(
            tenant_id=request.tenant_id,
            case_id=request.case_id,
            summary_types=request.summary_types,
        )

        context: dict[str, Any] = {
            "tenant_id": request.tenant_id,
            "case_id": request.case_id,
            "workflow_id": request.workflow_id,
            "agent_name": request.agent_name,
            "short_term": {
                "active_memory": active_memory or {},
                "scratchpad": scratchpad or {},
                "handoffs": handoffs[-10:],
            },
            "persistent": {
                "summaries": [
                    _model_dict(
                        summary,
                        [
                            "id",
                            "summary_type",
                            "summary",
                            "source_refs",
                            "created_at",
                            "updated_at",
                        ],
                    )
                    for summary in summaries
                ],
            },
        }

        if request.include_related_transactions:
            context["persistent"]["related_transactions"] = [
                _model_dict(
                    memory,
                    [
                        "id",
                        "transaction_id",
                        "related_transaction_id",
                        "counterparty_id",
                        "relationship_type",
                        "risk_signal",
                        "amount",
                        "currency",
                        "confidence",
                        "created_at",
                    ],
                )
                for memory in await self._repository.list_related_transactions(
                    tenant_id=request.tenant_id,
                    case_id=request.case_id,
                )
            ]

        if request.include_evidence:
            context["persistent"]["evidence"] = [
                _model_dict(
                    evidence,
                    [
                        "id",
                        "evidence_type",
                        "source_system",
                        "source_reference",
                        "content_hash",
                        "storage_uri",
                        "created_at",
                    ],
                )
                for evidence in await self._repository.list_evidence(
                    tenant_id=request.tenant_id,
                    case_id=request.case_id,
                )
            ]

        if request.include_prior_escalations:
            context["persistent"]["prior_escalations"] = [
                _model_dict(
                    escalation,
                    [
                        "id",
                        "escalation_type",
                        "reason",
                        "severity",
                        "decision",
                        "assigned_to",
                        "created_at",
                        "resolved_at",
                    ],
                )
                for escalation in await self._repository.list_prior_escalations(
                    tenant_id=request.tenant_id,
                    case_id=request.case_id,
                )
            ]

        if request.include_retry_history:
            context["persistent"]["retry_history"] = [
                _model_dict(
                    retry,
                    [
                        "id",
                        "workflow_step",
                        "agent_name",
                        "retry_number",
                        "failure_reason",
                        "retry_strategy",
                        "created_at",
                    ],
                )
                for retry in await self._repository.list_retry_history(
                    tenant_id=request.tenant_id,
                    case_id=request.case_id,
                )
            ]

        if request.include_critic_feedback:
            latest = await self._redis.get_latest_critic_feedback(request.workflow_id)
            unresolved = await self._repository.list_unresolved_critic_feedback(
                tenant_id=request.tenant_id,
                case_id=request.case_id,
            )
            context["short_term"]["latest_critic_feedback"] = latest or {}
            context["persistent"]["unresolved_critic_feedback"] = [
                _model_dict(
                    feedback,
                    [
                        "id",
                        "workflow_step",
                        "critic_agent",
                        "target_agent",
                        "feedback_type",
                        "severity",
                        "finding",
                        "recommendation",
                        "created_at",
                    ],
                )
                for feedback in unresolved
            ]

        return context

    async def checkpoint_short_term_memory(
        self,
        *,
        workflow_id: str,
        active_memory: dict[str, Any],
        ttl_seconds: int = 1800,
    ) -> None:
        await self._redis.set_active_workflow_memory(
            workflow_id,
            active_memory,
            ttl_seconds=ttl_seconds,
        )

    async def record_agent_handoff(
        self,
        *,
        workflow_id: str,
        from_agent: str,
        to_agent: str,
        reason: str,
        context_summary: str,
        required_action: str,
        confidence: float | None = None,
    ) -> None:
        handoff: dict[str, Any] = {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "reason": reason,
            "context_summary": context_summary,
            "required_action": required_action,
        }
        if confidence is not None:
            handoff["confidence"] = confidence
        await self._redis.append_agent_handoff(workflow_id, handoff)

    async def record_retry(
        self,
        *,
        tenant_id: str,
        case_id: str,
        workflow_id: str,
        workflow_step: str,
        failure_reason: str,
        retry_strategy: str,
        agent_name: str | None = None,
        previous_output: dict[str, Any] | None = None,
    ) -> int:
        retry_number = await self._redis.increment_retry_count(workflow_id, workflow_step)
        await self._repository.record_retry_event(
            tenant_id=tenant_id,
            case_id=case_id,
            workflow_step=workflow_step,
            agent_name=agent_name,
            retry_number=retry_number,
            failure_reason=failure_reason,
            retry_strategy=retry_strategy,
            previous_output=previous_output,
        )
        return retry_number
