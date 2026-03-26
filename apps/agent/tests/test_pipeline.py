"""Unit tests for pipeline.py — _extract_json and run_pipeline."""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline import _extract_json, run_pipeline


# ---------------------------------------------------------------------------
# _extract_json
# ---------------------------------------------------------------------------


def test_extract_json_plain_json() -> None:
    """Valid JSON string is parsed directly into a dict."""
    payload = '{"decision": "agent_approved", "confidence_score": 0.95}'
    result = _extract_json(payload)
    assert result == {"decision": "agent_approved", "confidence_score": 0.95}


def test_extract_json_markdown_fence() -> None:
    """JSON wrapped in ```json ... ``` fence is unwrapped and parsed."""
    payload = '```json\n{"fraud_score": 0.1, "verdict": "clean"}\n```'
    result = _extract_json(payload)
    assert result == {"fraud_score": 0.1, "verdict": "clean"}


def test_extract_json_plain_fence() -> None:
    """JSON wrapped in plain ``` fence (no language tag) is unwrapped and parsed."""
    payload = '```\n{"documents_verified": true, "missing_documents": []}\n```'
    result = _extract_json(payload)
    assert result == {"documents_verified": True, "missing_documents": []}


def test_extract_json_fallback() -> None:
    """Non-JSON string produces a fallback dict with the raw_response key."""
    text = "This is not valid JSON at all."
    result = _extract_json(text)
    assert result == {"raw_response": text}


def test_extract_json_non_dict_json_is_fallback() -> None:
    """A JSON array (not a dict) is treated as a fallback."""
    text = '["a", "b", "c"]'
    result = _extract_json(text)
    assert result == {"raw_response": text}


def test_extract_json_whitespace_stripped() -> None:
    """Leading/trailing whitespace around JSON is handled gracefully."""
    payload = "   \n  { \"key\": 1 }  \n  "
    result = _extract_json(payload)
    assert result == {"key": 1}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_async_generator(items: list[Any]):
    """Return an async generator that yields the given items."""
    async def _gen(*args: Any, **kwargs: Any):
        for item in items:
            yield item
    return _gen


def _make_mock_event(text: str, thought: bool = False) -> MagicMock:
    """Build a minimal mock ADK event with a single part."""
    part = MagicMock()
    part.thought = thought
    part.text = text

    content = MagicMock()
    content.parts = [part]

    event = MagicMock()
    event.content = content
    return event


def _make_runner_mock(response_json: dict[str, Any]) -> MagicMock:
    """Build a mock ADK Runner whose run_async yields one event containing JSON."""
    response_text = json.dumps(response_json)
    events = [_make_mock_event(response_text)]

    runner = MagicMock()
    runner.run_async = _make_async_generator(events)
    return runner


# ---------------------------------------------------------------------------
# run_pipeline — happy paths & branching
# ---------------------------------------------------------------------------


@pytest.fixture
def _mock_bq() -> dict[str, AsyncMock]:
    """Return a dict of AsyncMock objects for every bigquery_client function used by the pipeline."""
    return {
        "update_claim_status": AsyncMock(),
        "insert_audit_log": AsyncMock(),
        "insert_agent_analysis": AsyncMock(),
        "insert_hitl_request": AsyncMock(),
    }


@pytest.fixture
def _mock_publish() -> AsyncMock:
    return AsyncMock()


def _doc_result() -> dict[str, Any]:
    return {
        "documents_verified": True,
        "missing_documents": [],
        "authenticity_flags": [],
        "confidence_score": 0.9,
        "summary": "All docs present",
    }


def _fraud_result(fraud_score: float = 0.05) -> dict[str, Any]:
    return {
        "fraud_score": fraud_score,
        "risk_level": "low",
        "indicators": [],
        "confidence_score": 0.9,
        "summary": "No fraud indicators",
    }


def _val_result() -> dict[str, Any]:
    return {
        "policy_covers_claim": True,
        "coverage_gaps": [],
        "confidence_score": 0.9,
        "summary": "Policy covers the claim",
    }


