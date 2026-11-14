import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.database.session import get_db, normalize_url
from app.main import app


@pytest.fixture(scope="session")
def test_engine():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Defina TEST_DATABASE_URL para uma base PostgreSQL dedicada com nome terminado em _test")
    parsed = make_url(url)
    if not parsed.database or not parsed.database.endswith("_test") or not parsed.drivername.startswith("postgresql"):
        pytest.fail("TEST_DATABASE_URL deve apontar a PostgreSQL dedicado cujo nome termina em _test")
    engine = create_engine(normalize_url(url), pool_pre_ping=True, connect_args={"connect_timeout": 10})
    # Apply the exact versioned migrations to the isolated database, never create_all.
    previous = os.environ.get("DATABASE_DIRECT_URL")
    os.environ["DATABASE_DIRECT_URL"] = url
    from app.core.config import get_settings
    get_settings.cache_clear()
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    command.upgrade(cfg, "head")
    if previous is None:
        os.environ.pop("DATABASE_DIRECT_URL", None)
    else:
        os.environ["DATABASE_DIRECT_URL"] = previous
    get_settings.cache_clear()
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def clear_test_database(test_engine):
    # The name guard above confines cleanup to a deliberately supplied test database.
    from app.database.session import Base
    with test_engine.begin() as connection:
        names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
        connection.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture
def db(test_engine):
    with sessionmaker(bind=test_engine, expire_on_commit=False)() as session:
        yield session


@pytest.fixture
def client(test_engine):
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    def override():
        with factory() as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise
    app.dependency_overrides[get_db] = override
    with TestClient(app) as value:
        token = value.get("/api/v1/auth/session").json()["csrf_token"]
        value.headers["X-CSRF-Token"] = token
        yield value
    app.dependency_overrides.clear()


@pytest.fixture
def password():
    return "Test-only-strong-password-123!"


@pytest.fixture
def sample(db, password):
    from decimal import Decimal
    from app.core.security import hash_password
    from app.models import Category, Listing, Store, User
    encoded = hash_password(password)
    values = {}
    for key, role in [("customer", "customer"), ("other", "customer"), ("vendor", "vendor"),
                       ("vendor2", "vendor"), ("pending", "vendor"), ("admin", "admin")]:
        user = User(name=key, email=f"{key}@example.com", password_hash=encoded, role=role, is_demo=True)
        db.add(user)
        db.flush()
        values[key] = user
    category = Category(name="Casa", slug="casa")
    db.add(category)
    db.flush()
    values["category"] = category
    for key in ("vendor", "vendor2", "pending"):
        store = Store(owner_id=values[key].id, slug=key, name=key, description="Loja de teste isolado",
                      province="Nampula", district="Nampula", address="Rua de teste", phone="840000000",
                      status="pending" if key == "pending" else "approved", is_demo=True)
        db.add(store)
        db.flush()
        values[f"{key}_store"] = store
        listing = Listing(store_id=store.id, category_id=category.id, slug=f"{key}-produto", kind="product",
                          name=f"Produto {key}", description="Descrição de teste com dados fictícios",
                          price=Decimal("100.25"), stock=5, sku="TEST-1", status="published", is_demo=True)
        db.add(listing)
        db.flush()
        values[f"{key}_product"] = listing
    service = Listing(store_id=values["vendor_store"].id, category_id=category.id, slug="servico", kind="service",
                      name="Serviço de teste", description="Descrição de serviço demonstrativo", price=Decimal("25.50"),
                      stock=None, status="published", is_demo=True)
    db.add(service)
    db.commit()
    values["service"] = service
    return values


def login(client, user, password):
    response = client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    assert response.status_code == 200, response.text
    return response
