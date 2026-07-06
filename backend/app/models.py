import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

CAMPAIGN_STATUSES = ("draft", "scheduled", "live", "ended")
OFFER_TYPES = ("PRODUCT_PERCENT_DISCOUNT", "CART_FIXED_DISCOUNT", "STICKER_EARN")


def utcnow():
    return datetime.now(timezone.utc)


def new_public_token():
    return secrets.token_urlsafe(9)  # 12 chars, unguessable


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
        String(24), unique=True, index=True, default=new_public_token, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    offers: Mapped[list["Offer"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="Offer.position",
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="campaign")


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(
        Enum(*OFFER_TYPES, name="offer_type"), nullable=False
    )
    params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    campaign: Mapped[Campaign] = relationship(back_populates="offers")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint(
            "campaign_id", "identity_normalized", name="uq_enrollment_identity"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    identity_type: Mapped[str] = mapped_column(
        Enum("email", "phone", name="identity_type"), nullable=False
    )
    identity_raw: Mapped[str] = mapped_column(String(200), nullable=False)
    identity_normalized: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    campaign: Mapped[Campaign] = relationship(back_populates="enrollments")
