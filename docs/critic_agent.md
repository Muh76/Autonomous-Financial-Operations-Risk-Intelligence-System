# Critic Agent

The Critic Agent is the enterprise reliability validator for financial investigation workflows.
It validates outputs from fraud detection, compliance validation, financial retrieval, risk
scoring, and executive reporting before the platform continues to escalation, human approval, or
final report publication.

The agent is deterministic-first and evidence-grounded. Model-assisted critique can be attached as
an additional validator, but production workflow gates should be driven by structured claims,
citations, evidence references, contradictions, calibrated confidence, and persisted audit records.

## 1. Critic Architecture

```text
LangGraph critic_agent_node
  -> CriticService
      -> output normalization
      -> evidence verification
      -> citation validation
      -> retrieval grounding checks
      -> hallucination detection
      -> contradiction analysis
      -> confidence calibration
      -> reasoning consistency validation
      -> reliability score breakdown
      -> safety recommendation
  -> InvestigationState partial update
```

Validated producers:

- Fraud Detection Agent
- Compliance Agent
- Financial Retrieval Agent
- Risk Scoring Agent
- Executive Reporting Agent

Validation stores:

- active reliability snapshot in workflow state
- findings in investigation history
- evidence and citation mappings for audit replay
- score breakdown for observability and model risk review

## 2. Validation Pipeline

Pipeline stages:

1. Normalize agent outputs into checked claims, citations, evidence references, confidence values,
   and decisions.
2. Verify that each agent's claims are supported by structured evidence or retrieval evidence.
3. Validate citation integrity across retrieval, compliance, and reporting outputs.
4. Check that report findings are grounded in retrieved evidence and citation IDs.
5. Detect hallucinations and unsupported high-impact assertions.
6. Compare outputs across agents for contradictions.
7. Calibrate reported confidence against evidence grounding and citation support.
8. Validate that recommendations follow from the observed fraud, compliance, retrieval, and risk
   signals.
9. Compute an explainable reliability score and gate recommendation.

Gate recommendations:

- `continue`
- `expand_evidence`
- `revise_outputs`
- `human_review`
- `block_final_action`

## 3. Hallucination Detection Methods

The Critic Agent treats hallucination as an evidence-contract failure, not only a language quality
problem.

Detection methods:

- high-risk workflow without retrieval evidence
- fraud or compliance claim without evidence references
- executive report finding without citation or evidence IDs
- policy conclusion without compliance citation
- escalation recommendation that exceeds validated risk evidence
- generated citation ID that does not exist in retrieval or policy sources
- final report path after failed critic validation

Findings are emitted as structured `CriticFinding` records with severity, target agent, claim,
explanation, evidence refs, recommendation, and critic confidence.

## 4. Evidence Verification Framework

The critic emits `EvidenceVerificationResult` per target agent:

```text
target_agent
checked_claims
supported_claims
unsupported_claims
citation_count
grounding_score
```

Evidence sources:

- workflow evidence refs
- transaction evidence
- retrieved document evidence
- retrieval citations
- compliance citations
- fraud signals and heuristics
- risk scoring signals
- report finding evidence IDs

High-impact claims require authoritative evidence. Narrative report language should inherit support
from validated findings rather than inventing new unsupported assertions.

## 5. Contradiction Analysis System

The critic detects contradictions across agent outputs and workflow state.

Examples:

- fraud risk is high or critical while operational risk is low
- sanctions hit exists without block or regulatory escalation
- failed critic state is followed by a ready or final report
- compliance breach exists while report suggests no action
- citation-backed report finding conflicts with risk score or fraud signal

Each contradiction records:

```text
contradiction_id
left_agent
right_agent
description
severity
evidence_refs
```

Critical contradictions block final action. High contradictions require human review or agent
revision.

## 6. Confidence Scoring Validation

The critic compares reported agent confidence with evidence-grounded confidence.

Inputs:

- grounding score
- citation support score
- retrieval evidence count
- contradiction count
- reasoning consistency score
- severity of critic findings

Calibration output:

```text
target_agent
reported_confidence
evidence_confidence
calibrated_confidence
calibration_delta
status
```

Overconfident unsupported outputs trigger reliability findings and may route the workflow to
evidence expansion or human review.

## 7. Citation Verification Pipeline

Citation validation checks whether generated citations are present, valid, and traceable to approved
retrieval or policy sources.

Pipeline:

1. Collect retrieval citations from the Financial Retrieval Agent.
2. Collect policy citations from the Compliance Agent.
3. Collect report citations and finding-level citation IDs from the Executive Reporting Agent.
4. Verify that report citations map back to retrieval or compliance citation IDs.
5. Flag missing finding citations and invalid generated citation IDs.
6. Emit `CitationValidationResult` for each checked agent.

Output:

```text
target_agent
checked_citations
valid_citations
invalid_citations
missing_citations
citation_support_score
```

Citation repair should happen before executive reports are approved or exported.

## 8. Typed Schemas

Primary typed outputs:

- `CriticValidationResult`
- `CriticFinding`
- `EvidenceVerificationResult`
- `CitationValidationResult`
- `RetrievalGroundingResult`
- `ContradictionResult`
- `ConfidenceCalibrationResult`
- `ReasoningConsistencyResult`
- `ReliabilityScoreBreakdown`

`CriticValidationResult` includes:

```text
passed
reliability_score
confidence
findings
evidence_verification
citation_validation
retrieval_grounding
contradictions
confidence_calibration
reasoning_consistency
score_breakdown
safety_recommendation
required_actions
policy_version
model_version
metadata
```

## 9. LangGraph Integration

`critic_agent_node(...)` writes:

- `critic_validation`
- `critic_passed`
- `critic_notes`
- `confidence_assessment`
- `findings`
- `agent_executions`
- `workflow_history`
- `next_route`

Recommended placement:

```text
transaction_analysis
  -> fraud_detection
  -> compliance_validation
  -> financial_retrieval
  -> risk_scoring_agent
  -> critic_agent
      -> continue: report_generation
      -> expand_evidence: retrieval_expansion
      -> revise_outputs: agent_retry
      -> human_review: approval_checkpoint
      -> block_final_action: investigation_hold
```

Run the example:

```bash
python examples/run_critic_agent.py
```

Operational requirements:

- persist every critic validation snapshot
- attach validation IDs to final reports
- alert on unsupported claim and invalid citation trends
- require human approval for critical reliability findings
- prevent stale critic results from approving newer agent outputs
- keep deterministic validation as the minimum safety baseline

