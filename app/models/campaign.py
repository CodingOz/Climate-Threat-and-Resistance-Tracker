import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Integer, ForeignKey, DateTime, Date, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class CampaignType(str, enum.Enum):
    LEGAL_CHALLENGE = "LEGAL_CHALLENGE"
    PROTEST = "PROTEST"
    PETITION = "PETITION"
    LOBBYING = "LOBBYING"
    DIRECT_ACTION = "DIRECT_ACTION"
    MEDIA_CAMPAIGN = "MEDIA_CAMPAIGN"


class CampaignStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    WON = "WON"
    LOST = "LOST"
    ONGOING = "ONGOING"
    SUSPENDED = "SUSPENDED"


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_name: Mapped[str] = mapped_column(String, nullable=False)
    campaign_type: Mapped[CampaignType] = mapped_column(SAEnum(CampaignType), nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(SAEnum(CampaignStatus), nullable=False, default=CampaignStatus.ACTIVE)
    organisation_id: Mapped[str] = mapped_column(String, ForeignKey("organisations.id"), nullable=False)
    threat_id: Mapped[str] = mapped_column(String, ForeignKey("threats.id"), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    outcome_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    signatures_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    # Relationships
    organisation: Mapped["Organisation"] = relationship("Organisation", back_populates="campaigns")
    threat: Mapped["Threat"] = relationship("Threat", back_populates="campaigns")