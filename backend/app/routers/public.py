from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Campaign, Enrollment
from ..normalize import InvalidIdentity, normalize_identity
from ..schemas import (
    CampaignPublic, EnrollRequest, EnrollResponse, OfferPublic, PublicCampaignResponse,
)

router = APIRouter(prefix="/api/public/campaigns", tags=["public"])


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
    return "not_open"  # draft and scheduled collapse — shoppers never see internals


@router.get("/{token}", response_model=PublicCampaignResponse)
def view_campaign(token: str, db: Session = Depends(get_db)):
    campaign = resolve_token(db, token)
    state = public_state(campaign)
    return PublicCampaignResponse(
        state=state,
        campaign=public_shape(campaign) if state == "live" else None,
    )


@router.post("/{token}/enroll", response_model=EnrollResponse)
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

    # Dedup enforced by DB unique constraint; ON CONFLICT makes write race-free.
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
