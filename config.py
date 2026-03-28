import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _get_env(key: str, default=None, required: bool = False):
    value = os.getenv(key, default)

    if required and value is None:
        raise ValueError(f"Missing environment variable: {key}")

    return value


@dataclass
class Settings:
    # API JONBET
    JONBET_USERNAME: str
    JONBET_PASSWORD: str

    # TOKEN
    TOKEN_TTL_SECONDS: int

    # POSTGRES (URL OU CAMPOS)
    POSTGRES_URL: str | None
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    # REDIS (URL OU CAMPOS)
    REDIS_URL: str | None
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_PASSWORD: str | None

    # APP
    POLLING_INTERVAL: int


def load_settings() -> Settings:
    return Settings(
        # API
        JONBET_USERNAME=_get_env("JONBET_USERNAME", required=True),
        JONBET_PASSWORD=_get_env("JONBET_PASSWORD", required=True),

        # TOKEN
        TOKEN_TTL_SECONDS=int(_get_env("TOKEN_TTL_SECONDS", 3600)),

        # POSTGRES
        POSTGRES_URL=_get_env("POSTGRES_URL", None),
        POSTGRES_HOST=_get_env("POSTGRES_HOST", "localhost"),
        POSTGRES_PORT=int(_get_env("POSTGRES_PORT", 5432)),
        POSTGRES_DB=_get_env("POSTGRES_DB", required=False),
        POSTGRES_USER=_get_env("POSTGRES_USER", required=False),
        POSTGRES_PASSWORD=_get_env("POSTGRES_PASSWORD", required=False),

        # REDIS
        REDIS_URL=_get_env("REDIS_URL", None),
        REDIS_HOST=_get_env("REDIS_HOST", "localhost"),
        REDIS_PORT=int(_get_env("REDIS_PORT", 6379)),
        REDIS_DB=int(_get_env("REDIS_DB", 0)),
        REDIS_PASSWORD=_get_env("REDIS_PASSWORD", None),

        # APP
        POLLING_INTERVAL=int(_get_env("POLLING_INTERVAL", 5)),
    )


settings = load_settings()