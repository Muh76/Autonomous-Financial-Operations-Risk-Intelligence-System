# Workflow Persistence Architecture

## Goals

The investigation workflow uses three persistence layers with different responsibilities:

```text
LangGraph checkpointer  -> durable graph resume and interrupt state
PostgreSQL              -> business records, snapshots, history, checkpoint metadata
Redis                   -> short-lived state cache, resume hints, live execution events
```

LangGraph checkpoints are the execution recovery layer. PostgreSQL is the system of record for
investigation runs, serialized workflow snapshots, audit-style history, and checkpoint references.
Redis is intentionally short-lived and should never be the only copy of regulated data.

## Checkpoint Strategy

Production graph compilation should inject a durable LangGraph checkpointer:

```python
workflow = build_investigation_workflow(checkpointer=postgres_checkpointer)
config = {"configurable": {"thread_id": state["thread_id"]}}
result = await workflow.ainvoke(state, config=config)
```

Recommended conventions:

- `thread_id`: stable investigation execution ID
- `case_id`: business case ID
- `checkpoint_namespace`: use for replay lanes, approval waits, or remediation branches
- checkpoint metadata: workflow version, schema version, tenant ID, case ID, node name

Use LangGraph checkpoints for resume, interrupts, and time travel. Use PostgreSQL snapshots for
business audit, operational search, reporting, and long-term investigation reconstruction.

## State Serialization

`app/repositories/investigations.py` provides:

- `serialize_state(state)`: JSON-safe state payload for JSONB
- `state_hash(payload)`: SHA-256 hash for snapshot integrity checks
- `InvestigationRepository.save_snapshot(...)`: stores execution snapshots

Large evidence payloads should not be stored in workflow state. Persist references and hashes in
state, and store raw evidence in object storage, warehouses, or graph databases.

## Redis Design

`RedisStore` supports short-term workflow operations:

- `cache_workflow_state(thread_id, state, ttl_seconds=900)`
- `get_cached_workflow_state(thread_id)`
- `cache_resume_pointer(thread_id, checkpoint_id, snapshot_id)`
- `get_resume_pointer(thread_id)`
- `append_execution_event(thread_id, event)`
- `get_execution_events(thread_id)`

Suggested TTLs:

- live workflow state cache: 5-15 minutes
- resume pointer: 30-60 minutes
- execution event stream: 1-6 hours

Redis keys follow:

```text
aforis:workflow:{thread_id}:state
aforis:workflow:{thread_id}:resume
aforis:workflow:{thread_id}:events
```

## PostgreSQL Schema

The SQLAlchemy models live in `app/models/investigations.py`.

### `investigation_runs`

Stores the current business-level state for each workflow run:

- `case_id`
- `tenant_id`
- `thread_id`
- `transaction_id`
- `workflow_version`
- `schema_version`
- `status`
- `risk_band`
- `escalation_level`
- `confidence`
- `latest_snapshot_id`
- timestamps

### `workflow_snapshots`

Stores serialized state snapshots:

- `run_id`
- `thread_id`
- `step_number`
- `node_name`
- `state` JSONB
- `state_hash`
- `created_at`

### `workflow_history_events`

Stores append-only workflow history events:

- `run_id`
- `event_id`
- `node_name`
- `status`
- `message`
- `event_payload` JSONB
- `created_at`

### `workflow_checkpoint_refs`

Stores metadata pointers to LangGraph checkpoint storage:

- `run_id`
- `thread_id`
- `checkpoint_namespace`
- `checkpoint_id`
- `checkpoint_metadata` JSONB
- `created_at`

## Repository Pattern

`InvestigationRepository` owns durable investigation persistence:

- `upsert_run(state)`
- `save_snapshot(state, node_name, step_number)`
- `append_history_events(state, events)`
- `save_checkpoint_ref(state, checkpoint_id, checkpoint_namespace, metadata)`
- `get_run_by_thread_id(thread_id)`
- `get_latest_snapshot(thread_id)`
- `load_latest_state(thread_id)`
- `list_history(thread_id)`

Routes and graph nodes should not write SQL directly. Services should coordinate repository writes
around graph invocation boundaries, node completion hooks, or background persistence tasks.

## Resumable Workflow Flow

```text
1. Receive transaction investigation request.
2. Build initial typed InvestigationState.
3. Invoke graph with stable thread_id and durable checkpointer.
4. After important nodes, save PostgreSQL snapshot and append history events.
5. Cache latest state and resume pointer in Redis.
6. On interruption or failure, reload using LangGraph checkpoint first.
7. If checkpoint is unavailable, inspect PostgreSQL latest snapshot for recovery triage.
```

## Enterprise Notes

- Keep tenant ID in every persistence query.
- Use row-level security or tenant-scoped repository methods in production.
- Add Alembic migrations before deploying these models.
- Treat PostgreSQL snapshots as audit-supporting records, not as a replacement for immutable audit logs.
- Add OpenTelemetry spans around repository calls and Redis operations.
- Add idempotency keys around external side effects before enabling replay of action nodes.
