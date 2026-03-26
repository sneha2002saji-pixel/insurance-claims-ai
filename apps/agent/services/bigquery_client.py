from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

import structlog
from google.cloud import bigquery

logger = structlog.get_logger(__name__)

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET = "insurance"

_bq_client: bigquery.Client | None = None

_CLAIM_COLUMNS = (
    "id, claim_type, claimant_name, policy_number, amount, "
    "incident_description, document_refs, status, created_at, updated_at"
)


def _client() -> bigquery.Client:
    """Return a module-level singleton BigQuery client."""
    global _bq_client  # noqa: PLW0603
    if _bq_client is None:
        _bq_client = bigquery.Client(project=PROJECT_ID)
    return _bq_client


def _table(table_name: str) -> str:
    return f"{PROJECT_ID}.{DATASET}.{table_name}"


def _job_config(params: list, stage: str = "general") -> bigquery.QueryJobConfig:
    return bigquery.QueryJobConfig(
        query_parameters=params,
        labels={"service": "insurance-claims", "stage": stage},
    )


async def get_claim(claim_id: str) -> dict[str, Any] | None:
    """Fetch a single claim by ID.

    Args:
        claim_id: UUID string of the claim to retrieve.

    Returns:
        A dict of column→value for the matching row, or None if not found.

    Raises:
        RuntimeError: If the BigQuery query fails.
    """
    client = _client()
    query = f"""
        SELECT {_CLAIM_COLUMNS}
        FROM `{_table('insurance_claims')}`
        WHERE id = @claim_id
        LIMIT 1
    """
    config = _job_config(
        [bigquery.ScalarQueryParameter("claim_id", "STRING", claim_id)],
        stage="get_claim",
    )
    rows = await asyncio.to_thread(
        lambda: list(client.query(query, job_config=config).result())
    )
    if not rows:
        return None
    return dict(rows[0])


async def list_claims(limit: int = 20) -> list[dict[str, Any]]:
    """List claims ordered by created_at descending.

    Args:
        limit: Maximum number of rows to return (max 100).

    Returns:
        List of claim row dicts.
    """
    client = _client()
    query = f"""
        SELECT {_CLAIM_COLUMNS}
        FROM `{_table('insurance_claims')}`
        ORDER BY created_at DESC
        LIMIT @limit
    """
    config = _job_config(
        [bigquery.ScalarQueryParameter("limit", "INT64", min(limit, 100))],
        stage="list_claims",
    )
    rows = await asyncio.to_thread(
        lambda: list(client.query(query, job_config=config).result())
    )
    return [dict(r) for r in rows]


async def insert_claim(claim: dict[str, Any]) -> None:
    """Insert a new claim row via streaming insert.

    Args:
        claim: Dict matching the insurance_claims table schema.

    Raises:
        RuntimeError: If BigQuery returns insertion errors.
    """
    client = _client()
    errors = await asyncio.to_thread(
        lambda: client.insert_rows_json(_table("insurance_claims"), [claim])
    )
    if errors:
        raise RuntimeError(f"BigQuery insert errors: {errors}")
    logger.info("claim_inserted", claim_id=claim.get("id"))


async def update_claim_status(claim_id: str, new_status: str) -> None:
    """Update claim status and updated_at timestamp via DML.

    Args:
        claim_id: UUID of the claim to update.
        new_status: New ClaimStatus value as a string.

    Raises:
        RuntimeError: If the DML job fails.
    """
    client = _client()
    query = f"""
        UPDATE `{_table('insurance_claims')}`
        SET status = @status, updated_at = @updated_at
        WHERE id = @claim_id
    """
    config = _job_config(
        [
            bigquery.ScalarQueryParameter("status", "STRING", new_status),
            bigquery.ScalarQueryParameter(
                "updated_at", "TIMESTAMP", datetime.now(timezone.utc).isoformat()
            ),
            bigquery.ScalarQueryParameter("claim_id", "STRING", claim_id),
        ],
        stage="update_status",
    )
    await asyncio.to_thread(
        lambda: client.query(query, job_config=config).result()
    )
    logger.info("claim_status_updated", claim_id=claim_id, new_status=new_status)


async def insert_agent_analysis(analysis: dict[str, Any]) -> None:
    """Insert an agent analysis result via streaming insert.

    Args:
        analysis: Dict matching the agent_analyses table schema.

    Raises:
        RuntimeError: If BigQuery returns insertion errors.
    """
    client = _client()
    errors = await asyncio.to_thread(
        lambda: client.insert_rows_json(_table("agent_analyses"), [analysis])
    )
    if errors:
        raise RuntimeError(f"BigQuery insert errors: {errors}")
    logger.debug(
        "agent_analysis_inserted",
        claim_id=analysis.get("claim_id"),
        stage=analysis.get("stage"),
    )


async def insert_audit_log(entry: dict[str, Any]) -> None:
    """Insert an audit log entry — insert-only, never updated or deleted.

    Args:
        entry: Dict matching the audit_log table schema.

    Raises:
        RuntimeError: If BigQuery returns insertion errors.
    """
    client = _client()
    errors = await asyncio.to_thread(
        lambda: client.insert_rows_json(_table("audit_log"), [entry])
    )
    if errors:
        raise RuntimeError(f"BigQuery insert errors: {errors}")
    logger.debug("audit_log_inserted", claim_id=entry.get("claim_id"))


async def insert_hitl_request(request: dict[str, Any]) -> None:
    """Insert a human approval request via streaming insert.

    Args:
        request: Dict matching the human_approval_requests table schema.

    Raises:
        RuntimeError: If BigQuery returns insertion errors.
    """
    client = _client()
    errors = await asyncio.to_thread(
        lambda: client.insert_rows_json(_table("human_approval_requests"), [request])
    )
    if errors:
        raise RuntimeError(f"BigQuery insert errors: {errors}")
    logger.info("hitl_request_inserted", claim_id=request.get("claim_id"))


async def update_hitl_decision(claim_id: str, decision: str, comment: str) -> None:
    """Record the human adjuster's decision on a pending HITL request.

    Only rows where decision IS NULL are updated to prevent overwriting a prior decision.

    Args:
        claim_id: UUID of the claim whose approval request should be updated.
        decision: HumanDecision value as a string.
        comment: Free-text adjuster comment (must not be empty).

    Raises:
        RuntimeError: If the DML job fails.
    """
    client = _client()
    query = f"""
        UPDATE `{_table('human_approval_requests')}`
        SET decision = @decision,
            adjuster_comment = @comment,
            decided_at = @decided_at
        WHERE claim_id = @claim_id
          AND decision IS NULL
    """
    config = _job_config(
        [
            bigquery.ScalarQueryParameter("decision", "STRING", decision),
            bigquery.ScalarQueryParameter("comment", "STRING", comment),
            bigquery.ScalarQueryParameter(
                "decided_at", "TIMESTAMP", datetime.now(timezone.utc).isoformat()
            ),
            bigquery.ScalarQueryParameter("claim_id", "STRING", claim_id),
        ],
        stage="hitl_decision",
    )
    await asyncio.to_thread(
        lambda: client.query(query, job_config=config).result()
    )
    logger.info("hitl_decision_recorded", claim_id=claim_id, decision=decision)
