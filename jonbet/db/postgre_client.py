import psycopg
from psycopg.rows import dict_row
from config import settings
from logger import AppLogger

#logger = App#logger.get_#logger("PostgresClient")


class PostgresClient:
    def __init__(self):
        self.url = settings.POSTGRES_URL
        self.conn = None

    async def connect(self):
        try:
            self.conn = await psycopg.AsyncConnection.connect(
                self.url, row_factory=dict_row
            )
            await self.conn.set_autocommit(True)
            #logger.info("Connected to database")
        except Exception as e:
            #logger.error(f"Failed to connect to database: {e}")
            raise

    async def _ensure_connection(self):
        try:
            await self.conn.execute("SELECT 1")
        except Exception:
            #logger.warning("Connection lost, reconnecting...")
            await self.connect()

    async def fetch_one(self, query: str, params=None) -> dict | None:
        await self._ensure_connection()
        #logger.debug(f"fetch_one: {query[:80]}...")
        async with self.conn.cursor() as cur:
            await cur.execute(query, params)
            return await cur.fetchone()

    async def fetch_all(self, query: str, params=None) -> list[dict]:
        await self._ensure_connection()
        #logger.debug(f"fetch_all: {query[:80]}...")
        async with self.conn.cursor() as cur:
            await cur.execute(query, params)
            return await cur.fetchall()

    async def execute(self, query: str, params=None) -> None:
        await self._ensure_connection()
        #logger.debug(f"execute: {query[:80]}...")
        async with self.conn.cursor() as cur:
            await cur.execute(query, params)

    async def close(self):
        if self.conn:
            await self.conn.close()
            #logger.info("Connection closed")