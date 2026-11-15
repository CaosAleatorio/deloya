from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models import AuditLog, Listing, Order, PaymentAttempt, User
from app.schemas.requests import ManualPaymentInput, ManualPaymentReview
from app.services.manual_payments import report_transfer, review_transfer
from app.services.receipts import receipt_content
from conftest import login


@pytest.fixture
def manual(monkeypatch, sample, db):
    monkeypatch.setenv("PAYMENT_MODE", "manual")
    get_settings.cache_clear()
    for key in ("vendor", "vendor2"):
        store = sample[f"{key}_store"]
        store.mpesa_phone = "+258840000001" if key == "vendor" else "+258840000002"
        store.mpesa_account_name = f"Titular {key}"
        store.emola_phone = "+258860000001" if key == "vendor" else "+258860000002"
        store.emola_account_name = f"Titular {key} e-Mola"
    db.commit()
    yield sample
    get_settings.cache_clear()


def buy(client, sample, password, stores=("vendor", "vendor2")):
    login(client, sample["customer"], password)
    for key in stores:
        added = client.post("/api/v1/cart", json={"listing_id": str(sample[f"{key}_product"].id), "quantity": 1})
        assert added.status_code == 201, added.text
    response = client.post("/api/v1/orders", json={"delivery_method": "pickup", "idempotency_key": uuid4().hex})
    assert response.status_code == 201, response.text
    return response.json()


def suborder(order, sample, key="vendor"):
    return next(v for v in order["vendor_orders"] if v["store_id"] == str(sample[f"{key}_store"].id))


def report(client, order, vendor, **changes):
    payload = {"provider": "mpesa", "reference": f"ABC-{uuid4().hex}", "idempotency_key": uuid4().hex, **changes}
    return client.post(f"/api/v1/orders/{order['id']}/vendor-orders/{vendor['id']}/payments", json=payload)


def review(client, vendor, payment, **changes):
    return client.post(f"/api/v1/vendor/orders/{vendor['id']}/payments/{payment['id']}/review",
                       json={"decision": "confirm", "wallet_verified": True, **changes})


