from decimal import Decimal
from io import BytesIO
from pathlib import PurePath
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.catalog import Page, PageSize
from app.api.v1.customer import service_request_data
from app.core.config import get_settings
from app.core.security import current_user
from app.database.session import get_db
from app.models import Category, Listing, Order, PaymentAttempt, ServiceRequest, Store, UploadedImage, VendorOrder
from app.schemas.requests import ListingInput, ServiceRequestUpdate, StoreInput, VendorTransition
from app.services.commerce import approved_store, audit
from app.services.presentation import listing_data, money, paginate, slugify, store_data, vendor_order_data

router = APIRouter(prefix="/vendor")


@router.post("/application", status_code=201)
def application(data: StoreInput, user=Depends(current_user), db: Session = Depends(get_db)):
    if db.scalar(select(Store).where(Store.owner_id == user.id)):
        raise HTTPException(409, "Já existe uma candidatura ou loja nesta conta")
    if data.logo_url and not data.logo_url.startswith("/demo/"):
        raise HTTPException(422, "Adicione o logótipo após a aprovação e carregamento da imagem na sua loja")
    store = Store(owner_id=user.id, slug=f"{slugify(data.name)}-{uuid4().hex[:6]}",
                  is_demo=user.is_demo, **data.model_dump())
    db.add(store)
    if user.role == "customer":
        user.role = "vendor"
    db.flush()
    audit(db, user, "store.applied", store)
    db.commit()
    return store_data(store)


@router.get("/store")
def own_store(user=Depends(current_user), db: Session = Depends(get_db)):
    return store_data(approved_store(db, user, allow_pending=True))


@router.patch("/store")
def update_store(data: StoreInput, user=Depends(current_user), db: Session = Depends(get_db)):
    store = approved_store(db, user)
    validate_images(db, store, [data.logo_url])
    for name, value in data.model_dump().items():
        setattr(store, name, value)
    audit(db, user, "store.updated", store)
    db.commit()
    return store_data(store)


@router.get("/dashboard")
def dashboard(user=Depends(current_user), db: Session = Depends(get_db)):
    store = approved_store(db, user, allow_pending=True)
    count = lambda kind: db.scalar(select(func.count()).select_from(Listing).where(
        Listing.store_id == store.id, Listing.kind == kind, Listing.status == "published"))
    paid = lambda demo: db.scalar(select(func.coalesce(func.sum(VendorOrder.total), 0)).join(Order)
        .where(VendorOrder.store_id == store.id, Order.is_demo == demo,
               Order.status.in_(["paga", "em_preparacao", "pronta", "entregue"])))
    recent = db.scalars(select(VendorOrder).where(VendorOrder.store_id == store.id)
                        .order_by(VendorOrder.created_at.desc()).limit(5)).all()
    low = db.scalars(select(Listing).where(Listing.store_id == store.id, Listing.kind == "product",
                                           Listing.status == "published", Listing.stock <= 5)
                     .order_by(Listing.stock).limit(10)).all()
    return {"store": store_data(store), "active_products": count("product"), "active_services": count("service"),
            "orders_count": db.scalar(select(func.count()).select_from(VendorOrder).where(VendorOrder.store_id == store.id)),
            "low_stock": [listing_data(l) for l in low], "paid_total": money(paid(False)),
            "simulated_paid_total": money(paid(True)), "recent_orders": [vendor_order_data(v) for v in recent]}


def own_listing(db, user, listing_id, kind):
    store = approved_store(db, user)
    listing = db.scalar(select(Listing).where(Listing.id == listing_id, Listing.store_id == store.id,
                                            Listing.kind == kind).with_for_update())
    if not listing:
        raise HTTPException(404, "Anúncio não encontrado")
    return store, listing


def validate_images(db, store, urls):
    for url in urls:
        if url and not url.startswith("/demo/"):
            image = db.scalar(select(UploadedImage).where(UploadedImage.url == url,
                              UploadedImage.store_id == store.id).with_for_update())
            if not image:
                raise HTTPException(422, "A imagem deve pertencer à sua loja")


def validate_listing(db, data, kind):
    category = db.get(Category, data.category_id)
    if not category or not category.active:
        raise HTTPException(422, "Categoria inválida")
    if kind == "product" and (data.price is None or data.stock is None or not data.sku):
        raise HTTPException(422, "Produto exige preço, SKU e stock")
    if kind == "service" and data.stock is not None:
        raise HTTPException(422, "Um serviço não tem stock físico")


def listing_list_endpoint(kind):
    def endpoint(page: Page = 1, page_size: PageSize = 20, user=Depends(current_user), db: Session = Depends(get_db)):
        store = approved_store(db, user)
        return paginate(db, select(Listing).where(Listing.store_id == store.id, Listing.kind == kind,
                        Listing.status != "archived").order_by(Listing.created_at.desc()), listing_data, page, page_size)
    return endpoint


