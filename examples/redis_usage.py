import asyncio

from app.cache.redis import RedisStore, get_redis_client


async def main() -> None:
    client = get_redis_client()
    try:
        store = RedisStore(client)
        key = store.key("investigation", "txn_2026_000001", "memory")
        await store.set_json(key, {"transaction_id": "txn_2026_000001", "status": "review"})
        await store.append_workflow_history("txn_2026_000001", "collect_transaction_context")
        print(await store.get_json(key))
        print(await store.get_workflow_history("txn_2026_000001"))
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
