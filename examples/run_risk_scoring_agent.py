import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.graph.risk_scoring_agent_node import risk_scoring_agent_node

WORKFLOW_VERSION = "financial-investigation-v1"
SCHEMA_VERSION = "investigation-state-v1"


async def main() -> None:
    state = {
        "case_id": "case_risk_agent_demo",
        "tenant_id": "demo",
        "thread_id": "thread_demo_risk_agent",
        "transaction_id": "txn_risk_001",
        "workflow_version": WORKFLOW_VERSION,
        "schema_version": SCHEMA_VERSION,
        "status": "initialized",
        "fraud_score": 92.0,
        "compliance_score": 75.0,
        "compliance_flags": ["sar_threshold_met"],
        "critic_passed": False,
        "critic_notes": ["High-risk decision needs additional grounded evidence."],
        "fraud_detection": {
            "transaction_id": "txn_risk_001",
            "fraud_score": 92.0,
            "risk_band": "critical",
            "confidence": 0.91,
            "signals": ["structuring_signal", "rapid_chain_movement"],
            "evidence": [],
            "heuristics": [],
            "geographic_inconsistencies": [],
            "suspicious_behaviors": ["Structuring and rapid chain movement detected."],
            "escalation_recommendation": "temporary_hold",
            "explanation": "Critical fraud indicators detected.",
            "recommended_actions": ["place_temporary_hold", "senior_review"],
        },
        "transaction_analysis": {
            "transaction_id": "txn_risk_001",
            "aggregate": {
                "transaction_count": 3,
                "total_amount": 29_500.0,
                "average_amount": 9_833.33,
                "max_amount": 9_900.0,
                "currency": "USD",
                "unique_counterparties": 1,
                "inbound_amount": 0.0,
                "outbound_amount": 29_500.0,
            },
            "temporal": {
                "first_seen_at": "2026-05-20T01:02:00+00:00",
                "last_seen_at": "2026-05-20T01:14:00+00:00",
                "window_minutes": 12.0,
                "transactions_per_hour": 15.0,
                "burst_count": 2,
                "unusual_hour_count": 3,
            },
            "chain": [],
            "indicators": [],
            "anomaly_score": 88.0,
            "confidence": 0.82,
            "summary": "Structuring pattern detected.",
            "recommended_actions": ["senior_review"],
        },
        "financial_retrieval": {
            "query": "AML structuring escalation",
            "retrieval_intent": "risk_scoring",
            "results": [],
            "evidence": [{"evidence_id": "retrieval_ev_1"}],
            "citations": [{"citation_id": "cite_1"}],
            "confidence": 0.72,
            "answer_summary": "Grounded AML escalation evidence retrieved.",
            "source_attribution": ["AML Monitoring Guidance"],
            "recommended_actions": ["attach_citations"],
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

    result = await risk_scoring_agent_node(state)
    score = result["operational_risk"]
    print(
        {
            "severity_score": score["severity_score"],
            "risk_band": score["risk_band"],
            "confidence": score["confidence"],
            "escalation": score["escalation"]["level"],
            "actions": score["recommended_actions"],
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
