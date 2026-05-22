# Investigation Audit Trail System

This document defines a production-grade investigation audit trail system for enterprise financial
AI workflows. The system records workflow transitions, agent decisions, escalations, retries,
evidence retrieval, critic feedback, and final decisions as immutable-style, timestamped,
structured audit events that can power investigation replay and operational audit reviews.

The audit trail should be treated as a canonical system of record for workflow accountability. It
must explain what happened, when it happened, which agent or human actor caused it, what evidence
was available, and why the workflow moved to the next state.

## 1. Audit Trail Architecture

```text
LangGraph workflow node
  -> audit event builder
      -> workflow transition recorder
      -> agent decision recorder
      -> escalation recorder
      -> retry recorder
      -> evidence retrieval recorder
      -> critic feedback recorder
      -> final decision recorder
  -> audit repository
      -> PostgreSQL immutable audit events
      -> workflow snapshots
      -> checkpoint references
      -> replay indexes
  -> replay service
      -> timeline reconstruction
      -> state reconstruction
      -> decision lineage view
      -> evidence lineage view
```

Core principles:

- Audit records are append-only. Corrections create superseding events rather than modifying prior
  events.
- Every event is timestamped, tenant-scoped, case-scoped, and workflow-run-scoped.
- Every node transition should emit at least one audit event.
- Agent decisions should include confidence, rationale, model or rule version, and evidence refs.
- Human approvals should include actor identity, role, rationale, and decision timestamp.
- Final decisions should link to upstream evidence, critic validation, approvals, and reports.

## 2. Event Schema

Canonical audit event:

```text
audit_event_id
tenant_id
case_id
workflow_run_id
thread_id
sequence_number
event_type
event_status
source_node
target_node
agent_role
actor_type
actor_id
occurred_at
workflow_version
schema_version
policy_version
model_version
rule_version
correlation_id
causation_id
input_snapshot_id
output_snapshot_id
checkpoint_id
evidence_refs
citation_refs
decision_refs
approval_refs
escalation_refs
retry_refs
critic_refs
event_payload
audit_hash
previous_audit_hash
```

Event types:

- `workflow_started`
- `workflow_transitioned`
- `node_started`
- `node_completed`
- `node_failed`
- `agent_decision_recorded`
- `evidence_retrieved`
- `evidence_validated`
- `critic_feedback_recorded`
- `retry_scheduled`
- `retry_exhausted`
- `escalation_recommended`
- `escalation_resolved`
- `approval_requested`
- `approval_decided`
- `report_generated`
- `final_decision_recorded`
- `workflow_closed`

Event payloads should be structured JSON, not log strings. Free-form messages may exist for
readability, but auditors and replay systems should rely on typed fields.

## 3. Replay System Design

The replay system reconstructs the investigation from audit events, workflow snapshots, and
checkpoint references.

Replay modes:

- **Timeline replay**: list events in sequence with node, actor, status, and timestamp.
- **State replay**: reconstruct workflow state at a selected sequence number or snapshot.
- **Decision replay**: show the evidence, agent rationale, critic feedback, approvals, and route
  that produced a decision.
- **Escalation replay**: show escalation trigger, reviewer decision, and final outcome.
- **Evidence replay**: show retrieval events, citations, validation results, and report usage.

Replay pipeline:

1. Load audit events by `workflow_run_id` ordered by `sequence_number`.
2. Verify hash chain integrity with `previous_audit_hash`.
3. Load workflow snapshots and checkpoint references.
4. Build a timeline of node transitions, decisions, retries, approvals, and escalations.
5. Attach evidence, citation, critic, and report references to each event.
6. Render replay views for auditor, compliance officer, operator, or model risk reviewer.

Replay output:

```text
workflow_run_id
case_id
timeline
state_snapshots
decision_lineage
evidence_lineage
approval_history
escalation_history
critic_feedback_history
final_decision
integrity_status
```

Replay should be read-only and deterministic. If an audit event cannot be verified, replay should
surface an integrity warning instead of silently continuing.

## 4. Audit Repository Layer

The repository layer should provide append-only writes and ordered reads.

Repository responsibilities:

- append audit events
- allocate sequence numbers per workflow run
- compute audit hash and previous hash
- persist workflow snapshots
- persist checkpoint references
- list events by workflow, case, actor, node, event type, or date range
- load replay bundles
- export audit bundles for compliance review

Suggested interface:

```python
class InvestigationAuditRepository:
    async def append_event(self, event: AuditEventCreate) -> AuditEventRead: ...
    async def append_events(self, events: list[AuditEventCreate]) -> list[AuditEventRead]: ...
    async def list_events(self, workflow_run_id: str) -> list[AuditEventRead]: ...
    async def get_event(self, audit_event_id: str) -> AuditEventRead | None: ...
    async def get_latest_hash(self, workflow_run_id: str) -> str | None: ...
    async def load_replay_bundle(self, workflow_run_id: str) -> AuditReplayBundle: ...
```

PostgreSQL tables:

```text
investigation_audit_events
workflow_snapshots
workflow_checkpoint_refs
workflow_history_events
agent_decision_records
evidence_lineage_records
escalation_audit_records
approval_audit_records
```

Redis usage:

- active workflow audit cursor
- latest sequence number cache
- replay request status
- short-lived dashboard timeline cache
- idempotency keys for retry-safe event writes

Repository constraints:

- unique `(workflow_run_id, sequence_number)`
- unique idempotency key for event creation
- non-null tenant, case, workflow run, event type, and timestamp
- immutable event payload after insertion
- indexed event type, source node, actor, and occurred timestamp

## 5. Workflow Integration

Audit integration should be built into workflow execution boundaries.

Node lifecycle:

```text
before node:
  append node_started
  save input snapshot reference

after node success:
  append node_completed
  append agent_decision_recorded when decision fields exist
  append workflow_transitioned when next_route changes
  save output snapshot reference

after node failure:
  append node_failed
  append retry_scheduled or retry_exhausted
  save failure snapshot reference
```

Agent-specific audit events:

- transaction analysis: transaction aggregates, anomaly indicators, chain analysis refs
- fraud detection: fraud signals, heuristics, score, risk band, recommended actions
- compliance validation: rule results, policy refs, citations, escalation recommendation
- retrieval agent: query, retrieved document IDs, citation IDs, grounding scores
- risk scoring: weighted inputs, score components, severity, escalation priority
- critic agent: findings, contradictions, confidence calibration, reliability score
- reporting agent: report ID, finding refs, citations, confidence, final report URI

Workflow gates:

- Evidence expansion should link to the evidence gap that caused it.
- Human approval should link to the exact state and evidence presented to the reviewer.
- Escalation should link to risk, compliance, critic, and evidence validation records.
- Final decision should link to report, approval, escalation, and validation IDs.

Operational requirements:

- emit structured logs and audit records from the same workflow context
- preserve ordering across parallel branches using branch IDs and fan-in sequence events
- use idempotency keys for retries so duplicate events are detectable
- include trace IDs for OpenTelemetry correlation
- expose replay APIs using read-only audit projections
- redact or reference restricted source content according to tenant policy

