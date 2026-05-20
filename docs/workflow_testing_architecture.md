# LangGraph Workflow Testing Architecture

Enterprise workflow systems need deterministic tests at several levels. The goal is to prove that
nodes, branches, retries, escalation paths, and full graph execution remain stable as agent
implementations become more capable and less deterministic.

The test scaffold lives in:

```text
tests/conftest.py
tests/unit/
tests/integration/
```

## 1. Testing Architecture

Use a layered test strategy:

```text
Unit tests
  -> pure route helpers
  -> isolated node functions
  -> retry manager
  -> approval checkpoint service
  -> visualization metadata builder

Branching tests
  -> low, medium, high, sanctions, fallback routes
  -> explicit next_route overrides

State transition tests
  -> status changes
  -> append-only reducers
  -> approval pending/approved/rejected states

Integration tests
  -> full LangGraph invocation
  -> parallel workflow invocation
  -> deterministic final state assertions
```

Test pyramid:

```text
many node isolation tests
some branch and retry tests
few full workflow tests
```

This keeps CI fast while still catching orchestration regressions.

## 2. Pytest Structure

Recommended layout:

```text
tests/
|-- conftest.py
|-- unit/
|   |-- test_node_isolation.py
|   |-- test_branching_and_state_transitions.py
|   |-- test_retry_policy.py
|   `-- test_approval_and_visualization.py
`-- integration/
    `-- test_workflow_integration.py
```

Suggested CI stages:

```bash
pytest tests/unit
pytest tests/integration
```

Unit tests should not require PostgreSQL, Redis, external APIs, or model providers. Integration
tests may use LangGraph runtime behavior but should still avoid external services unless explicitly
marked.

## 3. Workflow Fixtures

`tests/conftest.py` provides `investigation_state_factory`.

The factory returns a complete `InvestigationState` with reducer-backed lists initialized:

```python
state = investigation_state_factory(
    transaction_amount=75_000.0,
    jurisdiction="US",
)
```

Provided scenario fixtures:

- `low_risk_state`
- `high_risk_state`
- `sanctions_state`

Keep fixtures complete and explicit. Missing state keys can hide bugs in graph initialization.

## 4. Mock State Generators

State generators should create deterministic financial scenarios:

```text
low risk:
  small amount
  normal jurisdiction
  no compliance flags

high risk:
  high amount
  normal jurisdiction
  senior review escalation

sanctions:
  sanctioned jurisdiction
  block escalation
```

Use plain state dictionaries instead of mocking LangGraph internals. Nodes are async functions that
accept state and return partial state, which makes them naturally testable.

## 5. Node Test Examples

Node isolation tests validate a single node contract:

```python
result = await compliance_validation_node(sanctions_state)

assert result["compliance_score"] == 95.0
assert "sanctions_hit" in result["compliance_flags"]
```

Good node tests assert:

- status and route outputs
- domain outputs
- evidence and finding additions
- agent execution records
- retry/fallback metadata
- deterministic output for stable inputs

Avoid asserting generated UUID values or exact timestamps.

## 6. Workflow Integration Tests

Workflow integration tests invoke the graph end to end:

```python
result = await run_investigation_workflow(
    "low_risk_txn",
    tenant_id="test",
    transaction_amount=125.0,
    jurisdiction="US",
)

assert result["status"] == "closed"
assert result["risk_band"] == "low"
```

Current integration coverage includes:

- low-risk workflow closes deterministically
- high-risk workflow pauses for human approval
- parallel workflow aggregates fraud and compliance branch results

For production CI, add marks such as:

```python
@pytest.mark.integration
@pytest.mark.requires_langgraph
```

## Deterministic Validation Rules

Reliable workflow tests should avoid brittle assertions:

- assert business state, not UUIDs
- assert route names, not event ordering when parallelism is involved
- assert risk bands and escalation levels, not exact timestamps
- use deterministic input fixtures
- isolate provider/model calls behind fakes
- snapshot only stable read models

Recommended checks:

```text
python -m compileall app examples tests
pytest tests/unit
pytest tests/integration
```

## Enterprise Extensions

Next steps for a production test program:

- add contract tests for repository and Redis memory layers
- add fake model/provider fixtures for agent nodes
- add property tests for route invariants
- add approval resume tests using a durable LangGraph checkpointer
- add trace snapshot tests for workflow visualization metadata
- add performance tests for high-volume timeline generation
- run integration tests in Docker Compose with PostgreSQL and Redis
