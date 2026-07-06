from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..lifecycle import TransitionError, allowed_actions, apply_transition, launch_problems
from ..models import Campaign, Enrollment, Offer
from ..schemas import (
    CampaignAdmin, CampaignUpdate, CampaignWrite, TransitionRequest,
)

router = APIRouter(prefix="/api/campaigns", tags=["admin"])


def conflict(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": code, "message": message})


def get_campaign_or_404(db: Session, campaign_id: UUID) -> Campaign:
    campaign = db.scalars(
        select(Campaign)
        .options(selectinload(Campaign.offers))
        .where(Campaign.id == campaign_id)
    ).first()
    if campaign is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Campaign not found"})
    return campaign


def check_version(campaign: Campaign, client_version: int) -> None:
    if campaign.version != client_version:
        raise conflict(
            "version_conflict",
            "This campaign changed since you loaded it. Reload to see the latest.",
        )


def serialize(db: Session, campaign: Campaign) -> CampaignAdmin:
    count = db.scalar(
        select(func.count(Enrollment.id)).where(Enrollment.campaign_id == campaign.id)
    )
    out = CampaignAdmin.model_validate(campaign)
    out.allowed_actions = allowed_actions(campaign)
    out.launch_problems = launch_problems(campaign)
    out.enrollment_count = count or 0
    return out


def set_offers(campaign: Campaign, offers_in) -> None:
    campaign.offers.clear()
    for position, offer in enumerate(offers_in):
        data = offer.model_dump()
        offer_type = data.pop("type")
        campaign.offers.append(Offer(type=offer_type, params=data, position=position))


@router.get("", response_model=list[CampaignAdmin])
def list_campaigns(db: Session = Depends(get_db)):
    campaigns = db.scalars(
        select(Campaign)
        .options(selectinload(Campaign.offers))
        .order_by(Campaign.created_at.desc())
    ).all()
    return [serialize(db, c) for c in campaigns]


@router.post("", response_model=CampaignAdmin, status_code=201)
def create_campaign(body: CampaignWrite, db: Session = Depends(get_db)):
    campaign = Campaign(
        name=body.name, description=body.description,
        starts_at=body.starts_at, ends_at=body.ends_at,
    )
    set_offers(campaign, body.offers)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return serialize(db, campaign)


@router.get("/{campaign_id}", response_model=CampaignAdmin)
def get_campaign(campaign_id: UUID, db: Session = Depends(get_db)):
    return serialize(db, get_campaign_or_404(db, campaign_id))


@router.put("/{campaign_id}", response_model=CampaignAdmin)
def update_campaign(campaign_id: UUID, body: CampaignUpdate, db: Session = Depends(get_db)):
    campaign = get_campaign_or_404(db, campaign_id)
    if campaign.status != "draft":
        raise conflict(
            "status_conflict",
            f"Only drafts can be edited; this campaign is {campaign.status}.",
        )
    check_version(campaign, body.version)
    campaign.name = body.name
    campaign.description = body.description
    campaign.starts_at = body.starts_at
    campaign.ends_at = body.ends_at
    set_offers(campaign, body.offers)
    campaign.version += 1
    db.commit()
    db.refresh(campaign)
    return serialize(db, campaign)


@router.post("/{campaign_id}/transitions", response_model=CampaignAdmin)
def transition_campaign(campaign_id: UUID, body: TransitionRequest, db: Session = Depends(get_db)):
    campaign = get_campaign_or_404(db, campaign_id)
    check_version(campaign, body.version)
    try:
        apply_transition(campaign, body.action)
    except TransitionError as exc:
        raise conflict("illegal_transition", exc.message)
    campaign.version += 1
    db.commit()
    db.refresh(campaign)
    return serialize(db, campaign)
