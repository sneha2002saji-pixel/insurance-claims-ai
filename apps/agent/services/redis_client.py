from __future__ import annotations

import asyncio
import json
import os
from typing import Any, AsyncIterator

import structlog
import redis.asyncio as aioredis
from redis.asyncio.client import PubSub, Redis

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


async def create_subscription(claim_id: str) -> tuple[Redis, PubSub]:
    """Eagerly establish a Redis pub/sub subscription before the pipeline starts.

    Unlike an async generator, this coroutine executes immediately on await,
    so the subscription is live before the pipeline task is created. This
    eliminates the race where early pipeline events are published before the
    generator has a chance to call pubsub.subscribe().

    Args:
        claim_id: UUID of the claim to subscribe to.

    Returns:
        Tuple of (redis_client, pubsub). Ownership is transferred to the
        caller; use yield_events() to consume events and close both.

    Raises:
        redis.exceptions.RedisError: On connection failure.
    """
    client = aioredis.from_url(REDIS_URL, decode_responses=True)
    pubsub = client.pubsub()
    await pubsub.subscribe(_channel(claim_id))
    logger.info("subscribed_to_claim_events", claim_id=claim_id)
    return client, pubsub


async def yield_events(
    client: Redis,
    pubsub: PubSub,
    claim_id: str,
    timeout: float = 300.0,
) -> AsyncIterator[dict[str, Any]]:
    """Yield parsed event dicts from an already-subscribed pubsub.

    Cleans up the subscription and closes the client in its finally block,
    so the caller does not need to manage them separately.

    Args:
        client: Redis client returned by create_subscription.
        pubsub: Already-subscribed PubSub object from create_subscription.
        claim_id: UUID of the claim (used for logging and unsubscribe).
        timeout: Seconds to wait for the next message before raising
            asyncio.TimeoutError. Prevents the stream from hanging forever
            when the pipeline dies without publishing a terminal event.

    Yields:
        Parsed event dicts. Malformed JSON messages are skipped with a warning.

    Raises:
        asyncio.TimeoutError: If no message arrives within `timeout` seconds.
    """
    try:
        aiter = pubsub.listen().__aiter__()
        while True:
            try:
                message = await asyncio.wait_for(aiter.__anext__(), timeout=timeout)
            except StopAsyncIteration:
                break
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
