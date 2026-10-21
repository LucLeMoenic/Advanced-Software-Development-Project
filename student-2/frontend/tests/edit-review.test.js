// @vitest-environment jsdom
import { createApp, h, nextTick, reactive } from "vue";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import EditReview from "../EditReview.vue";

let app;
let props;
let accepted;
const id = "wf-20261020T080000Z-0123abcd";
function ready() {
  return { id, status: "awaiting_human_review", stale: false,
    plan: { objective: "Review saved days", steps: [{ id: "s1", description: "Check coverage" }], success_criteria: ["Cite evidence"] },
    work: { summary: "Flexible days", items: [{ id: "i1", subject: "Trip overview", detail: "Day 2 is empty.", evidence_ids: ["trip-12"] }] },
    review: { verdict: "pass", degraded: false, findings: [], recommendations: [] },
    evidence: [{ id: "trip-12", title: "Trip overview", text: "Saved days only." }], history: [{ stage: "planner", ok: true }],
    human_decision: null, final_output: null };
}
function response(body, status = 200) {
  return Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) });
}
function button(text) {
  return [...document.querySelectorAll("button")].find((element) => element.textContent === text);
}
function input(selector, value) {
  const field = document.querySelector(selector);
  field.value = value;
  field.dispatchEvent(new Event("input", { bubbles: true }));
}
async function mount(fetch, enabled = true) {
  vi.stubGlobal("fetch", fetch);
  accepted = vi.fn();
  props = reactive({ trip: { id: 12, stops: [] }, enabled, active: true, workflowId: id, expired: false, onAccepted: accepted });
  app = createApp({ render: () => h(EditReview, props) });
  app.mount("#app");
  await nextTick();
}
async function start(fetch = vi.fn(() => response(ready()))) {
  await mount(fetch);
  await vi.waitFor(() => expect(document.body.textContent).toContain("Worker assessment"));
  return fetch;
}
beforeEach(() => { document.body.innerHTML = '<div id="app"></div>'; });
afterEach(() => { app?.unmount(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

test("disabled mode never calls a service", async () => {
  const fetch = vi.fn();
  await mount(fetch, false);
  expect(document.querySelector("#check-plan-status").disabled).toBe(true);
  document.querySelector("#check-plan-status").click();
  expect(fetch).not.toHaveBeenCalled();
});

test.each(["approve", "partial", "reject", "correct"])("records explicit %s without itinerary writes", async (decision) => {
  const fetch = vi.fn((url, options) => {
    if (url.endsWith("/decision")) {
      const body = JSON.parse(options.body);
      return response({ ...ready(), status: { approve: "approved", partial: "partially_accepted", reject: "rejected", correct: "corrected" }[body.decision],
        human_decision: body, final_output: body.decision === "reject" ? null : body.corrected_output || ready().work });
    }
    return response(options.method === "POST" ? { id, status: "queued" } : ready());
  });
  await start(fetch);
  if (decision === "partial") document.querySelector('input[type="checkbox"]').click();
  if (decision === "reject") input("#plan-notes", "Unsupported claim");
  if (decision === "correct") input("#corrected-summary", "Human correction");
  await nextTick();
  button({ approve: "Approve assessment", partial: "Accept selected", reject: "Reject assessment", correct: "Save corrected assessment" }[decision]).click();
  await vi.waitFor(() => expect(document.body.textContent).toContain(`Recorded decision: ${decision}`));
  const writes = fetch.mock.calls.filter(([, options]) => options.method === "POST");
  expect(writes).toHaveLength(1);
  expect(JSON.parse(writes[0][1].body).decision).toBe(decision);
  expect(accepted).toHaveBeenLastCalledWith(decision !== "reject");
  expect(document.body.textContent).toContain("do not change your saved itinerary");
});

test("reject and partial require human input", async () => {
  const fetch = await start();
  button("Reject assessment").click();
  await nextTick();
  expect(document.body.textContent).toContain("Explain why");
  button("Accept selected").click();
  await nextTick();
  expect(document.body.textContent).toContain("Select at least one");
  expect(fetch).toHaveBeenCalledTimes(1);
});

test("stale review cannot be accepted and degraded review stays visible", async () => {
  await start(vi.fn((url, options) => response(options.method === "POST" ? { id, status: "queued" } : {
    ...ready(), stale: true, review: { ...ready().review, degraded: true, verdict: "concerns" },
  })));
  expect(button("Approve assessment").disabled).toBe(true);
  expect(accepted).toHaveBeenLastCalledWith(false);
  expect(document.body.textContent).toContain("automatic checks only");
  expect(document.body.textContent).toContain("historical");
});

test("trip switch ignores a late response and aborts its request", async () => {
  let resolve;
  const fetch = vi.fn(() => new Promise((done) => { resolve = done; }));
  await mount(fetch);
  document.querySelector("#check-plan-status").click();
  expect(fetch).toHaveBeenCalledTimes(1);
  props.enabled = false;
  props.trip = { id: 99, stops: [] };
  await nextTick();
  expect(fetch.mock.calls[0][1].signal.aborted).toBe(true);
  resolve(await response({ id, status: "queued" }));
  await nextTick();
  expect(document.body.textContent).not.toContain("Worker assessment");
  expect(fetch).toHaveBeenCalledTimes(1);
});

test("uncertain decisions are never retried and require status refresh", async () => {
  const fetch = vi.fn((url, options) => url.endsWith("/decision")
    ? Promise.reject(new Error("Connection lost"))
    : response(options.method === "POST" ? { id, status: "queued" } : ready()));
  await start(fetch);
  button("Approve assessment").click();
  await vi.waitFor(() => expect(document.body.textContent).toContain("outcome may be uncertain"));
  expect(button("Approve assessment")).toBeUndefined();
  expect(accepted).toHaveBeenLastCalledWith(false);
  expect(document.querySelector("#workflow-id").textContent).toBe(id);
  expect(fetch.mock.calls.filter(([url]) => url.endsWith("/decision"))).toHaveLength(1);
});

test("can reload the bound workflow after remount", async () => {
  const fetch = vi.fn(() => response({ ...ready(), status: "rejected", human_decision: { decision: "reject", notes: "No changes" } }));
  await mount(fetch);
  await vi.waitFor(() => expect(document.body.textContent).toContain("Recorded decision: reject"));
  expect(fetch.mock.calls[0][1].method).toBe("GET");
});

test("expired previews cannot receive a new decision", async () => {
  const fetch = await start();
  props.expired = true;
  await nextTick();
  expect(button("Approve assessment").disabled).toBe(true);
  expect(document.body.textContent).toContain("preview expired");
  button("Approve assessment").click();
  expect(fetch).toHaveBeenCalledTimes(1);
});

test("a response for another workflow cannot enable confirmation", async () => {
  await mount(vi.fn(() => response({ ...ready(), id: "different", status: "approved" })));
  await vi.waitFor(() => expect(document.body.textContent).toContain("different workflow"));
  expect(accepted).toHaveBeenLastCalledWith(false);
  expect(document.body.textContent).not.toContain("Worker assessment");
});

test("changing the saved trip revokes accepted assessment", async () => {
  await start(vi.fn(() => response({ ...ready(), status: "approved", human_decision: { decision: "approve" } })));
  expect(accepted).toHaveBeenLastCalledWith(true);
  props.trip.stops.push({ id: 1, day: 2 });
  await nextTick();
  expect(accepted).toHaveBeenLastCalledWith(false);
  expect(document.body.textContent).toContain("historical");
});
