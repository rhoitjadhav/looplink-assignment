from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Campaign, Enrollment
from ..normalize import InvalidIdentity, normalize_identity
from ..schemas import (
    CampaignAdmin, CampaignUpdate, CampaignWrite, TransitionRequest,
    CampaignPublic, EnrollRequest, EnrollResponse, OfferPublic, PublicCampaignResponse,
)
from ..services.campaign import CampaignService

admin_router = APIRouter(prefix="/api/campaigns", tags=["admin"])
public_router = APIRouter(prefix="/api/public/campaigns", tags=["public"])

service = CampaignService()


# --- public helpers ----------------------------------------------------------

def resolve_token(db: Session, token: str) -> Campaign:
    campaign = db.scalars(
        select(Campaign)
        .options(selectinload(Campaign.offers))
        .where(Campaign.public_token == token)
    ).first()
    if campaign is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "This link isn't valid."})
    return campaign


def public_shape(campaign: Campaign) -> CampaignPublic:
    return CampaignPublic(
        name=campaign.name,
        description=campaign.description,
        offers=[OfferPublic(type=o.type, params=o.params) for o in campaign.offers],
    )


def public_state(campaign: Campaign) -> str:
    if campaign.status == "live":
        return "live"
    if campaign.status == "ended":
        return "ended"
    return "not_open"


# --- admin routes ------------------------------------------------------------

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


# --- public routes -----------------------------------------------------------

@public_router.get("/{token}", response_model=PublicCampaignResponse)
def view_campaign(token: str, db: Session = Depends(get_db)):
    campaign = resolve_token(db, token)
    state = public_state(campaign)
    return PublicCampaignResponse(
        state=state,
        campaign=public_shape(campaign) if state == "live" else None,
    )


@public_router.post("/{token}/enroll", response_model=EnrollResponse)
def enroll(token: str, body: EnrollRequest, db: Session = Depends(get_db)):
    campaign = resolve_token(db, token)
    if campaign.status != "live":
        raise HTTPException(
            status_code=409,
            detail={"code": "not_live", "message": "This campaign isn't open for enrollment."},
        )
    try:
        identity_type, normalized = normalize_identity(body.identity)
    except InvalidIdentity as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_identity", "message": str(exc)})

    stmt = (
        pg_insert(Enrollment)
        .values(
            campaign_id=campaign.id,
            identity_type=identity_type,
            identity_raw=body.identity.strip(),
            identity_normalized=normalized,
        )
        .on_conflict_do_nothing(constraint="uq_enrollment_identity")
        .returning(Enrollment.id)
    )
    inserted = db.execute(stmt).first()
    db.commit()

    return EnrollResponse(
        already_enrolled=inserted is None,
        identity_type=identity_type,
        campaign=public_shape(campaign),
    )
