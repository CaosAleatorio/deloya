from functools import lru_cache
from typing import Literal
from urllib.parse import SplitResult, urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def _parse_frontend_origin(value: str, name: str) -> SplitResult:
    message = f"{name} deve ser uma origem HTTP(S) sem caminho, parâmetros, fragmento ou wildcard"
    try:
        origin = urlsplit(value)
        _ = origin.port
    except ValueError:
        raise ValueError(message) from None
    if (origin.scheme not in {"http", "https"} or not origin.hostname
            or origin.username is not None or origin.password is not None
            or origin.path not in {"", "/"} or "?" in value or "#" in value
            or "*" in origin.netloc or "\\" in origin.netloc or origin.netloc.endswith(":")
            or any(character.isspace() for character in value)):
        raise ValueError(message)
    return origin


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")
    database_url: str = Field(min_length=1)
    database_direct_url: str | None = None
    jwt_secret: str = Field(min_length=32)
    frontend_origin: str = "http://localhost:3000"
    development_frontend_origins: list[str] = Field(default_factory=list)
    cookie_secure: bool = False
    payment_mode: Literal["manual", "demo", "disabled"] = "manual"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    blob_read_write_token: str | None = None
    blob_public_base_url: str | None = None
    blob_private_read_write_token: str | None = None
    environment: Literal["development", "test", "production"] = "development"

    @property
    def allowed_frontend_origins(self) -> list[str]:
        configured = self.frontend_origin.rstrip("/")
        origins = [configured]
        if self.environment != "development":
            return origins
        origin = urlsplit(configured)
        alias = {"localhost": "127.0.0.1", "127.0.0.1": "localhost"}.get(origin.hostname)
        if alias:
            port = f":{origin.port}" if origin.port is not None else ""
            origins.append(f"{origin.scheme}://{alias}{port}")
        for additional in self.development_frontend_origins:
            normalized = additional.rstrip("/")
            if normalized not in origins:
                origins.append(normalized)
        return origins

    @model_validator(mode="after")
    def production_safety(self):
        if self.environment == "production" and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE deve ser true em produção")
        origin = _parse_frontend_origin(self.frontend_origin, "FRONTEND_ORIGIN")
        for additional in self.development_frontend_origins:
            _parse_frontend_origin(additional, "DEVELOPMENT_FRONTEND_ORIGINS")
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
