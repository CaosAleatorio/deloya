from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Category, Listing, Store
from app.services.presentation import category_data, listing_data, paginate, store_data

router = APIRouter()
Page = Annotated[int, Query(ge=1, le=100000)]
PageSize = Annotated[int, Query(ge=1, le=100)]


def catalog_query(kind, q=None, category=None, store=None, province=None, min_price=None, max_price=None,
                  sort="recent"):
    query = select(Listing).join(Store).join(Category).where(Listing.kind == kind,
        Listing.status == "published", Store.status == "approved", Category.active.is_(True))
    if q:
        term = q.replace("%", r"\%").replace("_", r"\_")
        query = query.where(or_(Listing.name.ilike(f"%{term}%"), Listing.description.ilike(f"%{term}%")))
    if category:
        query = query.where(or_(Category.slug == category, Category.id.cast(__import__("sqlalchemy").String) == category))
    if store:
        query = query.where(or_(Store.slug == store, Store.id.cast(__import__("sqlalchemy").String) == store))
    if province:
        query = query.where(Store.province.ilike(province))
    if min_price is not None:
        query = query.where(Listing.price >= min_price)
    if max_price is not None:
        query = query.where(Listing.price <= max_price)
    return query.order_by(Listing.price.asc().nulls_last() if sort == "price_asc" else
                          Listing.price.desc().nulls_last() if sort == "price_desc" else Listing.created_at.desc())


def catalog_endpoint(kind):
    def endpoint(q: str | None = Query(default=None, max_length=120),
                 category: str | None = Query(default=None, max_length=120),
                 store: str | None = Query(default=None, max_length=180),
                 province: str | None = Query(default=None, max_length=80),
                 min_price: Decimal | None = Query(default=None, ge=0),
                 max_price: Decimal | None = Query(default=None, ge=0),
                 sort: Literal["recent", "price_asc", "price_desc"] = "recent",
                 page: Page = 1, page_size: PageSize = 20, db: Session = Depends(get_db)):
        return paginate(db, catalog_query(kind, q, category, store, province, min_price, max_price, sort),
                        listing_data, page, page_size)
    return endpoint


router.add_api_route("/products", catalog_endpoint("product"), methods=["GET"])
router.add_api_route("/services", catalog_endpoint("service"), methods=["GET"])


def detail_endpoint(kind):
    def endpoint(slug: str, db: Session = Depends(get_db)):
        listing = db.scalar(select(Listing).join(Store).join(Category).where(Listing.slug == slug,
                            Listing.kind == kind, Listing.status == "published", Store.status == "approved",
                            Category.active.is_(True)))
        if not listing:
            raise HTTPException(404, "Anúncio não encontrado")
        return listing_data(listing)
    return endpoint


router.add_api_route("/products/{slug}", detail_endpoint("product"), methods=["GET"])
router.add_api_route("/services/{slug}", detail_endpoint("service"), methods=["GET"])


@router.get("/categories")
def categories(page: Page = 1, page_size: PageSize = 100, db: Session = Depends(get_db)):
    return paginate(db, select(Category).where(Category.active.is_(True)).order_by(Category.name),
                    category_data, page, page_size)


@router.get("/stores")
def stores(q: str | None = Query(default=None, max_length=120), province: str | None = Query(default=None, max_length=80),
           page: Page = 1, page_size: PageSize = 20, db: Session = Depends(get_db)):
    query = select(Store).where(Store.status == "approved")
    if q:
        query = query.where(Store.name.ilike(f"%{q}%"))
    if province:
        query = query.where(Store.province.ilike(province))
    return paginate(db, query.order_by(Store.name), store_data, page, page_size)


@router.get("/stores/{slug}")
def store(slug: str, db: Session = Depends(get_db)):
    result = db.scalar(select(Store).where(Store.slug == slug, Store.status == "approved"))
    if not result:
        raise HTTPException(404, "Loja não encontrada")
    return store_data(result)
