from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .offer import OfferIn, OfferOut, OfferPublic


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
    allowed_actions: list[str] = []
    launch_problems: list[str] = []
    enrollment_count: int = 0


class TransitionRequest(BaseModel):
    action: Literal["schedule", "launch", "end"]
    version: int


class CampaignPublic(BaseModel):
    name: str
    description: str
    offers: list[OfferPublic]
    # NO id, NO token echo, NO window, NO version, NO internal status values.


class PublicCampaignResponse(BaseModel):
    state: Literal["live", "not_open", "ended"]
    campaign: CampaignPublic | None = None  # populated only when live
