from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from app.constants import REFUND_STATUSES
from app.services.risk_engine import calculate_risk
from app.supabase_client import supabase

router = APIRouter(prefix="/refunds", tags=["Refunds"])


# ============================================================
# Schemas
# ============================================================

class RefundCreate(BaseModel):
    transaction_id: str = Field(min_length=1)
    refund_amount: float = Field(gt=0, le=10_000_000)
    reason: str = Field(min_length=3, max_length=500)
    applied_date: date
    due_date: date
    status: str = Field(default="pending")

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in REFUND_STATUSES:
            raise ValueError(f"status must be one of {REFUND_STATUSES}")
        return v

    @model_validator(mode="after")
    def due_after_applied(self):
        if self.due_date < self.applied_date:
            raise ValueError("Due date cannot be before applied date")
        return self


class RefundUpdate(BaseModel):
    refund_amount: float = Field(gt=0, le=10_000_000)
    reason: str = Field(min_length=3, max_length=500)
    applied_date: date
    due_date: date
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in REFUND_STATUSES:
            raise ValueError(f"status must be one of {REFUND_STATUSES}")
        return v

    @model_validator(mode="after")
    def due_after_applied(self):
        if self.due_date < self.applied_date:
            raise ValueError("Due date cannot be before applied date")
        return self


# ============================================================
# Helpers
# ============================================================

def _get_transaction(transaction_id: str):
    return (
        supabase.table("transactions")
        .select("*")
        .eq("transaction_id", transaction_id)
        .execute()
        .data
    )


def _get_transaction_refunds(transaction_id: str):
    return (
        supabase.table("refunds")
        .select("*")
        .eq("transaction_id", transaction_id)
        .execute()
        .data
    )


def calculate_display_status(refund: dict) -> str:
    """
    Turns the stored status + due_date into the status the UI shows.

      completed / rejected  -> shown as-is (final states)
      otherwise:
        due_date already passed      -> "overdue"
        due_date within 2 days       -> "due_soon"
        else                         -> the stored status
                                         ("pending" or "processing")
    """
    status = refund.get("status", "pending")

    if status in ("completed", "rejected"):
        return status

    due_date = refund.get("due_date")
    if not due_date:
        return status

    if isinstance(due_date, str):
        due_date = date.fromisoformat(due_date[:10])

    days_remaining = (due_date - date.today()).days

    if days_remaining < 0:
        return "overdue"
    if days_remaining <= 2:
        return "due_soon"
    return status


def _attach_display_status(refund: dict) -> dict:
    refund["display_status"] = calculate_display_status(refund)
    return refund


# ============================================================
# Routes
# ============================================================

@router.post("/", status_code=201)
def create_refund(refund: RefundCreate):
    transaction = _get_transaction(refund.transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    existing_refunds = _get_transaction_refunds(refund.transaction_id)
    refund_count = len(existing_refunds) + 1

    risk = calculate_risk(refund.refund_amount, refund_count, refund.status)

    row = {
        "transaction_id": refund.transaction_id,
        "refund_amount": refund.refund_amount,
        "reason": refund.reason,
        "applied_date": refund.applied_date.isoformat(),
        "due_date": refund.due_date.isoformat(),
        "status": refund.status,
        "risk_score": risk["risk_score"],
        "risk_level": risk["risk_level"],
        "risk_reasons": risk["risk_reasons"],
    }

    try:
        response = supabase.table("refunds").insert(row).execute()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Could not save refund: {exc}") from exc

    saved = response.data[0] if response.data else row
    return _attach_display_status(saved)


@router.post("/risk")
def analyze_refund_risk(refund: RefundCreate):
    transaction = _get_transaction(refund.transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    existing_refunds = _get_transaction_refunds(refund.transaction_id)
    refund_count = len(existing_refunds) + 1

    return calculate_risk(refund.refund_amount, refund_count, refund.status)


@router.get("/overdue")
def get_overdue_refunds():
    response = supabase.table("refunds").select("*").execute()
    overdue = [_attach_display_status(r) for r in response.data if calculate_display_status(r) == "overdue"]
    return overdue


@router.get("/")
def list_refunds():
    response = supabase.table("refunds").select("*").order("due_date").execute()
    return [_attach_display_status(r) for r in response.data]


@router.get("/{refund_id}")
def get_refund(refund_id: int):
    rows = supabase.table("refunds").select("*").eq("id", refund_id).execute().data
    if not rows:
        raise HTTPException(status_code=404, detail="Refund not found")
    return _attach_display_status(rows[0])


@router.put("/{refund_id}")
def update_refund(refund_id: int, refund: RefundUpdate):
    existing = supabase.table("refunds").select("*").eq("id", refund_id).execute().data
    if not existing:
        raise HTTPException(status_code=404, detail="Refund not found")

    sibling_refunds = _get_transaction_refunds(existing[0]["transaction_id"])
    risk = calculate_risk(refund.refund_amount, max(len(sibling_refunds), 1), refund.status)

    row = {
        "refund_amount": refund.refund_amount,
        "reason": refund.reason,
        "applied_date": refund.applied_date.isoformat(),
        "due_date": refund.due_date.isoformat(),
        "status": refund.status,
        "risk_score": risk["risk_score"],
        "risk_level": risk["risk_level"],
        "risk_reasons": risk["risk_reasons"],
    }

    response = supabase.table("refunds").update(row).eq("id", refund_id).execute()
    saved = response.data[0] if response.data else row
    return _attach_display_status(saved)


@router.delete("/{refund_id}")
def delete_refund(refund_id: int):
    existing = supabase.table("refunds").select("id").eq("id", refund_id).execute().data
    if not existing:
        raise HTTPException(status_code=404, detail="Refund not found")

    supabase.table("refunds").delete().eq("id", refund_id).execute()

    return {"message": "Refund deleted successfully", "refund_id": refund_id}
