from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.constants import TRANSACTION_STATUSES, TRANSACTION_TYPES, get_platform_logo
from app.supabase_client import supabase

router = APIRouter(prefix="/transactions", tags=["Transactions"])


# ============================================================
# Schemas
# ============================================================

class TransactionCreate(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=100)
    order_id: str = Field(min_length=1, max_length=100)
    platform: str = Field(min_length=1, max_length=50)
    transaction_type: str = Field(default="purchase")
    amount: float = Field(gt=0, le=10_000_000)
    transaction_date: date
    status: str = Field(default="completed")

    @field_validator("transaction_id", "order_id", "platform")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field cannot be empty")
        return v

    @field_validator("transaction_type")
    @classmethod
    def valid_type(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in TRANSACTION_TYPES:
            raise ValueError(f"transaction_type must be one of {TRANSACTION_TYPES}")
        return v

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in TRANSACTION_STATUSES:
            raise ValueError(f"status must be one of {TRANSACTION_STATUSES}")
        return v


class TransactionUpdate(BaseModel):
    order_id: str = Field(min_length=1, max_length=100)
    platform: str = Field(min_length=1, max_length=50)
    transaction_type: str = Field(default="purchase")
    amount: float = Field(gt=0, le=10_000_000)
    transaction_date: date
    status: str

    @field_validator("order_id", "platform")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field cannot be empty")
        return v

    @field_validator("transaction_type")
    @classmethod
    def valid_type(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in TRANSACTION_TYPES:
            raise ValueError(f"transaction_type must be one of {TRANSACTION_TYPES}")
        return v

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in TRANSACTION_STATUSES:
            raise ValueError(f"status must be one of {TRANSACTION_STATUSES}")
        return v


# ============================================================
# Helpers
# ============================================================

def _find_transaction(transaction_id: str):
    return (
        supabase.table("transactions")
        .select("*")
        .eq("transaction_id", transaction_id)
        .execute()
        .data
    )


# ============================================================
# Routes
# ============================================================

@router.post("/", status_code=201)
def create_transaction(transaction: TransactionCreate):
    if _find_transaction(transaction.transaction_id):
        raise HTTPException(status_code=409, detail="Transaction ID already exists")

    row = {
        "transaction_id": transaction.transaction_id,
        "order_id": transaction.order_id,
        "platform": transaction.platform,
        "platform_logo": get_platform_logo(transaction.platform),
        "transaction_type": transaction.transaction_type,
        "amount": transaction.amount,
        "transaction_date": transaction.transaction_date.isoformat(),
        "status": transaction.status,
    }

    try:
        response = supabase.table("transactions").insert(row).execute()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Could not save transaction: {exc}") from exc

    return response.data[0] if response.data else row


@router.get("/")
def list_transactions():
    response = (
        supabase.table("transactions")
        .select("*")
        .order("transaction_date", desc=True)
        .execute()
    )
    return response.data


@router.get("/{transaction_id}")
def get_transaction(transaction_id: str):
    rows = _find_transaction(transaction_id)
    if not rows:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return rows[0]


@router.put("/{transaction_id}")
def update_transaction(transaction_id: str, transaction: TransactionUpdate):
    if not _find_transaction(transaction_id):
        raise HTTPException(status_code=404, detail="Transaction not found")

    row = {
        "order_id": transaction.order_id,
        "platform": transaction.platform,
        "platform_logo": get_platform_logo(transaction.platform),
        "transaction_type": transaction.transaction_type,
        "amount": transaction.amount,
        "transaction_date": transaction.transaction_date.isoformat(),
        "status": transaction.status,
    }

    response = (
        supabase.table("transactions")
        .update(row)
        .eq("transaction_id", transaction_id)
        .execute()
    )
    return response.data[0] if response.data else row


@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: str):
    if not _find_transaction(transaction_id):
        raise HTTPException(status_code=404, detail="Transaction not found")

    supabase.table("transactions").delete().eq("transaction_id", transaction_id).execute()

    return {"message": "Transaction deleted successfully", "transaction_id": transaction_id}
