import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.graph.state import InvestigationState, WorkflowEvent
from app.models.investigations import (
    InvestigationRun,
    WorkflowCheckpointRef,
    WorkflowHistoryEvent,
    WorkflowSnapshot,
)


def serialize_state(state: InvestigationState) -> dict[str, Any]:
    """Return a JSON-serializable state payload for PostgreSQL JSONB storage."""

    return json.loads(json.dumps(state, default=str, separators=(",", ":")))


def state_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class InvestigationRepository:
    """Repository for durable investigation workflow runs, snapshots, and history."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_run(self, state: InvestigationState) -> InvestigationRun:
        result = await self._session.execute(
            select(InvestigationRun).where(InvestigationRun.thread_id == state["thread_id"])
        )
        run = result.scalar_one_or_none()
        if run is None:
            run = InvestigationRun(
                case_id=state["case_id"],
                tenant_id=state["tenant_id"],
                thread_id=state["thread_id"],
                transaction_id=state["transaction_id"],
                workflow_version=state["workflow_version"],
                schema_version=state["schema_version"],
                status=state["status"],
            )
            self._session.add(run)

        run.case_id = state["case_id"]
        run.tenant_id = state["tenant_id"]
        run.transaction_id = state["transaction_id"]
        run.workflow_version = state["workflow_version"]
        run.schema_version = state["schema_version"]
        run.status = state["status"]
        run.risk_band = state.get("risk_band")
        run.escalation_level = state.get("escalation_level")
        run.confidence = state.get("confidence")
        return run

    async def save_snapshot(
        self,
        state: InvestigationState,
        *,
        node_name: str,
        step_number: int,
    ) -> WorkflowSnapshot:
        run = await self.upsert_run(state)
        payload = serialize_state(state)
        snapshot = WorkflowSnapshot(
            run=run,
            thread_id=state["thread_id"],
            step_number=step_number,
            node_name=node_name,
            state=payload,
            state_hash=state_hash(payload),
        )
        self._session.add(snapshot)
        await self._session.flush()
        run.latest_snapshot_id = snapshot.id
        return snapshot

    async def append_history_events(
        self,
        state: InvestigationState,
        events: list[WorkflowEvent],
    ) -> None:
        run = await self.upsert_run(state)
        for event in events:
            self._session.add(
                WorkflowHistoryEvent(
                    run=run,
                    event_id=event["event_id"],
                    node_name=event["node"],
                    status=event["status"],
                    message=event["message"],
                    event_payload=dict(event),
                )
            )

    async def save_checkpoint_ref(
        self,
        state: InvestigationState,
        *,
        checkpoint_id: str,
        checkpoint_namespace: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowCheckpointRef:
        run = await self.upsert_run(state)
        checkpoint = WorkflowCheckpointRef(
            run=run,
            thread_id=state["thread_id"],
            checkpoint_namespace=checkpoint_namespace,
            checkpoint_id=checkpoint_id,
            checkpoint_metadata=metadata or {},
        )
        self._session.add(checkpoint)
        return checkpoint

    async def get_run_by_thread_id(self, thread_id: str) -> InvestigationRun | None:
        result = await self._session.execute(
            select(InvestigationRun).where(InvestigationRun.thread_id == thread_id)
        )
        return result.scalar_one_or_none()

    async def get_latest_snapshot(self, thread_id: str) -> WorkflowSnapshot | None:
        result = await self._session.execute(
            select(WorkflowSnapshot)
            .where(WorkflowSnapshot.thread_id == thread_id)
            .order_by(WorkflowSnapshot.step_number.desc(), WorkflowSnapshot.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def load_latest_state(self, thread_id: str) -> dict[str, Any] | None:
        snapshot = await self.get_latest_snapshot(thread_id)
        if snapshot is None:
            return None
        return snapshot.state

    async def list_history(self, thread_id: str) -> list[WorkflowHistoryEvent]:
        run = await self.get_run_by_thread_id(thread_id)
        if run is None:
            return []
        result = await self._session.execute(
            select(WorkflowHistoryEvent)
            .where(WorkflowHistoryEvent.run_id == run.id)
            .order_by(WorkflowHistoryEvent.created_at.asc())
        )
        return list(result.scalars().all())
