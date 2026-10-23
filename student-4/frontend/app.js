const apiBase = "/budget-api";
const state = {
  journeys: [], budgets: [], expenses: [], dashboard: null, currencies: [], rate: null, selectedJourney: "",
  capabilities: null, budgetCheckVersion: 0, budgetCheckController: null,
  guidanceVersion: 0, guidanceController: null,
  journeyVersion: 0, journeyController: null,
};

const elements = {
  journey: document.querySelector("#journey-select"), status: document.querySelector("#status"), notices: document.querySelector("#notices"),
  budgetRows: document.querySelector("#budget-rows"), budgetEmpty: document.querySelector("#budget-empty"),
  expenseRows: document.querySelector("#expense-rows"), expenseEmpty: document.querySelector("#expense-empty"),
  adviceOutput: document.querySelector("#advice-output"), adviceEmpty: document.querySelector("#advice-empty"),
  budgetCheckButton: document.querySelector("#run-budget-check"), budgetCheckStatus: document.querySelector("#budget-check-status"),
  budgetCheckResult: document.querySelector("#budget-check-result"), budgetCheckCategories: document.querySelector("#budget-check-categories"),
  guidanceForm: document.querySelector("#guidance-form"), guidanceQuestion: document.querySelector("#guidance-question"),
  guidanceButton: document.querySelector("#submit-guidance"), guidanceCancel: document.querySelector("#cancel-guidance"),
  guidanceStatus: document.querySelector("#guidance-status"), guidanceResult: document.querySelector("#guidance-result"),
  guidanceAnswer: document.querySelector("#guidance-answer"), guidanceCitations: document.querySelector("#guidance-citations"),
  budgetDialog: document.querySelector("#budget-dialog"), budgetForm: document.querySelector("#budget-form"),
  expenseDialog: document.querySelector("#expense-dialog"), expenseForm: document.querySelector("#expense-form"),
  confirmDialog: document.querySelector("#confirm-dialog"), conversionPreview: document.querySelector("#conversion-preview"),
};

let confirmResolve = null;
let restoreFocus = null;

const planner = {
  form: document.querySelector("#what-if-form"), limits: document.querySelector("#what-if-limits"),
  inputs: document.querySelector("#what-if-inputs"), status: document.querySelector("#what-if-status"),
  preview: document.querySelector("#what-if-preview"), previewButton: document.querySelector("#preview-what-if"),
  start: document.querySelector("#start-what-if"), workflow: document.querySelector("#what-if-workflow"),
  record: document.querySelector("#what-if-record"), stop: document.querySelector("#stop-what-if"),
  retry: document.querySelector("#retry-what-if"), decisionForm: document.querySelector("#what-if-decision-form"),
  decisionFields: document.querySelector("#what-if-decision-fields"), decision: document.querySelector("#what-if-decision"),
  name: document.querySelector("#what-if-name"), notes: document.querySelector("#what-if-notes"),
  partial: document.querySelector("#what-if-partial"), corrections: document.querySelector("#what-if-corrections"),
  submit: document.querySelector("#submit-what-if-decision"),
};
const whatIf = { version: 0, controller: null, timer: null, preview: null, proposal: null, handle: null, record: null, startedAt: 0, paused: false, uncertain: false, startUncertain: false };

async function api(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, { ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) } });
  if (response.status === 204) return null;
  let body;
  try { body = await response.json(); } catch { throw new Error("The service returned an unreadable response."); }
  if (!response.ok) {
    const firstField = Object.values(body?.error?.fields || {}).find(Array.isArray)?.[0];
    const error = new Error(firstField || body?.error?.message || "The request could not be completed.");
    error.code = body?.error?.code;
    error.fields = body?.error?.fields;
    error.status = response.status;
    throw error;
  }
  return body;
}

function setStatus(message, kind = "info") {
  elements.status.textContent = message;
  elements.status.dataset.kind = kind;
}

function setToolStatus(node, message, kind, busy = false, focus = false) {
  node.textContent = message;
  node.dataset.state = kind;
  node.setAttribute("aria-busy", String(busy));
  if (focus) node.focus();
}

function renderToolAvailability() {
  const capabilities = state.capabilities;
  const budgetAvailable = capabilities?.mcpEnabled === true && Boolean(state.selectedJourney) && Boolean(state.dashboard);
  const guidanceAvailable = capabilities?.ragEnabled === true;
  elements.budgetCheckButton.disabled = !budgetAvailable;
  elements.guidanceButton.disabled = !guidanceAvailable;

  if (!capabilities) {
    setToolStatus(elements.budgetCheckStatus, "Budget check is unavailable because capabilities could not be confirmed.", "disabled");
    setToolStatus(elements.guidanceStatus, "Guidance is unavailable because capabilities could not be confirmed.", "disabled");
  } else {
    const checkMessage = !capabilities.mcpEnabled ? "Budget check is disabled by the current runtime mode."
      : !state.selectedJourney ? "Select a journey to enable the budget check."
        : state.dashboard ? "Ready for the selected journey." : "Loading selected journey totals...";
    const checkState = !capabilities.mcpEnabled ? "disabled" : capabilities.mcpEnabled && state.selectedJourney && !state.dashboard ? "loading" : "empty";
    setToolStatus(elements.budgetCheckStatus, checkMessage, checkState, checkState === "loading");
    setToolStatus(elements.guidanceStatus, capabilities.ragEnabled ? "Ready for a general budgeting question." : "Budgeting guidance is disabled by the current runtime mode.", capabilities.ragEnabled ? "empty" : "disabled");
  }
}

function make(tag, text, className = "") {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = String(text);
  if (className) node.className = className;
  return node;
}

function money(minor, currency) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(minor / 100);
}

function formatExactMoney(minor, currency) {
  if (!Number.isSafeInteger(minor)) throw new TypeError("Money must be a safe integer number of minor units.");

  const amount = BigInt(minor);
  const negative = amount < 0n;
  const absolute = negative ? -amount : amount;
  const fractionDigits = 2;
  const scale = 100n;
  const whole = absolute / scale;
  const fraction = absolute % scale;
  const currencyFormat = new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: 0 });
  const integerFormat = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0, useGrouping: true });
  const pattern = currencyFormat.formatToParts(negative ? (whole === 0n ? -1n : -whole) : whole);
  const integerParts = integerFormat.formatToParts(whole).filter((part) => part.type === "integer" || part.type === "group");
  let integerIndex = 0;
  const parts = pattern.map((part) => part.type === "integer" || part.type === "group" ? integerParts[integerIndex++] : part);

  if (fractionDigits > 0) {
    const decimal = new Intl.NumberFormat(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }).formatToParts(1.1).find((part) => part.type === "decimal").value;
    const digitFormat = new Intl.NumberFormat(undefined, { useGrouping: false, maximumFractionDigits: 0 });
    const fractionText = fraction.toString().padStart(fractionDigits, "0").replace(/\d/g, (digit) => digitFormat.format(Number(digit)));
    const lastNumberIndex = parts.reduce((last, part, index) => part.type === "integer" || part.type === "group" ? index : last, -1);
    parts.splice(lastNumberIndex + 1, 0, { type: "decimal", value: decimal }, { type: "fraction", value: fractionText });
  }

  return parts.map((part) => part.value).join("");
}

function majorToMinor(value) {
  const match = String(value).trim().match(/^(\d{1,10})(?:\.(\d{1,2}))?$/);
  if (!match) throw new Error("Amount must be a positive value with at most two decimal places.");
  const minor = Number(match[1]) * 100 + Number((match[2] || "").padEnd(2, "0"));
  if (!Number.isSafeInteger(minor) || minor <= 0) throw new Error("Amount must be greater than zero.");
  return minor;
}

function minorToMajor(value) { return (value / 100).toFixed(2); }

