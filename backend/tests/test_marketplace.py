from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import jwt
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models import (AuditLog, AuthSession, CartItem, Listing, Order, PaymentAttempt, User, VendorOrder, utcnow)
from app.schemas.requests import OrderInput
from app.services.commerce import PaymentService, create_order
from conftest import login


def add(client, listing, quantity=1):
    response = client.post("/api/v1/cart", json={"listing_id": str(listing.id), "quantity": quantity})
    assert response.status_code == 201, response.text
    return response.json()


def checkout(client, key=None, **extra):
    response = client.post("/api/v1/orders", json={"delivery_method": "pickup", "idempotency_key": key or uuid4().hex, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def payment(client, order, outcome):
    response = client.post("/api/v1/payments", json={"order_id": order["id"], "provider": "demo", "idempotency_key": uuid4().hex})
    assert response.status_code == 201, response.text
    result = response.json()
    simulated = client.post(f"/api/v1/payments/{result['id']}/simulate", json={"outcome": outcome})
    assert simulated.status_code == 200, simulated.text
    return result, simulated.json()


def test_register_login_logout_and_cookie_flags(client, password):
    data = {"name": "Cliente de teste", "email": "novo@example.com", "password": password}
    response = client.post("/api/v1/auth/register", json=data)
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "customer"
    assert response.json()["user"]["is_demo"] is True
    assert any("HttpOnly" in cookie for cookie in response.headers.get_list("set-cookie") if cookie.startswith("access_token="))
    assert client.get("/api/v1/me").status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/me").status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": data["email"], "password": password}).status_code == 200
    assert client.post("/api/v1/auth/register", json={**data, "role": "admin"}).status_code == 422


def test_csrf_and_origin_enforced(client, password):
    payload = {"name": "Cliente de teste", "email": "novo@example.com", "password": password}
    token = client.headers.pop("X-CSRF-Token")
    assert client.post("/api/v1/auth/register", json=payload).status_code == 403
    client.headers["X-CSRF-Token"] = token
    assert client.post("/api/v1/auth/register", json=payload, headers={"Origin": "https://evil.example"}).status_code == 403


def test_invalid_expired_tokens_and_refresh_replay(client, sample, password, db):
    login(client, sample["customer"], password)
    old_refresh = client.cookies.get("refresh_token")
    assert client.post("/api/v1/auth/refresh").status_code == 200
    new_refresh = client.cookies.get("refresh_token")
    assert new_refresh != old_refresh
    assert client.get("/api/v1/me").status_code == 200
    client.cookies.set("refresh_token", old_refresh, domain="testserver.local", path="/")
    assert client.post("/api/v1/auth/refresh").status_code == 401
    assert client.get("/api/v1/me").status_code == 401
    client.cookies.clear()
    client.cookies.set("access_token", "invalid.token", domain="testserver.local", path="/")
    assert client.get("/api/v1/me").status_code == 401
    expired = jwt.encode({"sub": str(sample["customer"].id), "sid": str(uuid4()), "iat": utcnow() - timedelta(hours=2),
                          "exp": utcnow() - timedelta(hours=1), "iss": "deloya", "aud": "deloya-web"},
                         get_settings().jwt_secret, algorithm="HS256")
    client.cookies.set("access_token", expired, domain="testserver.local", path="/")
    assert client.get("/api/v1/me").status_code == 401


def test_pending_vendor_cannot_publish_and_catalog_hides_store(client, sample, password):
    login(client, sample["pending"], password)
    payload = {"name": "Novo produto", "description": "Descrição longa do produto", "price": "30.00", "stock": 1,
               "sku": "P-2", "category_id": str(sample["category"].id)}
    assert client.post("/api/v1/vendor/products", json=payload).status_code == 403
    assert client.get("/api/v1/vendor/products").status_code == 403
    public = client.get("/api/v1/products").json()
    assert all(item["store_id"] != str(sample["pending_store"].id) for item in public["items"])


def test_vendor_and_customer_idor(client, sample, password):
    login(client, sample["customer"], password)
    add(client, sample["vendor_product"])
    add(client, sample["vendor2_product"])
    order = checkout(client)
    vendor2_suborder = next(o for o in order["vendor_orders"] if o["store_id"] == str(sample["vendor2_store"].id))
    login(client, sample["other"], password)
    assert client.get(f"/api/v1/orders/{order['id']}").status_code == 404
    assert client.post(f"/api/v1/orders/{order['id']}/cancel").status_code == 404
    login(client, sample["vendor"], password)
    assert client.delete(f"/api/v1/vendor/products/{sample['vendor2_product'].id}").status_code == 404
    assert client.patch(f"/api/v1/vendor/orders/{vendor2_suborder['id']}", json={"status": "em_preparacao"}).status_code == 404
    vendor_items = client.get("/api/v1/vendor/orders").json()["items"]
    assert len(vendor_items) == 1
    assert all(i["store_id"] == str(sample["vendor_store"].id) for i in vendor_items)


