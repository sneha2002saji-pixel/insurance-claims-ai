from __future__ import annotations

from typing import Any

import structlog
from google.adk.agents import Agent
from google.adk.tools import tool

logger = structlog.get_logger(__name__)

# Per-type coverage limits and deductible amounts (in USD)
COVERAGE_LIMITS: dict[str, dict[str, float]] = {
    "AUTO": {"max_claim": 50_000.0, "deductible": 500.0},
    "HEALTH": {"max_claim": 100_000.0, "deductible": 1_000.0},
    "PROPERTY": {"max_claim": 75_000.0, "deductible": 750.0},
}


@tool
def validate_against_policy(
    claim_type: str,
    amount: float,
    policy_number: str,
) -> dict[str, Any]:
    """Validate claim amount against policy coverage limits and deductibles.

    Args:
        claim_type: Type of insurance claim (AUTO/HEALTH/PROPERTY).
        amount: Claimed amount in dollars.
        policy_number: Policy identifier (used for context only; no live lookup).

    Returns:
        Dict with is_within_coverage, payable_amount, deductible_applied,
        and coverage_notes.
    """
    limits = COVERAGE_LIMITS.get(
        claim_type.upper(), {"max_claim": 10_000.0, "deductible": 500.0}
    )
    max_claim: float = limits["max_claim"]
    deductible: float = limits["deductible"]

    within_max = amount <= max_claim
    above_deductible = amount >= deductible

    notes: list[str] = []
    if not within_max:
        notes.append(
            f"Claim amount ${amount:,.2f} exceeds {claim_type.upper()} policy"
            f" limit of ${max_claim:,.2f}"
        )
    if not above_deductible:
        notes.append(
            f"Claim amount ${amount:,.2f} is below the ${deductible:,.2f}"
            " deductible — not payable"
        )

    is_within_coverage = within_max and above_deductible
    payable = round(max(0.0, min(amount, max_claim) - deductible), 2) if is_within_coverage else 0.0

    return {
        "is_within_coverage": is_within_coverage,
        "payable_amount": payable,
        "deductible_applied": deductible,
        "coverage_notes": notes,
    }


@tool
def validate_claim_type_specifics(
    claim_type: str,
    incident_description: str,
    amount: float,
) -> dict[str, Any]:
    """Apply claim-type-specific validation rules to the incident description.

    Args:
        claim_type: Type of insurance claim (AUTO/HEALTH/PROPERTY).
        incident_description: Free-text description of the incident.
        amount: Claimed amount in dollars.

    Returns:
        Dict with type_valid bool, type_issues list, and type_notes list.
    """
    issues: list[str] = []
    notes: list[str] = []
    desc_lower = incident_description.lower()

    if claim_type.upper() == "AUTO":
        if not any(
            word in desc_lower
            for word in ["collision", "accident", "theft", "damage", "flood"]
        ):
            issues.append("No recognisable auto incident type in description")
        notes.append("Auto claim: vehicle details and accident report required")

    elif claim_type.upper() == "HEALTH":
        if not any(
            word in desc_lower
            for word in ["surgery", "hospital", "treatment", "injury", "illness", "procedure"]
        ):
            issues.append("No recognisable medical event in description")
        notes.append("Health claim: diagnosis codes and treatment records required")

    elif claim_type.upper() == "PROPERTY":
        if not any(
            word in desc_lower
            for word in ["damage", "flood", "fire", "theft", "storm", "water"]
        ):
            issues.append("No recognisable property damage event in description")
        notes.append("Property claim: damage assessment and contractor estimate required")

    else:
        issues.append(f"Unknown claim type: {claim_type}")

    return {
        "type_valid": len(issues) == 0,
        "type_issues": issues,
        "type_notes": notes,
    }


def build_claim_validation_agent() -> Agent:
    """Build and return the ClaimValidationAgent.

    Returns:
        Configured ADK Agent instance ready to be wrapped in a Runner.
    """
    return Agent(
        name="ClaimValidationAgent",
        model="gemini-2.5-pro",
        description="Validates insurance claims against policy terms and type-specific rules",
        instruction="""You are a claims validation specialist for insurance policies.

Your job is to:
1. Use validate_against_policy to check if the claim amount is within coverage limits
   and above the deductible for the policy type.
2. Use validate_claim_type_specifics to apply type-specific rules to the description.

Output ONLY a JSON object (no markdown fences) with these exact keys:
- claim_valid: boolean — true only if both tools return no blocking issues
- payable_amount: float — calculated payable amount after deductible (0.0 if invalid)
- coverage_notes: list of strings describing coverage findings (may be empty)
- type_issues: list of strings for any type-specific validation failures (empty if none)
- validation_summary: a concise explanation of findings suitable for the claimant

Be precise about amounts. If a claim is partially valid, explain exactly what is and
is not covered in the validation_summary.""",
        tools=[validate_against_policy, validate_claim_type_specifics],
    )
