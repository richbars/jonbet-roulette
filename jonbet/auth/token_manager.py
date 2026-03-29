import asyncio

from curl_cffi import requests as curl_requests
from seleniumbase import SB

from config import settings
from jonbet.db.redis_client import RedisClient
from logger import AppLogger

logger = AppLogger.get_logger("TokenManager")


class TokenManager:

    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self.token_key = "jonbet:access_token"

    async def get_token(self) -> str:
        token_redis = await self.redis.get(self.token_key)

        if token_redis:
            # logger.info("Token retrieved from Redis")
            return token_redis

        logger.warning("Token not found in Redis, authenticating via Playwright...")
        token = await self._get_token_playwright()

        if not token:
            raise Exception("Failed to obtain token after all attempts")

        return token

    async def _authenticate(self) -> str:
        logger.debug("Attempting authentication via API...")
        response = curl_requests.put(
            "https://jonbet.bet.br/api/auth/password",
            json={
                "username": settings.JONBET_USERNAME,
                "password": settings.JONBET_PASSWORD,
                "two_factor_code": ""
            },
            headers={
                "ipcountry": "BR",
                "sec-ch-ua-mobile": "?0",
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Origin": "https://jonbet.bet.br",
                "Referer": "https://jonbet.bet.br/pt/?modal=auth",
                "X-Client-Language": "pt",
                "X-Client-Version": "dad562fc3",
            },
            impersonate="chrome124",
            timeout=15
        )
        logger.debug(f"Authentication response: {response.status_code} - {response.text}")

        if response.status_code != 200:
            logger.error(f"Login failed: {response.status_code} - {response.text}")
            raise Exception(f"Login error: {response.status_code} - {response.text}")

        data = response.json()
        token = data.get("token") or data.get("access_token")

        if not token:
            logger.error(f"Token not found in response: {data}")
            raise Exception(f"Token not found in response: {data}")

        await self.redis.setex(self.token_key, settings.TOKEN_TTL_SECONDS, token)
        logger.info("Token successfully obtained and stored in Redis")

        return token

    async def _get_token_playwright(self, max_retries: int = 3) -> str | None:
        for attempt in range(1, max_retries + 1):
            logger.info(f"Playwright attempt {attempt}/{max_retries}...")
            try:
                token = await self._run_playwright()
                if token:
                    await self.redis.setex(self.token_key, settings.TOKEN_TTL_SECONDS, token)
                    logger.info(f"Token obtained on attempt {attempt}")
                    return token
                else:
                    logger.warning(f"Token not found on attempt {attempt}")
            except Exception as e:
                logger.error(f"Error on attempt {attempt}: {e}")

            if attempt < max_retries:
                logger.debug("Waiting 3s before next attempt...")
                await asyncio.sleep(3)

        logger.error("All attempts failed")
        return None

    async def _run_playwright(self) -> str | None:

        logger.debug("Starting browser session...")

        loop = asyncio.get_event_loop()
        token = await loop.run_in_executor(None, self._run_playwright_sync)
        return token

    def _run_playwright_sync(self) -> str | None:

        with SB(
                uc=True,
                headless=True,
                chromium_arg="--lang=pt-BR --disable-dev-shm-usage",
        ) as sb:
            sb.execute_cdp_cmd("Network.enable", {})

            sb.execute_cdp_cmd("Network.setExtraHTTPHeaders", {
                "headers": {
                    "Accept-Language": "pt-BR,pt;q=0.9"
                }
            })

            sb.execute_cdp_cmd("Emulation.setLocaleOverride", {
                "locale": "pt-BR"
            })

            sb.execute_cdp_cmd("Emulation.setTimezoneOverride", {
                "timezoneId": "America/Sao_Paulo"
            })

            sb.open("https://jonbet.bet.br/pt/?modal=auth")

            try:
                sb.click("text=EU TENHO MAIS DE 18 ANOS")
                sb.sleep(1)
            except:
                pass

            try:
                sb.click("text=ACEITAR TODOS OS COOKIES")
                sb.sleep(1)
            except:
                pass

            sb.wait_for_element('input[name="username"]', timeout=10)
            sb.type('input[name="username"]', settings.JONBET_USERNAME)
            sb.sleep(0.3)
            sb.type('input[type="password"]', settings.JONBET_PASSWORD)
            sb.sleep(0.5)

            try:
                sb.uc_gui_click_captcha()
                sb.sleep(2)
            except Exception as e:
                logger.warning(f"Captcha not clicked: {e}")

            sb.click('button[data-testid="login-submit-button"]')
            sb.sleep(5)

            refresh_token = sb.execute_script("return localStorage.getItem('REFRESH_TOKEN');")

            if not refresh_token:
                logger.warning("REFRESH_TOKEN not found in localStorage")
                return None

            logger.info("Refresh token captured successfully")
            return refresh_token

    async def invalidate(self):
        logger.info(f"Invalidating token for key: {self.token_key}")
        await self.redis.delete(self.token_key)
