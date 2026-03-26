from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from agents import (
    build_claim_validation_agent,
    build_decision_agent,
    build_document_verification_agent,
    build_fraud_detection_agent,
)
from models.claim import AgentEventType, AgentStage, ClaimStatus
from services import bigquery_client as bq
from services.redis_client import publish_event

logger = structlog.get_logger(__name__)

APP_NAME = "insurance-claims-pipeline"
USER_ID = "pipeline-system"


async def _publish(
    claim_id: str,
    event_type: str,
    stage: str,
    content: str,
    **kwargs: Any,
) -> None:
    """Publish an agent event dict to the Redis channel for this claim.

    Args:
        claim_id: UUID of the claim being processed.
        event_type: One of the AgentEventType string values.
        stage: One of the AgentStage string values.
        content: Human-readable event description or agent text output.
        **kwargs: Any additional fields to merge into the event payload.
    """
    event: dict[str, Any] = {
        "type": event_type,
        "stage": stage,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **kwargs,
    }
    await publish_event(claim_id, event)


def _extract_json(text: str) -> dict[str, Any]:
    """Extract and parse the first JSON object from an agent response string.

    Handles responses wrapped in markdown code fences (```json ... ```) as well
    as bare JSON.  Falls back to a raw_response dict on any parse failure.

    Args:
        text: Raw text output from an ADK agent run.

    Returns:
        Parsed dict, or {"raw_response": text} if parsing fails.
    """
    cleaned = text.strip()

    # Strip markdown JSON fence if present
    if "```json" in cleaned:
        try:
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
        except IndexError:
            pass
    elif "```" in cleaned:
        try:
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
        except IndexError:
            pass

    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
        return {"raw_response": text}
    except json.JSONDecodeError:
        return {"raw_response": text}


