// @vitest-environment jsdom

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const page = readFileSync(resolve(process.cwd(), "index.html"), "utf8");
const body = page.match(/<body>([\s\S]*)<\/body>/)[1];
const sharedNginx = readFileSync(resolve(process.cwd(), "../../shared/vue-frontend/nginx.conf"), "utf8");

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

function previewFixture(source = dashboard, limits = source.categories.map((category) => category.plannedAmountMinor)) {
  const proposed = structuredClone(source);
  proposed.categories.forEach((category, index) => {
    category.plannedAmountMinor = limits[index];
    category.remainingAmountMinor = category.plannedAmountMinor - category.actualAmountMinor;
    category.percentageUsed = category.actualAmountMinor * 100 / category.plannedAmountMinor;
    category.status = category.actualAmountMinor > category.plannedAmountMinor ? "overspent" : category.actualAmountMinor * 100 >= category.plannedAmountMinor * 80 ? "warning" : "within_budget";
  });
  proposed.plannedAmountMinor = limits.reduce((sum, value) => sum + value, 0);
  proposed.remainingAmountMinor = proposed.plannedAmountMinor - proposed.actualAmountMinor;
  proposed.percentageUsed = proposed.actualAmountMinor * 100 / proposed.plannedAmountMinor;
  return { original: structuredClone(source), proposed, snapshotHash: "a".repeat(64) };
}

