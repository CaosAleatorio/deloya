from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier, Event, current_thread
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request, Response
from sqlalchemy import event, func, select, text
from sqlalchemy.orm import sessionmaker

from app.core.security import verify_password
from app.models import (Address, AuditLog, AuthSession, CartItem, Listing, Order, OrderItem,
                        PaymentAttempt, PrivateAttachment, ServiceRequest, Store, SupportTicket, UploadedImage, User,
                        VendorOrder)
from app.api.v1 import auth
from app.schemas.requests import Login, OrderInput, ProfileUpdate
from app.services.accounts import change_password, close_account, update_profile
from app.services.commerce import audit, create_order
from conftest import login


def cookies(client):
    return dict(client.cookies)


def restore_cookies(client, saved):
    client.cookies.clear()
    for name, value in saved.items():
        client.cookies.set(name, value, domain="testserver.local", path="/")
    client.headers["X-CSRF-Token"] = saved["csrf_token"]


def delete_account(client, password, **extra):
    return client.request("DELETE", "/api/v1/me", json={
        "current_password": password, "confirmation": "ELIMINAR", **extra})


def history(db, sample, status="entregue", vendor_status=None):
    order = Order(customer_id=sample["customer"].id, reference=f"HISTORY-{uuid4().hex[:12]}",
                  idempotency_key=uuid4().hex, status=status, total=Decimal("100.25"),
                  is_demo=True, delivery_method="pickup", address="Morada da transacção")
    db.add(order)
    db.flush()
    vendor = VendorOrder(order_id=order.id, store_id=sample["vendor_store"].id,
                         total=order.total, status=vendor_status or status)
    db.add(vendor)
    db.flush()
    item = OrderItem(vendor_order_id=vendor.id, listing_id=sample["vendor_product"].id,
                     name="Artigo histórico", kind="product", quantity=1,
                     unit_price=order.total, total=order.total)
    db.add(item)
    db.commit()
    return order, vendor, item


def test_profile_patch_preserves_omitted_fields_and_rejects_privilege_or_target_changes(client, sample, password, db):
    customer = sample["customer"]
    customer.phone = "841234567"
    db.commit()
    login(client, customer, password)
    original_access = client.cookies.get("access_token")
    response = client.patch("/api/v1/me", json={"name": "Nome actualizado"})
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Nome actualizado"
    assert response.json()["phone"] == "841234567"
    assert client.cookies.get("access_token") == original_access
    for field, value in [("role", "admin"), ("active", False), ("is_demo", False),
                         ("id", str(sample["other"].id))]:
        assert client.patch("/api/v1/me", json={"name": "Ataque", field: value}).status_code == 422
    for payload in ({}, {"name": None}, {"phone": None}, {"email": None}):
        assert client.patch("/api/v1/me", json=payload).status_code == 422
    db.expire_all()
    assert db.get(User, sample["other"].id).name == "other"
    assert db.get(User, customer.id).role == "customer"


def test_email_requires_password_normalizes_unique_email_and_revokes_all_old_sessions(client, sample, password, db):
    customer = sample["customer"]
    login(client, customer, password)
    first = cookies(client)
    login(client, customer, password)
    second = cookies(client)
    original_email = customer.email
    for credential in (None, "wrong-password"):
        payload = {"email": "new@example.com"}
        if credential is not None:
            payload["current_password"] = credential
        response = client.patch("/api/v1/me", json=payload)
        assert response.status_code == 403
        assert "new@example.com" not in response.text
    assert client.patch("/api/v1/me", json={"email": "OTHER@EXAMPLE.COM",
                        "current_password": password}).status_code == 409
    response = client.patch("/api/v1/me", json={"email": "New.Email@Example.Com", "current_password": password})
    assert response.status_code == 200, response.text
    assert response.json()["email"] == "new.email@example.com"
    current = cookies(client)
    assert current["access_token"] not in (first["access_token"], second["access_token"])
    for old in (first, second):
        restore_cookies(client, old)
        assert client.get("/api/v1/me").status_code == 401
        assert client.post("/api/v1/auth/refresh").status_code == 401
    restore_cookies(client, current)
    assert client.get("/api/v1/me").status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": original_email, "password": password}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "NEW.EMAIL@example.com", "password": password}).status_code == 200
    db.expire_all()
    logs = db.scalars(select(AuditLog).where(AuditLog.actor_id == customer.id)).all()
    assert any(log.action == "account.email_changed" for log in logs)
    assert all("new.email@example.com" not in str(log.details) and password not in str(log.details) for log in logs)


