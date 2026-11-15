from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer,
                        Numeric, String, Text, UniqueConstraint, Uuid, JSON)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def utcnow():
    return datetime.now(timezone.utc)


class Entity:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class User(Entity, Base):
    __tablename__ = "users"
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(30), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="customer")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (CheckConstraint("role IN ('customer','vendor','admin')", name="ck_user_role"),)


class Address(Entity, Base):
    __tablename__ = "customer_addresses"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    label: Mapped[str] = mapped_column(String(80))
    address: Mapped[str] = mapped_column(String(500))
    province: Mapped[str] = mapped_column(String(80), default="Nampula")
    district: Mapped[str] = mapped_column(String(80), default="Nampula")
    phone: Mapped[str] = mapped_column(String(30), default="")


class AuthSession(Entity, Base):
    __tablename__ = "auth_sessions"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    family_id: Mapped[UUID] = mapped_column(Uuid, default=uuid4, index=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


class Category(Entity, Base):
    __tablename__ = "categories"
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("categories.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Store(Entity, Base):
    __tablename__ = "stores"
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    province: Mapped[str] = mapped_column(String(80), default="Nampula")
    district: Mapped[str] = mapped_column(String(80), default="Nampula")
    address: Mapped[str] = mapped_column(String(500))
    phone: Mapped[str] = mapped_column(String(30))
    nuit: Mapped[str | None] = mapped_column(String(30))
    logo_url: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    delivery_fee: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    mpesa_phone: Mapped[str | None] = mapped_column(String(13))
    mpesa_account_name: Mapped[str | None] = mapped_column(String(160))
    emola_phone: Mapped[str | None] = mapped_column(String(13))
    emola_account_name: Mapped[str | None] = mapped_column(String(160))
    __table_args__ = (CheckConstraint("status IN ('pending','approved','suspended')", name="ck_store_status"),
                     CheckConstraint("delivery_fee IS NULL OR delivery_fee >= 0", name="ck_store_delivery_fee"))


class Listing(Entity, Base):
    __tablename__ = "listings"
    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), index=True)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id"), index=True)
    slug: Mapped[str] = mapped_column(String(220), unique=True)
    kind: Mapped[str] = mapped_column(String(16), index=True)
    sku: Mapped[str | None] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    stock: Mapped[int | None] = mapped_column(Integer)
    image_url: Mapped[str | None] = mapped_column(String(1000))
    images: Mapped[list] = mapped_column(JSON, default=list)
    service_location: Mapped[str | None] = mapped_column(String(180))
    estimated_duration: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    store: Mapped[Store] = relationship()
    category: Mapped[Category] = relationship()
    __table_args__ = (
        UniqueConstraint("store_id", "sku", name="uq_listing_store_sku"),
        CheckConstraint("kind IN ('product','service')", name="ck_listing_kind"),
        CheckConstraint("status IN ('draft','pending','published','rejected','archived')", name="ck_listing_status"),
        CheckConstraint("price IS NULL OR price >= 0", name="ck_listing_price"),
        CheckConstraint("(kind='product' AND stock >= 0 AND price IS NOT NULL AND sku IS NOT NULL) OR (kind='service' AND stock IS NULL)", name="ck_listing_stock"),
    )


class CartItem(Entity, Base):
    __tablename__ = "cart_items"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("listings.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    listing: Mapped[Listing] = relationship()
    __table_args__ = (UniqueConstraint("user_id", "listing_id", name="uq_cart_user_listing"),
                     CheckConstraint("quantity > 0 AND quantity <= 999", name="ck_cart_quantity"))


class Order(Entity, Base):
    __tablename__ = "orders"
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), default="pendente_pagamento", index=True)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    is_demo: Mapped[bool] = mapped_column(Boolean)
    payment_mode: Mapped[str] = mapped_column(String(20), default="demo", server_default="demo")
    stock_released: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_method: Mapped[str] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(String(1000))
    requested_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    vendor_orders: Mapped[list["VendorOrder"]] = relationship(back_populates="order", order_by="VendorOrder.created_at")
    __table_args__ = (UniqueConstraint("customer_id", "idempotency_key", name="uq_order_idempotency"),
                     CheckConstraint("total >= 0", name="ck_order_total"),
                     CheckConstraint("status IN ('pendente_pagamento','parcialmente_paga','paga','em_preparacao','pronta','entregue','cancelada')", name="ck_order_status"))


