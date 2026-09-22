/* ============================================================
   RENDERING
   Every render function reads straight from appState — nothing
   here is hardcoded, and nothing here talks to the network.
============================================================ */

function el(tag, className, html) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (html !== undefined) node.innerHTML = html;
  return node;
}

function statusPillHtml(status, labelMap) {
  const key = status || "pending";
  const label = (labelMap && labelMap[key]) || key.replace(/_/g, " ");
  return `<span class="pill pill-${key}"><span class="pill-dot"></span>${escapeHtml(label)}</span>`;
}

function riskPillHtml(level) {
  const safe = level || "LOW";
  return `<span class="pill risk-pill-${safe}">${escapeHtml(safe)}</span>`;
}

function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function buildTransactionRow(txn) {
  const row = el("div", "row-item");
  row.dataset.transactionId = txn.transaction_id;

  const refundCount = getRefundsForTransaction(txn.transaction_id).length;
  const subtitleParts = [`Order #${txn.order_id}`, txn.transaction_id];
  if (refundCount) subtitleParts.push(`${refundCount} refund${refundCount > 1 ? "s" : ""}`);

  row.innerHTML = `
    <div class="row-logo">${platformLogo(txn.platform)}</div>
    <div class="row-main">
      <div class="row-title">${escapeHtml(txn.platform || "Unknown platform")}</div>
      <div class="row-subtitle">${escapeHtml(subtitleParts.join(" · "))}</div>
    </div>
    <div class="row-meta">
      <div class="row-amount">${formatCurrency(txn.amount)}</div>
      <div class="row-date">${formatDate(txn.transaction_date)}</div>
    </div>
    ${statusPillHtml(txn.status, TRANSACTION_STATUS_LABELS)}
    <span class="row-chevron">›</span>
  `;

  row.addEventListener("click", () => openTransactionDetail(txn.transaction_id));
  return row;
}

function buildRefundRow(refund) {
  const row = el("div", "row-item");
  row.dataset.refundId = refund.id;

  const txn = getTransactionById(refund.transaction_id);
  const subtitleParts = [`Txn: ${refund.transaction_id}`, `Refund #${refund.id}`];

  row.innerHTML = `
    <div class="row-logo">${platformLogo(txn ? txn.platform : "")}</div>
    <div class="row-main">
      <div class="row-title">${escapeHtml(txn ? txn.platform : "Unknown transaction")}</div>
      <div class="row-subtitle">${escapeHtml(subtitleParts.join(" · "))} · Due ${formatDate(refund.due_date)}</div>
    </div>
    <div class="row-meta">
      <div class="row-amount">${formatCurrency(refund.refund_amount)}</div>
      <div class="row-date">${riskPillHtml(refund.risk_level)}</div>
    </div>
    ${statusPillHtml(refund.display_status, REFUND_DISPLAY_STATUS_LABELS)}
    <span class="row-chevron">›</span>
  `;

  row.addEventListener("click", () => openRefundDetail(refund.id));
  return row;
}

function matchesSearch(haystack, query) {
  if (!query) return true;
  return haystack.toLowerCase().includes(query.toLowerCase());
}

/* ---------------- DASHBOARD ---------------- */

function renderDashboard() {
  const summary = appState.dashboardSummary;
  const risk = appState.riskSummary;

  const displayName = localStorage.getItem(LS_KEYS.DISPLAY_NAME);
  const hour = new Date().getHours();
  const greetingWord = hour < 12 ? "Good Morning" : hour < 17 ? "Good Afternoon" : "Good Evening";
  const greetingEl = document.getElementById("dashboard-greeting");
  if (greetingEl) {
    greetingEl.textContent = displayName
      ? `${greetingWord}, ${displayName} 👋`
      : `${greetingWord} 👋`;
  }

  if (summary) {
    document.getElementById("kpi-total-value").textContent = formatCurrency(
      summary.total_transaction_value
    );
    document.getElementById("kpi-total-sub").textContent = `${summary.total_transactions} transactions`;

    document.getElementById("kpi-received-value").textContent = formatCurrency(
      summary.received_refund_amount
    );
    document.getElementById("kpi-received-sub").textContent = `${summary.received_refunds} refunds`;

    document.getElementById("kpi-pending-value").textContent = formatCurrency(
      summary.pending_refund_amount
    );
    document.getElementById("kpi-pending-sub").textContent = `${summary.pending_refunds} refunds`;

    document.getElementById("kpi-overdue-value").textContent = formatCurrency(
      summary.overdue_refund_amount
    );
    document.getElementById("kpi-overdue-sub").textContent = `${summary.overdue_refunds} refunds`;
  }

  // Recent transactions (latest 5)
  const list = document.getElementById("recent-transactions-list");
  const emptyState = document.getElementById("recent-transactions-empty");
  list.innerHTML = "";

  const recent = [...appState.transactions]
    .sort((a, b) => new Date(b.transaction_date) - new Date(a.transaction_date))
    .slice(0, 5);

  if (!recent.length) {
    emptyState.classList.remove("hidden");
  } else {
    emptyState.classList.add("hidden");
    recent.forEach((txn) => list.appendChild(buildTransactionRow(txn)));
  }

  // Risk overview
  const riskContainer = document.getElementById("risk-overview");
  riskContainer.innerHTML = "";
  if (risk) {
    const total = Math.max(risk.low + risk.medium + risk.high, 1);
    const rows = [
      { label: "Low", count: risk.low, color: "var(--mint-500)" },
      { label: "Medium", count: risk.medium, color: "#f5a623" },
      { label: "High", count: risk.high, color: "var(--red-600)" },
    ];
    rows.forEach((r) => {
      const pct = Math.round((r.count / total) * 100);
      const rowEl = el(
        "div",
        "risk-bar-row",
        `
        <span class="risk-bar-label">${r.label}</span>
        <span class="risk-bar-track"><span class="risk-bar-fill" style="width:${pct}%;background:${r.color}"></span></span>
        <span class="risk-bar-count">${r.count}</span>
      `
      );
      riskContainer.appendChild(rowEl);
    });
  }
}

