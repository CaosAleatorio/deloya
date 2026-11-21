from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.catalog import Page, PageSize
from app.core.security import current_user, rate_limit
from app.core.config import get_settings
from app.database.session import get_db
from app.models import CartItem, Listing, Order, PaymentAttempt, PaymentConfig, ServiceRequest, Store, SupportTicket, User
from app.services.accounts import lock_active_account
from app.schemas.requests import (CartAdd, OrderInput, PaymentInput, Quantity, ServiceRequestInput,
                                  Simulation, SupportInput, ManualPaymentInput)
from app.services.commerce import (PaymentService, audit, available, cancel_order, cart_data,
                                   create_order)
from app.services.presentation import entity, order_data, paginate, payment_data
from app.services.manual_payments import report_transfer

router = APIRouter()


@router.get("/payment-settings")
def payment_settings(db: Session = Depends(get_db)):
    config = db.get(PaymentConfig, 1)
    mode = get_settings().payment_mode
    return {"mode": mode, "demo_enabled": mode == "demo" and (config.demo_enabled if config else True)}


@router.get("/cart")
def cart(user=Depends(current_user), db: Session = Depends(get_db)):
    return cart_data(db, user)


@router.post("/cart", status_code=201)
def add_cart(data: CartAdd, user=Depends(current_user), db: Session = Depends(get_db)):
    user = lock_active_account(db, user)
    listing = db.get(Listing, data.listing_id)
    if not listing:
        raise HTTPException(404, "Anúncio não encontrado")
    available(listing)
    item = db.scalar(select(CartItem).where(CartItem.user_id == user.id, CartItem.listing_id == data.listing_id))
    quantity = data.quantity + (item.quantity if item else 0)
    if quantity > 999 or (listing.kind == "service" and quantity > 1):
        raise HTTPException(422, "Quantidade inválida para este anúncio")
    if listing.kind == "product" and listing.stock < quantity:
        raise HTTPException(409, "Stock insuficiente")
    if item:
        item.quantity = quantity
    else:
        db.add(CartItem(user_id=user.id, listing_id=listing.id, quantity=quantity))
    db.commit()
    return cart_data(db, user)


@router.patch("/cart/{item_id}")
def update_cart(item_id: UUID, data: Quantity, user=Depends(current_user), db: Session = Depends(get_db)):
    user = lock_active_account(db, user)
    item = db.scalar(select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user.id))
    if not item:
        raise HTTPException(404, "Item não encontrado")
    available(item.listing)
    if item.listing.kind == "service" and data.quantity != 1:
        raise HTTPException(422, "Cada solicitação de serviço corresponde a uma unidade")
    if item.listing.kind == "product" and item.listing.stock < data.quantity:
        raise HTTPException(409, "Stock insuficiente")
    item.quantity = data.quantity
    db.commit()
    return cart_data(db, user)


@router.delete("/cart/{item_id}")
def remove_cart(item_id: UUID, user=Depends(current_user), db: Session = Depends(get_db)):
    user = lock_active_account(db, user)
    item = db.scalar(select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user.id))
    if not item:
        raise HTTPException(404, "Item não encontrado")
    db.delete(item)
    db.commit()
    return cart_data(db, user)


@router.get("/orders")
def orders(page: Page = 1, page_size: PageSize = 20, user=Depends(current_user), db: Session = Depends(get_db)):
    return paginate(db, select(Order).where(Order.customer_id == user.id).order_by(Order.created_at.desc()),
                    order_data, page, page_size)


@router.post("/orders", status_code=201)
def checkout(data: OrderInput, request: Request, user=Depends(current_user), db: Session = Depends(get_db)):
    rate_limit(db, request, f"checkout:{user.id}", 30)
    return order_data(create_order(db, user, data))


@router.get("/orders/{order_id}")
def order(order_id: UUID, user=Depends(current_user), db: Session = Depends(get_db)):
    result = db.scalar(select(Order).where(Order.id == order_id, Order.customer_id == user.id))
    if not result:
        raise HTTPException(404, "Encomenda não encontrada")
    return order_data(result)


