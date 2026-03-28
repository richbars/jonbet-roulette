import asyncio
from datetime import datetime
from typing import Optional

import requests

from jonbet.auth.token_manager import TokenManager
from jonbet.db.postgre_client import PostgresClient
from jonbet.db.redis_client import RedisClient
from jonbet.dto.roulette_spin_dto import RouletteSpinDTO
from jonbet.entity.roulette_spin_entity import RouletteSpinEntity
from jonbet.schema.roulette_spin_schema import RouletteSpinSchema
from logger import AppLogger

logger = AppLogger.get_logger("Polling")


class Polling:
    POLLING_INTERVAL_SECONDS = 5

    def __init__(self):
        redis_client = RedisClient()
        self.token_manager = TokenManager(redis_client)
        self.token_key = "jonbet:access_token"
        self.postgres = PostgresClient()

    async def get_spins(self) -> list[dict]:
        token = await self.token_manager.get_token()

        url = "https://jonbet.bet.br/api/singleplayer-originals/originals/roulette_games/recent/1"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"Bearer {token}"
        }

        response = requests.request("GET", url, headers=headers)
        response.raise_for_status()

        return response.json()

    async def _spin_to_entity(self, spin_data: dict) -> Optional[RouletteSpinEntity]:
        spin_id = str(spin_data.get("id"))
        created_at = datetime.fromisoformat(spin_data.get("created_at").replace("Z", "+00:00"))
        color = spin_data.get("color")
        roll = spin_data.get("roll")

        if not all([spin_id, created_at, color is not None, roll is not None]):
            logger.warning(f"Invalid spin data: {spin_data}")
            return None

        return RouletteSpinEntity(
            id=spin_id,
            created_at=created_at,
            color=color,
            roll=roll
        )

    async def _save_spin(self, entity: RouletteSpinEntity) -> bool:
        await self.postgres.execute(
            RouletteSpinSchema.insert(),
            (entity.id, entity.created_at, entity.color, entity.roll)
        )
        logger.info(f"Spin saved: id={entity.id}, roll={entity.roll}, color={entity.color}")
        return True

    async def _spin_exists(self, spin_id: str) -> bool:
        result = await self.postgres.fetch_one(RouletteSpinSchema.exists(), (spin_id,))
        return result is not None

    async def process_spins(self):
        await self.postgres.connect()
        await self.postgres.execute(RouletteSpinSchema.create_table())

        try:
            while True:
                spins_data = await self.get_spins()

                if not spins_data:
                    logger.debug("No spins data received")
                    await asyncio.sleep(self.POLLING_INTERVAL_SECONDS)
                    continue

                saved_count = 0
                for spin_data in spins_data:
                    entity = await self._spin_to_entity(spin_data)
                    if not entity:
                        continue

                    exists = await self._spin_exists(entity.id)
                    if exists:
                        #logger.debug(f"Spin {entity.id} already exists, skipping")
                        continue

                    await self._save_spin(entity)
                    saved_count += 1

                if saved_count > 0:
                    logger.info(f"Saved {saved_count} new spins")

                await asyncio.sleep(self.POLLING_INTERVAL_SECONDS)

        except Exception as e:
            logger.error(f"Polling error: {e}")
            raise
        finally:
            await self.postgres.close()
