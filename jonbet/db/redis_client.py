import redis.asyncio as aioredis
from config import settings


class RedisClient:
    def __init__(self):
        if settings.REDIS_URL:
            self.client = aioredis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )
        else:
            self.client = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )

    async def get(self, key: str) -> str | None:
        return await self.client.get(key)

    async def set(self, key: str, value: str) -> None:
        await self.client.set(key, value)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        await self.client.setex(key, ttl, value)

    async def delete(self, key: str) -> None:
        await self.client.delete(key)

    async def ping(self) -> bool:
        try:
            return await self.client.ping()
        except Exception:
            return False