async function loadApplication(preferredJourney = state.selectedJourney) {
  const version = ++state.journeyVersion;
  state.journeyController?.abort();
  const controller = new AbortController();
  state.journeyController = controller;
  invalidateBudgetCheck("Budget check cleared while budget data refreshes.");
  elements.budgetCheckButton.disabled = true;
  setStatus("Loading budget data...");
  clearWorkspace();
  state.journeys = [];
  state.currencies = [];
  state.rate = null;
  elements.journey.replaceChildren();
  elements.journey.disabled = true;
  document.querySelector("#add-budget").disabled = true;
  try {
    const [journeys, currencyData, capabilities] = await Promise.all([
      api("/journeys", { signal: controller.signal }), api("/currencies", { signal: controller.signal }), api("/capabilities", { signal: controller.signal }).catch(() => null),
    ]);
    if (version !== state.journeyVersion) return;
    state.capabilities = capabilities && typeof capabilities.mcpEnabled === "boolean" && typeof capabilities.ragEnabled === "boolean"
      ? capabilities : null;
    state.journeys = journeys;
    state.currencies = currencyData.currencies.map((value) => value.code);
    state.rate = currencyData;
    populateCurrencies();
    renderJourneyOptions(preferredJourney);
    renderToolAvailability();
    elements.journey.disabled = state.journeys.length === 0;
    document.querySelector("#add-budget").disabled = false;
    if (!state.selectedJourney) {
      clearWorkspace();
      setStatus("No journeys are available. Add a budget to begin.");
      return;
    }
    return loadJourney();
  } catch (error) {
    if (controller.signal.aborted || version !== state.journeyVersion) return;
    setStatus(error.message, "error");
    throw error;
  }
}

async function loadJourney() {
  const version = ++state.journeyVersion;
  state.journeyController?.abort();
  const controller = new AbortController();
  state.journeyController = controller;
  const journeyLabel = state.selectedJourney;
  invalidateBudgetCheck("Budget check cleared while the selected journey loads.");
  setStatus("Loading selected journey...");
  elements.budgetCheckButton.disabled = true;
  setToolStatus(elements.budgetCheckStatus, "Loading selected journey totals...", "loading", true);
  clearWorkspace();
  const label = encodeURIComponent(state.selectedJourney);
  try {
    const [dashboard, budgets, expenses] = await Promise.all([
      api(`/dashboard?journeyLabel=${label}`, { signal: controller.signal }), api(`/budgets?journeyLabel=${label}`, { signal: controller.signal }), api(`/expenses?journeyLabel=${label}`, { signal: controller.signal }),
    ]);
    if (version !== state.journeyVersion || journeyLabel !== state.selectedJourney) return;
    state.dashboard = dashboard;
    state.budgets = budgets;
    state.expenses = expenses;
    renderDashboard();
    renderBudgets();
    renderExpenses();
    renderWhatIfInputs();
    resetAdvice();
    elements.budgetCheckButton.disabled = state.capabilities?.mcpEnabled !== true;
    setToolStatus(elements.budgetCheckStatus, state.capabilities?.mcpEnabled === true ? "Ready for the selected journey." : "Budget check is disabled by the current runtime mode.", state.capabilities?.mcpEnabled === true ? "empty" : "disabled");
    setWorkspaceActionsDisabled(false);
    elements.budgetCheckButton.disabled = state.capabilities?.mcpEnabled !== true;
    const checkMessage = !state.capabilities ? "Budget check is unavailable because capabilities could not be confirmed."
      : state.capabilities.mcpEnabled ? "Ready for the selected journey." : "Budget check is disabled by the current runtime mode.";
    setToolStatus(elements.budgetCheckStatus, checkMessage, state.capabilities?.mcpEnabled === true ? "empty" : "disabled");
    setStatus(`${state.selectedJourney} is up to date.`);
  } catch (error) {
    if (controller.signal.aborted || version !== state.journeyVersion) return;
    setToolStatus(elements.budgetCheckStatus, error.message, "error", false, true);
    elements.budgetCheckButton.disabled = true;
    setStatus(error.message, "error");
    throw error;
  }
}

function renderJourneyOptions(preferred) {
  elements.journey.replaceChildren();
  for (const journey of state.journeys) {
    const option = make("option", journey.journeyLabel);
    option.value = journey.journeyLabel;
    elements.journey.append(option);
  }
  const labels = state.journeys.map((value) => value.journeyLabel);
  state.selectedJourney = labels.includes(preferred) ? preferred : labels[0] || "";
  elements.journey.value = state.selectedJourney;
}

function populateCurrencies() {
  for (const selector of [document.querySelector("#budget-currency"), document.querySelector("#expense-currency")]) {
    selector.replaceChildren(...state.currencies.map((currency) => { const option = make("option", currency); option.value = currency; return option; }));
  }
  document.querySelector("#rate-date").textContent = `Rates as of ${state.rate.rateAsOf} · ${state.rate.rateVersion}`;
  document.querySelector("#rate-disclaimer").textContent = state.rate.disclaimer;
}

function clearWorkspace() {
  state.dashboard = null; state.budgets = []; state.expenses = [];
  renderWhatIfInputs();
  for (const id of ["total-planned", "total-actual", "total-remaining", "total-percentage"]) document.querySelector(`#${id}`).textContent = "—";
  elements.budgetRows.replaceChildren(); elements.expenseRows.replaceChildren(); elements.notices.replaceChildren();
  elements.budgetEmpty.hidden = false; elements.expenseEmpty.hidden = false;
  resetAdvice();
  setWorkspaceActionsDisabled(true);
}

function invalidateBudgetCheck(message = "Run a new check to see current totals.") {
  invalidateWhatIf("Journey data changed; request a fresh preview.");
  state.budgetCheckVersion++;
  state.budgetCheckController?.abort();
  state.budgetCheckController = null;
  const available = state.capabilities?.mcpEnabled === true && Boolean(state.selectedJourney) && Boolean(state.dashboard);
  elements.budgetCheckButton.disabled = true;
  elements.budgetCheckResult.hidden = true;
  setToolStatus(elements.budgetCheckStatus, !state.capabilities || state.capabilities.mcpEnabled !== true ? "Budget check is disabled or capabilities are unavailable." : available ? message : "Select a loaded journey to enable the budget check.", !state.capabilities || state.capabilities.mcpEnabled !== true ? "disabled" : "empty");
}

function validateBudgetCheck(payload, requestedJourney) {
  const summary = payload?.result?.summary;
  if (payload?.tool !== "budget.get_summary" || payload.result?.ok !== true
    || !summary || summary.journeyLabel !== requestedJourney || !state.currencies.includes(summary.baseCurrency)
    || !Number.isFinite(summary.percentageUsed) || !Array.isArray(summary.categories)
    || summary.categories.length < 1 || summary.categories.length > 6) {
    throw new Error("The budget check returned an invalid summary.");
  }

  for (const field of ["plannedAmountMinor", "actualAmountMinor", "remainingAmountMinor"]) {
    if (!Number.isSafeInteger(summary[field])) throw new Error("The budget check returned money outside the exact display range.");
  }
  if (summary.plannedAmountMinor <= 0 || summary.actualAmountMinor < 0
    || BigInt(summary.remainingAmountMinor) !== BigInt(summary.plannedAmountMinor) - BigInt(summary.actualAmountMinor)) {
    throw new Error("The budget check returned incoherent journey totals.");
  }
  const categoryNames = new Set();
  const totals = { planned: 0n, actual: 0n, remaining: 0n };
  for (const category of summary.categories) {
    if (typeof category.category !== "string" || !["accommodation", "food", "transport", "activities", "shopping", "other"].includes(category.category)
      || categoryNames.has(category.category.toLowerCase())
      || !["within_budget", "warning", "overspent"].includes(category.status)
      || !Number.isFinite(category.percentageUsed)) {
      throw new Error("The budget check returned an invalid category summary.");
    }
    categoryNames.add(category.category.toLowerCase());
    for (const field of ["plannedAmountMinor", "actualAmountMinor", "remainingAmountMinor"]) {
      if (!Number.isSafeInteger(category[field])) throw new Error("The budget check returned money outside the exact display range.");
    }
    if (category.plannedAmountMinor <= 0 || category.actualAmountMinor < 0
      || BigInt(category.remainingAmountMinor) !== BigInt(category.plannedAmountMinor) - BigInt(category.actualAmountMinor)) {
      throw new Error("The budget check returned incoherent category totals.");
    }
    const actualHundredths = BigInt(category.actualAmountMinor) * 100n;
    const plannedHundredths = BigInt(category.plannedAmountMinor) * 100n;
    const expectedStatus = actualHundredths > plannedHundredths ? "overspent"
      : actualHundredths >= BigInt(category.plannedAmountMinor) * 80n ? "warning" : "within_budget";
    if (category.status !== expectedStatus) throw new Error("The budget check returned an invalid category status.");
    totals.planned += BigInt(category.plannedAmountMinor);
    totals.actual += BigInt(category.actualAmountMinor);
    totals.remaining += BigInt(category.remainingAmountMinor);
  }
  if (totals.planned !== BigInt(summary.plannedAmountMinor) || totals.actual !== BigInt(summary.actualAmountMinor)
    || totals.remaining !== BigInt(summary.remainingAmountMinor)) {
    throw new Error("The budget check returned category totals that do not match the journey.");
  }
  return summary;
}

