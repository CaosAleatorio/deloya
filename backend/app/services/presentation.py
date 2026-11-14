import re
import unicodedata
from decimal import Decimal

from sqlalchemy import func, select


def slugify(value: str):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-") or "item"


def money(value):
    return None if value is None else format(Decimal(value), ".2f")


def entity(obj, *fields):
    return {name: getattr(obj, name) for name in ("id", "created_at", *fields)}


def user_data(user):
    return entity(user, "name", "email", "phone", "role", "is_demo")


def store_data(store):
    result = entity(store, "slug", "name", "description", "province", "district", "address", "phone",
                    "nuit", "logo_url", "status", "is_demo")
    result["delivery_fee"] = money(store.delivery_fee)
    return result


def category_data(category):
    return entity(category, "name", "slug", "parent_id", "active")


def listing_data(listing):
    result = entity(listing, "slug", "kind", "name", "description", "stock", "sku", "category_id", "store_id",
                    "image_url", "images", "status", "is_demo", "service_location", "estimated_duration")
    result.update(updated_at=listing.updated_at, price=money(listing.price), store=store_data(listing.store), category=category_data(listing.category))
    return result


def vendor_order_data(order):
    result = entity(order, "order_id", "status", "service_status", "store_id")
    result.update(total=money(order.total), delivery_fee=money(order.delivery_fee), store=store_data(order.store),
                  items=[dict(entity(i, "listing_id", "name", "kind", "quantity"),
                              unit_price=money(i.unit_price), total=money(i.total)) for i in order.items])
    result.update(reference=order.order.reference, is_demo=order.order.is_demo,
                  delivery_method=order.order.delivery_method, address=order.order.address,
                  notes=order.order.notes, requested_date=order.order.requested_date)
    return result


def order_data(order):
    result = entity(order, "reference", "status", "is_demo", "delivery_method", "address", "notes", "requested_date")
    result.update(total=money(order.total), vendor_orders=[vendor_order_data(v) for v in order.vendor_orders])
    return result


def payment_data(payment):
    return dict(entity(payment, "reference", "provider", "status", "is_demo", "order_id"),
                amount=money(payment.amount), demo_notice="PAGAMENTO DE TESTE — SEM MOVIMENTAÇÃO DE DINHEIRO" if payment.is_demo else None)


def paginate(db, query, serializer, page=1, page_size=20):
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    values = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).unique().all()
    return {"items": [serializer(value) for value in values], "total": total, "page": page, "page_size": page_size}
