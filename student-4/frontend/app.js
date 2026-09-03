const apiBase = "/budget-api";
const state = { journeys: [], budgets: [], expenses: [], dashboard: null, currencies: [], rate: null, selectedJourney: "" };

const elements = {
  journey: document.querySelector("#journey-select"), status: document.querySelector("#status"), notices: document.querySelector("#notices"),
  budgetRows: document.querySelector("#budget-rows"), budgetEmpty: document.querySelector("#budget-empty"),
  expenseRows: document.querySelector("#expense-rows"), expenseEmpty: document.querySelector("#expense-empty"),
  adviceOutput: document.querySelector("#advice-output"), adviceEmpty: document.querySelector("#advice-empty"),
  budgetDialog: document.querySelector("#budget-dialog"), budgetForm: document.querySelector("#budget-form"),
  expenseDialog: document.querySelector("#expense-dialog"), expenseForm: document.querySelector("#expense-form"),
  confirmDialog: document.querySelector("#confirm-dialog"), conversionPreview: document.querySelector("#conversion-preview"),
};

let confirmResolve = null;
let restoreFocus = null;

async function api(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, { ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) } });
  if (response.status === 204) return null;
  let body;
  try { body = await response.json(); } catch { throw new Error("The service returned an unreadable response."); }
  if (!response.ok) {
    const firstField = Object.values(body.error?.fields || {}).flat()[0];
    throw new Error(firstField || body.error?.message || "The request could not be completed.");
  }
  return body;
}

function setStatus(message, kind = "info") {
  elements.status.textContent = message;
  elements.status.dataset.kind = kind;
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

function majorToMinor(value) {
  const match = String(value).trim().match(/^(\d{1,10})(?:\.(\d{1,2}))?$/);
  if (!match) throw new Error("Amount must be a positive value with at most two decimal places.");
  const minor = Number(match[1]) * 100 + Number((match[2] || "").padEnd(2, "0"));
  if (!Number.isSafeInteger(minor) || minor <= 0) throw new Error("Amount must be greater than zero.");
  return minor;
}

function minorToMajor(value) { return (value / 100).toFixed(2); }

async function loadApplication(preferredJourney = state.selectedJourney) {
  setStatus("Loading budget data...");
  clearWorkspace();
  state.journeys = [];
  state.currencies = [];
  state.rate = null;
  elements.journey.replaceChildren();
  elements.journey.disabled = true;
  document.querySelector("#add-budget").disabled = true;
  try {
    const [journeys, currencyData] = await Promise.all([api("/journeys"), api("/currencies")]);
    state.journeys = journeys;
    state.currencies = currencyData.currencies.map((value) => value.code);
    state.rate = currencyData;
    populateCurrencies();
    renderJourneyOptions(preferredJourney);
    elements.journey.disabled = state.journeys.length === 0;
    document.querySelector("#add-budget").disabled = false;
    if (!state.selectedJourney) {
      clearWorkspace();
      setStatus("No journeys are available. Add a budget to begin.");
      return;
    }
    await loadJourney();
  } catch (error) {
    setStatus(error.message, "error");
    throw error;
  }
}

async function loadJourney() {
  setStatus("Loading selected journey...");
  clearWorkspace();
  const label = encodeURIComponent(state.selectedJourney);
  try {
    const [dashboard, budgets, expenses] = await Promise.all([
      api(`/dashboard?journeyLabel=${label}`), api(`/budgets?journeyLabel=${label}`), api(`/expenses?journeyLabel=${label}`),
    ]);
    state.dashboard = dashboard;
    state.budgets = budgets;
    state.expenses = expenses;
    renderDashboard();
    renderBudgets();
    renderExpenses();
    resetAdvice();
    setWorkspaceActionsDisabled(false);
    setStatus(`${state.selectedJourney} is up to date.`);
  } catch (error) { setStatus(error.message, "error"); throw error; }
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
  for (const id of ["total-planned", "total-actual", "total-remaining", "total-percentage"]) document.querySelector(`#${id}`).textContent = "—";
  elements.budgetRows.replaceChildren(); elements.expenseRows.replaceChildren(); elements.notices.replaceChildren();
  elements.budgetEmpty.hidden = false; elements.expenseEmpty.hidden = false;
  resetAdvice();
  setWorkspaceActionsDisabled(true);
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
    try { await api(`/budgets/${id}`, { method: "DELETE" }); await loadApplication(); setStatus("Budget and linked expenses deleted."); document.querySelector("#add-budget").focus(); } catch (error) { setStatus(error.message, "error"); }
  }
  if (target.dataset.action === "delete-expense" && await confirmDelete("Delete expense?", "This permanently removes the selected ledger entry.", target)) {
    try { await api(`/expenses/${id}`, { method: "DELETE" }); await loadJourney(); setStatus("Expense deleted."); document.querySelector("#add-expense").focus(); } catch (error) { setStatus(error.message, "error"); }
  }
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

export { api, loadApplication, majorToMinor, money };