# Workflow Memory Architecture

This platform uses a two-tier memory system for long-running financial investigations:

```text
Redis      -> short-term workflow memory, active agent coordination, retry counters
PostgreSQL -> durable investigation memory, evidence history, escalations, critic feedback
```

Agents should not directly read or write either store. They use `WorkflowMemoryService`, which
builds scoped context and records memory through repository interfaces.

## Memory Types

Short-term memory lives in Redis:

- `active_workflow_memory`: current workflow state projection and pending decisions.
- `agent_scratchpad`: temporary agent notes that can expire safely.
- `agent_handoffs`: compact context passed between agents.
- `retry_count`: per-workflow-step retry counters.
- `latest_critic_feedback`: immediate feedback used by the next correction loop.

Persistent memory lives in PostgreSQL:

- `investigation_memory_summaries`: investigation, workflow, escalation, evidence, retry, and critic summaries.
- `related_transaction_memory`: related transactions, counterparties, typologies, and risk signals.
- `evidence_memory_items`: evidence registry with source, storage, and hash metadata.
- `evidence_memory_events`: append-only evidence lifecycle history.
- `escalation_memory`: prior escalations and human decision context.
- `retry_memory_events`: retry audit history for nodes and agents.
- `critic_feedback_memory`: critic, QA, and compliance feedback history.

## Access Patterns

At workflow start, load durable summaries, related transactions, prior escalations, evidence
references, unresolved critic feedback, and recent retry history from PostgreSQL. Then hydrate Redis
with active workflow memory for fast agent coordination.

During an agent step, read from Redis first for active state and handoffs. Read from PostgreSQL only
for durable case memory needed by the current task. Write temporary scratchpads and latest critic
feedback to Redis. Write validated evidence, escalations, retries, critic feedback, and summaries to
PostgreSQL.

On retry, increment Redis first so the orchestrator can route immediately, then append
`retry_memory_events` in PostgreSQL for audit and reliability reporting.

On resume, rebuild Redis from PostgreSQL snapshots, summaries, unresolved feedback, and the latest
LangGraph checkpoint. Redis is a projection, not the system of record.

## Repository Layer

The durable repository is `app.repositories.memory.WorkflowMemoryRepository`.

It provides methods for:

- investigation and workflow summaries
- related transaction memory
- evidence items and evidence lifecycle events
- prior escalations
- retry history
- critic feedback and resolution

The Redis working-memory operations live in `app.cache.redis.RedisStore`:

- `set_active_workflow_memory`
- `get_active_workflow_memory`
- `set_agent_scratchpad`
- `get_agent_scratchpad`
- `append_agent_handoff`
- `get_agent_handoffs`
- `increment_retry_count`
- `set_latest_critic_feedback`
- `get_latest_critic_feedback`

The service layer is `app.services.workflow_memory.WorkflowMemoryService`. Its main entry point is
`build_agent_context(...)`, which returns a layered context:

```text
short_term.active_memory
short_term.scratchpad
short_term.handoffs
short_term.latest_critic_feedback
persistent.summaries
persistent.related_transactions
persistent.evidence
persistent.prior_escalations
persistent.retry_history
persistent.unresolved_critic_feedback
```

## Workflow Integration

Recommended integration points:

1. `normalize_intake`: create or load case-level memory namespace.
2. `collect_transaction_context`: persist related transaction memory and evidence registry entries.
3. `fraud_analysis`: read related transaction memory and prior typology summaries.
4. `compliance_validation`: read prior escalations and regulatory evidence history.
5. `risk_scoring`: write a compact risk summary.
6. `critic_validation`: write Redis latest feedback and durable critic feedback.
7. `evidence_expansion`: append evidence items and evidence lifecycle events.
8. `escalation_router`: write escalation memory before human approval.
9. `workflow_failure`: record retry/failure summaries before closure.
10. `report_generation`: write final investigation and workflow summaries.

For enterprise scale, keep raw evidence out of prompts and workflow state. Store references, hashes,
and short summaries in memory, then retrieve raw evidence from governed storage only when needed.

## Scaling Notes

- Keep every PostgreSQL query tenant-scoped.
- Use Redis TTLs for all short-term workflow keys.
- Add idempotency keys before writing external side effects.
- Use PostgreSQL partitioning for high-volume event tables if case volume grows.
- Add `pgvector` columns or a separate vector index for semantic search over summaries and evidence.
- Treat append-only events as the audit trail and summaries as retrieval accelerators.
