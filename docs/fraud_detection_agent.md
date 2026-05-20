# Fraud Detection Agent

The Fraud Detection Agent provides explainable fraud scoring for enterprise financial
investigations. It combines deterministic heuristics with an AI-assisted narrative extension point
while preserving structured evidence, confidence scoring, and LangGraph-compatible outputs.

## 1. Fraud Detection Architecture

```text
LangGraph fraud_detection_node
  -> FraudDetectionService
      -> transaction analysis dependency
      -> rule-based heuristic framework
      -> evidence generation
      -> fraud score aggregation
      -> escalation recommendation
      -> AI-assisted narrative provider
  -> InvestigationState partial update
```

Implementation files:

```text
app/core/graph/state_schemas/fraud_detection.py
app/services/fraud_detection.py
app/core/graph/fraud_detection_node.py
examples/run_fraud_detection_agent.py
```

The default implementation is deterministic. The AI-assisted layer is isolated behind
`FraudNarrativeProvider`, so production teams can plug in a governed model call without changing the
score, evidence, or routing contracts.

## 2. Scoring Pipeline

Pipeline stages:

1. Load or compute `TransactionAnalysisResult`.
2. Execute fraud heuristics.
3. Generate structured evidence for triggered signals.
4. Aggregate weighted heuristic deltas with transaction anomaly score.
5. Assign risk band.
6. Compute confidence.
7. Produce escalation recommendation.
8. Generate explainable summary and recommended actions.

Fraud score inputs:

- transaction anomaly score
- high-value amount anomaly
- velocity anomaly
- geographic inconsistency
- device mismatch
- risky merchant category
- behavioral deviation
- structuring signal
- rapid chain movement

## 3. Evidence Generation

Each triggered heuristic emits `FraudEvidence`:

```text
evidence_id
signal_type
description
source
transaction_ids
weight
confidence
```

Evidence is deterministic, source-labeled, and suitable for:

- audit records
- analyst review
- workflow visualization
- final report generation
- SAR review packets

The LangGraph node also maps fraud evidence into workflow `EvidenceRef` and `InvestigationFinding`
records.

## 4. Risk Heuristic Framework

The heuristic framework emits `FraudHeuristicResult`:

```text
heuristic_id
signal_type
triggered
score_delta
rationale
evidence_ids
confidence
```

Supported fraud signals:

- `amount_anomaly`
- `velocity_anomaly`
- `geo_inconsistency`
- `device_mismatch`
- `merchant_risk`
- `behavioral_deviation`
- `structuring_signal`
- `rapid_chain_movement`

Thresholds are configured through `FraudDetectionPolicy`, making the rules policy-versionable and
testable.

## 5. Typed Outputs

The typed response schema is `FraudDetectionResult`.

It includes:

```text
transaction_id
fraud_score
risk_band
confidence
signals
evidence
heuristics
geographic_inconsistencies
suspicious_behaviors
escalation_recommendation
explanation
ai_assisted_summary
recommended_actions
```

Outputs are explainable by construction: every triggered signal has evidence and every score
contribution has a rationale.

## 6. LangGraph Integration

`fraud_detection_node(...)` is a LangGraph-compatible async node wrapper.

It writes:

- `fraud_detection`
- `fraud_score`
- `risk_band`
- `confidence`
- `fraud_typologies`
- `recommended_actions`
- `evidence`
- `findings`
- `agent_executions`
- `workflow_history`

It also uses `with_node_resilience(...)` for retry and fallback behavior.

Run the example:

```bash
python examples/run_fraud_detection_agent.py
```

## Enterprise Notes

- Keep fraud rules deterministic for baseline review.
- Use model-generated narrative only as an explanation layer, not the scoring source of truth.
- Persist `FraudDetectionResult` as JSONB for audit and replay.
- Version fraud policies and model prompts.
- Route high and critical fraud scores to human approval or temporary hold flows.
- Feed fraud evidence into visualization timelines and final investigation reports.
