# Compliance Agent

The Compliance Agent provides rule-based, explainable compliance validation for enterprise
financial investigation workflows. It focuses on AML-inspired checks, KYC validation, policy
thresholds, suspicious activity review, policy citation grounding, confidence scoring, and
escalation recommendations.

## 1. Compliance Architecture

```text
LangGraph compliance_agent_node
  -> ComplianceAgentService
      -> ComplianceRuleEngine
          -> KYC rule
          -> sanctions jurisdiction rule
          -> policy threshold rule
          -> AML behavior rule
          -> policy citation grounding rule
      -> scoring
      -> confidence calibration
      -> escalation recommendation
  -> InvestigationState partial update
```

Implementation files:

```text
app/core/graph/state_schemas/compliance.py
app/services/compliance.py
app/core/graph/compliance_agent_node.py
examples/run_compliance_agent.py
```

## 2. Rule Engine Design

The rule engine emits `ComplianceRuleResult` records:

```text
rule_id
category
passed
severity
rationale
policy_refs
evidence_refs
confidence
```

Included rules:

- `kyc_status_valid`
- `sanctions_jurisdiction_screen`
- `reporting_threshold_check`
- `aml_suspicious_activity_review`
- `policy_citation_grounding`

Rules are deterministic and policy-versioned through `CompliancePolicy`.

## 3. Policy Validation Pipeline

Pipeline stages:

1. Load transaction, subject, fraud, retrieval, and evidence state.
2. Extract policy citations from financial retrieval output.
3. Run KYC, sanctions, threshold, AML, and citation-grounding rules.
4. Convert failed rules into compliance flags.
5. Compute compliance score.
6. Calibrate confidence using rule and citation support.
7. Recommend escalation path and actions.

## 4. Compliance Reasoning Outputs

The main typed output is `ComplianceValidationResult`.

It includes:

```text
passed
compliance_score
confidence
flags
rule_results
citations
recommendation
suspicious_activity_summary
policy_version
reasoning
metadata
```

The LangGraph node maps this into:

- `compliance_validation`
- `compliance_score`
- `compliance_flags`
- `compliance_review`
- `recommended_actions`
- `findings`
- `agent_executions`
- `workflow_history`

## 5. Escalation Recommendation System

Default recommendations:

- `block`: sanctions hit
- `regulatory`: SAR threshold or suspicious activity review
- `compliance_review`: KYC or policy review required
- `analyst_review`: lower-severity policy exception
- `none`: no material compliance exception

Recommended actions are attached to the workflow state for downstream risk scoring and escalation.

## 6. LangGraph Integration

`compliance_agent_node(...)` is async-ready and uses `with_node_resilience(...)` for retry/fallback.

Run the example:

```bash
python examples/run_compliance_agent.py
```

Recommended graph placement:

```text
fraud_detection
  -> financial_retrieval
  -> compliance_agent
  -> risk_scoring_agent
```

## Enterprise Notes

- Keep rule thresholds policy-versioned.
- Require policy citations for high-risk compliance outcomes.
- Persist rule results for audit and regulator-facing explanations.
- Treat model-generated compliance summaries as secondary to deterministic rules.
- Use retrieval-backed citations to ground SAR, AML, and escalation decisions.