def listing_create_endpoint(kind):
    def endpoint(data: ListingInput, user=Depends(current_user), db: Session = Depends(get_db)):
        store = approved_store(db, user)
        validate_listing(db, data, kind)
        validate_images(db, store, [data.image_url, *data.images])
        listing = Listing(store_id=store.id, kind=kind, is_demo=store.is_demo,
                          slug=f"{slugify(data.name)}-{uuid4().hex[:8]}", **data.model_dump(exclude={"expected_updated_at"}))
        db.add(listing)
        db.flush()
        audit(db, user, "listing.created", listing)
        db.commit()
        return listing_data(listing)
    return endpoint


def listing_update_endpoint(kind):
    def endpoint(listing_id: UUID, data: ListingInput, user=Depends(current_user), db: Session = Depends(get_db)):
        store, listing = own_listing(db, user, listing_id, kind)
        validate_listing(db, data, kind)
        validate_images(db, store, [data.image_url, *data.images])
        if data.expected_updated_at is not None:
            if data.expected_updated_at != listing.updated_at:
                raise HTTPException(409, "O anúncio foi actualizado; recarregue os dados antes de editar")
        elif data.stock != listing.stock:
            raise HTTPException(409, "Para alterar o stock, recarregue o anúncio e envie expected_updated_at")
        for name, value in data.model_dump(exclude={"expected_updated_at"}).items():
            setattr(listing, name, value)
        audit(db, user, "listing.updated", listing)
        db.commit()
        return listing_data(listing)
    return endpoint


def listing_delete_endpoint(kind):
    def endpoint(listing_id: UUID, user=Depends(current_user), db: Session = Depends(get_db)):
        _, listing = own_listing(db, user, listing_id, kind)
        listing.status = "archived"
        audit(db, user, "listing.archived", listing)
        db.commit()
        return {"message": "Anúncio arquivado"}
    return endpoint


for path, kind in [("products", "product"), ("services", "service")]:
    router.add_api_route(f"/{path}", listing_list_endpoint(kind), methods=["GET"])
    router.add_api_route(f"/{path}", listing_create_endpoint(kind), methods=["POST"], status_code=201)
    router.add_api_route(f"/{path}/{{listing_id}}", listing_update_endpoint(kind), methods=["PATCH"])
    router.add_api_route(f"/{path}/{{listing_id}}", listing_delete_endpoint(kind), methods=["DELETE"])


@router.get("/orders")
def vendor_orders(status: str | None = None, page: Page = 1, page_size: PageSize = 20,
                  user=Depends(current_user), db: Session = Depends(get_db)):
    store = approved_store(db, user)
    query = select(VendorOrder).where(VendorOrder.store_id == store.id)
    if status:
        query = query.where(VendorOrder.status == status)
    return paginate(db, query.order_by(VendorOrder.created_at.desc()), vendor_order_data, page, page_size)


@router.patch("/orders/{vendor_order_id}")
def transition(vendor_order_id: UUID, data: VendorTransition, user=Depends(current_user), db: Session = Depends(get_db)):
    store = approved_store(db, user)
    initial = db.scalar(select(VendorOrder).where(VendorOrder.id == vendor_order_id, VendorOrder.store_id == store.id))
    if not initial:
        raise HTTPException(404, "Subencomenda não encontrada")
    order = db.scalar(select(Order).where(Order.id == initial.order_id).with_for_update())
    vendor = db.scalar(select(VendorOrder).where(VendorOrder.id == vendor_order_id).with_for_update()
                       .execution_options(populate_existing=True))
    if order.status in {"pendente_pagamento", "cancelada"}:
        raise HTTPException(409, "A encomenda ainda não está paga ou foi cancelada")
    if data.service_status:
        allowed = {"solicitada": {"confirmada"}, "confirmada": {"concluida"}, "concluida": set()}
        if data.service_status != vendor.service_status and data.service_status not in allowed.get(vendor.service_status, set()):
            raise HTTPException(409, "Transição de serviço inválida")
        vendor.service_status = data.service_status
    if data.status and data.status != vendor.status:
        allowed = {"paga": "em_preparacao", "em_preparacao": "pronta", "pronta": "entregue"}
        if allowed.get(vendor.status) != data.status:
            raise HTTPException(409, "Transição de estado inválida")
        if vendor.service_status == "solicitada":
            raise HTTPException(409, "Confirme primeiro a disponibilidade do serviço")
        if data.status == "entregue" and vendor.service_status and vendor.service_status != "concluida":
            raise HTTPException(409, "Conclua primeiro o serviço")
        vendor.status = data.status
    rank = ["paga", "em_preparacao", "pronta", "entregue"]
    db.flush()
    states = db.scalars(select(VendorOrder.status).where(VendorOrder.order_id == order.id)).all()
    order.status = min(states, key=rank.index)
    audit(db, user, "vendor_order.updated", vendor, {"status": vendor.status, "service_status": vendor.service_status})
    db.commit()
    return vendor_order_data(vendor)


