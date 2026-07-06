import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.schemas import CampaignUpdate, CampaignWrite, EnrollRequest, TransitionRequest
from app.services.campaign import CampaignService

STARTS = datetime(2026, 7, 10, tzinfo=timezone.utc)
ENDS = datetime(2026, 7, 20, tzinfo=timezone.utc)


def make_campaign(**kwargs):
    c = MagicMock()
    c.id = kwargs.get("id", uuid.uuid4())
    c.name = kwargs.get("name", "Test")
    c.description = kwargs.get("description", "")
    c.status = kwargs.get("status", "draft")
    c.version = kwargs.get("version", 1)
    c.public_token = kwargs.get("public_token", "tok123")
    c.starts_at = kwargs.get("starts_at", STARTS)
    c.ends_at = kwargs.get("ends_at", ENDS)
    c.offers = kwargs.get("offers", [])
    return c


@pytest.fixture
def svc():
    return CampaignService()


@pytest.fixture
def mock_serialize():
    with patch.object(CampaignService, "serialize", return_value=MagicMock()) as m:
        yield m


# --- get_campaign ------------------------------------------------------------

class TestGetCampaign:
    def test_not_found_raises_404(self, svc):
        with patch("app.services.campaign.Campaign.get_by_pk", return_value=None):
            with pytest.raises(HTTPException) as exc:
                svc.get_campaign(uuid.uuid4())
        assert exc.value.status_code == 404
        assert exc.value.detail["code"] == "not_found"

    def test_found_returns_serialized(self, svc, mock_serialize):
        campaign = make_campaign()
        with patch("app.services.campaign.Campaign.get_by_pk", return_value=campaign):
            result = svc.get_campaign(campaign.id)
        mock_serialize.assert_called_once_with(campaign)
        assert result is mock_serialize.return_value


# --- update_campaign ---------------------------------------------------------

class TestUpdateCampaign:
    def _body(self, version=1):
        return CampaignUpdate(
            name="Updated", description="", starts_at=STARTS, ends_at=ENDS,
            offers=[], version=version,
        )

    def test_not_found_raises_404(self, svc):
        with patch("app.services.campaign.Campaign.get_by_pk", return_value=None):
            with pytest.raises(HTTPException) as exc:
                svc.update_campaign(uuid.uuid4(), self._body())
        assert exc.value.status_code == 404

    def test_non_draft_raises_status_conflict(self, svc):
        campaign = make_campaign(status="live")
        with patch("app.services.campaign.Campaign.get_by_pk", return_value=campaign):
            with pytest.raises(HTTPException) as exc:
                svc.update_campaign(campaign.id, self._body())
        assert exc.value.status_code == 409
        assert exc.value.detail["code"] == "status_conflict"

    def test_version_mismatch_raises_version_conflict(self, svc):
        campaign = make_campaign(status="draft", version=2)
        with patch("app.services.campaign.Campaign.get_by_pk", return_value=campaign):
            with pytest.raises(HTTPException) as exc:
                svc.update_campaign(campaign.id, self._body(version=1))
        assert exc.value.status_code == 409
        assert exc.value.detail["code"] == "version_conflict"

    def test_success_calls_update_and_returns_serialized(self, svc, mock_serialize):
        campaign = make_campaign(status="draft", version=1)
        with patch("app.services.campaign.Campaign.get_by_pk", return_value=campaign) as get_mock, \
             patch("app.services.campaign.Campaign.update") as update_mock:
            result = svc.update_campaign(campaign.id, self._body(version=1))

        update_mock.assert_called_once()
        assert update_mock.call_args.args[0] == campaign.id
        assert result is mock_serialize.return_value


# --- transition_campaign -----------------------------------------------------

class TestTransitionCampaign:
    def _body(self, action="launch", version=1):
        return TransitionRequest(action=action, version=version)

    def test_not_found_raises_404(self, svc):
        with patch("app.services.campaign.Campaign.get_by_pk", return_value=None):
            with pytest.raises(HTTPException) as exc:
                svc.transition_campaign(uuid.uuid4(), self._body())
        assert exc.value.status_code == 404

    def test_version_mismatch_raises_version_conflict(self, svc):
        campaign = make_campaign(version=2)
        with patch("app.services.campaign.Campaign.get_by_pk", return_value=campaign):
            with pytest.raises(HTTPException) as exc:
                svc.transition_campaign(campaign.id, self._body(version=1))
        assert exc.value.status_code == 409
        assert exc.value.detail["code"] == "version_conflict"

    def test_illegal_transition_raises_conflict(self, svc):
        from app.services.lifecycle import TransitionError
        campaign = make_campaign(status="draft", version=1)
        with patch("app.services.campaign.Campaign.get_by_pk", return_value=campaign), \
             patch("app.services.campaign.apply_transition", side_effect=TransitionError("bad")):
            with pytest.raises(HTTPException) as exc:
                svc.transition_campaign(campaign.id, self._body(version=1))
        assert exc.value.status_code == 409
        assert exc.value.detail["code"] == "illegal_transition"

    def test_success_calls_set_status_and_returns_serialized(self, svc, mock_serialize):
        campaign = make_campaign(status="draft", version=1)
        with patch("app.services.campaign.Campaign.get_by_pk", return_value=campaign), \
             patch("app.services.campaign.apply_transition", lambda c, a: setattr(c, "status", "live")), \
             patch("app.services.campaign.Campaign.set_status") as set_mock:
            result = svc.transition_campaign(campaign.id, self._body(action="launch", version=1))

        set_mock.assert_called_once_with(campaign.id, "live")
        assert result is mock_serialize.return_value