def test_wallet_normalization_pairs_and_public_privacy(client, manual, password):
    login(client, manual["vendor"], password)
    own = client.get("/api/v1/vendor/store").json()
    payload = {key: own[key] for key in ("name", "description", "province", "district", "address", "phone",
                                        "nuit", "logo_url", "delivery_fee")}
    payload.update(mpesa_phone="84 123 4567", mpesa_account_name="  Titular indicado  ",
                   emola_phone="258 (86) 123-4567", emola_account_name="Titular e-Mola")
    saved = client.patch("/api/v1/vendor/store", json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()["mpesa_phone"] == "+258841234567"
    assert saved.json()["mpesa_account_name"] == "Titular indicado"
    assert saved.json()["emola_phone"] == "+258861234567"
    for invalid in ({"mpesa_account_name": None}, {"mpesa_phone": "123"}, {"emola_account_name": "X"}):
        assert client.patch("/api/v1/vendor/store", json={**payload, **invalid}).status_code == 422
    public = client.get(f"/api/v1/stores/{manual['vendor_store'].slug}").json()
    assert "mpesa_phone" not in public and "emola_account_name" not in public
    products = client.get("/api/v1/products").json()["items"]
    assert all("mpesa_phone" not in product["store"] for product in products)
    assert "+258841234567" not in str(products)
    login(client, manual["admin"], password)
    assert any(s.get("mpesa_phone") == "+258841234567" for s in client.get("/api/v1/admin/stores").json()["items"])


def test_manual_checkout_requires_wallet_and_snapshots_recipient(client, manual, password, db):
    store = manual["vendor_store"]
    store.mpesa_phone = store.mpesa_account_name = store.emola_phone = store.emola_account_name = None
    db.commit()
    login(client, manual["customer"], password)
    client.post("/api/v1/cart", json={"listing_id": str(manual["vendor_product"].id), "quantity": 1})
    rejected = client.post("/api/v1/orders", json={"idempotency_key": uuid4().hex})
    assert rejected.status_code == 409
    db.refresh(manual["vendor_product"])
    assert manual["vendor_product"].stock == 5
    store.mpesa_phone, store.mpesa_account_name = "+258840000001", "Titular original"
    db.commit()
    response = client.post("/api/v1/orders", json={"idempotency_key": uuid4().hex})
    assert response.status_code == 201, response.text
    order = response.json()
    vendor = order["vendor_orders"][0]
    assert order["payment_mode"] == "manual" and order["can_cancel"] is True
    assert vendor["payment_destinations"] == {"mpesa": {"phone": "+258840000001", "account_name": "Titular original"}}
    store.mpesa_phone, store.mpesa_account_name = "+258849999999", "Outro titular"
    db.commit()
    claimed = report(client, order, vendor).json()
    assert claimed["destination"] == vendor["payment_destinations"]["mpesa"]
    assert report(client, order, vendor, provider="emola").status_code == 422


def test_manual_partial_then_full_payment_and_own_metrics(client, manual, password, db):
    order = buy(client, manual, password)
    first, second = suborder(order, manual), suborder(order, manual, "vendor2")
    claim1, claim2 = report(client, order, first).json(), report(client, order, second, provider="emola").json()
    assert claim1["amount"] == "100.25" and claim2["amount"] == "100.25"
    assert claim1["is_demo"] is True and "SEM MOVIMENTAÇÃO" in claim1["demo_notice"]
    assert client.get(f"/api/v1/orders/{order['id']}").json()["status"] == "pendente_pagamento"
    assert client.post(f"/api/v1/orders/{order['id']}/cancel").status_code == 409
    login(client, manual["vendor"], password)
    confirmed = review(client, first, claim1)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "success"
    assert confirmed.json()["reviewed_by"] == str(manual["vendor"].id)
    timestamp = confirmed.json()["reviewed_at"]
    assert review(client, first, claim1).json()["reviewed_at"] == timestamp
    assert review(client, first, claim1, decision="reject", notes="Não recebido").status_code == 409
    assert client.patch(f"/api/v1/vendor/orders/{first['id']}", json={"status": "em_preparacao"}).status_code == 200
    dashboard = client.get("/api/v1/vendor/dashboard").json()
    assert dashboard["simulated_paid_total"] == "100.25" and dashboard["paid_total"] == "0.00"
    login(client, manual["customer"], password)
    partial = client.get(f"/api/v1/orders/{order['id']}").json()
    assert partial["status"] == "parcialmente_paga" and partial["can_cancel"] is False
    assert client.post(f"/api/v1/orders/{order['id']}/cancel").status_code == 409
    login(client, manual["vendor2"], password)
    assert client.patch(f"/api/v1/vendor/orders/{second['id']}", json={"status": "em_preparacao"}).status_code == 409
    assert review(client, second, claim2).status_code == 200
    login(client, manual["customer"], password)
    assert client.get(f"/api/v1/orders/{order['id']}").json()["status"] == "paga"
    login(client, manual["admin"], password)
    assert client.get("/api/v1/admin/dashboard").json()["simulated_paid_total"] == "200.50"
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "payment.manual.confirm")) == 2


def test_rejection_preserves_stock_allows_resubmit_and_paid_is_immutable(client, manual, password, db):
    order = buy(client, manual, password, stores=("vendor",))
    vendor = order["vendor_orders"][0]
    claim = report(client, order, vendor).json()
    login(client, manual["vendor"], password)
    assert review(client, vendor, claim, wallet_verified=False).status_code == 422
    assert review(client, vendor, claim, decision="reject", notes="").status_code == 422
    rejected = review(client, vendor, claim, decision="reject", wallet_verified=False, notes="Referência não encontrada")
    assert rejected.status_code == 200 and rejected.json()["status"] == "failure"
    assert review(client, vendor, claim).status_code == 409
    db.expire_all()
    assert db.get(Listing, manual["vendor_product"].id).stock == 4
    assert db.get(Order, UUID(order["id"])).stock_released is False
    login(client, manual["customer"], password)
    assert client.get(f"/api/v1/orders/{order['id']}").json()["can_cancel"] is True
    replacement = report(client, order, vendor, reference=claim["transfer_reference"]).json()
    assert replacement["id"] != claim["id"]
    login(client, manual["vendor"], password)
    assert review(client, vendor, replacement).status_code == 200
    login(client, manual["customer"], password)
    assert report(client, order, vendor).status_code == 409


