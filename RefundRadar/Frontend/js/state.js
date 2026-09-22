/* ============================================================
   GLOBAL STATE + DATA LOADERS

   Loading order matters (this is exactly what caused bugs in the
   old project): transactions must exist in memory BEFORE we ask
   for evidence, because evidence lookups are keyed by
   transaction_id.
============================================================ */

const appState = {
  transactions: [],
  refunds: [],
  evidence: [],
  dashboardSummary: null,
  riskSummary: null,
  backendOnline: null, // null = unknown, true/false once checked
};

function getTransactionById(transactionId) {
  return appState.transactions.find((t) => t.transaction_id === transactionId) || null;
}

function getRefundsForTransaction(transactionId) {
  return appState.refunds.filter((r) => r.transaction_id === transactionId);
}

function getEvidenceForTransaction(transactionId) {
  return appState.evidence.filter((e) => e.transaction_id === transactionId);
}

async function checkBackendHealth() {
  try {
    await apiRequest("/", { method: "GET" });
    appState.backendOnline = true;
  } catch (error) {
    appState.backendOnline = false;
  }
  return appState.backendOnline;
}

async function loadTransactions() {
  const data = await apiRequest("/transactions/", { method: "GET" });
  appState.transactions = Array.isArray(data) ? data : [];
  return appState.transactions;
}

async function loadRefunds() {
  const data = await apiRequest("/refunds/", { method: "GET" });
  appState.refunds = Array.isArray(data) ? data : [];
  return appState.refunds;
}

async function loadEvidence() {
  // Loaded AFTER transactions/refunds exist, using the single
  // "list everything" endpoint (fast — one request instead of one
  // per transaction, which is what caused slow/broken loading before).
  const data = await apiRequest("/evidence/", { method: "GET" });
  appState.evidence = Array.isArray(data) ? data : [];
  return appState.evidence;
}

async function loadDashboard() {
  const [summary, risk] = await Promise.all([
    apiRequest("/dashboard/summary", { method: "GET" }),
    apiRequest("/dashboard/risk-summary", { method: "GET" }),
  ]);
  appState.dashboardSummary = summary;
  appState.riskSummary = risk;
  return { summary, risk };
}

/**
 * Loads everything in the correct order, then renders every view.
 * Called on startup and after any create/update/delete so the whole
 * app always reflects the backend, never stale local data.
 */
async function loadAllData() {
  try {
    // 1 & 2: transactions
    await loadTransactions();

    // 3 & 4: refunds
    await loadRefunds();

    // 5 & 6: evidence (needs transactions/refunds to exist first)
    await loadEvidence();

    // dashboard summary numbers (server-calculated, never hardcoded)
    await loadDashboard();

    // 7-10: render everything from the freshly loaded state
    renderEverything();
  } catch (error) {
    showToast(error.message, "error");
  }
}
