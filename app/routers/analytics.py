from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.core.limiter import limiter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.threat import Threat, ThreatType, ThreatStatus
from app.models.company import Company
from app.models.organisation import Organisation
from app.models.campaign import Campaign, CampaignStatus
from app.models.threat_company import ThreatCompany
from app.schemas.analytics import (
    ThreatByTypeResponse, ThreatByStatusResponse, ThreatHotspotResponse,
    CO2AtRiskResponse, CO2BreakdownItem, WorstOffenderResponse,
    CampaignSuccessRateResponse, CampaignOutcomeItem, ResistanceCoverageResponse,
    MostActiveOrgResponse, ResistanceWinResponse, SummaryResponse,
    ThreatSummary, CorporateSummary, ResistanceSummary, RiskScoreBreakdown,
    ThreatRiskScoreResponse
)
from app.schemas.error import ErrorResponse

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/threats/by-type", response_model=list[ThreatByTypeResponse])
@limiter.limit("50/minute")
async def threats_by_type(request: Request, db: AsyncSession = Depends(get_db)):
    """Count of threats and total projected CO2 impact grouped by threat type."""
    result = await db.execute(
        select(
            Threat.threat_type,
            func.count(Threat.id).label("count"),
            func.coalesce(func.sum(Threat.estimated_co2_impact_tonnes), 0).label("total_co2_tonnes"),
            func.coalesce(func.avg(Threat.estimated_co2_impact_tonnes), 0).label("avg_co2_tonnes"),
        ).group_by(Threat.threat_type)
    )
    rows = result.all()
    return [
        ThreatByTypeResponse(
            threat_type=row.threat_type,
            count=row.count,
            total_co2_tonnes=row.total_co2_tonnes,
            avg_co2_tonnes=round(row.avg_co2_tonnes, 2),
        )
        for row in rows
    ]


@router.get("/threats/by-status", response_model=list[ThreatByStatusResponse])
@limiter.limit("50/minute")
async def threats_by_status(request: Request, db: AsyncSession = Depends(get_db)):
    """Count of threats at each stage of the approval/construction pipeline."""
    result = await db.execute(
        select(
            Threat.status,
            func.count(Threat.id).label("count"),
            func.coalesce(func.sum(Threat.estimated_co2_impact_tonnes), 0).label("total_co2_tonnes"),
        ).group_by(Threat.status)
    )
    rows = result.all()
    return [
        ThreatByStatusResponse(
            status=row.status,
            count=row.count,
            total_co2_tonnes=row.total_co2_tonnes,
        )
        for row in rows
    ]


@router.get("/threats/hotspots", response_model=list[ThreatHotspotResponse])
@limiter.limit("50/minute")
async def threat_hotspots(request: Request, db: AsyncSession = Depends(get_db)):
    """Countries ranked by number of active threats and total CO2 at risk."""
    result = await db.execute(
        select(
            Threat.country,
            func.count(Threat.id).label("threat_count"),
            func.coalesce(func.sum(Threat.estimated_co2_impact_tonnes), 0).label("total_co2_tonnes"),
            func.coalesce(func.sum(Threat.land_area_affected_km2), 0).label("total_land_affected_km2"),
        )
        .where(Threat.status.notin_([ThreatStatus.CANCELLED, ThreatStatus.SUSPENDED]))
        .group_by(Threat.country)
        .order_by(func.count(Threat.id).desc())
    )
    rows = result.all()
    return [
        ThreatHotspotResponse(
            country=row.country,
            threat_count=row.threat_count,
            total_co2_tonnes=row.total_co2_tonnes,
            total_land_affected_km2=row.total_land_affected_km2,
        )
        for row in rows
    ]


