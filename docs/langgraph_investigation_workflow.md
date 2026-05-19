# LangGraph Investigation Workflow

## Purpose

The investigation graph coordinates transaction investigation, fraud analysis, compliance
validation, risk scoring, critic validation, escalation, approval checkpoints, and report
generation. LangGraph owns durable orchestration and typed state transitions; external fraud,
compliance, case-management, and evidence systems should remain behind service or integration
interfaces.

## Production Shape

```text
normalize_intake
  -> collect_transaction_context
  -> fraud_analysis
  -> compliance_validation
  -> risk_scoring
  -> risk_router
       -> low_risk_auto_close -> report_generation
       -> medium_risk_compliance_review -> critic_validation
       -> escalation_router -> human_approval_checkpoint
       -> workflow_failure
```

Low-risk cases move through an auto-close branch into report generation. Medium-risk cases route
through enhanced compliance review and critic validation before reporting. High, critical, and
blocking cases route through escalation logic. Approval checkpoints currently prepare typed
approval records and stop the graph in `awaiting_human_approval`; once an analyst UI exists, this
is the place to enable LangGraph `interrupt(...)` and resume with a structured reviewer decision.

Retry and fallback routes are handled with conditional edges after resilient nodes:

```text
collect_transaction_context -> fraud_analysis | evidence_expansion | workflow_failure
fraud_analysis              -> compliance_validation | evidence_expansion | workflow_failure
compliance_validation       -> risk_scoring | evidence_expansion | workflow_failure
risk_scoring                -> risk_router | evidence_expansion | workflow_failure
```

The router functions are deterministic and only read typed state fields such as `next_route`,
`risk_band`, `escalation_level`, and retry/error metadata.

## State Strategy

`app/core/graph/state.py` defines the canonical typed state. The state intentionally stores
evidence references, findings, workflow events, retry metadata, approval requests, and scores
rather than large raw documents or transaction histories. Raw evidence should live in object
storage, graph stores, warehouses, or case systems and be referenced by stable IDs and URIs.

The state schema is split into focused modules under `app/core/graph/state_schemas`:

- `enums.py`: workflow statuses, routes, risk bands, escalation levels, agent roles
- `evidence.py`: evidence references and investigation findings
- `history.py`: workflow events, approval requests, escalation decisions
- `execution.py`: node results, retry state, node errors, confidence, agent execution records
- `risk.py`: aggregate risk assessment contract
- `investigation.py`: transaction, subject, compliance, and persistent memory structures

Append-only lists use LangGraph reducers:

- `evidence`
- `findings`
- `workflow_history`
- `node_errors`
- `approvals`
- `escalations`
- `node_results`
- `agent_executions`

This lets nodes add new investigation material without overwriting prior state.

## Retry and Fallback

Node resilience is centralized in `app/core/graph/retry.py`.

Core components:

- `RetryPolicy`: node-level max attempts, retry route, failure route, recoverable classes, fallback name
- `ErrorClassifier`: maps exceptions into enterprise failure classes
- `RetryManager`: executes handlers, applies retry/fallback/failure routing, and writes structured state
- `with_node_resilience(...)`: reusable async utility for LangGraph nodes
- `RecoverableNodeError`: explicit recoverable node failure
- `NonRecoverableNodeError`: explicit hard-stop node failure

Failure classes:

- `transient`
- `rate_limit`
- `timeout`
- `validation`
- `semantic`
- `dependency`
- `permission`
- `non_recoverable`
- `unknown`

The retry system records:

- retry count per node
- typed node errors
- fallback provider names
- workflow history events
- recovery routing to evidence expansion
- retry exhaustion state
- recoverable vs non-recoverable classification
- node result envelopes for future observability integrations

Production integrations should add provider-specific retry policies, idempotency keys, circuit
breakers, and action ledgers for external side effects.

Example node integration:

```python
return await with_node_resilience(
    "fraud_analysis",
    state,
    handler,
    fallback,
    policy=RetryPolicy(
        max_attempts=2,
        retry_route="evidence_expansion",
        fallback_name="deterministic_fallback",
    ),
)
```

Retry route behavior:

```text
recoverable failure before max attempts -> evidence_expansion
retry exhaustion with fallback          -> fallback result path
retry exhaustion without fallback       -> workflow_failure
non-recoverable failure                 -> fallback or workflow_failure
```

## Persistence

`build_investigation_workflow(checkpointer=...)` accepts a LangGraph checkpointer. Production
should use a durable checkpointer such as Postgres and invoke with a stable `thread_id`.

Recommended persistence layers:

- LangGraph checkpointer for resume, history, and interrupts
- case database for current business state and assignment
- evidence store for raw documents and transaction context
- append-only audit log for regulatory review
- observability stack for traces, cost, latency, and provider failures

LangGraph checkpoints are workflow recovery infrastructure. They should complement, not replace,
the regulated audit log.

## Scalability Rules

- Keep routing deterministic and based on typed state fields.
- Keep nodes narrow and async-ready.
- Keep side effects idempotent.
- Store large payloads outside graph state.
- Version workflow, schema, prompts, models, and policies.
- Use subgraphs when fraud, compliance, risk, or reporting logic grows beyond a small module.
- Put every sensitive action behind an approval checkpoint or an idempotent action ledger.
