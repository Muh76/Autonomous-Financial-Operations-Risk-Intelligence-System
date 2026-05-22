# Evidence Validation System

This document defines a production-grade evidence validation system for enterprise AI workflows.
The system verifies that claims, citations, retrieved evidence, reasoning, and confidence values are
grounded before downstream agents produce risk decisions, compliance recommendations, escalation
summaries, or executive reports.

The design is deterministic-first, explainable, and audit-ready. Model-assisted validation can be
used as an additional signal, but final workflow gates should depend on source references,
retrieval metadata, typed claims, citation integrity, and persisted validation records.

## 1. Evidence Validation Architecture

```text
Agent output
  -> claim normalizer
  -> evidence resolver
  -> citation verifier
  -> retrieval grounding validator
  -> completeness checker
  -> contradiction analyzer
  -> confidence-aware scorer
  -> validation decision router
  -> audit repository
```

Core components:

- **Claim normalizer**: extracts atomic claims from fraud, compliance, retrieval, risk scoring,
  critic, and reporting outputs.
- **Evidence resolver**: maps claim references to transactions, retrieved evidence, citations,
  policy rules, investigation findings, and durable evidence records.
- **Citation verifier**: checks citation existence, source version, document identity, quote
  integrity, attribution, and policy-source allowlists.
- **Retrieval grounding validator**: verifies that retrieved passages actually support the claim
  they are attached to.
- **Completeness checker**: verifies that high-impact conclusions include enough evidence across
  required categories.
- **Contradiction analyzer**: detects conflicts between claims, evidence, citations, policies, and
  workflow decisions.
- **Confidence-aware scorer**: calibrates validation confidence and evidence strength against
  source quality and claim severity.
- **Audit repository**: persists validation inputs, decisions, score components, and remediation
  actions.

Validation should run before critical workflow transitions such as risk scoring, regulatory review,
human approval, report generation, and final escalation.

## 2. Citation Verification Pipeline

Citation verification ensures that every citation is real, source-attributed, and appropriate for
the claim it supports.

Pipeline:

1. Collect citation references from retrieval outputs, compliance validation, critic findings, risk
   scoring explanations, and executive report findings.
2. Resolve each citation ID against the retrieval result set, policy registry, or durable evidence
   repository.
3. Verify required citation fields: document ID, chunk ID, title, source URI, document type, quote,
   attribution, version, and retrieved timestamp.
4. Check that the cited document category matches the claim type.
5. Validate that the citation source is approved for the tenant, jurisdiction, workflow type, and
   user permission level.
6. Detect fabricated, stale, duplicate, malformed, or orphaned citations.
7. Emit citation validation findings with severity and remediation steps.

Citation statuses:

- `valid`: citation exists and matches the supported claim category.
- `missing`: claim requires a citation but no citation was supplied.
- `orphaned`: citation appears in an output but is absent from retrieval or policy records.
- `stale`: citation source version is no longer active for the workflow timestamp.
- `mismatched`: citation exists but does not support the claim category or entity.
- `restricted`: citation exists but cannot be used in this tenant or access context.

High-risk compliance, fraud, and report claims should not proceed with missing, orphaned, or stale
citations.

## 3. Retrieval Grounding Strategy

Retrieval grounding validates alignment between claims and retrieved evidence.

Grounding checks:

- claim entities match cited passage entities
- transaction IDs, account IDs, customer IDs, merchant IDs, and counterparties match evidence
- amounts, dates, currencies, jurisdictions, and thresholds match source records
- policy claims cite policy or guidance documents, not unrelated evidence
- fraud and anomaly claims cite transaction or behavior evidence
- report summaries do not introduce new claims absent from validated findings
- grounding score and rerank score meet the severity threshold

Severity-based thresholds:

```text
low impact: grounding_score >= 0.50
medium impact: grounding_score >= 0.65
high impact: grounding_score >= 0.80
critical impact: grounding_score >= 0.90 and citation required
```

Grounding states:

- `grounded`: claim is directly supported by evidence and citations.
- `partially_grounded`: evidence supports only part of the claim.
- `weakly_grounded`: evidence exists but has low retrieval or grounding confidence.
- `ungrounded`: no source evidence supports the claim.
- `contradicted`: source evidence conflicts with the claim.

The validator should preserve the evidence chain from generated claim to cited document chunk so
investigation replay can reconstruct why a decision was allowed or blocked.

## 4. Evidence Scoring System

Evidence scoring combines completeness, source quality, citation integrity, retrieval grounding, and
confidence calibration.

Score dimensions:

```text
citation_integrity_score: 0.00-1.00
retrieval_grounding_score: 0.00-1.00
evidence_completeness_score: 0.00-1.00
source_authority_score: 0.00-1.00
freshness_score: 0.00-1.00
contradiction_score: 0.00-1.00
confidence_alignment_score: 0.00-1.00
```

Weighted evidence support score:

