import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String, Text, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from ..database import Base, SessionLocal

CAMPAIGN_STATUSES = ("draft", "scheduled", "live", "ended")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        Enum(*CAMPAIGN_STATUSES, name="campaign_status"),
        default="draft", nullable=False,
    )
    public_token: Mapped[str] = mapped_column(
        String(24), unique=True, index=True,
        default=lambda: secrets.token_urlsafe(9),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    offers: Mapped[list["Offer"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="Offer.position",
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="campaign")



    @classmethod
    def create(cls, offers=None, **kwargs):
        kwargs.pop("offers", None)
        model_obj = cls(**kwargs)
        if offers:
            model_obj.offers.extend(offers)
        with SessionLocal() as session:
            session.add(model_obj)
            session.commit()
            session.refresh(model_obj)
            return model_obj

    @classmethod
    def get_by_pk(cls, pk):
        stmt = (
            select(Campaign)
            .options(selectinload(Campaign.offers))
            .where(Campaign.id == pk)
        )
        with SessionLocal() as session:
            return session.scalars(stmt).first()

    @classmethod
    def get(cls):
        stmt = (
            select(Campaign)
            .options(selectinload(Campaign.offers))
            .order_by(Campaign.created_at.desc())
        )
        with SessionLocal() as session:
            return session.scalars(stmt).all()

    @classmethod
    def update(cls, campaign_id, offers=None, **kwargs):
        with SessionLocal() as session:
            campaign = session.scalars(
                select(cls).options(selectinload(cls.offers)).where(cls.id == campaign_id)
            ).first()
            if not campaign:
                return None
            for key, value in kwargs.items():
                setattr(campaign, key, value)
            if offers is not None:
                campaign.offers.clear()
                campaign.offers.extend(offers)
            campaign.version += 1
            session.commit()
            return campaign_id

    @classmethod
    def set_status(cls, campaign_id, status):
        with SessionLocal() as session:
            campaign = session.scalars(
                select(cls).where(cls.id == campaign_id)
            ).first()
            if not campaign:
                return None
            campaign.status = status
            campaign.version += 1
            session.commit()
            return campaign_id
