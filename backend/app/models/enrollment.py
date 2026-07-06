import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sqlalchemy.dialects.postgresql import insert

from ..database import Base, SessionLocal
from .campaign import Campaign


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
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    campaign: Mapped[Campaign] = relationship(back_populates="enrollments")

    @classmethod
    def get_enrollment_count(cls, campaign_id) -> int:
        with SessionLocal() as session:
            return session.scalar(
                select(func.count(cls.id)).where(cls.campaign_id == campaign_id)
            ) or 0

    @classmethod
    def enroll(cls, campaign_id, identity_type, identity_raw, identity_normalized) -> bool:
        """Returns True if already enrolled, False if newly enrolled."""
        with SessionLocal() as session:
            stmt = (
                insert(cls)
                .values(
                    campaign_id=campaign_id,
                    identity_type=identity_type,
                    identity_raw=identity_raw,
                    identity_normalized=identity_normalized,
                )
                .on_conflict_do_nothing(constraint="uq_enrollment_identity")
                .returning(cls.id)
            )
            inserted = session.execute(stmt).first()
            session.commit()
            return inserted is None
    