# Transaction Analysis Agent

The Transaction Analysis Agent is a deterministic, async-ready agent service for transaction-level
financial investigation. It is designed to run inside LangGraph workflows and emit structured,
auditable outputs that can feed fraud scoring, escalation decisions, dashboards, and replay systems.

## 1. Agent Architecture

```text
LangGraph node wrapper
  -> TransactionAnalysisService
      -> aggregation stage
      -> temporal stage
      -> behavioral pattern stage
      -> transaction chain stage
      -> anomaly scoring stage
      -> action recommendation stage
  -> typed workflow state update
```

The implementation is split across:

```text
app/core/graph/state_schemas/transaction_analysis.py
app/services/transaction_analysis.py
app/core/graph/transaction_analysis_node.py
examples/run_transaction_analysis_agent.py
```

The service is intentionally deterministic today. Enterprise deployments can replace individual
pipeline stages with model-assisted or vendor-backed implementations while preserving the same typed
output contract.

## 2. Service Layer

`TransactionAnalysisService` is async-ready and policy-driven.

Core responsibilities:

- normalize incoming transaction observations
- aggregate amount, volume, counterparty, and direction metrics
- analyze transaction velocity and timing
- detect behavioral patterns with deterministic heuristics
- build transaction chain hops
- calculate anomaly score
- calculate confidence score
- recommend operational next actions

Configuration lives in `TransactionAnalysisPolicy`, including:

- high-value threshold
- structuring threshold and margin
- velocity threshold
- burst-window threshold
- counterparty concentration ratio
- chain-depth threshold
- unusual-hour window

## 3. Analysis Pipeline

Pipeline stages:

1. Normalize observations.
2. Aggregate transaction metrics.
3. Analyze temporal velocity and bursts.
4. Build transaction chain hops.
5. Detect suspicious activity indicators.
6. Score anomaly severity.
7. Score confidence.
8. Generate summary and recommended actions.

Supported suspicious indicators:

- `high_velocity`
- `structuring`
- `round_amount`
- `rapid_movement`
- `counterparty_concentration`
- `cross_border`
- `chain_depth`
- `unusual_time`

## 4. Typed Outputs

The typed response schema is `TransactionAnalysisResult`.

It includes:

```text
transaction_id
aggregate
temporal
chain
indicators
anomaly_score
confidence
summary
recommended_actions
```

Each suspicious activity indicator includes:

```text
indicator
severity
description
evidence_transaction_ids
confidence
```

These outputs are suitable for JSONB persistence, audit records, workflow visualization, and API
responses.

## 5. LangGraph Node Wrapper

`transaction_analysis_node(...)` adapts service output to `InvestigationState`.

It writes:

- `transaction_analysis`
- `fraud_score`
- `confidence`
- `fraud_typologies`
- `recommended_actions`
- `evidence`
- `findings`
- `agent_executions`
- `workflow_history`
- retry and fallback metadata through `with_node_resilience`

The wrapper is compatible with existing LangGraph reducer fields and can be inserted before fraud
analysis or used as a richer replacement for transaction context enrichment.

## 6. Example Investigation Execution

Run:

```bash
python examples/run_transaction_analysis_agent.py
```

The example creates a synthetic transaction history with near-threshold values, rapid movement,
counterparty concentration, and cross-border activity. The agent emits anomaly score, confidence,
indicators, and recommended actions.

## Enterprise Notes

- Keep transaction observations normalized before analysis.
- Persist raw source transactions separately from workflow state.
- Store analysis output as JSONB for audit and replay.
- Keep thresholds policy-versioned.
- Use deterministic heuristics for baseline review.
- Add model-assisted narrative analysis behind the same typed schema later.
- Route high anomaly scores to critic review or human escalation.