def test_manual_idempotency_and_untrusted_client_amount(client, manual, password):
    order = buy(client, manual, password)
    first, second = suborder(order, manual), suborder(order, manual, "vendor2")
    assert report(client, order, first, amount="0.01").status_code == 422
    assert report(client, order, first, status="success").status_code == 422
    params = {"reference": "abc-123", "idempotency_key": uuid4().hex, "notes": "Enviado pelo cliente"}
    original = report(client, order, first, **params)
    assert original.status_code == 201
    assert original.json()["amount"] == first["total"] and original.json()["transfer_reference"] == "ABC-123"
    assert report(client, order, first, **params).json()["id"] == original.json()["id"]
    assert report(client, order, second, **params).status_code == 409
    assert report(client, order, first, **{**params, "notes": "Alterado"}).status_code == 409
    assert report(client, order, first).status_code == 409


def test_manual_customer_vendor_idor_and_review_not_customer_or_admin(client, manual, password):
    order = buy(client, manual, password)
    first, second = suborder(order, manual), suborder(order, manual, "vendor2")
    claim = report(client, order, first).json()
    for actor in ("other", "vendor", "admin"):
        login(client, manual[actor], password)
        assert client.get(f"/api/v1/orders/{order['id']}").status_code == 404
        assert report(client, order, first).status_code == 404
    for actor in ("customer", "admin", "vendor2", "pending"):
        login(client, manual[actor], password)
        assert review(client, first, claim).status_code in {403, 404}
    login(client, manual["vendor2"], password)
    assert client.get("/api/v1/vendor/payments").json()["items"] == []
    assert "payment_destinations" in client.get("/api/v1/vendor/orders").json()["items"][0]
    login(client, manual["vendor"], password)
    queue = client.get("/api/v1/vendor/payments?status=pending").json()["items"]
    assert len(queue) == 1 and queue[0]["vendor_order_id"] == first["id"]
    assert review(client, second, claim).status_code == 404
    assert client.post(f"/api/v1/payments/{claim['id']}/simulate", json={"outcome": "success"}).status_code == 503


def test_transfer_reference_cannot_pay_twice_for_same_wallet(client, manual, password):
    order1 = buy(client, manual, password, stores=("vendor",))
    assert report(client, order1, order1["vendor_orders"][0], reference="TRANSFER-UNIQUE").status_code == 201
    order2 = buy(client, manual, password, stores=("vendor",))
    assert report(client, order2, order2["vendor_orders"][0], reference="transfer-unique").status_code == 409


def test_disabled_mode_and_external_providers_still_fail_closed(client, manual, password, monkeypatch):
    assert client.get("/api/v1/payment-settings").json() == {"mode": "manual", "demo_enabled": False}
    order = buy(client, manual, password, stores=("vendor",))
    for provider in ("demo", "mpesa", "emola"):
        response = client.post("/api/v1/payments", json={"order_id": order["id"], "provider": provider,
                                                       "idempotency_key": uuid4().hex})
        assert response.status_code == 503
    monkeypatch.setenv("PAYMENT_MODE", "disabled")
    get_settings.cache_clear()
    assert report(client, order, order["vendor_orders"][0]).status_code == 503


def test_suspended_seller_can_reject_pending_but_cannot_confirm(client, manual, password, db):
    order = buy(client, manual, password, stores=("vendor",))
    vendor = order["vendor_orders"][0]
    claim = report(client, order, vendor).json()
    manual["vendor_store"].status = "suspended"
    db.commit()
    login(client, manual["vendor"], password)
    queue = client.get("/api/v1/vendor/payments?status=pending")
    assert queue.status_code == 200 and queue.json()["items"][0]["id"] == claim["id"]
    assert client.get("/api/v1/vendor/store").status_code == 200
    assert review(client, vendor, claim).status_code == 403
    assert review(client, vendor, claim, decision="reject", wallet_verified=False,
                  notes="Loja suspensa: não foi possível validar o recebimento").status_code == 200
    login(client, manual["customer"], password)
    assert client.post(f"/api/v1/orders/{order['id']}/cancel").status_code == 200
    db.expire_all()
    assert db.get(Listing, manual["vendor_product"].id).stock == 5


