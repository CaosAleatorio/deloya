import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.fixture(autouse=True)
def clear_test_database():
    """Configuration tests require no database; override the integration cleanup fixture."""


def configuration(**changes):
    values = {"database_url": "postgresql+psycopg://example.invalid/deloya?sslmode=require",
              "database_direct_url": None, "jwt_secret": "unit-test-only-secret-" * 3,
              "frontend_origin": "https://marketplace.example.com", "cookie_secure": True,
              "environment": "production"}
    values.update(changes)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize("mode", ["require", "verify-ca", "verify-full"])
def test_production_accepts_only_explicit_tls_modes(mode):
    assert configuration(database_url=f"postgresql://example.invalid/deloya?sslmode={mode}").environment == "production"


@pytest.mark.parametrize("suffix", ["", "?sslmode=disable", "?sslmode=allow", "?sslmode=prefer"])
def test_production_rejects_unencrypted_or_opportunistic_database_connections(suffix):
    with pytest.raises(ValidationError, match="DATABASE_URL deve exigir TLS"):
        configuration(database_url=f"postgresql://example.invalid/deloya{suffix}")


def test_production_validates_direct_database_connection_too():
    with pytest.raises(ValidationError, match="DATABASE_DIRECT_URL deve exigir TLS"):
        configuration(database_direct_url="postgresql://example.invalid/deloya")
    assert configuration(database_direct_url="postgresql://example.invalid/deloya?sslmode=verify-full")


def test_development_allows_local_postgres_without_tls():
    assert configuration(environment="development", cookie_secure=False, frontend_origin="http://localhost:3000",
                         database_url="postgresql+psycopg://localhost/deloya")


def test_postgres_is_required_for_both_connections():
    with pytest.raises(ValidationError, match="DATABASE_URL deve usar PostgreSQL"):
        configuration(database_url="sqlite:///database.sqlite")
    with pytest.raises(ValidationError, match="DATABASE_DIRECT_URL deve usar PostgreSQL"):
        configuration(database_direct_url="sqlite:///database.sqlite")


def test_production_requires_secure_cookies_and_https_origin():
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        configuration(cookie_secure=False)
    with pytest.raises(ValidationError, match="FRONTEND_ORIGIN deve usar HTTPS"):
        configuration(frontend_origin="http://marketplace.example.com")


@pytest.mark.parametrize("origin", ["https://marketplace.example.com/api", "https://marketplace.example.com?x=1", "marketplace.example.com"])
def test_cors_configuration_is_an_exact_origin(origin):
    with pytest.raises(ValidationError, match="FRONTEND_ORIGIN deve ser uma origem"):
        configuration(frontend_origin=origin)
