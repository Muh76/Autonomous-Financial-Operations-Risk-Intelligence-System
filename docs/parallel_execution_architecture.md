# Parallel Execution Architecture

This architecture uses LangGraph fan-out/fan-in orchestration for independent agent branches. A
coordination node dispatches work, independent async nodes run in the same graph superstep, and an
aggregation node joins their results into a deterministic state update.

Example:

```text
normalize_intake
  -> parallel_analysis_fanout
      -> parallel_fraud_analysis
      -> parallel_compliance_validation
  -> aggregate_parallel_results
  -> report_generation
```

The implementation lives in `app/core/graph/parallel_workflow.py`.

## 1. Parallel Execution Architecture

The graph uses these responsibilities:

- Coordination node: records dispatch intent and sets workflow status.
- Parallel branch nodes: execute independent work and write disjoint state fields.
- Aggregation node: waits for branch completion and computes canonical aggregate state.
- Terminal node: writes a report or routes to escalation, critic review, or human approval.

In LangGraph, fan-out is represented with multiple edges from one node:

```python
workflow.add_edge("parallel_analysis_fanout", "parallel_fraud_analysis")
workflow.add_edge("parallel_analysis_fanout", "parallel_compliance_validation")
```

Fan-in is represented by joining multiple upstream nodes into one downstream node:

```python
workflow.add_edge(
    ["parallel_fraud_analysis", "parallel_compliance_validation"],
    "aggregate_parallel_results",
)
```

The aggregation node runs only after both upstream branches finish.

## 2. Concurrency Strategy

Concurrency-safe state updates follow one rule: parallel nodes must not write conflicting scalar
fields.

Safe branch ownership:

```text
parallel_fraud_analysis:
  fraud_score
  fraud_typologies

parallel_compliance_validation:
  compliance_score
  compliance_flags
  compliance_review

both branches:
  findings
  node_results
  agent_executions
  workflow_history
  node_errors
```

Shared list fields are safe because `InvestigationState` defines reducer-backed lists using
`Annotated[..., add]`. Scalar fields such as `status`, `next_route`, `risk_band`, and
`aggregate_risk_score` are reserved for coordination and aggregation nodes.

For enterprise deployment:

- Use per-branch ownership for scalar state fields.
- Use reducers for append-only lists and event logs.
- Keep external side effects idempotent.
- Store durable branch outputs before irreversible actions.
- Use Redis locks only around external resources, not normal graph state merges.

## 3. Async Node Patterns

Each parallel node should be fully async:

```python
async def parallel_fraud_analysis_node(state: InvestigationState) -> PartialState:
    async def handler(current: InvestigationState) -> PartialState:
        result = await fraud_agent.analyze(current)
        return {"fraud_score": result.score}

    return await _run_with_timeout(
        node="parallel_fraud_analysis",
        state=state,
        timeout_seconds=8.0,
        handler=handler,
        fallback=fallback,
    )
```

Recommended production pattern:

- Validate inputs at node start.
- Call model/provider/database clients with native async APIs.
- Bound every branch with `asyncio.wait_for`.
- Return only partial state owned by that branch.
- Put provider latency and model metadata in `agent_executions`.
- Put branch failures in `node_errors`.

## 4. Result Aggregation Strategy

Aggregation should be deterministic and centralized.

The example aggregation node:

- Reads `fraud_score`.
- Reads `compliance_score`.
- Reads `compliance_flags`.
- Computes `aggregate_risk_score`.
- Assigns `risk_band`.
- Assigns `escalation_level`.
- Writes `risk_assessment`.
- Sets final workflow status and recommended actions.

This prevents parallel branches from racing over final business decisions.

Aggregation can also enforce quality gates:

```text
if any required branch is missing:
  route to retry or failure
if branch fallback was used:
  lower confidence or require critic review
if sanctions_hit:
  override aggregate score with block escalation
```

## 5. Timeout Handling

The example uses `_run_with_timeout(...)`, which wraps each branch with `asyncio.wait_for`.

On timeout:

- A structured `NodeError` is appended.
- A fallback branch result is returned.
- A fallback `NodeResult` is appended.
- Workflow history records the timeout fallback.
- The graph continues to aggregation with degraded confidence.

Recommended timeout policy:

```text
short provider call: 5-10 seconds
retrieval-heavy branch: 15-30 seconds
batch enrichment branch: 60-120 seconds
human approval branch: interrupt/checkpoint, not timeout
```

Do not let one slow branch block the whole investigation indefinitely. For regulated workflows,
fallbacks should be explicit and visible in the final report.

## 6. Example Workflow Implementation

Use:

```python
from app.core.graph.parallel_workflow import run_parallel_investigation_workflow

result = await run_parallel_investigation_workflow(
    "txn_123",
    tenant_id="bank_a",
    transaction_amount=12500,
    transaction_currency="USD",
    jurisdiction="US",
)
```

Or build the graph directly:

```python
from app.core.graph.parallel_workflow import build_parallel_investigation_workflow

workflow = build_parallel_investigation_workflow(checkpointer=postgres_checkpointer)
config = {"configurable": {"thread_id": "parallel_thread_bank_a_txn_123"}}
result = await workflow.ainvoke(initial_state, config=config)
```

Production deployments should combine this with:

- durable LangGraph checkpointer
- PostgreSQL workflow snapshots
- Redis short-term memory
- per-branch observability spans
- retry policies for retryable branch failures
- critic review after fallback or low-confidence aggregation
