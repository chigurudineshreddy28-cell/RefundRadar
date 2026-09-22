/* ============================================================
   API + ERROR HANDLING + TOASTS
   The one rule this file exists to enforce: the user NEVER sees
   "undefined", "null", "[object Object]", "Failed to fetch" or a
   raw stack trace. Every error becomes a short, human sentence.
============================================================ */

function formatErrorDetail(detail) {
  if (detail === null || detail === undefined) {
    return "Something went wrong. Please try again.";
  }

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (item && typeof item === "object") {
          const field =
            Array.isArray(item.loc) && item.loc.length ? item.loc[item.loc.length - 1] : null;
          const msg = item.msg || item.message;
          if (field && msg) return `${field}: ${msg}`;
          if (msg) return msg;
        }
        return typeof item === "string" ? item : null;
      })
      .filter(Boolean);

    return parts.length ? parts.join("; ") : "Please check the required fields.";
  }

  if (typeof detail === "object") {
    if (typeof detail.msg === "string") return detail.msg;
    if (typeof detail.message === "string") return detail.message;
    return "Please check the required fields.";
  }

  return "Something went wrong. Please try again.";
}

/**
 * Makes a request to the FastAPI backend and always resolves to
 * parsed JSON, or throws an Error with a clean, human-readable message.
 *
 * @param {string} path   e.g. "/transactions/"
 * @param {object} options fetch options. Pass `body` as a plain object
 *                          for JSON requests, or a FormData instance
 *                          for file uploads.
 */
async function apiRequest(path, options = {}) {
  const { body, headers, ...rest } = options;

  const fetchOptions = { ...rest, headers: { ...(headers || {}) } };

  if (body instanceof FormData) {
    fetchOptions.body = body;
    // Do NOT set Content-Type — the browser sets the multipart boundary.
  } else if (body !== undefined) {
    fetchOptions.headers["Content-Type"] = "application/json";
    fetchOptions.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, fetchOptions);
  } catch (networkError) {
    throw new Error(
      "Unable to connect to the backend. Make sure the FastAPI server is running on " + API_BASE
    );
  }

  let payload = null;
  const text = await response.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch (parseError) {
      payload = null;
    }
  }

  if (!response.ok) {
    const detail = payload && typeof payload === "object" ? payload.detail : null;
    throw new Error(formatErrorDetail(detail) || `Request failed (${response.status})`);
  }

  return payload;
}

/* ============================================================
   TOASTS
============================================================ */
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const safeMessage =
    typeof message === "string" && message.trim() ? message : "Something happened.";

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = safeMessage;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.25s ease";
    setTimeout(() => toast.remove(), 250);
  }, 3800);
}
