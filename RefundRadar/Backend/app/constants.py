"""
Shared constants used across the API.

Keeping these in one place means the frontend and backend can never drift
apart on what a "valid" platform, status, or transaction type looks like.
"""

# Transaction lifecycle status.
# - completed  -> payment went through normally
# - pending    -> payment/order is still processing
# - cancelled  -> the order was cancelled (before or after payment)
# - failed     -> the payment attempt failed
TRANSACTION_STATUSES = ["completed", "pending", "cancelled", "failed"]

# What kind of transaction this is. Free-form enough to cover most
# everyday purchases without turning this into a huge enum.
TRANSACTION_TYPES = [
    "purchase",
    "subscription",
    "bill_payment",
    "food_order",
    "ride",
    "other",
]

# Refund lifecycle status, as *stored* in the database.
# The API also derives a "display_status" from this + due_date — see
# app/services/risk_engine.py / app/api/refunds.py -> calculate_display_status
REFUND_STATUSES = ["pending", "processing", "completed", "rejected"]

# Evidence file types we accept (matches the Supabase Storage bucket policy).
ALLOWED_EVIDENCE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "application/pdf": ".pdf",
}

MAX_EVIDENCE_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Small, dependency-free "logo" per platform (used by the frontend to
# render a colored badge). Falls back to a generic shopping-bag icon.
PLATFORM_LOGOS = {
    "amazon": "🛍️",
    "flipkart": "🛒",
    "myntra": "👗",
    "snapdeal": "🏷️",
    "zomato": "🍽️",
    "swiggy": "🍔",
    "uber": "🚗",
    "other": "💳",
}


def get_platform_logo(platform: str) -> str:
    return PLATFORM_LOGOS.get(platform.strip().lower(), PLATFORM_LOGOS["other"])
