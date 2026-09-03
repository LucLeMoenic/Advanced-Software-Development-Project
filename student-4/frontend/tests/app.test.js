// @vitest-environment jsdom

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, test, vi } from "vitest";

const page = readFileSync(resolve(process.cwd(), "index.html"), "utf8");
const body = page.match(/<body>([\s\S]*)<\/body>/)[1];

const journeys = [
  { journeyLabel: "Journey", baseCurrency: "AUD", startDate: "2026-09-01", endDate: "2026-09-07" },
];
const budgets = [
  { id: 1, journeyLabel: "Journey", category: "food", limitAmountMinor: 10000, baseCurrency: "AUD", startDate: "2026-09-01", endDate: "2026-09-07" },
  { id: 2, journeyLabel: "Journey", category: "shopping", limitAmountMinor: 5000, baseCurrency: "AUD", startDate: "2026-09-01", endDate: "2026-09-07" },
];
const expenses = [
  { id: 4, budgetId: 1, journeyLabel: "Journey", category: "food", description: "Market lunch", originalAmountMinor: 5850, originalCurrency: "USD", convertedAmountMinor: 9000, baseCurrency: "AUD", conversionRateScaled: 153846154, rateAsOf: "2026-08-01", spentOn: "2026-09-02", notes: null },
  { id: 5, budgetId: 2, journeyLabel: "Journey", category: "shopping", description: "Local gifts", originalAmountMinor: 6000, originalCurrency: "AUD", convertedAmountMinor: 6000, baseCurrency: "AUD", conversionRateScaled: 100000000, rateAsOf: "2026-08-01", spentOn: "2026-09-03", notes: null },
];
const dashboard = {
  journeyLabel: "Journey", baseCurrency: "AUD", plannedAmountMinor: 15000, actualAmountMinor: 15000,
  remainingAmountMinor: 0, percentageUsed: 100,
  categories: [
    { category: "food", plannedAmountMinor: 10000, actualAmountMinor: 9000, remainingAmountMinor: 1000, percentageUsed: 90, status: "warning" },
    { category: "shopping", plannedAmountMinor: 5000, actualAmountMinor: 6000, remainingAmountMinor: -1000, percentageUsed: 120, status: "overspent" },
  ],
};
const currencies = { rateAsOf: "2026-08-01", rateVersion: "demo-v1", disclaimer: "Demonstration rates only.", currencies: ["AUD", "USD", "EUR"].map((code) => ({ code })) };

function response(value, status = 200) {
  return Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(value) });
}

function defaultFetch(overrides = {}) {
  return vi.fn((url, options = {}) => {
    const method = options.method || "GET";
    const key = `${method} ${url}`;
    if (overrides[key]) return overrides[key](url, options);
    if (url === "/budget-api/journeys") return response(journeys);
    if (url === "/budget-api/currencies") return response(currencies);
    if (url.startsWith("/budget-api/dashboard")) return response(dashboard);
    if (url.startsWith("/budget-api/budgets")) return response(budgets);
    if (url.startsWith("/budget-api/expenses")) return response(expenses);
    if (url === "/budget-api/conversions/preview") return response({ convertedAmountMinor: 155, toCurrency: "AUD", rate: 1.53846154, rateAsOf: "2026-08-01" });
    if (url === "/budget-api/insights") return response({ summary: "Food needs attention.", suggestions: [{ category: "food", text: "Reserve the remaining meal budget." }], source: "ai" });
    throw new Error(`Unexpected request: ${key}`);
  });
}

async function start(fetchMock = defaultFetch()) {
  vi.stubGlobal("fetch", fetchMock);
  await import("../app.js");
  window.dispatchEvent(new Event("load"));
  await vi.waitFor(() => expect(document.querySelector("#status").textContent).toContain("up to date"));
  return fetchMock;
}

beforeEach(() => {
  vi.resetModules();
  vi.restoreAllMocks();
  document.body.innerHTML = body;
  document.querySelectorAll("dialog").forEach((dialog) => {
    dialog.showModal = vi.fn(() => { dialog.open = true; });
    dialog.close = vi.fn(() => { dialog.open = false; });
  });
  document.querySelectorAll("form").forEach((form) => { form.reportValidity = vi.fn(() => true); });
});

