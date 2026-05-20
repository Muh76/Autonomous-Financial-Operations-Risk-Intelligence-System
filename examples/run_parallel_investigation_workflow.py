import asyncio

from app.core.graph.parallel_workflow import run_parallel_investigation_workflow


async def main() -> None:
    result = await run_parallel_investigation_workflow(
        "txn_parallel_001",
        tenant_id="demo",
        transaction_amount=12_500.0,
        transaction_currency="USD",
        jurisdiction="US",
    )
    print(
        {
            "case_id": result["case_id"],
            "status": result["status"],
            "fraud_score": result.get("fraud_score"),
            "compliance_score": result.get("compliance_score"),
            "aggregate_risk_score": result.get("aggregate_risk_score"),
            "risk_band": result.get("risk_band"),
            "escalation_level": result.get("escalation_level"),
            "events": len(result.get("workflow_history", [])),
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
