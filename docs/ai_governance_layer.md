# AI Governance Layer

This document defines a production-style AI governance layer for a multi-agent enterprise AI
platform. The layer provides audit trails, workflow traceability, agent decision logging,
escalation tracking, approval checkpoints, evidence traceability, and compliance audit support for
long-running financial investigation workflows.

The governance layer is not a passive logging feature. It is an operational control plane that
records what happened, why it happened, which evidence supported it, who approved it, and which
policy or workflow version governed the decision.

## 1. Governance Architecture

```text
LangGraph workflow
  -> governance middleware
      -> workflow lineage tracker
      -> agent decision logger
      -> evidence traceability index
      -> escalation audit service
      -> approval checkpoint audit service
      -> compliance audit repository
      -> governance event stream
  -> PostgreSQL audit store
  -> Redis active workflow cache
  -> dashboard, replay, audit export, and compliance review interfaces
```

Core components:

- **Governance middleware**: wraps each workflow node and records inputs, outputs, state deltas,
  validation results, and routing decisions.
- **Workflow lineage tracker**: records node sequence, edge traversal, retries, pauses, resumes,
  and final disposition.
- **Agent decision logger**: captures agent rationale, confidence, model or rule version, evidence
  references, and recommended actions.
- **Evidence traceability index**: links claims, citations, evidence records, retrieval chunks,
  findings, reports, and decisions.
- **Escalation audit service**: records escalation triggers, risk bands, required roles,
  escalation rationale, and outcome.
- **Approval checkpoint audit service**: records human review requests, decisions, reviewer roles,
  timestamps, and rationale.
- **Compliance audit repository**: stores policy versions, compliance rule results, citations,
  exceptions, SAR-like review decisions, and audit exports.
- **Governance event stream**: emits append-only events for dashboards, observability, SIEM, and
  replay consumers.

Governance records should be append-only and versioned. Corrections should create superseding
records rather than overwriting prior audit history.

## 2. Audit Logging Framework

Audit logging should capture both operational events and decision events.

Audit event schema:

```text
audit_event_id
tenant_id
case_id
workflow_run_id
thread_id
event_type
event_status
source_node
agent_role
actor_type
actor_id
occurred_at
policy_version
workflow_version
schema_version
input_refs
output_refs
evidence_refs
decision_refs
trace_refs
metadata
audit_hash
previous_audit_hash
```

Event families:

- `workflow_started`
- `node_started`
- `node_completed`
- `node_failed`
- `agent_decision_recorded`
- `evidence_validated`
- `critic_validation_completed`
- `risk_score_computed`
- `compliance_rule_evaluated`
- `escalation_recommended`
- `approval_requested`
- `approval_decided`
- `workflow_resumed`
- `report_generated`
- `final_action_blocked`
- `workflow_closed`

Audit requirements:

- Store canonical records in PostgreSQL.
- Use Redis only for active workflow views, queues, locks, and short-lived status.
- Include policy, workflow, schema, model, and rule versions with each decision.
- Hash audit records to support tamper-evident replay.
- Avoid storing raw restricted documents in workflow state; store governed references and hashes.
- Keep audit events tenant-scoped and access-controlled.

## 3. Decision Traceability Strategy

Every automated or human decision should be explainable from state, evidence, policy, and prior
workflow events.

Decision record:

```text
decision_id
decision_type
source_agent
source_node
decision
rationale
confidence
calibrated_confidence
risk_band
severity
recommended_actions
evidence_refs
citation_refs
policy_refs
validation_refs
approval_refs
model_version
rule_version
created_at
```

Traceability links:

- transaction analysis decisions link to transaction IDs and behavioral indicators
- fraud decisions link to fraud signals, heuristics, and transaction evidence
- compliance decisions link to rule IDs, policy versions, and policy citations
- retrieval decisions link to document IDs, chunk IDs, citations, and rerank scores
- risk scoring decisions link to weighted inputs and critic feedback
- critic decisions link to unsupported claims, contradictions, citation checks, and score breakdowns
- report decisions link to findings, citations, evidence IDs, and approval status

