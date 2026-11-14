from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.api.v1.reports import report_rows, safe_csv
from app.models import Category, Order, OrderItem, VendorOrder
from conftest import login


def make_order(db, sample, reference, created_at, store_key="vendor", listings=None):
    listings = listings or [sample[f"{store_key}_product"]]
    total = sum((item.price for item in listings), Decimal("0.00"))
    order = Order(customer_id=sample["customer"].id, reference=reference,
                  idempotency_key=str(uuid4()), total=total, is_demo=True,
                  delivery_method="pickup", status="paga", created_at=created_at)
    db.add(order)
    db.flush()
    vendor_order = VendorOrder(order_id=order.id, store_id=sample[f"{store_key}_store"].id,
                               total=total, status="paga")
    db.add(vendor_order)
    db.flush()
    for listing in listings:
        db.add(OrderItem(vendor_order_id=vendor_order.id, listing_id=listing.id,
                         name=listing.name, kind=listing.kind, quantity=1,
                         unit_price=listing.price, total=listing.price))
    db.commit()
    return order


def test_report_date_filter_uses_maputo_midnight(db, sample):
    values = [
        ("BEFORE", datetime(2026, 11, 13, 21, 59, 59, tzinfo=timezone.utc)),
        ("MIDNIGHT", datetime(2026, 11, 13, 22, 0, tzinfo=timezone.utc)),
        ("LAST_SECOND", datetime(2026, 11, 14, 21, 59, 59, tzinfo=timezone.utc)),
        ("AFTER", datetime(2026, 11, 14, 22, 0, tzinfo=timezone.utc)),
    ]
    for reference, moment in values:
        make_order(db, sample, reference, moment)
    rows = report_rows(db, sample["admin"], date(2026, 11, 14), date(2026, 11, 14),
                       None, None, True)
    assert {row[0] for row in rows} == {"MIDNIGHT", "LAST_SECOND"}
    assert all(row[3] == "14/11/2026" for row in rows)


def test_vendor_export_cannot_select_another_store(db, client, sample, password):
    moment = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)
    make_order(db, sample, "MY-STORE-ONLY", moment)
    make_order(db, sample, "PRIVATE-OTHER-STORE", moment, store_key="vendor2")
    login(client, sample["vendor"], password)
    response = client.get("/api/v1/reports/orders.csv", params={"store_id": str(sample["vendor2_store"].id)})
    assert response.status_code == 200
    assert "MY-STORE-ONLY" in response.text
    assert "PRIVATE-OTHER-STORE" not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_category_filter_does_not_duplicate_matching_suborders(db, sample):
    moment = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)
    make_order(db, sample, "TWO-MATCHING-ITEMS", moment,
               listings=[sample["vendor_product"], sample["service"]])
    category = Category(name="Outra categoria", slug="outra-categoria")
    db.add(category)
    db.flush()
    sample["vendor2_product"].category_id = category.id
    db.commit()
    make_order(db, sample, "OTHER-CATEGORY", moment, store_key="vendor2")
    rows = report_rows(db, sample["admin"], None, None, None, None, True, sample["category"].id)
    assert len(rows) == 1
    assert rows[0][0] == "TWO-MATCHING-ITEMS"
    assert rows[0][5] == "125.75"


def test_report_rejects_inverted_dates(client, sample, password):
    login(client, sample["admin"], password)
    response = client.get("/api/v1/reports/orders.csv", params={"start": "2026-11-15", "end": "2026-11-14"})
    assert response.status_code == 422


def test_pdf_export_is_authenticated_and_generated(db, client, sample, password):
    make_order(db, sample, "PDF-DEMO", datetime(2026, 11, 14, 12, tzinfo=timezone.utc))
    assert client.get("/api/v1/reports/orders.pdf").status_code == 401
    login(client, sample["admin"], password)
    response = client.get("/api/v1/reports/orders.pdf", params={"is_demo": "true"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "no-store"
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 500


@pytest.mark.parametrize("value", ["=1+1", "+1+1", "-1+1", "@SUM(A1)", "  =1+1", "\t=1+1", "\n=1+1"])
def test_csv_neutralises_formula_cells(value):
    assert safe_csv(value) == "'" + value
