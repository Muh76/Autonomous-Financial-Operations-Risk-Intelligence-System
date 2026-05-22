# Compliance Reasoning Engine

This document defines a production-grade compliance reasoning engine for enterprise financial
investigation workflows. The engine supports AML-inspired checks, KYC workflows, operational policy
validation, transaction threshold monitoring, suspicious activity review, citation grounding, and
auditable escalation recommendations.

The engine is deterministic-first. Retrieval and AI-generated summaries can enrich context and
explanations, but compliance decisions should be driven by versioned policies, typed rules,
approved citations, and durable audit records.

## 1. Compliance Engine Architecture

```text
LangGraph compliance_agent_node
  -> ComplianceAgentService
      -> policy context loader
      -> policy retrieval adapter
      -> compliance rule engine
          -> AML-inspired rules
          -> KYC workflow rules
          -> operational policy rules
          -> transaction threshold rules
          -> suspicious activity review rules
      -> citation grounding validator
      -> compliance reasoning composer
      -> confidence scoring
      -> escalation recommender
      -> audit event writer
  -> InvestigationState partial update
```

Core components:

- **Policy context loader**: loads active policy version, threshold values, jurisdiction rules,
  KYC requirements, escalation mappings, and rule metadata.
- **Policy retrieval adapter**: retrieves AML guidance, compliance policies, governance reports,
  internal procedures, and policy excerpts for citation-backed reasoning.
- **Rule engine**: evaluates deterministic, policy-versioned rules against investigation state.
- **Reasoning composer**: turns rule outcomes into explainable compliance conclusions without
  inventing unsupported policy language.
- **Citation grounding validator**: ensures compliance conclusions cite approved policy or
  retrieval sources.
- **Confidence scorer**: calibrates confidence using rule coverage, citation support, evidence
  quality, and source freshness.
- **Escalation recommender**: maps rule outcomes to block, regulatory review, compliance review,
  analyst review, or no escalation.
- **Audit writer**: persists rule inputs, outputs, policy versions, citations, and decision
  rationale.

## 2. Policy Validation Framework

Policy validation should operate on explicit policy packs.

Policy pack structure:

```text
policy_pack_id
policy_version
effective_from
effective_to
jurisdiction_scope
thresholds
kyc_requirements
aml_typologies
sanctions_rules
escalation_matrix
citation_requirements
approval_requirements
```

Validation stages:

1. Resolve tenant, jurisdiction, customer segment, product type, and transaction context.
2. Load the active policy pack and validate it is effective for the investigation timestamp.
3. Retrieve relevant policy excerpts for AML, KYC, threshold, and suspicious activity checks.
4. Evaluate deterministic rules against typed workflow state.
5. Validate each failed or high-impact rule has policy citations.
6. Generate a policy-grounded reasoning summary.
7. Emit compliance flags, score, recommendation, confidence, citations, and audit metadata.

Policy validation outcomes:

- `compliant`: no material exception detected
- `policy_exception`: non-critical policy exception requires analyst review
- `kyc_review_required`: KYC profile is missing, stale, or insufficient
- `suspicious_activity_review_required`: AML-inspired pattern requires compliance review
- `threshold_review_required`: transaction threshold or aggregation threshold is exceeded
- `regulatory_review_required`: SAR-like review or regulatory workflow is required
- `blocked`: sanctions or critical policy failure requires immediate hold

## 3. Rule Engine Design

Rules should be small, deterministic, explainable, and versioned.

Rule contract:

```text
rule_id
rule_version
category
input_fields
policy_refs
evaluation
severity_mapping
failure_flag
required_citations
audit_tags
```

Runtime rule output:

```text
rule_id
category
passed
severity
rationale
policy_refs
evidence_refs
confidence
metadata
```

Recommended rule categories:

- **KYC rules**: verified status, enhanced due diligence, stale profile review, missing beneficial
  ownership, incomplete customer risk rating.
- **AML-inspired rules**: structuring indicators, rapid movement, circular flow, unusual
  counterparty behavior, high-risk geography, high-risk merchant category.
- **Threshold rules**: single transaction threshold, rolling window threshold, aggregate daily
  threshold, related transaction threshold.
- **Operational policy rules**: restricted account actions, manual approval requirements, internal
  investigation policy, report approval policy.
- **Citation rules**: high-risk compliance findings require approved policy citations.

Design principles:

- Rules should not call LLMs directly.
- Rules should return machine-readable failure flags.
- Thresholds should come from policy packs, not hard-coded business logic.
- Every high-impact failed rule should include evidence IDs and policy references.
- Rule versions should be persisted with each investigation decision.

## 4. Reasoning Pipeline

The reasoning pipeline converts deterministic rule outcomes into human-readable compliance
explanations.

Pipeline:

1. Group rule outcomes by category and severity.
2. Identify blocking failures, regulatory-review failures, and analyst-review failures.
3. Attach policy citations to each high-impact conclusion.
4. Summarize observed behavior without asserting intent unless evidence supports it.
5. Explain why the recommendation follows from the failed rules.
6. Calibrate confidence using rule coverage and citation grounding.
7. Persist the reasoning trace for audit and replay.

Reasoning rules:

- Use observed behavior language: "threshold exceeded" rather than "customer intended to evade."
- Separate evidence from inference.
- Cite policy for obligations and threshold requirements.
- Cite transaction evidence for observed behavior.
- Cite retrieval evidence for external or internal policy context.
- Mark evidence gaps explicitly.

Example reasoning trace:

```text
KYC status is verified.
Transaction amount exceeded the configured reporting threshold.
Fraud signals indicate threshold-adjacent repeated transfers.
AML policy citation cite_aml_threshold supports manual suspicious activity review.
Recommendation: regulatory review with SAR draft preparation.
```

## 5. Citation System

Citation grounding is mandatory for high-risk compliance outputs.

Citation sources:

- retrieved AML guidance
- internal compliance policies
- KYC procedures
- governance reports
- audit reports
- operational policy documents

Citation schema:

```text
citation_id
policy_pack_id
document_id
chunk_id
title
source_uri
source_version
quote
attribution
retrieved_at
grounding_score
```

Citation validation checks:

- citation ID exists in retrieval output or policy registry
- source version matches the active policy pack
- quote is non-empty for extractive policy support
- cited policy category matches the rule category
- high-risk finding has at least one policy citation
- report-ready compliance summary does not introduce uncited obligations

If citation validation fails, the engine should add `policy_citation_required` and route to
evidence expansion or compliance review.

## 6. Escalation Recommendation Logic

Escalation should be deterministic and explainable.

Priority order:

1. **Block**: sanctions hit, prohibited jurisdiction, frozen account policy, or critical policy
   breach.
2. **Regulatory review**: suspicious activity review, threshold review, SAR-like workflow, or
   severe AML pattern.
3. **Compliance review**: KYC failure, stale due diligence, policy citation gap, or unresolved
   policy exception.
4. **Analyst review**: medium-risk exception, missing context, or non-blocking operational policy
   issue.
5. **None**: no material compliance exception.

Recommendation output:

```text
level
required_role
rationale
recommended_actions
policy_refs
evidence_refs
confidence
```

Recommended actions:

- `place_temporary_hold`
- `prepare_sar_draft`
- `request_enhanced_due_diligence`
- `collect_missing_kyc`
- `rerun_policy_retrieval`
- `compliance_officer_review`
- `continue_standard_workflow`

Escalation decisions should be persisted with policy version, rule result IDs, citations, and the
workflow run ID.

## 7. LangGraph Integration

Recommended placement:

```text
transaction_analysis
  -> fraud_detection
  -> financial_retrieval
  -> compliance_agent
  -> risk_scoring_agent
  -> critic_agent
  -> reporting_agent / approval_checkpoint / escalation_router
```

The node should write:

- `compliance_validation`
- `compliance_score`
- `compliance_flags`
- `compliance_review`
- `recommended_actions`
- `findings`
- `agent_executions`
- `workflow_history`

Integration requirements:

- Run policy retrieval before compliance when high-impact reasoning requires citations.
- Re-run compliance after retrieval expansion, KYC updates, or human policy edits.
- Use retry policy for transient retrieval failures, not deterministic rule failures.
- Persist rule outputs and citation mappings before routing to risk scoring.
- Pass compliance flags and recommendation into risk scoring and critic validation.
- Pause for approval when recommendation level is `block` or `regulatory`.

Operational controls:

- alert on rising KYC failure, threshold review, and citation-gap rates
- monitor policy version drift across active workflow runs
- reconcile rule decisions during audit replay
- separate deterministic rule failures from retrieval coverage gaps
- require human approval for critical compliance recommendations