class VendorOrder(Entity, Base):
    __tablename__ = "vendor_orders"
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), index=True)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    status: Mapped[str] = mapped_column(String(30), default="pendente_pagamento")
    service_status: Mapped[str | None] = mapped_column(String(30))
    payment_destinations: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    order: Mapped[Order] = relationship(back_populates="vendor_orders")
    store: Mapped[Store] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(order_by="OrderItem.created_at")
    payments: Mapped[list["PaymentAttempt"]] = relationship(order_by="PaymentAttempt.created_at")
    __table_args__ = (UniqueConstraint("order_id", "store_id", name="uq_order_store"),)


class OrderItem(Entity, Base):
    __tablename__ = "order_items"
    vendor_order_id: Mapped[UUID] = mapped_column(ForeignKey("vendor_orders.id"), index=True)
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("listings.id"))
    name: Mapped[str] = mapped_column(String(180))
    kind: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class PaymentAttempt(Entity, Base):
    __tablename__ = "payment_attempts"
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    vendor_order_id: Mapped[UUID | None] = mapped_column(ForeignKey("vendor_orders.id"), index=True)
    reference: Mapped[str] = mapped_column(String(60), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(120))
    provider: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    is_demo: Mapped[bool] = mapped_column(Boolean)
    transfer_reference: Mapped[str | None] = mapped_column(String(120))
    destination_phone: Mapped[str | None] = mapped_column(String(13))
    destination_account_name: Mapped[str | None] = mapped_column(String(160))
    notes: Mapped[str | None] = mapped_column(String(1000))
    review_notes: Mapped[str | None] = mapped_column(String(1000))
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    order: Mapped[Order] = relationship()
    vendor_order: Mapped[VendorOrder | None] = relationship(overlaps="payments")
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key", name="uq_payment_idempotency"),
                     CheckConstraint("status IN ('pending','success','failure','expired')", name="ck_payment_status"))


class PaymentConfig(Base):
    __tablename__ = "payment_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    demo_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(Entity, Base):
    __tablename__ = "audit_logs"
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str] = mapped_column(String(60))
    resource_id: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class SupportTicket(Entity, Base):
    __tablename__ = "support_tickets"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    order_id: Mapped[UUID | None] = mapped_column(ForeignKey("orders.id"))
    subject: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")
    response: Mapped[str | None] = mapped_column(Text)


class PrivateAttachment(Entity, Base):
    __tablename__ = "private_attachments"
    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("support_tickets.id"), index=True)
    uploaded_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    pathname: Mapped[str] = mapped_column(String(500), unique=True)
    filename: Mapped[str] = mapped_column(String(180))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        CheckConstraint("size_bytes > 0 AND size_bytes <= 3145728", name="ck_private_attachment_size"),
        CheckConstraint("content_type IN ('image/jpeg','image/png','image/webp','application/pdf')",
                        name="ck_private_attachment_type"),
    )


class ServiceRequest(Entity, Base):
    __tablename__ = "service_requests"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("listings.id"), index=True)
    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), index=True)
    message: Mapped[str] = mapped_column(Text)
    requested_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="requested")
    listing: Mapped[Listing] = relationship()


class UploadedImage(Entity, Base):
    __tablename__ = "uploaded_images"
    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), index=True)
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    pathname: Mapped[str] = mapped_column(String(500))


Index("ix_listing_catalog", Listing.status, Listing.kind, Listing.created_at)
Index("uq_manual_payment_active", PaymentAttempt.vendor_order_id, unique=True,
      postgresql_where=(PaymentAttempt.vendor_order_id.is_not(None) & PaymentAttempt.status.in_(["pending", "success"])))
Index("uq_manual_transfer_reference", PaymentAttempt.provider, PaymentAttempt.destination_phone,
      PaymentAttempt.transfer_reference, unique=True,
      postgresql_where=(PaymentAttempt.vendor_order_id.is_not(None) & PaymentAttempt.status.in_(["pending", "success"])))
