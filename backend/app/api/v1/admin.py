from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.catalog import Page, PageSize
from app.api.v1.customer import support_data
from app.core.config import get_settings
from app.core.security import admin_user
from app.database.session import get_db
from app.models import (AuditLog, Category, Listing, Order, PaymentAttempt, PaymentConfig,
                        Store, SupportTicket, User)
from app.schemas.requests import (CategoryInput, ListingModeration, PaymentConfigInput,
                                  StoreModeration, SupportUpdate)
from app.services.commerce import audit
from app.services.presentation import (category_data, entity, listing_data, money, order_data,
                                       paginate, payment_data, private_store_data, slugify)

router = APIRouter(prefix="/admin", dependencies=[Depends(admin_user)])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    count = lambda model, *conditions: db.scalar(select(func.count()).select_from(model).where(*conditions))
    sums = lambda demo: db.scalar(select(func.coalesce(func.sum(PaymentAttempt.amount), 0)).where(
        PaymentAttempt.status == "success", PaymentAttempt.is_demo == demo))
    states = db.execute(select(PaymentAttempt.status, func.count()).group_by(PaymentAttempt.status)).all()
    states_by_mode = lambda demo: {status: total for status, total in db.execute(
        select(PaymentAttempt.status, func.count()).where(PaymentAttempt.is_demo == demo)
        .group_by(PaymentAttempt.status)).all()}
    def mode_metrics(demo):
        return {"users": count(User, User.is_demo == demo),
                "active_stores": count(Store, Store.status == "approved", Store.is_demo == demo),
                "pending_stores": count(Store, Store.status == "pending", Store.is_demo == demo),
                "orders": count(Order, Order.is_demo == demo),
                "support_open": db.scalar(select(func.count()).select_from(SupportTicket).join(User)
                                           .where(SupportTicket.status == "open", User.is_demo == demo))}
    return {"users": count(User), "active_stores": count(Store, Store.status == "approved"),
            "pending_stores": count(Store, Store.status == "pending"), "orders": count(Order),
            "payments_by_status": {status: total for status, total in states},
            "real_payments_by_status": states_by_mode(False),
            "simulated_payments_by_status": states_by_mode(True),
            "by_mode": {"real": mode_metrics(False), "demo": mode_metrics(True)},
            "paid_total": money(sums(False)), "simulated_paid_total": money(sums(True)),
            "support_open": count(SupportTicket, SupportTicket.status == "open")}


@router.get("/stores")
def stores(status: str | None = None, page: Page = 1, page_size: PageSize = 20, db: Session = Depends(get_db)):
    query = select(Store)
    if status:
        query = query.where(Store.status == status)
    return paginate(db, query.order_by(Store.created_at.desc()), private_store_data, page, page_size)


@router.patch("/stores/{store_id}")
def moderate_store(store_id: UUID, data: StoreModeration, user=Depends(admin_user), db: Session = Depends(get_db)):
    store = db.scalar(select(Store).where(Store.id == store_id).with_for_update())
    if not store:
        raise HTTPException(404, "Loja não encontrada")
    store.status = data.status
    audit(db, user, "store.moderated", store, {"status": data.status, "reason": data.reason})
    db.commit()
    return private_store_data(store)


@router.get("/catalog")
def catalog(kind: str | None = None, status: str | None = None,
            page: Page = 1, page_size: PageSize = 20, db: Session = Depends(get_db)):
    query = select(Listing)
    if kind:
        query = query.where(Listing.kind == kind)
    if status:
        query = query.where(Listing.status == status)
    return paginate(db, query.order_by(Listing.created_at.desc()), listing_data, page, page_size)


@router.patch("/catalog/{listing_id}")
def moderate_listing(listing_id: UUID, data: ListingModeration, user=Depends(admin_user), db: Session = Depends(get_db)):
    listing = db.scalar(select(Listing).where(Listing.id == listing_id).with_for_update())
    if not listing:
        raise HTTPException(404, "Anúncio não encontrado")
    if data.status == "published" and (listing.store.status != "approved" or not listing.category.active):
        raise HTTPException(409, "A loja e a categoria devem estar activas antes da publicação")
    if listing.status == "archived":
        raise HTTPException(409, "Anúncio arquivado pelo vendedor")
    listing.status = data.status
    audit(db, user, "listing.moderated", listing, {"status": data.status, "reason": data.reason})
    db.commit()
    return listing_data(listing)


@router.get("/categories")
def categories(page: Page = 1, page_size: PageSize = 100, db: Session = Depends(get_db)):
    return paginate(db, select(Category).order_by(Category.name), category_data, page, page_size)


