from datetime import datetime
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# --- Offer params: discriminated union on `type` ---------------------------

class ProductPercentDiscount(BaseModel):
    type: Literal["PRODUCT_PERCENT_DISCOUNT"]
    percent: float = Field(gt=0, le=100)
    applies_to: str = Field(min_length=1, max_length=200)


class CartFixedDiscount(BaseModel):
    type: Literal["CART_FIXED_DISCOUNT"]
    amount_off: float = Field(gt=0)
    min_basket: float = Field(ge=0)


class StickerEarn(BaseModel):
    type: Literal["STICKER_EARN"]
    stickers: int = Field(gt=0)
    per_amount: float = Field(gt=0)


OfferIn = Annotated[
    Union[ProductPercentDiscount, CartFixedDiscount, StickerEarn],
    Field(discriminator="type"),
]


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    type: str
    params: dict


# --- Admin (internal) -------------------------------------------------------

class CampaignWrite(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    offers: list[OfferIn] = Field(default_factory=list)


class CampaignUpdate(CampaignWrite):
    version: int  # optimistic lock: the version the client last read


class CampaignAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str
    starts_at: datetime | None
    ends_at: datetime | None
    status: str
    public_token: str
    version: int
    created_at: datetime
    updated_at: datetime
    offers: list[OfferOut]
    allowed_actions: list[str] = []       # injected by the router via lifecycle.py
    launch_problems: list[str] = []       # why schedule/launch is unavailable
    enrollment_count: int = 0


class TransitionRequest(BaseModel):
    action: Literal["schedule", "launch", "end"]
    version: int


# --- Public (shopper) — deliberately minimal --------------------------------

class OfferPublic(BaseModel):
    type: str
    params: dict


class CampaignPublic(BaseModel):
    name: str
    description: str
    offers: list[OfferPublic]
    # NO id, NO token echo, NO window, NO version, NO internal status values.


class PublicCampaignResponse(BaseModel):
    state: Literal["live", "not_open", "ended"]
    campaign: CampaignPublic | None = None  # populated only when live


class EnrollRequest(BaseModel):
    identity: str = Field(min_length=1, max_length=200)


class EnrollResponse(BaseModel):
    already_enrolled: bool
    identity_type: str
    campaign: CampaignPublic
