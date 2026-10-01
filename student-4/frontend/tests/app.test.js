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
    if (url === "/budget-api/capabilities") return response({ aiEnabled: true, mcpEnabled: true, ragEnabled: true });
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
    test("renders a validated MCP budget check with exact money and category status", async () => {
      const summary = {
        ...dashboard,
        plannedAmountMinor: Number.MAX_SAFE_INTEGER - 1,
        actualAmountMinor: Number.MAX_SAFE_INTEGER,
        remainingAmountMinor: -1,
        percentageUsed: 100,
        categories: [{ ...dashboard.categories[1], plannedAmountMinor: Number.MAX_SAFE_INTEGER - 1, actualAmountMinor: Number.MAX_SAFE_INTEGER, remainingAmountMinor: -1, percentageUsed: 100, status: "overspent" }],
      };
      const payload = { tool: "budget.get_summary", result: { ok: true, summary } };
      const fetchMock = await start(defaultFetch({ "POST /budget-api/api/budget-check": () => response(payload) }));
      document.querySelector("#run-budget-check").click();

      await vi.waitFor(() => expect(document.querySelector("#budget-check-result").hidden).toBe(false));
      const call = fetchMock.mock.calls.find(([url, options]) => url === "/budget-api/api/budget-check" && options.method === "POST");
      expect(JSON.parse(call[1].body)).toEqual({ journeyLabel: "Journey" });
      expect(document.querySelector("#budget-check-tool").textContent).toBe("budget.get_summary");
      expect(document.querySelector("#check-actual").textContent).toContain("90,071,992,547,409.91");
      expect(document.querySelector("#check-remaining").textContent).toContain("0.01");
      expect(document.querySelector("#budget-check-categories").textContent).toContain("overspent");
      expect(document.querySelector("#budget-check-raw").textContent).toContain('"tool": "budget.get_summary"');
      expect(document.querySelector("#budget-check-status").dataset.state).toBe("success");
    });

    test("renders grounded guidance separately with expandable named citations", async () => {
      const guidance = {
        answer: "Set a category limit and review it regularly. [category-budgets#1]",
        citations: [{ source: "Category budgets and spending statuses", chunkId: "category-budgets#1", snippet: "Budgets are grouped by category.", score: 0.62 }],
        confidence: "high",
      };
      const fetchMock = await start(defaultFetch({ "POST /budget-api/api/budget-guidance": () => response(guidance) }));
      document.querySelector("#guidance-question").value = "How should I plan category budgets?";
      document.querySelector("#guidance-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      document.querySelector("#guidance-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

      await vi.waitFor(() => expect(document.querySelector("#guidance-result").hidden).toBe(false));
      const call = fetchMock.mock.calls.find(([url, options]) => url === "/budget-api/api/budget-guidance" && options.method === "POST");
      expect(JSON.parse(call[1].body)).toEqual({ question: "How should I plan category budgets?" });
      expect(fetchMock.mock.calls.filter(([url]) => url === "/budget-api/api/budget-guidance")).toHaveLength(1);
      expect(document.querySelector("#guidance-confidence").textContent).toBe("High retrieval confidence");
      expect(document.querySelector("#guidance-citations summary").textContent).toBe("Category budgets and spending statuses");
      expect(document.querySelector("#guidance-citations").textContent).toContain("category-budgets#1");
      expect(document.querySelector("#guidance-description").textContent).toContain("does not use this journey's saved totals");
      expect(document.querySelector("#guidance-status").dataset.state).toBe("success");
    });

    test("reports fixed insufficient-context abstention distinctly", async () => {
      const guidance = { answer: "Not enough information in the knowledge base to answer this.", citations: [], confidence: "insufficient" };
      await start(defaultFetch({ "POST /budget-api/api/budget-guidance": () => response(guidance) }));
      document.querySelector("#guidance-question").value = "Can you guarantee tomorrow's fares?";
      document.querySelector("#guidance-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

      await vi.waitFor(() => expect(document.querySelector("#guidance-status").dataset.state).toBe("abstention"));
      expect(document.querySelector("#guidance-answer").textContent).toBe(guidance.answer);
      expect(document.querySelector("#guidance-citations").children).toHaveLength(0);
    });

    test("fails closed for disabled or unavailable capabilities without disabling CRUD", async () => {
      const offFetch = await start(defaultFetch({
        "GET /budget-api/capabilities": () => response({ aiEnabled: true, mcpEnabled: false, ragEnabled: false }),
      }));
      expect(document.querySelector("#run-budget-check").disabled).toBe(true);
      expect(document.querySelector("#submit-guidance").disabled).toBe(true);
      expect(document.querySelector("#budget-check-status").dataset.state).toBe("disabled");
      expect(document.querySelector("#guidance-status").dataset.state).toBe("disabled");
      document.querySelector("#run-budget-check").click();
      document.querySelector("#guidance-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      expect(offFetch.mock.calls.some(([url]) => url.includes("/api/budget-check") || url.includes("/api/budget-guidance"))).toBe(false);
      expect(document.querySelector("#add-budget").disabled).toBe(false);

      vi.resetModules();
      document.body.innerHTML = body;
      document.querySelectorAll("dialog").forEach((dialog) => { dialog.showModal = vi.fn(); dialog.close = vi.fn(); });
      const unavailable = await start(defaultFetch({ "GET /budget-api/capabilities": () => response({ error: { message: "Unavailable" } }, 503) }));
      expect(document.querySelector("#run-budget-check").disabled).toBe(true);
      expect(document.querySelector("#submit-guidance").disabled).toBe(true);
      expect(document.querySelector("#budget-check-status").dataset.state).toBe("disabled");
      expect(document.querySelector("#add-expense").disabled).toBe(false);
      expect(unavailable.mock.calls.some(([url]) => url.includes("/api/budget-check") || url.includes("/api/budget-guidance"))).toBe(false);
    });

    test("enforces the guidance question limit and surfaces dependency failures", async () => {
      const fetchMock = await start(defaultFetch({
        "POST /budget-api/api/budget-check": () => response({ error: { message: "MCP unavailable." } }, 503),
        "POST /budget-api/api/budget-guidance": () => response({ error: { message: "RAG unavailable." } }, 502),
      }));
      const question = document.querySelector("#guidance-question");
      question.value = "x".repeat(1001);
      document.querySelector("#guidance-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      expect(document.querySelector("#guidance-status").textContent).toContain("1 to 1000 characters");
      expect(fetchMock.mock.calls.some(([url]) => url === "/budget-api/api/budget-guidance")).toBe(false);

      question.value = "x".repeat(1000);
      document.querySelector("#guidance-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      await vi.waitFor(() => expect(document.querySelector("#guidance-status").textContent).toBe("RAG unavailable."));
      expect(JSON.parse(fetchMock.mock.calls.find(([url]) => url === "/budget-api/api/budget-guidance")[1].body).question).toHaveLength(1000);
      document.querySelector("#run-budget-check").click();
      await vi.waitFor(() => expect(document.querySelector("#budget-check-status").textContent).toBe("MCP unavailable."));
      expect(document.querySelector("#budget-check-status").dataset.state).toBe("error");
    });

    test("renders hostile guidance and citation text without interpreting HTML", async () => {
      const guidance = {
        answer: "<img src=x onerror=alert(1)> [category-budgets#1]",
        citations: [{ source: "<svg onload=alert(1)>", chunkId: "category-budgets#1", snippet: "<script>alert(1)</script>", score: 0.62 }],
        confidence: "high",
      };
      await start(defaultFetch({ "POST /budget-api/api/budget-guidance": () => response(guidance) }));
      document.querySelector("#guidance-question").value = "How can I plan?";
      document.querySelector("#guidance-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      await vi.waitFor(() => expect(document.querySelector("#guidance-result").hidden).toBe(false));
      expect(document.querySelector("#guidance-answer").textContent).toBe(guidance.answer);
      expect(document.querySelector("#guidance-result img, #guidance-result svg, #guidance-result script")).toBeNull();
    });

    test("prevents duplicate budget checks and stale journey responses", async () => {
      let resolveCheck;
      const checkPromise = new Promise((resolve) => { resolveCheck = resolve; });
      const twoJourneys = [...journeys, { ...journeys[0], journeyLabel: "Other" }];
      const payload = { tool: "budget.get_summary", result: { ok: true, summary: { ...dashboard } } };
      const fetchMock = await start(defaultFetch({
        "GET /budget-api/journeys": () => response(twoJourneys),
        "POST /budget-api/api/budget-check": () => checkPromise,
      }));
      const button = document.querySelector("#run-budget-check");
      button.click();
      button.click();
      expect(button.disabled).toBe(true);
      expect(fetchMock.mock.calls.filter(([url]) => url === "/budget-api/api/budget-check")).toHaveLength(1);

      const selector = document.querySelector("#journey-select");
      selector.value = "Other";
      selector.dispatchEvent(new Event("change", { bubbles: true }));
      resolveCheck(await response(payload));
      await vi.waitFor(() => expect(document.querySelector("#status").textContent).toContain("Other is up to date"));
      expect(document.querySelector("#budget-check-result").hidden).toBe(true);
      expect(document.querySelector("#budget-check-journey").textContent).not.toBe("Journey · AUD");
    });

    test("cancels guidance and invalidates budget check before selected-journey CRUD", async () => {
      const summary = { tool: "budget.get_summary", result: { ok: true, summary: { ...dashboard } } };
      const fetchMock = await start(defaultFetch({ "POST /budget-api/api/budget-check": () => response(summary) }));
      document.querySelector("#run-budget-check").click();
      await vi.waitFor(() => expect(document.querySelector("#budget-check-result").hidden).toBe(false));

      let resolveGuidance;
      const pendingGuidance = new Promise((resolve) => { resolveGuidance = resolve; });
      fetchMock.mockImplementation((url, options = {}) => url === "/budget-api/api/budget-guidance" ? pendingGuidance : defaultFetch()(url, options));
      document.querySelector("#guidance-question").value = "How do I plan?";
      document.querySelector("#guidance-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      expect(document.querySelector("#cancel-guidance").hidden).toBe(false);
      document.querySelector("#cancel-guidance").click();
      resolveGuidance(await response({ answer: "Late answer.", citations: [], confidence: "insufficient" }));
      await vi.waitFor(() => expect(document.querySelector("#guidance-status").textContent).toBe("Guidance request cancelled."));
      expect(document.querySelector("#guidance-result").hidden).toBe(true);

      document.querySelector("#add-expense").click();
      document.querySelector("#expense-description").value = "Snack";
      document.querySelector("#expense-amount").value = "1.00";
      document.querySelector("#expense-date").value = "2026-09-03";
      document.querySelector("#expense-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      expect(document.querySelector("#budget-check-result").hidden).toBe(true);
      expect(document.querySelector("#budget-check-status").textContent).toContain("expense is being changed");
      await vi.waitFor(() => expect(fetchMock.mock.calls.some(([url, options]) => url === "/budget-api/expenses" && options.method === "POST")).toBe(true));
    });

    test("changed guidance and selected-journey writes reject late responses", async () => {
      let resolveGuidance;
      let resolveCheck;
      const pendingGuidance = new Promise((resolve) => { resolveGuidance = resolve; });
      const pendingCheck = new Promise((resolve) => { resolveCheck = resolve; });
      const fetchMock = await start(defaultFetch({
        "POST /budget-api/api/budget-guidance": () => pendingGuidance,
        "POST /budget-api/api/budget-check": () => pendingCheck,
      }));
      const question = document.querySelector("#guidance-question");
      question.value = "First question";
      document.querySelector("#guidance-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      question.value = "Changed question";
      question.dispatchEvent(new Event("input", { bubbles: true }));
      resolveGuidance(await response({ answer: "Stale answer.", citations: [], confidence: "insufficient" }));
      await vi.waitFor(() => expect(document.querySelector("#guidance-status").textContent).toContain("Question changed"));
      expect(document.querySelector("#guidance-result").hidden).toBe(true);

      document.querySelector("#run-budget-check").click();
      document.querySelector("#add-expense").click();
      document.querySelector("#expense-description").value = "Coffee";
      document.querySelector("#expense-amount").value = "2.00";
      document.querySelector("#expense-date").value = "2026-09-03";
      document.querySelector("#expense-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      resolveCheck(await response({ tool: "budget.get_summary", result: { ok: true, summary: { ...dashboard } } }));
      await vi.waitFor(() => expect(document.querySelector("#status").textContent).toContain("up to date"));
      expect(fetchMock.mock.calls.filter(([url]) => url === "/budget-api/api/budget-check")).toHaveLength(1);
      expect(document.querySelector("#budget-check-result").hidden).toBe(true);
    });

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
    const { formatExactMoney, majorToMinor } = await import("../app.js");
    expect(majorToMinor("0.01")).toBe(1);
    expect(majorToMinor("12.3")).toBe(1230);
    expect(() => majorToMinor("12.345")).toThrow(/two decimal/);
    expect(() => majorToMinor("0")).toThrow(/greater than zero/);
    expect(formatExactMoney(1, "USD")).toContain("0.01");
    expect(formatExactMoney(-1, "USD")).toContain("0.01");
    expect(formatExactMoney(-1, "USD")).not.toBe(formatExactMoney(1, "USD"));
    expect(formatExactMoney(Number.MAX_SAFE_INTEGER, "USD")).toContain("90,071,992,547,409.91");
    expect(formatExactMoney(-Number.MAX_SAFE_INTEGER, "USD")).toContain("90,071,992,547,409.91");
    expect(formatExactMoney(-Number.MAX_SAFE_INTEGER, "USD")).not.toBe(formatExactMoney(Number.MAX_SAFE_INTEGER, "USD"));
    expect(() => formatExactMoney(Number.MAX_SAFE_INTEGER + 1, "USD")).toThrow(/safe integer/);
  });
});