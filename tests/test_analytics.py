import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_summary(client: AsyncClient):
    response = await client.get("/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "threats" in data
    assert "resistance" in data
    assert "corporate_actors" in data


@pytest.mark.asyncio
async def test_threats_by_type(client: AsyncClient):
    response = await client.get("/analytics/threats/by-type")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_threats_by_status(client: AsyncClient):
    response = await client.get("/analytics/threats/by-status")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_co2_at_risk(client: AsyncClient):
    response = await client.get("/analytics/threats/co2-at-risk")
    assert response.status_code == 200
    data = response.json()
    assert "total_co2_at_risk_tonnes" in data
    assert "total_co2_at_risk_megatonnes" in data
    assert "active_threat_count" in data


@pytest.mark.asyncio
async def test_hotspots(client: AsyncClient):
    response = await client.get("/analytics/threats/hotspots")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_worst_offenders(client: AsyncClient):
    response = await client.get("/analytics/companies/worst-offenders")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "rank" in data[0]
        assert "company" in data[0]


@pytest.mark.asyncio
async def test_resistance_coverage(client: AsyncClient):
    response = await client.get("/analytics/resistance/coverage")
    assert response.status_code == 200
    data = response.json()
    assert "coverage_percentage" in data
    assert "total_active_threats" in data
    assert "gap_analysis" in data


@pytest.mark.asyncio
async def test_campaign_success_rate(client: AsyncClient):
    response = await client.get("/analytics/campaigns/success-rate")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_resistance_wins(client: AsyncClient):
    response = await client.get("/analytics/resistance/wins")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    
@pytest.mark.asyncio
async def test_threat_risk_score(client: AsyncClient, auth_headers: dict):
    # Create a threat to test against
    create = await client.post("/threats/", json={
        "name": "Risk Score Test Threat",
        "threat_type": "PIPELINE",
        "status": "PROPOSED",
        "country": "Brazil",
        "region": "Amazon",
        "description": "Test threat for risk score endpoint",
        "estimated_co2_impact_tonnes": 250000000.0,
        "land_area_affected_km2": 500.0,
        "latitude": -5.0,
        "longitude": -60.0,
        "source_url": "https://example.com"
    }, headers=auth_headers)
    assert create.status_code == 201
    threat_id = create.json()["id"]

    response = await client.get(f"/analytics/threats/{threat_id}/risk-score")
    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data
    assert "risk_band" in data
    assert "breakdown" in data
    assert "methodology" in data
    assert data["risk_band"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert 0 <= data["risk_score"] <= 100
    assert "co2_score" in data["breakdown"]
    assert "corporate_exposure_score" in data["breakdown"]
    assert "resistance_gap_score" in data["breakdown"]
    assert "geographic_score" in data["breakdown"]


@pytest.mark.asyncio
async def test_threat_risk_score_not_found(client: AsyncClient):
    response = await client.get("/analytics/threats/nonexistent-id/risk-score")
    assert response.status_code == 404