@router.get("/threats/co2-at-risk", response_model=CO2AtRiskResponse)
@limiter.limit("50/minute")
async def co2_at_risk(request: Request, db: AsyncSession = Depends(get_db)):
    """Total projected CO2 from all non-cancelled threats — the headline number."""
    result = await db.execute(
        select(
            func.coalesce(func.sum(Threat.estimated_co2_impact_tonnes), 0).label("total"),
            func.count(Threat.id).label("threat_count"),
        ).where(Threat.status.notin_([ThreatStatus.CANCELLED, ThreatStatus.SUSPENDED]))
    )
    row = result.one()

    breakdown_result = await db.execute(
        select(
            Threat.status,
            func.coalesce(func.sum(Threat.estimated_co2_impact_tonnes), 0).label("co2_tonnes"),
            func.count(Threat.id).label("count"),
        )
        .where(Threat.status.notin_([ThreatStatus.CANCELLED, ThreatStatus.SUSPENDED]))
        .group_by(Threat.status)
    )
    breakdown = breakdown_result.all()

    return CO2AtRiskResponse(
        total_co2_at_risk_tonnes=row.total,
        total_co2_at_risk_megatonnes=round(row.total / 1_000_000, 2),
        active_threat_count=row.threat_count,
        breakdown_by_status=[
            CO2BreakdownItem(
                status=b.status,
                co2_tonnes=b.co2_tonnes,
                threat_count=b.count,
            )
            for b in breakdown
        ],
    )


@router.get("/companies/worst-offenders", response_model=list[WorstOffenderResponse])
@limiter.limit("50/minute")
async def worst_offenders(request: Request, db: AsyncSession = Depends(get_db)):
    """Companies ranked by number of active threats they are linked to."""
    result = await db.execute(
        select(
            Company.id,
            Company.name,
            Company.sector,
            Company.country_of_registration,
            Company.annual_emissions_mtonnes,
            Company.esg_score,
            Company.is_paris_signatory,
            func.count(ThreatCompany.threat_id).label("active_threat_count"),
        )
        .outerjoin(ThreatCompany, ThreatCompany.company_id == Company.id)
        .group_by(Company.id)
        .order_by(func.count(ThreatCompany.threat_id).desc())
    )
    rows = result.all()
    return [
        WorstOffenderResponse(
            rank=i + 1,
            company=row.name,
            sector=row.sector,
            country=row.country_of_registration,
            annual_emissions_mtonnes=row.annual_emissions_mtonnes,
            esg_score=row.esg_score,
            is_paris_signatory=row.is_paris_signatory,
            active_threat_count=row.active_threat_count,
        )
        for i, row in enumerate(rows)
    ]


@router.get("/campaigns/success-rate", response_model=list[CampaignSuccessRateResponse])
@limiter.limit("50/minute")
async def campaign_success_rate(request: Request, db: AsyncSession = Depends(get_db)):
    """Win/loss/ongoing breakdown by campaign type."""
    result = await db.execute(
        select(
            Campaign.campaign_type,
            Campaign.status,
            func.count(Campaign.id).label("count"),
            func.coalesce(func.sum(Campaign.signatures_count), 0).label("total_signatures"),
        ).group_by(Campaign.campaign_type, Campaign.status)
    )
    rows = result.all()

    grouped = {}
    for row in rows:
        ct = row.campaign_type
        if ct not in grouped:
            grouped[ct] = {"campaign_type": ct, "outcomes": [], "total_signatures": 0}
        grouped[ct]["outcomes"].append(CampaignOutcomeItem(status=row.status, count=row.count))
        grouped[ct]["total_signatures"] += row.total_signatures

    return [
        CampaignSuccessRateResponse(**v)
        for v in grouped.values()
    ]


@router.get("/resistance/coverage", response_model=ResistanceCoverageResponse)
@limiter.limit("50/minute")
async def resistance_coverage(request: Request, db: AsyncSession = Depends(get_db)):
    """What percentage of tracked threats have active opposition campaigns?"""
    total_result = await db.execute(
        select(func.count(Threat.id)).where(
            Threat.status.notin_([ThreatStatus.CANCELLED, ThreatStatus.SUSPENDED])
        )
    )
    total_threats = total_result.scalar()

    covered_result = await db.execute(
        select(func.count(func.distinct(Campaign.threat_id))).where(
            Campaign.status.in_([CampaignStatus.ACTIVE, CampaignStatus.ONGOING])
        )
    )
    covered_threats = covered_result.scalar()
    uncovered = total_threats - covered_threats
    coverage_pct = round((covered_threats / total_threats * 100), 1) if total_threats > 0 else 0

    return ResistanceCoverageResponse(
        total_active_threats=total_threats,
        threats_with_active_opposition=covered_threats,
        threats_without_opposition=uncovered,
        coverage_percentage=coverage_pct,
        gap_analysis=(
            f"{uncovered} out of {total_threats} tracked threats currently have "
            f"no active opposition campaign — representing a critical organising gap."
        ),
    )


