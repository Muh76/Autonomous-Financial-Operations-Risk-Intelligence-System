import json
from collections.abc import AsyncIterator
from typing import Any

from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

_pool: ConnectionPool | None = None


def initialize_redis_pool() -> None:
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=settings.redis_max_connections,
            socket_connect_timeout=settings.redis_socket_timeout,
            socket_timeout=settings.redis_socket_timeout,
            health_check_interval=settings.redis_health_check_interval,
        )


def get_redis_client() -> Redis:
    if _pool is None:
        initialize_redis_pool()
    if _pool is None:
        raise RuntimeError("Redis connection pool is not initialized")
    return Redis(connection_pool=_pool)


async def get_redis() -> AsyncIterator[Redis]:
    client = get_redis_client()
    try:
        yield client
    finally:
        await client.aclose()


async def check_redis_connection() -> bool:
    client = get_redis_client()
    try:
        return bool(await client.ping())
    except Exception:
        return False
    finally:
        await client.aclose()


async def close_redis_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


class RedisStore:
    def __init__(self, client: Redis, namespace: str = "aforis") -> None:
        self._client = client
        self._namespace = namespace

    def key(self, *parts: str) -> str:
        clean_parts = [part.strip(":") for part in parts if part]
        return ":".join([self._namespace, *clean_parts])

    async def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int | None = None) -> None:
        await self._client.set(
            key,
            json.dumps(value, separators=(",", ":")),
            ex=ttl_seconds,
        )

    async def get_json(self, key: str) -> dict[str, Any] | None:
        raw_value = await self._client.get(key)
        if raw_value is None:
            return None
        value = json.loads(raw_value)
        if not isinstance(value, dict):
            raise ValueError(f"Redis key {key} does not contain a JSON object")
        return value

    async def append_workflow_history(self, transaction_id: str, event: str) -> None:
        await self._client.rpush(self.key("workflow", transaction_id, "history"), event)

    async def get_workflow_history(self, transaction_id: str) -> list[str]:
        values = await self._client.lrange(self.key("workflow", transaction_id, "history"), 0, -1)
        return [str(value) for value in values]