# --- view_campaign -----------------------------------------------------------

class TestViewCampaign:
    def test_not_found_raises_404(self, svc):
        with patch("app.services.campaign.Campaign.get_by_token", return_value=None):
            with pytest.raises(HTTPException) as exc:
                svc.view_campaign("badtoken")
        assert exc.value.status_code == 404

    def test_draft_returns_not_open(self, svc):
        campaign = make_campaign(status="draft")
        with patch("app.services.campaign.Campaign.get_by_token", return_value=campaign):
            result = svc.view_campaign("tok")
        assert result.state == "not_open"
        assert result.campaign is None

    def test_scheduled_returns_not_open(self, svc):
        campaign = make_campaign(status="scheduled")
        with patch("app.services.campaign.Campaign.get_by_token", return_value=campaign):
            result = svc.view_campaign("tok")
        assert result.state == "not_open"

    def test_live_returns_campaign_shape(self, svc):
        campaign = make_campaign(status="live", name="Summer Sale", offers=[])
        with patch("app.services.campaign.Campaign.get_by_token", return_value=campaign):
            result = svc.view_campaign("tok")
        assert result.state == "live"
        assert result.campaign is not None
        assert result.campaign.name == "Summer Sale"

    def test_ended_returns_ended(self, svc):
        campaign = make_campaign(status="ended")
        with patch("app.services.campaign.Campaign.get_by_token", return_value=campaign):
            result = svc.view_campaign("tok")
        assert result.state == "ended"
        assert result.campaign is None


# --- enroll_campaign ---------------------------------------------------------

class TestEnrollCampaign:
    def test_not_found_raises_404(self, svc):
        with patch("app.services.campaign.Campaign.get_by_token", return_value=None):
            with pytest.raises(HTTPException) as exc:
                svc.enroll_campaign("bad", EnrollRequest(identity="a@b.com"))
        assert exc.value.status_code == 404

    def test_not_live_raises_409(self, svc):
        campaign = make_campaign(status="draft")
        with patch("app.services.campaign.Campaign.get_by_token", return_value=campaign):
            with pytest.raises(HTTPException) as exc:
                svc.enroll_campaign("tok", EnrollRequest(identity="a@b.com"))
        assert exc.value.status_code == 409
        assert exc.value.detail["code"] == "not_live"

    def test_invalid_identity_raises_422(self, svc):
        campaign = make_campaign(status="live")
        with patch("app.services.campaign.Campaign.get_by_token", return_value=campaign):
            with pytest.raises(HTTPException) as exc:
                svc.enroll_campaign("tok", EnrollRequest(identity="notanemail"))
        assert exc.value.status_code == 422
        assert exc.value.detail["code"] == "invalid_identity"

    def test_new_enrollment(self, svc):
        campaign = make_campaign(status="live", offers=[])
        with patch("app.services.campaign.Campaign.get_by_token", return_value=campaign), \
             patch("app.services.campaign.Enrollment.enroll", return_value=False):
            result = svc.enroll_campaign("tok", EnrollRequest(identity="user@test.com"))
        assert result.already_enrolled is False
        assert result.identity_type == "email"

    def test_duplicate_enrollment(self, svc):
        campaign = make_campaign(status="live", offers=[])
        with patch("app.services.campaign.Campaign.get_by_token", return_value=campaign), \
             patch("app.services.campaign.Enrollment.enroll", return_value=True):
            result = svc.enroll_campaign("tok", EnrollRequest(identity="user@test.com"))
        assert result.already_enrolled is True

    def test_phone_identity_accepted(self, svc):
        campaign = make_campaign(status="live", offers=[])
        with patch("app.services.campaign.Campaign.get_by_token", return_value=campaign), \
             patch("app.services.campaign.Enrollment.enroll", return_value=False):
            result = svc.enroll_campaign("tok", EnrollRequest(identity="+1234567890"))
        assert result.identity_type == "phone"