def validate_parent(db, parent_id, category_id=None):
    if not parent_id:
        return
    visited = {category_id} if category_id else set()
    item = db.get(Category, parent_id)
    if not item or not item.active:
        raise HTTPException(422, "Categoria superior inválida")
    while item:
        if item.id in visited:
            raise HTTPException(422, "A hierarquia de categorias não pode conter ciclos")
        visited.add(item.id)
        item = db.get(Category, item.parent_id) if item.parent_id else None


@router.post("/categories", status_code=201)
def create_category(data: CategoryInput, user=Depends(admin_user), db: Session = Depends(get_db)):
    validate_parent(db, data.parent_id)
    item = Category(name=data.name, slug=data.slug or slugify(data.name), parent_id=data.parent_id)
    db.add(item)
    db.flush()
    audit(db, user, "category.created", item)
    db.commit()
    return category_data(item)


@router.patch("/categories/{category_id}")
def update_category(category_id: UUID, data: CategoryInput, user=Depends(admin_user), db: Session = Depends(get_db)):
    item = db.get(Category, category_id)
    if not item:
        raise HTTPException(404, "Categoria não encontrada")
    validate_parent(db, data.parent_id, category_id)
    item.name, item.slug, item.parent_id = data.name, data.slug or slugify(data.name), data.parent_id
    audit(db, user, "category.updated", item)
    db.commit()
    return category_data(item)


@router.delete("/categories/{category_id}")
def archive_category(category_id: UUID, user=Depends(admin_user), db: Session = Depends(get_db)):
    item = db.get(Category, category_id)
    if not item:
        raise HTTPException(404, "Categoria não encontrada")
    if db.scalar(select(Category.id).where(Category.parent_id == category_id, Category.active.is_(True)).limit(1)):
        raise HTTPException(409, "Desactive primeiro as subcategorias")
    item.active = False
    audit(db, user, "category.archived", item)
    db.commit()
    return {"message": "Categoria desactivada"}


@router.get("/orders")
def orders(status: str | None = None, is_demo: bool | None = None,
           page: Page = 1, page_size: PageSize = 20, db: Session = Depends(get_db)):
    query = select(Order)
    if status:
        query = query.where(Order.status == status)
    if is_demo is not None:
        query = query.where(Order.is_demo == is_demo)
    return paginate(db, query.order_by(Order.created_at.desc()), order_data, page, page_size)


@router.get("/payments")
def payments(status: str | None = None, is_demo: bool | None = None,
             page: Page = 1, page_size: PageSize = 20, db: Session = Depends(get_db)):
    query = select(PaymentAttempt)
    if status:
        query = query.where(PaymentAttempt.status == status)
    if is_demo is not None:
        query = query.where(PaymentAttempt.is_demo == is_demo)
    return paginate(db, query.order_by(PaymentAttempt.created_at.desc()), payment_data, page, page_size)


@router.get("/payment-config")
def payment_config(db: Session = Depends(get_db)):
    config = db.get(PaymentConfig, 1)
    return {"demo_enabled": (config.demo_enabled if config else True) and get_settings().payment_mode == "demo",
            "mpesa_enabled": False, "emola_enabled": False, "mode": get_settings().payment_mode}


@router.patch("/payment-config")
def update_payment_config(data: PaymentConfigInput, user=Depends(admin_user), db: Session = Depends(get_db)):
    if data.demo_enabled and get_settings().payment_mode != "demo":
        raise HTTPException(409, "O modo de pagamento configurado não permite pagamentos de teste neste ambiente")
    config = db.get(PaymentConfig, 1)
    if not config:
        config = PaymentConfig(id=1)
        db.add(config)
    config.demo_enabled = data.demo_enabled
    audit(db, user, "payment_config.updated", config, {"demo_enabled": data.demo_enabled})
    db.commit()
    return payment_config(db)


@router.get("/audit")
def audit_logs(page: Page = 1, page_size: PageSize = 20, db: Session = Depends(get_db)):
    return paginate(db, select(AuditLog).order_by(AuditLog.created_at.desc()),
                    lambda item: entity(item, "actor_id", "action", "resource_type", "resource_id", "details"), page, page_size)


@router.get("/support")
def support(status: str | None = None, page: Page = 1, page_size: PageSize = 20, db: Session = Depends(get_db)):
    query = select(SupportTicket)
    if status:
        query = query.where(SupportTicket.status == status)
    return paginate(db, query.order_by(SupportTicket.created_at.desc()), support_data, page, page_size)


@router.patch("/support/{ticket_id}")
def resolve_support(ticket_id: UUID, data: SupportUpdate, user=Depends(admin_user), db: Session = Depends(get_db)):
    ticket = db.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(404, "Reclamação não encontrada")
    ticket.status, ticket.response = data.status, data.response
    audit(db, user, "support.updated", ticket, {"status": data.status})
    db.commit()
    return support_data(ticket)
