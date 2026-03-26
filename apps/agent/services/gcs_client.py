from __future__ import annotations

import asyncio
import os

import structlog
from google.cloud import storage

logger = structlog.get_logger(__name__)

BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "insurance-mock-documents")

_gcs_client: storage.Client | None = None


def _client() -> storage.Client:
    """Return a module-level singleton GCS client."""
    global _gcs_client  # noqa: PLW0603
    if _gcs_client is None:
        _gcs_client = storage.Client()
    return _gcs_client


async def get_document(document_ref: str) -> bytes:
    """Fetch a mock document from GCS by its blob reference name.

    Args:
        document_ref: The GCS object name (e.g. ``"claim-abc/policy.pdf"``).

    Returns:
        Raw bytes of the document.

    Raises:
        google.cloud.exceptions.NotFound: If the blob does not exist.
        google.cloud.exceptions.GoogleCloudError: On any other GCS error.
    """
    def _fetch() -> bytes:
        bucket = _client().bucket(BUCKET_NAME)
        blob = bucket.blob(document_ref)
        return blob.download_as_bytes()

    data = await asyncio.to_thread(_fetch)
    logger.info("document_fetched", document_ref=document_ref, size_bytes=len(data))
    return data


async def list_claim_documents(claim_id: str) -> list[str]:
    """List all document blob names stored under a claim's GCS prefix.

    Args:
        claim_id: UUID of the claim; used as the GCS prefix (``"<claim_id>/"``).

    Returns:
        List of blob names (full object paths within the bucket).

    Raises:
        google.cloud.exceptions.GoogleCloudError: On any GCS error.
    """
    def _list() -> list[str]:
        blobs = _client().list_blobs(BUCKET_NAME, prefix=f"{claim_id}/")
        return [b.name for b in blobs]

    names = await asyncio.to_thread(_list)
    logger.debug("claim_documents_listed", claim_id=claim_id, count=len(names))
    return names
