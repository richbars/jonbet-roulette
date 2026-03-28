import asyncio
import selectors

from jonbet.service.polling_roulette import Polling
from logger import AppLogger

logger = AppLogger.get_logger("Main")


async def run_polling():
    """Executa o polling de spins da roleta"""
    print("Iniciando polling de spins...")
    polling = Polling()
    await polling.process_spins()


if __name__ == "__main__":
    asyncio.run(run_polling(), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