function whatIfAmount(value) {
  const match = String(value).trim().match(/^(\d{1,16})(?:\.(\d{1,2}))?$/);
  if (!match) throw new Error("Enter a positive amount with at most two decimal places.");
  const minor = BigInt(match[1]) * 100n + BigInt((match[2] || "").padEnd(2, "0"));
  if (minor <= 0n || minor > BigInt(Number.MAX_SAFE_INTEGER)) throw new Error("Amount must be between 0.01 and 90071992547409.91.");
  return Number(minor);
}

function exactMajor(minor) {
  const amount = BigInt(minor);
  return `${amount / 100n}.${(amount % 100n).toString().padStart(2, "0")}`;
}

function validateWhatIfSummary(summary, journey) {
  return validateBudgetCheck({ tool: "budget.get_summary", result: { ok: true, summary } }, journey);
}

function updateWhatIfControls() {
  planner.previewButton.disabled = planner.limits.disabled || Boolean(whatIf.controller) || Boolean(whatIf.handle) || whatIf.startUncertain;
  planner.start.disabled = state.capabilities?.multiAgentEnabled !== true || !whatIf.preview || Boolean(whatIf.controller) || Boolean(whatIf.handle) || whatIf.startUncertain;
  planner.decisionFields.disabled = Boolean(whatIf.controller) || whatIf.uncertain;
  planner.submit.disabled = planner.decisionFields.disabled || whatIf.record?.status !== "awaiting_human_review";
  planner.retry.disabled = Boolean(whatIf.controller) || state.capabilities?.multiAgentEnabled !== true;
}

function invalidateWhatIf(message = "Limits changed; request a fresh preview.") {
  whatIf.version++;
  whatIf.controller?.abort();
  clearTimeout(whatIf.timer);
  Object.assign(whatIf, { controller: null, timer: null, preview: null, proposal: null, handle: null, record: null, startedAt: 0, paused: false, uncertain: false, startUncertain: false });
  planner.preview.hidden = true;
  planner.preview.replaceChildren();
  planner.workflow.hidden = true;
  planner.record.replaceChildren();
  planner.stop.hidden = true;
  planner.retry.hidden = true;
  planner.decisionForm.hidden = true;
  planner.decisionForm.reset();
  planner.partial.replaceChildren();
  planner.corrections.replaceChildren();
  setToolStatus(planner.status, message, "stale");
  updateWhatIfControls();
}

function renderWhatIfInputs() {
  planner.inputs.replaceChildren();
  planner.limits.disabled = true;
  document.querySelector("#what-if-currency").textContent = "";
  if (!state.dashboard || !state.selectedJourney) {
    setToolStatus(planner.status, "Select a loaded journey to preview limits.", "disabled");
  } else {
    try {
      const summary = validateWhatIfSummary(state.dashboard, state.selectedJourney);
      document.querySelector("#what-if-currency").textContent = `(${summary.baseCurrency})`;
      for (const category of summary.categories) {
        const label = make("label", title(category.category));
        const input = make("input");
        input.id = `what-if-limit-${category.category}`;
        input.dataset.category = category.category;
        input.inputMode = "decimal";
        input.required = true;
        input.value = exactMajor(category.plannedAmountMinor);
        label.append(input);
        planner.inputs.append(label);
      }
      planner.limits.disabled = false;
      setToolStatus(planner.status, state.capabilities?.multiAgentEnabled === true ? "Ready for a preview." : "Ready for a preview. Agent review is disabled.", "empty");
    } catch (error) {
      setToolStatus(planner.status, `Preview unavailable: ${error.message}`, "error");
    }
  }
  updateWhatIfControls();
}

function readWhatIfProposal() {
  const limits = [...planner.inputs.querySelectorAll("input")].map((input) => {
    try { return { category: input.dataset.category, limitAmountMinor: whatIfAmount(input.value) }; }
    catch (error) { input.focus(); throw error; }
  });
  if (limits.reduce((sum, limit) => sum + BigInt(limit.limitAmountMinor), 0n) > BigInt(Number.MAX_SAFE_INTEGER)) {
    throw new Error("The total proposed limit exceeds 90071992547409.91.");
  }
  return { journeyLabel: state.selectedJourney, limits };
}

function validateWhatIfPreview(payload, proposal) {
  const original = validateWhatIfSummary(payload?.original, proposal.journeyLabel);
  const proposed = validateWhatIfSummary(payload?.proposed, proposal.journeyLabel);
  if (typeof payload.snapshotHash !== "string" || !/^[a-f0-9]{64}$/.test(payload.snapshotHash)
    || original.baseCurrency !== proposed.baseCurrency || original.baseCurrency !== state.dashboard?.baseCurrency
    || original.actualAmountMinor !== proposed.actualAmountMinor
    || original.categories.length !== proposal.limits.length || proposed.categories.length !== proposal.limits.length
    || state.dashboard.categories.length !== proposal.limits.length) throw new Error("The preview does not match this proposal.");
  for (const limit of proposal.limits) {
    const before = original.categories.find((category) => category.category === limit.category);
    const after = proposed.categories.find((category) => category.category === limit.category);
    if (!before || !after || !state.dashboard.categories.some((category) => category.category === limit.category)
      || after.plannedAmountMinor !== limit.limitAmountMinor || before.actualAmountMinor !== after.actualAmountMinor) {
      throw new Error("The preview changed category identity, limits or actual spending.");
    }
  }
  return payload;
}

function renderWhatIfPreview(preview) {
  const { original, proposed } = preview;
  const delta = Number(BigInt(proposed.plannedAmountMinor) - BigInt(original.plannedAmountMinor));
  const deltaText = make("p", `Total limit change: ${delta > 0 ? "+" : ""}${formatExactMoney(delta, original.baseCurrency)}`, "what-if-delta");
  const wrap = make("div", null, "table-wrap what-if-comparison");
  wrap.tabIndex = 0;
  wrap.setAttribute("role", "region");
  wrap.setAttribute("aria-label", "Original and proposed category comparison");
  const table = make("table");
  table.append(make("caption", `${original.journeyLabel} / ${original.baseCurrency}`));
  const head = make("thead");
  const groups = make("tr");
  const categoryHeading = make("th", "Category");
  categoryHeading.rowSpan = 2;
  categoryHeading.scope = "col";
  groups.append(categoryHeading);
  for (const label of ["Original", "Proposed"]) {
    const group = make("th", label);
    group.colSpan = 4;
    group.scope = "colgroup";
    groups.append(group);
  }
  const columns = make("tr");
  for (const label of ["Planned", "Actual", "Remaining", "Status", "Planned", "Actual", "Remaining", "Status"]) {
    const heading = make("th", label); heading.scope = "col"; columns.append(heading);
  }
  head.append(groups, columns);
  const rows = make("tbody");
  function comparisonRow(label, before, after) {
    const row = make("tr");
    const heading = make("th", label); heading.scope = "row"; row.append(heading);
    for (const value of [before, after]) {
      for (const field of ["plannedAmountMinor", "actualAmountMinor", "remainingAmountMinor"]) row.append(cell(field, formatExactMoney(value[field], original.baseCurrency), "numeric"));
      const status = make("td");
      status.append(make("span", value.status ? value.status.replaceAll("_", " ") : "Total", value.status ? `status-label ${value.status}` : ""));
      row.append(status);
    }
    return row;
  }
  for (const before of original.categories) rows.append(comparisonRow(title(before.category), before, proposed.categories.find((category) => category.category === before.category)));
  const foot = make("tfoot"); foot.append(comparisonRow("Total", original, proposed));
  table.append(head, rows, foot); wrap.append(table);
  planner.preview.replaceChildren(deltaText, wrap);
  planner.preview.hidden = false;
}