def test_test_account_cannot_claim_real_order_and_amount_includes_delivery(client, manual, password, db):
    store, listing = manual["vendor_store"], manual["vendor_product"]
    store.is_demo = listing.is_demo = False
    store.delivery_fee = Decimal("19.75")
    db.commit()
    login(client, manual["customer"], password)
    client.post("/api/v1/cart", json={"listing_id": str(listing.id), "quantity": 1})
    denied = client.post("/api/v1/orders", json={"idempotency_key": uuid4().hex})
    assert denied.status_code == 409 and "conta de teste" in denied.json()["detail"]
    db.refresh(listing)
    assert listing.stock == 5
    manual["customer"].is_demo = False
    db.commit()
    created = client.post("/api/v1/orders", json={"idempotency_key": uuid4().hex,
        "delivery_method": "arranged", "address": "Morada de entrega"})
    assert created.status_code == 201, created.text
    order = created.json()
    vendor = order["vendor_orders"][0]
    assert order["total"] == vendor["total"] == "120.00" and vendor["delivery_fee"] == "19.75"
    assert report(client, order, vendor).json()["amount"] == "120.00"


def test_new_manual_accounts_real_totals_and_receipt_wording(client, manual, password, db):
    registered = client.post("/api/v1/auth/register", json={"name": "Cliente real", "email": "real@example.com", "password": password})
    assert registered.status_code == 201 and registered.json()["user"]["is_demo"] is False
    for key in ("customer", "vendor"):
        manual[key].is_demo = False
    manual["vendor_store"].is_demo = False
    manual["vendor_product"].is_demo = False
    db.commit()
    order = buy(client, manual, password, stores=("vendor",))
    vendor = order["vendor_orders"][0]
    claim = report(client, order, vendor).json()
    assert claim["is_demo"] is False and claim["demo_notice"] is None
    login(client, manual["vendor"], password)
    assert review(client, vendor, claim).status_code == 200
    assert client.get("/api/v1/vendor/dashboard").json()["paid_total"] == "100.25"
    login(client, manual["admin"], password)
    assert client.get("/api/v1/admin/dashboard").json()["paid_total"] == "100.25"
    db.expire_all()
    content = receipt_content(db.get(Order, UUID(order["id"])))
    assert "confirmação manual" in content["payment_note"]
    assert "não autenticou" in content["payment_note"]
    assert content["stores"][0]["payments"][0]["reference"] == claim["transfer_reference"]


def test_concurrent_claims_and_review_record_only_one_success(client, manual, password, test_engine, db):
    order = buy(client, manual, password, stores=("vendor",))
    vendor = order["vendor_orders"][0]
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    def submit(_):
        with factory() as session:
            user = session.get(User, manual["customer"].id)
            try:
                item = report_transfer(session, user, UUID(order["id"]), UUID(vendor["id"]),
                    ManualPaymentInput(provider="mpesa", reference="SAME-REFERENCE", idempotency_key="same-concurrent-key"))
                return item.id
            except HTTPException as exc:
                session.rollback()
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(submit, range(2)))
    assert ids[0] == ids[1] and isinstance(ids[0], UUID)
    def confirm(_):
        with factory() as session:
            user = session.get(User, manual["vendor"].id)
            item = review_transfer(session, user, UUID(vendor["id"]), ids[0],
                                   ManualPaymentReview(decision="confirm", wallet_verified=True))
            return item.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(confirm, range(2))) == ["success", "success"]
    assert db.scalar(select(func.count()).select_from(PaymentAttempt).where(PaymentAttempt.status == "success")) == 1
    assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "payment.manual.confirm")) == 1
