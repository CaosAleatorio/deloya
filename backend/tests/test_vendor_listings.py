from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.api.v1.vendor import listing_update_endpoint
from app.models import AuditLog, Listing
from app.schemas.requests import ListingInput
from conftest import login


CATALOGUES = [("products", "product", "vendor_product"), ("services", "service", "service")]


def listing_input(sample, kind, **changes):
    values = {"name": "Anúncio de ensaio", "description": "Descrição fictícia para testar o catálogo",
              "category_id": str(sample["category"].id), "status": "pending", "price": "42.50"}
    values.update({"stock": 7, "sku": "CRUD-TEST"} if kind == "product" else
                  {"service_location": "Na loja", "estimated_duration": "2 horas"})
    return {**values, **changes}


@pytest.mark.parametrize("path,kind,sample_key", CATALOGUES)
def test_vendor_creates_lists_edits_and_submits_for_moderation(client, sample, password, path, kind, sample_key):
    login(client, sample["vendor"], password)
    payload = listing_input(sample, kind, status="draft")
    created = client.post(f"/api/v1/vendor/{path}", json=payload)
    assert created.status_code == 201, created.text
    listing = created.json()
    assert listing["kind"] == kind
    assert listing["status"] == "draft"
    assert listing["store_id"] == str(sample["vendor_store"].id)
    assert listing["is_demo"] is True
    assert listing["id"] in {item["id"] for item in client.get(f"/api/v1/vendor/{path}").json()["items"]}
    assert client.get(f"/api/v1/{path}/{listing['slug']}").status_code == 404

    changes = {"name": "Anúncio actualizado", "price": "64.75", "expected_updated_at": listing["updated_at"]}
    changes.update({"stock": 9} if kind == "product" else {"service_location": "Ao domicílio", "estimated_duration": "3 horas"})
    payload.update(changes, status="pending")
    updated = client.patch(f"/api/v1/vendor/{path}/{listing['id']}", json=payload)
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Anúncio actualizado"
    assert updated.json()["price"] == "64.75"
    assert updated.json()["status"] == "pending"
    if kind == "product":
        assert updated.json()["stock"] == 9
    else:
        assert updated.json()["stock"] is None
        assert updated.json()["service_location"] == "Ao domicílio"
        assert updated.json()["estimated_duration"] == "3 horas"

    login(client, sample["admin"], password)
    published = client.patch(f"/api/v1/admin/catalog/{listing['id']}", json={"status": "published"})
    assert published.status_code == 200, published.text
    assert client.get(f"/api/v1/{path}/{listing['slug']}").status_code == 200
    login(client, sample["vendor"], password)
    payload.update(expected_updated_at=published.json()["updated_at"], description="Descrição revista após a publicação do anúncio")
    revised = client.patch(f"/api/v1/vendor/{path}/{listing['id']}", json=payload)
    assert revised.status_code == 200, revised.text
    assert revised.json()["status"] == "pending"
    assert client.get(f"/api/v1/{path}/{listing['slug']}").status_code == 404


@pytest.mark.parametrize("path,kind,sample_key", CATALOGUES)
def test_vendor_cannot_edit_or_remove_another_seller_or_wrong_kind(client, sample, password, path, kind, sample_key):
    own_listing = sample[sample_key]
    login(client, sample["vendor2"], password)
    own_list = client.get(f"/api/v1/vendor/{path}")
    assert own_list.status_code == 200
    assert str(own_listing.id) not in {item["id"] for item in own_list.json()["items"]}
    assert client.patch(f"/api/v1/vendor/{path}/{own_listing.id}", json=listing_input(sample, kind)).status_code == 404
    assert client.delete(f"/api/v1/vendor/{path}/{own_listing.id}").status_code == 404

    login(client, sample["vendor"], password)
    wrong_path = "services" if path == "products" else "products"
    assert client.patch(f"/api/v1/vendor/{wrong_path}/{own_listing.id}", json=listing_input(sample, kind)).status_code == 404
    assert client.delete(f"/api/v1/vendor/{wrong_path}/{own_listing.id}").status_code == 404

    login(client, sample["pending"], password)
    assert client.post(f"/api/v1/vendor/{path}", json=listing_input(sample, kind)).status_code == 403
    assert client.get(f"/api/v1/vendor/{path}").status_code == 403
    login(client, sample["customer"], password)
    assert client.delete(f"/api/v1/vendor/{path}/{own_listing.id}").status_code == 403


