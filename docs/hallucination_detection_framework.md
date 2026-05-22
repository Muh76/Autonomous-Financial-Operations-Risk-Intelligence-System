# Hallucination Detection Framework

This framework defines production-style hallucination detection for financial AI systems. It is
designed for multi-agent investigation workflows where fraud, compliance, retrieval, risk scoring,
and reporting agents produce structured outputs that must be grounded before they influence
operational decisions.

The framework treats hallucination as a reliability failure: a claim, citation, evidence reference,
or recommendation is unsafe when it cannot be reconciled with approved source data, retrieved
documents, policy records, or deterministic workflow state.

## 1. Hallucination Detection Architecture

```text
Agent output
  -> claim extractor
  -> claim classifier
  -> evidence resolver
  -> citation validator
  -> retrieval consistency checker
  -> reasoning consistency checker
  -> confidence mismatch detector
  -> hallucination scorer
  -> remediation router
```

Core services:

- **Claim extractor**: converts narrative and structured outputs into atomic claims.
- **Evidence resolver**: maps claims to transaction records, retrieval evidence, citations, and
  policy rules.
- **Citation validator**: verifies that citation IDs exist and refer to approved retrieval or
  policy sources.
- **Retrieval consistency checker**: compares claim text against retrieved evidence, reranker
  scores, and citation grounding scores.
- **Reasoning consistency checker**: validates that conclusions follow from fraud signals,
  compliance flags, retrieval evidence, and risk scores.
- **Confidence analyzer**: compares reported confidence with evidence support and source quality.
- **Hallucination scoring service**: emits a severity, score, explanation, and remediation route.

The framework should run inside the Critic Agent for inline workflow validation and as a reusable
library for report review, batch audit replay, and model risk monitoring.

## 2. Validation Heuristics

Unsupported claim heuristics:

- factual claim has no evidence ID, transaction ID, citation ID, or policy rule ID
- compliance claim lacks an approved policy citation
- fraud claim lacks transaction, behavioral, or anomaly evidence
- risk recommendation has no upstream fraud, compliance, retrieval, or critic support
- report finding cites no validated source

Fabricated evidence heuristics:

- evidence ID is absent from the evidence registry
- evidence source URI is malformed or not on an approved source allowlist
- citation ID appears in a report but not in retrieval or compliance outputs
- evidence timestamp is newer than report generation without a matching workflow event
- evidence hash does not match the stored audit hash

Invalid citation heuristics:

- citation ID is missing, duplicated, or generated outside the retrieval/policy layer
- citation source version is not the active policy or document version
- quote is empty for a source that requires extractive citation support
- report finding references a citation that is not attached to the report

Retrieval mismatch heuristics:

- cited document type does not match the claim category
- retrieval score or rerank score is below the claim severity threshold
- evidence grounding score is weak for a high-impact claim
- retrieved passage discusses a different entity, account, jurisdiction, or date range

Reasoning inconsistency heuristics:

- conclusion severity exceeds validated evidence severity
- high risk is reported while risk score is low
- sanctions or AML flags are not reflected in escalation recommendation
- final report is ready while critic validation has failed

Overconfidence heuristics:

- reported confidence is high while evidence coverage is low
- confidence remains high despite contradictions or missing citations
- deterministic rule result is ignored by narrative confidence
- final report confidence exceeds aggregate calibrated workflow confidence

## 3. Evidence Comparison Pipeline

Evidence comparison should operate on normalized claim records:

```text
claim_id
target_agent
claim_text
claim_type
severity
reported_confidence
evidence_refs
citation_refs
policy_refs
transaction_refs
created_at
```

Pipeline stages:

1. **Normalize sources**: load transaction records, retrieval evidence, compliance citations,
   policy rules, fraud signals, risk scores, report findings, and prior critic results.
2. **Resolve references**: verify every evidence, citation, policy, and transaction reference
   exists in the current workflow snapshot or durable repository.
3. **Compare entities**: match customer, counterparty, account, merchant, jurisdiction, and date
   fields across claims and evidence.
4. **Compare thresholds**: validate amounts, velocity windows, sanctions flags, AML thresholds,
   and escalation rules against configured policy.
5. **Check semantic support**: compare claim text to retrieved evidence using retrieval scores,
   rerank scores, grounding scores, and optional entailment models.
6. **Emit validation result**: produce support status, mismatch reasons, source references, and
   remediation actions.

Support states:

- `supported`: evidence directly supports the claim
- `partially_supported`: evidence supports part of the claim or has weak grounding
- `unsupported`: no valid evidence was found
- `contradicted`: evidence conflicts with the claim
- `unverifiable`: source access, freshness, or permissions prevent validation

## 4. Confidence Mismatch Detection

Confidence mismatch detection compares reported confidence with an evidence-calibrated confidence.

Calibration inputs:

- evidence coverage ratio
- citation support score
- retrieval grounding score
- source authority tier
- contradiction count
- policy rule coverage
- source freshness
- historical precision for the agent and claim type

Example calibration:

