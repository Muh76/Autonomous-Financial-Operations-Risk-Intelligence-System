import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.graph.critic_agent_node import critic_agent_node

WORKFLOW_VERSION = "financial-investigation-v1"
SCHEMA_VERSION = "investigation-state-v1"


async def main() -> None:
    state = {
        "case_id": "case_critic_demo",
        "tenant_id": "demo",
        "thread_id": "thread_demo_critic",
        "transaction_id": "txn_critic_001",
        "workflow_version": WORKFLOW_VERSION,
        "schema_version": SCHEMA_VERSION,
        "status": "critic_validation",
        "risk_band": "critical",
        "compliance_flags": ["sar_threshold_met"],
        "fraud_detection": {
            "transaction_id": "txn_critic_001",
            "fraud_score": 91.0,
            "risk_band": "critical",
            "confidence": 0.92,
            "signals": ["structuring_signal", "rapid_chain_movement"],
            "evidence": [],
            "heuristics": [],
            "geographic_inconsistencies": [],
            "suspicious_behaviors": ["Structuring detected."],
            "escalation_recommendation": "temporary_hold",
            "explanation": "Critical fraud indicators detected.",
            "recommended_actions": ["place_temporary_hold"],
        },
        "financial_retrieval": {
            "query": "AML structuring escalation",
            "retrieval_intent": "critic_validation",
            "results": [],
            "evidence": [{"evidence_id": "retrieval_ev_1"}],
            "citations": [{"citation_id": "cite_1"}],
            "confidence": 0.74,
            "answer_summary": "Grounded AML escalation evidence retrieved.",
            "source_attribution": ["AML Monitoring Guidance"],
            "recommended_actions": ["attach_citations"],
        },
        "operational_risk": {
            "aggregate_score": 72.0,
            "severity_score": 94.0,
            "risk_band": "critical",
            "confidence": 0.86,
            "signals": [{"signal_name": "fraud"}, {"signal_name": "compliance"}],
            "escalation": {
                "level": "block",
                "priority": 1,
                "required_role": "compliance_officer",
                "rationale": "Critical risk requires controlled escalation.",
                "recommended_actions": ["place_temporary_hold"],
            },
            "critic_adjustments": [],
            "evidence_gaps": [],
            "recommended_actions": ["place_temporary_hold"],
            "explanation": "Critical operational risk.",
            "policy_version": "operational-risk-policy-v1",
            "scoring_model_version": "weighted-operational-risk-v1",
        },
        "compliance_validation": {
            "passed": False,
            "score": 68.0,
            "flags": ["sar_threshold_met"],
            "rule_results": [],
            "citations": [{"citation_id": "cite_1"}],
            "recommendation": {
                "level": "regulatory",
                "rationale": "SAR threshold requires review.",
                "required_actions": ["prepare_sar_review"],
            },
            "suspicious_activity_summary": "Structuring review required.",
            "policy_version": "aml-compliance-policy-v1",
            "confidence": 0.74,
        },
        "evidence": [{"evidence_id": "ev_1"}],
        "findings": [],
        "workflow_history": [],
        "node_errors": [],
        "approvals": [],
        "escalations": [],
        "node_results": [],
        "agent_executions": [],
        "node_traces": [],
        "edge_traversals": [],
        "timeline_events": [],
        "retry_counts": {},
        "retry_state": {},
        "fallback_used": {},
    }

    result = await critic_agent_node(state)
    critic = result["critic_validation"]
    print(
        {
            "passed": critic["passed"],
            "reliability_score": critic["reliability_score"],
            "recommendation": critic["safety_recommendation"],
            "findings": len(critic["findings"]),
            "next_route": result["next_route"],
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
