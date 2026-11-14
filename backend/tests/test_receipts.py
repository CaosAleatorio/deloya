from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.models import Order
from app.services.receipts import build_order_receipt, receipt_content
from conftest import login


def purchase(client, sample, password):
    login(client, sample["customer"], password)
    for key in ("vendor_product", "vendor2_product"):
        added = client.post("/api/v1/cart", json={"listing_id": str(sample[key].id), "quantity": 1})
        assert added.status_code == 201, added.text
    response = client.post("/api/v1/orders", json={"delivery_method": "pickup", "idempotency_key": uuid4().hex})
    assert response.status_code == 201, response.text
    return response.json()


def test_receipt_uses_snapshots_and_keeps_store_groups(db, client, sample, password):
    original_name = sample["vendor_product"].name
    order_data = purchase(client, sample, password)
    sample["vendor_product"].name = "Nome alterado depois da compra"
    sample["vendor_product"].price = Decimal("999.00")
    db.commit()
    order = db.get(Order, UUID(order_data["id"]))
    document = receipt_content(order)
    assert len(document["stores"]) == 2
    assert {store["name"] for store in document["stores"]} == {sample["vendor_store"].name, sample["vendor2_store"].name}
    first = next(store for store in document["stores"] if store["name"] == sample["vendor_store"].name)
    assert first["items"][0]["name"] == original_name
    assert first["items"][0]["unit_price"] == "100.25"
    assert document["total"] == "200.50"
    assert document["title"] == "REGISTO DE TESTE"
    assert "não tem pagamento confirmado" in document["payment_note"]
    assert document["demo_notice"] == "PAGAMENTO DE TESTE — SEM MOVIMENTAÇÃO DE DINHEIRO"
    assert document["warning"] == "NÃO CONSTITUI PROVA DE DINHEIRO RECEBIDO"
    assert build_order_receipt(order).startswith(b"%PDF-")


@pytest.mark.parametrize("actor", ["other", "vendor", "vendor2", "admin"])
def test_receipt_rejects_other_customer_and_vendor_full_order(client, sample, password, actor):
    order = purchase(client, sample, password)
    login(client, sample[actor], password)
    response = client.get(f"/api/v1/orders/{order['id']}/receipt.pdf")
    assert response.status_code == 404


def test_receipt_download_is_private_and_uses_safe_filename(client, sample, password):
    order = purchase(client, sample, password)
    path = f"/api/v1/orders/{order['id']}/receipt.pdf"
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-disposition"] == f'attachment; filename="deloya-encomenda-{order["id"]}.pdf"'
    assert response.content.startswith(b"%PDF-")
    client.cookies.clear()
    assert client.get(path).status_code == 401


def test_successful_simulation_document_still_disclaims_real_money(db, client, sample, password):
    order_data = purchase(client, sample, password)
    started = client.post("/api/v1/payments", json={"order_id": order_data["id"], "provider": "demo",
                                                  "idempotency_key": uuid4().hex})
    assert started.status_code == 201
    confirmed = client.post(f"/api/v1/payments/{started.json()['id']}/simulate", json={"outcome": "success"})
    assert confirmed.status_code == 200
    document = receipt_content(db.get(Order, UUID(order_data["id"])))
    assert document["title"] == "REGISTO DE TESTE"
    assert document["demo_notice"] == "PAGAMENTO DE TESTE — SEM MOVIMENTAÇÃO DE DINHEIRO"
    assert document["warning"] == "NÃO CONSTITUI PROVA DE DINHEIRO RECEBIDO"
    assert "Não houve movimentação de dinheiro" in document["payment_note"]