def test_password_change_revokes_old_access_and_refresh_and_preserves_secret_whitespace(client, sample, password, db):
    customer = sample["customer"]
    login(client, customer, password)
    first = cookies(client)
    login(client, customer, password)
    second = cookies(client)
    for new_password in ("tiny-pwd", "x" * 129):
        response = client.post("/api/v1/me/password", json={"current_password": password, "new_password": new_password})
        assert response.status_code == 422
        assert new_password not in response.text
    assert client.post("/api/v1/me/password", json={"current_password": "incorrect-password",
                       "new_password": "new-secure-password-2026"}).status_code == 403
    new_password = "  new-secure-password-2026  "
    response = client.post("/api/v1/me/password", json={"current_password": password, "new_password": new_password})
    assert response.status_code == 200, response.text
    assert password not in response.text and new_password not in response.text
    current = cookies(client)
    for old in (first, second):
        restore_cookies(client, old)
        assert client.get("/api/v1/me").status_code == 401
        assert client.post("/api/v1/auth/refresh").status_code == 401
    restore_cookies(client, current)
    assert client.get("/api/v1/me").status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": customer.email, "password": password}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": customer.email, "password": new_password.strip()}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": customer.email, "password": new_password}).status_code == 200
    db.refresh(customer)
    assert verify_password(new_password, customer.password_hash)


@pytest.mark.parametrize("method,path,payload", [
    ("PATCH", "/api/v1/me", {"name": "Actualizado"}),
    ("POST", "/api/v1/me/password", {"current_password": "ignored", "new_password": "new-password-secure"}),
    ("DELETE", "/api/v1/me", {"current_password": "ignored", "confirmation": "ELIMINAR"}),
])
def test_account_writes_require_csrf(client, sample, password, method, path, payload):
    login(client, sample["customer"], password)
    client.headers.pop("X-CSRF-Token")
    assert client.request(method, path, json=payload).status_code == 403


def test_customer_closure_anonymizes_profile_revokes_access_and_retains_history(client, sample, password, db):
    customer = sample["customer"]
    original_email = customer.email
    order, vendor, item = history(db, sample)
    transfer = PaymentAttempt(order_id=order.id, vendor_order_id=vendor.id, user_id=customer.id,
        reference=f"PAY-{uuid4().hex}", idempotency_key=uuid4().hex, provider="mpesa", amount=order.total,
        status="success", is_demo=True, transfer_reference="HISTORY-REF")
    ticket = SupportTicket(user_id=customer.id, order_id=order.id, subject="Histórico de apoio",
                           message="Conservar para acompanhamento", status="closed")
    db.add_all([transfer, ticket,
                Address(user_id=customer.id, label="Casa", address="Rua do perfil"),
                CartItem(user_id=customer.id, listing_id=sample["vendor_product"].id, quantity=1)])
    db.flush()
    attachment = PrivateAttachment(ticket_id=ticket.id, uploaded_by=customer.id,
        pathname=f"support/{uuid4().hex}.pdf", filename="historico.pdf", content_type="application/pdf", size_bytes=32)
    db.add(attachment)
    db.commit()
    login(client, customer, password)
    old = cookies(client)
    assert delete_account(client, password, confirmation="eliminar").status_code == 422
    assert delete_account(client, "wrong-password").status_code == 403
    response = delete_account(client, password)
    assert response.status_code == 200, response.text
    assert response.json()["retained_records"] is True
    assert not client.cookies.get("access_token") and not client.cookies.get("refresh_token")
    db.expire_all()
    closed = db.get(User, customer.id)
    assert not closed.active and closed.name == "Conta eliminada" and closed.phone == ""
    assert closed.email.endswith("@accounts.invalid") and closed.email != original_email
    assert not verify_password(password, closed.password_hash)
    assert not db.scalar(select(Address.id).where(Address.user_id == customer.id))
    assert not db.scalar(select(CartItem.id).where(CartItem.user_id == customer.id))
    assert all(session.revoked for session in db.scalars(select(AuthSession).where(AuthSession.user_id == customer.id)))
    assert db.get(Order, order.id).customer_id == customer.id
    assert db.get(OrderItem, item.id).name == "Artigo histórico"
    assert db.get(PaymentAttempt, transfer.id).status == "success"
    assert db.get(SupportTicket, ticket.id).message == "Conservar para acompanhamento"
    assert db.get(PrivateAttachment, attachment.id).pathname == attachment.pathname
    assert db.scalar(select(AuditLog.id).where(AuditLog.actor_id == customer.id, AuditLog.action == "account.closed"))
    restore_cookies(client, old)
    assert client.get("/api/v1/auth/session").json()["user"] is None
    assert client.get("/api/v1/me").status_code == 401
    assert client.post("/api/v1/auth/refresh").status_code == 401
    assert delete_account(client, password).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": original_email, "password": password}).status_code == 401
    assert db.scalar(select(func.count()).select_from(User).where(User.id == customer.id)) == 1


