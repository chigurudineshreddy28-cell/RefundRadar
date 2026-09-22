"""
Rule-based, fully explainable refund risk engine.

IMPORTANT: this is NOT an AI/ML prediction. It is a simple, transparent
points system so a user can always see exactly *why* a refund got the
score it did (risk_reasons). Every rule and its weight is listed below —
nothing hidden.

Scoring rules
-------------
Refund amount > ₹1000                          -> +40
Refund amount > ₹500  (and <= ₹1000)            -> +20
More than 3 refund requests on the transaction  -> +40
More than 1 refund request on the transaction   -> +20  (and <= 3)
Refund status is "rejected"                     -> +30

Score is capped at 100.

Risk levels
-----------
0-29   -> LOW
30-59  -> MEDIUM
60-100 -> HIGH
"""

from typing import Literal

RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]


def get_risk_category(risk_score: int) -> RiskLevel:
    if risk_score >= 60:
        return "HIGH"
    if risk_score >= 30:
        return "MEDIUM"
    return "LOW"


def calculate_risk(refund_amount: float, refund_count: int, status: str = "pending") -> dict:
    """
    refund_amount: the amount of *this* refund request
    refund_count:  how many refund requests exist for the transaction,
                   INCLUDING this one
    status:        the stored status of this refund ("pending",
                   "processing", "completed", "rejected")
    """
    risk_score = 0
    reasons: list[str] = []

    if refund_amount > 1000:
        risk_score += 40
        reasons.append("High refund amount (over ₹1,000)")
    elif refund_amount > 500:
        risk_score += 20
        reasons.append("Moderately high refund amount (over ₹500)")

    if refund_count > 3:
        risk_score += 40
        reasons.append("Multiple refund requests on this transaction (more than 3)")
    elif refund_count > 1:
        risk_score += 20
        reasons.append("Repeated refund activity on this transaction")

    if status == "rejected":
        risk_score += 30
        reasons.append("Refund was rejected")

    risk_score = min(risk_score, 100)

    if not reasons:
        reasons.append("No significant risk factors detected")

    return {
        "risk_score": risk_score,
        "risk_level": get_risk_category(risk_score),
        "risk_reasons": reasons,
    }