@router.get("/resistance/most-active-organisations", response_model=list[MostActiveOrgResponse])
@limiter.limit("50/minute")
async def most_active_organisations(request: Request, db: AsyncSession = Depends(get_db)):
    """Organisations ranked by number of campaigns and total petition signatures."""
    result = await db.execute(
        select(
            Organisation.id,
            Organisation.name,
            Organisation.org_type,
            Organisation.country,
            Organisation.member_count,
            func.count(Campaign.id).label("campaign_count"),
            func.coalesce(func.sum(Campaign.signatures_count), 0).label("total_signatures"),
        )
        .outerjoin(Campaign, Campaign.organisation_id == Organisation.id)
        .group_by(Organisation.id)
        .order_by(func.count(Campaign.id).desc())
    )
    rows = result.all()
    return [
        MostActiveOrgResponse(
            rank=i + 1,
            organisation=row.name,
            org_type=row.org_type,
            country=row.country,
            member_count=row.member_count,
            campaign_count=row.campaign_count,
            total_signatures=row.total_signatures,
        )
        for i, row in enumerate(rows)
    ]


@router.get("/resistance/wins", response_model=list[ResistanceWinResponse])
@limiter.limit("50/minute")
async def resistance_wins(request: Request, db: AsyncSession = Depends(get_db)):
    """All campaigns that have been won."""
    result = await db.execute(
        select(Campaign, Organisation, Threat)
        .join(Organisation, Campaign.organisation_id == Organisation.id)
        .join(Threat, Campaign.threat_id == Threat.id)
        .where(Campaign.status == CampaignStatus.WON)
        .order_by(Campaign.end_date.desc())
    )
    rows = result.all()
    return [
        ResistanceWinResponse(
            campaign=row.Campaign.campaign_name,
            organisation=row.Organisation.name,
            threat=row.Threat.name,
            campaign_type=row.Campaign.campaign_type,
            outcome_summary=row.Campaign.outcome_summary,
            end_date=row.Campaign.end_date,
            signatures=row.Campaign.signatures_count,
        )
        for row in rows
    ]


@router.get("/summary", response_model=SummaryResponse)
@limiter.limit("50/minute")
async def summary(request: Request, db: AsyncSession = Depends(get_db)):
    """High-level dashboard summary — the full story at a glance."""
    total_threats = await db.execute(select(func.count(Threat.id)))
    total_companies = await db.execute(select(func.count(Company.id)))
    total_organisations = await db.execute(select(func.count(Organisation.id)))
    total_campaigns = await db.execute(select(func.count(Campaign.id)))

    co2_result = await db.execute(
        select(func.coalesce(func.sum(Threat.estimated_co2_impact_tonnes), 0))
        .where(Threat.status.notin_([ThreatStatus.CANCELLED, ThreatStatus.SUSPENDED]))
    )
    won_result = await db.execute(
        select(func.count(Campaign.id)).where(Campaign.status == CampaignStatus.WON)
    )
    active_campaigns = await db.execute(
        select(func.count(Campaign.id)).where(
            Campaign.status.in_([CampaignStatus.ACTIVE, CampaignStatus.ONGOING])
        )
    )
    total_signatures = await db.execute(
        select(func.coalesce(func.sum(Campaign.signatures_count), 0))
    )

    return SummaryResponse(
        threats=ThreatSummary(
            total=total_threats.scalar(),
            total_co2_at_risk_megatonnes=round(co2_result.scalar() / 1_000_000, 2),
        ),
        corporate_actors=CorporateSummary(
            total_companies=total_companies.scalar(),
        ),
        resistance=ResistanceSummary(
            total_organisations=total_organisations.scalar(),
            total_campaigns=total_campaigns.scalar(),
            active_campaigns=active_campaigns.scalar(),
            campaigns_won=won_result.scalar(),
            total_petition_signatures=total_signatures.scalar(),
        ),
    )
    