def test_vendor_closure_archives_store_catalog_preserves_history_and_blocks_reapproval(client, sample, password, db):
    order, vendor_order, item = history(db, sample)
    db.add(CartItem(user_id=sample["other"].id, listing_id=sample["vendor_product"].id, quantity=1))
    db.commit()
    login(client, sample["vendor"], password)
    assert delete_account(client, password).status_code == 200
    db.expire_all()
    assert db.get(Store, sample["vendor_store"].id).status == "suspended"
    assert all(listing.status == "archived" for listing in db.scalars(
        select(Listing).where(Listing.store_id == sample["vendor_store"].id)))
    assert db.get(OrderItem, item.id).listing_id == sample["vendor_product"].id
    assert db.get(VendorOrder, vendor_order.id).store_id == sample["vendor_store"].id
    login(client, sample["other"], password)
    cart = client.get("/api/v1/cart").json()
    assert len(cart["items"]) == 1 and cart["items"][0]["available"] is False
    assert client.get(f"/api/v1/products/{sample['vendor_product'].slug}").status_code == 404
    login(client, sample["admin"], password)
    assert client.patch(f"/api/v1/admin/stores/{sample['vendor_store'].id}",
                        json={"status": "approved"}).status_code == 409


@pytest.mark.parametrize("status", ["pendente_pagamento", "parcialmente_paga", "paga", "em_preparacao", "pronta"])
@pytest.mark.parametrize("account", ["customer", "vendor"])
def test_closure_blocks_nonterminal_buyer_or_store_orders(client, sample, password, db, status, account):
    history(db, sample, status)
    login(client, sample[account], password)
    assert delete_account(client, password).status_code == 409
    db.expire_all()
    assert db.get(User, sample[account].id).active
    assert db.get(Store, sample["vendor_store"].id).status == "approved"
    assert client.get("/api/v1/me").status_code == 200


@pytest.mark.parametrize("account", ["customer", "vendor"])
@pytest.mark.parametrize("obligation", ["pending_transfer", "requested", "confirmed"])
def test_closure_blocks_pending_transfers_and_open_services_even_with_terminal_orders(
        client, sample, password, db, account, obligation):
    order, vendor, _ = history(db, sample, "cancelada")
    if obligation == "pending_transfer":
        db.add(PaymentAttempt(order_id=order.id, vendor_order_id=vendor.id, user_id=sample["customer"].id,
            reference=f"PENDING-{uuid4().hex}", idempotency_key=uuid4().hex, provider="mpesa",
            amount=order.total, status="pending", is_demo=True))
    else:
        db.add(ServiceRequest(user_id=sample["customer"].id, store_id=sample["vendor_store"].id,
            listing_id=sample["service"].id, message="Pedido aberto", status=obligation))
    db.commit()
    login(client, sample[account], password)
    assert delete_account(client, password).status_code == 409
    db.expire_all()
    assert db.get(User, sample[account].id).active


def test_closure_allows_completed_and_declined_service_requests(client, sample, password, db):
    db.add_all([ServiceRequest(user_id=sample["customer"].id, store_id=sample["vendor_store"].id,
        listing_id=sample["service"].id, message="Pedido terminado", status=status)
        for status in ("completed", "declined")])
    db.commit()
    login(client, sample["customer"], password)
    assert delete_account(client, password).status_code == 200


def test_last_active_admin_cannot_close_but_another_active_admin_allows_it(client, sample, password, db):
    other = sample["other"]
    other.role, other.active = "admin", False
    db.commit()
    login(client, sample["admin"], password)
    assert delete_account(client, password).status_code == 409
    other.active = True
    db.commit()
    assert delete_account(client, password).status_code == 200
    db.refresh(other)
    assert other.active


