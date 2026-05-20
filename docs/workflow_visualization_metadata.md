# Workflow Visualization Metadata

This system turns LangGraph workflow execution state into dashboard-ready metadata for operational
monitoring, investigation replay, escalation analysis, and observability interfaces.

It is intentionally split into two layers:

```text
Static graph metadata  -> nodes, edges, labels, route conditions, human checkpoints
Runtime execution trace -> timings, traversed edges, retries, escalations, timeline events
```

The implementation lives in:

```text
app/core/graph/state_schemas/visualization.py
app/services/workflow_visualization.py
```

## 1. Metadata Schema

Static graph metadata describes what can happen:

- `GraphNodeMetadata`
- `GraphEdgeMetadata`

Node metadata supports:

- node ID
- display label
- node type
- agent role
- timeout
- retryability
- human review requirement
- dashboard grouping

Edge metadata supports:

- edge ID
- source node
- target node
- normal or conditional edge type
- route condition
- display label

Runtime metadata describes what did happen:

- `NodeExecutionTrace`
- `EdgeTraversalTrace`
- `RetryVisualizationTrace`
- `EscalationPathTrace`
- `WorkflowTimelineEvent`
- `WorkflowVisualizationMetadata`

These models are plain typed dictionaries so they can be serialized to JSON, stored in PostgreSQL
JSONB, streamed to observability systems, or returned directly from API endpoints.

## 2. Execution Trace Models

`NodeExecutionTrace` records node timing and outcome:

```text
trace_id
node_id
status
started_at
completed_at
duration_ms
attempt
confidence
output_fields
error_type
error_message
```

`EdgeTraversalTrace` records route movement:

```text
source
target
traversed_at
route
reason
confidence
```

`RetryVisualizationTrace` records retry posture:

```text
node_id
attempt
max_attempts
retryable
failure_class
fallback_used
next_retry_route
```

`EscalationPathTrace` records high-risk routing:

```text
escalation_id
source_node
escalation_level
required_role
reason
approval_id
created_at
resolved_at
```

## 3. Workflow Visualization Structures

`WorkflowVisualizationMetadata` is the complete read model:

```text
workflow_id
case_id
tenant_id
status
nodes
edges
node_traces
edge_traversals
retries
escalations
timeline
```

Dashboards can render:

- graph topology from `nodes` and `edges`
- active or completed nodes from `node_traces`
- highlighted route paths from `edge_traversals`
- retry badges from `retries`
- escalation ribbons from `escalations`
- chronological replay from `timeline`

## 4. Node Execution Logging

The workflow state now supports append-only visualization fields:

```text
node_traces
edge_traversals
timeline_events
```

Existing execution records are also reused:

```text
workflow_history
node_results
agent_executions
retry_state
escalations
approvals
```

Production node wrappers should log:

1. node start time
2. node completion time
3. duration
4. attempt number
5. output field names
6. confidence
7. error metadata
8. selected next route

For high-throughput systems, write trace events asynchronously to an append-only store while keeping
the current state compact.

## 5. Timeline Generation Approach

`WorkflowVisualizationService.build_metadata(state)` creates a complete visualization payload.

It derives:

- node traces from `node_traces`, `agent_executions`, and `node_results`
- edge traversal from `edge_traversals` and ordered `workflow_history`
- retry visualization from `retry_state`
- escalation paths from `escalations`
- timeline events from workflow history, node traces, edge traversal, retries, and escalations

The timeline is sorted by event timestamp and can power:

- investigation replay
- dashboard activity feeds
- escalation review screens
- SLA and latency reporting
- node failure diagnostics

Recommended event categories:

```text
workflow_started
node_started
node_completed
node_failed
edge_traversed
retry_scheduled
fallback_used
escalation_requested
approval_requested
approval_decided
workflow_paused
workflow_resumed
workflow_completed
```

## Enterprise Notes

- Store raw trace events append-only.
- Keep visualization read models rebuildable from workflow history.
- Use tenant ID and case ID in every query.
- Add indexes on workflow ID, node ID, event timestamp, and escalation level.
- Preserve state hashes for replay integrity.
- Do not rely on Redis as the only trace store.
- Use OpenTelemetry spans for provider calls and merge span IDs into node traces later.