@router.get("/service-requests")
def requests(page: Page = 1, page_size: PageSize = 20, user=Depends(current_user), db: Session = Depends(get_db)):
    store = approved_store(db, user)
    return paginate(db, select(ServiceRequest).where(ServiceRequest.store_id == store.id)
                    .order_by(ServiceRequest.created_at.desc()), service_request_data, page, page_size)


@router.patch("/service-requests/{request_id}")
def update_request(request_id: UUID, data: ServiceRequestUpdate, user=Depends(current_user), db: Session = Depends(get_db)):
    store = approved_store(db, user)
    item = db.scalar(select(ServiceRequest).where(ServiceRequest.id == request_id, ServiceRequest.store_id == store.id).with_for_update())
    if not item:
        raise HTTPException(404, "Solicitação não encontrada")
    allowed = {"requested": {"confirmed", "declined"}, "confirmed": {"completed"}}
    if data.status != item.status and data.status not in allowed.get(item.status, set()):
        raise HTTPException(409, "Transição de solicitação inválida")
    item.status = data.status
    audit(db, user, "service_request.updated", item, {"status": item.status})
    db.commit()
    return service_request_data(item)


@router.post("/uploads", status_code=201)
def upload(file: UploadFile = File(...), user=Depends(current_user), db: Session = Depends(get_db)):
    store = approved_store(db, user)
    settings = get_settings()
    if not settings.blob_read_write_token or not settings.blob_public_base_url:
        raise HTTPException(503, "Configure Vercel Blob para carregar imagens persistentes")
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"} or PurePath(file.filename or "").suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(422, "Apenas imagens JPEG, PNG ou WebP são permitidas")
    content = file.file.read(3 * 1024 * 1024 + 1)
    if len(content) > 3 * 1024 * 1024:
        raise HTTPException(413, "A imagem deve ter no máximo 3 MB")
    try:
        image = Image.open(BytesIO(content))
        if image.format not in {"JPEG", "PNG", "WEBP"} or image.width * image.height > 20000000:
            raise ValueError()
        image.load()
        image = image.convert("RGB")
        image.thumbnail((1600, 1600))
        output = BytesIO()
        image.save(output, format="WEBP", quality=85)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, "Conteúdo de imagem inválido")
    import os
    from vercel.blob.sync import put_blob
    try:
        os.environ["BLOB_READ_WRITE_TOKEN"] = settings.blob_read_write_token
        result = put_blob(f"stores/{store.id}/{uuid4().hex}.webp", output.getvalue(), access="public", content_type="image/webp")
    except Exception:
        raise HTTPException(502, "O armazenamento de imagens não respondeu; tente novamente")
    url = result.url
    image = UploadedImage(store_id=store.id, url=url, pathname=result.pathname)
    db.add(image)
    audit(db, user, "image.uploaded", store, {"path": f"stores/{store.id}"})
    db.commit()
    return {"id": image.id, "url": url}


@router.delete("/uploads/{image_id}")
def delete_upload(image_id: UUID, user=Depends(current_user), db: Session = Depends(get_db)):
    store = approved_store(db, user)
    image = db.scalar(select(UploadedImage).where(UploadedImage.id == image_id, UploadedImage.store_id == store.id).with_for_update())
    if not image:
        raise HTTPException(404, "Imagem não encontrada")
    db.refresh(store)
    references = db.scalars(select(Listing).where(Listing.store_id == store.id)).all()
    if store.logo_url == image.url or any(l.image_url == image.url or image.url in l.images for l in references):
        raise HTTPException(409, "Remova primeiro as referências da loja e dos anúncios, incluindo os arquivados")
    settings = get_settings()
    if not settings.blob_read_write_token:
        raise HTTPException(503, "Configure Vercel Blob para remover imagens")
    import os
    from vercel.blob.sync import delete_blob
    try:
        os.environ["BLOB_READ_WRITE_TOKEN"] = settings.blob_read_write_token
        delete_blob(image.url)
    except Exception:
        raise HTTPException(502, "Não foi possível remover a imagem do armazenamento")
    db.delete(image)
    audit(db, user, "image.deleted", store, {"image_id": str(image_id)})
    db.commit()
    return {"message": "Imagem removida"}
