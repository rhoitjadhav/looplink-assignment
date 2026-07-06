from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class OfferPublic(BaseModel):
    type: str
    params: dict
