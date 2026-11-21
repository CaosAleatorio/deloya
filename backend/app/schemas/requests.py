from datetime import datetime
import re
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Register(StrictModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(min_length=12, max_length=128)
    phone: str = Field(default="", max_length=30)


class Login(StrictModel):
    email: EmailStr
    password: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(min_length=1, max_length=128)


class ProfileUpdate(StrictModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = Field(default=None, max_length=254)
    current_password: Annotated[str, StringConstraints(strip_whitespace=False)] | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("name", "phone", "email", mode="before")
    @classmethod
    def non_null_profile_field(cls, value):
        if value is None:
            raise ValueError("Indique um valor para este campo")
        return value

    @model_validator(mode="after")
    def profile_changes(self):
        if not self.model_fields_set.intersection({"name", "phone", "email"}):
            raise ValueError("Indique os dados do perfil a actualizar")
        return self


class PasswordChange(StrictModel):
    current_password: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(min_length=1, max_length=128)
    new_password: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(min_length=12, max_length=128)


class AccountDelete(StrictModel):
    current_password: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(min_length=1, max_length=128)
    confirmation: Literal["ELIMINAR"]


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
    mpesa_phone: str | None = Field(default=None, max_length=30)
    mpesa_account_name: str | None = Field(default=None, min_length=2, max_length=160)
    emola_phone: str | None = Field(default=None, max_length=30)
    emola_account_name: str | None = Field(default=None, min_length=2, max_length=160)
    _logo = field_validator("logo_url")(valid_image_url)

    @field_validator("mpesa_phone", "emola_phone", mode="before")
    @classmethod
    def wallet_phone(cls, value):
        if value is None or not str(value).strip():
            return None
        number = re.sub(r"[\s()-]", "", str(value))
        if re.fullmatch(r"\d{9}", number):
            number = "+258" + number
        elif re.fullmatch(r"258\d{9}", number):
            number = "+" + number
        if not re.fullmatch(r"\+258\d{9}", number):
            raise ValueError("Indique um número moçambicano de 9 dígitos, com +258 opcional")
        return number

    @field_validator("mpesa_account_name", "emola_account_name", mode="before")
    @classmethod
    def wallet_name(cls, value):
        if value is None:
            return None
        return str(value).strip() or None

    @model_validator(mode="after")
    def wallet_pairs(self):
        for provider in ("mpesa", "emola"):
            if bool(getattr(self, f"{provider}_phone")) != bool(getattr(self, f"{provider}_account_name")):
                raise ValueError("Preencha o número e o nome do titular da mesma carteira")
        return self


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


class ManualPaymentInput(StrictModel):
    provider: Literal["mpesa", "emola"]
    reference: str = Field(min_length=3, max_length=120, pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]{2,119}$")
    idempotency_key: str = Field(min_length=8, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("reference")
    @classmethod
    def normalize_reference(cls, value):
        return value.upper()


class ManualPaymentReview(StrictModel):
    decision: Literal["confirm", "reject"]
    wallet_verified: bool = False
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def verified_decision(self):
        if self.decision == "confirm" and not self.wallet_verified:
            raise ValueError("Confirme que consultou a carteira e verificou o recebimento")
        if self.decision == "reject" and (not self.notes or len(self.notes) < 3):
            raise ValueError("Indique o motivo da rejeição")
        return self


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
