from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")
    database_url: str = Field(min_length=1)
    database_direct_url: str | None = None
    jwt_secret: str = Field(min_length=32)
    frontend_origin: str = "http://localhost:3000"
    cookie_secure: bool = False
    payment_mode: Literal["demo", "disabled"] = "demo"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    blob_read_write_token: str | None = None
    blob_public_base_url: str | None = None
    environment: Literal["development", "test", "production"] = "development"

    @model_validator(mode="after")
    def production_safety(self):
        if self.environment == "production" and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE deve ser true em produção")
        origin = urlsplit(self.frontend_origin)
        if origin.scheme not in {"http", "https"} or not origin.hostname or origin.username or origin.password or origin.path not in {"", "/"} or origin.query or origin.fragment:
            raise ValueError("FRONTEND_ORIGIN deve ser uma origem HTTP(S) sem caminho, parâmetros ou fragmento")
        if self.environment == "production" and origin.scheme != "https":
            raise ValueError("FRONTEND_ORIGIN deve usar HTTPS em produção")
        for name, value in [("DATABASE_URL", self.database_url), ("DATABASE_DIRECT_URL", self.database_direct_url)]:
            if not value:
                continue
            if not value.startswith(("postgresql://", "postgresql+psycopg://")):
                raise ValueError(f"{name} deve usar PostgreSQL")
            try:
                parsed = make_url(value)
            except ArgumentError:
                raise ValueError(f"{name} deve ser uma ligação PostgreSQL válida") from None
            if self.environment == "production" and parsed.query.get("sslmode") not in {"require", "verify-ca", "verify-full"}:
                raise ValueError(f"{name} deve exigir TLS com sslmode=require, verify-ca ou verify-full em produção")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