def test_concurrent_admin_closures_leave_one_active_admin(test_engine, sample, password, db):
    sample["other"].role = "admin"
    db.commit()
    barrier = Barrier(2)
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)

    def close(user_id):
        with factory() as session:
            user = session.get(User, user_id)
            barrier.wait(timeout=10)
            try:
                close_account(session, user, password)
                session.commit()
                return 200
            except HTTPException as exc:
                session.rollback()
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(close, [sample["admin"].id, sample["other"].id]))
    assert sorted(outcomes) == [200, 409]
    assert db.scalar(select(func.count()).select_from(User).where(User.role == "admin", User.active.is_(True))) == 1


def test_stale_authenticated_user_cannot_restore_profile_or_checkout_after_closure(test_engine, sample, password, db):
    stale = sample["customer"]
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    with factory() as session:
        close_account(session, session.get(User, stale.id), password)
        session.commit()
    with pytest.raises(HTTPException) as profile_error:
        update_profile(db, stale, ProfileUpdate(name="Perfil ressuscitado"))
    assert profile_error.value.status_code == 401
    db.rollback()
    with pytest.raises(HTTPException) as checkout_error:
        create_order(db, stale, OrderInput(idempotency_key=uuid4().hex))
    assert checkout_error.value.status_code == 401


@pytest.mark.parametrize("account", ["customer", "vendor"])
def test_checkout_racing_closure_cannot_create_obligations_for_a_closed_account(
        test_engine, sample, password, db, account):
    db.add(CartItem(user_id=sample["customer"].id, listing_id=sample["vendor_product"].id, quantity=1))
    db.commit()
    barrier = Barrier(2)
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)

    def operation(close):
        with factory() as session:
            user = session.get(User, sample[account if close else "customer"].id)
            barrier.wait(timeout=10)
            try:
                if close:
                    close_account(session, user, password)
                    session.commit()
                    return 200
                create_order(session, user, OrderInput(idempotency_key=uuid4().hex))
                return 201
            except HTTPException as exc:
                session.rollback()
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        closed, checkout = list(executor.map(operation, [True, False]))
    assert (closed, checkout) in ((409, 201), (200, 401 if account == "customer" else 409))
    db.expire_all()
    is_active = db.get(User, sample[account].id).active
    assert is_active == (closed == 409)
    orders = db.scalar(select(func.count()).select_from(Order))
    assert orders == (1 if checkout == 201 else 0)


@pytest.mark.parametrize("operation", ["refresh", "login"])
def test_inflight_auth_cannot_issue_session_after_password_change(
        test_engine, client, sample, password, db, operation):
    customer = sample["customer"]
    login(client, customer, password)
    refresh_token = client.cookies.get("refresh_token")
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    reached_user_lock = Event()
    new_password = "new-concurrent-password-2026"
    change_password(db, customer, password, new_password)

    def observe_lock(connection, cursor, statement, parameters, context, executemany):
        if current_thread().name.startswith("inflight-auth") and "FROM users" in statement and "FOR NO KEY UPDATE" in statement:
            reached_user_lock.set()

    def authenticate():
        request = Request({"type": "http", "method": "POST", "path": f"/api/v1/auth/{operation}",
                           "headers": [(b"cookie", f"refresh_token={refresh_token}".encode())],
                           "client": ("testclient", 50000)})
        with factory() as session:
            try:
                if operation == "refresh":
                    auth.refresh(request, Response(), db=session)
                else:
                    auth.login(Login(email=customer.email, password=password), request, Response(), db=session)
                return 200
            except HTTPException as exc:
                session.rollback()
                return exc.status_code

    event.listen(test_engine, "before_cursor_execute", observe_lock)
    try:
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="inflight-auth") as executor:
            pending = executor.submit(authenticate)
            reached = reached_user_lock.wait(timeout=10)
            db.commit()
            assert reached, "A autenticação não chegou ao lock da conta"
            assert pending.result(timeout=15) == 401
    finally:
        db.rollback()
        event.remove(test_engine, "before_cursor_execute", observe_lock)
    assert db.scalar(select(func.count()).select_from(AuthSession).where(
        AuthSession.user_id == customer.id, AuthSession.revoked.is_(False))) == 0


