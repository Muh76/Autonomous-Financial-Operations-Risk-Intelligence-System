# Risk Scoring Agent

The Risk Scoring Agent aggregates operational risk signals into an explainable severity score,
confidence score, and escalation recommendation. It is designed for enterprise investigation
workflows where decisions must be auditable, deterministic, and easy for analysts to review.

## 1. Scoring Architecture

```text
LangGraph risk_scoring_agent_node
  -> RiskScoringService
      -> fraud signal extractor
      -> compliance signal extractor
      -> anomaly signal extractor
      -> retrieval evidence signal extractor
      -> critic feedback signal extractor
      -> operational context signal extractor
      -> weighted score aggregation
      -> confidence calibration
      -> escalation prioritization
  -> InvestigationState partial update
```

Implementation files:

```text
app/core/graph/state_schemas/risk.py
app/services/risk_scoring.py
app/core/graph/risk_scoring_agent_node.py
examples/run_risk_scoring_agent.py
```

The agent preserves compatibility with the existing `RiskAssessment` schema while also emitting a
richer `OperationalRiskScore`.

## 2. Weighted Scoring Strategy

Default weights:

```text
fraud: 0.32
compliance: 0.24
anomaly: 0.16
retrieval evidence: 0.10
critic feedback: 0.10
operational context: 0.08
```

Each signal emits:

```text
signal_name
raw_score
weight
weighted_score
confidence
rationale
```

The aggregate score is the sum of weighted scores. A separate severity score applies override rules
for sanctions, temporary hold recommendations, and failed critic review.

## 3. Confidence Calculation

Confidence is calibrated from:

- signal-level confidence
- signal weights
- structured evidence count
- retrieval citation presence

This means high risk with missing evidence can still escalate, but its confidence will remain lower
and evidence gaps will be visible.

## 4. Escalation Recommendation Logic

Escalation recommendations include:

```text
level
priority
required_role
rationale
recommended_actions
```

Default escalation logic:

- `block`: sanctions hit, critical risk, or temporary hold-level severity
- `regulatory`: SAR threshold or regulatory compliance trigger
- `senior_review`: high operational risk
- `analyst_review`: medium operational risk
- `none`: low risk

Evidence gaps can add `resolve_evidence_gaps` before final action.

## 5. Typed Outputs

The main typed output is `OperationalRiskScore`.

It includes:

```text
aggregate_score
severity_score
risk_band
confidence
signals
escalation
critic_adjustments
evidence_gaps
recommended_actions
explanation
policy_version
scoring_model_version
```

The LangGraph node maps this into:

- `operational_risk`
- `risk_assessment`
- `aggregate_risk_score`
- `risk_band`
- `escalation_level`
- `confidence`
- `recommended_actions`
- `findings`
- `agent_executions`
- `workflow_history`

## 6. LangGraph Integration

`risk_scoring_agent_node(...)` is async-ready and uses `with_node_resilience(...)` for retry and
fallback behavior.

Run the example:

```bash
python examples/run_risk_scoring_agent.py
```

Recommended graph placement:

```text
transaction_analysis
  -> fraud_detection
  -> financial_retrieval
  -> compliance_validation
  -> risk_scoring_agent
  -> escalation_router or medium_risk_compliance_review
```

## Enterprise Notes

- Keep weights policy-versioned.
- Preserve signal-level rationale for audit and model risk management.
- Treat critic feedback as a scoring modifier, not just a workflow note.
- Require retrieval citations for high-impact actions when possible.
- Store `OperationalRiskScore` as JSONB for replay and dashboards.
