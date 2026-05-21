import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.graph.reporting_agent_node import reporting_agent_node

WORKFLOW_VERSION = "financial-investigation-v1"
SCHEMA_VERSION = "investigation-state-v1"


async def main() -> None:
    state = {
        "case_id": "case_reporting_demo",
        "tenant_id": "demo",
        "thread_id": "thread_demo_reporting",
        "transaction_id": "txn_reporting_001",
        "workflow_version": WORKFLOW_VERSION,
        "schema_version": SCHEMA_VERSION,
        "status": "reporting",
        "risk_band": "critical",
        "escalation_level": "block",
        "financial_retrieval": {
            "query": "AML escalation evidence",
            "retrieval_intent": "reporting",
            "results": [],
            "evidence": [],
            "citations": [
                {
                    "citation_id": "cite_1",
                    "document_id": "aml_guidance_001",
                    "chunk_id": "chunk_1",
                    "title": "AML Monitoring Guidance",
                    "source_uri": "policy://aml/monitoring-guidance",
                    "document_type": "aml_guidance",
                    "quote": "AML programs should monitor structuring.",
                    "attribution": "AML Monitoring Guidance",
                }
            ],
            "confidence": 0.72,
            "answer_summary": "AML evidence retrieved.",
            "source_attribution": ["AML Monitoring Guidance"],
            "recommended_actions": ["attach_citations"],
        },
        "fraud_detection": {
            "risk_band": "critical",
            "confidence": 0.91,
            "explanation": "Critical fraud indicators detected.",
        },
        "operational_risk": {
            "severity_score": 94.0,
            "risk_band": "critical",
            "confidence": 0.88,
            "explanation": "Operational risk is critical.",
            "escalation": {
                "level": "block",
                "rationale": "Critical risk requires controlled escalation.",
            },
            "recommended_actions": ["place_temporary_hold", "senior_review"],
        },
        "critic_validation": {
            "passed": True,
            "reliability_score": 0.9,
            "confidence": 0.84,
            "summary": "Critic validation passed.",
            "safety_recommendation": "continue",
            "required_actions": ["continue_workflow"],
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

    result = await reporting_agent_node(state)
    report = result["executive_report"]
    print(
        {
            "status": report["status"],
            "confidence": report["confidence"],
            "citations": len(report["citations"]),
            "findings": len(report["findings"]),
            "final_report_uri": result["final_report_uri"],
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