async function previewWhatIf(event) {
  event.preventDefault();
  if (planner.previewButton.disabled || whatIf.controller) return;
  let proposal;
  try { proposal = readWhatIfProposal(); }
  catch (error) { setToolStatus(planner.status, error.message, "error"); return; }
  invalidateWhatIf();
  const version = whatIf.version;
  const controller = new AbortController(); whatIf.controller = controller;
  updateWhatIfControls();
  setToolStatus(planner.status, "Calculating preview...", "loading", true);
  try {
    const payload = await api("/what-if/preview", { method: "POST", body: JSON.stringify(proposal), signal: controller.signal });
    if (version !== whatIf.version || controller.signal.aborted) return;
    whatIf.preview = validateWhatIfPreview(payload, proposal);
    whatIf.proposal = proposal;
    renderWhatIfPreview(whatIf.preview);
    setToolStatus(planner.status, state.capabilities?.multiAgentEnabled === true ? "Preview ready. No saved budgets changed." : "Preview ready. Agent review is disabled. No saved budgets changed.", "success");
  } catch (error) {
    if (version !== whatIf.version || controller.signal.aborted) return;
    setToolStatus(planner.status, error.message, "error", false, true);
  } finally {
    if (version === whatIf.version) { whatIf.controller = null; updateWhatIfControls(); }
  }
}

planner.form.addEventListener("submit", previewWhatIf);
planner.inputs.addEventListener("input", () => invalidateWhatIf());

const workflowStatuses = ["queued", "planning", "working", "reviewing", "awaiting_human_review", "approved", "corrected", "partially_accepted", "rejected", "failed"];
const activeWorkflowStatuses = workflowStatuses.slice(0, 4);
const pollingWindow = 20 * 60 * 1000;

function validWhatIfHandle(id, token) {
  return typeof id === "string" && /^wf-\d{8}T\d{6}Z-[a-f0-9]{8}$/.test(id)
    && typeof token === "string" && token.length > 0 && token.length <= 4096;
}

function requireWhatIf(condition) {
  if (!condition) throw new Error("The agent service returned an invalid workflow. Retry status.");
}

function workflowText(value, maximum) {
  return typeof value === "string" && value.trim().length > 0 && value.length <= maximum;
}

function validateWhatIfWork(work, evidenceIds) {
  requireWhatIf(workflowText(work?.summary, 400) && Array.isArray(work.items) && work.items.length >= 1 && work.items.length <= 8);
  const ids = new Set();
  for (const item of work.items) {
    requireWhatIf(typeof item?.id === "string" && /^i\d{1,2}$/.test(item.id) && !ids.has(item.id)
      && workflowText(item.subject, 120) && workflowText(item.detail, 400)
      && Array.isArray(item.evidence_ids) && item.evidence_ids.length >= 1 && item.evidence_ids.length <= 3
      && item.evidence_ids.every((id) => evidenceIds.includes(id)));
    ids.add(item.id);
  }
}

function validateWhatIfWorkflow(payload) {
  requireWhatIf(payload?.id === whatIf.handle?.id && workflowStatuses.includes(payload.status));
  validateWhatIfPreview(payload.preview, whatIf.proposal);
  requireWhatIf(payload.preview.snapshotHash === whatIf.preview.snapshotHash);
  const record = payload.workflow;
  requireWhatIf(record?.id === payload.id && record.feature === "student-4" && record.status === payload.status
    && Array.isArray(record.history) && record.history.length <= 20
    && Array.isArray(record.evidence) && record.evidence.length >= 2 && record.evidence.length <= 7);
  const evidenceIds = record.evidence.map((entry) => entry?.id);
  requireWhatIf(new Set(evidenceIds).size === evidenceIds.length);
  for (const entry of record.evidence) requireWhatIf(workflowText(entry.id, 60) && workflowText(entry.title, 120) && workflowText(entry.text, 800));
  if (record.plan != null) {
    requireWhatIf(workflowText(record.plan.objective, 300) && Array.isArray(record.plan.steps) && record.plan.steps.length >= 1 && record.plan.steps.length <= 6
      && record.plan.steps.every((step) => workflowText(step?.id, 3) && workflowText(step.description, 200))
      && Array.isArray(record.plan.required_evidence_ids) && record.plan.required_evidence_ids.every((id) => evidenceIds.includes(id))
      && Array.isArray(record.plan.success_criteria) && record.plan.success_criteria.every((value) => workflowText(value, 300)));
  }
  if (record.work != null) validateWhatIfWork(record.work, evidenceIds);
  if (record.review != null) {
    requireWhatIf(["pass", "concerns", "fail"].includes(record.review.verdict) && typeof record.review.degraded === "boolean"
      && Array.isArray(record.review.findings) && record.review.findings.length <= 32
      && Array.isArray(record.review.recommendations) && record.review.recommendations.length <= 5
      && record.review.recommendations.every((value) => workflowText(value, 300)));
    for (const finding of record.review.findings) requireWhatIf(["info", "warning", "blocking"].includes(finding?.severity)
      && workflowText(finding.message, 300) && (finding.item_id === null || record.work?.items.some((item) => item.id === finding.item_id)));
    requireWhatIf(!record.review.degraded || record.review.verdict !== "pass");
  }
  for (const entry of record.history) requireWhatIf(workflowText(entry?.stage, 40) && typeof entry.ok === "boolean");
  if (["working", "reviewing", "awaiting_human_review", "approved", "corrected", "partially_accepted", "rejected"].includes(record.status)) requireWhatIf(record.plan);
  if (["reviewing", "awaiting_human_review", "approved", "corrected", "partially_accepted", "rejected"].includes(record.status)) requireWhatIf(record.work);
  if (["awaiting_human_review", "approved", "corrected", "partially_accepted", "rejected"].includes(record.status)) requireWhatIf(record.review);
  if (["approved", "corrected", "partially_accepted", "rejected"].includes(record.status)) {
    requireWhatIf(workflowText(record.human_decision?.decided_by, 60) && typeof record.human_decision.notes === "string"
      && record.human_decision.notes.length <= 1000
      && ({ approve: "approved", correct: "corrected", partial: "partially_accepted", reject: "rejected" })[record.human_decision.decision] === record.status);
    if (record.status !== "rejected") validateWhatIfWork(record.final_output, evidenceIds);
  }
  if (record.status === "failed") requireWhatIf(workflowText(record.error?.message, 2000));
  return record;
}

function appendWhatIfList(container, heading, values, ordered = false) {
  container.append(make("h3", heading));
  const list = make(ordered ? "ol" : "ul");
  for (const value of values) list.append(make("li", value));
  container.append(list);
}

function appendWhatIfWork(container, work, heading) {
  container.append(make("h3", heading), make("p", work.summary));
  const list = make("ul");
  for (const item of work.items) {
    const node = make("li");
    node.append(make("strong", `${item.id}: ${item.subject}`), make("p", item.detail), make("code", item.evidence_ids.join(", ")));
    list.append(node);
  }
  container.append(list);
}

function renderWhatIfDecision() {
  planner.decisionForm.hidden = whatIf.record?.status !== "awaiting_human_review";
  if (!planner.decisionForm.hidden && !planner.corrections.children.length) {
    const summaryLabel = make("label", "Corrected summary", "full-field");
    const summary = make("textarea"); summary.id = "what-if-corrected-summary"; summary.maxLength = 400; summary.rows = 2; summary.value = whatIf.record.work.summary;
    summaryLabel.append(summary); planner.corrections.append(summaryLabel);
    planner.partial.append(make("h3", "Accept items"));
    for (const item of whatIf.record.work.items) {
      const label = make("label");
      const checkbox = make("input"); checkbox.type = "checkbox"; checkbox.value = item.id;
      label.append(checkbox, make("span", `${item.id}: ${item.subject}`)); planner.partial.append(label);
      const detailLabel = make("label", `${item.id}: ${item.subject}`, "full-field");
      const detail = make("textarea"); detail.maxLength = 400; detail.rows = 2; detail.dataset.itemId = item.id; detail.value = item.detail;
      detailLabel.append(detail); planner.corrections.append(detailLabel);
    }
  }
  planner.partial.hidden = planner.decision.value !== "partial";
  planner.corrections.hidden = planner.decision.value !== "correct";
  planner.notes.required = planner.decision.value === "reject";
  updateWhatIfControls();
}