def test_server_totals_snapshots_and_multi_store(client, sample, password, db):
    login(client, sample["customer"], password)
    add(client, sample["vendor_product"], 2)
    add(client, sample["vendor2_product"], 1)
    assert client.post("/api/v1/orders", json={"delivery_method": "pickup", "idempotency_key": uuid4().hex, "total": "0.01"}).status_code == 422
    order = checkout(client, key="same-order-idempotency")
    assert order["total"] == "300.75"
    assert len(order["vendor_orders"]) == 2
    assert sum(Decimal(v["total"]) for v in order["vendor_orders"]) == Decimal(order["total"])
    assert checkout(client, key="same-order-idempotency")["id"] == order["id"]
    db.expire_all()
    assert db.get(Listing, sample["vendor_product"].id).stock == 3
    product = db.get(Listing, sample["vendor_product"].id)
    product.price = Decimal("999.99")
    db.commit()
    unchanged = client.get(f"/api/v1/orders/{order['id']}").json()
    assert unchanged["total"] == "300.75"
    assert unchanged["vendor_orders"][0]["items"][0]["unit_price"] == "100.25"


def test_failed_payment_and_cancel_restore_stock_once(client, sample, password, db):
    login(client, sample["customer"], password)
    add(client, sample["vendor_product"], 2)
    order = checkout(client)
    attempt, result = payment(client, order, "failure")
    assert result["status"] == "failure"
    assert client.get(f"/api/v1/orders/{order['id']}").json()["status"] == "cancelada"
    for outcome in ["failure", "success", "expired"]:
        repeated = client.post(f"/api/v1/payments/{attempt['id']}/simulate", json={"outcome": outcome})
        assert repeated.status_code == 200
        assert repeated.json()["status"] == "failure"
    assert client.post(f"/api/v1/orders/{order['id']}/cancel").status_code == 200
    db.expire_all()
    assert db.get(Listing, sample["vendor_product"].id).stock == 5


def test_demo_success_replays_real_providers_fail_closed(client, sample, password, db):
    login(client, sample["customer"], password)
    add(client, sample["vendor_product"])
    order = checkout(client)
    for provider in ["mpesa", "emola"]:
        assert client.post("/api/v1/payments", json={"order_id": order["id"], "provider": provider,
                           "idempotency_key": uuid4().hex}).status_code == 503
        assert client.post(f"/api/v1/payment-webhooks/{provider}", json={"status": "success"}).status_code == 503
    attempt, result = payment(client, order, "success")
    assert result["demo_notice"] == "PAGAMENTO SIMULADO — SEM TRANSACÇÃO REAL"
    assert result["amount"] == "100.25"
    assert client.get(f"/api/v1/orders/{order['id']}").json()["status"] == "paga"
    assert client.post(f"/api/v1/payments/{attempt['id']}/simulate", json={"outcome": "failure"}).json()["status"] == "success"
    assert client.post(f"/api/v1/orders/{order['id']}/cancel").status_code == 409
    db.expire_all()
    assert db.get(Listing, sample["vendor_product"].id).stock == 4
    assert db.scalar(select(func.count()).select_from(PaymentAttempt)) == 1


def test_expiry_and_unknown_delivery_fee(client, sample, password, db):
    login(client, sample["customer"], password)
    add(client, sample["vendor_product"])
    response = client.post("/api/v1/orders", json={"delivery_method": "arranged", "address": "Rua de teste 20",
                           "idempotency_key": uuid4().hex})
    assert response.status_code == 409
    order = checkout(client)
    payment(client, order, "expired")
    db.expire_all()
    assert db.get(Listing, sample["vendor_product"].id).stock == 5


def test_concurrent_stock_never_oversells(test_engine, sample, db):
    product = sample["vendor_product"]
    product.stock = 1
    db.add_all([CartItem(user_id=sample[key].id, listing_id=product.id, quantity=1) for key in ["customer", "other"]])
    db.commit()
    barrier = Barrier(2)
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    ids = [sample["customer"].id, sample["other"].id]
    def attempt(user_id):
        with factory() as session:
            user = session.get(User, user_id)
            barrier.wait(timeout=10)
            try:
                create_order(session, user, OrderInput(idempotency_key=uuid4().hex))
                return 201
            except HTTPException as exc:
                session.rollback()
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(attempt, ids))
    assert sorted(outcomes) == [201, 409]
    db.expire_all()
    assert db.get(Listing, product.id).stock == 0
    assert db.scalar(select(func.count()).select_from(Order)) == 1


