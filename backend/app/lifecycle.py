"""Single source of truth for campaign lifecycle legality.

The server both ENFORCES transitions with this module and EXPOSES its output
(`allowed_actions`) on every admin API response. The client renders action
buttons purely from that list, so client and server cannot drift.
"""
from datetime import datetime, timezone

from .models import Campaign

# action -> (statuses it is legal FROM, status it moves TO, needs launch-validity?)
TRANSITIONS: dict[str, tuple[set[str], str, bool]] = {
    "schedule": ({"draft"}, "scheduled", True),
    "launch": ({"draft", "scheduled"}, "live", True),
    # Decision: `end` is allowed from any non-terminal status (abandoning a
    # draft counts as ending it). Forward-only either way. Noted in TECH_NOTES.
    "end": ({"draft", "scheduled", "live"}, "ended", False),
}


class TransitionError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def window_problems(campaign: Campaign) -> list[str]:
    problems = []
    if campaign.starts_at is None or campaign.ends_at is None:
        problems.append("Set both a start and an end for the window.")
        return problems
    if campaign.ends_at <= campaign.starts_at:
        problems.append("The window ends before it starts.")
    if campaign.ends_at <= datetime.now(timezone.utc):
        problems.append("The window is already in the past.")
    return problems


def launch_problems(campaign: Campaign) -> list[str]:
    """Why this campaign cannot be scheduled/launched right now (empty = it can)."""
    problems = window_problems(campaign)
    if len(campaign.offers) == 0:
        problems.append("Attach at least one offer.")
    return problems


def allowed_actions(campaign: Campaign) -> list[str]:
    actions = []
    for action, (from_statuses, _to, needs_validity) in TRANSITIONS.items():
        if campaign.status not in from_statuses:
            continue
        if needs_validity and launch_problems(campaign):
            continue
        actions.append(action)
    return actions


def apply_transition(campaign: Campaign, action: str) -> None:
    """Mutates campaign.status or raises TransitionError with a human reason."""
    if action not in TRANSITIONS:
        raise TransitionError(f"Unknown action '{action}'.")
    from_statuses, to_status, needs_validity = TRANSITIONS[action]
    if campaign.status not in from_statuses:
        raise TransitionError(
            f"Cannot {action} a campaign that is '{campaign.status}'."
        )
    if needs_validity:
        problems = launch_problems(campaign)
        if problems:
            raise TransitionError(" ".join(problems))
    campaign.status = to_status
