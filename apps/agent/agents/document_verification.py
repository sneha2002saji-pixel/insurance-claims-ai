from __future__ import annotations

from typing import Any

import structlog
from google.adk.agents import Agent
from google.adk.tools import tool

logger = structlog.get_logger(__name__)

# Required documents per claim type (partial-match keys against submitted doc names)
REQUIRED_DOCS: dict[str, list[str]] = {
    "AUTO": ["police_report", "repair_estimate", "photos"],
    "HEALTH": ["hospital_discharge", "surgical_report", "itemized_bill"],
    "PROPERTY": ["damage_photos", "contractor_estimate", "weather_report"],
}


@tool
def check_required_documents(claim_type: str, submitted_docs: list[str]) -> dict[str, Any]:
    """Check if all required documents for the claim type have been submitted.

    Args:
        claim_type: Type of insurance claim (AUTO/HEALTH/PROPERTY).
        submitted_docs: List of submitted document references.

    Returns:
        Dict with present_docs, missing_docs, and completeness_score.
    """
    required = REQUIRED_DOCS.get(claim_type.upper(), [])
    # Partial match: "police_report.pdf" satisfies the "police_report" requirement
    present = [r for r in required if any(r in doc for doc in submitted_docs)]
    missing = [r for r in required if r not in present]
    score = len(present) / max(len(required), 1)
    return {
        "present_docs": present,
        "missing_docs": missing,
        "completeness_score": round(score, 2),
    }


@tool
def flag_authenticity_issues(
    incident_description: str,
    claim_type: str,
    amount: float,
) -> dict[str, Any]:
    """Analyse the incident description for authenticity red flags.

    Args:
        incident_description: Text description of the incident.
        claim_type: Type of insurance claim (AUTO/HEALTH/PROPERTY).
        amount: Claimed amount in dollars.

    Returns:
        Dict with flags list and severity level.
    """
    flags: list[str] = []
    desc_lower = incident_description.lower()

    # Generic red flags
    if len(desc_lower.split()) < 10:
        flags.append("Description is unusually brief")
    if amount > 50_000:
        flags.append("Exceptionally high claim amount")

    # Claim-type-specific checks
    if claim_type.upper() == "PROPERTY" and "third claim" in desc_lower:
        flags.append("Multiple claims from same claimant this year")
    if claim_type.upper() == "AUTO" and "no witness" in desc_lower:
        flags.append("No independent witnesses mentioned")
    if claim_type.upper() == "HEALTH" and "elective" in desc_lower:
        flags.append("Potentially elective procedure")

    severity: str
    if len(flags) >= 2:
        severity = "high"
    elif flags:
        severity = "medium"
    else:
        severity = "none"

    return {"flags": flags, "severity": severity}


def build_document_verification_agent() -> Agent:
    """Build and return the DocumentVerificationAgent.

    Returns:
        Configured ADK Agent instance ready to be wrapped in a Runner.
    """
    return Agent(
        name="DocumentVerificationAgent",
        model="gemini-2.5-flash",
        description="Verifies insurance claim documents for completeness and authenticity",
        instruction="""You are a document verification specialist for insurance claims.

Your job is to:
1. Use check_required_documents to verify all necessary documents are present for the claim type.
2. Use flag_authenticity_issues to identify any red flags in the claim description.
3. Provide a clear, structured verification summary.

Output ONLY a JSON object (no markdown fences) with these exact keys:
- documents_verified: boolean — true only if completeness_score is 1.0 and severity is not "high"
- missing_documents: list of missing document type strings (empty list if all present)
- authenticity_flags: list of concern strings found (empty list if none)
- confidence_score: float 0.0–1.0 reflecting confidence in document validity
- summary: brief explanation of your findings

Be thorough but fair. A claim with all documents present and no red flags should receive
a confidence_score of at least 0.85.""",
        tools=[check_required_documents, flag_authenticity_issues],
    )