@pytest.mark.parametrize("path,kind,sample_key", CATALOGUES)
def test_remove_is_idempotent_preserves_history_and_prevents_new_sales(client, sample, password, db, path, kind, sample_key):
    listing = sample[sample_key]
    login(client, sample["customer"], password)
    assert client.post("/api/v1/cart", json={"listing_id": str(listing.id)}).status_code == 201
    checked_out = client.post("/api/v1/orders", json={"idempotency_key": uuid4().hex})
    assert checked_out.status_code == 201, checked_out.text
    order = checked_out.json()
    historical_item = order["vendor_orders"][0]["items"][0]
    assert client.post("/api/v1/cart", json={"listing_id": str(listing.id)}).status_code == 201
    cart_id = client.get("/api/v1/cart").json()["items"][0]["id"]
    if kind == "service":
        request = client.post("/api/v1/service-requests", json={"listing_id": str(listing.id), "message": "Pedido fictício anterior à eliminação"})
        assert request.status_code == 201, request.text

    login(client, sample["vendor"], password)
    removed = client.delete(f"/api/v1/vendor/{path}/{listing.id}")
    assert removed.status_code == 200, removed.text
    assert "histórico" in removed.json()["message"]
    repeated = client.delete(f"/api/v1/vendor/{path}/{listing.id}")
    assert repeated.status_code == 200
    assert repeated.json() == removed.json()
    assert str(listing.id) not in {item["id"] for item in client.get(f"/api/v1/vendor/{path}").json()["items"]}
    assert str(listing.id) not in {item["id"] for item in client.get(f"/api/v1/{path}").json()["items"]}
    assert client.get(f"/api/v1/{path}/{listing.slug}").status_code == 404
    assert client.patch(f"/api/v1/vendor/{path}/{listing.id}", json=listing_input(sample, kind)).status_code == 409
    db.expire_all()
    assert db.get(Listing, listing.id).status == "archived"
    assert db.scalar(select(func.count()).select_from(AuditLog).where(
        AuditLog.action == "listing.archived", AuditLog.resource_id == str(listing.id))) == 1
    if kind == "service":
        requests = client.get("/api/v1/vendor/service-requests").json()["items"]
        assert any(item["id"] == request.json()["id"] for item in requests)

    login(client, sample["admin"], password)
    assert client.patch(f"/api/v1/admin/catalog/{listing.id}", json={"status": "published"}).status_code == 409
    login(client, sample["customer"], password)
    cart = client.get("/api/v1/cart").json()
    assert len(cart["items"]) == 1
    assert cart["items"][0]["available"] is False
    assert client.post("/api/v1/cart", json={"listing_id": str(listing.id)}).status_code == 409
    assert client.patch(f"/api/v1/cart/{cart_id}", json={"quantity": 1}).status_code == 409
    assert client.post("/api/v1/orders", json={"idempotency_key": uuid4().hex}).status_code == 409
    history = client.get(f"/api/v1/orders/{order['id']}")
    assert history.status_code == 200
    assert history.json()["total"] == order["total"]
    assert history.json()["vendor_orders"][0]["items"][0] == historical_item
    if kind == "service":
        assert client.post("/api/v1/service-requests", json={"listing_id": str(listing.id), "message": "Um novo pedido que deve ser recusado"}).status_code == 404
        assert client.get("/api/v1/service-requests").json()["items"][0]["id"] == request.json()["id"]
    assert client.delete(f"/api/v1/cart/{cart_id}").status_code == 200
    assert client.get("/api/v1/cart").json()["items"] == []


def test_product_sku_conflicts_and_stale_edits_are_rejected(client, sample, password):
    login(client, sample["vendor"], password)
    payload = listing_input(sample, "product", sku=sample["vendor_product"].sku)
    assert client.post("/api/v1/vendor/products", json=payload).status_code == 409
    payload["sku"] = "UNIQUE-CRUD"
    created = client.post("/api/v1/vendor/products", json=payload)
    assert created.status_code == 201, created.text
    listing = created.json()
    path = f"/api/v1/vendor/products/{listing['id']}"
    payload.update(stock=8, expected_updated_at=listing["updated_at"])
    assert client.patch(path, json=payload).status_code == 200
    payload["stock"] = 99
    assert client.patch(path, json=payload).status_code == 409
    persisted = next(item for item in client.get("/api/v1/vendor/products").json()["items"] if item["id"] == listing["id"])
    assert persisted["stock"] == 8


@pytest.mark.parametrize("path,kind,sample_key", CATALOGUES)
def test_vendor_cannot_self_publish_or_change_kind_invariants(client, sample, password, path, kind, sample_key):
    login(client, sample["vendor"], password)
    assert client.post(f"/api/v1/vendor/{path}", json=listing_input(sample, kind, status="published")).status_code == 422
    invalid = listing_input(sample, kind, **({"stock": None} if kind == "product" else {"stock": 1}))
    assert client.post(f"/api/v1/vendor/{path}", json=invalid).status_code == 422


@pytest.mark.parametrize("path,kind,sample_key", CATALOGUES)
def test_preloaded_listing_cannot_revive_an_archived_advert(client, sample, password, db, path, kind, sample_key):
    listing = sample[sample_key]
    assert listing.status == "published"
    login(client, sample["vendor"], password)
    assert client.delete(f"/api/v1/vendor/{path}/{listing.id}").status_code == 200
    # The editor's SQLAlchemy identity map still contains the old published object.
    assert listing.status == "published"
    with pytest.raises(HTTPException) as rejected:
        listing_update_endpoint(kind)(listing.id, ListingInput(**listing_input(sample, kind)), sample["vendor"], db)
    assert rejected.value.status_code == 409
    db.rollback()
    assert db.get(Listing, listing.id).status == "archived"
