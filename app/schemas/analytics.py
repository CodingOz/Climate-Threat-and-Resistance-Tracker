from pydantic import BaseModel
from typing import Optional
from app.models.threat import ThreatType, ThreatStatus
from app.models.campaign import CampaignType, CampaignStatus
from app.models.company import CompanySector
from app.models.organisation import OrgType
from datetime import date


# ─────────────────────────────────────────────────────────────
# THREAT ANALYTICS
# ─────────────────────────────────────────────────────────────

class ThreatByTypeResponse(BaseModel):
    threat_type: ThreatType
    count: int
    total_co2_tonnes: float
    avg_co2_tonnes: float


class ThreatByStatusResponse(BaseModel):
    status: ThreatStatus
    count: int
    total_co2_tonnes: float


class ThreatHotspotResponse(BaseModel):
    country: str
    threat_count: int
    total_co2_tonnes: float
    total_land_affected_km2: float


class CO2BreakdownItem(BaseModel):
    status: ThreatStatus
    co2_tonnes: float
    threat_count: int


class CO2AtRiskResponse(BaseModel):
    total_co2_at_risk_tonnes: float
    total_co2_at_risk_megatonnes: float
    active_threat_count: int
    breakdown_by_status: list[CO2BreakdownItem]


# ─────────────────────────────────────────────────────────────
# COMPANY ANALYTICS
# ─────────────────────────────────────────────────────────────

class WorstOffenderResponse(BaseModel):
    rank: int
    company: str
    sector: CompanySector
    country: str
    annual_emissions_mtonnes: Optional[float] = None
    esg_score: Optional[float] = None
    is_paris_signatory: bool
    active_threat_count: int


# ─────────────────────────────────────────────────────────────
# CAMPAIGN / RESISTANCE ANALYTICS
# ─────────────────────────────────────────────────────────────

class CampaignOutcomeItem(BaseModel):
    status: CampaignStatus
    count: int


class CampaignSuccessRateResponse(BaseModel):
    campaign_type: CampaignType
    outcomes: list[CampaignOutcomeItem]
    total_signatures: int


class ResistanceCoverageResponse(BaseModel):
    total_active_threats: int
    threats_with_active_opposition: int
    threats_without_opposition: int
    coverage_percentage: float
    gap_analysis: str


class MostActiveOrgResponse(BaseModel):
    rank: int
    organisation: str
    org_type: OrgType
    country: str
    member_count: Optional[int] = None
    campaign_count: int
    total_signatures: int


class ResistanceWinResponse(BaseModel):
    campaign: str
    organisation: str
    threat: str
    campaign_type: CampaignType
    outcome_summary: Optional[str] = None
    end_date: Optional[date] = None
    signatures: Optional[int] = None


# ─────────────────────────────────────────────────────────────
# SUMMARY DASHBOARD
# ─────────────────────────────────────────────────────────────

class ThreatSummary(BaseModel):
    total: int
    total_co2_at_risk_megatonnes: float


class CorporateSummary(BaseModel):
    total_companies: int


class ResistanceSummary(BaseModel):
    total_organisations: int
    total_campaigns: int
    active_campaigns: int
    campaigns_won: int
    total_petition_signatures: int


class SummaryResponse(BaseModel):
    threats: ThreatSummary
    corporate_actors: CorporateSummary
    resistance: ResistanceSummary
    


# ─────────────────────────────────────────────────────────────
# RISK ANALYSIS
# ─────────────────────────────────────────────────────────────

class RiskScoreBreakdown(BaseModel):
    co2_score: float
    corporate_exposure_score: float
    resistance_gap_score: float
    geographic_score: float


class ThreatRiskScoreResponse(BaseModel):
    threat_id: str
    threat_name: str
    risk_score: float
    risk_band: str
    breakdown: RiskScoreBreakdown
    methodology: str