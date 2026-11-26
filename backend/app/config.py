from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_prefix="SPONSR_", extra="ignore")

    database_url: str = f"sqlite:///{(ROOT / 'data' / 'sponsr.db').as_posix()}"
    jwt_secret: SecretStr = SecretStr("dev-only-change-me")
    session_days: int = 14
    cookie_secure: bool = False  # true behind HTTPS
    aws_region: str = "us-east-1"
    cv_model: str = "us.anthropic.claude-sonnet-5-5"
    import_key: SecretStr = SecretStr("")  # shared with the upstream matching engine for the daily push; empty = push disabled
    import_user: str = "demo"  # account that receives the daily import (and that the MCP server acts as)
    app_url: str = "https://sponsr.codetrend.com"  # public base URL (MCP OAuth issuer and links)
    mcp_token: SecretStr = SecretStr("")  # bearer token for /mcp (Claude Code demo); empty = closed


@lru_cache
def get_settings() -> Settings:
    return Settings()
