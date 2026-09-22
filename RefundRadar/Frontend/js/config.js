/* ============================================================
   CONFIG — one place to change the backend URL, platform icons,
   and status label/color mappings.
============================================================ */

// Change this if your FastAPI backend runs somewhere else.
const API_BASE = "http://127.0.0.1:8000";

const LS_KEYS = {
  DISPLAY_NAME: "refundradar_display_name",
  SEEN_SPLASH: "refundradar_seen_splash",
};

const PLATFORM_LOGOS = {
  amazon: "🛍️",
  flipkart: "🛒",
  myntra: "👗",
  snapdeal: "🏷️",
  zomato: "🍽️",
  swiggy: "🍔",
  uber: "🚗",
};

function platformLogo(platform) {
  if (!platform) return "💳";
  return PLATFORM_LOGOS[String(platform).trim().toLowerCase()] || "💳";
}

const TRANSACTION_TYPE_LABELS = {
  purchase: "Purchase",
  subscription: "Subscription",
  bill_payment: "Bill Payment",
  food_order: "Food Order",
  ride: "Ride",
  other: "Other",
};

const TRANSACTION_STATUS_LABELS = {
  completed: "Completed",
  pending: "Pending",
  cancelled: "Cancelled",
  failed: "Failed",
};

const REFUND_DISPLAY_STATUS_LABELS = {
  pending: "Pending",
  processing: "Processing",
  due_soon: "Due Soon",
  overdue: "Overdue",
  completed: "Received",
  rejected: "Rejected",
};

function formatCurrency(amount) {
  const value = Number(amount);
  if (Number.isNaN(value)) return "₹0";
  return "₹" + value.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function formatDate(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}