@router.get("/orders/{order_id}/receipt.pdf")
def order_receipt(order_id: UUID, user=Depends(current_user), db: Session = Depends(get_db)):
    from app.services.receipts import build_order_receipt
    result = db.scalar(select(Order).where(Order.id == order_id, Order.customer_id == user.id))
    if not result:
        raise HTTPException(404, "Encomenda não encontrada")
    return Response(build_order_receipt(result), media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="deloya-encomenda-{result.id}.pdf"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/orders/{order_id}/cancel")
def cancel(order_id: UUID, user=Depends(current_user), db: Session = Depends(get_db)):
    return order_data(cancel_order(db, user, order_id))


@router.get("/payments")
def payments(page: Page = 1, page_size: PageSize = 20, user=Depends(current_user), db: Session = Depends(get_db)):
    return paginate(db, select(PaymentAttempt).where(PaymentAttempt.user_id == user.id)
                    .order_by(PaymentAttempt.created_at.desc()), payment_data, page, page_size)


@router.post("/payments", status_code=201)
def payment(data: PaymentInput, request: Request, user=Depends(current_user), db: Session = Depends(get_db)):
    rate_limit(db, request, f"payment:{user.id}", 30)
    return payment_data(PaymentService.create(db, user, data))


@router.post("/orders/{order_id}/vendor-orders/{vendor_order_id}/payments", status_code=201)
def manual_payment(order_id: UUID, vendor_order_id: UUID, data: ManualPaymentInput, request: Request,
                   user=Depends(current_user), db: Session = Depends(get_db)):
    rate_limit(db, request, f"manual-payment:{user.id}", 30)
    return payment_data(report_transfer(db, user, order_id, vendor_order_id, data))


@router.post("/payments/{payment_id}/simulate")
def simulate(payment_id: UUID, data: Simulation, user=Depends(current_user), db: Session = Depends(get_db)):
    return payment_data(PaymentService.simulate(db, user, payment_id, data.outcome))


@router.post("/payment-webhooks/{provider}")
def webhook(provider: str):
    # No external provider is enabled. A return URL or arbitrary callback cannot mark an order paid.
    raise HTTPException(503, "Callback externo desactivado; não existe integração financeira autorizada")


def support_data(ticket):
    return entity(ticket, "order_id", "subject", "message", "status", "response")


@router.get("/support")
def support(page: Page = 1, page_size: PageSize = 20, user=Depends(current_user), db: Session = Depends(get_db)):
    return paginate(db, select(SupportTicket).where(SupportTicket.user_id == user.id)
                    .order_by(SupportTicket.created_at.desc()), support_data, page, page_size)


@router.post("/support", status_code=201)
def create_support(data: SupportInput, request: Request, user=Depends(current_user), db: Session = Depends(get_db)):
    rate_limit(db, request, f"support:{user.id}", 10)
    if data.order_id and not db.scalar(select(Order.id).where(Order.id == data.order_id, Order.customer_id == user.id)):
        raise HTTPException(404, "Encomenda não encontrada")
    ticket = SupportTicket(user_id=user.id, **data.model_dump())
    db.add(ticket)
    db.commit()
    return support_data(ticket)


def service_request_data(item):
    return dict(entity(item, "listing_id", "store_id", "message", "requested_date", "status"),
                listing_name=item.listing.name)


@router.get("/service-requests")
def service_requests(page: Page = 1, page_size: PageSize = 20, user=Depends(current_user), db: Session = Depends(get_db)):
    return paginate(db, select(ServiceRequest).where(ServiceRequest.user_id == user.id)
                    .order_by(ServiceRequest.created_at.desc()), service_request_data, page, page_size)


@router.post("/service-requests", status_code=201)
def create_service_request(data: ServiceRequestInput, request: Request, user=Depends(current_user), db: Session = Depends(get_db)):
    rate_limit(db, request, f"service_request:{user.id}", 20)
    user = lock_active_account(db, user)
    listing = db.scalar(select(Listing).where(Listing.id == data.listing_id).with_for_update()
                        .execution_options(populate_existing=True))
    if not listing or listing.kind != "service" or listing.status != "published":
        raise HTTPException(404, "Serviço não encontrado")
    store = db.scalar(select(Store).where(Store.id == listing.store_id).with_for_update()
                      .execution_options(populate_existing=True))
    if store.status != "approved":
        raise HTTPException(404, "Serviço não encontrado")
    item = ServiceRequest(user_id=user.id, listing_id=listing.id, store_id=listing.store_id,
                          message=data.message, requested_date=data.requested_date)
    db.add(item)
    db.flush()
    audit(db, user, "service.requested", item)
    db.commit()
    return service_request_data(item)
