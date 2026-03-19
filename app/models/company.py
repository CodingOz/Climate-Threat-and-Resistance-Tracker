import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class CompanySector(str, enum.Enum):
    OIL_GAS = "OIL_GAS"
    AGRICULTURE = "AGRICULTURE"
    MINING = "MINING"
    AVIATION = "AVIATION"
    SHIPPING = "SHIPPING"
    ENERGY = "ENERGY"
    MANUFACTURING = "MANUFACTURING"


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    sector: Mapped[CompanySector] = mapped_column(SAEnum(CompanySector), nullable=False)
    country_of_registration: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    esg_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    annual_emissions_mtonnes: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_paris_signatory: Mapped[bool] = mapped_column(Boolean, default=False)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship to junction table
    threat_associations: Mapped[list["ThreatCompany"]] = relationship(
        "ThreatCompany", back_populates="company", cascade="all, delete-orphan"
    )
    