```text
calibrated_confidence =
  0.35 * reported_confidence
  + 0.25 * evidence_coverage
  + 0.20 * citation_support
  + 0.10 * retrieval_grounding
  + 0.10 * source_authority
  - contradiction_penalty
  - missing_evidence_penalty
```

Mismatch categories:

- `aligned`: reported confidence is within acceptable delta
- `overconfident`: reported confidence exceeds calibrated confidence
- `underconfident`: deterministic support is strong but reported confidence is low
- `unsafe_confidence`: high-impact claim is overconfident and weakly grounded

Routing:

- low mismatch: continue and log calibration data
- medium mismatch: lower confidence and annotate report
- high mismatch: rerun retrieval or regenerate output
- critical mismatch: human review or block final action

## 5. Retrieval Grounding Validation

Retrieval grounding validation ensures that generated claims are tied to the documents they cite.

Validation stages:

1. Collect retrieved chunks, citations, evidence objects, and source attribution.
2. Verify each cited source exists and was returned in the workflow run or approved cache.
3. Match claim entities against cited passage entities.
4. Match claim policy or regulatory terms against cited document metadata.
5. Require stronger grounding for high-risk, regulatory, or customer-impacting statements.
6. Flag mismatches when citation support does not cover the generated claim.

Grounding thresholds:

```text
low impact claim: grounding_score >= 0.50
medium impact claim: grounding_score >= 0.65
high impact claim: grounding_score >= 0.80
critical claim: grounding_score >= 0.90 and citation required
```

Retrieval mismatches should create explainable findings that include the claim, citation ID,
document title, mismatch reason, and recommended remediation.

## 6. Scoring System

Hallucination score should be separate from overall reliability score so teams can track this
failure mode directly.

Score components:

```text
claim_support_score: 0.00-1.00
citation_validity_score: 0.00-1.00
retrieval_grounding_score: 0.00-1.00
evidence_integrity_score: 0.00-1.00
reasoning_consistency_score: 0.00-1.00
confidence_alignment_score: 0.00-1.00
```

Aggregate score:

```text
hallucination_risk =
  1.00 - (
    0.25 * claim_support_score
    + 0.20 * citation_validity_score
    + 0.20 * retrieval_grounding_score
    + 0.15 * evidence_integrity_score
    + 0.10 * reasoning_consistency_score
    + 0.10 * confidence_alignment_score
  )
```

Risk bands:

- `low`: risk < 0.15
- `moderate`: risk >= 0.15 and < 0.35
- `high`: risk >= 0.35 and < 0.60
- `critical`: risk >= 0.60 or fabricated evidence is detected

Critical findings should block final action. High findings should route to evidence expansion or
human review depending on workflow impact.

## 7. Example Validation Outputs

Unsupported claim:

```json
{
  "finding_type": "unsupported_claim",
  "severity": "high",
  "target_agent": "reporting_agent",
  "claim": "The customer intentionally structured deposits to avoid reporting.",
  "support_status": "unsupported",
  "explanation": "The claim asserts intent, but the evidence only supports repeated threshold-adjacent transfers.",
  "evidence_refs": ["txn_101", "txn_102", "txn_103"],
  "citation_refs": [],
  "confidence": 0.88,
  "recommended_action": "Revise the claim to describe observed behavior or add admissible evidence of intent."
}
```

Invalid citation:

```json
{
  "finding_type": "invalid_citation",
  "severity": "critical",
  "target_agent": "executive_report",
  "claim": "AML policy requires immediate account closure.",
  "support_status": "contradicted",
  "explanation": "The cited policy ID was not returned by retrieval and does not exist in the policy registry.",
  "evidence_refs": [],
  "citation_refs": ["generated_policy_cite_44"],
  "confidence": 0.94,
  "recommended_action": "Block report approval and regenerate citations from approved policy sources."
}
```

Retrieval mismatch:

```json
{
  "finding_type": "retrieval_mismatch",
  "severity": "medium",
  "target_agent": "risk_scoring_agent",
  "claim": "The counterparty is located in a sanctioned jurisdiction.",
  "support_status": "partially_supported",
  "explanation": "The citation discusses jurisdiction screening generally but does not mention the counterparty.",
  "evidence_refs": ["retrieval_ev_9"],
  "citation_refs": ["cite_aml_9"],
  "confidence": 0.77,
  "recommended_action": "Run targeted counterparty retrieval and sanctions evidence verification."
}
```

Overconfident output:

```json
{
  "finding_type": "confidence_mismatch",
  "severity": "high",
  "target_agent": "fraud_detection_agent",
  "claim": "Fraud is confirmed.",
  "reported_confidence": 0.96,
  "calibrated_confidence": 0.61,
  "support_status": "partially_supported",
  "explanation": "Signals support suspicious behavior, but evidence does not confirm fraud.",
  "recommended_action": "Downgrade language to suspected fraud and route to analyst review."
}
```

Enterprise controls:

- persist every hallucination finding with claim and evidence lineage
- alert on fabricated evidence and invalid citation rates
- enforce stricter thresholds for regulatory and customer-impacting outputs
- block final reports with critical hallucination risk
- include hallucination risk trends in model risk management reviews