function renderWhatIfWorkflow() {
  const record = whatIf.record;
  planner.workflow.hidden = false;
  planner.record.replaceChildren(make("p", `Workflow ${whatIf.handle.id} / ${record ? record.status.replaceAll("_", " ") : "Status unknown"}`, "tool-identity"));
  if (!record) return;
  if (record.history.length) appendWhatIfList(planner.record, "Stage history", record.history.map((entry) => {
    const timing = entry.finished_at || entry.at || "";
    return `${entry.stage}: ${entry.ok ? "complete" : "failed"}${timing ? ` / ${timing}` : ""}${entry.model ? ` / ${entry.model}` : ""}${entry.error?.message ? ` / ${entry.error.message}` : ""}`;
  }), true);
  if (record.plan) {
    planner.record.append(make("h3", "Plan"), make("p", record.plan.objective));
    appendWhatIfList(planner.record, "Steps", record.plan.steps.map((step) => `${step.id}: ${step.description}`), true);
    appendWhatIfList(planner.record, "Success criteria", record.plan.success_criteria);
    planner.record.append(make("p", `Required evidence: ${record.plan.required_evidence_ids.join(", ")}`));
  }
  if (record.work) appendWhatIfWork(planner.record, record.work, "Worker");
  if (record.review) {
    planner.record.append(make("h3", `Reviewer: ${record.review.verdict}${record.review.degraded ? " / degraded" : ""}`));
    appendWhatIfList(planner.record, "Findings", record.review.findings.length ? record.review.findings.map((finding) => `${finding.severity}${finding.item_id ? ` / ${finding.item_id}` : ""}: ${finding.message}`) : ["No findings."]);
    appendWhatIfList(planner.record, "Recommendations", record.review.recommendations.length ? record.review.recommendations : ["No recommendations."]);
  }
  const evidence = make("details", null, "raw-details");
  evidence.append(make("summary", "Supplied evidence"));
  for (const entry of record.evidence) evidence.append(make("h3", `${entry.id}: ${entry.title}`), make("p", entry.text));
  planner.record.append(evidence);
  if (record.error) planner.record.append(make("p", `${record.error.code || "failed"}: ${record.error.message}`));
  if (record.human_decision) {
    const human = record.human_decision;
    planner.record.append(make("h3", `Human decision: ${human.decision}`), make("p", `${human.decided_by} / ${human.decided_at || ""}`), make("p", human.notes));
    if (human.accepted_item_ids) planner.record.append(make("p", `Accepted: ${human.accepted_item_ids.join(", ")}`));
    if (record.final_output) appendWhatIfWork(planner.record, record.final_output, "Accepted commentary");
  }
  renderWhatIfDecision();
}

function showWhatIfWorkflowStatus() {
  const record = whatIf.record;
  if (record.status === "failed") setToolStatus(planner.status, `Workflow failed: ${record.error.message}`, "failed");
  else if (activeWorkflowStatuses.includes(record.status)) setToolStatus(planner.status, `Agent review: ${record.status}.`, "loading", true);
  else if (record.status === "awaiting_human_review") setToolStatus(planner.status, record.review.degraded ? "Reviewer degraded. Human review required." : "Awaiting your decision.", record.review.degraded ? "degraded" : "review");
  else setToolStatus(planner.status, `${title(record.status)}. Preview only; no saved budgets changed.`, record.review?.degraded ? "degraded" : "success");
}

function pauseWhatIf(message = "Polling stopped. Resume status checks when ready.", kind = "paused") {
  const restore = document.activeElement === planner.stop;
  whatIf.version++;
  whatIf.controller?.abort(); whatIf.controller = null;
  clearTimeout(whatIf.timer); whatIf.timer = null;
  whatIf.paused = true;
  planner.stop.hidden = true;
  planner.retry.hidden = !whatIf.handle;
  planner.retry.textContent = "Resume status";
  setToolStatus(planner.status, message, kind);
  updateWhatIfControls();
  if (restore) planner.retry.focus();
}

function scheduleWhatIfPoll() {
  clearTimeout(whatIf.timer);
  const active = activeWorkflowStatuses.includes(whatIf.record?.status);
  planner.stop.hidden = !active || whatIf.paused;
  planner.retry.hidden = !whatIf.paused || !whatIf.handle;
  if (!active || whatIf.paused) return;
  const remaining = pollingWindow - (Date.now() - whatIf.startedAt);
  if (remaining <= 0) { pauseWhatIf("Polling paused after 20 minutes. Resume to check this workflow."); return; }
  const version = whatIf.version;
  whatIf.timer = setTimeout(() => { if (version === whatIf.version) pollWhatIf(); }, Math.min(3000, remaining));
}

function handleWhatIfFailure(error, operation) {
  if (error.code === "snapshot_stale") { invalidateWhatIf(error.message); return; }
  if (error.code === "feature_disabled") {
    state.capabilities = { ...state.capabilities, multiAgentEnabled: false };
    pauseWhatIf(error.message, "disabled");
    return;
  }
  whatIf.paused = true;
  planner.stop.hidden = true;
  planner.retry.hidden = !whatIf.handle;
  planner.retry.textContent = "Retry status";
  setToolStatus(planner.status, `${error.message}${operation === "decision" && whatIf.uncertain ? " Decision outcome unknown; retry status before deciding again." : ""}${operation === "start" && whatIf.startUncertain && !whatIf.handle ? " Start outcome unknown. Check shared workflow history before requesting another review." : ""}`, "error", false, true);
}

async function startWhatIf() {
  if (planner.start.disabled || whatIf.controller || whatIf.handle || !whatIf.preview) return;
  const version = whatIf.version;
  const controller = new AbortController(); whatIf.controller = controller;
  whatIf.startUncertain = true;
  whatIf.startedAt = Date.now();
  setToolStatus(planner.status, "Starting agent review...", "loading", true);
  updateWhatIfControls();
  try {
    const payload = await api("/what-if/workflows", { method: "POST", body: JSON.stringify({ ...whatIf.proposal, snapshotHash: whatIf.preview.snapshotHash }), signal: controller.signal });
    if (version !== whatIf.version || controller.signal.aborted) return;
    requireWhatIf(validWhatIfHandle(payload?.id, payload?.token));
    whatIf.handle = { id: payload.id, token: payload.token };
    whatIf.record = validateWhatIfWorkflow(payload);
    whatIf.startUncertain = false;
    renderWhatIfWorkflow(); showWhatIfWorkflowStatus();
    document.querySelector("#what-if-workflow-heading").focus();
  } catch (error) {
    if (version !== whatIf.version || controller.signal.aborted) return;
    if (validWhatIfHandle(error.fields?.id, error.fields?.token)) whatIf.handle = { id: error.fields.id, token: error.fields.token };
    if (["validation_error", "multi_agent_busy", "feature_disabled", "journey_not_found"].includes(error.code)) whatIf.startUncertain = false;
    if (whatIf.handle) renderWhatIfWorkflow();
    handleWhatIfFailure(error, "start");
  } finally {
    if (version === whatIf.version) { whatIf.controller = null; updateWhatIfControls(); scheduleWhatIfPoll(); }
  }
}

async function pollWhatIf() {
  if (!whatIf.handle || whatIf.controller || state.capabilities?.multiAgentEnabled !== true) return;
  const remaining = pollingWindow - (Date.now() - whatIf.startedAt);
  if (remaining <= 0) { pauseWhatIf("Polling paused after 20 minutes. Resume to check this workflow."); return; }
  const version = whatIf.version;
  const controller = new AbortController(); whatIf.controller = controller;
  whatIf.paused = false;
  planner.stop.hidden = false;
  const restore = document.activeElement === planner.retry;
  updateWhatIfControls();
  setToolStatus(planner.status, "Checking workflow status...", "loading", true);
  whatIf.timer = setTimeout(() => pauseWhatIf("Polling paused after 20 minutes. Resume to check this workflow."), remaining);
  try {
    const payload = await api(`/what-if/workflows/${encodeURIComponent(whatIf.handle.id)}`, { headers: { "X-WhatIf-Token": whatIf.handle.token }, signal: controller.signal });
    if (version !== whatIf.version || controller.signal.aborted) return;
    whatIf.record = validateWhatIfWorkflow(payload);
    whatIf.uncertain = false; whatIf.startUncertain = false;
    renderWhatIfWorkflow(); showWhatIfWorkflowStatus();
    if (restore) document.querySelector("#what-if-workflow-heading").focus();
  } catch (error) {
    if (version !== whatIf.version || controller.signal.aborted) return;
    whatIf.uncertain = true;
    handleWhatIfFailure(error, "poll");
  } finally {
    if (version === whatIf.version) { clearTimeout(whatIf.timer); whatIf.controller = null; updateWhatIfControls(); scheduleWhatIfPoll(); }
  }
}

