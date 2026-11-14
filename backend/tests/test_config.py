import pytest
from fastapi import HTTPException, Request
from pydantic import ValidationError

from app.core.config import Settings
from app.core import security


@pytest.fixture(autouse=True)
def clear_test_database():
    """Configuration tests require no database; override the integration cleanup fixture."""


def configuration(**changes):
    values = {"database_url": "postgresql+psycopg://example.invalid/deloya?sslmode=require",
              "database_direct_url": None, "jwt_secret": "unit-test-only-secret-" * 3,
              "frontend_origin": "https://marketplace.example.com", "cookie_secure": True,
              "development_frontend_origins": [],
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


@pytest.mark.parametrize("origin", ["http://localhost:invalid", "http://localhost:65536", "http://127.0.0.1:-1"])
def test_frontend_origin_rejects_invalid_ports_at_configuration_time(origin):
    with pytest.raises(ValidationError, match="FRONTEND_ORIGIN deve ser uma origem"):
        configuration(environment="development", frontend_origin=origin)


@pytest.mark.parametrize(("configured", "alias"), [
    ("http://localhost:3000", "http://127.0.0.1:3000"),
    ("http://127.0.0.1:3000", "http://localhost:3000"),
    ("https://localhost", "https://127.0.0.1"),
    ("https://127.0.0.1:4443/", "https://localhost:4443"),
])
def test_development_allows_only_the_matching_loopback_alias(configured, alias):
    settings = configuration(environment="development", frontend_origin=configured)
    assert settings.allowed_frontend_origins == [configured.rstrip("/"), alias]


@pytest.mark.parametrize("origin", ["https://marketplace.example.com", "http://localhost.example.com:3000", "http://127.0.0.2:3000"])
def test_development_does_not_expand_other_hosts(origin):
    assert configuration(environment="development", frontend_origin=origin).allowed_frontend_origins == [origin]


@pytest.mark.parametrize("environment", ["test", "production"])
def test_other_environments_allow_only_the_configured_loopback_origin(environment):
    origin = "https://localhost:3000"
    assert configuration(environment=environment, frontend_origin=origin).allowed_frontend_origins == [origin]


def csrf_request(origin, cookie="valid-token", header="valid-token"):
    headers = [(b"origin", origin.encode())]
    if cookie is not None:
        headers.append((b"cookie", f"csrf_token={cookie}".encode()))
    if header is not None:
        headers.append((b"x-csrf-token", header.encode()))
    return Request({"type": "http", "method": "POST", "path": "/api/v1/auth/logout", "headers": headers})


@pytest.mark.parametrize(("configured", "origin"), [
    ("http://localhost:3000", "http://127.0.0.1:3000"),
    ("http://127.0.0.1:3000", "http://localhost:3000"),
])
def test_csrf_accepts_a_development_loopback_alias_with_a_valid_token(monkeypatch, configured, origin):
    settings = configuration(environment="development", frontend_origin=configured)
    monkeypatch.setattr(security, "get_settings", lambda: settings)
    assert security.verify_csrf(csrf_request(origin)) is None


@pytest.mark.parametrize("origin", [
    "http://localhost:3001", "http://127.0.0.1:3001", "https://localhost:3000",
    "https://127.0.0.1:3000", "http://localhost.example.com:3000", "http://127.0.0.2:3000",
    "http://example.com:3000", "http://[::1]:3000",
])
def test_csrf_rejects_other_ports_schemes_and_hosts_in_development(monkeypatch, origin):
    settings = configuration(environment="development", frontend_origin="http://localhost:3000")
    monkeypatch.setattr(security, "get_settings", lambda: settings)
    with pytest.raises(HTTPException, match="Origem não autorizada") as error:
        security.verify_csrf(csrf_request(origin))
    assert error.value.status_code == 403


@pytest.mark.parametrize("environment", ["test", "production"])
def test_csrf_rejects_loopback_aliases_outside_development(monkeypatch, environment):
    settings = configuration(environment=environment, frontend_origin="https://localhost:3000")
    monkeypatch.setattr(security, "get_settings", lambda: settings)
    with pytest.raises(HTTPException, match="Origem não autorizada") as error:
        security.verify_csrf(csrf_request("https://127.0.0.1:3000"))
    assert error.value.status_code == 403


@pytest.mark.parametrize(("cookie", "header"), [(None, "valid-token"), ("valid-token", None), ("valid-token", "wrong-token")])
def test_development_loopback_alias_still_requires_a_valid_csrf_token(monkeypatch, cookie, header):
    settings = configuration(environment="development", frontend_origin="http://localhost:3000")
    monkeypatch.setattr(security, "get_settings", lambda: settings)
    with pytest.raises(HTTPException, match="Token CSRF inválido") as error:
        security.verify_csrf(csrf_request("http://127.0.0.1:3000", cookie, header))
    assert error.value.status_code == 403


def test_development_origins_are_loaded_from_a_json_environment_array(monkeypatch):
    monkeypatch.setenv("DEVELOPMENT_FRONTEND_ORIGINS", '["http://192.168.240.1:3000"]')
    values = configuration(environment="development").model_dump(exclude={"development_frontend_origins"})
    settings = Settings(_env_file=None, **values)
    assert settings.development_frontend_origins == ["http://192.168.240.1:3000"]
    assert "http://192.168.240.1:3000" in settings.allowed_frontend_origins


@pytest.mark.parametrize("origin", [
    "*", "http://*:3000", "https://*.example.com", "http://user:password@192.168.240.1:3000",
    "http://@192.168.240.1:3000", "http://192.168.240.1:3000/login",
    "http://192.168.240.1:3000?x=1", "http://192.168.240.1:3000#fragment",
    "http://192.168.240.1:3000?", "http://192.168.240.1:3000#", "192.168.240.1:3000",
    "http://192.168.240.1:invalid", "http://192.168.240.1:65536", "http://192.168.240.1:",
    "http://host with spaces:3000", "http://192.168.240.1\\example.com:3000",
])
def test_development_origins_reject_non_origins_and_wildcards(origin):
    with pytest.raises(ValidationError, match="DEVELOPMENT_FRONTEND_ORIGINS deve ser uma origem"):
        configuration(environment="development", development_frontend_origins=[origin])


def test_explicit_development_origins_share_the_exact_csrf_allowlist(monkeypatch):
    settings = configuration(environment="development", frontend_origin="http://localhost:3000",
                             development_frontend_origins=["http://192.168.240.1:3000/", "http://localhost:3000"])
    assert settings.allowed_frontend_origins == [
        "http://localhost:3000", "http://127.0.0.1:3000", "http://192.168.240.1:3000"]
    monkeypatch.setattr(security, "get_settings", lambda: settings)
    assert security.verify_csrf(csrf_request("http://192.168.240.1:3000")) is None
    with pytest.raises(HTTPException, match="Origem não autorizada") as error:
        security.verify_csrf(csrf_request("http://192.168.240.2:3000"))
    assert error.value.status_code == 403


@pytest.mark.parametrize("environment", ["test", "production"])
def test_development_origins_are_never_authorized_in_other_environments(monkeypatch, environment):
    settings = configuration(environment=environment,
                             development_frontend_origins=["http://192.168.240.1:3000"])
    assert settings.allowed_frontend_origins == [settings.frontend_origin]
    monkeypatch.setattr(security, "get_settings", lambda: settings)
    with pytest.raises(HTTPException, match="Origem não autorizada") as error:
        security.verify_csrf(csrf_request("http://192.168.240.1:3000"))
    assert error.value.status_code == 403


@pytest.mark.parametrize(("cookie", "header"), [(None, "valid-token"), ("valid-token", None), ("valid-token", "wrong-token")])
def test_explicit_development_origins_still_require_a_valid_csrf_token(monkeypatch, cookie, header):
    settings = configuration(environment="development", development_frontend_origins=["http://192.168.240.1:3000"])
    monkeypatch.setattr(security, "get_settings", lambda: settings)
    with pytest.raises(HTTPException, match="Token CSRF inválido") as error:
        security.verify_csrf(csrf_request("http://192.168.240.1:3000", cookie, header))
    assert error.value.status_code == 403