Decision traceability should support a simple audit question:

```text
Given this final recommendation, show every upstream claim, evidence item, citation, validation
result, approval, and workflow route that contributed to it.
```

## 4. Escalation Audit System

Escalation tracking should make high-impact operational decisions reconstructable.

Escalation audit record:

```text
escalation_id
case_id
workflow_run_id
trigger_node
trigger_reason
risk_band
escalation_level
required_role
recommended_actions
evidence_refs
critic_refs
compliance_refs
approval_refs
status
created_at
resolved_at
resolution
resolution_actor
resolution_rationale
```

Escalation lifecycle:

1. Risk scoring, compliance validation, critic validation, or policy routing triggers escalation.
2. Escalation router creates an append-only escalation event.
3. Approval checkpoint creates a review request when policy requires human approval.
4. Human reviewer approves, rejects, requests more evidence, or blocks final action.
5. Workflow resumes with a route tied to the escalation and approval IDs.
6. Final report references the escalation record and supporting evidence.

Escalation audit controls:

- require evidence references for high and critical escalations
- require approval references for manual escalation outcomes
- require policy references for compliance-driven escalations
- record all retry, evidence expansion, and route changes
- prevent final action when escalation status is unresolved

## 5. Workflow Lineage Tracking

Workflow lineage records how the workflow moved through the graph and how state changed over time.

Lineage model:

```text
workflow_run_id
thread_id
case_id
started_at
completed_at
workflow_version
entry_node
final_node
final_status
node_traces
edge_traversals
state_snapshot_refs
retry_refs
approval_refs
escalation_refs
validation_refs
report_refs
```

Lineage events:

- node execution order
- edge traversal and route condition
- retry attempts and failure class
- timeout fallback path
- human approval pause and resume
- evidence expansion path
- critic or evidence validation gate decisions
- escalation branch and final disposition

State lineage should use immutable snapshots or patch records:

```text
snapshot_id
parent_snapshot_id
state_version
changed_fields
changed_by_node
created_at
audit_event_id
hash
```

This supports investigation replay, regression analysis, incident review, and auditor-facing
explanations.

## 6. Evidence Traceability Design

Evidence traceability links source material to claims, decisions, validations, and reports.

Evidence lineage record:

```text
evidence_id
source_type
source_uri
source_version
source_hash
retrieved_at
created_by_agent
claim_refs
finding_refs
citation_refs
validation_refs
decision_refs
report_refs
access_label
retention_policy
metadata
```

Traceability rules:

- Every report finding should link to evidence IDs or citation IDs.
- Every compliance recommendation should link to policy refs and rule results.
- Every risk score should link to upstream signals and evidence references.
- Every critic finding should link to claims, citations, contradictions, or missing evidence.
- Every final escalation should link to evidence validation and approval status.

Evidence audit views:

- **source-to-decision**: show every decision influenced by a source record
- **decision-to-source**: show all evidence and citations behind a decision
- **claim-to-citation**: show whether a generated claim has valid citation support
- **report-to-evidence**: show all report findings and their evidence chain
- **approval-to-evidence**: show what evidence a human reviewer saw before deciding

Compliance audit support:

- preserve policy version and effective date for each compliance decision
- retain rule inputs and outputs for replay
- record reviewer identity and role for human approvals
- export case-level audit bundles with workflow lineage, evidence lineage, decisions, approvals,
  escalations, and final reports
- support retention, legal hold, and tenant-specific access controls

Operational governance metrics:

- unsupported claim rate by agent
- invalid citation rate by workflow
- approval override rate by reviewer role
- escalation aging and unresolved escalation count
- evidence completeness score by case type
- critic failure rate by model or rule version
- report correction rate after human review

