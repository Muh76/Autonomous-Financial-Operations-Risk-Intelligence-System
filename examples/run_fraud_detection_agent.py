import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.graph.fraud_detection_node import fraud_detection_node

WORKFLOW_VERSION = "financial-investigation-v1"
SCHEMA_VERSION = "investigation-state-v1"


async def main() -> None:
    state = {
        "case_id": "case_fraud_agent_demo",
        "tenant_id": "demo",
        "thread_id": "thread_demo_fraud_agent",
        "transaction_id": "txn_fraud_003",
        "workflow_version": WORKFLOW_VERSION,
        "schema_version": SCHEMA_VERSION,
        "status": "initialized",
        "transaction_amount": 9_850.0,
        "transaction_currency": "USD",
        "jurisdiction": "US",
        "transaction": {"device_id": "device_new"},
        "customer_profile": {"jurisdiction": "US", "known_device_ids": ["device_home"]},
        "merchant_profile": {"category": "crypto"},
        "transaction_history": [
            {
                "transaction_id": "txn_fraud_001",
                "amount": 9_750.0,
                "currency": "USD",
                "occurred_at": "2026-05-20T01:02:00+00:00",
                "account_id": "acct_123",
                "counterparty_id": "cp_shared",
                "direction": "outbound",
                "jurisdiction": "US",
                "device_id": "device_new",
            },
            {
                "transaction_id": "txn_fraud_002",
                "amount": 9_900.0,
                "currency": "USD",
                "occurred_at": "2026-05-20T01:08:00+00:00",
                "account_id": "acct_123",
                "counterparty_id": "cp_shared",
                "direction": "outbound",
                "jurisdiction": "US",
                "device_id": "device_new",
            },
            {
                "transaction_id": "txn_fraud_003",
                "amount": 9_850.0,
                "currency": "USD",
                "occurred_at": "2026-05-20T01:14:00+00:00",
                "account_id": "acct_123",
                "counterparty_id": "cp_shared",
                "direction": "outbound",
                "jurisdiction": "GB",
                "device_id": "device_new",
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

    result = await fraud_detection_node(state)
    fraud = result["fraud_detection"]
    print(
        {
            "fraud_score": fraud["fraud_score"],
            "risk_band": fraud["risk_band"],
            "confidence": fraud["confidence"],
            "signals": fraud["signals"],
            "escalation": fraud["escalation_recommendation"],
            "recommended_actions": fraud["recommended_actions"],
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
