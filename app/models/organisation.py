import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Integer, DateTime, Date, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class OrgType(str, enum.Enum):
    GRASSROOTS = "GRASSROOTS"
    NGO = "NGO"
    LEGAL_COALITION = "LEGAL_COALITION"
    INDIGENOUS_GROUP = "INDIGENOUS_GROUP"
    INTERNATIONAL = "INTERNATIONAL"
    POLITICAL_PARTY = "POLITICAL_PARTY"


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    org_type: Mapped[OrgType] = mapped_column(SAEnum(OrgType), nullable=False)
    country: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    founding_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    member_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)

    # Relationship to campaigns
    campaigns: Mapped[list["Campaign"]] = relationship(
        "Campaign", back_populates="organisation", cascade="all, delete-orphan"
    )
    