def _dec_result_approved() -> dict[str, Any]:
    return {
        "decision": "agent_approved",
        "hitl_required": False,
        "decision_reason": "All checks passed",
        "final_amount": 3000.0,
        "confidence_score": 0.92,
    }


def _dec_result_hitl() -> dict[str, Any]:
    return {
        "decision": "pending",
        "hitl_required": True,
        "trigger_reason": "high_amount",
        "decision_reason": "Amount exceeds threshold",
        "confidence_score": 0.7,
    }


def _dec_result_rejected() -> dict[str, Any]:
    return {
        "decision": "rejected",
        "hitl_required": False,
        "decision_reason": "High fraud score",
        "final_amount": 0.0,
        "confidence_score": 0.85,
    }


async def test_run_pipeline_auto_approve(
    sample_claim: dict, _mock_bq: dict, _mock_publish: AsyncMock
) -> None:
    """Auto-approve path: all stages pass, decision=agent_approved, status updated accordingly."""
    runners = [
        _make_runner_mock(_doc_result()),
        _make_runner_mock(_fraud_result()),
        _make_runner_mock(_val_result()),
        _make_runner_mock(_dec_result_approved()),
    ]

    with (
        patch("pipeline.bq.update_claim_status", _mock_bq["update_claim_status"]),
        patch("pipeline.bq.insert_audit_log", _mock_bq["insert_audit_log"]),
        patch("pipeline.bq.insert_agent_analysis", _mock_bq["insert_agent_analysis"]),
        patch("pipeline.bq.insert_hitl_request", _mock_bq["insert_hitl_request"]),
        patch("pipeline.publish_event", _mock_publish),
        patch("pipeline.Runner", side_effect=runners),
        patch("pipeline.build_document_verification_agent", return_value=MagicMock()),
        patch("pipeline.build_fraud_detection_agent", return_value=MagicMock()),
        patch("pipeline.build_claim_validation_agent", return_value=MagicMock()),
        patch("pipeline.build_decision_agent", return_value=MagicMock()),
        patch("pipeline.InMemorySessionService", return_value=MagicMock()),
    ):
        await run_pipeline(sample_claim["id"], sample_claim)

    # Status should transition: pending -> under_review -> agent_approved
    status_calls = [
        call.args[1]
        for call in _mock_bq["update_claim_status"].call_args_list
    ]
    assert "under_review" in status_calls
    assert "agent_approved" in status_calls
    # HITL should never be triggered for an auto-approved claim
    _mock_bq["insert_hitl_request"].assert_not_called()


async def test_run_pipeline_hitl_trigger(
    hitl_claim: dict, _mock_bq: dict, _mock_publish: AsyncMock
) -> None:
    """HITL path: dec_result has hitl_required=True; insert_hitl_request called, status=awaiting_human_approval."""
    runners = [
        _make_runner_mock(_doc_result()),
        _make_runner_mock(_fraud_result()),
        _make_runner_mock(_val_result()),
        _make_runner_mock(_dec_result_hitl()),
    ]

    with (
        patch("pipeline.bq.update_claim_status", _mock_bq["update_claim_status"]),
        patch("pipeline.bq.insert_audit_log", _mock_bq["insert_audit_log"]),
        patch("pipeline.bq.insert_agent_analysis", _mock_bq["insert_agent_analysis"]),
        patch("pipeline.bq.insert_hitl_request", _mock_bq["insert_hitl_request"]),
        patch("pipeline.publish_event", _mock_publish),
        patch("pipeline.Runner", side_effect=runners),
        patch("pipeline.build_document_verification_agent", return_value=MagicMock()),
        patch("pipeline.build_fraud_detection_agent", return_value=MagicMock()),
        patch("pipeline.build_claim_validation_agent", return_value=MagicMock()),
        patch("pipeline.build_decision_agent", return_value=MagicMock()),
        patch("pipeline.InMemorySessionService", return_value=MagicMock()),
    ):
        await run_pipeline(hitl_claim["id"], hitl_claim)

    # Must write a HITL request row
    _mock_bq["insert_hitl_request"].assert_called_once()
    # Claim status must reach awaiting_human_approval
    status_calls = [
        call.args[1]
        for call in _mock_bq["update_claim_status"].call_args_list
    ]
    assert "awaiting_human_approval" in status_calls