function submitWhatIf() {
  document.querySelector("#what-if-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
}

const workflowId = "wf-20261023T010000Z-1234abcd";
const workflowPath = `/budget-api/what-if/workflows/${workflowId}`;
const workflowToken = "protected-test-handle";

function workflowFixture(status = "awaiting_human_review") {
  const evidence = [{ id: "snapshot", title: "Journey budget snapshot", text: "Authoritative snapshot" }, ...dashboard.categories.map((category) => ({ id: `category:${category.category}`, title: `Category: ${category.category}`, text: JSON.stringify(category) }))];
  const plan = { objective: "Assess proposed limits", steps: [{ id: "s1", description: "Compare evidence" }], required_evidence_ids: ["snapshot", "category:food"], success_criteria: ["Actual spending unchanged"] };
  const work = { summary: "Food needs attention", items: [{ id: "i1", subject: "Category: food", detail: "Review meals", evidence_ids: ["category:food"] }, { id: "i2", subject: "Category: shopping", detail: "Review gifts", evidence_ids: ["category:shopping"] }] };
  const review = { verdict: "pass", model_verdict: "pass", degraded: false, automatic_findings: [], model_findings: [], findings: [], recommendations: ["Review both categories"] };
  const workflow = { id: workflowId, feature: "student-4", task: "Assess limits", submitted_by: "student-4-backend", status, created_at: "2026-10-23T01:00:00Z", updated_at: "2026-10-23T01:00:01Z", evidence, plan: null, work: null, review: null, human_decision: null, final_output: null, history: [], error: null };
  if (!["queued", "planning"].includes(status)) workflow.plan = plan;
  if (!["queued", "planning", "working"].includes(status)) workflow.work = work;
  if (!["queued", "planning", "working", "reviewing", "failed"].includes(status)) workflow.review = review;
  for (const [stage, output] of [["planner", workflow.plan], ["worker", workflow.work], ["reviewer", workflow.review]]) {
    if (output) workflow.history.push({ stage, agent: stage, prompt: `multi-agent-${stage}-v1.txt`, model: "test-model", started_at: workflow.created_at, finished_at: workflow.updated_at, duration_ms: 1000, ok: true, output });
  }
  if (status === "failed") workflow.error = { code: "agent_failed", message: "Worker unavailable" };
  return { id: workflowId, status, preview: previewFixture(), workflow };
}

function decisionFixture(payload) {
  const status = { approve: "approved", correct: "corrected", partial: "partially_accepted", reject: "rejected" }[payload.decision];
  const envelope = workflowFixture(status);
  envelope.workflow.human_decision = { decision: payload.decision, notes: payload.notes, decided_by: payload.decidedBy, decided_at: "2026-10-23T01:00:02Z" };
  envelope.workflow.final_output = payload.decision === "reject" ? null : payload.correctedOutput || structuredClone(envelope.workflow.work);
  if (payload.decision === "partial") {
    envelope.workflow.human_decision.accepted_item_ids = payload.acceptedItemIds;
    envelope.workflow.human_decision.rejected_item_ids = envelope.workflow.work.items.map((item) => item.id).filter((id) => !payload.acceptedItemIds.includes(id));
    envelope.workflow.final_output.items = envelope.workflow.final_output.items.filter((item) => payload.acceptedItemIds.includes(item.id));
  }
  return envelope;
}

async function previewPlanner(overrides = {}) {
  const fetchMock = await start(defaultFetch({
    "GET /budget-api/capabilities": () => response({ mcpEnabled: true, ragEnabled: true, multiAgentEnabled: true }),
    "POST /budget-api/what-if/preview": () => response(previewFixture()),
    ...overrides,
  }));
  submitWhatIf();
  await vi.waitFor(() => expect(document.querySelector("#start-what-if").disabled).toBe(false));
  return fetchMock;
}

async function startPlanner(overrides = {}, status = "awaiting_human_review", fakeTimers = false) {
  const fetchMock = await previewPlanner({ "POST /budget-api/what-if/workflows": () => response({ ...workflowFixture(status), token: workflowToken }, 202), ...overrides });
  if (fakeTimers) vi.useFakeTimers();
  document.querySelector("#start-what-if").click();
  if (fakeTimers) {
    await vi.advanceTimersByTimeAsync(0);
    expect(document.querySelector("#what-if-record").textContent).toContain(workflowId);
  } else {
    await vi.waitFor(() => expect(document.querySelector("#what-if-record").textContent).toContain(workflowId));
  }
  return fetchMock;
}

function chooseDecision(decision, name = "Liam Zelmanowski", notes = "Reviewed against evidence") {
  document.querySelector("#what-if-decision").value = decision;
  document.querySelector("#what-if-decision").dispatchEvent(new Event("change", { bubbles: true }));
  document.querySelector("#what-if-name").value = name;
  document.querySelector("#what-if-notes").value = notes;
}

function submitDecision() {
  document.querySelector("#what-if-decision-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
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

afterEach(() => {
  window.dispatchEvent(new Event("pagehide"));
  vi.useRealTimers();
});

describe("Budget & Expense Tracker", () => {
  test("recovers an accepted start's ID and token from error fields by GET only", async () => {
    const fetchMock = await previewPlanner({
      "POST /budget-api/what-if/workflows": () => response({ error: { code: "multi_agent_timeout", message: "Start accepted; poll this workflow.", fields: { id: workflowId, token: workflowToken } } }, 503),
      [`GET ${workflowPath}`]: () => response(workflowFixture()),
    });
    document.querySelector("#start-what-if").click();
    await vi.waitFor(() => expect(document.querySelector("#retry-what-if").hidden).toBe(false));
    expect(document.querySelector("#what-if-record").textContent).toContain(workflowId);
    expect(document.querySelector("#what-if-status").textContent).not.toContain(workflowToken);
    submitWhatIf(); document.querySelector("#start-what-if").click();
    document.querySelector("#retry-what-if").click();
    await vi.waitFor(() => expect(document.querySelector("#what-if-decision-form").hidden).toBe(false));
    expect(fetchMock.mock.calls.filter(([url]) => url === "/budget-api/what-if/workflows")).toHaveLength(1);
    expect(fetchMock.mock.calls.filter(([url]) => url === workflowPath)).toHaveLength(1);
  });

  test("locks an unknown start outcome without retrying a POST or fabricating a handle", async () => {
    const fetchMock = await previewPlanner({ "POST /budget-api/what-if/workflows": () => Promise.reject(new TypeError("Network interrupted")) });
    document.querySelector("#start-what-if").click();
    await vi.waitFor(() => expect(document.querySelector("#what-if-status").textContent).toContain("Start outcome unknown"));
    submitWhatIf(); document.querySelector("#start-what-if").click();
    expect(document.querySelector("#retry-what-if").hidden).toBe(true);
    expect(document.querySelector("#preview-what-if").disabled).toBe(true);
    expect(fetchMock.mock.calls.filter(([url]) => url === "/budget-api/what-if/workflows")).toHaveLength(1);
  });

  test("shows busy without automatically repeating a rejected start", async () => {
    const fetchMock = await previewPlanner({ "POST /budget-api/what-if/workflows": () => response({ error: { code: "multi_agent_busy", message: "Agent server is busy. Try later." } }, 503) });
    document.querySelector("#start-what-if").click();
    await vi.waitFor(() => expect(document.querySelector("#what-if-status").textContent).toContain("busy"));
    expect(document.querySelector("#start-what-if").disabled).toBe(false);
    expect(fetchMock.mock.calls.filter(([url]) => url === "/budget-api/what-if/workflows")).toHaveLength(1);
  });

  test("aborts duplicate preview work on amount edits and ignores the late response", async () => {
    let finish;
    const fetchMock = await start(defaultFetch({ "POST /budget-api/what-if/preview": () => new Promise((resolve) => { finish = resolve; }) }));
    submitWhatIf(); submitWhatIf();
    const calls = fetchMock.mock.calls.filter(([url]) => url.endsWith("/what-if/preview"));
    expect(calls).toHaveLength(1);
    expect(document.querySelector("#what-if-status").getAttribute("aria-busy")).toBe("true");
    const input = document.querySelector("#what-if-limit-food");
    input.value = "99.99"; input.dispatchEvent(new Event("input", { bubbles: true }));
    expect(calls[0][1].signal.aborted).toBe(true);
    finish(await response(previewFixture()));
    await Promise.resolve(); await Promise.resolve();
    expect(document.querySelector("#what-if-preview").hidden).toBe(true);
    expect(document.querySelector("#what-if-status").dataset.state).toBe("stale");
    expect(input.value).toBe("99.99");
  });

  test("prevents duplicate starts while the initial request is pending", async () => {
    let finish;
    const fetchMock = await previewPlanner({ "POST /budget-api/what-if/workflows": () => new Promise((resolve) => { finish = resolve; }) });
    document.querySelector("#start-what-if").click(); document.querySelector("#start-what-if").click(); submitWhatIf();
    expect(fetchMock.mock.calls.filter(([url]) => url === "/budget-api/what-if/workflows")).toHaveLength(1);
    expect(document.querySelector("#preview-what-if").disabled).toBe(true);
    finish(await response({ ...workflowFixture(), token: workflowToken }, 202));
    await vi.waitFor(() => expect(document.querySelector("#what-if-decision-form").hidden).toBe(false));
  });

  test("never displays a previous workflow or preview after selecting another journey", async () => {
    let finishPoll;
    const fetchMock = await startPlanner({
      "GET /budget-api/journeys": () => response([...journeys, { ...journeys[0], journeyLabel: "Other" }]),
      "GET /budget-api/dashboard?journeyLabel=Other": () => response({ ...dashboard, journeyLabel: "Other" }),
      [`GET ${workflowPath}`]: () => new Promise((resolve) => { finishPoll = resolve; }),
    }, "working", true);
    await vi.advanceTimersByTimeAsync(3000);
    const poll = fetchMock.mock.calls.find(([url]) => url === workflowPath);
    const selector = document.querySelector("#journey-select"); selector.value = "Other"; selector.dispatchEvent(new Event("change", { bubbles: true }));
    expect(poll[1].signal.aborted).toBe(true);
    expect(document.querySelector("#what-if-preview").hidden).toBe(true);
    expect(document.querySelector("#what-if-record").textContent).toBe("");
    finishPoll(await response(workflowFixture()));
    await vi.advanceTimersByTimeAsync(0);
    expect(document.querySelector("#status").textContent).toContain("Other is up to date");
    expect(document.querySelector("#what-if-workflow").hidden).toBe(true);
    expect(document.querySelector("#start-what-if").disabled).toBe(true);
    await vi.advanceTimersByTimeAsync(9000);
    expect(fetchMock.mock.calls.filter(([url]) => url === workflowPath)).toHaveLength(1);
  });

  test("ignores a late dashboard load when the user returns to the original journey", async () => {
    let finishDashboard;
    const fetchMock = await start(defaultFetch({
      "GET /budget-api/journeys": () => response([...journeys, { ...journeys[0], journeyLabel: "Other" }]),
      "GET /budget-api/dashboard?journeyLabel=Other": () => new Promise((resolve) => { finishDashboard = resolve; }),
    }));
    const selector = document.querySelector("#journey-select");
    selector.value = "Other"; selector.dispatchEvent(new Event("change", { bubbles: true }));
    const otherCall = fetchMock.mock.calls.find(([url]) => url === "/budget-api/dashboard?journeyLabel=Other");
    selector.value = "Journey"; selector.dispatchEvent(new Event("change", { bubbles: true }));
    await vi.waitFor(() => expect(document.querySelector("#status").textContent).toContain("Journey is up to date"));
    finishDashboard(await response({ ...dashboard, journeyLabel: "Other", baseCurrency: "USD" }));
    await Promise.resolve(); await Promise.resolve(); await Promise.resolve();
    expect(otherCall[1].signal.aborted).toBe(true);
    expect(document.querySelector("#what-if-currency").textContent).toBe("(AUD)");
    expect(document.querySelector("#status").textContent).toContain("Journey is up to date");
  });

  test("invalidates preview, token and human draft before a CRUD write and refresh", async () => {
    const fetchMock = await startPlanner();
    chooseDecision("correct");
    document.querySelector("#add-expense").click();
    document.querySelector("#expense-description").value = "Coffee";
    document.querySelector("#expense-amount").value = "1.00";
    document.querySelector("#expense-date").value = "2026-09-03";
    document.querySelector("#expense-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(document.querySelector("#what-if-preview").hidden).toBe(true);
    expect(document.querySelector("#what-if-workflow").hidden).toBe(true);
    submitDecision();
    await vi.waitFor(() => expect(document.querySelector("#status").textContent).toContain("Expense created"));
    expect(fetchMock.mock.calls.some(([url]) => url.endsWith("/decision"))).toBe(false);
    expect(document.querySelector("#what-if-name").value).toBe("");
    expect(document.querySelector("#start-what-if").disabled).toBe(true);
  });

  test("invalidates an active review on amount change without sending another agent request", async () => {
    const fetchMock = await startPlanner({}, "working");
    const input = document.querySelector("#what-if-limit-food");
    input.value = "80.01"; input.dispatchEvent(new Event("input", { bubbles: true }));
    expect(document.querySelector("#what-if-status").dataset.state).toBe("stale");
    expect(document.querySelector("#what-if-preview").hidden).toBe(true);
    expect(document.querySelector("#what-if-workflow").hidden).toBe(true);
    expect(document.querySelector("#start-what-if").disabled).toBe(true);
    vi.useFakeTimers(); await vi.advanceTimersByTimeAsync(6000);
    expect(fetchMock.mock.calls.some(([url]) => url === workflowPath)).toBe(false);
  });

  test("fails closed on malformed workflow finances but retains its handle for status recovery", async () => {
    const bad = workflowFixture(); bad.preview.proposed.actualAmountMinor++;
    const fetchMock = await previewPlanner({ "POST /budget-api/what-if/workflows": () => response({ ...bad, token: workflowToken }, 202), [`GET ${workflowPath}`]: () => response(workflowFixture()) });
    document.querySelector("#start-what-if").click();
    await vi.waitFor(() => expect(document.querySelector("#what-if-status").dataset.state).toBe("error"));
    expect(document.querySelector("#what-if-decision-form").hidden).toBe(true);
    document.querySelector("#retry-what-if").click();
    await vi.waitFor(() => expect(document.querySelector("#what-if-decision-form").hidden).toBe(false));
    expect(fetchMock.mock.calls.filter(([url]) => url === "/budget-api/what-if/workflows")).toHaveLength(1);
  });

  test("prefills aggregated dashboard limits even when a category has multiple saved periods", async () => {
    const aggregate = previewFixture(dashboard, [15000, 5000]).proposed;
    await start(defaultFetch({ "GET /budget-api/dashboard?journeyLabel=Journey": () => response(aggregate), "GET /budget-api/budgets?journeyLabel=Journey": () => response([...budgets, { ...budgets[0], id: 3, limitAmountMinor: 5000 }]) }));
    expect(document.querySelectorAll("#what-if-inputs input")).toHaveLength(2);
    expect(document.querySelector("#what-if-limit-food").value).toBe("150.00");
  });

  test("starts one protected workflow with the exact preview snapshot and renders shared records", async () => {
    const fetchMock = await startPlanner();
    document.querySelector("#start-what-if").click();
    const calls = fetchMock.mock.calls.filter(([url]) => url === "/budget-api/what-if/workflows");
    expect(calls).toHaveLength(1);
    expect(JSON.parse(calls[0][1].body)).toEqual({ journeyLabel: "Journey", limits: [{ category: "food", limitAmountMinor: 10000 }, { category: "shopping", limitAmountMinor: 5000 }], snapshotHash: "a".repeat(64) });
    const text = document.querySelector("#what-if-record").textContent;
    for (const value of [workflowId, "Stage history", "planner: complete", "Assess proposed limits", "Compare evidence", "Food needs attention", "i1: Category: food", "category:food", "Reviewer: pass", "Review both categories"]) expect(text).toContain(value);
    expect(text).not.toContain(workflowToken);
    expect(document.querySelector("#what-if-decision-form").hidden).toBe(false);
    expect(document.querySelector("#what-if-name").value).toBe("");
    expect(document.querySelector("#what-if-decision").value).toBe("");
    expect(document.querySelector("#preview-what-if").disabled).toBe(true);
    expect(document.activeElement.id).toBe("what-if-workflow-heading");
  });

  test.each(["approve", "correct", "partial", "reject"])("records explicit %s commentary without financial writes", async (decision) => {
    const fetchMock = await startPlanner({ [`POST ${workflowPath}/decision`]: (_url, options) => response(decisionFixture(JSON.parse(options.body))) });
    chooseDecision(decision);
    if (decision === "partial") document.querySelector("#what-if-partial input").checked = true;
    if (decision === "correct") {
      document.querySelector("#what-if-corrected-summary").value = "Human corrected summary";
      document.querySelector("#what-if-corrections textarea[data-item-id='i1']").value = "Human corrected meals";
    }
    submitDecision();
    submitDecision();
    await vi.waitFor(() => expect(document.querySelector("#what-if-decision-form").hidden).toBe(true));
    const calls = fetchMock.mock.calls.filter(([url]) => url.endsWith("/decision"));
    expect(calls).toHaveLength(1);
    expect(calls[0][1].headers["X-WhatIf-Token"]).toBe(workflowToken);
    const payload = JSON.parse(calls[0][1].body);
    expect(payload).toMatchObject({ decision, decidedBy: "Liam Zelmanowski", notes: "Reviewed against evidence" });
    expect(payload.decided_by).toBeUndefined();
    if (decision === "partial") expect(payload.acceptedItemIds).toEqual(["i1"]);
    if (decision === "correct") {
      expect(payload.correctedOutput).toEqual({ summary: "Human corrected summary", items: [{ ...workflowFixture().workflow.work.items[0], detail: "Human corrected meals" }, workflowFixture().workflow.work.items[1]] });
      expect(document.querySelector("#what-if-record").textContent).toContain("Human corrected summary");
    }
    expect(document.querySelector("#what-if-status").textContent).toContain("no saved budgets changed");
    expect(document.querySelector("#total-planned").textContent).toContain("150.00");
    expect(fetchMock.mock.calls.some(([url, options]) => /\/(budgets|expenses)/.test(url) && options.method && options.method !== "GET")).toBe(false);
  });

  test.each([["approve", "", ""], ["approve", "human", ""], ["approve", "x".repeat(61), ""], ["reject", "Liam", "   "], ["approve", "Liam", "x".repeat(1001)], ["partial", "Liam", ""], ["", "Liam", ""]])("blocks incomplete decision %s / %s", async (decision, name, notes) => {
    const fetchMock = await startPlanner();
    chooseDecision(decision, name, notes);
    submitDecision();
    expect(document.querySelector("#what-if-status").dataset.state).toBe("error");
    expect(fetchMock.mock.calls.some(([url]) => url.endsWith("/decision"))).toBe(false);
  });

  test("rejects unknown partial IDs and empty or oversized correction commentary", async () => {
    const fetchMock = await startPlanner();
    chooseDecision("partial");
    const checkbox = document.querySelector("#what-if-partial input"); checkbox.value = "i99"; checkbox.checked = true;
    submitDecision();
    expect(document.querySelector("#what-if-status").textContent).toContain("known item");
    chooseDecision("correct");
    document.querySelector("#what-if-corrected-summary").value = "";
    submitDecision();
    expect(document.querySelector("#what-if-status").textContent).toContain("1 to 400");
    document.querySelector("#what-if-corrected-summary").value = "Corrected";
    document.querySelector("#what-if-corrections textarea[data-item-id]").value = "x".repeat(401);
    submitDecision();
    expect(fetchMock.mock.calls.some(([url]) => url.endsWith("/decision"))).toBe(false);
  });

  test("polls each 3 seconds with the token, stops for human review, and never autoapproves", async () => {
    const fetchMock = await startPlanner({ [`GET ${workflowPath}`]: () => response(workflowFixture()) }, "queued", true);
    await vi.advanceTimersByTimeAsync(2999);
    expect(fetchMock.mock.calls.filter(([url, options]) => url === workflowPath && !options.method)).toHaveLength(0);
    await vi.advanceTimersByTimeAsync(1);
    expect(fetchMock.mock.calls.filter(([url, options]) => url === workflowPath && !options.method)).toHaveLength(1);
    const call = fetchMock.mock.calls.find(([url]) => url === workflowPath);
    expect(call[1].headers["X-WhatIf-Token"]).toBe(workflowToken);
    expect(document.querySelector("#what-if-decision-form").hidden).toBe(false);
    await vi.advanceTimersByTimeAsync(9000);
    expect(fetchMock.mock.calls.filter(([url]) => url === workflowPath)).toHaveLength(1);
    expect(fetchMock.mock.calls.some(([url]) => url.endsWith("/decision"))).toBe(false);
  });

  test("stops polling with focus restoration and resumes by GET without another start", async () => {
    const fetchMock = await startPlanner({ [`GET ${workflowPath}`]: () => response(workflowFixture()) }, "working");
    vi.useFakeTimers();
    const stop = document.querySelector("#stop-what-if");
    expect(stop.title).toContain("Stop automatic");
    stop.focus(); stop.click();
    expect(document.activeElement.id).toBe("retry-what-if");
    await vi.advanceTimersByTimeAsync(9000);
    expect(fetchMock.mock.calls.some(([url]) => url === workflowPath)).toBe(false);
    document.querySelector("#retry-what-if").click();
    await vi.advanceTimersByTimeAsync(0);
    expect(document.querySelector("#what-if-decision-form").hidden).toBe(false);
    expect(fetchMock.mock.calls.filter(([url]) => url === "/budget-api/what-if/workflows")).toHaveLength(1);
    expect(fetchMock.mock.calls.filter(([url]) => url === workflowPath)).toHaveLength(1);
  });

  test("bounds automatic polling to 20 minutes and tears down on pagehide", async () => {
    const fetchMock = await startPlanner({ [`GET ${workflowPath}`]: () => response(workflowFixture("planning")) }, "queued", true);
    await vi.advanceTimersByTimeAsync(20 * 60 * 1000);
    expect(document.querySelector("#what-if-status").textContent).toContain("20 minutes");
    const count = fetchMock.mock.calls.length;
    await vi.advanceTimersByTimeAsync(6000);
    expect(fetchMock.mock.calls).toHaveLength(count);
    document.querySelector("#retry-what-if").click();
    await vi.advanceTimersByTimeAsync(0);
    window.dispatchEvent(new Event("pagehide"));
    const afterHide = fetchMock.mock.calls.length;
    await vi.advanceTimersByTimeAsync(6000);
    expect(fetchMock.mock.calls).toHaveLength(afterHide);
    expect(document.querySelector("#what-if-workflow").hidden).toBe(true);
  });

  test("shows degraded reviewer evidence without fabricating approval", async () => {
    const degraded = workflowFixture();
    degraded.workflow.review = { ...degraded.workflow.review, verdict: "concerns", model_verdict: "concerns", degraded: true, findings: [{ severity: "warning", item_id: null, message: "Reviewer model unavailable" }], recommendations: ["Inspect evidence manually"] };
    await startPlanner({ "POST /budget-api/what-if/workflows": () => response({ ...degraded, token: workflowToken }, 202) });
    expect(document.querySelector("#what-if-status").dataset.state).toBe("degraded");
    expect(document.querySelector("#what-if-record").textContent).toContain("Reviewer model unavailable");
    expect(document.querySelector("#what-if-record").textContent).toContain("Inspect evidence manually");
    expect(document.querySelector("#what-if-decision-form").hidden).toBe(false);
    expect(document.querySelector("#what-if-decision").value).toBe("");
  });

  test("shows terminal failure and stops polling", async () => {
    const fetchMock = await startPlanner({}, "failed");
    expect(document.querySelector("#what-if-status").dataset.state).toBe("failed");
    expect(document.querySelector("#what-if-record").textContent).toContain("Worker unavailable");
    expect(document.querySelector("#what-if-decision-form").hidden).toBe(true);
    vi.useFakeTimers();
    await vi.advanceTimersByTimeAsync(6000);
    expect(fetchMock.mock.calls.some(([url]) => url === workflowPath)).toBe(false);
  });

  test("keeps an uncertain decision locked until a GET confirms the applied decision", async () => {
    const payload = { decision: "approve", notes: "Reviewed against evidence", decidedBy: "Liam Zelmanowski" };
    const fetchMock = await startPlanner({ [`POST ${workflowPath}/decision`]: () => Promise.reject(new TypeError("Network interrupted")), [`GET ${workflowPath}`]: () => response(decisionFixture(payload)) });
    chooseDecision("approve"); submitDecision();
    await vi.waitFor(() => expect(document.querySelector("#what-if-status").textContent).toContain("outcome unknown"));
    submitDecision(); document.querySelector("#start-what-if").click(); submitWhatIf();
    expect(document.querySelector("#submit-what-if-decision").disabled).toBe(true);
    document.querySelector("#retry-what-if").click();
    await vi.waitFor(() => expect(document.querySelector("#what-if-decision-form").hidden).toBe(true));
    expect(document.querySelector("#what-if-status").textContent).toContain("Approved");
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith("/decision"))).toHaveLength(1);
    expect(fetchMock.mock.calls.filter(([url]) => url === "/budget-api/what-if/workflows")).toHaveLength(1);
  });

  test("retries failed status requests using GET and retains the protected handle", async () => {
    let fail = true;
    const fetchMock = await startPlanner({ [`GET ${workflowPath}`]: () => fail ? response({ error: { code: "multi_agent_unavailable", message: "Unavailable" } }, 503) : response(workflowFixture()) }, "queued");
    document.querySelector("#stop-what-if").click();
    document.querySelector("#retry-what-if").click();
    await vi.waitFor(() => expect(document.querySelector("#what-if-status").textContent).toBe("Unavailable"));
    expect(document.querySelector("#what-if-record").textContent).toContain(workflowId);
    fail = false;
    document.querySelector("#retry-what-if").click();
    await vi.waitFor(() => expect(document.querySelector("#what-if-decision-form").hidden).toBe(false));
    expect(fetchMock.mock.calls.filter(([url]) => url === "/budget-api/what-if/workflows")).toHaveLength(1);
    expect(fetchMock.mock.calls.filter(([url]) => url === workflowPath)).toHaveLength(2);
  });

  test("discards stale preview and handle when a decision returns snapshot_stale", async () => {
    const fetchMock = await startPlanner({ [`POST ${workflowPath}/decision`]: () => response({ error: { code: "snapshot_stale", message: "Snapshot changed; request a fresh preview." } }, 409) });
    chooseDecision("approve"); submitDecision();
    await vi.waitFor(() => expect(document.querySelector("#what-if-status").dataset.state).toBe("stale"));
    expect(document.querySelector("#what-if-preview").hidden).toBe(true);
    expect(document.querySelector("#what-if-workflow").hidden).toBe(true);
    expect(document.querySelector("#start-what-if").disabled).toBe(true);
    expect(document.querySelector("#preview-what-if").disabled).toBe(false);
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith("/decision"))).toHaveLength(1);
  });

  test("renders hostile shared agent, review and evidence text only as text", async () => {
    const hostile = "<img src=x onerror=alert(1)><script>alert(2)</script>";
    const envelope = workflowFixture();
    envelope.workflow.plan.objective = hostile;
    envelope.workflow.plan.steps[0].description = hostile;
    envelope.workflow.work.summary = hostile;
    envelope.workflow.work.items[0].subject = hostile;
    envelope.workflow.work.items[0].detail = hostile;
    envelope.workflow.review.findings = [{ severity: "info", item_id: "i1", message: hostile }];
    envelope.workflow.review.recommendations = [hostile];
    envelope.workflow.evidence[0].text = hostile;
    await startPlanner({ "POST /budget-api/what-if/workflows": () => response({ ...envelope, token: workflowToken }, 202) });
    expect(document.querySelector("#what-if-record").textContent).toContain(hostile);
    expect(document.querySelector("#what-if img, #what-if script, #what-if svg")).toBeNull();
    chooseDecision("correct");
    expect(document.querySelector("#what-if-corrected-summary").value).toBe(hostile);
  });

  test.each([false, undefined, "true", null])("allows preview but makes zero agent calls with multiAgentEnabled=%s", async (multiAgentEnabled) => {
    const fetchMock = await start(defaultFetch({ "GET /budget-api/capabilities": () => response({ mcpEnabled: true, ragEnabled: true, multiAgentEnabled }), "POST /budget-api/what-if/preview": () => response(previewFixture()) }));
    submitWhatIf();
    await vi.waitFor(() => expect(document.querySelector("#what-if-preview").hidden).toBe(false));
    document.querySelector("#start-what-if").click(); submitDecision();
    expect(fetchMock.mock.calls.some(([url]) => url.includes("/what-if/workflows"))).toBe(false);
    expect(document.querySelector("#add-expense").disabled).toBe(false);
  });

  test("previews every aggregate dashboard category without changing saved budgets", async () => {
    const preview = previewFixture(dashboard, [8000, 10000]);
    const fetchMock = await start(defaultFetch({ "POST /budget-api/what-if/preview": () => response(preview) }));
    expect([...document.querySelectorAll("#what-if-inputs input")].map((input) => input.value)).toEqual(["100.00", "50.00"]);
    document.querySelector("#what-if-limit-food").value = "80.00";
    document.querySelector("#what-if-limit-shopping").value = "100";
    submitWhatIf();
    await vi.waitFor(() => expect(document.querySelector("#what-if-preview").hidden).toBe(false));
    expect(JSON.parse(fetchMock.mock.calls.find(([url]) => url.endsWith("/what-if/preview"))[1].body)).toEqual({ journeyLabel: "Journey", limits: [{ category: "food", limitAmountMinor: 8000 }, { category: "shopping", limitAmountMinor: 10000 }] });
    expect(document.querySelector("#what-if-preview").textContent).toContain("30.00");
    expect(document.querySelector("#what-if-preview").textContent).toContain("overspent");
    expect(document.querySelector("#total-planned").textContent).toContain("150.00");
    expect(fetchMock.mock.calls.filter(([, options]) => options.method && options.method !== "GET")).toHaveLength(1);
    expect(document.querySelector("#start-what-if").disabled).toBe(true);
  });

  test("prefills exact cents at the safe-integer boundary and uses dashboard aggregates", async () => {
    const large = { ...dashboard, plannedAmountMinor: Number.MAX_SAFE_INTEGER, actualAmountMinor: 1, remainingAmountMinor: Number.MAX_SAFE_INTEGER - 1, percentageUsed: 0, categories: [{ category: "food", plannedAmountMinor: Number.MAX_SAFE_INTEGER, actualAmountMinor: 1, remainingAmountMinor: Number.MAX_SAFE_INTEGER - 1, percentageUsed: 0, status: "within_budget" }] };
    const fetchMock = await start(defaultFetch({ "GET /budget-api/dashboard?journeyLabel=Journey": () => response(large), "POST /budget-api/what-if/preview": () => response(previewFixture(large)) }));
    expect(document.querySelectorAll("#what-if-inputs input")).toHaveLength(1);
    expect(document.querySelector("#what-if-limit-food").value).toBe("90071992547409.91");
    submitWhatIf();
    await vi.waitFor(() => expect(document.querySelector("#what-if-preview").hidden).toBe(false));
    expect(JSON.parse(fetchMock.mock.calls.find(([url]) => url.endsWith("/what-if/preview"))[1].body).limits[0].limitAmountMinor).toBe(Number.MAX_SAFE_INTEGER);
    expect(document.querySelector("#what-if-preview").textContent).toContain("90,071,992,547,409.91");
  });

  test.each(["0", "-1", "1.001", "1e2", "NaN", "", "90071992547409.92", "1,000.00"])("rejects invalid proposed money %s without HTTP", async (amount) => {
    const fetchMock = await start();
    document.querySelector("#what-if-limit-food").value = amount;
    submitWhatIf();
    expect(document.querySelector("#what-if-status").dataset.state).toBe("error");
    expect(fetchMock.mock.calls.some(([url]) => url.includes("/what-if/"))).toBe(false);
  });

  test("rejects a total over the safe boundary and accepts a single cent", async () => {
    const fetchMock = await start(defaultFetch({ "POST /budget-api/what-if/preview": () => response(previewFixture(dashboard, [1, 5000])) }));
    document.querySelector("#what-if-limit-food").value = "90071992547409.91";
    submitWhatIf();
    expect(document.querySelector("#what-if-status").textContent).toContain("total proposed limit exceeds");
    expect(fetchMock.mock.calls.some(([url]) => url.includes("/what-if/"))).toBe(false);
    document.querySelector("#what-if-limit-food").value = "0.01";
    submitWhatIf();
    await vi.waitFor(() => expect(document.querySelector("#what-if-preview").hidden).toBe(false));
  });

  test.each(["unsafe", "remaining", "categorySum", "status", "actual", "category", "hash", "journey", "currency", "limit", "duplicate"])("fails closed on invalid preview %s", async (fault) => {
    const preview = previewFixture();
    if (fault === "unsafe") preview.proposed.plannedAmountMinor = Number.MAX_SAFE_INTEGER + 1;
    if (fault === "remaining") preview.proposed.categories[0].remainingAmountMinor++;
    if (fault === "categorySum") preview.proposed.plannedAmountMinor++;
    if (fault === "status") preview.proposed.categories[0].status = "within_budget";
    if (fault === "actual") { preview.proposed.actualAmountMinor++; preview.proposed.remainingAmountMinor--; preview.proposed.categories[0].actualAmountMinor++; preview.proposed.categories[0].remainingAmountMinor--; }
    if (fault === "category") preview.proposed.categories[0].category = "transport";
    if (fault === "hash") preview.snapshotHash = "bad";
    if (fault === "journey") preview.original.journeyLabel = "Elsewhere";
    if (fault === "currency") preview.proposed.baseCurrency = "USD";
    if (fault === "limit") { preview.proposed.plannedAmountMinor++; preview.proposed.remainingAmountMinor++; preview.proposed.categories[0].plannedAmountMinor++; preview.proposed.categories[0].remainingAmountMinor++; }
    if (fault === "duplicate") preview.proposed.categories[1].category = "food";
    await start(defaultFetch({ "POST /budget-api/what-if/preview": () => response(preview) }));
    submitWhatIf();
    await vi.waitFor(() => expect(document.querySelector("#what-if-status").dataset.state).toBe("error"));
    expect(document.querySelector("#what-if-preview").hidden).toBe(true);
    expect(document.querySelector("#start-what-if").disabled).toBe(true);
  });

  test("keeps What-If agent review disabled when the capability is absent", async () => {
    const fetchMock = await start();
    expect(document.querySelector("#what-if").textContent).toContain("Preview only");
    expect(document.querySelector("#start-what-if").disabled).toBe(true);
    document.querySelector("#start-what-if").click();
    expect(fetchMock.mock.calls.some(([url]) => url.includes("/what-if/"))).toBe(false);
    expect(document.querySelector("#add-budget").disabled).toBe(false);
    expect(document.querySelector("#add-expense").disabled).toBe(false);
  });

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
      expect(sharedNginx).toContain("location /budget-api/");
      expect(sharedNginx).toContain("rewrite ^/budget-api/(.*)$ /api/$1 break;");
      const fetchMock = await start(defaultFetch({ "POST /budget-api/budget-check": () => response(payload) }));
      document.querySelector("#run-budget-check").click();

      await vi.waitFor(() => expect(document.querySelector("#budget-check-result").hidden).toBe(false));
      const call = fetchMock.mock.calls.find(([url, options]) => url === "/budget-api/budget-check" && options.method === "POST");
      expect(fetchMock.mock.calls.some(([url]) => url === "/budget-api/api/budget-check")).toBe(false);
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
      expect(sharedNginx).toContain("location /budget-api/");
      expect(sharedNginx).toContain("rewrite ^/budget-api/(.*)$ /api/$1 break;");
      const fetchMock = await start(defaultFetch({ "POST /budget-api/budget-guidance": () => response(guidance) }));
      document.querySelector("#guidance-question").value = "How should I plan category budgets?";
      document.querySelector("#guidance-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      document.querySelector("#guidance-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

      await vi.waitFor(() => expect(document.querySelector("#guidance-result").hidden).toBe(false));
      const call = fetchMock.mock.calls.find(([url, options]) => url === "/budget-api/budget-guidance" && options.method === "POST");
      expect(JSON.parse(call[1].body)).toEqual({ question: "How should I plan category budgets?" });
      expect(fetchMock.mock.calls.filter(([url]) => url === "/budget-api/budget-guidance")).toHaveLength(1);
      expect(fetchMock.mock.calls.some(([url]) => url === "/budget-api/api/budget-guidance")).toBe(false);
      expect(document.querySelector("#guidance-confidence").textContent).toBe("High retrieval confidence");
      expect(document.querySelector("#guidance-citations summary").textContent).toBe("Category budgets and spending statuses");
      expect(document.querySelector("#guidance-citations").textContent).toContain("category-budgets#1");
      expect(document.querySelector("#guidance-description").textContent).toContain("does not use this journey's saved totals");
      expect(document.querySelector("#guidance-status").dataset.state).toBe("success");
    });

    test("reports fixed insufficient-context abstention distinctly", async () => {
      const guidance = { answer: "Not enough information in the knowledge base to answer this.", citations: [], confidence: "insufficient" };
      await start(defaultFetch({ "POST /budget-api/budget-guidance": () => response(guidance) }));
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
        "POST /budget-api/budget-check": () => response({ error: { message: "MCP unavailable." } }, 503),
        "POST /budget-api/budget-guidance": () => response({ error: { message: "RAG unavailable." } }, 502),
      }));
      const question = document.querySelector("#guidance-question");
      question.value = "x".repeat(1001);
      document.querySelector("#guidance-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      expect(document.querySelector("#guidance-status").textContent).toContain("1 to 1000 characters");
      expect(fetchMock.mock.calls.some(([url]) => url === "/budget-api/budget-guidance")).toBe(false);

      question.value = "x".repeat(1000);
      document.querySelector("#guidance-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      await vi.waitFor(() => expect(document.querySelector("#guidance-status").textContent).toBe("RAG unavailable."));
      expect(JSON.parse(fetchMock.mock.calls.find(([url]) => url === "/budget-api/budget-guidance")[1].body).question).toHaveLength(1000);
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
      await start(defaultFetch({ "POST /budget-api/budget-guidance": () => response(guidance) }));
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
        "POST /budget-api/budget-check": () => checkPromise,
      }));
      const button = document.querySelector("#run-budget-check");
      button.click();
      button.click();
      expect(button.disabled).toBe(true);
      expect(fetchMock.mock.calls.filter(([url]) => url === "/budget-api/budget-check")).toHaveLength(1);

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
      const fetchMock = await start(defaultFetch({ "POST /budget-api/budget-check": () => response(summary) }));
      document.querySelector("#run-budget-check").click();
      await vi.waitFor(() => expect(document.querySelector("#budget-check-result").hidden).toBe(false));

      let resolveGuidance;
      const pendingGuidance = new Promise((resolve) => { resolveGuidance = resolve; });
      fetchMock.mockImplementation((url, options = {}) => url === "/budget-api/budget-guidance" ? pendingGuidance : defaultFetch()(url, options));
      document.querySelector("#guidance-question").value = "How do I plan?";
      document.querySelector("#guidance-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      expect(document.querySelector("#cancel-guidance").hidden).toBe(false);
      document.querySelector("#cancel-guidance").focus();
      document.querySelector("#cancel-guidance").click();
      expect(document.activeElement).toBe(document.querySelector("#guidance-question"));
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
        "POST /budget-api/budget-guidance": () => pendingGuidance,
        "POST /budget-api/budget-check": () => pendingCheck,
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
      expect(fetchMock.mock.calls.filter(([url]) => url === "/budget-api/budget-check")).toHaveLength(1);
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