def test_vendor_stock_edit_detects_stale_form(client, sample, password, db):
    login(client, sample["vendor"], password)
    listing = client.get("/api/v1/vendor/products").json()["items"][0]
    db.expire_all()
    product = db.get(Listing, sample["vendor_product"].id)
    product.stock = 4
    db.commit()
    payload = {key: listing[key] for key in ["name", "description", "price", "stock", "sku", "category_id"]}
    payload["expected_updated_at"] = listing["updated_at"]
    assert client.patch(f"/api/v1/vendor/products/{listing['id']}", json=payload).status_code == 409
    db.refresh(product)
    assert product.stock == 4


def test_service_has_no_stock_and_requires_confirmation(client, sample, password):
    login(client, sample["customer"], password)
    assert sample["service"].stock is None
    add(client, sample["service"])
    order = checkout(client)
    payment(client, order, "success")
    vendor = order["vendor_orders"][0]
    login(client, sample["vendor"], password)
    assert client.patch(f"/api/v1/vendor/orders/{vendor['id']}", json={"status": "em_preparacao"}).status_code == 409
    response = client.patch(f"/api/v1/vendor/orders/{vendor['id']}", json={"service_status": "confirmada", "status": "em_preparacao"})
    assert response.status_code == 200
    assert response.json()["service_status"] == "confirmada"


def test_dashboards_separate_simulated_and_real(client, sample, password):
    login(client, sample["customer"], password)
    add(client, sample["vendor_product"])
    payment(client, checkout(client), "success")
    login(client, sample["vendor"], password)
    metrics = client.get("/api/v1/vendor/dashboard").json()
    assert metrics["paid_total"] == "0.00"
    assert metrics["simulated_paid_total"] == "100.25"
    login(client, sample["admin"], password)
    metrics = client.get("/api/v1/admin/dashboard").json()
    assert metrics["paid_total"] == "0.00"
    assert metrics["simulated_paid_total"] == "100.25"
    assert metrics["simulated_payments_by_status"] == {"success": 1}
    assert metrics["real_payments_by_status"] == {}


def test_auth_rate_limit_persisted(client, sample):
    codes = [client.post("/api/v1/auth/login", json={"email": sample["customer"].email, "password": "incorrect"}).status_code for _ in range(16)]
    assert codes[:15] == [401] * 15
    assert codes[-1] == 429


def test_concurrent_duplicate_payment_settles_once(client, sample, password, db, test_engine):
    login(client, sample["customer"], password)
    add(client, sample["vendor_product"])
    order = checkout(client)
    response = client.post("/api/v1/payments", json={"order_id": order["id"], "provider": "demo", "idempotency_key": uuid4().hex})
    assert response.status_code == 201
    from uuid import UUID
    payment_id = UUID(response.json()["id"])
    user_id = sample["customer"].id
    barrier = Barrier(2)
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    def notify(_):
        with factory() as session:
            user = session.get(User, user_id)
            # Preload both attempts to reproduce identity-map staleness across the order lock.
            session.get(PaymentAttempt, payment_id)
            barrier.wait(timeout=10)
            return PaymentService.simulate(session, user, payment_id, "success").status
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(notify, [0, 1]))
    assert outcomes == ["success", "success"]
    db.expire_all()
    assert db.get(Listing, sample["vendor_product"].id).stock == 4
    assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "payment.demo.success")) == 1


def test_admin_approval_moderation_and_payment_configuration(client, sample, password):
    login(client, sample["pending"], password)
    assert client.get("/api/v1/admin/dashboard").status_code == 403
    login(client, sample["admin"], password)
    approved = client.patch(f"/api/v1/admin/stores/{sample['pending_store'].id}", json={"status": "approved"})
    assert approved.status_code == 200
    login(client, sample["pending"], password)
    payload = {"name": "Novo produto", "description": "Descrição longa do produto", "price": "30.00", "stock": 1,
               "sku": "P-2", "category_id": str(sample["category"].id)}
    product = client.post("/api/v1/vendor/products", json=payload)
    assert product.status_code == 201
    assert product.json()["status"] == "pending"
    assert client.get(f"/api/v1/products/{product.json()['slug']}").status_code == 404
    login(client, sample["admin"], password)
    assert client.patch(f"/api/v1/admin/catalog/{product.json()['id']}", json={"status": "published"}).status_code == 200
    assert client.get(f"/api/v1/products/{product.json()['slug']}").status_code == 200
    config = client.patch("/api/v1/admin/payment-config", json={"demo_enabled": False})
    assert config.status_code == 200
    assert config.json()["demo_enabled"] is False
    assert client.patch("/api/v1/admin/payment-config", json={"demo_enabled": True, "mpesa_enabled": True}).status_code == 422
    assert client.get("/api/v1/admin/audit").json()["total"] >= 3
