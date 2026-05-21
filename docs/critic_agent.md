# Critic Agent

The Critic Agent validates enterprise AI workflow outputs before final reporting, escalation, or
human approval. It focuses on hallucination detection, unsupported claims, evidence grounding,
contradiction analysis, reasoning consistency, and confidence calibration.

## 1. Critic Architecture

```text
LangGraph critic_agent_node
  -> CriticService
      -> evidence verification
      -> contradiction detection
      -> confidence calibration
      -> hallucination and unsupported-claim checks
      -> reliability scoring
      -> safety recommendation
  -> InvestigationState partial update
```

Validated sources:

- fraud agent output
- compliance flags and review output
- retrieval agent citations and evidence
- risk scoring output

## 2. Validation Pipeline

Pipeline stages:

1. Count checked claims from each target agent.
2. Compare claims against structured evidence and retrieval citations.
3. Detect cross-agent contradictions.
4. Calibrate reported confidence against evidence support.
5. Generate explainable critic findings.
6. Compute reliability score.
7. Decide whether workflow may continue, needs evidence expansion, or requires human review.

## 3. Hallucination Detection Strategy

The deterministic baseline treats high-impact claims as unsafe when they lack grounding.

Examples:

- high-risk workflow without retrieval citations
- fraud signals without evidence references
- risk score escalation unsupported by fraud/compliance evidence
- final action recommendation without citation-backed rationale

Model-assisted hallucination detection can later be added behind the same typed output contract.

## 4. Evidence Verification Framework

The critic emits `EvidenceVerificationResult` per agent:

```text
target_agent
checked_claims
supported_claims
unsupported_claims
citation_count
grounding_score
```

Grounding uses:

- workflow evidence refs
- retrieval evidence
- retrieval citations
- structured fraud/risk/compliance outputs

## 5. Contradiction Analysis System

The critic detects contradictions such as:

- fraud agent says high/critical while risk scoring says low
- sanctions hit without block or regulatory escalation
- critic failure ignored by final report path

Each contradiction records:

```text
left_agent
right_agent
description
severity
evidence_refs
```

## 6. Reliability Scoring

Reliability score combines:

- average grounding score
- contradiction penalties
- confidence calibration penalties
- finding count penalties

Safety recommendations:

- `continue`
- `revise_outputs`
- `expand_evidence`
- `human_review`
- `block_final_action`

## 7. LangGraph Integration

`critic_agent_node(...)` writes:

- `critic_validation`
- `critic_passed`
- `critic_notes`
- `confidence_assessment`
- `findings`
- `agent_executions`
- `workflow_history`
- `next_route`

Run the example:

```bash
python examples/run_critic_agent.py
```

Recommended placement:

```text
fraud_detection
  -> financial_retrieval
  -> risk_scoring_agent
  -> critic_agent
  -> report_generation / evidence_expansion / escalation_router
```

## Enterprise Notes

- Keep critic outputs structured and auditable.
- Use deterministic checks as the safety baseline.
- Treat model-assisted critique as an additional signal, not sole authority.
- Require citations for high-risk final actions.
- Persist critic findings for model risk management and investigation replay.
