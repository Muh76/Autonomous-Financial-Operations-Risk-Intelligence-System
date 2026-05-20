import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.graph.transaction_analysis_node import transaction_analysis_node

WORKFLOW_VERSION = "financial-investigation-v1"
SCHEMA_VERSION = "investigation-state-v1"


async def main() -> None:
    state = {
        "case_id": "case_transaction_agent_demo",
        "tenant_id": "demo",
        "thread_id": "thread_demo_transaction_agent",
        "transaction_id": "txn_demo_003",
        "workflow_version": WORKFLOW_VERSION,
        "schema_version": SCHEMA_VERSION,
        "status": "initialized",
        "transaction_amount": 9_850.0,
        "transaction_currency": "USD",
        "jurisdiction": "US",
        "transaction_history": [
            {
                "transaction_id": "txn_demo_001",
                "amount": 9_750.0,
                "currency": "USD",
                "occurred_at": "2026-05-20T01:02:00+00:00",
                "account_id": "acct_123",
                "counterparty_id": "cp_shared",
                "direction": "outbound",
                "jurisdiction": "US",
            },
            {
                "transaction_id": "txn_demo_002",
                "amount": 9_900.0,
                "currency": "USD",
                "occurred_at": "2026-05-20T01:08:00+00:00",
                "account_id": "acct_123",
                "counterparty_id": "cp_shared",
                "direction": "outbound",
                "jurisdiction": "US",
            },
            {
                "transaction_id": "txn_demo_003",
                "amount": 9_850.0,
                "currency": "USD",
                "occurred_at": "2026-05-20T01:14:00+00:00",
                "account_id": "acct_123",
                "counterparty_id": "cp_shared",
                "direction": "outbound",
                "jurisdiction": "GB",
            },
        ],
        "evidence": [],
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

    result = await transaction_analysis_node(state)
    analysis = result["transaction_analysis"]
    print(
        {
            "anomaly_score": analysis["anomaly_score"],
            "confidence": analysis["confidence"],
            "indicators": [item["indicator"] for item in analysis["indicators"]],
            "recommended_actions": analysis["recommended_actions"],
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
