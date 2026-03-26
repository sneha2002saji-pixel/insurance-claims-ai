from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ClaimType(str, Enum):
    AUTO = "AUTO"
    HEALTH = "HEALTH"
    PROPERTY = "PROPERTY"


class ClaimStatus(str, Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    AGENT_APPROVED = "agent_approved"
    AWAITING_HUMAN_APPROVAL = "awaiting_human_approval"
    REJECTED = "rejected"
    PARTIAL_SETTLEMENT = "partial_settlement"
    SETTLED = "settled"


class AgentStage(str, Enum):
    DOCUMENT_VERIFICATION = "document_verification"
    FRAUD_DETECTION = "fraud_detection"
    CLAIM_VALIDATION = "claim_validation"
    DECISION = "decision"


class HumanDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PARTIAL_SETTLEMENT = "partial_settlement"


class HitlTriggerReason(str, Enum):
    HIGH_AMOUNT = "high_amount"
    HIGH_FRAUD_RISK = "high_fraud_risk"
    BOTH = "both"


class InsuranceClaim(BaseModel):
    """Represents a single insurance claim record as stored in BigQuery."""

    id: str
    claim_type: ClaimType
    claimant_name: str
    policy_number: str
    amount: float
    incident_description: str
    document_refs: list[str] = Field(default_factory=list)
    status: ClaimStatus = ClaimStatus.PENDING
    created_at: datetime
    updated_at: datetime


class CreateClaimRequest(BaseModel):
    """Validated payload for the POST /v1/claims endpoint."""

    claim_type: ClaimType
    claimant_name: str
    policy_number: str
    amount: float = Field(gt=0)
    incident_description: str
    document_refs: list[str] = Field(default_factory=list)


class AgentAnalysis(BaseModel):
    """Result row written to the agent_analyses BigQuery table after each pipeline stage."""

    id: str
    claim_id: str
    stage: AgentStage
    agent_name: str
    output_json: dict[str, Any]
    confidence_score: float = Field(ge=0.0, le=1.0)
    fraud_score: float | None = Field(default=None, ge=0.0, le=1.0)
    duration_ms: int
    created_at: datetime


class HumanApprovalRequest(BaseModel):
    """Row written to human_approval_requests when the pipeline triggers HITL."""

    id: str
    claim_id: str
    trigger_reason: HitlTriggerReason
    fraud_score: float
    amount: float
    assigned_to: str | None = None
    decision: HumanDecision | None = None
    adjuster_comment: str | None = None
    created_at: datetime
    decided_at: datetime | None = None


class HumanApprovalPayload(BaseModel):
    """Request body for the human adjuster decision endpoint."""

    decision: HumanDecision
    comment: str = Field(min_length=1)


class AgentEventType(str, Enum):
    THOUGHT = "thought"
    STAGE_START = "stage_start"
    STAGE_COMPLETE = "stage_complete"
    HITL_REQUIRED = "hitl_required"
    PIPELINE_COMPLETE = "pipeline_complete"
    ERROR = "error"


class AgentEvent(BaseModel):
    """Real-time event published to Redis pub/sub and streamed to the frontend via SSE."""

    type: AgentEventType
    stage: AgentStage
    content: str
    fraud_score: float | None = None
    final_status: ClaimStatus | None = None
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