/* ---------------- TRANSACTIONS ---------------- */

let transactionsFilter = "all";

function renderTransactionsList() {
  const search = document.getElementById("transactions-search").value.trim();
  const list = document.getElementById("transactions-list");
  const emptyState = document.getElementById("transactions-empty");
  list.innerHTML = "";

  let rows = [...appState.transactions];

  if (transactionsFilter === "refunds") {
    const txnIdsWithRefunds = new Set(appState.refunds.map((r) => r.transaction_id));
    rows = rows.filter((t) => txnIdsWithRefunds.has(t.transaction_id));
  } else if (transactionsFilter === "failed") {
    rows = rows.filter((t) => t.status === "failed");
  } else if (transactionsFilter === "cancelled") {
    rows = rows.filter((t) => t.status === "cancelled");
  }

  if (search) {
    rows = rows.filter((t) =>
      matchesSearch(`${t.platform} ${t.order_id} ${t.transaction_id}`, search)
    );
  }

  rows.sort((a, b) => new Date(b.transaction_date) - new Date(a.transaction_date));

  if (!rows.length) {
    emptyState.classList.remove("hidden");
  } else {
    emptyState.classList.add("hidden");
    rows.forEach((t) => list.appendChild(buildTransactionRow(t)));
  }
}

/* ---------------- REFUNDS ---------------- */

let refundsFilter = "all";

function refundMatchesFilter(refund, filter) {
  if (filter === "all") return true;
  if (filter === "received") return refund.display_status === "completed";
  if (filter === "pending") return ["pending", "due_soon"].includes(refund.display_status);
  return refund.display_status === filter;
}

function renderRefundsList() {
  const search = document.getElementById("refunds-search").value.trim();
  const list = document.getElementById("refunds-list");
  const emptyState = document.getElementById("refunds-empty");
  list.innerHTML = "";

  let rows = appState.refunds.filter((r) => refundMatchesFilter(r, refundsFilter));

  if (search) {
    rows = rows.filter((r) => {
      const txn = getTransactionById(r.transaction_id);
      return matchesSearch(
        `${r.transaction_id} ${r.id} ${txn ? txn.platform : ""} ${txn ? txn.order_id : ""}`,
        search
      );
    });
  }

  rows.sort((a, b) => new Date(a.due_date) - new Date(b.due_date));

  if (!rows.length) {
    emptyState.classList.remove("hidden");
  } else {
    emptyState.classList.add("hidden");
    rows.forEach((r) => list.appendChild(buildRefundRow(r)));
  }
}

/* ---------------- FAILED PAYMENTS ---------------- */

function renderFailedPayments() {
  const search = document.getElementById("failed-search").value.trim();
  const list = document.getElementById("failed-list");
  const emptyState = document.getElementById("failed-empty");
  list.innerHTML = "";

  let rows = appState.transactions.filter((t) => t.status === "failed");
  if (search) {
    rows = rows.filter((t) => matchesSearch(`${t.platform} ${t.order_id} ${t.transaction_id}`, search));
  }

  if (!rows.length) {
    emptyState.classList.remove("hidden");
  } else {
    emptyState.classList.add("hidden");
    rows.forEach((t) => list.appendChild(buildTransactionRow(t)));
  }
}

/* ---------------- CANCELLED ORDERS ---------------- */

