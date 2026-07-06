from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .database import SessionLocal
from .models import Campaign


def tick() -> None:
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        # scheduled campaigns whose window has started but not yet ended → live
        to_launch = db.scalars(
            select(Campaign)
            .options(selectinload(Campaign.offers))
            .where(
                Campaign.status == "scheduled",
                Campaign.starts_at <= now,
                Campaign.ends_at > now,
            )
        ).all()
        for c in to_launch:
            c.status = "live"
            c.version += 1

        # live or scheduled campaigns whose window has expired → ended
        to_end = db.scalars(
            select(Campaign).where(
                Campaign.status.in_(["live", "scheduled"]),
                Campaign.ends_at <= now,
            )
        ).all()
        for c in to_end:
            c.status = "ended"
            c.version += 1

        if to_launch or to_end:
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
