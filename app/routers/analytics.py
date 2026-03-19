from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from app.core.database import get_db
from app.models.threat import Threat, ThreatType, ThreatStatus
from app.models.company import Company
from app.models.organisation import Organisation
from app.models.campaign import Campaign, CampaignStatus
from app.models.threat_company import ThreatCompany

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ─────────────────────────────────────────────────────────────
# THREAT ANALYTICS
# ─────────────────────────────────────────────────────────────

@router.get("/threats/by-type")
async def threats_by_type(db: AsyncSession = Depends(get_db)):
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
        {
            "threat_type": row.threat_type,
            "count": row.count,
            "total_co2_tonnes": row.total_co2_tonnes,
            "avg_co2_tonnes": round(row.avg_co2_tonnes, 2),
        }
        for row in rows
    ]


@router.get("/threats/by-status")
async def threats_by_status(db: AsyncSession = Depends(get_db)):
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
        {
            "status": row.status,
            "count": row.count,
            "total_co2_tonnes": row.total_co2_tonnes,
        }
        for row in rows
    ]


@router.get("/threats/hotspots")
async def threat_hotspots(db: AsyncSession = Depends(get_db)):
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
        {
            "country": row.country,
            "threat_count": row.threat_count,
            "total_co2_tonnes": row.total_co2_tonnes,
            "total_land_affected_km2": row.total_land_affected_km2,
        }
        for row in rows
    ]


@router.get("/threats/co2-at-risk")
async def co2_at_risk(db: AsyncSession = Depends(get_db)):
    """
    Total projected CO2 emissions from all non-cancelled threats.
    The headline number — how much carbon is at stake across all tracked threats.
    """
    # All active/proposed threats
    result = await db.execute(
        select(
            func.coalesce(func.sum(Threat.estimated_co2_impact_tonnes), 0).label("total"),
            func.count(Threat.id).label("threat_count"),
        ).where(Threat.status.notin_([ThreatStatus.CANCELLED, ThreatStatus.SUSPENDED]))
    )
    row = result.one()

    # Breakdown by status
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

    return {
        "total_co2_at_risk_tonnes": row.total,
        "total_co2_at_risk_megatonnes": round(row.total / 1_000_000, 2),
        "active_threat_count": row.threat_count,
        "breakdown_by_status": [
            {
                "status": b.status,
                "co2_tonnes": b.co2_tonnes,
                "threat_count": b.count,
            }
            for b in breakdown
        ],
    }


# ─────────────────────────────────────────────────────────────
# COMPANY ANALYTICS
# ─────────────────────────────────────────────────────────────

@router.get("/companies/worst-offenders")
async def worst_offenders(db: AsyncSession = Depends(get_db)):
    """
    Companies ranked by combination of annual emissions,
    number of active threats they are linked to, and ESG score.
    """
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
        {
            "rank": i + 1,
            "company": row.name,
            "sector": row.sector,
            "country": row.country_of_registration,
            "annual_emissions_mtonnes": row.annual_emissions_mtonnes,
            "esg_score": row.esg_score,
            "is_paris_signatory": row.is_paris_signatory,
            "active_threat_count": row.active_threat_count,
        }
        for i, row in enumerate(rows)
    ]


# ─────────────────────────────────────────────────────────────
# CAMPAIGN / RESISTANCE ANALYTICS
# ─────────────────────────────────────────────────────────────

@router.get("/campaigns/success-rate")
async def campaign_success_rate(db: AsyncSession = Depends(get_db)):
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

    # Group by campaign type
    grouped = {}
    for row in rows:
        ct = row.campaign_type
        if ct not in grouped:
            grouped[ct] = {"campaign_type": ct, "outcomes": [], "total_signatures": 0}
        grouped[ct]["outcomes"].append({"status": row.status, "count": row.count})
        grouped[ct]["total_signatures"] += row.total_signatures

    return list(grouped.values())


@router.get("/resistance/coverage")
async def resistance_coverage(db: AsyncSession = Depends(get_db)):
    """
    What percentage of tracked threats have active opposition campaigns?
    Shows the gap between environmental harm and organised resistance.
    """
    # Total active threats
    total_result = await db.execute(
        select(func.count(Threat.id)).where(
            Threat.status.notin_([ThreatStatus.CANCELLED, ThreatStatus.SUSPENDED])
        )
    )
    total_threats = total_result.scalar()

    # Threats with at least one active campaign
    covered_result = await db.execute(
        select(func.count(func.distinct(Campaign.threat_id))).where(
            Campaign.status.in_([CampaignStatus.ACTIVE, CampaignStatus.ONGOING])
        )
    )
    covered_threats = covered_result.scalar()

    uncovered = total_threats - covered_threats
    coverage_pct = round((covered_threats / total_threats * 100), 1) if total_threats > 0 else 0

    return {
        "total_active_threats": total_threats,
        "threats_with_active_opposition": covered_threats,
        "threats_without_opposition": uncovered,
        "coverage_percentage": coverage_pct,
        "gap_analysis": (
            f"{uncovered} out of {total_threats} tracked threats currently have "
            f"no active opposition campaign — representing a critical organising gap."
        ),
    }


@router.get("/resistance/most-active-organisations")
async def most_active_organisations(db: AsyncSession = Depends(get_db)):
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
        {
            "rank": i + 1,
            "organisation": row.name,
            "org_type": row.org_type,
            "country": row.country,
            "member_count": row.member_count,
            "campaign_count": row.campaign_count,
            "total_signatures": row.total_signatures,
        }
        for i, row in enumerate(rows)
    ]


@router.get("/resistance/wins")
async def resistance_wins(db: AsyncSession = Depends(get_db)):
    """All campaigns that have been won — the victories worth celebrating."""
    result = await db.execute(
        select(Campaign, Organisation, Threat)
        .join(Organisation, Campaign.organisation_id == Organisation.id)
        .join(Threat, Campaign.threat_id == Threat.id)
        .where(Campaign.status == CampaignStatus.WON)
        .order_by(Campaign.end_date.desc())
    )
    rows = result.all()
    return [
        {
            "campaign": row.Campaign.campaign_name,
            "organisation": row.Organisation.name,
            "threat": row.Threat.name,
            "campaign_type": row.Campaign.campaign_type,
            "outcome_summary": row.Campaign.outcome_summary,
            "end_date": row.Campaign.end_date,
            "signatures": row.Campaign.signatures_count,
        }
        for row in rows
    ]


# ─────────────────────────────────────────────────────────────
# SUMMARY DASHBOARD
# ─────────────────────────────────────────────────────────────

@router.get("/summary")
async def summary(db: AsyncSession = Depends(get_db)):
    """
    High-level dashboard summary — the single endpoint that tells the
    full story of the climate threat landscape at a glance.
    """
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

    return {
        "threats": {
            "total": total_threats.scalar(),
            "total_co2_at_risk_megatonnes": round(co2_result.scalar() / 1_000_000, 2),
        },
        "corporate_actors": {
            "total_companies": total_companies.scalar(),
        },
        "resistance": {
            "total_organisations": total_organisations.scalar(),
            "total_campaigns": total_campaigns.scalar(),
            "active_campaigns": active_campaigns.scalar(),
            "campaigns_won": won_result.scalar(),
            "total_petition_signatures": total_signatures.scalar(),
        },
    }