function readWhatIfDecision() {
  const decision = planner.decision.value;
  const decidedBy = planner.name.value.trim();
  const notes = planner.notes.value.trim();
  if (!["approve", "correct", "partial", "reject"].includes(decision)) { planner.decision.focus(); throw new Error("Choose a human decision."); }
  if (!decidedBy || decidedBy.length > 60 || !/\p{L}/u.test(decidedBy) || /[\u0000-\u001f\u007f]/.test(decidedBy)
    || ["human", "frontend", "system", "ai", "assistant", "unknown", "student-4-backend"].includes(decidedBy.toLowerCase())) {
    planner.name.focus(); throw new Error("Enter your actual name (1 to 60 characters).");
  }
  if (planner.notes.value.length > 1000 || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(notes) || (decision === "reject" && !notes)) {
    planner.notes.focus(); throw new Error("Notes must be at most 1000 characters; rejection requires notes.");
  }
  const payload = { decision, notes, decidedBy };
  if (decision === "partial") {
    const ids = [...planner.partial.querySelectorAll("input:checked")].map((input) => input.value);
    if (!ids.length || new Set(ids).size !== ids.length || ids.some((id) => !whatIf.record.work.items.some((item) => item.id === id))) {
      planner.partial.querySelector("input")?.focus(); throw new Error("Select at least one known item to accept.");
    }
    payload.acceptedItemIds = ids;
  }
  if (decision === "correct") {
    const summary = document.querySelector("#what-if-corrected-summary").value.trim();
    const items = whatIf.record.work.items.map((item) => ({ id: item.id, subject: item.subject, detail: [...planner.corrections.querySelectorAll("textarea[data-item-id]")].find((input) => input.dataset.itemId === item.id).value.trim(), evidence_ids: [...item.evidence_ids] }));
    if (!workflowText(summary, 400) || items.some((item) => !workflowText(item.detail, 400))) {
      document.querySelector("#what-if-corrected-summary").focus(); throw new Error("Correction summary and each detail must contain 1 to 400 characters.");
    }
    payload.correctedOutput = { summary, items };
  }
  return payload;
}

async function submitWhatIfDecision(event) {
  event.preventDefault();
  if (planner.submit.disabled || whatIf.controller || whatIf.uncertain || whatIf.record?.status !== "awaiting_human_review") return;
  let payload;
  try { payload = readWhatIfDecision(); }
  catch (error) { setToolStatus(planner.status, error.message, "error"); return; }
  const version = whatIf.version;
  const controller = new AbortController(); whatIf.controller = controller;
  whatIf.uncertain = true;
  planner.stop.hidden = true;
  updateWhatIfControls();
  setToolStatus(planner.status, "Recording your decision...", "loading", true);
  try {
    const result = await api(`/what-if/workflows/${encodeURIComponent(whatIf.handle.id)}/decision`, { method: "POST", body: JSON.stringify(payload), headers: { "X-WhatIf-Token": whatIf.handle.token }, signal: controller.signal });
    if (version !== whatIf.version || controller.signal.aborted) return;
    const record = validateWhatIfWorkflow(result);
    requireWhatIf(record.status === ({ approve: "approved", correct: "corrected", partial: "partially_accepted", reject: "rejected" })[payload.decision]);
    whatIf.record = record; whatIf.uncertain = false; whatIf.paused = false;
    renderWhatIfWorkflow(); showWhatIfWorkflowStatus();
    document.querySelector("#what-if-workflow-heading").focus();
  } catch (error) {
    if (version !== whatIf.version || controller.signal.aborted) return;
    if (error.status === 400) whatIf.uncertain = false;
    handleWhatIfFailure(error, "decision");
  } finally {
    if (version === whatIf.version) { whatIf.controller = null; updateWhatIfControls(); scheduleWhatIfPoll(); }
  }
}

planner.start.addEventListener("click", startWhatIf);
planner.stop.addEventListener("click", () => pauseWhatIf());
planner.retry.addEventListener("click", () => { whatIf.startedAt = Date.now(); pollWhatIf(); });
planner.decision.addEventListener("change", renderWhatIfDecision);
planner.decisionForm.addEventListener("submit", submitWhatIfDecision);
window.addEventListener("pagehide", () => { invalidateWhatIf("Planner closed."); state.journeyVersion++; state.journeyController?.abort(); });

function renderBudgetCheck(payload, summary) {
  document.querySelector("#budget-check-tool").textContent = payload.tool;
  document.querySelector("#budget-check-journey").textContent = `${summary.journeyLabel} · ${summary.baseCurrency}`;
  document.querySelector("#check-planned").textContent = formatExactMoney(summary.plannedAmountMinor, summary.baseCurrency);
  document.querySelector("#check-actual").textContent = formatExactMoney(summary.actualAmountMinor, summary.baseCurrency);
  document.querySelector("#check-remaining").textContent = formatExactMoney(summary.remainingAmountMinor, summary.baseCurrency);
  document.querySelector("#check-percentage").textContent = `${summary.percentageUsed}%`;
  elements.budgetCheckCategories.replaceChildren(...summary.categories.map((category) => {
    const item = make("li");
    item.append(make("strong", title(category.category)), make("span", `Planned ${formatExactMoney(category.plannedAmountMinor, summary.baseCurrency)}`));
    item.append(make("span", `Actual ${formatExactMoney(category.actualAmountMinor, summary.baseCurrency)}`));
    item.append(make("span", `Remaining ${formatExactMoney(category.remainingAmountMinor, summary.baseCurrency)}`));
    item.append(make("span", `${category.percentageUsed}% · ${category.status.replaceAll("_", " ")}`, `status-label ${category.status}`));
    return item;
  }));
  document.querySelector("#budget-check-raw").textContent = JSON.stringify(payload, null, 2);
  elements.budgetCheckResult.hidden = false;
}

async function runBudgetCheck() {
  if (elements.budgetCheckButton.disabled || state.budgetCheckController) return;
  const journeyLabel = state.selectedJourney;
  const version = ++state.budgetCheckVersion;
  const controller = new AbortController();
  state.budgetCheckController = controller;
  elements.budgetCheckButton.disabled = true;
  elements.budgetCheckResult.hidden = true;
  setToolStatus(elements.budgetCheckStatus, `Checking ${journeyLabel}...`, "loading", true);
  try {
    const payload = await api("/budget-check", { method: "POST", body: JSON.stringify({ journeyLabel }), signal: controller.signal });
    if (version !== state.budgetCheckVersion || journeyLabel !== state.selectedJourney) return;
    const summary = validateBudgetCheck(payload, journeyLabel);
    renderBudgetCheck(payload, summary);
    setToolStatus(elements.budgetCheckStatus, `Current totals verified for ${journeyLabel}.`, "success");
  } catch (error) {
    if (controller.signal.aborted || version !== state.budgetCheckVersion) return;
    elements.budgetCheckResult.hidden = true;
    setToolStatus(elements.budgetCheckStatus, error.message, "error", false, true);
  } finally {
    if (version === state.budgetCheckVersion) {
      state.budgetCheckController = null;
      elements.budgetCheckButton.disabled = !(state.capabilities?.mcpEnabled === true && state.selectedJourney && state.dashboard);
      elements.budgetCheckStatus.setAttribute("aria-busy", "false");
    }
  }
}

function invalidateGuidance(message = "Ask a question to request general budgeting guidance.") {
  state.guidanceVersion++;
  state.guidanceController?.abort();
  state.guidanceController = null;
  elements.guidanceResult.hidden = true;
  elements.guidanceCancel.hidden = true;
  elements.guidanceButton.disabled = state.capabilities?.ragEnabled !== true;
  setToolStatus(elements.guidanceStatus, message, "empty");
}