# Geographic risk multipliers — regions with weaker regulation score higher
GEOGRAPHIC_RISK = {
    "United Kingdom": 0.6,
    "United States": 0.65,
    "Canada": 0.6,
    "Norway": 0.5,
    "France": 0.55,
    "Brazil": 0.9,
    "Uganda": 0.95,
    "Tanzania": 0.95,
}
GEOGRAPHIC_DEFAULT = 0.75


@router.get(
    "/threats/{threat_id}/risk-score",
    response_model=ThreatRiskScoreResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Composite risk score for a specific threat",
    description=(
        "Synthesises CO2 impact, number of linked corporate actors, "
        "active resistance campaign coverage, and geographic regulatory "
        "context into a single weighted risk score out of 100."
    )
)
@limiter.limit("60/minute")
async def threat_risk_score(
    request: Request,
    threat_id: str,
    db: AsyncSession = Depends(get_db)
):
    # Fetch the threat
    threat_result = await db.execute(select(Threat).where(Threat.id == threat_id))
    threat = threat_result.scalar_one_or_none()
    if not threat:
        raise HTTPException(status_code=404, detail="Threat not found")

    # --- CO2 Score (0-40 points) ---
    # Normalised against 500Mt as the upper bound (JBS Amazon case)
    MAX_CO2 = 500_000_000
    co2 = threat.estimated_co2_impact_tonnes or 0
    co2_score = round(min(co2 / MAX_CO2, 1.0) * 40, 2)

    # --- Corporate Exposure Score (0-25 points) ---
    # More companies involved = harder to stop, higher risk
    company_count_result = await db.execute(
        select(func.count(ThreatCompany.company_id))
        .where(ThreatCompany.threat_id == threat_id)
    )
    company_count = company_count_result.scalar() or 0
    # Caps at 5 companies for full score
    corporate_score = round(min(company_count / 5, 1.0) * 25, 2)

    # --- Resistance Gap Score (0-25 points) ---
    # No active campaigns = maximum risk score for this component
    # Active campaigns reduce the score — organised resistance lowers risk
    active_campaign_result = await db.execute(
        select(func.count(Campaign.id))
        .where(
            Campaign.threat_id == threat_id,
            Campaign.status.in_([CampaignStatus.ACTIVE, CampaignStatus.ONGOING])
        )
    )
    active_campaigns = active_campaign_result.scalar() or 0
    # More campaigns = lower resistance gap score
    resistance_gap_score = round(max(0, 1.0 - min(active_campaigns / 3, 1.0)) * 25, 2)

    # --- Geographic Score (0-10 points) ---
    # Regions with weaker regulatory environments score higher
    geo_multiplier = GEOGRAPHIC_RISK.get(threat.country, GEOGRAPHIC_DEFAULT)
    geographic_score = round(geo_multiplier * 10, 2)

    # --- Composite Score ---
    total_score = round(co2_score + corporate_score + resistance_gap_score + geographic_score, 2)

    # --- Risk Band ---
    if total_score >= 75:
        risk_band = "CRITICAL"
    elif total_score >= 50:
        risk_band = "HIGH"
    elif total_score >= 25:
        risk_band = "MEDIUM"
    else:
        risk_band = "LOW"

    return ThreatRiskScoreResponse(
        threat_id=threat_id,
        threat_name=threat.name,
        risk_score=total_score,
        risk_band=risk_band,
        breakdown=RiskScoreBreakdown(
            co2_score=co2_score,
            corporate_exposure_score=corporate_score,
            resistance_gap_score=resistance_gap_score,
            geographic_score=geographic_score,
        ),
        methodology=(
            "Score out of 100 composed of: CO2 impact (40pts, normalised against 500Mt upper bound), "
            "corporate exposure (25pts, number of linked companies capped at 5), "
            "resistance gap (25pts, reduced by active opposition campaigns), "
            "geographic regulatory risk (10pts, based on country regulatory context). "
            "Bands: LOW <25, MEDIUM 25-50, HIGH 50-75, CRITICAL 75+."
        )
    )