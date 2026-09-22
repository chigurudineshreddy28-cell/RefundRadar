from fastapi import APIRouter

from app.api.refunds import calculate_display_status
from app.supabase_client import supabase

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def dashboard_summary():
    transactions = supabase.table("transactions").select("*").execute().data
    refunds = supabase.table("refunds").select("*").execute().data

    buckets: dict[str, list] = {
        "pending": [],
        "processing": [],
        "due_soon": [],
        "overdue": [],
        "completed": [],
        "rejected": [],
    }

    for refund in refunds:
        buckets[calculate_display_status(refund)].append(refund)

    def total(rows):
        return round(sum(float(r["refund_amount"]) for r in rows), 2)

    active_pending = buckets["pending"] + buckets["processing"] + buckets["due_soon"]

    failed_payments = [t for t in transactions if t["status"] == "failed"]
    cancelled_orders = [t for t in transactions if t["status"] == "cancelled"]

    return {
        # transactions
        "total_transactions": len(transactions),
        "total_transaction_value": round(sum(float(t["amount"]) for t in transactions), 2),
        "failed_payments_count": len(failed_payments),
        "cancelled_orders_count": len(cancelled_orders),
        # refunds — counts
        "total_refunds_tracked": len(refunds),
        "pending_refunds": len(active_pending),
        "processing_refunds": len(buckets["processing"]),
        "due_soon_refunds": len(buckets["due_soon"]),
        "overdue_refunds": len(buckets["overdue"]),
        "received_refunds": len(buckets["completed"]),
        "rejected_refunds": len(buckets["rejected"]),
        # refunds — amounts (used by the dashboard summary cards)
        "pending_refund_amount": total(active_pending),
        "overdue_refund_amount": total(buckets["overdue"]),
        "received_refund_amount": total(buckets["completed"]),
        "total_refund_amount": total(refunds),
    }


@router.get("/risk-summary")
def risk_summary():
    refunds = supabase.table("refunds").select("risk_score, risk_level").execute().data

    return {
        "high": len([r for r in refunds if r.get("risk_level") == "HIGH"]),
        "medium": len([r for r in refunds if r.get("risk_level") == "MEDIUM"]),
        "low": len([r for r in refunds if r.get("risk_level") == "LOW"]),
        "average_score": (
            round(sum(r.get("risk_score") or 0 for r in refunds) / len(refunds), 1)
            if refunds
            else 0
        ),
    }
