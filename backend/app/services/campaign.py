from uuid import UUID

from fastapi import HTTPException

from ..lifecycle import TransitionError, allowed_actions, apply_transition, launch_problems
from ..models import Campaign, Enrollment, Offer
from ..schemas import CampaignAdmin, CampaignUpdate, CampaignWrite, TransitionRequest


def conflict(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": code, "message": message})


class CampaignService:
    def __int__(self, campaign_model: Campaign):
        self.campaign_model = campaign_model

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
        campaign = Campaign.create(**campaign_data.model_dump(exclude={"offers"}), offers=offers)
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
