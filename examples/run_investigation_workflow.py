import asyncio

from app.core.graph.workflow import run_investigation_workflow


async def main() -> None:
    result = await run_investigation_workflow("txn_2026_000001")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
