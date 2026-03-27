from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from google.adk.agents import Agent
from google.adk.tools import tool

logger = structlog.get_logger(__name__)


@tool
def analyze_claim_patterns(
    claim_type: str,
    amount: float,
    incident_description: str,
    policy_number: str,
) -> dict[str, Any]:
    """Analyze claim patterns for statistical fraud indicators.

    Args:
        claim_type: Type of insurance claim (AUTO/HEALTH/PROPERTY).
        amount: Claimed amount in dollars.
        incident_description: Text description of the incident.
        policy_number: Policy identifier string.

    Returns:
        Dict with pattern_flags list and flag_count integer.
    """
    risk_indicators: list[str] = []
    desc_lower = incident_description.lower()

    # High-value AUTO claim for a described minor incident
    if claim_type.upper() == "AUTO" and amount > 5_000 and "minor" in desc_lower:
        risk_indicators.append("High amount for described minor incident")

    # Repeated-claims language embedded in the description
    if any(
        phrase in desc_lower
        for phrase in ["third claim", "second claim", "previous claim"]
    ):
        risk_indicators.append("History of multiple claims detected")

    # Suspiciously round amounts (common in inflated claims)
    if amount % 1_000 == 0 and amount >= 5_000:
        risk_indicators.append("Suspiciously round claim amount")

    # Vague description for a large claim
    if amount > 10_000 and len(desc_lower.split()) < 20:
        risk_indicators.append("Inadequate description for high-value claim")

    # Large claim on a policy issued in the current year (recently opened)
    current_year = str(datetime.now(timezone.utc).year)
    if amount > 8_000 and current_year in policy_number:
        risk_indicators.append("Large claim on recently issued policy")

    return {
        "pattern_flags": risk_indicators,
        "flag_count": len(risk_indicators),
    }


@tool
def calculate_fraud_risk_score(
    flag_count: int,
    claim_amount: float,
    has_authenticity_flags: bool,
) -> dict[str, Any]:
    """Calculate a fraud risk score from 0.0 to 1.0.

    Args:
        flag_count: Number of fraud pattern flags detected by analyze_claim_patterns.
        claim_amount: Claimed amount in dollars.
        has_authenticity_flags: Whether document verification found authenticity issues.

    Returns:
        Dict with fraud_score (float) and risk_level (low/medium/high).
    """
    base_score = min(flag_count * 0.15, 0.60)

    # Boost score for high-value claims
    if claim_amount > 20_000:
        base_score = min(base_score + 0.15, 0.85)
    elif claim_amount > 10_000:
        base_score = min(base_score + 0.08, 0.75)

    # Further boost when authenticity issues were already found
    if has_authenticity_flags:
        base_score = min(base_score + 0.20, 0.95)

    score = round(base_score, 2)

    risk_level: str
    if score >= 0.70:
        risk_level = "high"
    elif score >= 0.40:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {"fraud_score": score, "risk_level": risk_level}


def build_fraud_detection_agent() -> Agent:
    """Build and return the FraudDetectionAgent.

    Returns:
        Configured ADK Agent instance ready to be wrapped in a Runner.
    """
    return Agent(
        name="FraudDetectionAgent",
        model="gemini-2.5-flash",
        description="Detects fraud indicators in insurance claims",
        instruction="""You are a fraud detection specialist for insurance claims.

Your job is to:
1. Use analyze_claim_patterns to identify statistical fraud indicators in this claim.
2. Use calculate_fraud_risk_score to produce a final fraud risk score, passing:
   - flag_count from step 1
   - the claim amount
   - has_authenticity_flags=true if the document verification step found any flags, false otherwise

The fraud_score threshold is critical:
- Score < 0.4:  Low risk — processing continues normally
- Score 0.4–0.69: Medium risk — flagged for extra scrutiny but processing continues
- Score >= 0.7: HIGH RISK — will trigger mandatory human review

Output ONLY a JSON object (no markdown fences) with these exact keys:
- fraud_score: float 0.0–1.0 (taken directly from calculate_fraud_risk_score)
- risk_level: "low" / "medium" / "high"
- fraud_indicators: complete list of all suspicious patterns found (empty list if none)
- recommendation: brief explanation of findings and suggested next steps

Be objective and evidence-based. Do not add indicators that were not returned by the tools.""",
        tools=[analyze_claim_patterns, calculate_fraud_risk_score],
    )
