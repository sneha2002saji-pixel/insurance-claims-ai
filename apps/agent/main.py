from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from models.claim import AgentEventType, ClaimStatus, CreateClaimRequest, HumanApprovalPayload
from pipeline import run_pipeline
from services import bigquery_client as bq
from services.redis_client import create_subscription, yield_events

logger = structlog.get_logger(__name__)

app = FastAPI(title="Insurance Claims Agent", version="0.1.0")

_ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Map HumanDecision string values to ClaimStatus string values.
# HumanDecision.APPROVED -> "approved", but the ClaimStatus is "agent_approved".
_HUMAN_DECISION_TO_STATUS: dict[str, str] = {
    "approved": ClaimStatus.AGENT_APPROVED.value,
    "rejected": ClaimStatus.REJECTED.value,
    "partial_settlement": ClaimStatus.PARTIAL_SETTLEMENT.value,
}


@app.get("/healthz")
async def healthz() -> dict:
    """Liveness probe — always returns 200 if the process is running."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict:
    """Readiness probe — always returns 200; extend with BQ/Redis checks if needed."""
    return {"status": "ok"}


@app.get("/claims")
async def list_claims() -> dict:
    """List all claims ordered by created_at descending (max 50).

    Returns:
        JSON envelope with ``data`` list and ``pagination`` metadata.
    """
    claims = await bq.list_claims(limit=50)
    return {
        "data": claims,
        "pagination": {"hasMore": False, "total": len(claims)},
    }


@app.post("/claims", status_code=201)
async def create_claim(request: CreateClaimRequest) -> dict:
    """Create a new insurance claim and persist it to BigQuery.

    Args:
        request: Validated CreateClaimRequest body.

    Returns:
        Dict with ``id`` and initial ``status``.
    """
    claim_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    claim: dict = {
        "id": claim_id,
        "claim_type": request.claim_type.value,
        "claimant_name": request.claimant_name,
        "policy_number": request.policy_number,
        "amount": request.amount,
        "incident_description": request.incident_description,
        # Serialise as JSON string to match the BQ STRING column
        "document_refs": json.dumps(request.document_refs),
        "status": ClaimStatus.PENDING.value,
        "created_at": now,
        "updated_at": now,
    }
    await bq.insert_claim(claim)
    await bq.insert_audit_log({
        "id": str(uuid.uuid4()),
        "claim_id": claim_id,
        "event_type": "claim_created",
        "previous_status": None,
        "new_status": ClaimStatus.PENDING.value,
        "actor": "api",
        "details_json": json.dumps({"claim_type": request.claim_type.value}),
        "created_at": now,
    })
    return {"id": claim_id, "status": ClaimStatus.PENDING.value}


@app.get("/claims/{claim_id}")
async def get_claim(claim_id: str) -> dict:
    """Fetch a single claim by ID.

    Args:
        claim_id: UUID string.

    Returns:
        Full claim row as a dict.

    Raises:
        HTTPException 404: If the claim does not exist.
    """
    claim = await bq.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@app.post("/claims/{claim_id}/run")
async def run_claim_pipeline(claim_id: str) -> StreamingResponse:
    """Start the 4-stage agent pipeline for a claim and stream events as SSE.

    The pipeline runs in a background asyncio task. The route returns an
    ``text/event-stream`` response that replays Redis pub/sub events until the
    pipeline reaches a terminal state (``pipeline_complete``, ``hitl_required``,
    or ``error``).

    Args:
        claim_id: UUID of the claim to process.

    Returns:
        StreamingResponse with ``text/event-stream`` content type.

    Raises:
        HTTPException 404: Claim not found.
        HTTPException 409: Claim is not in PENDING status.
    """
    claim = await bq.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim["status"] != ClaimStatus.PENDING.value:
        raise HTTPException(
            status_code=409,
            detail=f"Claim is already in status: {claim['status']}",
        )

    # Terminal event types that signal the SSE stream should close
    _terminal_types = frozenset({
        AgentEventType.PIPELINE_COMPLETE.value,
        AgentEventType.HITL_REQUIRED.value,
        AgentEventType.ERROR.value,
    })

    async def event_stream():
        """Yield SSE-formatted event lines until the pipeline finishes."""
        # create_subscription is a plain coroutine — it establishes the Redis
        # subscription immediately (before create_task), so no early events
        # published by the pipeline can be missed.
        redis_client, pubsub = await create_subscription(claim_id)
        pipeline_task = asyncio.create_task(run_pipeline(claim_id, claim))

        try:
            async for event in yield_events(redis_client, pubsub, claim_id):
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") in _terminal_types:
                    break
        finally:
            # Wait briefly for the pipeline task to flush final BQ writes
            try:
                # shield prevents the pipeline task from being cancelled if the
                # client disconnects and FastAPI propagates CancelledError here,
                # ensuring final BQ writes and audit log entries always complete.
                await asyncio.wait_for(asyncio.shield(pipeline_task), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("pipeline_task_timeout", claim_id=claim_id)
            except Exception as exc:  # noqa: BLE001
                # Pipeline already published an ERROR event to Redis; log here
                # so the exception is visible in Cloud Run logs.
                logger.error("pipeline_task_error", claim_id=claim_id, exc_info=exc)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/claims/{claim_id}/resume")
async def resume_claim(claim_id: str, payload: HumanApprovalPayload) -> dict:
    """Record a human adjuster's decision on a HITL-paused claim.

    Updates both ``human_approval_requests`` and ``insurance_claims`` tables
    and writes an audit log entry.

    Args:
        claim_id: UUID of the claim to resume.
        payload: HumanApprovalPayload with ``decision`` and ``comment``.

    Returns:
        Dict with ``claim_id``, ``new_status``, and ``decision``.

    Raises:
        HTTPException 404: Claim not found.
        HTTPException 409: Claim is not in AWAITING_HUMAN_APPROVAL status.
        HTTPException 400: Unrecognised decision value (should not occur with
            a validated Pydantic model but included for safety).
    """
    claim = await bq.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim["status"] != ClaimStatus.AWAITING_HUMAN_APPROVAL.value:
        raise HTTPException(
            status_code=409,
            detail="Claim is not awaiting human approval",
        )

    decision_str = payload.decision.value  # e.g. "approved"
    new_status = _HUMAN_DECISION_TO_STATUS.get(decision_str)
    if not new_status:
        raise HTTPException(
            status_code=400,
            detail=f"Unrecognised decision value: {decision_str}",
        )

    now = datetime.now(timezone.utc).isoformat()

    await bq.update_hitl_decision(claim_id, decision_str, payload.comment)
    await bq.update_claim_status(claim_id, new_status)
    await bq.insert_audit_log({
        "id": str(uuid.uuid4()),
        "claim_id": claim_id,
        "event_type": "human_decision",
        "previous_status": ClaimStatus.AWAITING_HUMAN_APPROVAL.value,
        "new_status": new_status,
        "actor": "human-adjuster",
        "details_json": json.dumps(
            {"decision": decision_str, "comment": payload.comment}
        ),
        "created_at": now,
    })

    logger.info(
        "human_decision_recorded",
        claim_id=claim_id,
        decision=decision_str,
        new_status=new_status,
    )
    return {
        "claim_id": claim_id,
        "new_status": new_status,
        "decision": decision_str,
    }
