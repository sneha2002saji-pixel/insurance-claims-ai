"""Shared pytest fixtures for the insurance agent test suite."""
from __future__ import annotations

import pytest


@pytest.fixture
def sample_claim() -> dict:
    """A minimal pending claim dict as returned by bigquery_client.get_claim."""
    return {
        "id": "claim-001",
        "claim_type": "AUTO",
        "claimant_name": "Jane Smith",
        "policy_number": "POL-2023-001",
        "amount": 3000.0,
        "incident_description": (
            "Vehicle was rear-ended at a traffic light causing damage to the bumper "
            "and trunk area. Police report filed. Two independent witnesses present."
        ),
        "document_refs": '["police_report.pdf", "repair_estimate.pdf", "photos.zip"]',
        "status": "pending",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }


@pytest.fixture
def hitl_claim() -> dict:
    """A claim that should trigger HITL (amount > $10k)."""
    return {
        "id": "claim-002",
        "claim_type": "HEALTH",
        "claimant_name": "Bob Jones",
        "policy_number": "POL-2023-002",
        "amount": 15000.0,
        "incident_description": (
            "Emergency hospitalisation following acute appendicitis. "
            "Surgery performed at City Hospital. Full itemised bill attached."
        ),
        "document_refs": '["hospital_discharge.pdf", "surgical_report.pdf", "itemized_bill.pdf"]',
        "status": "pending",
        "created_at": "2026-01-02T00:00:00+00:00",
        "updated_at": "2026-01-02T00:00:00+00:00",
    }


@pytest.fixture
def fraud_claim() -> dict:
    """A claim with high fraud risk indicators."""
    return {
        "id": "claim-003",
        "claim_type": "PROPERTY",
        "claimant_name": "Alice Brown",
        "policy_number": "POL-2024-003",
        "amount": 9000.0,
        "incident_description": (
            "Storm damage to roof. This is the third claim this year on this property."
        ),
        "document_refs": '["damage_photos.zip", "contractor_estimate.pdf", "weather_report.pdf"]',
        "status": "pending",
        "created_at": "2026-01-03T00:00:00+00:00",
        "updated_at": "2026-01-03T00:00:00+00:00",
    }
