from collections import defaultdict
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models import (AuditLog, CartItem, Listing, Order, OrderItem, PaymentAttempt,
                        PaymentConfig, Store, User, VendorOrder)
from app.schemas.requests import OrderInput, PaymentInput
from app.services.presentation import listing_data, money


def audit(db, actor, action, resource, details=None):
    db.add(AuditLog(actor_id=actor.id if actor else None, action=action,
                    resource_type=resource.__tablename__, resource_id=str(resource.id), details=details or {}))


def approved_store(db: Session, user: User, allow_pending=False) -> Store:
    store = db.scalar(select(Store).where(Store.owner_id == user.id))
    if not store:
        raise HTTPException(403, "Submeta primeiro uma candidatura de vendedor")
    if not allow_pending and store.status != "approved":
        raise HTTPException(403, "A loja necessita de aprovação da administração")
    return store


def available(listing: Listing):
    if listing.status != "published" or listing.store.status != "approved":
        raise HTTPException(409, "Este anúncio já não está disponível")
    if listing.price is None:
        raise HTTPException(409, "Serviço sob consulta: envie uma solicitação ao vendedor")


def cart_data(db: Session, user: User):
    items = db.scalars(select(CartItem).where(CartItem.user_id == user.id).order_by(CartItem.created_at)).all()
    total = Decimal("0.00")
    result = []
    for item in items:
        subtotal = (item.listing.price or Decimal("0")) * item.quantity
        total += subtotal
        result.append({"id": item.id, "quantity": item.quantity, "listing": listing_data(item.listing),
                       "unit_price": money(item.listing.price), "subtotal": money(subtotal)})
    return {"items": result, "total": money(total), "is_demo": bool(items) and all(i.listing.is_demo for i in items)}


def create_order(db: Session, user: User, data: OrderInput) -> Order:
    # Serialize checkouts for the same account, then lock inventory in a stable order.
    db.execute(select(User.id).where(User.id == user.id).with_for_update())
    existing = db.scalar(select(Order).where(Order.customer_id == user.id, Order.idempotency_key == data.idempotency_key))
    if existing:
        return existing
    cart = db.scalars(select(CartItem).where(CartItem.user_id == user.id).order_by(CartItem.listing_id).with_for_update()).all()
    if not cart:
        raise HTTPException(400, "O carrinho está vazio")
    listings = db.scalars(select(Listing).where(Listing.id.in_([c.listing_id for c in cart]))
                          .order_by(Listing.id).with_for_update()).all()
    lookup = {l.id: l for l in listings}
    modes = {l.is_demo for l in listings}
    if len(modes) != 1:
        raise HTTPException(409, "Separe anúncios demonstrativos e reais em encomendas diferentes")
    if get_settings().payment_mode == "demo" and not all(l.is_demo for l in listings):
        raise HTTPException(409, "O pagamento simulado só aceita anúncios demonstrativos")
    grouped = defaultdict(list)
    for item in cart:
        listing = lookup[item.listing_id]
        available(listing)
        if listing.kind == "product" and listing.stock < item.quantity:
            raise HTTPException(409, f"Stock insuficiente: {listing.name}")
        if listing.kind == "service" and item.quantity != 1:
            raise HTTPException(422, "Uma solicitação de serviço corresponde a uma unidade")
        grouped[listing.store_id].append((item, listing))
    total = Decimal("0.00")
    fees = {}
    for store_id, rows in grouped.items():
        store = rows[0][1].store
        fee = Decimal("0.00")
        if data.delivery_method == "arranged":
            if store.delivery_fee is None:
                raise HTTPException(409, f"A loja {store.name} ainda não definiu o custo de entrega; escolha levantamento")
            fee = store.delivery_fee
        fees[store_id] = fee
        total += sum((l.price * c.quantity for c, l in rows), Decimal("0.00")) + fee
    if total > Decimal("9999999999.99"):
        raise HTTPException(422, "O montante excede o limite do protótipo")
    order = Order(customer_id=user.id, reference=f"DLY-{uuid4().hex[:12].upper()}",
                  idempotency_key=data.idempotency_key, total=total, is_demo=modes.pop(),
                  delivery_method=data.delivery_method, address=data.address, notes=data.notes,
                  requested_date=data.requested_date)
    db.add(order)
    db.flush()
    for store_id, rows in grouped.items():
        vendor = VendorOrder(order_id=order.id, store_id=store_id,
                             total=sum((l.price * c.quantity for c, l in rows), Decimal("0.00")) + fees[store_id],
                             delivery_fee=fees[store_id],
                             service_status="solicitada" if any(l.kind == "service" for _, l in rows) else None)
        db.add(vendor)
        db.flush()
        for item, listing in rows:
            db.add(OrderItem(vendor_order_id=vendor.id, listing_id=listing.id, name=listing.name,
                             kind=listing.kind, quantity=item.quantity, unit_price=listing.price,
                             total=listing.price * item.quantity))
            if listing.kind == "product":
                listing.stock -= item.quantity
    db.execute(delete(CartItem).where(CartItem.user_id == user.id))
    audit(db, user, "order.created", order, {"is_demo": order.is_demo})
    db.commit()
    db.refresh(order)
    return order


