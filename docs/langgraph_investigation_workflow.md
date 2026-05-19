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
  -> critic_validation
       -> report_generation
       -> evidence_expansion -> fraud_analysis
       -> escalation_router -> human_approval_checkpoint
       -> workflow_failure
```

Low-risk cases can move directly to report generation. Medium, high, regulatory, or blocking
cases route through escalation logic. Approval checkpoints currently prepare typed approval
records and stop the graph in `awaiting_human_approval`; once an analyst UI exists, this is the
place to enable LangGraph `interrupt(...)` and resume with a structured reviewer decision.

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

Node resilience is centralized in `with_node_resilience(...)`.

The current pattern records:

- retry count per node
- typed node errors
- fallback provider names
- workflow history events
- recovery routing to evidence expansion

Production integrations should add provider-specific retry policies, idempotency keys, circuit
breakers, and action ledgers for external side effects.

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
