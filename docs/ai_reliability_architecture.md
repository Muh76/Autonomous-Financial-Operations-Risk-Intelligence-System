# AI Reliability Architecture

This architecture defines the reliability layer for long-running multi-agent financial
investigation workflows. It validates agent outputs from transaction analysis, fraud detection,
compliance validation, retrieval, and risk scoring before the platform produces executive reports,
regulatory escalation summaries, or automated operational decisions.

The reliability layer is deterministic-first, evidence-grounded, and audit-oriented. Model-based
critique can be added as a supplemental signal, but final workflow gates should depend on typed
claims, citations, state transitions, and persisted validation records.

## 1. Reliability Architecture

```text
Investigation workflow
  -> transaction analysis agent
  -> fraud detection agent
  -> compliance validation agent
  -> financial retrieval agent
  -> risk scoring agent
  -> reliability control plane
      -> claim extraction
      -> evidence validation
      -> hallucination detection
      -> contradiction analysis
      -> confidence calibration
      -> reasoning consistency checks
      -> reliability scoring
      -> workflow gate decision
  -> report generation / evidence expansion / human approval / escalation
```

Core components:

- **Reliability control plane**: orchestrates validation stages and emits a single reliability
  decision for the workflow.
- **Critic validator**: evaluates unsupported claims, hallucinations, contradictions, confidence
  mismatches, and reasoning consistency.
- **Evidence registry**: indexes citations, retrieved documents, transaction references,
  compliance policies, fraud signals, and audit-ready evidence IDs.
- **Claim ledger**: stores normalized claims extracted from each agent output with owner,
  severity, confidence, citations, and downstream usage.
- **Calibration service**: compares claimed confidence against evidence quality, historical
  false-positive rates, and rule coverage.
- **Reliability repository**: persists validation results in PostgreSQL and caches active
  workflow reliability snapshots in Redis.
- **Workflow gate router**: decides whether to continue, expand evidence, request revision,
  pause for human approval, or block final action.

Reliability decisions should be treated as first-class workflow state, not log-only metadata.

## 2. Critic Validation Pipeline

The critic pipeline runs after major agent stages and again before final reporting.

Pipeline stages:

1. **Normalize outputs**: convert agent-specific responses into typed claims, evidence refs,
   confidence values, reasoning traces, and recommended actions.
2. **Classify claims**: label claims as factual, analytical, inferred, policy-based, risk-based,
   or recommendation-based.
3. **Validate evidence**: verify that high-impact claims are backed by citations, transaction
   records, policy references, or structured agent outputs.
4. **Detect hallucinations**: flag factual or policy claims that cannot be tied to source data.
5. **Check contradictions**: compare claims across agents and against immutable investigation
   facts.
6. **Calibrate confidence**: adjust confidence based on evidence strength, agreement between
   agents, retrieval quality, and policy coverage.
7. **Validate reasoning consistency**: ensure the recommendation follows from the observed
   evidence, risk score, compliance flags, and workflow rules.
8. **Score reliability**: combine grounding, contradiction, calibration, and consistency scores.
9. **Route workflow**: emit a gate decision and required remediation actions.

Recommended gate decisions:

- `continue`: output is sufficiently grounded and internally consistent.
- `expand_evidence`: retrieval or transaction context is incomplete.
- `revise_agent_output`: an agent must regenerate or correct an unsupported section.
- `human_review`: high-impact uncertainty or conflict requires manual approval.
- `block_final_action`: final escalation or report publication is unsafe.

## 3. Evidence Validation Strategy

Evidence validation should use a source hierarchy rather than treating all evidence equally.

Evidence tiers:

- **Tier 1 authoritative records**: transaction ledger rows, customer KYC records, case history,
  approved compliance policy, sanctions screening results, and audit artifacts.
- **Tier 2 retrieved source documents**: SEC filings, audit reports, AML guidance, governance
  reports, and compliance policies with citations and version metadata.
- **Tier 3 derived agent outputs**: fraud signals, anomaly scores, transaction chains, behavioral
  summaries, risk scores, and critic findings.
- **Tier 4 narrative summaries**: executive summaries and free-form explanations.

Validation rules:

- High-risk escalation recommendations require Tier 1 or Tier 2 support.
- Compliance findings require policy citations or explicit rule IDs.
- Fraud findings require transaction IDs, behavioral signals, or anomaly evidence.
- Risk scoring inputs must map back to fraud, compliance, retrieval, or critic evidence.
- Executive report statements must cite evidence or reference previously validated findings.

Evidence records should include:

```text
evidence_id
source_type
source_uri
source_version
retrieved_at
claim_ids
agent_origin
confidence
freshness
access_control_label
audit_hash
```

Redis can hold the active evidence index for an in-flight workflow. PostgreSQL should persist the
canonical evidence registry, claim-to-evidence mappings, and validation results for replay.

## 4. Hallucination Detection Approach

Hallucination detection should focus on unsupported high-impact assertions rather than generic
language quality.

Detection categories:

- **Missing citation**: factual claim has no evidence reference.
- **Source mismatch**: citation exists but does not support the claim.
- **Unsupported policy claim**: compliance statement references no policy, rule, or guidance.
- **Unsupported entity claim**: customer, counterparty, geography, account, or transaction detail
  is absent from source records.
- **Unsupported causal claim**: agent asserts why behavior occurred without evidence.
- **Unsupported action claim**: escalation recommendation exceeds validated risk evidence.

Production approach:

1. Extract atomic claims from each output.
2. Require evidence for factual, policy, and final-action claims.
3. Use deterministic source checks for IDs, amounts, dates, jurisdictions, and thresholds.
4. Use retrieval entailment or cross-encoder verification for citation-to-claim support.
5. Require stricter support for high-risk, regulatory, or customer-impacting claims.
6. Store hallucination findings with claim ID, missing evidence type, severity, and remediation.

Model-assisted critique can identify suspicious narrative claims, but deterministic evidence
contracts should decide whether the workflow may proceed.

## 5. Contradiction Analysis Framework

Contradictions should be analyzed across agent outputs, source records, and workflow decisions.

Contradiction classes:

- **Risk contradiction**: fraud agent says high risk while risk scoring says low risk.
- **Compliance contradiction**: compliance agent finds policy breach while final recommendation
  says no action.
- **Evidence contradiction**: cited document conflicts with transaction data or KYC records.
- **Temporal contradiction**: sequence of events is impossible or out of order.
- **Entity contradiction**: customer, counterparty, account, or jurisdiction differs across
  outputs.
- **Decision contradiction**: workflow route conflicts with approval, critic, or escalation state.

Framework:

```text
Claim graph
  -> nodes: claims, evidence, entities, transactions, policies, decisions
  -> edges: supports, contradicts, derived_from, cites, recommends, overrides
  -> checks: entity equality, temporal ordering, policy threshold, risk band agreement
```

Severity logic:

- `critical`: contradiction can cause invalid regulatory escalation, false clearance, or unsafe
  final action.
- `high`: contradiction affects risk band, compliance result, or executive report finding.
- `medium`: contradiction affects supporting rationale or non-final recommendations.
- `low`: contradiction is localized, explainable, or informational.

Critical and high contradictions should pause the workflow for revision or human review.

## 6. Confidence Calibration Strategy

Reported confidence should be calibrated against evidence quality and historical reliability, not
just generated by the agent.

Calibration inputs:

- evidence coverage ratio
- citation support score
- retrieval relevance and reranking score
- number and severity of contradictions
- agreement between agents
- rule coverage for fraud and compliance checks
- source freshness and authority tier
- historical precision for similar cases
- critic finding severity

Calibration formula:

```text
calibrated_confidence =
  base_agent_confidence
  * evidence_coverage_factor
  * citation_support_factor
  * source_authority_factor
  * agent_agreement_factor
  - contradiction_penalty
  - missing_evidence_penalty
  - policy_gap_penalty
```

Confidence mismatch findings:

- **Overconfident unsupported claim**: high confidence with weak evidence coverage.
- **Underconfident deterministic finding**: low confidence despite rule-backed evidence.
- **Inconsistent confidence**: agent confidence conflicts with risk severity or critic findings.
- **Uncalibrated final action**: final recommendation confidence differs from aggregate evidence.

Confidence should be stored as both raw agent confidence and calibrated workflow confidence.

## 7. Reliability Scoring System

Reliability scoring should produce a clear operational score and an explainable breakdown.

Suggested scoring dimensions:

```text
grounding_score: 0.00-1.00
citation_support_score: 0.00-1.00
contradiction_score: 0.00-1.00
confidence_calibration_score: 0.00-1.00
reasoning_consistency_score: 0.00-1.00
policy_coverage_score: 0.00-1.00
workflow_integrity_score: 0.00-1.00
```

Weighted aggregate:

```text
reliability_score =
  0.25 * grounding_score
  + 0.20 * citation_support_score
  + 0.20 * contradiction_score
  + 0.15 * confidence_calibration_score
  + 0.10 * reasoning_consistency_score
  + 0.05 * policy_coverage_score
  + 0.05 * workflow_integrity_score
```

Bands:

- `trusted`: score >= 0.90 and no high-severity findings.
- `reviewable`: score >= 0.75 and no critical findings.
- `needs_evidence`: score >= 0.60 with missing evidence or citation gaps.
- `unsafe`: score < 0.60 or any critical contradiction, hallucination, or policy breach.

Every score should include:

- score components
- blocking findings
- affected claims
- evidence references
- remediation actions
- workflow route recommendation

## 8. Workflow Integration Strategy

Reliability validation should run as both inline checks and final gates.

Recommended LangGraph placement:

```text
transaction_analysis
  -> fraud_detection
  -> compliance_validation
  -> financial_retrieval
  -> risk_scoring
  -> critic_validation
  -> reliability_gate
      -> continue: executive_reporting
      -> expand_evidence: financial_retrieval
      -> revise: target_agent_retry
      -> human_review: approval_checkpoint
      -> block: investigation_hold
```

Integration patterns:

- Run lightweight validation after each agent to catch missing IDs, malformed outputs, and absent
  evidence early.
- Run full critic validation after risk scoring, before final report generation.
- Re-run reliability validation after human edits, retries, retrieval expansion, or escalation
  changes.
- Persist validation snapshots at every reliability gate.
- Include reliability findings in executive reports and audit exports.
- Use Redis for active reliability state, retry counters, and gate locks.
- Use PostgreSQL for claim ledgers, evidence mappings, critic results, calibration history, and
  audit replay.

Concurrency safeguards:

- Treat reliability gate updates as compare-and-swap state transitions.
- Use workflow run ID and validation version to prevent stale critic results from approving newer
  agent outputs.
- Require idempotency keys for critic retries and evidence expansion.
- Store immutable validation snapshots for audit and replay.

Operational controls:

- Alert on rising hallucination rates by agent, workflow type, or document source.
- Track unsupported claim rates and contradiction rates over time.
- Use calibration drift reports to tune confidence thresholds.
- Require manual approval for critical findings, regulatory escalation, or low-reliability reports.
- Block final report publication when evidence support does not meet enterprise thresholds.

