from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Register(StrictModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    phone: str = Field(default="", max_length=30)


class Login(StrictModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdate(StrictModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(default="", max_length=30)


class AddressInput(StrictModel):
    label: str = Field(min_length=1, max_length=80)
    address: str = Field(min_length=5, max_length=500)
    province: str = Field(default="Nampula", min_length=2, max_length=80)
    district: str = Field(default="Nampula", min_length=2, max_length=80)
    phone: str = Field(default="", max_length=30)


def valid_image_url(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if value.startswith("/demo/") and ".." not in value:
        return value
    # Only the configured public Blob origin is allowed; no arbitrary remote fetches.
    from app.core.config import get_settings
    origin = get_settings().blob_public_base_url
    if origin and value.startswith(origin.rstrip("/") + "/") and ".." not in value:
        return value
    raise ValueError("Use uma imagem carregada no armazenamento público autorizado")


class StoreInput(StrictModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10, max_length=5000)
    province: str = Field(default="Nampula", min_length=2, max_length=80)
    district: str = Field(default="Nampula", min_length=2, max_length=80)
    address: str = Field(min_length=3, max_length=500)
    phone: str = Field(min_length=5, max_length=30)
    nuit: str | None = Field(default=None, max_length=30)
    logo_url: str | None = Field(default=None, max_length=1000)
    delivery_fee: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    _logo = field_validator("logo_url")(valid_image_url)


class ListingInput(StrictModel):
    name: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=10, max_length=10000)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    stock: int | None = Field(default=None, ge=0, le=1000000)
    sku: str | None = Field(default=None, min_length=1, max_length=80)
    category_id: UUID
    image_url: str | None = Field(default=None, max_length=1000)
    images: list[str] = Field(default_factory=list, max_length=6)
    service_location: str | None = Field(default=None, max_length=180)
    estimated_duration: str | None = Field(default=None, max_length=100)
    status: Literal["draft", "pending"] = "pending"
    expected_updated_at: datetime | None = None
    _image = field_validator("image_url")(valid_image_url)

    @field_validator("images")
    @classmethod
    def images_valid(cls, values):
        return [valid_image_url(value) for value in values]


class CartAdd(StrictModel):
    listing_id: UUID
    quantity: int = Field(default=1, ge=1, le=999)


class Quantity(StrictModel):
    quantity: int = Field(ge=1, le=999)


class OrderInput(StrictModel):
    delivery_method: Literal["pickup", "arranged"] = "pickup"
    address: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    requested_date: datetime | None = None
    idempotency_key: str = Field(min_length=8, max_length=120)

    @model_validator(mode="after")
    def delivery_address(self):
        if self.delivery_method == "arranged" and (not self.address or len(self.address) < 5):
            raise ValueError("Indique a morada de entrega")
        if self.requested_date and self.requested_date.tzinfo is None:
            raise ValueError("A data pretendida deve incluir o fuso horário")
        return self


class PaymentInput(StrictModel):
    order_id: UUID
    provider: Literal["demo", "mpesa", "emola"] = "demo"
    idempotency_key: str = Field(min_length=8, max_length=120)


class Simulation(StrictModel):
    outcome: Literal["success", "failure", "expired"]


class StoreModeration(StrictModel):
    status: Literal["approved", "suspended"]
    reason: str = Field(default="", max_length=1000)


class ListingModeration(StrictModel):
    status: Literal["published", "rejected", "draft"]
    reason: str = Field(default="", max_length=1000)


class CategoryInput(StrictModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str | None = Field(default=None, min_length=2, max_length=120, pattern=r"^[a-z0-9-]+$")
    parent_id: UUID | None = None


class VendorTransition(StrictModel):
    status: Literal["paga", "em_preparacao", "pronta", "entregue"] | None = None
    service_status: Literal["confirmada", "concluida"] | None = None


class SupportInput(StrictModel):
    subject: str = Field(min_length=3, max_length=180)
    message: str = Field(min_length=10, max_length=5000)
    order_id: UUID | None = None


class SupportUpdate(StrictModel):
    status: Literal["open", "resolved"]
    response: str | None = Field(default=None, max_length=5000)


class PaymentConfigInput(StrictModel):
    demo_enabled: bool


class ServiceRequestInput(StrictModel):
    listing_id: UUID
    message: str = Field(min_length=10, max_length=3000)
    requested_date: datetime | None = None

    @field_validator("requested_date")
    @classmethod
    def aware_date(cls, value):
        if value and value.tzinfo is None:
            raise ValueError("A data pretendida deve incluir o fuso horário")
        return value


class ServiceRequestUpdate(StrictModel):
    status: Literal["confirmed", "declined", "completed"]
