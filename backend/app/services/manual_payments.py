"""Direct transfers declared by buyers and independently reviewed by sellers.

These records are not provider callbacks or bank verification. No money moves here.
All mutations serialize on the parent order before the suborder/payment.
"""
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Order, PaymentAttempt, Store, User, VendorOrder, utcnow
from app.schemas.requests import ManualPaymentInput, ManualPaymentReview
from app.services.commerce import aggregate_order_status, approved_store, audit


def ensure_manual():
    if get_settings().payment_mode != "manual":
        raise HTTPException(503, "O registo de transferências directas não está activo")


def report_transfer(db: Session, user: User, order_id: UUID, vendor_order_id: UUID, data: ManualPaymentInput):
    ensure_manual()
    # The user lock also serializes reuse of an idempotency key across different orders.
    db.execute(select(User.id).where(User.id == user.id).with_for_update())
    order = db.scalar(select(Order).where(Order.id == order_id, Order.customer_id == user.id)
                      .with_for_update().execution_options(populate_existing=True))
    if not order:
        raise HTTPException(404, "Encomenda não encontrada")
    vendor = db.scalar(select(VendorOrder).where(VendorOrder.id == vendor_order_id,
                       VendorOrder.order_id == order.id).with_for_update().execution_options(populate_existing=True))
    if not vendor:
        raise HTTPException(404, "Subencomenda não encontrada")
    existing = db.scalar(select(PaymentAttempt).where(PaymentAttempt.user_id == user.id,
                          PaymentAttempt.idempotency_key == data.idempotency_key))
    if existing:
        if (existing.vendor_order_id != vendor.id or existing.provider != data.provider
                or existing.transfer_reference != data.reference or existing.notes != data.notes):
            raise HTTPException(409, "A chave de idempotência já foi utilizada com outros dados")
        return existing
    if order.payment_mode != "manual":
        raise HTTPException(409, "Esta encomenda não usa transferências directas")
    if order.status == "cancelada" or vendor.status != "pendente_pagamento":
        raise HTTPException(409, "Esta subencomenda já não aceita declarações de pagamento")
    store = db.scalar(select(Store).where(Store.id == vendor.store_id).with_for_update()
                      .execution_options(populate_existing=True))
    if store.status != "approved":
        raise HTTPException(409, "A loja não está aprovada; contacte o apoio antes de transferir")
    destination = vendor.payment_destinations.get(data.provider)
    if not destination:
        raise HTTPException(422, "Esta carteira não estava configurada quando a encomenda foi criada")
    active = db.scalar(select(PaymentAttempt).where(PaymentAttempt.vendor_order_id == vendor.id,
                       PaymentAttempt.status.in_(["pending", "success"])))
    if active:
        raise HTTPException(409, "Já existe um pagamento a aguardar verificação ou confirmado nesta loja")
    payment = PaymentAttempt(order_id=order.id, vendor_order_id=vendor.id, user_id=user.id,
        reference=f"DLY-PAY-{uuid4().hex.upper()}", idempotency_key=data.idempotency_key,
        provider=data.provider, amount=vendor.total, is_demo=order.is_demo,
        transfer_reference=data.reference, notes=data.notes,
        destination_phone=destination["phone"], destination_account_name=destination["account_name"])
    db.add(payment)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Esta referência já foi comunicada para a mesma carteira ou existe um pagamento activo") from None
    audit(db, user, "payment.manual.reported", payment,
          {"vendor_order_id": str(vendor.id), "provider": payment.provider, "amount": str(payment.amount),
           "is_demo": payment.is_demo, "transfer_reference": payment.transfer_reference})
    db.commit()
    return payment


def review_transfer(db: Session, user: User, vendor_order_id: UUID, payment_id: UUID, data: ManualPaymentReview):
    ensure_manual()
    store = approved_store(db, user, allow_pending=True)
    initial = db.scalar(select(VendorOrder).where(VendorOrder.id == vendor_order_id, VendorOrder.store_id == store.id))
    if not initial:
        raise HTTPException(404, "Subencomenda não encontrada")
    order = db.scalar(select(Order).where(Order.id == initial.order_id).with_for_update()
                      .execution_options(populate_existing=True))
    vendor = db.scalar(select(VendorOrder).where(VendorOrder.id == vendor_order_id).with_for_update()
                       .execution_options(populate_existing=True))
    payment = db.scalar(select(PaymentAttempt).where(PaymentAttempt.id == payment_id,
                        PaymentAttempt.vendor_order_id == vendor.id).with_for_update()
                        .execution_options(populate_existing=True))
    if not payment:
        raise HTTPException(404, "Declaração de pagamento não encontrada")
    store = db.scalar(select(Store).where(Store.id == store.id).with_for_update()
                      .execution_options(populate_existing=True))
    if data.decision == "confirm" and store.status != "approved":
        raise HTTPException(403, "Só uma loja aprovada pode confirmar recebimentos")
    desired = "success" if data.decision == "confirm" else "failure"
    if payment.status != "pending":
        if payment.status == desired:
            return payment  # Replays never alter the reviewer, timestamp, ledger or order.
        raise HTTPException(409, "A decisão deste pagamento já foi registada e não pode ser alterada")
    if order.status == "cancelada" or order.payment_mode != "manual" or vendor.status != "pendente_pagamento":
        raise HTTPException(409, "Esta subencomenda já não aceita confirmação de pagamento")
    payment.status = desired
    payment.reviewed_by = user.id
    payment.reviewed_at = utcnow()
    payment.review_notes = data.notes
    if desired == "success":
        vendor.status = "paga"
        aggregate_order_status(db, order)
    # Rejection leaves the order and reserved inventory intact, allowing correction.
    audit(db, user, f"payment.manual.{data.decision}", payment,
          {"vendor_order_id": str(vendor.id), "wallet_verified": data.wallet_verified,
           "notes": data.notes, "amount": str(payment.amount), "is_demo": payment.is_demo})
    db.commit()
    return payment
