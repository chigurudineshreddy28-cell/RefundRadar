/* ============================================================
   APP INIT + NAVIGATION
============================================================ */

function goToView(viewId) {
  // Re-enable any fields left disabled by a previous "edit" flow.
  const txnIdField = document.getElementById("txn-id");
  const refundTxnField = document.getElementById("refund-transaction");
  if (txnIdField) txnIdField.disabled = false;
  if (refundTxnField) refundTxnField.disabled = false;

  document.querySelectorAll(".view").forEach((v) => v.classList.add("hidden"));
  const target = document.getElementById(`view-${viewId}`);
  if (target) target.classList.remove("hidden");

  document.querySelectorAll(".nav-item").forEach((n) => {
    n.classList.toggle("active", n.dataset.view === viewId);
  });

  closeSidebarMobile();
  window.scrollTo(0, 0);
}

function closeSidebarMobile() {
  document.getElementById("sidebar").classList.remove("open");
  document.getElementById("sidebar-backdrop").classList.remove("open");
}

function updateBackendIndicator() {
  const dot = document.querySelector("#backend-indicator .dot");
  const text = document.getElementById("backend-indicator-text");
  const settingsStatus = document.getElementById("settings-backend-status");

  if (appState.backendOnline === true) {
    dot.className = "dot dot-online";
    text.textContent = "Backend connected";
    if (settingsStatus) settingsStatus.textContent = "Connected ✅";
  } else if (appState.backendOnline === false) {
    dot.className = "dot dot-offline";
    text.textContent = "Backend unavailable";
    if (settingsStatus) settingsStatus.textContent = "Unable to connect. Start FastAPI (uvicorn app.main:app --reload).";
  } else {
    dot.className = "dot dot-checking";
    text.textContent = "Checking backend…";
    if (settingsStatus) settingsStatus.textContent = "Checking…";
  }
}

function loadSettingsIntoView() {
  document.getElementById("settings-api-base").textContent = API_BASE;
  document.getElementById("settings-display-name").value = localStorage.getItem(LS_KEYS.DISPLAY_NAME) || "";
  updateBackendIndicator();
}

/* ============================================================
   INIT
============================================================ */

document.addEventListener("DOMContentLoaded", async () => {
  // --- backend health check (drives splash status + sidebar dot) ---
  const splashStatus = document.getElementById("splash-status");
  await checkBackendHealth();
  updateBackendIndicator();

  if (appState.backendOnline) {
    splashStatus.textContent = "Backend connected — ready to go.";
  } else {
    splashStatus.textContent =
      "Backend unavailable — start FastAPI (uvicorn app.main:app --reload) on " + API_BASE;
  }

  // --- splash -> app shell ---
  document.getElementById("btn-get-started").addEventListener("click", async () => {
    document.getElementById("view-splash").classList.add("hidden");
    document.getElementById("app-shell").classList.remove("hidden");
    await loadAllData();
    loadSettingsIntoView();
  });

  // --- sidebar nav ---
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => goToView(btn.dataset.view));
  });

  // --- generic "go to view" buttons (Cancel, +Add Transaction/Refund cards) ---
  document.querySelectorAll("[data-goto]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.goto;
      if (target === "add-transaction") resetTransactionForm();
      if (target === "add-refund") resetRefundForm();
      goToView(target);
    });
  });

  // --- dashboard "view all" links ---
  document.querySelectorAll("[data-view-link]").forEach((btn) => {
    btn.addEventListener("click", () => goToView(btn.dataset.viewLink));
  });

  // --- header add-transaction shortcut ---
  document.getElementById("btn-add-transaction-header").addEventListener("click", () => {
    resetTransactionForm();
    goToView("add-transaction");
  });

  // --- evidence vault upload button ---
  document.getElementById("btn-upload-evidence").addEventListener("click", openEvidenceUploadModal);

  // --- mobile sidebar toggle ---
  document.getElementById("btn-hamburger").addEventListener("click", () => {
    document.getElementById("sidebar").classList.add("open");
    document.getElementById("sidebar-backdrop").classList.add("open");
  });
  document.getElementById("sidebar-backdrop").addEventListener("click", closeSidebarMobile);

  // --- transactions tabs + search ---
  document.querySelectorAll("#transactions-tabs .tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll("#transactions-tabs .tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      transactionsFilter = tab.dataset.filter;
      renderTransactionsList();
    });
  });
  document.getElementById("transactions-search").addEventListener("input", renderTransactionsList);

  // --- refunds tabs + search ---
  document.querySelectorAll("#refunds-tabs .tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll("#refunds-tabs .tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      refundsFilter = tab.dataset.filter;
      renderRefundsList();
    });
  });
  document.getElementById("refunds-search").addEventListener("input", renderRefundsList);

  // --- other search boxes ---
  document.getElementById("failed-search").addEventListener("input", renderFailedPayments);
  document.getElementById("cancelled-search").addEventListener("input", renderCancelledOrders);
  document.getElementById("evidence-search").addEventListener("input", renderEvidenceGrid);

  // --- global header search: jump to Transactions and filter there ---
  document.getElementById("global-search").addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    const query = e.target.value.trim();
    goToView("transactions");
    document.getElementById("transactions-search").value = query;
    renderTransactionsList();
  });

  // --- modal close handlers ---
  document.getElementById("modal-close").addEventListener("click", closeModal);
  document.getElementById("modal-overlay").addEventListener("click", (e) => {
    if (e.target.id === "modal-overlay") closeModal();
  });

  document.getElementById("confirm-close").addEventListener("click", closeConfirm);
  document.getElementById("confirm-cancel").addEventListener("click", closeConfirm);
  document.getElementById("confirm-overlay").addEventListener("click", (e) => {
    if (e.target.id === "confirm-overlay") closeConfirm();
  });
  document.getElementById("confirm-ok").addEventListener("click", async () => {
    const callback = confirmCallback;
    closeConfirm();
    if (callback) await callback();
  });

  // --- settings ---
  document.getElementById("btn-save-settings").addEventListener("click", () => {
    const name = document.getElementById("settings-display-name").value.trim();
    if (name) {
      localStorage.setItem(LS_KEYS.DISPLAY_NAME, name);
    } else {
      localStorage.removeItem(LS_KEYS.DISPLAY_NAME);
    }
    showToast("Settings saved", "success");
    renderDashboard();
  });

  // --- forms ---
  initTransactionForm();
  initRefundForm();
  resetTransactionForm();
  resetRefundForm();
});
