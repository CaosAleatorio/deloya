"""Own-account changes preserve transaction history while removing account access."""
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, func, or_, select, text, update
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import (Address, AuthSession, CartItem, Listing, Order, PaymentAttempt,
                        ServiceRequest, Store, User, VendorOrder)
from app.schemas.requests import ProfileUpdate
from app.services.commerce import audit


def lock_active_account(db: Session, user: User) -> User:
    # Re-read after waiting: a request authenticated before closure must not restore data.
    # IDs are immutable: NO KEY UPDATE still serializes account changes, while
    # allowing FK KEY SHARE locks from audit/uploads to finish before closure.
    locked = db.scalar(select(User).where(User.id == user.id).with_for_update(key_share=True, read=False)
                       .execution_options(populate_existing=True))
    if not locked or not locked.active:
        raise HTTPException(401, "Inicie sessão para continuar")
    return locked


def require_password(user: User, password: str | None):
    if not password or not verify_password(password, user.password_hash):
        raise HTTPException(403, "A palavra-passe actual está incorrecta")


def revoke_sessions(db: Session, user: User):
    db.execute(update(AuthSession).where(AuthSession.user_id == user.id).values(revoked=True))


def update_profile(db: Session, user: User, data: ProfileUpdate) -> tuple[User, bool]:
    user = lock_active_account(db, user)
    email = str(data.email).lower() if data.email is not None else user.email
    changed_email = email != user.email
    if changed_email:
        require_password(user, data.current_password)
        if db.scalar(select(User.id).where(func.lower(User.email) == email, User.id != user.id)):
            raise HTTPException(409, "Este email já está registado")
    for field in ("name", "phone"):
        if field in data.model_fields_set:
            setattr(user, field, getattr(data, field))
    if changed_email:
        user.email = email
        revoke_sessions(db, user)
        audit(db, user, "account.email_changed", user)
    else:
        audit(db, user, "account.profile_updated", user,
              {"fields": sorted(data.model_fields_set.intersection({"name", "phone"}))})
    db.flush()
    return user, changed_email


def change_password(db: Session, user: User, current_password: str, new_password: str) -> User:
    user = lock_active_account(db, user)
    require_password(user, current_password)
    user.password_hash = hash_password(new_password)
    revoke_sessions(db, user)
    audit(db, user, "account.password_changed", user)
    db.flush()
    return user


def close_account(db: Session, user: User, current_password: str) -> User:
    # Every administrator closure takes the same guard BEFORE any user row lock.
    # Two remaining administrators therefore cannot both observe the other as active.
    if user.role == "admin":
        db.execute(text("SELECT pg_advisory_xact_lock(731942807)"))
    user = lock_active_account(db, user)
    require_password(user, current_password)
    if user.role == "admin" and not db.scalar(select(User.id).where(
            User.role == "admin", User.active.is_(True), User.id != user.id).limit(1)):
        raise HTTPException(409, "Não pode eliminar a última conta de administração activa")

    # Checkout and service requests lock listings before stores. With these locks held,
    # no new buyer obligation can be created for this seller before it is suspended.
    store_id = db.scalar(select(Store.id).where(Store.owner_id == user.id))
    listings = []
    store = None
    if store_id:
        listings = db.scalars(select(Listing).where(Listing.store_id == store_id)
                              .order_by(Listing.id).with_for_update()
                              .execution_options(populate_existing=True)).all()
        store = db.scalar(select(Store).where(Store.id == store_id).with_for_update()
                          .execution_options(populate_existing=True))

    terminal = ("entregue", "cancelada")
    if db.scalar(select(Order.id).where(Order.customer_id == user.id,
                                      Order.status.not_in(terminal)).limit(1)):
        raise HTTPException(409, "Conclua ou cancele as encomendas pendentes antes de eliminar a conta")
    if store and db.scalar(select(VendorOrder.id).where(VendorOrder.store_id == store.id,
                                                       VendorOrder.status.not_in(terminal)).limit(1)):
        raise HTTPException(409, "A loja tem encomendas por concluir; resolva-as antes de eliminar a conta")
    payment_scope = PaymentAttempt.user_id == user.id
    request_scope = ServiceRequest.user_id == user.id
    if store:
        payment_scope = or_(payment_scope, PaymentAttempt.vendor_order_id.in_(
            select(VendorOrder.id).where(VendorOrder.store_id == store.id)))
        request_scope = or_(request_scope, ServiceRequest.store_id == store.id)
    if db.scalar(select(PaymentAttempt.id).where(payment_scope,
            PaymentAttempt.vendor_order_id.is_not(None), PaymentAttempt.status == "pending").limit(1)):
        raise HTTPException(409, "Existe uma transferência a aguardar verificação; resolva-a antes de eliminar a conta")
    if db.scalar(select(ServiceRequest.id).where(request_scope,
            ServiceRequest.status.not_in(("completed", "declined"))).limit(1)):
        raise HTTPException(409, "Existem solicitações de serviço por concluir; resolva-as antes de eliminar a conta")

    if store:
        store.status = "suspended"
        for listing in listings:
            listing.status = "archived"
    db.execute(delete(Address).where(Address.user_id == user.id))
    db.execute(delete(CartItem).where(CartItem.user_id == user.id))
    revoke_sessions(db, user)
    user.active = False
    user.name = "Conta eliminada"
    user.email = f"deleted-{uuid4().hex}@accounts.invalid"
    user.phone = ""
    user.password_hash = f"!closed:{uuid4().hex}"
    audit(db, user, "account.closed", user, {"retained_records": True})
    db.flush()
    return user
