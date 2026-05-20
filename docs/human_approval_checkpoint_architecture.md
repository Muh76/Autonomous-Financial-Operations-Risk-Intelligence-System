# Human Approval Checkpoint Architecture

Human approval checkpoints provide controlled pauses for high-impact investigation decisions. They
let the graph stop before final escalation, collect an authorized human decision, preserve an audit
trail, and resume the workflow with deterministic routing.

Example policy:

```text
HIGH or CRITICAL risk investigation
  -> escalation_router
  -> human_approval_checkpoint
  -> pause for senior investigator or compliance officer
  -> approved: continue to final escalation/reporting
  -> rejected: route to evidence expansion, remediation, or closure
```

## 1. Approval Workflow Architecture

The approval architecture has five layers:

```text
LangGraph workflow
  -> checkpoint node
  -> approval service
  -> approval/audit repository
  -> reviewer UI or case-management queue
```

Core responsibilities:

- `escalation_router`: decides whether a case requires human approval.
- `human_approval_checkpoint`: pauses execution while approvals are pending.
- `ApprovalCheckpointService`: applies human decisions to append-only workflow state.
- persistent memory/audit store: records approval request, decision, reviewer, rationale,
  and timestamps.
- workflow resume API: reloads checkpointed state and continues from the approved/rejected route.

Approval checkpoints should be policy-driven. Typical checkpoint policies include:

- high-risk escalation before final action
- sanctions or watchlist hit before account hold
- suspicious activity report draft before regulatory submission
- low-confidence critic result before case closure
- repeated retry exhaustion before fallback disposition

## 2. Workflow Pause/Resume Strategy

Pause strategy:

1. The graph reaches `escalation_router`.
2. The router appends an `ApprovalRequest` with `status="pending"`.
3. The graph routes to `human_approval_checkpoint`.
4. The checkpoint node detects the pending approval.
5. The graph returns `status="awaiting_human_approval"` and stops.
6. A durable LangGraph checkpointer stores the paused thread.
7. PostgreSQL stores the approval request and workflow event trail.
8. Redis may cache the active approval queue for low-latency UI reads.

Resume strategy:

1. A reviewer submits an approval or rejection through an authenticated API.
2. The approval service validates reviewer role and approval status.
3. The decision is appended to approval history, not destructively overwritten.
4. The workflow state receives a continuation route.
5. The graph resumes from the checkpoint using the same `thread_id`.
6. Approved cases continue to final escalation/reporting.
7. Rejected cases route to remediation, evidence expansion, or failure handling.

Append-only approval state is intentional. It preserves the original request and the later decision.
When reading state, use latest-status-by-`approval_id` semantics.

## 3. Approval State Management

The canonical state object is `ApprovalRequest`:

```python
class ApprovalRequest(TypedDict):
    approval_id: str
    checkpoint_name: str
    reason: str
    required_role: str
    status: ApprovalStatus
    requested_at: NotRequired[str]
    decided_at: NotRequired[str]
    reviewer_id: NotRequired[str]
    reviewer_rationale: NotRequired[str]
```

Supported states:

```text
not_required
pending
approved
rejected
```

Recommended state transitions:

```text
not_required -> pending
pending -> approved
pending -> rejected
approved -> terminal
rejected -> terminal or remediation
```

The implementation in `app/services/approval_checkpoints.py` provides:

- `latest_approval_states(...)`
- `ApprovalCheckpointService.pending_approvals(...)`
- `ApprovalCheckpointService.is_paused_for_approval(...)`
- `ApprovalCheckpointService.apply_decision(...)`

`apply_decision(...)` appends a new approval record with the reviewer decision, rationale, and
continuation route.

## 4. Audit Logging Strategy

Approval audit logs should capture:

- approval ID
- checkpoint name
- case ID
- tenant ID
- workflow thread ID
- risk band and escalation level at time of request
- required reviewer role
- reviewer identity
- decision
- rationale
- request timestamp
- decision timestamp
- policy version
- state hash or snapshot ID

Use multiple audit layers:

- LangGraph checkpoint: execution resume point.
- PostgreSQL workflow history: business event trail.
- PostgreSQL approval records: reviewer decision trail.
- Redis active queue: operational cache only.
- Object storage or evidence registry: supporting evidence references.

Audit events should be append-only. Corrections should create new events rather than mutate old
ones.

Recommended event names:

```text
approval_requested
workflow_paused_for_approval
approval_assigned
approval_approved
approval_rejected
workflow_resumed_after_approval
approval_expired
approval_reassigned
```

## 5. LangGraph Integration Approach

The current workflow already routes high-risk decisions through `escalation_router` and
`human_approval_checkpoint`.

Production LangGraph integration should use a durable checkpointer and an interrupt/resume boundary:

```python
workflow = build_investigation_workflow(
    checkpointer=postgres_checkpointer,
    interrupt_before=["human_approval_checkpoint"],
)
```

When the graph pauses:

```text
thread_id = state["thread_id"]
status = "awaiting_human_approval"
approval_id = pending_approval["approval_id"]
```

When a reviewer decides:

```python
service = ApprovalCheckpointService()
patch = service.apply_decision(
    state,
    ApprovalDecisionRequest(
        approval_id=approval_id,
        reviewer_id="senior-investigator-123",
        decision="approved",
        rationale="Evidence supports senior review escalation.",
    ),
)
```

The patch is merged into the workflow state and the graph resumes with the same `thread_id`.

Continuation routing:

```text
approved -> report_generation or final escalation action
rejected -> evidence_expansion, remediation, or workflow_failure
expired  -> reassignment or escalation_router
```

For enterprise systems, keep final external actions outside the approval checkpoint itself. The
checkpoint should only authorize continuation; the next graph node should perform the controlled
action with idempotency keys and full audit logging.