async def test_run_pipeline_fraud_rejection(
    fraud_claim: dict, _mock_bq: dict, _mock_publish: AsyncMock
) -> None:
    """Fraud path: dec_result decision=rejected; status transitions to rejected."""
    runners = [
        _make_runner_mock(_doc_result()),
        _make_runner_mock(_fraud_result(fraud_score=0.8)),
        _make_runner_mock(_val_result()),
        _make_runner_mock(_dec_result_rejected()),
    ]

    with (
        patch("pipeline.bq.update_claim_status", _mock_bq["update_claim_status"]),
        patch("pipeline.bq.insert_audit_log", _mock_bq["insert_audit_log"]),
        patch("pipeline.bq.insert_agent_analysis", _mock_bq["insert_agent_analysis"]),
        patch("pipeline.bq.insert_hitl_request", _mock_bq["insert_hitl_request"]),
        patch("pipeline.publish_event", _mock_publish),
        patch("pipeline.Runner", side_effect=runners),
        patch("pipeline.build_document_verification_agent", return_value=MagicMock()),
        patch("pipeline.build_fraud_detection_agent", return_value=MagicMock()),
        patch("pipeline.build_claim_validation_agent", return_value=MagicMock()),
        patch("pipeline.build_decision_agent", return_value=MagicMock()),
        patch("pipeline.InMemorySessionService", return_value=MagicMock()),
    ):
        await run_pipeline(fraud_claim["id"], fraud_claim)

    status_calls = [
        call.args[1]
        for call in _mock_bq["update_claim_status"].call_args_list
    ]
    assert "rejected" in status_calls
    # HITL must NOT be triggered for a straight rejection
    _mock_bq["insert_hitl_request"].assert_not_called()


async def test_run_pipeline_error_publishes_event(
    sample_claim: dict, _mock_publish: AsyncMock
) -> None:
    """When insert_agent_analysis raises inside the try block, an ERROR event is published and the exception re-raised.

    The pre-try status update calls are outside the except handler, so the
    error that triggers the ERROR event must occur inside the `try` block —
    e.g. when persisting a stage result to BigQuery.
    """
    # insert_agent_analysis is called inside _run_agent_stage, which is inside
    # the try block, so an error here will be caught by the except handler and
    # result in an ERROR event being published to Redis.
    exploding_analysis = AsyncMock(side_effect=RuntimeError("BQ write failed"))

    runners = [_make_runner_mock(_doc_result())]

    with (
        patch("pipeline.bq.update_claim_status", AsyncMock()),
        patch("pipeline.bq.insert_audit_log", AsyncMock()),
        patch("pipeline.bq.insert_agent_analysis", exploding_analysis),
        patch("pipeline.bq.insert_hitl_request", AsyncMock()),
        patch("pipeline.publish_event", _mock_publish),
        patch("pipeline.Runner", side_effect=runners),
        patch("pipeline.build_document_verification_agent", return_value=MagicMock()),
        patch("pipeline.build_fraud_detection_agent", return_value=MagicMock()),
        patch("pipeline.build_claim_validation_agent", return_value=MagicMock()),
        patch("pipeline.build_decision_agent", return_value=MagicMock()),
        patch("pipeline.InMemorySessionService", return_value=MagicMock()),
    ):
        with pytest.raises(RuntimeError, match="BQ write failed"):
            await run_pipeline(sample_claim["id"], sample_claim)

    # The ERROR event must have been published so the SSE stream can close cleanly
    published_types = [call.args[1]["type"] for call in _mock_publish.call_args_list]
    assert "error" in published_types
