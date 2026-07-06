from uuid import UUID

from fastapi import APIRouter

from ..schemas import (
    CampaignAdmin, CampaignUpdate, CampaignWrite, TransitionRequest,
    EnrollRequest, EnrollResponse, PublicCampaignResponse,
)
from ..services.campaign import CampaignService

admin_router = APIRouter(prefix="/api/campaigns", tags=["admin"])
public_router = APIRouter(prefix="/api/public/campaigns", tags=["public"])

service = CampaignService()


# ---- Admin routes -----
@admin_router.get("", response_model=list[CampaignAdmin])
def list_campaigns():
    return service.list_campaigns()


@admin_router.post("", response_model=CampaignAdmin, status_code=201)
def create_campaign(body: CampaignWrite):
    return service.create_campaign(body)


@admin_router.get("/{campaign_id}", response_model=CampaignAdmin)
def get_campaign(campaign_id: UUID):
    return service.get_campaign(campaign_id)


@admin_router.put("/{campaign_id}", response_model=CampaignAdmin)
def update_campaign(campaign_id: UUID, body: CampaignUpdate):
    return service.update_campaign(campaign_id, body)


@admin_router.post("/{campaign_id}/transitions", response_model=CampaignAdmin)
def transition_campaign(campaign_id: UUID, body: TransitionRequest):
    return service.transition_campaign(campaign_id, body)


# ---- Public routes -----
@public_router.get("/{token}", response_model=PublicCampaignResponse)
def view_campaign(token: str):
    return service.view_campaign(token)


@public_router.post("/{token}/enroll", response_model=EnrollResponse)
def enroll(token: str, body: EnrollRequest):
    return service.enroll_campaign(token, body)