def test_closure_waiting_for_upload_allows_audit_user_foreign_key_to_finish(test_engine, sample, password, db):
    """A store FK held by an upload must not deadlock with its audit actor FK."""
    vendor_id = sample["vendor"].id
    store_id = sample["vendor_store"].id
    image = UploadedImage(store_id=store_id, url=f"https://example.com/{uuid4().hex}.webp",
                          pathname=f"stores/{store_id}/{uuid4().hex}.webp")
    db.execute(text("SET LOCAL lock_timeout = '5s'"))
    db.add(image)
    db.flush()  # PostgreSQL holds Store KEY SHARE until this transaction ends.
    image_id = image.id
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    reached_store_lock = Event()

    def observe_lock(connection, cursor, statement, parameters, context, executemany):
        if current_thread().name.startswith("closure-upload") and "FROM stores" in statement and "FOR UPDATE" in statement:
            reached_store_lock.set()

    def close():
        with factory() as session:
            session.execute(text("SET LOCAL lock_timeout = '5s'"))
            close_account(session, session.get(User, vendor_id), password)
            session.commit()
            return True

    event.listen(test_engine, "before_cursor_execute", observe_lock)
    try:
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="closure-upload") as executor:
            pending = executor.submit(close)
            try:
                assert reached_store_lock.wait(timeout=10), "O encerramento não chegou ao lock da loja"
                audit(db, sample["vendor"], "image.uploaded", sample["vendor_store"])
                db.flush()  # Actor User KEY SHARE is compatible with NO KEY UPDATE.
                db.commit()
            finally:
                db.rollback()  # Always release the store before waiting on the worker.
            assert pending.result(timeout=15)
    finally:
        event.remove(test_engine, "before_cursor_execute", observe_lock)
    db.expire_all()
    assert not db.get(User, vendor_id).active
    assert db.get(Store, store_id).status == "suspended"
    assert db.get(UploadedImage, image_id)
    assert db.scalar(select(AuditLog.id).where(AuditLog.actor_id == vendor_id, AuditLog.action == "image.uploaded"))


def test_upload_waits_for_account_closure_before_blob_or_store_writes(test_engine, sample, password, db, monkeypatch):
    """A stale upload cannot reverse User/Store lock order or write after closure."""
    from io import BytesIO
    from types import SimpleNamespace
    from fastapi import UploadFile
    from starlette.datastructures import Headers
    from PIL import Image
    from app.api.v1.vendor import upload
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "blob_read_write_token", "vercel_blob_rw_teststore_test-key")
    monkeypatch.setattr(settings, "blob_public_base_url", "https://teststore.public.blob.vercel-storage.com")
    reached_user_lock, remote_called = Event(), Event()
    vendor_id, store_id = sample["vendor"].id, sample["vendor_store"].id
    output = BytesIO()
    Image.new("RGB", (2, 2), "blue").save(output, format="PNG")

    def fake_put(path, content, **options):
        remote_called.set()
        return SimpleNamespace(pathname=path, url=f"https://teststore.public.blob.vercel-storage.com/{path}")

    monkeypatch.setattr("vercel.blob.sync.put_blob", fake_put)
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)

    def observe_lock(connection, cursor, statement, parameters, context, executemany):
        if current_thread().name.startswith("blocked-upload") and "FROM users" in statement and "FOR NO KEY UPDATE" in statement:
            reached_user_lock.set()

    def send_upload():
        with factory() as session:
            session.execute(text("SET LOCAL lock_timeout = '5s'"))
            stale_user = session.get(User, vendor_id)
            file = UploadFile(file=BytesIO(output.getvalue()), filename="tiny.png", headers=Headers({"content-type": "image/png"}))
            try:
                upload(file=file, user=stale_user, db=session)
                return 201
            except HTTPException as exc:
                session.rollback()
                return exc.status_code
            finally:
                file.file.close()

    close_account(db, sample["vendor"], password)
    event.listen(test_engine, "before_cursor_execute", observe_lock)
    try:
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="blocked-upload") as executor:
            pending = executor.submit(send_upload)
            try:
                assert reached_user_lock.wait(timeout=10), "Upload did not lock the account before business writes"
                assert not remote_called.is_set()
            finally:
                db.commit()  # Release closure locks before waiting for the worker.
            assert pending.result(timeout=15) == 401
    finally:
        event.remove(test_engine, "before_cursor_execute", observe_lock)
    assert not remote_called.is_set()
    assert db.scalar(select(func.count()).select_from(UploadedImage).where(UploadedImage.store_id == store_id)) == 0