def release_stock(db: Session, order: Order):
    if order.stock_released:
        return
    items = db.scalars(select(OrderItem).join(VendorOrder).where(VendorOrder.order_id == order.id,
                                                               OrderItem.kind == "product")
                       .order_by(OrderItem.listing_id)).all()
    listings = db.scalars(select(Listing).where(Listing.id.in_([i.listing_id for i in items]))
                          .order_by(Listing.id).with_for_update()).all()
    lookup = {l.id: l for l in listings}
    for item in items:
        lookup[item.listing_id].stock += item.quantity
    order.stock_released = True


def cancel_order(db: Session, user: User, order_id: UUID):
    order = db.scalar(select(Order).where(Order.id == order_id, Order.customer_id == user.id).with_for_update())
    if not order:
        raise HTTPException(404, "Encomenda não encontrada")
    if order.status == "cancelada":
        return order
    if order.status != "pendente_pagamento":
        raise HTTPException(409, "Só pode cancelar uma encomenda por pagar; contacte o apoio para outros estados")
    release_stock(db, order)
    order.status = "cancelada"
    for vendor in order.vendor_orders:
        vendor.status = "cancelada"
    for payment in db.scalars(select(PaymentAttempt).where(PaymentAttempt.order_id == order.id,
                                                          PaymentAttempt.status == "pending")):
        payment.status = "expired"
    audit(db, user, "order.cancelled", order)
    db.commit()
    return order


class PaymentService:
    @staticmethod
    def create(db: Session, user: User, data: PaymentInput):
        from app.integrations.payments.providers import DemoPaymentProvider, EMolaProvider, MPesaProvider
        providers = {"demo": DemoPaymentProvider, "mpesa": MPesaProvider, "emola": EMolaProvider}
        providers[data.provider]().ensure_available()
        order = db.scalar(select(Order).where(Order.id == data.order_id, Order.customer_id == user.id).with_for_update())
        if not order:
            raise HTTPException(404, "Encomenda não encontrada")
        existing = db.scalar(select(PaymentAttempt).where(PaymentAttempt.user_id == user.id,
                                                          PaymentAttempt.idempotency_key == data.idempotency_key))
        if existing:
            if existing.order_id != order.id or existing.provider != data.provider:
                raise HTTPException(409, "A chave de idempotência já foi utilizada noutro pagamento")
            return existing
        if order.status != "pendente_pagamento":
            raise HTTPException(409, "Esta encomenda já não aceita pagamentos")
        config = db.get(PaymentConfig, 1)
        if config and not config.demo_enabled:
            raise HTTPException(503, "O modo de demonstração foi desactivado pela administração")
        if not order.is_demo:
            raise HTTPException(409, "Simulação permitida apenas em encomendas demonstrativas")
        pending = db.scalar(select(PaymentAttempt).where(PaymentAttempt.order_id == order.id,
                                                         PaymentAttempt.status == "pending"))
        if pending:
            return pending
        payment = PaymentAttempt(order_id=order.id, user_id=user.id,
                                 reference=f"DEMO-{uuid4().hex.upper()}", idempotency_key=data.idempotency_key,
                                 provider="demo", amount=order.total, is_demo=True)
        db.add(payment)
        db.flush()
        audit(db, user, "payment.demo.started", payment)
        db.commit()
        return payment

    @staticmethod
    def simulate(db: Session, user: User, payment_id: UUID, outcome: str):
        from app.integrations.payments.providers import DemoPaymentProvider
        DemoPaymentProvider().ensure_available()
        initial = db.scalar(select(PaymentAttempt).where(PaymentAttempt.id == payment_id, PaymentAttempt.user_id == user.id))
        if not initial:
            raise HTTPException(404, "Pagamento não encontrado")
        # Lock order before attempt, as in creation and cancellation.
        order = db.scalar(select(Order).where(Order.id == initial.order_id).with_for_update())
        payment = db.scalar(select(PaymentAttempt).where(PaymentAttempt.id == payment_id).with_for_update()
                            .execution_options(populate_existing=True))
        if payment.provider != "demo" or not payment.is_demo or not order.is_demo:
            raise HTTPException(403, "Este pagamento não é uma simulação")
        if payment.status != "pending":
            return payment  # Replayed or out-of-order notifications never change settled state.
        if order.status != "pendente_pagamento":
            raise HTTPException(409, "A encomenda já não aceita confirmação")
        config = db.get(PaymentConfig, 1)
        if config and not config.demo_enabled:
            raise HTTPException(503, "Demonstração desactivada")
        payment.status = outcome
        if outcome == "success":
            order.status = "paga"
            for vendor in order.vendor_orders:
                vendor.status = "paga"
        else:
            release_stock(db, order)
            order.status = "cancelada"
            for vendor in order.vendor_orders:
                vendor.status = "cancelada"
        audit(db, user, f"payment.demo.{outcome}", payment)
        db.commit()
        return payment