```text
supporting_evidence_score =
  0.20 * citation_integrity_score
  + 0.20 * retrieval_grounding_score
  + 0.20 * evidence_completeness_score
  + 0.15 * source_authority_score
  + 0.10 * freshness_score
  + 0.10 * contradiction_score
  + 0.05 * confidence_alignment_score
```

Decision bands:

- `strong`: score >= 0.90 and no high-severity validation findings
- `sufficient`: score >= 0.75 and no critical validation findings
- `incomplete`: score >= 0.55 with evidence gaps or citation gaps
- `weak`: score < 0.55 or unsupported high-impact claims
- `invalid`: fabricated evidence, invalid citation, or critical contradiction detected

Evidence completeness checks:

- high-risk fraud findings require transaction evidence and behavioral signal evidence
- compliance findings require policy citations and rule IDs
- retrieval claims require source attribution and citation IDs
- risk scoring requires upstream fraud, compliance, retrieval, or critic evidence
- report findings require evidence IDs or citation IDs from validated upstream outputs

## 5. Contradiction Analysis

Contradiction analysis compares claims against evidence and against each other.

Contradiction classes:

- **Claim-evidence contradiction**: source evidence conflicts with the generated claim.
- **Citation-claim contradiction**: cited passage discusses a different fact, policy, or entity.
- **Cross-agent contradiction**: fraud, compliance, risk, critic, or reporting agents disagree on
  severity or recommendation.
- **Temporal contradiction**: event sequence is impossible or inconsistent with timestamps.
- **Entity contradiction**: customer, account, jurisdiction, merchant, or counterparty differs
  across evidence.
- **Decision contradiction**: workflow route conflicts with validation state or approval state.

Analysis graph:

```text
claim -> cites -> citation -> sourced_from -> evidence
claim -> derived_from -> agent_output
claim -> references -> entity / transaction / policy
claim -> supports | contradicts -> claim
decision -> depends_on -> validation_result
```

Severity rules:

- critical: invalid regulatory action, false clearance, fabricated source, or unsafe final report
- high: changes risk band, escalation recommendation, or compliance outcome
- medium: affects explanation, supporting rationale, or non-final recommendation
- low: informational conflict that does not affect workflow route

Critical contradictions should block final action. High contradictions should route to human review
or targeted evidence expansion.

## 6. Validation Outputs

Primary validation result:

```text
validation_id
workflow_run_id
case_id
target_agent
validated_at
passed
supporting_evidence_score
evidence_band
confidence
findings
claim_results
citation_results
grounding_results
contradictions
required_actions
policy_version
metadata
```

Finding schema:

```text
finding_id
finding_type
severity
claim_id
target_agent
explanation
evidence_refs
citation_refs
recommendation
confidence
```

Example output:

```json
{
  "validation_id": "ev_val_001",
  "target_agent": "reporting_agent",
  "passed": false,
  "supporting_evidence_score": 0.52,
  "evidence_band": "incomplete",
  "confidence": 0.86,
  "findings": [
    {
      "finding_type": "missing_citation",
      "severity": "high",
      "claim_id": "claim_report_7",
      "explanation": "High-risk escalation summary has no policy or retrieval citation.",
      "recommendation": "Run retrieval expansion and bind the claim to approved citations."
    }
  ],
  "required_actions": ["expand_evidence", "repair_citations", "human_review"]
}
```

Outputs should be immutable once persisted. Later corrections should create a new validation version
rather than overwriting the original result.

## 7. Workflow Integration

Recommended LangGraph placement:

```text
financial_retrieval
  -> evidence_validation
  -> compliance_agent
  -> fraud_detection
  -> risk_scoring_agent
  -> critic_agent
  -> report_generation
  -> final_evidence_validation
  -> approval_checkpoint / escalation_router
```

Integration patterns:

- Run lightweight citation and evidence checks after retrieval.
- Run full evidence validation before risk scoring and before final report approval.
- Re-run validation after evidence expansion, human edits, policy updates, or agent retries.
- Persist validation results to PostgreSQL for audit replay.
- Cache active validation status in Redis for long-running workflow coordination.
- Attach validation IDs to critic outputs and executive reports.
- Use validation results as inputs to confidence calibration and escalation routing.

Gate routing:

- `continue`: evidence is strong or sufficient.
- `expand_evidence`: evidence is incomplete or weak.
- `repair_citations`: citations are missing, stale, orphaned, or mismatched.
- `resolve_contradictions`: high-impact conflicts exist.
- `human_review`: validation uncertainty affects customer, regulatory, or operational outcomes.
- `block_final_action`: fabricated evidence, invalid citation, or critical contradiction detected.

Operational controls:

- track missing citation and unsupported claim rates by agent
- alert on fabricated evidence or citation mismatch spikes
- audit validation decisions by policy version and workflow version
- enforce stricter evidence thresholds for regulatory and customer-impacting actions
- include evidence validation summaries in executive reports and investigation replay views

