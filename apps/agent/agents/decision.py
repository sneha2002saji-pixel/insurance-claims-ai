from __future__ import annotations

from typing import Any

import structlog
from google.adk.agents import Agent

logger = structlog.get_logger(__name__)

# Thresholds that trigger mandatory human review
HITL_AMOUNT_THRESHOLD: float = 10_000.0
HITL_FRAUD_THRESHOLD: float = 0.7


def evaluate_hitl_trigger(amount: float, fraud_score: float) -> dict[str, Any]:
    """Determine whether this claim requires human review before a decision is made.

    A claim requires human review (HITL) when:
    - The amount exceeds $10,000, OR
    - The fraud score is >= 0.7, OR
    - Both conditions are true.

    Args:
        amount: Claim amount in dollars.
        fraud_score: Fraud risk score from FraudDetectionAgent (0.0–1.0).

    Returns:
        Dict with requires_hitl bool, trigger_reason string, and the
        threshold values used.
    """
    high_amount = amount > HITL_AMOUNT_THRESHOLD
    high_fraud = fraud_score >= HITL_FRAUD_THRESHOLD

    trigger_reason: str | None
    if high_amount and high_fraud:
        trigger_reason = "both"
    elif high_amount:
        trigger_reason = "high_amount"
    elif high_fraud:
        trigger_reason = "high_fraud_risk"
    else:
        trigger_reason = None

    return {
        "requires_hitl": high_amount or high_fraud,
        "trigger_reason": trigger_reason,
        "amount_threshold": HITL_AMOUNT_THRESHOLD,
        "fraud_threshold": HITL_FRAUD_THRESHOLD,
    }


def make_claim_decision(
    claim_valid: bool,
    within_coverage: bool,
    fraud_score: float,
    payable_amount: float,
    type_issues: list[str],
    authenticity_flags: list[str],
) -> dict[str, Any]:
    """Make the final claim decision based on all pipeline findings.

    Decision logic (evaluated in order):
    1. Hard reject — claim failed validation or is out of coverage.
    2. Hard reject — fraud score >= 0.85 (near-certain fraud).
    3. Partial settlement — medium fraud risk (0.5–0.84) combined with
       document authenticity issues.
    4. Approve — all validations passed.

    Args:
        claim_valid: Whether the claim passed type-specific validation.
        within_coverage: Whether the amount is within policy limits and above
            deductible.
        fraud_score: Fraud risk score (0.0–1.0).
        payable_amount: Payable amount calculated by ClaimValidationAgent.
        type_issues: List of type-specific validation failures.
        authenticity_flags: Document authenticity issues from
            DocumentVerificationAgent.

    Returns:
        Dict with decision string, final_amount float, and decision_reason.
    """
    # 1. Hard reject: validation or coverage failure
    if not claim_valid or not within_coverage:
        return {
            "decision": "rejected",
            "final_amount": 0.0,
            "decision_reason": (
                "; ".join(type_issues)
                if type_issues
                else "Claim did not meet policy requirements"
            ),
        }

    # 2. Hard reject: very high fraud confidence
    if fraud_score >= 0.85:
        return {
            "decision": "rejected",
            "final_amount": 0.0,
            "decision_reason": (
                f"Claim rejected due to high fraud risk score ({fraud_score:.2f})"
            ),
        }

    # 3. Partial settlement: medium-high fraud + authenticity issues
    if fraud_score >= 0.50 and authenticity_flags:
        return {
            "decision": "partial_settlement",
            "final_amount": round(payable_amount * 0.60, 2),
            "decision_reason": (
                "Partial settlement offered due to unresolved authenticity concerns"
            ),
        }

    # 4. Full approval
    return {
        "decision": "agent_approved",
        "final_amount": payable_amount,
        "decision_reason": "Claim approved — all validations passed",
    }


def build_decision_agent() -> Agent:
    """Build and return the DecisionAgent.

    Returns:
        Configured ADK Agent instance ready to be wrapped in a Runner.
    """
    return Agent(
        name="DecisionAgent",
        model="gemini-2.5-pro",
        description="Makes final claim decisions and determines if human review is needed",
        instruction="""You are the final decision maker for insurance claim processing.

You have access to all prior pipeline findings. Your job is to:

STEP 1 — Always call evaluate_hitl_trigger first with the claim amount and fraud_score.

STEP 2 — Based on the result:
  - If requires_hitl is TRUE: output hitl_required=true and STOP. Do NOT call
    make_claim_decision. Leave decision, final_amount as null.
  - If requires_hitl is FALSE: call make_claim_decision with all the pipeline findings,
    then output the full result.

Output ONLY a JSON object (no markdown fences) with these exact keys:
- hitl_required: boolean
- trigger_reason: "high_amount" / "high_fraud_risk" / "both" / null
- decision: "agent_approved" / "rejected" / "partial_settlement" / null
- final_amount: float or null (0.0 means rejected; null means HITL — do not pay yet)
- decision_reason: string explanation suitable for the claimant
- processing_summary: brief overall summary of the claim assessment

Your decisions must be fair, consistent, and clearly explained. Never fabricate numbers
or reasons beyond what the tools return.""",
        tools=[evaluate_hitl_trigger, make_claim_decision],
    )
