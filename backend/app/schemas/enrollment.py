from pydantic import BaseModel, Field

from .campaign import CampaignPublic


class EnrollRequest(BaseModel):
    identity: str = Field(min_length=1, max_length=200)


class EnrollResponse(BaseModel):
    already_enrolled: bool
    identity_type: str
    campaign: CampaignPublic