function renderGuidance(response) {
  const confidenceLabels = { high: "High retrieval confidence", medium: "Medium retrieval confidence", low: "Low retrieval confidence" };
  if (typeof response?.answer !== "string" || !Array.isArray(response.citations)
    || !["high", "medium", "low", "insufficient"].includes(response.confidence)
    || (response.confidence === "insufficient" && (response.answer !== "Not enough information in the knowledge base to answer this." || response.citations.length !== 0))) {
    throw new Error("The guidance service returned an invalid response.");
  }
  elements.guidanceAnswer.textContent = response.answer;
  document.querySelector("#guidance-confidence").textContent = response.confidence === "insufficient" ? "Insufficient information" : confidenceLabels[response.confidence];
  elements.guidanceCitations.replaceChildren(...response.citations.map((citation) => {
    if (typeof citation.source !== "string" || typeof citation.chunkId !== "string" || typeof citation.snippet !== "string") {
      throw new Error("The guidance service returned an invalid citation.");
    }
    const details = make("details", null, "citation-details");
    details.append(make("summary", citation.source));
    details.append(make("p", citation.snippet));
    details.append(make("code", citation.chunkId), make("span", ` Relevance ${Number(citation.score).toFixed(3)}`));
    return details;
  }));
  elements.guidanceResult.hidden = false;
  const insufficient = response.confidence === "insufficient";
  setToolStatus(elements.guidanceStatus, insufficient ? "The knowledge base cannot support an answer to this question." : "Grounded general guidance received.", insufficient ? "abstention" : "success");
}

async function submitGuidance(event) {
  event.preventDefault();
  if (elements.guidanceButton.disabled || state.guidanceController) return;
  const question = elements.guidanceQuestion.value.trim();
  if (!question || question.length > 1000) {
    setToolStatus(elements.guidanceStatus, "Enter a question of 1 to 1000 characters.", "error", false, true);
    return;
  }
  const version = ++state.guidanceVersion;
  const controller = new AbortController();
  state.guidanceController = controller;
  elements.guidanceButton.disabled = true;
  elements.guidanceCancel.hidden = false;
  elements.guidanceResult.hidden = true;
  setToolStatus(elements.guidanceStatus, "Retrieving general budgeting guidance...", "loading", true);
  try {
    const response = await api("/budget-guidance", { method: "POST", body: JSON.stringify({ question }), signal: controller.signal });
    if (version !== state.guidanceVersion || question !== elements.guidanceQuestion.value.trim()) return;
    renderGuidance(response);
  } catch (error) {
    if (controller.signal.aborted || version !== state.guidanceVersion) return;
    elements.guidanceResult.hidden = true;
    setToolStatus(elements.guidanceStatus, error.message, "error", false, true);
  } finally {
    if (version === state.guidanceVersion) {
      state.guidanceController = null;
      elements.guidanceCancel.hidden = true;
      elements.guidanceButton.disabled = state.capabilities?.ragEnabled !== true;
      elements.guidanceStatus.setAttribute("aria-busy", "false");
    }
  }
}

function setWorkspaceActionsDisabled(disabled) {
  document.querySelector("#add-expense").disabled = disabled;
  document.querySelector("#generate-advice").disabled = disabled;
}

function renderDashboard() {
  const value = state.dashboard;
  document.querySelector("#total-planned").textContent = money(value.plannedAmountMinor, value.baseCurrency);
  document.querySelector("#total-actual").textContent = money(value.actualAmountMinor, value.baseCurrency);
  document.querySelector("#total-remaining").textContent = money(value.remainingAmountMinor, value.baseCurrency);
  document.querySelector("#total-percentage").textContent = `${value.percentageUsed}%`;
  const journey = state.journeys.find((item) => item.journeyLabel === state.selectedJourney);
  document.querySelector("#summary-period").textContent = journey ? `${journey.startDate} to ${journey.endDate} · ${value.baseCurrency}` : value.baseCurrency;
  elements.notices.replaceChildren();
  for (const category of value.categories.filter((item) => item.status !== "within_budget")) {
    const notice = make("p", category.status === "overspent" ? `${title(category.category)} is over budget by ${money(-category.remainingAmountMinor, value.baseCurrency)}.` : `${title(category.category)} has reached ${category.percentageUsed}% of its limit.`, `notice ${category.status}`);
    elements.notices.append(notice);
  }
}

function renderBudgets() {
  elements.budgetRows.replaceChildren();
  for (const budget of state.budgets) {
    const actual = state.expenses.filter((value) => value.budgetId === budget.id).reduce((total, value) => total + value.convertedAmountMinor, 0);
    const percentage = Math.round(actual * 10000 / budget.limitAmountMinor) / 100;
    const status = percentage > 100 ? "overspent" : percentage >= 80 ? "warning" : "within_budget";
    const row = document.createElement("tr");
    row.append(cell("Category", `${title(budget.category)} · ${budget.startDate} to ${budget.endDate}`));
    row.append(cell("Planned", money(budget.limitAmountMinor, budget.baseCurrency), "numeric"));
    row.append(cell("Actual", money(actual, budget.baseCurrency), "numeric"));
    row.append(cell("Remaining", money(budget.limitAmountMinor - actual, budget.baseCurrency), "numeric"));
    const use = cell("Use");
    const track = make("div", null, "progress-track");
    const fill = make("div", null, `progress-fill ${status}`);
    fill.style.width = `${Math.min(percentage, 100)}%`;
    track.append(fill); use.append(track, make("span", `${percentage}% · ${status.replaceAll("_", " ")}`, `status-label ${status}`));
    row.append(use);
    row.append(actionCell([{ label: "Edit", action: "edit-budget", id: budget.id }, { label: "Delete", action: "delete-budget", id: budget.id, danger: true }]));
    elements.budgetRows.append(row);
  }
  elements.budgetEmpty.hidden = state.budgets.length > 0;
}

function renderExpenses() {
  elements.expenseRows.replaceChildren();
  for (const expense of state.expenses) {
    const row = document.createElement("tr");
    row.append(cell("Date", expense.spentOn), cell("Description", expense.description), cell("Category", title(expense.category)));
    row.append(cell("Original", money(expense.originalAmountMinor, expense.originalCurrency), "numeric"));
    const converted = cell("Converted", money(expense.convertedAmountMinor, expense.baseCurrency), "numeric");
    converted.title = `Rate snapshot ${expense.conversionRateScaled} · ${expense.rateAsOf}`;
    row.append(converted, actionCell([{ label: "Edit", action: "edit-expense", id: expense.id }, { label: "Delete", action: "delete-expense", id: expense.id, danger: true }]));
    elements.expenseRows.append(row);
  }
  elements.expenseEmpty.hidden = state.expenses.length > 0;
}

function cell(label, text, className = "") { const value = make("td", text, className); value.dataset.label = label; return value; }
function actionCell(actions) {
  const value = make("td", null, "actions");
  for (const action of actions) { const button = make("button", action.label, `row-button ${action.danger ? "danger" : ""}`); button.type = "button"; button.dataset.action = action.action; button.dataset.id = String(action.id); value.append(button); }
  return value;
}
function title(value) { return value ? value[0].toUpperCase() + value.slice(1).replaceAll("_", " ") : ""; }

function openBudget(budget = null, opener = null) {
  restoreFocus = opener;
  document.querySelector("#budget-dialog-title").textContent = budget ? "Edit budget" : "Add budget";
  document.querySelector("#budget-id").value = budget?.id || "";
  document.querySelector("#budget-journey").value = budget?.journeyLabel || state.selectedJourney;
  document.querySelector("#budget-category").value = budget?.category || "food";
  document.querySelector("#budget-amount").value = budget ? minorToMajor(budget.limitAmountMinor) : "";
  document.querySelector("#budget-currency").value = budget?.baseCurrency || state.dashboard?.baseCurrency || "AUD";
  document.querySelector("#budget-start").value = budget?.startDate || state.journeys.find((value) => value.journeyLabel === state.selectedJourney)?.startDate || "";
  document.querySelector("#budget-end").value = budget?.endDate || state.journeys.find((value) => value.journeyLabel === state.selectedJourney)?.endDate || "";
  elements.budgetDialog.showModal();
  document.querySelector("#budget-journey").focus();
}

function openExpense(expense = null, opener = null) {
  if (!state.budgets.length) { setStatus("Add a category budget before recording an expense.", "error"); return; }
  restoreFocus = opener;
  document.querySelector("#expense-dialog-title").textContent = expense ? "Edit expense" : "Add expense";
  document.querySelector("#expense-id").value = expense?.id || "";
  const selector = document.querySelector("#expense-budget");
  selector.replaceChildren(...state.budgets.map((budget) => { const option = make("option", `${title(budget.category)} · ${money(budget.limitAmountMinor, budget.baseCurrency)}`); option.value = String(budget.id); return option; }));
  selector.value = String(expense?.budgetId || state.budgets[0].id);
  document.querySelector("#expense-description").value = expense?.description || "";
  document.querySelector("#expense-amount").value = expense ? minorToMajor(expense.originalAmountMinor) : "";
  document.querySelector("#expense-currency").value = expense?.originalCurrency || state.dashboard.baseCurrency;
  document.querySelector("#expense-date").value = expense?.spentOn || state.budgets.find((value) => value.id === Number(selector.value)).startDate;
  document.querySelector("#expense-notes").value = expense?.notes || "";
  elements.conversionPreview.textContent = "";
  elements.expenseDialog.showModal();
  document.querySelector("#expense-description").focus();
  previewConversion();
}

