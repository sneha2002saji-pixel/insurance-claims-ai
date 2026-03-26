"""Unit tests for models/claim.py — enums, Pydantic validation."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from models.claim import (
    AgentEventType,
    AgentStage,
    ClaimStatus,
    ClaimType,
    CreateClaimRequest,
    HumanApprovalPayload,
    HumanDecision,
    HitlTriggerReason,
)


# ---------------------------------------------------------------------------
# ClaimStatus enum
# ---------------------------------------------------------------------------


def test_claim_status_pending_value() -> None:
    assert ClaimStatus.PENDING.value == "pending"


def test_claim_status_under_review_value() -> None:
    assert ClaimStatus.UNDER_REVIEW.value == "under_review"


def test_claim_status_agent_approved_value() -> None:
    assert ClaimStatus.AGENT_APPROVED.value == "agent_approved"


def test_claim_status_awaiting_human_approval_value() -> None:
    assert ClaimStatus.AWAITING_HUMAN_APPROVAL.value == "awaiting_human_approval"


def test_claim_status_rejected_value() -> None:
    assert ClaimStatus.REJECTED.value == "rejected"


def test_claim_status_partial_settlement_value() -> None:
    assert ClaimStatus.PARTIAL_SETTLEMENT.value == "partial_settlement"


def test_claim_status_settled_value() -> None:
    assert ClaimStatus.SETTLED.value == "settled"


def test_claim_status_all_members_present() -> None:
    """Ensure the seven expected status values are all defined."""
    expected = {
        "pending", "under_review", "agent_approved", "awaiting_human_approval",
        "rejected", "partial_settlement", "settled",
    }
    actual = {s.value for s in ClaimStatus}
    assert actual == expected


# ---------------------------------------------------------------------------
# ClaimType enum
# ---------------------------------------------------------------------------


def test_claim_type_values() -> None:
    assert ClaimType.AUTO.value == "AUTO"
    assert ClaimType.HEALTH.value == "HEALTH"
    assert ClaimType.PROPERTY.value == "PROPERTY"


# ---------------------------------------------------------------------------
# AgentStage enum
# ---------------------------------------------------------------------------


def test_agent_stage_values() -> None:
    assert AgentStage.DOCUMENT_VERIFICATION.value == "document_verification"
    assert AgentStage.FRAUD_DETECTION.value == "fraud_detection"
    assert AgentStage.CLAIM_VALIDATION.value == "claim_validation"
    assert AgentStage.DECISION.value == "decision"


# ---------------------------------------------------------------------------
# AgentEventType enum
# ---------------------------------------------------------------------------


def test_agent_event_type_thought() -> None:
    assert AgentEventType.THOUGHT.value == "thought"


def test_agent_event_type_stage_start() -> None:
    assert AgentEventType.STAGE_START.value == "stage_start"


def test_agent_event_type_stage_complete() -> None:
    assert AgentEventType.STAGE_COMPLETE.value == "stage_complete"


def test_agent_event_type_hitl_required() -> None:
    assert AgentEventType.HITL_REQUIRED.value == "hitl_required"


def test_agent_event_type_pipeline_complete() -> None:
    assert AgentEventType.PIPELINE_COMPLETE.value == "pipeline_complete"


def test_agent_event_type_error() -> None:
    assert AgentEventType.ERROR.value == "error"


# ---------------------------------------------------------------------------
# HumanDecision enum
# ---------------------------------------------------------------------------


def test_human_decision_approved() -> None:
    assert HumanDecision.APPROVED.value == "approved"


def test_human_decision_rejected() -> None:
    assert HumanDecision.REJECTED.value == "rejected"


def test_human_decision_partial_settlement() -> None:
    assert HumanDecision.PARTIAL_SETTLEMENT.value == "partial_settlement"


# ---------------------------------------------------------------------------
# HitlTriggerReason enum
# ---------------------------------------------------------------------------


def test_hitl_trigger_reason_values() -> None:
    assert HitlTriggerReason.HIGH_AMOUNT.value == "high_amount"
    assert HitlTriggerReason.HIGH_FRAUD_RISK.value == "high_fraud_risk"
    assert HitlTriggerReason.BOTH.value == "both"


# ---------------------------------------------------------------------------
# CreateClaimRequest — Pydantic validation
# ---------------------------------------------------------------------------


def _valid_claim_payload(**overrides) -> dict:
    base = {
        "claim_type": "AUTO",
        "claimant_name": "Jane Smith",
        "policy_number": "POL-2024-001",
        "amount": 5000.0,
        "incident_description": "Rear-end collision at a traffic light.",
        "document_refs": ["police_report.pdf"],
    }
    base.update(overrides)
    return base


def test_create_claim_request_valid() -> None:
    """A fully valid payload is accepted without error."""
    req = CreateClaimRequest(**_valid_claim_payload())
    assert req.claimant_name == "Jane Smith"
    assert req.amount == 5000.0
    assert req.claim_type == ClaimType.AUTO


def test_create_claim_request_amount_must_be_positive() -> None:
    """amount <= 0 raises a ValidationError (Field gt=0)."""
    with pytest.raises(ValidationError) as exc_info:
        CreateClaimRequest(**_valid_claim_payload(amount=0.0))
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("amount",) for e in errors)


def test_create_claim_request_negative_amount_rejected() -> None:
    """Negative amount is rejected."""
    with pytest.raises(ValidationError):
        CreateClaimRequest(**_valid_claim_payload(amount=-1.0))


def test_create_claim_request_document_refs_default_empty() -> None:
    """document_refs has a default of empty list when omitted."""
    payload = _valid_claim_payload()
    del payload["document_refs"]
    req = CreateClaimRequest(**payload)
    assert req.document_refs == []


def test_create_claim_request_invalid_claim_type() -> None:
    """An unrecognised claim_type is rejected with a ValidationError."""
    with pytest.raises(ValidationError):
        CreateClaimRequest(**_valid_claim_payload(claim_type="LIFE"))


def test_create_claim_request_health_type() -> None:
    """HEALTH claim type is accepted."""
    req = CreateClaimRequest(**_valid_claim_payload(claim_type="HEALTH", amount=12000.0))
    assert req.claim_type == ClaimType.HEALTH


def test_create_claim_request_property_type() -> None:
    """PROPERTY claim type is accepted."""
    req = CreateClaimRequest(**_valid_claim_payload(claim_type="PROPERTY", amount=8500.0))
    assert req.claim_type == ClaimType.PROPERTY


# ---------------------------------------------------------------------------
# HumanApprovalPayload — Pydantic validation
# ---------------------------------------------------------------------------


def test_human_approval_payload_approved_valid() -> None:
    """Approved decision with a non-empty comment is accepted."""
    payload = HumanApprovalPayload(decision="approved", comment="All checks passed.")
    assert payload.decision == HumanDecision.APPROVED
    assert payload.comment == "All checks passed."


def test_human_approval_payload_rejected_valid() -> None:
    """Rejected decision with a comment is accepted."""
    payload = HumanApprovalPayload(decision="rejected", comment="Fraud indicators present.")
    assert payload.decision == HumanDecision.REJECTED


def test_human_approval_payload_partial_settlement_valid() -> None:
    """Partial settlement decision is accepted."""
    payload = HumanApprovalPayload(
        decision="partial_settlement", comment="Partial coverage applies."
    )
    assert payload.decision == HumanDecision.PARTIAL_SETTLEMENT


def test_human_approval_payload_empty_comment_rejected() -> None:
    """Empty string comment violates min_length=1 and raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        HumanApprovalPayload(decision="approved", comment="")
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("comment",) for e in errors)


def test_human_approval_payload_invalid_decision_rejected() -> None:
    """An unrecognised decision value raises a ValidationError."""
    with pytest.raises(ValidationError):
        HumanApprovalPayload(decision="escalate", comment="Escalating.")


def test_human_approval_payload_missing_comment_rejected() -> None:
    """Missing comment field raises ValidationError."""
    with pytest.raises(ValidationError):
        HumanApprovalPayload(decision="approved")