async def _run_agent_stage(
    runner: Runner,
    session_id: str,
    stage: AgentStage,
    prompt: str,
    claim_id: str,
) -> tuple[str, dict[str, Any]]:
    """Run a single agent stage, stream events to Redis, and persist to BigQuery.

    Thought parts (part.thought == True) are forwarded to the frontend as
    THOUGHT events but are never re-injected into subsequent turns.

    Args:
        runner: Configured ADK Runner wrapping the agent.
        session_id: Shared session identifier for the full pipeline run.
        stage: The AgentStage enum value identifying this pipeline step.
        prompt: User-turn prompt text containing claim context and prior findings.
        claim_id: UUID of the claim being processed.

    Returns:
        Tuple of (full_text_response, parsed_output_dict).

    Raises:
        RuntimeError: If the BigQuery insert fails.
    """
    stage_value = stage.value
    await _publish(
        claim_id,
        AgentEventType.STAGE_START,
        stage_value,
        f"Starting {stage_value.replace('_', ' ').title()}...",
    )

    start_ts = time.monotonic()
    full_response = ""

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=prompt)],
        ),
    ):
        if not event.content:
            continue
        for part in event.content.parts:
            # Thought tokens: display-only, never re-injected
            if getattr(part, "thought", False) and part.text:
                await _publish(
                    claim_id, AgentEventType.THOUGHT, stage_value, part.text
                )
            elif part.text:
                full_response += part.text

    duration_ms = int((time.monotonic() - start_ts) * 1_000)
    parsed = _extract_json(full_response)

    if "raw_response" in parsed:
        logger.warning(
            "agent_response_not_json",
            stage=stage_value,
            claim_id=claim_id,
            preview=full_response[:200],
        )

    await _publish(
        claim_id, AgentEventType.STAGE_COMPLETE, stage_value, full_response
    )

    # Derive a clean agent class name from the stage value
    # e.g. "document_verification" -> "DocumentVerificationAgent"
    agent_name = (
        "".join(word.capitalize() for word in stage_value.split("_")) + "Agent"
    )

    await bq.insert_agent_analysis({
        "id": str(uuid.uuid4()),
        "claim_id": claim_id,
        "stage": stage_value,
        "agent_name": agent_name,
        "output_json": json.dumps(parsed),
        "confidence_score": float(parsed["confidence_score"]) if "confidence_score" in parsed else None,
        "fraud_score": (
            float(parsed["fraud_score"]) if "fraud_score" in parsed else None
        ),
        "duration_ms": duration_ms,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    logger.info(
        "stage_complete",
        stage=stage_value,
        claim_id=claim_id,
        duration_ms=duration_ms,
    )
    return full_response, parsed


async def run_pipeline(claim_id: str, claim_data: dict[str, Any]) -> None:
    """Run the full 4-stage agent pipeline for an insurance claim.

    Pipeline stages (sequential):
      1. DocumentVerificationAgent  — completeness + authenticity checks
      2. FraudDetectionAgent        — fraud pattern scoring
      3. ClaimValidationAgent       — policy coverage + type-specific rules
      4. DecisionAgent              — final decision or HITL trigger

    Publishes AgentEvent dicts to Redis throughout execution.
    Persists stage results to BigQuery agent_analyses after each stage.
    On HITL trigger, writes to human_approval_requests and sets status to
    awaiting_human_approval. Otherwise writes the final decision directly.

    Args:
        claim_id: UUID of the claim to process.
        claim_data: Full claim row dict as returned by bigquery_client.get_claim.

    Raises:
        RuntimeError: If any BigQuery write fails (pipeline aborts).
        Exception: Any unexpected error is logged and re-raised.
    """
    session_service = InMemorySessionService()
    session_id = f"claim-{claim_id}"

    # Transition to under_review
    await bq.update_claim_status(claim_id, ClaimStatus.UNDER_REVIEW.value)
    await bq.insert_audit_log({
        "id": str(uuid.uuid4()),
        "claim_id": claim_id,
        "event_type": "pipeline_started",
        "previous_status": ClaimStatus.PENDING.value,
        "new_status": ClaimStatus.UNDER_REVIEW.value,
        "actor": USER_ID,
        "details_json": json.dumps({"trigger": "api_request"}),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Resolve document_refs — stored as JSON string in BQ or as a list directly
    raw_refs = claim_data.get("document_refs", "[]")
    doc_refs: list[str] = (
        json.loads(raw_refs) if isinstance(raw_refs, str) else list(raw_refs)
    )

    claim_context = (
        f"Claim ID: {claim_id}\n"
        f"Type: {claim_data['claim_type']}\n"
        f"Claimant: {claim_data['claimant_name']}\n"
        f"Policy: {claim_data['policy_number']}\n"
        f"Amount: ${float(claim_data['amount']):,.2f}\n"
        f"Description: {claim_data['incident_description']}\n"
        f"Documents: {', '.join(doc_refs) if doc_refs else 'none submitted'}"
    )

    try:
        # ── Stage 1: Document Verification ─────────────────────────────────
        doc_runner = Runner(
            agent=build_document_verification_agent(),
            app_name=APP_NAME,
            session_service=session_service,
        )
        _, doc_result = await _run_agent_stage(
            doc_runner,
            session_id,
            AgentStage.DOCUMENT_VERIFICATION,
            f"Verify the documents for this insurance claim:\n\n{claim_context}",
            claim_id,
        )

        # ── Stage 2: Fraud Detection ────────────────────────────────────────
        authenticity_flags: list[str] = doc_result.get("authenticity_flags", [])
        fraud_runner = Runner(
            agent=build_fraud_detection_agent(),
            app_name=APP_NAME,
            session_service=session_service,
        )
        _, fraud_result = await _run_agent_stage(
            fraud_runner,
            session_id,
            AgentStage.FRAUD_DETECTION,
            (
                f"Analyse this claim for fraud indicators:\n\n{claim_context}\n\n"
                f"Document verification authenticity flags: {authenticity_flags}\n"
                f"has_authenticity_flags: {bool(authenticity_flags)}"
            ),
            claim_id,
        )
        fraud_score = float(fraud_result.get("fraud_score", 0.0))

        # ── Stage 3: Claim Validation ───────────────────────────────────────
        val_runner = Runner(
            agent=build_claim_validation_agent(),
            app_name=APP_NAME,
            session_service=session_service,
        )
        _, val_result = await _run_agent_stage(
            val_runner,
            session_id,
            AgentStage.CLAIM_VALIDATION,
            f"Validate this insurance claim against policy terms:\n\n{claim_context}",
            claim_id,
        )

        # ── Stage 4: Decision ───────────────────────────────────────────────
        dec_runner = Runner(
            agent=build_decision_agent(),
            app_name=APP_NAME,
            session_service=session_service,
        )
        _, dec_result = await _run_agent_stage(
            dec_runner,
            session_id,
            AgentStage.DECISION,
            (
                f"Make a final decision for this claim:\n\n{claim_context}\n\n"
                f"Document verification result:\n{json.dumps(doc_result, indent=2)}\n\n"
                f"Fraud detection result:\n{json.dumps(fraud_result, indent=2)}\n\n"
                f"Claim validation result:\n{json.dumps(val_result, indent=2)}"
            ),
            claim_id,
        )

        # ── Handle HITL or Final Decision ──────────────────────────────────
        if dec_result.get("hitl_required"):
            trigger_reason = dec_result.get("trigger_reason") or "high_amount"
            await bq.update_claim_status(
                claim_id, ClaimStatus.AWAITING_HUMAN_APPROVAL.value
            )
            await bq.insert_hitl_request({
                "id": str(uuid.uuid4()),
                "claim_id": claim_id,
                "trigger_reason": trigger_reason,
                "fraud_score": fraud_score,
                "amount": float(claim_data["amount"]),
                "interrupt_payload": json.dumps({
                    "document_verification": doc_result,
                    "fraud_detection": fraud_result,
                    "claim_validation": val_result,
                    "decision": dec_result,
                }),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            await bq.insert_audit_log({
                "id": str(uuid.uuid4()),
                "claim_id": claim_id,
                "event_type": "hitl_triggered",
                "previous_status": ClaimStatus.UNDER_REVIEW.value,
                "new_status": ClaimStatus.AWAITING_HUMAN_APPROVAL.value,
                "actor": USER_ID,
                "details_json": json.dumps(
                    {"trigger_reason": trigger_reason, "fraud_score": fraud_score}
                ),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            await _publish(
                claim_id,
                AgentEventType.HITL_REQUIRED,
                AgentStage.DECISION.value,
                f"Human review required: {trigger_reason.replace('_', ' ')}",
                trigger_reason=trigger_reason,
                fraud_score=fraud_score,
            )

        else:
            # Map decision string to ClaimStatus enum value
            decision_str = dec_result.get("decision", "rejected")
            # Valid decisions from make_claim_decision:
            # "agent_approved" | "rejected" | "partial_settlement"
            try:
                final_status = ClaimStatus(decision_str)
            except ValueError:
                logger.error(
                    "unknown_decision_value",
                    decision=decision_str,
                    claim_id=claim_id,
                )
                final_status = ClaimStatus.REJECTED

            await bq.update_claim_status(claim_id, final_status.value)

            event_type_str = (
                "claim_settled"
                if final_status == ClaimStatus.AGENT_APPROVED
                else "claim_rejected"
            )
            await bq.insert_audit_log({
                "id": str(uuid.uuid4()),
                "claim_id": claim_id,
                "event_type": event_type_str,
                "previous_status": ClaimStatus.UNDER_REVIEW.value,
                "new_status": final_status.value,
                "actor": USER_ID,
                "details_json": json.dumps(
                    {
                        "decision": decision_str,
                        "final_amount": dec_result.get("final_amount", 0.0),
                    }
                ),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            await _publish(
                claim_id,
                AgentEventType.PIPELINE_COMPLETE,
                AgentStage.DECISION.value,
                dec_result.get("decision_reason", "Pipeline complete"),
                final_status=final_status.value,
                fraud_score=fraud_score,
            )

    except Exception:
        logger.exception("pipeline_error", claim_id=claim_id)
        # Publish error event so the SSE stream can close cleanly
        await _publish(
            claim_id,
            AgentEventType.ERROR,
            AgentStage.DECISION.value,
            "An internal error occurred during claims processing",
        )
        raise