function renderCancelledOrders() {
  const search = document.getElementById("cancelled-search").value.trim();
  const list = document.getElementById("cancelled-list");
  const emptyState = document.getElementById("cancelled-empty");
  list.innerHTML = "";

  let rows = appState.transactions.filter((t) => t.status === "cancelled");
  if (search) {
    rows = rows.filter((t) => matchesSearch(`${t.platform} ${t.order_id} ${t.transaction_id}`, search));
  }

  if (!rows.length) {
    emptyState.classList.remove("hidden");
  } else {
    emptyState.classList.add("hidden");
    rows.forEach((t) => list.appendChild(buildTransactionRow(t)));
  }
}

/* ---------------- EVIDENCE VAULT ---------------- */

const EVIDENCE_ICONS = {
  "image/jpeg": "🖼️",
  "image/png": "🖼️",
  "application/pdf": "📄",
};

function renderEvidenceGrid() {
  const search = document.getElementById("evidence-search").value.trim();
  const grid = document.getElementById("evidence-grid");
  const emptyState = document.getElementById("evidence-empty");
  grid.innerHTML = "";

  let rows = [...appState.evidence];
  if (search) {
    rows = rows.filter((e) => matchesSearch(`${e.transaction_id} ${e.file_name}`, search));
  }
  rows.sort((a, b) => new Date(b.uploaded_at || b.created_at) - new Date(a.uploaded_at || a.created_at));

  if (!rows.length) {
    emptyState.classList.remove("hidden");
  } else {
    emptyState.classList.add("hidden");
    rows.forEach((e) => {
      const card = el(
        "div",
        "evidence-card",
        `
        <div class="evidence-file-icon">${EVIDENCE_ICONS[e.file_type] || "📎"}</div>
        <div class="evidence-file-name">${escapeHtml(e.file_name)}</div>
        <div class="evidence-meta">
          Transaction: ${escapeHtml(e.transaction_id)}<br />
          ${e.refund_id ? `Refund #${escapeHtml(e.refund_id)}<br />` : ""}
          Uploaded ${formatDate(e.uploaded_at || e.created_at)}
        </div>
        <div class="evidence-actions">
          <button class="btn btn-ghost btn-sm" data-evidence-view="${e.id}">View</button>
          <button class="btn btn-ghost btn-sm" data-evidence-delete="${e.id}">Delete</button>
        </div>
      `
      );
      grid.appendChild(card);
    });

    grid.querySelectorAll("[data-evidence-view]").forEach((btn) => {
      btn.addEventListener("click", () => viewEvidenceFile(Number(btn.dataset.evidenceView)));
    });
    grid.querySelectorAll("[data-evidence-delete]").forEach((btn) => {
      btn.addEventListener("click", () => confirmDeleteEvidence(Number(btn.dataset.evidenceDelete)));
    });
  }
}

/* ---------------- ALERTS ---------------- */

function renderAlerts() {
  const list = document.getElementById("alerts-list");
  const emptyState = document.getElementById("alerts-empty");
  list.innerHTML = "";

  const alerts = [];

  appState.refunds.forEach((r) => {
    if (r.display_status === "overdue") {
      alerts.push({ ...r, _alertLabel: "Overdue refund", _priority: 3 });
    } else if (r.display_status === "due_soon") {
      alerts.push({ ...r, _alertLabel: "Refund due soon", _priority: 2 });
    } else if (r.risk_level === "HIGH") {
      alerts.push({ ...r, _alertLabel: "High-risk refund", _priority: 1 });
    }
  });

  alerts.sort((a, b) => b._priority - a._priority || new Date(a.due_date) - new Date(b.due_date));

  if (!alerts.length) {
    emptyState.classList.remove("hidden");
  } else {
    emptyState.classList.add("hidden");
    alerts.forEach((refund) => {
      const txn = getTransactionById(refund.transaction_id);
      const row = el(
        "div",
        "row-item",
        `
        <div class="row-logo">${platformLogo(txn ? txn.platform : "")}</div>
        <div class="row-main">
          <div class="row-title">${escapeHtml(refund._alertLabel)} · ${escapeHtml(txn ? txn.platform : refund.transaction_id)}</div>
          <div class="row-subtitle">${escapeHtml(refund.reason || "")} · Due ${formatDate(refund.due_date)}</div>
        </div>
        <div class="row-meta">
          <div class="row-amount">${formatCurrency(refund.refund_amount)}</div>
        </div>
        ${riskPillHtml(refund.risk_level)}
        <span class="row-chevron">›</span>
      `
      );
      row.addEventListener("click", () => openRefundDetail(refund.id));
      list.appendChild(row);
    });
  }
}

/* ---------------- RENDER EVERYTHING ---------------- */

function renderEverything() {
  renderDashboard();
  renderTransactionsList();
  renderRefundsList();
  renderFailedPayments();
  renderCancelledOrders();
  renderEvidenceGrid();
  renderAlerts();
}