function closeDialog(dialog) { dialog.close(); restoreFocus?.focus(); restoreFocus = null; }

async function previewConversion() {
  const budget = state.budgets.find((value) => value.id === Number(document.querySelector("#expense-budget").value));
  if (!budget) return;
  try {
    const amount = majorToMinor(document.querySelector("#expense-amount").value);
    const result = await api("/conversions/preview", { method: "POST", body: JSON.stringify({ originalAmountMinor: amount, fromCurrency: document.querySelector("#expense-currency").value, toCurrency: budget.baseCurrency }) });
    elements.conversionPreview.textContent = `Preview: ${money(result.convertedAmountMinor, result.toCurrency)} at ${result.rate.toFixed(6)} · ${result.rateAsOf}`;
  } catch { elements.conversionPreview.textContent = "Enter a valid amount to preview conversion."; }
}

function confirmDelete(titleText, message, opener) {
  restoreFocus = opener;
  document.querySelector("#confirm-title").textContent = titleText;
  document.querySelector("#confirm-message").textContent = message;
  elements.confirmDialog.showModal();
  document.querySelector("#confirm-cancel").focus();
  return new Promise((resolve) => { confirmResolve = resolve; });
}

function finishConfirm(value) { elements.confirmDialog.close(); const resolve = confirmResolve; confirmResolve = null; resolve?.(value); restoreFocus?.focus(); restoreFocus = null; }

elements.budgetForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!elements.budgetForm.reportValidity()) return;
  const id = document.querySelector("#budget-id").value;
  const button = elements.budgetForm.querySelector("button[type=submit]"); button.disabled = true;
  try {
    const payload = { journeyLabel: document.querySelector("#budget-journey").value, category: document.querySelector("#budget-category").value, limitAmountMinor: majorToMinor(document.querySelector("#budget-amount").value), baseCurrency: document.querySelector("#budget-currency").value, startDate: document.querySelector("#budget-start").value, endDate: document.querySelector("#budget-end").value };
    invalidateBudgetCheck("Budget check cleared because a budget is being changed.");
    await api(id ? `/budgets/${id}` : "/budgets", { method: id ? "PUT" : "POST", body: JSON.stringify(payload) });
    closeDialog(elements.budgetDialog);
    state.selectedJourney = payload.journeyLabel.trim();
    await loadApplication(state.selectedJourney);
    setStatus(id ? "Budget updated." : "Budget created.");
  } catch (error) { setStatus(error.message, "error"); } finally { button.disabled = false; }
});

elements.expenseForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!elements.expenseForm.reportValidity()) return;
  const id = document.querySelector("#expense-id").value;
  const button = elements.expenseForm.querySelector("button[type=submit]"); button.disabled = true;
  try {
    const payload = { budgetId: Number(document.querySelector("#expense-budget").value), description: document.querySelector("#expense-description").value, originalAmountMinor: majorToMinor(document.querySelector("#expense-amount").value), originalCurrency: document.querySelector("#expense-currency").value, spentOn: document.querySelector("#expense-date").value, notes: document.querySelector("#expense-notes").value };
    invalidateBudgetCheck("Budget check cleared because an expense is being changed.");
    await api(id ? `/expenses/${id}` : "/expenses", { method: id ? "PUT" : "POST", body: JSON.stringify(payload) });
    closeDialog(elements.expenseDialog);
    await loadJourney();
    setStatus(id ? "Expense updated." : "Expense created with an authoritative conversion snapshot.");
  } catch (error) { setStatus(error.message, "error"); } finally { button.disabled = false; }
});

document.addEventListener("click", async (event) => {
  const target = event.target.closest("[data-action]");
  if (!target) return;
  const id = Number(target.dataset.id);
  if (target.dataset.action === "edit-budget") openBudget(state.budgets.find((value) => value.id === id), target);
  if (target.dataset.action === "edit-expense") openExpense(state.expenses.find((value) => value.id === id), target);
  if (target.dataset.action === "delete-budget" && await confirmDelete("Delete budget?", "This permanently deletes the category budget and all of its expenses.", target)) {
    try { invalidateBudgetCheck("Budget check cleared because a budget is being deleted."); await api(`/budgets/${id}`, { method: "DELETE" }); await loadApplication(); setStatus("Budget and linked expenses deleted."); document.querySelector("#add-budget").focus(); } catch (error) { setStatus(error.message, "error"); }
  }
  if (target.dataset.action === "delete-expense" && await confirmDelete("Delete expense?", "This permanently removes the selected ledger entry.", target)) {
    try { invalidateBudgetCheck("Budget check cleared because an expense is being deleted."); await api(`/expenses/${id}`, { method: "DELETE" }); await loadJourney(); setStatus("Expense deleted."); document.querySelector("#add-expense").focus(); } catch (error) { setStatus(error.message, "error"); }
  }
});

elements.budgetCheckButton.addEventListener("click", runBudgetCheck);
elements.guidanceForm.addEventListener("submit", submitGuidance);
elements.guidanceCancel.addEventListener("click", () => {
  invalidateGuidance("Guidance request cancelled.");
  elements.guidanceQuestion.focus();
});
elements.guidanceQuestion.addEventListener("input", () => {
  document.querySelector("#guidance-count").textContent = `${elements.guidanceQuestion.value.length} / 1000`;
  if (state.guidanceController || !elements.guidanceResult.hidden) invalidateGuidance("Question changed; submit it again for a fresh answer.");
});

document.querySelector("#generate-advice").addEventListener("click", async (event) => {
  const button = event.currentTarget; button.disabled = true; button.textContent = "Generating..."; setStatus("Generating optional budget advice...");
  try {
    const result = await api("/insights", { method: "POST", body: JSON.stringify({ journeyLabel: state.selectedJourney }) });
    document.querySelector("#advice-summary").textContent = result.summary;
    document.querySelector("#advice-source").textContent = result.source === "fallback" ? "Reliable fallback" : result.source === "ai_retry" ? "AI after retry" : "AI";
    document.querySelector("#advice-suggestions").replaceChildren(...result.suggestions.map((value) => make("li", `${title(value.category)}: ${value.text}`)));
    elements.adviceOutput.hidden = false; elements.adviceEmpty.hidden = true;
    setStatus(result.source === "fallback" ? "The model was unavailable or invalid; deterministic advice is shown." : "Budget advice generated.");
  } catch (error) { setStatus(error.message, "error"); } finally { button.disabled = false; button.textContent = "Generate budget advice"; }
});

function resetAdvice() { elements.adviceOutput.hidden = true; elements.adviceEmpty.hidden = false; document.querySelector("#advice-suggestions").replaceChildren(); }
elements.journey.addEventListener("change", () => { state.selectedJourney = elements.journey.value; loadJourney().catch(() => {}); });
document.querySelector("#refresh").addEventListener("click", () => loadApplication().catch(() => {}));
document.querySelector("#add-budget").addEventListener("click", (event) => openBudget(null, event.currentTarget));
document.querySelector("#add-expense").addEventListener("click", (event) => openExpense(null, event.currentTarget));
document.querySelector("#cancel-budget").addEventListener("click", () => closeDialog(elements.budgetDialog));
document.querySelector("#cancel-expense").addEventListener("click", () => closeDialog(elements.expenseDialog));
document.querySelector("#confirm-cancel").addEventListener("click", () => finishConfirm(false));
document.querySelector("#confirm-accept").addEventListener("click", () => finishConfirm(true));
elements.confirmDialog.addEventListener("cancel", (event) => { event.preventDefault(); finishConfirm(false); });
for (const id of ["expense-amount", "expense-currency", "expense-budget"]) document.querySelector(`#${id}`).addEventListener("change", previewConversion);
window.addEventListener("load", () => loadApplication().catch(() => {}), { once: true });

export { api, formatExactMoney, loadApplication, majorToMinor, money };