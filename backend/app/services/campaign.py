from uuid import UUID

from fastapi import HTTPException

from ..lifecycle import TransitionError, allowed_actions, apply_transition, launch_problems
from ..models import Campaign, Enrollment, Offer
from ..normalize import InvalidIdentity, normalize_identity
from ..schemas import (
    CampaignAdmin, CampaignPublic, CampaignUpdate, CampaignWrite,
    EnrollRequest, EnrollResponse, OfferPublic, PublicCampaignResponse, TransitionRequest,
)


def conflict(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": code, "message": message})


class CampaignService:
    def __int__(self, campaign_model: Campaign):
        self.campaign_model = campaign_model

    @staticmethod
    def _public_shape(campaign: Campaign) -> CampaignPublic:
        return CampaignPublic(
            name=campaign.name,
            description=campaign.description,
            offers=[OfferPublic(type=o.type, params=o.params) for o in campaign.offers],
        )

    @staticmethod
    def _public_state(campaign: Campaign) -> str:
        if campaign.status == "live":
            return "live"
        if campaign.status == "ended":
            return "ended"
        return "not_open"

    @staticmethod
    def serialize(campaign: Campaign) -> CampaignAdmin:
        out = CampaignAdmin.model_validate(campaign)
        out.allowed_actions = allowed_actions(campaign)
        out.launch_problems = launch_problems(campaign)
        out.enrollment_count = Enrollment.get_enrollment_count(campaign.id)
        return out

    @staticmethod
    def _build_offers(offers_in) -> list[Offer]:
        offers = []
        for position, offer in enumerate(offers_in):
            data = offer.model_dump()
            offer_type = data.pop("type")
            offers.append(Offer(type=offer_type, params=data, position=position))
        return offers

    def create_campaign(self, campaign_data: CampaignWrite) -> CampaignAdmin:
        offers = self._build_offers(campaign_data.offers)
        campaign = Campaign.create(
            **campaign_data.model_dump(exclude={"offers"}), offers=offers
        )
        return self.serialize(Campaign.get_by_pk(campaign.id))

    def list_campaigns(self):
        return [self.serialize(c) for c in Campaign.get()]

    def get_campaign(self, campaign_id: UUID) -> CampaignAdmin:
        campaign = Campaign.get_by_pk(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Campaign not found"})
        return self.serialize(campaign)

    def update_campaign(self, campaign_id: UUID, body: CampaignUpdate) -> CampaignAdmin:
        campaign = Campaign.get_by_pk(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Campaign not found"})
        if campaign.status != "draft":
            raise conflict("status_conflict", f"Only drafts can be edited; this campaign is {campaign.status}.")
        if campaign.version != body.version:
            raise conflict("version_conflict", "This campaign changed since you loaded it. Reload to see the latest.")

        Campaign.update(
            campaign_id,
            offers=self._build_offers(body.offers),
            name=body.name,
            description=body.description,
            starts_at=body.starts_at,
            ends_at=body.ends_at,
        )
        return self.serialize(Campaign.get_by_pk(campaign_id))

    def transition_campaign(self, campaign_id: UUID, body: TransitionRequest) -> CampaignAdmin:
        campaign = Campaign.get_by_pk(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Campaign not found"})
        if campaign.version != body.version:
            raise conflict("version_conflict", "This campaign changed since you loaded it. Reload to see the latest.")
        try:
            apply_transition(campaign, body.action)
        except TransitionError as exc:
            raise conflict("illegal_transition", exc.message)

        Campaign.set_status(campaign_id, campaign.status)
        return self.serialize(Campaign.get_by_pk(campaign_id))

    def view_campaign(self, token: str) -> PublicCampaignResponse:
        campaign = Campaign.get_by_token(token)
        if not campaign:
            raise HTTPException(status_code=404, detail={"code": "not_found", "message": "This link isn't valid."})
        state = self._public_state(campaign)
        return PublicCampaignResponse(
            state=state,
            campaign=self._public_shape(campaign) if state == "live" else None,
        )

    def enroll_campaign(self, token: str, body: EnrollRequest) -> EnrollResponse:
        campaign = Campaign.get_by_token(token)
        if not campaign:
            raise HTTPException(status_code=404, detail={"code": "not_found", "message": "This link isn't valid."})
        if campaign.status != "live":
            raise HTTPException(status_code=409, detail={"code": "not_live", "message": "This campaign isn't open for enrollment."})
        try:
            identity_type, normalized = normalize_identity(body.identity)
        except InvalidIdentity as exc:
            raise HTTPException(status_code=422, detail={"code": "invalid_identity", "message": str(exc)})

        already_enrolled = Enrollment.enroll(
            campaign_id=campaign.id,
            identity_type=identity_type,
            identity_raw=body.identity.strip(),
            identity_normalized=normalized,
        )
        return EnrollResponse(
            already_enrolled=already_enrolled,
            identity_type=identity_type,
            campaign=self._public_shape(campaign),
        )