describe("Budget & Expense Tracker", () => {
  test("loads the seeded dashboard and renders warning, overspend, ledger, and rate evidence", async () => {
    const fetchMock = await start();

    expect(fetchMock).toHaveBeenCalledWith("/budget-api/journeys", expect.any(Object));
    expect(document.querySelector("#total-planned").textContent).toContain("150.00");
    expect(document.querySelector("#notices").textContent).toContain("Food has reached 90%");
    expect(document.querySelector("#notices").textContent).toContain("Shopping is over budget");
    expect(document.querySelector("#budget-rows").textContent).toContain("overspent");
    expect(document.querySelector("#expense-rows").textContent).toContain("Market lunch");
    expect(document.querySelector("#expense-rows").textContent).toContain("90.00");
    expect(document.querySelector("#rate-date").textContent).toContain("demo-v1");
  });

  test("creates and updates a budget with exact minor units", async () => {
    const fetchMock = await start();
    document.querySelector("#add-budget").click();
    expect(document.querySelector("#budget-dialog").open).toBe(true);
    document.querySelector("#budget-journey").value = "Journey";
    document.querySelector("#budget-category").value = "activities";
    document.querySelector("#budget-amount").value = "123.45";
    document.querySelector("#budget-currency").value = "AUD";
    document.querySelector("#budget-start").value = "2026-09-01";
    document.querySelector("#budget-end").value = "2026-09-07";
    document.querySelector("#budget-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

    await vi.waitFor(() => expect(fetchMock.mock.calls.some(([url, options]) => url === "/budget-api/budgets" && options.method === "POST")).toBe(true));
    const createCall = fetchMock.mock.calls.find(([url, options]) => url === "/budget-api/budgets" && options.method === "POST");
    expect(JSON.parse(createCall[1].body).limitAmountMinor).toBe(12345);

    document.querySelector("[data-action='edit-budget']").click();
    document.querySelector("#budget-amount").value = "140.00";
    document.querySelector("#budget-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await vi.waitFor(() => expect(fetchMock.mock.calls.some(([url, options]) => url === "/budget-api/budgets/1" && options.method === "PUT")).toBe(true));
  });

  test("confirmed budget delete calls the backend and restores focus", async () => {
    const fetchMock = await start();
    const deleteButton = document.querySelector("[data-action='delete-budget']");
    deleteButton.focus();
    deleteButton.click();
    expect(document.querySelector("#confirm-dialog").open).toBe(true);
    expect(document.querySelector("#confirm-cancel")).toBe(document.activeElement);
    document.querySelector("#confirm-accept").click();

    await vi.waitFor(() => expect(fetchMock.mock.calls.some(([url, options]) => url === "/budget-api/budgets/1" && options.method === "DELETE")).toBe(true));
    await vi.waitFor(() => expect(document.querySelector("#add-budget")).toBe(document.activeElement));
  });

  test("previews, creates, updates, and confirmed-deletes an expense", async () => {
    const fetchMock = await start();
    document.querySelector("#add-expense").click();
    document.querySelector("#expense-description").value = "Train ticket";
    document.querySelector("#expense-amount").value = "1.01";
    document.querySelector("#expense-currency").value = "USD";
    document.querySelector("#expense-date").value = "2026-09-03";
    document.querySelector("#expense-amount").dispatchEvent(new Event("change", { bubbles: true }));
    await vi.waitFor(() => expect(document.querySelector("#conversion-preview").textContent).toContain("1.55"));
    document.querySelector("#expense-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await vi.waitFor(() => expect(fetchMock.mock.calls.some(([url, options]) => url === "/budget-api/expenses" && options.method === "POST")).toBe(true));
    const create = fetchMock.mock.calls.find(([url, options]) => url === "/budget-api/expenses" && options.method === "POST");
    expect(JSON.parse(create[1].body)).not.toHaveProperty("convertedAmountMinor");

    document.querySelector("[data-action='edit-expense']").click();
    document.querySelector("#expense-description").value = "Updated lunch";
    document.querySelector("#expense-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await vi.waitFor(() => expect(fetchMock.mock.calls.some(([url, options]) => url === "/budget-api/expenses/4" && options.method === "PUT")).toBe(true));

    document.querySelector("[data-action='delete-expense']").click();
    document.querySelector("#confirm-accept").click();
    await vi.waitFor(() => expect(fetchMock.mock.calls.some(([url, options]) => url === "/budget-api/expenses/4" && options.method === "DELETE")).toBe(true));
  });

  test("reports amount validation and API failures in the live status", async () => {
    const fetchMock = defaultFetch({
      "POST /budget-api/budgets": () => response({ error: { message: "A matching budget already exists.", fields: {} } }, 409),
    });
    await start(fetchMock);
    document.querySelector("#add-budget").click();
    document.querySelector("#budget-amount").value = "1.234";
    document.querySelector("#budget-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(document.querySelector("#status").textContent).toContain("at most two decimal places");
    expect(document.querySelector("#status").dataset.kind).toBe("error");

    document.querySelector("#budget-amount").value = "100.00";
    document.querySelector("#budget-start").value = "2026-09-01";
    document.querySelector("#budget-end").value = "2026-09-07";
    document.querySelector("#budget-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await vi.waitFor(() => expect(document.querySelector("#status").textContent).toBe("A matching budget already exists."));
  });

  test("renders AI retry and deterministic fallback sources with a loading state", async () => {
    let resolveAdvice;
    const advicePromise = new Promise((resolve) => { resolveAdvice = resolve; });
    const fetchMock = defaultFetch({ "POST /budget-api/insights": () => advicePromise });
    await start(fetchMock);
    const button = document.querySelector("#generate-advice");
    button.click();
    expect(button.textContent).toBe("Generating...");
    expect(button.disabled).toBe(true);
    resolveAdvice(await response({ summary: "Recovered.", suggestions: [{ category: "food", text: "Track meals." }], source: "ai_retry" }));
    await vi.waitFor(() => expect(document.querySelector("#advice-source").textContent).toBe("AI after retry"));

    fetchMock.mockImplementation((url, options = {}) => url === "/budget-api/insights"
      ? response({ summary: "Fallback.", suggestions: [{ category: "food", text: "Track meals." }], source: "fallback" })
      : defaultFetch()(url, options));
    button.click();
    await vi.waitFor(() => expect(document.querySelector("#advice-source").textContent).toBe("Reliable fallback"));
    expect(document.querySelector("#status").textContent).toContain("deterministic advice");
  });

  test("handles an empty journey list and renders hostile text without HTML interpretation", async () => {
    const emptyFetch = defaultFetch({ "GET /budget-api/journeys": () => response([]) });
    vi.stubGlobal("fetch", emptyFetch);
    await import("../app.js");
    window.dispatchEvent(new Event("load"));
    await vi.waitFor(() => expect(document.querySelector("#status").textContent).toContain("No journeys"));
    expect(document.querySelector("#budget-empty").hidden).toBe(false);

    vi.resetModules();
    document.body.innerHTML = body;
    document.querySelectorAll("dialog").forEach((dialog) => { dialog.showModal = vi.fn(); dialog.close = vi.fn(); });
    const hostile = [{ ...expenses[0], description: "<img src=x onerror=alert(1)>" }];
    await start(defaultFetch({ "GET /budget-api/expenses?journeyLabel=Journey": () => response(hostile) }));
    expect(document.querySelector("#expense-rows").textContent).toContain("<img src=x");
    expect(document.querySelector("#expense-rows img")).toBeNull();
  });

  test("clears stale actions on journey failure and calculates each budget period separately", async () => {
    const periodBudgets = [
      { ...budgets[0], id: 1, startDate: "2026-09-01", endDate: "2026-09-07" },
      { ...budgets[0], id: 3, startDate: "2026-10-01", endDate: "2026-10-07" },
    ];
    const periodExpenses = [{ ...expenses[0], budgetId: 1, convertedAmountMinor: 5000 }];
    const fetchMock = await start(defaultFetch({
      "GET /budget-api/budgets?journeyLabel=Journey": () => response(periodBudgets),
      "GET /budget-api/expenses?journeyLabel=Journey": () => response(periodExpenses),
    }));
    const rows = document.querySelectorAll("#budget-rows tr");
    expect(rows[0].children[2].textContent).toContain("50.00");
    expect(rows[1].children[2].textContent).toContain("0.00");

    fetchMock.mockImplementation((url, options = {}) => url.startsWith("/budget-api/dashboard")
      ? response({ error: { message: "Journey data is unavailable." } }, 503)
      : defaultFetch()(url, options));
    document.querySelector("#journey-select").dispatchEvent(new Event("change", { bubbles: true }));
    await vi.waitFor(() => expect(document.querySelector("#status").textContent).toBe("Journey data is unavailable."));
    expect(document.querySelector("#budget-rows").children).toHaveLength(0);
    expect(document.querySelector("#add-expense").disabled).toBe(true);
    expect(document.querySelector("#generate-advice").disabled).toBe(true);
  });

  test("full reload failures clear stale data and are not overwritten by mutation success", async () => {
    const fetchMock = await start();
    fetchMock.mockImplementation((url, options = {}) => {
      if (url === "/budget-api/budgets" && options.method === "POST") return response({ id: 9 }, 201);
      if (url === "/budget-api/journeys") return response({ error: { message: "Journey reload failed." } }, 503);
      return defaultFetch()(url, options);
    });
    document.querySelector("#add-budget").click();
    document.querySelector("#budget-journey").value = "Journey";
    document.querySelector("#budget-category").value = "food";
    document.querySelector("#budget-amount").value = "100.00";
    document.querySelector("#budget-currency").value = "AUD";
    document.querySelector("#budget-start").value = "2026-09-01";
    document.querySelector("#budget-end").value = "2026-09-07";
    document.querySelector("#budget-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

    await vi.waitFor(() => expect(document.querySelector("#status").textContent).toBe("Journey reload failed."));
    expect(document.querySelector("#budget-rows").children).toHaveLength(0);
    expect(document.querySelector("#add-budget").disabled).toBe(true);
    expect(document.querySelector("#add-expense").disabled).toBe(true);
  });

  test("minor-unit parser accepts cents and rejects unsafe values", async () => {
    vi.stubGlobal("fetch", defaultFetch());
    const { majorToMinor } = await import("../app.js");
    expect(majorToMinor("0.01")).toBe(1);
    expect(majorToMinor("12.3")).toBe(1230);
    expect(() => majorToMinor("12.345")).toThrow(/two decimal/);
    expect(() => majorToMinor("0")).toThrow(/greater than zero/);
  });
});