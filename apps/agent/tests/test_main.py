"""Integration tests for FastAPI routes in main.py (uses httpx.AsyncClient)."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app

# ---------------------------------------------------------------------------
# Shared client fixture
# ---------------------------------------------------------------------------

BASE_URL = "http://test"


@pytest.fixture
async def client() -> AsyncClient:
    """Return an httpx AsyncClient wired to the FastAPI app under test."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=BASE_URL
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# GET /claims
# ---------------------------------------------------------------------------


async def test_list_claims_returns_envelope(client: AsyncClient) -> None:
    """GET /claims returns 200 with a data list and pagination envelope."""
    mock_claims = [
        {"id": "c1", "status": "pending"},
        {"id": "c2", "status": "agent_approved"},
    ]

    with patch("main.bq.list_claims", AsyncMock(return_value=mock_claims)):
        response = await client.get("/claims")

    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "pagination" in body
    assert body["data"] == mock_claims
    assert body["pagination"]["total"] == 2


# ---------------------------------------------------------------------------
# POST /claims
# ---------------------------------------------------------------------------


async def test_create_claim_persists_and_returns_id(client: AsyncClient) -> None:
    """POST /claims returns 201 with id and status=pending."""
    mock_insert = AsyncMock()
    mock_audit = AsyncMock()

    payload = {
        "claim_type": "AUTO",
        "claimant_name": "Jane Smith",
        "policy_number": "POL-001",
        "amount": 3000.0,
        "incident_description": "Rear-end collision at traffic light.",
        "document_refs": ["police_report.pdf"],
    }

    with (
        patch("main.bq.insert_claim", mock_insert),
        patch("main.bq.insert_audit_log", mock_audit),
    ):
        response = await client.post("/claims", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["status"] == "pending"
    mock_insert.assert_called_once()
    mock_audit.assert_called_once()


async def test_create_claim_rejects_zero_amount(client: AsyncClient) -> None:
    """POST /claims with amount <= 0 returns 422 validation error."""
    payload = {
        "claim_type": "AUTO",
        "claimant_name": "Jane Smith",
        "policy_number": "POL-001",
        "amount": 0.0,
        "incident_description": "Collision.",
        "document_refs": [],
    }

    response = await client.post("/claims", json=payload)
    assert response.status_code == 422


async def test_create_claim_rejects_negative_amount(client: AsyncClient) -> None:
    """POST /claims with negative amount returns 422 validation error."""
    payload = {
        "claim_type": "HEALTH",
        "claimant_name": "Bob",
        "policy_number": "POL-002",
        "amount": -500.0,
        "incident_description": "Hospital visit.",
        "document_refs": [],
    }

    response = await client.post("/claims", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /claims/{id}
# ---------------------------------------------------------------------------


async def test_get_claim_not_found(client: AsyncClient) -> None:
    """GET /claims/{id} returns 404 when bigquery_client.get_claim returns None."""
    with patch("main.bq.get_claim", AsyncMock(return_value=None)):
        response = await client.get("/claims/nonexistent-id")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_get_claim_found(client: AsyncClient) -> None:
    """GET /claims/{id} returns 200 with the full claim dict when found."""
    mock_claim = {
        "id": "claim-001",
        "claim_type": "AUTO",
        "status": "pending",
        "amount": 3000.0,
    }

    with patch("main.bq.get_claim", AsyncMock(return_value=mock_claim)):
        response = await client.get("/claims/claim-001")

    assert response.status_code == 200
    assert response.json() == mock_claim


# ---------------------------------------------------------------------------
# POST /claims/{id}/run
# ---------------------------------------------------------------------------


async def test_run_pipeline_claim_not_pending_returns_409(client: AsyncClient) -> None:
    """POST /claims/{id}/run returns 409 when claim is not in pending status."""
    mock_claim = {
        "id": "claim-001",
        "status": "agent_approved",
        "amount": 3000.0,
    }

    with patch("main.bq.get_claim", AsyncMock(return_value=mock_claim)):
        response = await client.post("/claims/claim-001/run")

    assert response.status_code == 409
    assert "agent_approved" in response.json()["detail"]


async def test_run_pipeline_claim_not_found_returns_404(client: AsyncClient) -> None:
    """POST /claims/{id}/run returns 404 when claim does not exist."""
    with patch("main.bq.get_claim", AsyncMock(return_value=None)):
        response = await client.post("/claims/missing-id/run")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /claims/{id}/resume
# ---------------------------------------------------------------------------


async def test_resume_claim_not_awaiting_returns_409(client: AsyncClient) -> None:
    """POST /claims/{id}/resume returns 409 when claim is not awaiting human approval."""
    mock_claim = {
        "id": "claim-002",
        "status": "pending",
        "amount": 15000.0,
    }

    payload = {"decision": "approved", "comment": "Looks good."}

    with patch("main.bq.get_claim", AsyncMock(return_value=mock_claim)):
        response = await client.post("/claims/claim-002/resume", json=payload)

    assert response.status_code == 409
    assert "not awaiting" in response.json()["detail"].lower()


async def test_resume_claim_not_found_returns_404(client: AsyncClient) -> None:
    """POST /claims/{id}/resume returns 404 when claim does not exist."""
    payload = {"decision": "approved", "comment": "Approved."}

    with patch("main.bq.get_claim", AsyncMock(return_value=None)):
        response = await client.post("/claims/ghost-id/resume", json=payload)

    assert response.status_code == 404


async def test_resume_claim_records_human_decision(client: AsyncClient) -> None:
    """POST /claims/{id}/resume records approval and returns new_status=agent_approved."""
    mock_claim = {
        "id": "claim-002",
        "status": "awaiting_human_approval",
        "amount": 15000.0,
    }

    mock_update_hitl = AsyncMock()
    mock_update_status = AsyncMock()
    mock_audit = AsyncMock()

    payload = {"decision": "approved", "comment": "All documents verified by adjuster."}

    with (
        patch("main.bq.get_claim", AsyncMock(return_value=mock_claim)),
        patch("main.bq.update_hitl_decision", mock_update_hitl),
        patch("main.bq.update_claim_status", mock_update_status),
        patch("main.bq.insert_audit_log", mock_audit),
    ):
        response = await client.post("/claims/claim-002/resume", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["new_status"] == "agent_approved"
    assert body["decision"] == "approved"
    assert body["claim_id"] == "claim-002"
    mock_update_hitl.assert_called_once()
    mock_update_status.assert_called_once_with("claim-002", "agent_approved")
    mock_audit.assert_called_once()


async def test_resume_claim_rejected_decision(client: AsyncClient) -> None:
    """POST /claims/{id}/resume with rejected decision returns new_status=rejected."""
    mock_claim = {
        "id": "claim-003",
        "status": "awaiting_human_approval",
        "amount": 9000.0,
    }

    payload = {"decision": "rejected", "comment": "Fraudulent claim indicators found."}

    with (
        patch("main.bq.get_claim", AsyncMock(return_value=mock_claim)),
        patch("main.bq.update_hitl_decision", AsyncMock()),
        patch("main.bq.update_claim_status", AsyncMock()),
        patch("main.bq.insert_audit_log", AsyncMock()),
    ):
        response = await client.post("/claims/claim-003/resume", json=payload)

    assert response.status_code == 200
    assert response.json()["new_status"] == "rejected"


async def test_resume_claim_partial_settlement(client: AsyncClient) -> None:
    """POST /claims/{id}/resume with partial_settlement returns new_status=partial_settlement."""
    mock_claim = {
        "id": "claim-004",
        "status": "awaiting_human_approval",
        "amount": 8000.0,
    }

    payload = {"decision": "partial_settlement", "comment": "Partial coverage applies."}

    with (
        patch("main.bq.get_claim", AsyncMock(return_value=mock_claim)),
        patch("main.bq.update_hitl_decision", AsyncMock()),
        patch("main.bq.update_claim_status", AsyncMock()),
        patch("main.bq.insert_audit_log", AsyncMock()),
    ):
        response = await client.post("/claims/claim-004/resume", json=payload)

    assert response.status_code == 200
    assert response.json()["new_status"] == "partial_settlement"


# ---------------------------------------------------------------------------
# Health probes
# ---------------------------------------------------------------------------


async def test_healthz(client: AsyncClient) -> None:
    """GET /healthz returns 200 {"status": "ok"}."""
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readyz(client: AsyncClient) -> None:
    """GET /readyz returns 200 {"status": "ok"}."""
    response = await client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
