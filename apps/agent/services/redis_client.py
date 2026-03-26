from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator

import structlog
import redis.asyncio as aioredis

logger = structlog.get_logger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
CHANNEL_PREFIX = "agent:events:"


def _channel(claim_id: str) -> str:
    """Return the Redis pub/sub channel name for a claim."""
    return f"{CHANNEL_PREFIX}{claim_id}"


async def publish_event(claim_id: str, event: dict[str, Any]) -> None:
    """Publish an agent event to the Redis pub/sub channel for a claim.

    A new connection is created and closed per call so this function is safe
    to call from multiple concurrent agent tasks without shared state.

    Args:
        claim_id: UUID of the claim the event belongs to.
        event: Dict representation of an AgentEvent (must be JSON-serialisable).

    Raises:
        redis.exceptions.RedisError: On connection or publish failure.
    """
    client = aioredis.from_url(REDIS_URL, decode_responses=True)
    try:
        payload = json.dumps(event)
        await client.publish(_channel(claim_id), payload)
        logger.debug(
            "event_published",
            claim_id=claim_id,
            event_type=event.get("type"),
        )
    finally:
        await client.aclose()


async def subscribe_events(claim_id: str) -> AsyncIterator[dict]:
    """Subscribe to agent events for a claim and yield parsed event dicts.

    This is an async generator intended for use in Server-Sent Event (SSE)
    route handlers. The subscription is cleaned up automatically when the
    generator is exhausted or closed by the caller.

    Args:
        claim_id: UUID of the claim to subscribe to.

    Yields:
        Parsed event dicts. Malformed JSON messages are skipped with a warning.

    Raises:
        redis.exceptions.RedisError: On connection failure.
    """
    client = aioredis.from_url(REDIS_URL, decode_responses=True)
    pubsub = client.pubsub()
    await pubsub.subscribe(_channel(claim_id))
    logger.info("subscribed_to_claim_events", claim_id=claim_id)
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    yield json.loads(message["data"])
                except json.JSONDecodeError:
                    logger.warning(
                        "invalid_event_payload",
                        claim_id=claim_id,
                        raw=message["data"],
                    )
    finally:
        await pubsub.unsubscribe(_channel(claim_id))
        await client.aclose()
        logger.info("unsubscribed_from_claim_events", claim_id=claim_id)
