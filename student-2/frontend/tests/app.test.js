// @vitest-environment jsdom

import { createApp, nextTick } from "vue";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import App from "../App.vue";

let application;

function setValue(selector, value) {
  const input = document.querySelector(selector);
  input.value = value;
  input.dispatchEvent(new Event("input", { bubbles: true }));
}

function jsonResponse(value, status = 200) {
  const body = JSON.stringify(value);
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(JSON.parse(body)),
  });
}

async function loadApplication() {
  application = createApp(App);
  application.mount("#app");
  await nextTick();
}

function reviewResponse() {
  return { tripId: 12, clarification: "", tool: "itinerary.preview_edit", preview: {
    tripId: 12, token: "signed-preview", expiresIn: 600,
    changes: [{ id: 1, activity: "Park walk", notes: "Saved plan", fromDay: 1, toDay: 2, fromOrder: 0, toOrder: 0 }],
  } };
}

function adviceResponse(weather) {
  return { tripId: 12, answer: "Keep timing flexible. [planning#1]", confidence: "high",
    citations: [{ source: "Planning guidance", chunk_id: "planning#1", snippet: "Keep timing flexible." }], weather };
}

beforeEach(() => {
  document.body.innerHTML = '<div id="app"></div>';
  vi.restoreAllMocks();
  HTMLDialogElement.prototype.showModal = vi.fn(function () { this.open = true; });
  HTMLDialogElement.prototype.close = vi.fn(function () { this.open = false; });
});

afterEach(() => {
  application?.unmount();
  vi.unstubAllGlobals();
});

describe("Itinerary Planner", () => {
  test("minimises the assistant without losing its selected tab, draft or late result", async () => {
    let resolveAdvice;
    const fetchMock = vi.fn((url) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: true, mcpEnabled: true, ragEnabled: true });
      if (url.endsWith("/itinerary-advice")) return new Promise((resolve) => { resolveAdvice = resolve; });
      return jsonResponse([]);
    });
    vi.stubGlobal("fetch", fetchMock);
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("#advice-submit").disabled).toBe(false));
    document.querySelector("#advice-tab").click();
    setValue("#advice-question", "Budget?");
    document.querySelector("#advice-submit").click();
    const toggle = document.querySelector("#toggle-assistant");
    toggle.focus();
    toggle.click();
    await nextTick();
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(toggle.getAttribute("aria-label")).toBe("Expand trip assistant");
    expect(document.querySelector(".planner-grid").classList.contains("assistant-collapsed")).toBe(true);
    expect(document.querySelector("#assistant-tabs").hidden).toBe(true);
    expect(document.querySelector("#assistant-content").hidden).toBe(true);
    resolveAdvice(await jsonResponse(adviceResponse()));
    await vi.waitFor(() => expect(document.querySelector("#advice-result").hidden).toBe(false));
    expect(document.activeElement).toBe(toggle);
    toggle.click();
    await nextTick();
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(document.querySelector("#assistant-content").hidden).toBe(false);
    expect(document.querySelector("#advice-tab").getAttribute("aria-selected")).toBe("true");
    expect(document.querySelector("#advice-question").value).toBe("Budget?");
    expect(document.querySelector("#advice-answer").textContent).toContain("Keep timing flexible");
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith("/itinerary-advice"))).toHaveLength(1);
  });

  test("keeps the assistant outside stops with keyboard tabs, selected trip and dated days", async () => {
    const trip = { id: 12, user: "Alex", destination: "Tokyo", startDate: "2026-12-31", endDate: "2027-01-01", budget: 900,
      stops: [{ id: 1, day: 2, activity: "Walk", notes: "Morning" }] };
    vi.stubGlobal("fetch", vi.fn((url) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: true, mcpEnabled: true, ragEnabled: true });
      return jsonResponse(url.endsWith("/trips/12") ? trip : [trip]);
    }));
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("[data-trip-id='12']")).not.toBeNull());
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#trip-title").textContent).toContain("Tokyo"));
    expect(document.querySelector("[data-trip-id='12']").getAttribute("aria-current")).toBe("true");
    expect(document.querySelector("#day-2 time").getAttribute("datetime")).toBe("2027-01-01");
    expect(document.querySelector("#day-2 time").textContent).toBe("1 Jan 2027");
    expect(document.querySelector(".itinerary-panel #edit-panel")).toBeNull();
    expect(document.querySelector(".itinerary-panel #advice-panel")).toBeNull();
    expect(document.querySelector(".assistant-panel #days")).toBeNull();
    expect(document.querySelector("#edit-panel").hidden).toBe(false);
    document.querySelector("#edit-tab").dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    await nextTick();
    expect(document.querySelector("#advice-tab").getAttribute("aria-selected")).toBe("true");
    expect(document.querySelector("#edit-tab").tabIndex).toBe(-1);
    expect(document.activeElement.id).toBe("advice-tab");
    expect(document.querySelector("#edit-panel").hidden).toBe(true);
    expect(document.querySelector("#advice-panel").hidden).toBe(false);
    document.querySelector("#advice-tab").dispatchEvent(new KeyboardEvent("keydown", { key: "Home", bubbles: true }));
    await nextTick();
    expect(document.activeElement.id).toBe("edit-tab");
    expect(document.querySelector("#edit-panel").hidden).toBe(false);
  });

  test("cancels late advice safely, retries and renders citation markers as plain text", async () => {
    const requests = [];
    vi.stubGlobal("fetch", vi.fn((url, options) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: true, mcpEnabled: true, ragEnabled: true });
      if (url.endsWith("/itinerary-advice")) return new Promise((resolve) => requests.push({ resolve, signal: options.signal }));
      return jsonResponse([]);
    }));
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("#advice-submit").disabled).toBe(false));
    document.querySelector("#advice-tab").click();
    setValue("#advice-question", "Budget?");
    document.querySelector("#advice-submit").click();
    await nextTick();
    expect(document.querySelector("#advice-submit").textContent).toContain("Getting advice...");
    expect(document.querySelector("#advice-question").disabled).toBe(true);
    document.querySelector("#cancel-advice").click();
    await nextTick();
    expect(requests[0].signal.aborted).toBe(true);
    expect(document.querySelector("#advice-status").textContent).toBe("Advice request cancelled.");
    expect(document.querySelector("#advice-submit").disabled).toBe(false);
    document.querySelector("#advice-submit").click();
    requests[0].resolve(await jsonResponse(adviceResponse()));
    await nextTick();
    expect(document.querySelector("#advice-result").hidden).toBe(true);
    expect(document.querySelector("#advice-submit").disabled).toBe(true);
    const answer = adviceResponse();
    answer.answer = '<img src=x onerror=alert(1)> [planning#1] [unknown#2]';
    answer.citations[0].snippet = '<script>alert(1)</script>' + "Keep plans flexible. ".repeat(30) + "Missing forecasts do not mean dry weather.";
    requests[1].resolve(await jsonResponse(answer));
    await vi.waitFor(() => expect(document.querySelector("#advice-result").hidden).toBe(false));
    expect(document.querySelector("#advice-answer img")).toBeNull();
    expect(document.querySelector("#advice-citations script")).toBeNull();
    expect(document.querySelector("#advice-answer").textContent).toContain("[unknown#2]");
    expect(document.querySelector("#advice-answer").textContent).toContain("[1]");
    expect(document.querySelector("#advice-answer").textContent).not.toContain("[planning#1]");
    expect(document.querySelectorAll("#advice-answer a, #advice-answer button")).toHaveLength(0);
    expect(document.querySelector("#advice-source-0").open).toBe(false);
    document.querySelector("#advice-source-0 summary").click();
    expect(document.querySelector("#advice-source-0").open).toBe(true);
    expect(document.querySelector("#advice-source-0 p").textContent).toBe(answer.citations[0].snippet);
    expect(document.querySelector("#advice-confidence").textContent).toBe("Source relevance: high");
    expect(document.querySelector("#cancel-advice")).toBeNull();
  });

  test.each(["add_stop", "remove_stop", "update_stop", "shift_dates"])("previews and confirms %s through the assistant", async (kind) => {
    const originalStop = { id: 1, day: 1, sortOrder: 4, activity: "Museum", notes: "Bring booking" };
    const trip = { id: 12, user: "Alex", destination: "Tokyo", startDate: "2026-10-10", endDate: "2026-10-12", budget: 900, stops: [originalStop] };
    const proposedStop = { ...originalStop, id: kind === "add_stop" ? 0 : 1, activity: "<img src=x onerror=alert(1)>", notes: "Bring tickets", sortOrder: kind === "add_stop" ? 5 : 4 };
    const change = kind === "shift_dates"
      ? { kind, fromStartDate: trip.startDate, fromEndDate: trip.endDate, toStartDate: "2027-06-01", toEndDate: "2027-06-03" }
      : { kind, id: proposedStop.id, before: kind === "add_stop" ? null : originalStop, after: kind === "remove_stop" ? null : proposedStop };
    const result = reviewResponse();
    result.preview.changes = [change];
    let saved = false;
    const updated = kind === "shift_dates" ? { ...trip, startDate: change.toStartDate, endDate: change.toEndDate }
      : { ...trip, stops: kind === "remove_stop" ? [] : kind === "add_stop" ? [originalStop, { ...proposedStop, id: 2 }] : [proposedStop] };
    const fetchMock = vi.fn((url) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: true, mcpEnabled: true, ragEnabled: false });
      if (url.endsWith("/edit-preview")) return jsonResponse(result);
      if (url.endsWith("/edit-confirm")) { saved = true; return jsonResponse({ tripId: 12, applied: true, changes: [change] }); }
      return jsonResponse(url.endsWith("/trips/12") ? (saved ? updated : trip) : [trip]);
    });
    vi.stubGlobal("fetch", fetchMock);
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("[data-trip-id='12']")).not.toBeNull());
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#mcp-summary").disabled).toBe(false));
    setValue("#review-question", "Requested assistant change");
    document.querySelector("#mcp-summary").click();
    await vi.waitFor(() => expect(document.querySelector("#confirm-edit")).not.toBeNull());
    const text = document.querySelector("#mcp-result").textContent;
    expect(text).toContain({ add_stop: "Add activity", remove_stop: "Remove activity", update_stop: "Update activity", shift_dates: "Shift trip dates" }[kind]);
    expect(text).toContain("Current");
    expect(text).toContain("Proposed");
    expect(document.querySelector("#mcp-result img")).toBeNull();
    if (kind === "shift_dates") {
      expect(text).toContain(trip.startDate);
      expect(text).toContain(change.toStartDate);
    } else {
      expect(text).toContain(kind === "remove_stop" ? "Removed from itinerary" : proposedStop.activity);
      expect(text).toContain(kind === "add_stop" ? "Not scheduled" : originalStop.notes);
    }
    expect(saved).toBe(false);
    document.querySelector("#cancel-edit").click();
    await nextTick();
    expect(document.querySelector("#confirm-edit")).toBeNull();
    expect(saved).toBe(false);
    document.querySelector("#mcp-summary").click();
    await vi.waitFor(() => expect(document.querySelector("#confirm-edit")).not.toBeNull());
    document.querySelector("#confirm-edit").click();
    await vi.waitFor(() => expect(document.querySelector("#mcp-status").textContent).toContain({ add_stop: "Added", remove_stop: "Removed", update_stop: "Updated", shift_dates: "Trip dates shifted" }[kind]));
    expect(document.querySelector("#status").textContent).toBe(document.querySelector("#mcp-status").textContent);
    if (kind === "shift_dates") expect(document.querySelector("#trip-dates").classList.contains("saved-highlight")).toBe(true);
    if (kind === "add_stop" || kind === "update_stop") expect(document.querySelector(`[data-stop-id='${kind === "add_stop" ? 2 : 1}']`).classList.contains("saved-highlight")).toBe(true);
    const saves = fetchMock.mock.calls.filter(([url]) => url.endsWith("/edit-confirm"));
    expect(saves).toHaveLength(1);
    expect(JSON.parse(saves[0][1].body)).toEqual({ token: "signed-preview" });
    expect(document.querySelector("#metric-stops").textContent).toBe(String(updated.stops.length));
    if (kind === "shift_dates") expect(document.querySelector("[data-trip-id='12']").textContent).toContain(change.toStartDate);
  });

  test("shows actual same-day positions and previews undo without saving", async () => {
    const trip = { id: 12, user: "Alex", destination: "Tokyo", startDate: "2026-10-10", endDate: "2026-10-12", budget: 900,
      stops: [
        { id: 1, day: 1, sortOrder: 0, activity: "Museum", notes: "" },
        { id: 2, day: 1, sortOrder: 0, activity: "Lunch", notes: "" },
        { id: 3, day: 1, sortOrder: 8, activity: "Gallery", notes: "" },
      ] };
    const result = reviewResponse();
    result.preview.changes = trip.stops.map((stop) => ({ id: stop.id, activity: stop.activity, notes: "",
      fromDay: 1, toDay: 1, fromOrder: stop.sortOrder, toOrder: stop.id === 3 ? 0 : stop.id }));
    const fetchMock = vi.fn((url) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: true, mcpEnabled: true, ragEnabled: false });
      if (url.endsWith("/edit-operation-preview")) return jsonResponse(result);
      return jsonResponse(url.endsWith("/trips/12") ? trip : [trip]);
    });
    vi.stubGlobal("fetch", fetchMock);
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("[data-trip-id='12']")).not.toBeNull());
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#mcp-summary").disabled).toBe(false));
    expect(document.querySelector(".reorder-panel")).toBeNull();
    document.querySelector("#undo-edit").click();
    await vi.waitFor(() => expect(document.querySelectorAll(".review-finding")).toHaveLength(3));
    const gallery = [...document.querySelectorAll(".review-finding")].find((element) => element.textContent.includes("Gallery"));
    expect(gallery.textContent).toContain("Stop 3 (current)");
    expect(gallery.textContent).toContain("Stop 1 (proposed)");
    expect(document.querySelector(".review-finding").textContent).toContain("Stop 2 (proposed)");
    const requests = fetchMock.mock.calls.filter(([url]) => url.endsWith("/edit-operation-preview"));
    expect(requests).toHaveLength(1);
    expect(JSON.parse(requests[0][1].body)).toEqual({ operation: { action: "undo", sourceDay: 1, targetDay: 1, stopId: 0, targetStopId: 0 } });
    expect(fetchMock.mock.calls.some(([url]) => url.endsWith("/edit-confirm"))).toBe(false);
    await vi.waitFor(() => expect(document.querySelector("#confirm-edit")).not.toBeNull());
    document.querySelector("#cancel-edit").click();
    await nextTick();
    expect(document.querySelector("#confirm-edit")).toBeNull();
  });

  test("boots a single Vue application without legacy markup or handlers", async () => {
    const html = readFileSync(resolve(process.cwd(), "index.html"), "utf8");
    expect(html.match(/<!doctype html>/gi)).toHaveLength(1);
    expect(html).not.toContain('id="trip-form"');
    vi.stubGlobal("fetch", vi.fn((url) => jsonResponse(url.endsWith("/capabilities")
      ? { aiEnabled: false, mcpEnabled: false, ragEnabled: false } : [])));
    await import("../app.js");
    application = document.querySelector("#app").__vue_app__;
    await vi.waitFor(() => expect(document.querySelector("#trip-count").textContent).toBe("0 saved trips"));
    window.dispatchEvent(new Event("load"));
    await nextTick();
    expect(document.querySelectorAll("#trip-form")).toHaveLength(1);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  test("ignores a pending edit preview after a successful 204 stop deletion", async () => {
    const trip = { id: 12, user: "Alex", destination: "Tokyo", startDate: "2026-10-10", endDate: "2026-10-12", budget: 900,
      stops: [{ id: 1, tripId: 12, day: 1, activity: "Walk", notes: "", sortOrder: 0 }] };
    let resolveSummary;
    let deleted = false;
    vi.stubGlobal("fetch", vi.fn((url, options) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: true, mcpEnabled: true, ragEnabled: false });
      if (url.endsWith("/edit-preview")) return new Promise((resolve) => { resolveSummary = resolve; });
      if (options?.method === "DELETE") { deleted = true; return jsonResponse(null, 204); }
      if (url.endsWith("/trips/12")) return deleted ? new Promise(() => {}) : jsonResponse(trip);
      return jsonResponse([trip]);
    }));
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("[data-trip-id='12']")).not.toBeNull());
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#mcp-summary").disabled).toBe(false));
    document.querySelector("#mcp-summary").click();
    document.querySelector("[data-remove-stop='1']").click();
    document.querySelector("#feedback-confirm").click();
    await vi.waitFor(() => expect(deleted).toBe(true));
    resolveSummary(await jsonResponse(reviewResponse()));
    await vi.waitFor(() => expect(document.querySelector("#mcp-summary").disabled).toBe(false));
    expect(document.querySelector("#mcp-result").hidden).toBe(true);
  });

  test("locks the pending advice question and restores controls after an error", async () => {
    let resolveAdvice;
    const fetchMock = vi.fn((url) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: false, mcpEnabled: false, ragEnabled: true });
      if (url.endsWith("/itinerary-advice")) return new Promise((resolve) => { resolveAdvice = resolve; });
      return jsonResponse([]);
    });
    vi.stubGlobal("fetch", fetchMock);
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("#advice-submit").disabled).toBe(false));
    setValue("#advice-question", "Budget?");
    document.querySelector("#advice-form").dispatchEvent(new Event("submit", { cancelable: true }));
    document.querySelector("#advice-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await nextTick();
    expect(document.querySelector("#advice-question").disabled).toBe(true);
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith("/itinerary-advice"))).toHaveLength(1);
    resolveAdvice(await jsonResponse({ error: { message: "The local model is unavailable." } }, 503));
    await vi.waitFor(() => expect(document.querySelector("#advice-question").disabled).toBe(false));
    expect(document.querySelector("#advice-status").textContent).toContain("unavailable");
    expect(document.querySelector("#advice-result").hidden).toBe(true);
    expect(document.querySelector("#mcp-summary").disabled).toBe(true);
  });

  test("shows MCP edit preview and safely renders cited RAG answers and insufficient context", async () => {
    const trip = { id: 12, user: "Alex", destination: "Tokyo", startDate: "2026-10-10", endDate: "2026-10-12", budget: 900, stops: [] };
    let insufficient = false;
    vi.stubGlobal("fetch", vi.fn((url) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: true, mcpEnabled: true, ragEnabled: true });
      if (url.endsWith("/edit-preview")) return jsonResponse(reviewResponse());
      if (url.endsWith("/itinerary-advice")) return jsonResponse(insufficient
        ? { answer: "Not enough information in the knowledge base to answer this.", confidence: "insufficient", citations: [] }
        : { answer: "Budget is total. [budget#1]", confidence: "high", citations: [{ source: "<img src=x onerror=alert(1)>", chunk_id: "budget#1", snippet: "Trip budget" }] });
      if (url.endsWith("/trips/12")) return jsonResponse(trip);
      return jsonResponse([trip]);
    }));
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("[data-trip-id='12']")).not.toBeNull());
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#mcp-summary").disabled).toBe(false));
    document.querySelector("#mcp-summary").click();
    await vi.waitFor(() => expect(document.querySelector("#mcp-result").hidden).toBe(false));
    expect(document.querySelector("#mcp-result").textContent).toContain("Park walk");
    expect(document.querySelector("#mcp-result").textContent).toContain("Day 1");
    expect(document.querySelector("#mcp-result").textContent).toContain("Day 2");
    expect(document.querySelector("#mcp-result .trip-metrics")).toBeNull();
    setValue("#advice-question", "Budget?");
    document.querySelector("#advice-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await vi.waitFor(() => expect(document.querySelector("#advice-result").hidden).toBe(false));
    expect(document.querySelector("#advice-confidence").textContent).toBe("Source relevance: high");
    expect(document.querySelector("#advice-citations img")).toBeNull();
    insufficient = true;
    document.querySelector("#advice-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await vi.waitFor(() => expect(document.querySelector("#advice-status").textContent).toBe("Insufficient context."));
    expect(document.querySelector("#advice-citations").textContent).toBe("");
  });

  test("shows weather advice then clears the report for a non-weather response", async () => {
    const trip = { id: 12, user: "Alex", destination: "Tokyo", startDate: "2026-10-10", endDate: "2026-10-12", budget: 900, stops: [] };
    const locations = [{ id: 1, name: "Tokyo", admin1: "Tokyo", country: "Japan" }, { id: 2, name: "Tokyo", admin1: "Central", country: "Papua New Guinea" }];
    const fetchMock = vi.fn((url, options) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: true, mcpEnabled: true, ragEnabled: true });
      if (url.endsWith("/itinerary-advice")) {
        if (JSON.parse(options.body).question === "Is my budget per day?") {
          return jsonResponse({ ...adviceResponse(null), weatherNotice: "" });
        }
        return jsonResponse(adviceResponse({
          status: "partial", locations, location: locations[0], retrievedAt: "2026-09-28T10:00:00Z", unavailableDates: ["2026-10-12"],
          days: [{ date: "2026-10-10", weatherCode: 63, minTemperature: 12, maxTemperature: 20, precipitationProbability: 80 },
            { date: "2026-10-11", weatherCode: null, minTemperature: 13, maxTemperature: 21, precipitationProbability: null }],
        }));
      }
      return jsonResponse(url.endsWith("/trips/12") ? trip : [trip]);
    });
    vi.stubGlobal("fetch", fetchMock);
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("[data-trip-id='12']")).not.toBeNull());
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#mcp-summary").disabled).toBe(false));
    setValue("#advice-question", "Does the forecast affect my plans?");
    document.querySelector("#advice-submit").click();
    await vi.waitFor(() => expect(document.querySelector(".weather-days")).not.toBeNull());
    expect(document.querySelector("#weather-location")).toBeNull();
    expect(document.querySelector("#advice-result #overview-weather")).not.toBeNull();
    expect(document.querySelector("#mcp-result #overview-weather")).toBeNull();
    expect(document.querySelector(".weather-place").textContent).toContain("top match): Tokyo, Japan");
    expect(document.querySelector("#weather-status").textContent).toContain("part of this trip");
    expect(document.querySelector(".weather-days").textContent).toContain("80%");
    expect(document.querySelector(".weather-days").textContent).toContain("Not available");
    expect(document.querySelector(".weather-days").textContent).not.toContain("null");
    expect(document.querySelector(".weather-missing").textContent).toContain("2026-10-12");
    expect(document.querySelector(".weather-attribution").textContent).toContain("Open-Meteo");
    const calls = fetchMock.mock.calls.filter(([url]) => url.endsWith("/itinerary-advice"));
    expect(calls).toHaveLength(1);
    expect(JSON.parse(calls[0][1].body)).toEqual({ question: "Does the forecast affect my plans?", tripId: 12 });
    expect(fetchMock.mock.calls.every(([url]) => url.startsWith("/itinerary-api/"))).toBe(true);
    setValue("#advice-question", "Is my budget per day?");
    document.querySelector("#advice-submit").click();
    await nextTick();
    await vi.waitFor(() => expect(document.querySelector("#advice-result").hidden).toBe(false));
    expect(document.querySelector("#overview-weather")).toBeNull();
    expect(document.querySelector(".weather-attribution")).toBeNull();
    expect(document.querySelector("#advice-result").textContent).toContain("Keep timing flexible.");
  });

  test.each([
    ["unavailable", "Weather is currently unavailable"],
    ["outside_window", "outside the current forecast window"],
    ["not_found", "No matching weather location"],
  ])("retains advice when weather is %s", async (weatherStatus, message) => {
    const trip = { id: 12, user: "Alex", destination: "Tokyo", startDate: "2026-10-10", endDate: "2026-10-12", budget: 900, stops: [] };
    vi.stubGlobal("fetch", vi.fn((url) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: true, mcpEnabled: true, ragEnabled: true });
      if (url.endsWith("/itinerary-advice")) return jsonResponse(adviceResponse(
        { status: weatherStatus, locations: [], location: null, days: [], unavailableDates: ["2026-10-10"], retrievedAt: null }));
      return jsonResponse(url.endsWith("/trips/12") ? trip : [trip]);
    }));
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("[data-trip-id='12']")).not.toBeNull());
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#mcp-summary").disabled).toBe(false));
    setValue("#advice-question", "Outdoor planning in rainy weather?");
    document.querySelector("#advice-submit").click();
    await vi.waitFor(() => expect(document.querySelector("#weather-status")?.textContent).toContain(message));
    expect(document.querySelector("#advice-result").hidden).toBe(false);
    expect(document.querySelector("#advice-result").textContent).toContain("Keep timing flexible.");
    expect(document.querySelector(".weather-days")).toBeNull();
  });

  test("drops edit preview when switching trips during a request", async () => {
    const trip = { id: 12, user: "Alex", destination: "Tokyo", startDate: "2026-10-10", endDate: "2026-10-12", budget: 900, stops: [] };
    const other = { ...trip, id: 13, destination: "Paris" };
    let resolveOverview;
    vi.stubGlobal("fetch", vi.fn((url) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: true, mcpEnabled: true, ragEnabled: false });
      if (url.endsWith("/edit-preview")) return new Promise((resolve) => { resolveOverview = resolve; });
      if (url.endsWith("/trips/12")) return jsonResponse(trip);
      if (url.endsWith("/trips/13")) return jsonResponse(other);
      return jsonResponse([trip, other]);
    }));
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("[data-trip-id='12']")).not.toBeNull());
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#mcp-summary").disabled).toBe(false));
    document.querySelector("#mcp-summary").click();
    document.querySelector("[data-trip-id='13']").click();
    await vi.waitFor(() => expect(document.querySelector("#trip-title").textContent).toContain("Paris"));
    resolveOverview(await jsonResponse(reviewResponse()));
    await nextTick();
    expect(document.querySelector("#mcp-result").hidden).toBe(true);
    expect(document.querySelector("#overview-weather")).toBeNull();
  });

  test("locks edit preview while pending, prevents duplicates and restores input on failure", async () => {
    const trip = { id: 12, user: "Alex", destination: "Tokyo", startDate: "2026-10-10", endDate: "2026-10-12", budget: 900, stops: [] };
    let resolveReview;
    vi.stubGlobal("fetch", vi.fn((url) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: true, mcpEnabled: true, ragEnabled: false });
      if (url.endsWith("/edit-preview")) return new Promise((resolve) => { resolveReview = resolve; });
      return jsonResponse(url.endsWith("/trips/12") ? trip : [trip]);
    }));
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("[data-trip-id='12']")).not.toBeNull());
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#mcp-summary").disabled).toBe(false));
    document.querySelector("#review-form").dispatchEvent(new Event("submit", { cancelable: true }));
    document.querySelector("#review-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await nextTick();
    expect(document.querySelector("#review-question").disabled).toBe(true);
    expect(fetch.mock.calls.filter(([url]) => url.endsWith("/edit-preview"))).toHaveLength(1);
    resolveReview(await jsonResponse({ error: { message: "The requested service is unavailable." } }, 503));
    await vi.waitFor(() => expect(document.querySelector("#review-question").disabled).toBe(false));
    expect(document.querySelector("#mcp-status").textContent).toContain("unavailable");
    expect(document.querySelector("#mcp-result").hidden).toBe(true);
  });

  test("renders preview as text and supports clarification without a save button", async () => {
    const trip = { id: 12, user: "Alex", destination: "Tokyo", startDate: "2026-10-10", endDate: "2026-10-12", budget: 900, stops: [] };
    const result = reviewResponse();
    result.preview.changes[0].activity = "<img src=x onerror=alert(1)>";
    vi.stubGlobal("fetch", vi.fn((url) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: true, mcpEnabled: true, ragEnabled: false });
      if (url.endsWith("/edit-preview")) return jsonResponse(result);
      return jsonResponse(url.endsWith("/trips/12") ? trip : [trip]);
    }));
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("[data-trip-id='12']")).not.toBeNull());
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#mcp-summary").disabled).toBe(false));
    document.querySelector("#mcp-summary").click();
    await vi.waitFor(() => expect(document.querySelector("#mcp-result").hidden).toBe(false));
    expect(document.querySelector("#mcp-result img")).toBeNull();
    expect(document.querySelector("#mcp-result").textContent).toContain("<img src=x");
    result.preview = null;
    result.clarification = "Which days should be swapped?";
    document.querySelector("#mcp-summary").click();
    await vi.waitFor(() => expect(document.querySelector("#mcp-status").textContent).toContain("Which days"));
    expect(document.querySelectorAll(".review-finding")).toHaveLength(0);
    expect(document.querySelector("#confirm-edit")).toBeNull();
  });

  test("cancels without saving, then confirms only the token and refreshes the itinerary", async () => {
    const trip = { id: 12, user: "Alex", destination: "Tokyo", startDate: "2026-10-10", endDate: "2026-10-12", budget: 900,
      stops: [{ id: 1, day: 1, activity: "Park walk", notes: "Saved plan", sortOrder: 0 }] };
    let resolveSave;
    const fetchMock = vi.fn((url) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: true, mcpEnabled: true, ragEnabled: true });
      if (url.endsWith("/edit-preview")) return jsonResponse(reviewResponse());
      if (url.endsWith("/edit-confirm")) return new Promise((resolve) => { resolveSave = resolve; });
      return jsonResponse(url.endsWith("/trips/12") ? trip : [trip]);
    });
    vi.stubGlobal("fetch", fetchMock);
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("[data-trip-id='12']")).not.toBeNull());
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#mcp-summary").disabled).toBe(false));
    document.querySelector("#mcp-summary").click();
    await vi.waitFor(() => expect(document.querySelector("#confirm-edit")).not.toBeNull());
    expect(document.activeElement.id).toBe("mcp-result");
    document.querySelector("#cancel-edit").click();
    await nextTick();
    expect(document.querySelector("#mcp-result").hidden).toBe(true);
    expect(fetchMock.mock.calls.some(([url]) => url.endsWith("/edit-confirm"))).toBe(false);
    document.querySelector("#mcp-summary").click();
    await vi.waitFor(() => expect(document.querySelector("#confirm-edit")).not.toBeNull());
    document.querySelector("#confirm-edit").click();
    document.querySelector("#confirm-edit").click();
    await nextTick();
    expect(document.querySelector("#confirm-edit").disabled).toBe(true);
    const saves = fetchMock.mock.calls.filter(([url]) => url.endsWith("/edit-confirm"));
    expect(saves).toHaveLength(1);
    expect(JSON.parse(saves[0][1].body)).toEqual({ token: "signed-preview" });
    trip.stops[0].day = 2;
    resolveSave(await jsonResponse({ tripId: 12, applied: true, changes: reviewResponse().preview.changes }));
    await vi.waitFor(() => expect(document.querySelector("#mcp-status").textContent).toContain('Moved "Park walk" to Day 2.'));
    expect(document.querySelector("#days #day-2")).not.toBeNull();
    expect(document.querySelector("#mcp-result").hidden).toBe(true);
  });

  test.each([409, 504])("discards a rejected or uncertain save (%s) and permits a new preview", async (httpStatus) => {
    const trip = { id: 12, user: "Alex", destination: "Tokyo", startDate: "2026-10-10", endDate: "2026-10-12", budget: 900, stops: [] };
    vi.stubGlobal("fetch", vi.fn((url) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: true, mcpEnabled: true, ragEnabled: false });
      if (url.endsWith("/edit-preview")) return jsonResponse(reviewResponse());
      if (url.endsWith("/edit-confirm")) return jsonResponse({ error: { message: "Save was not acknowledged." } }, httpStatus);
      return jsonResponse(url.endsWith("/trips/12") ? trip : [trip]);
    }));
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("[data-trip-id='12']")).not.toBeNull());
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#mcp-summary").disabled).toBe(false));
    document.querySelector("#mcp-summary").click();
    await vi.waitFor(() => expect(document.querySelector("#confirm-edit")).not.toBeNull());
    setValue("#review-question", "Move day 1 to day 3");
    await nextTick();
    expect(document.querySelector("#confirm-edit")).toBeNull();
    document.querySelector("#mcp-summary").click();
    await vi.waitFor(() => expect(document.querySelector("#confirm-edit")).not.toBeNull());
    document.querySelector("#confirm-edit").click();
    await vi.waitFor(() => expect(document.querySelector("#mcp-status").textContent).toContain("Refresh the saved trip"));
    expect(document.querySelector("#confirm-edit")).toBeNull();
    expect(document.querySelector("#mcp-summary").disabled).toBe(false);
    expect(fetch.mock.calls.filter(([url]) => url.endsWith("/edit-confirm"))).toHaveLength(1);
  });

  test("clears weather and ignores stale advice after changing trips", async () => {
    const trip = { id: 12, user: "Alex", destination: "Tokyo", startDate: "2026-10-10", endDate: "2026-10-12", budget: 900, stops: [] };
    const other = { ...trip, id: 13, destination: "Paris" };
    let resolveAdvice;
    vi.stubGlobal("fetch", vi.fn((url) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: true, mcpEnabled: true, ragEnabled: true });
      if (url.endsWith("/itinerary-advice")) return new Promise((resolve) => { resolveAdvice = resolve; });
      if (url.endsWith("/trips/12")) return jsonResponse(trip);
      if (url.endsWith("/trips/13")) return jsonResponse(other);
      return jsonResponse([trip, other]);
    }));
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("[data-trip-id='12']")).not.toBeNull());
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#trip-title").textContent).toContain("Tokyo"));
    setValue("#advice-question", "Outdoor planning?");
    document.querySelector("#advice-submit").click();
    document.querySelector("[data-trip-id='13']").click();
    await vi.waitFor(() => expect(document.querySelector("#trip-title").textContent).toContain("Paris"));
    resolveAdvice(await jsonResponse(adviceResponse({ status: "unavailable", days: [] })));
    await nextTick();
    expect(document.querySelector("#advice-result").hidden).toBe(true);
    expect(document.querySelector("#overview-weather")).toBeNull();
  });

  test("loads saved trips through the same-origin backend route", async () => {
    const fetchMock = vi.fn(() => jsonResponse([
      { id: 4, user: "Alex", destination: "Kyoto", startDate: "2026-10-10", endDate: "2026-10-12" },
      { id: 5, user: "Sam", destination: "Lisbon", startDate: "2026-11-10", endDate: "2026-11-12" },
    ]));
    vi.stubGlobal("fetch", fetchMock);

    await loadApplication();

    await vi.waitFor(() => expect(document.querySelector("#trip-list").textContent).toContain("Kyoto"));
    expect(fetchMock).toHaveBeenCalledWith("/itinerary-api/trips", expect.any(Object));
    expect(document.querySelector("#trip-count").textContent).toBe("2 saved trips");
    document.querySelector("#trip-filter").value = "sam";
    document.querySelector("#trip-filter").dispatchEvent(new Event("input", { bubbles: true }));
    await nextTick();
    expect(document.querySelector("#trip-list").textContent).toContain("Lisbon");
    expect(document.querySelector("#trip-list").textContent).not.toContain("Kyoto");
    expect(document.querySelector("#trip-count").textContent).toBe("1 of 2 trips");
  });

  test("submits trip details and renders the generated day-by-day itinerary", async () => {
    const createdTrip = {
      id: 12,
      user: "Alex",
      destination: "Osaka",
      startDate: "2026-10-10",
      endDate: "2026-10-11",
      budget: 1500,
      interests: "food",
      generationMode: "ai",
      agentTrace: [
        { stage: "Plan", outcome: "Validated the trip." },
        { stage: "Act", outcome: "Generated four stops." },
        { stage: "Observe", outcome: "Validated the stops." },
        { stage: "Adapt", outcome: "Accepted the itinerary." },
      ],
      stops: [
        { id: 1, day: 1, activity: "Market walk", notes: "Try local food." },
        { id: 2, day: 2, activity: "Museum visit", notes: "See local exhibits." },
      ],
    };
    const fetchMock = vi.fn((url, options) => {
      if (options?.method === "POST") return jsonResponse(createdTrip, 201);
      return jsonResponse([]);
    });
    vi.stubGlobal("fetch", fetchMock);
    await loadApplication();
    setValue("#user", "Alex");
    setValue("#destination", "Osaka");
    setValue("#start-date", "2026-10-10");
    setValue("#end-date", "2026-10-11");
    setValue("#budget", "1500");
    setValue("#interests", "food");

    document.querySelector("#trip-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

    await vi.waitFor(() => expect(document.querySelector("#trip-title").textContent).toBe("Osaka itinerary"));
    expect(document.querySelector("#days").textContent).toContain("Market walk");
    expect(document.querySelector("#days").textContent).toContain("Museum visit");
    expect(document.querySelector("#metric-duration").textContent).toBe("2 days");
    expect(document.querySelector("#metric-stops").textContent).toBe("2");
    expect(document.querySelector("#metric-budget").textContent).toBe("AUD 750");
    expect(document.querySelector("#metric-days").textContent).toBe("2 / 2");
    const createCall = fetchMock.mock.calls.find(([, options]) => options?.method === "POST");
    expect(createCall[0]).toBe("/itinerary-api/trips");
    expect(JSON.parse(createCall[1].body)).toMatchObject({ destination: "Osaka", budget: 1500, interests: "food" });
  });

  test("opens a saved trip and updates its details through the backend", async () => {
    const trip = {
      id: 12, user: "Alex", destination: "Osaka", startDate: "2026-10-10",
      endDate: "2026-10-11", budget: 1500, interests: "food", stops: [],
    };
    const updated = { ...trip, destination: "Kyoto" };
    let wasUpdated = false;
    const fetchMock = vi.fn((url, options) => {
      if (url === "/itinerary-api/trips/12" && options?.method === "PUT") {
        wasUpdated = true;
        return jsonResponse(updated);
      }
      if (url === "/itinerary-api/trips/12") return jsonResponse(wasUpdated ? updated : trip);
      return jsonResponse([wasUpdated ? updated : trip]);
    });
    vi.stubGlobal("fetch", fetchMock);
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("#trip-list").textContent).toContain("Osaka"));

    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#trip-title").textContent).toBe("Osaka itinerary"));
    document.querySelector("#trip-composer").open = false;
    document.querySelector("#edit-trip").click();
    await nextTick();
    expect(document.querySelector("#trip-composer").open).toBe(true);
    expect(document.querySelector("#trip-form-summary").textContent).toBe("Osaka · 2026-10-10 to 2026-10-11");
    expect(document.querySelector("#destination").value).toBe("Osaka");
    setValue("#destination", "Kyoto");
    document.querySelector("#trip-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

    await vi.waitFor(() => expect(document.querySelector("#trip-title").textContent).toBe("Kyoto itinerary"));
    const updateCall = fetchMock.mock.calls.find(([, options]) => options?.method === "PUT");
    expect(updateCall[0]).toBe("/itinerary-api/trips/12");
    expect(JSON.parse(updateCall[1].body).destination).toBe("Kyoto");
    expect(document.querySelector("#status").textContent).toBe("Trip details updated.");
  });

  test("edits, regenerates, replaces, and removes itinerary stops", async () => {
    const trip = {
      id: 12, user: "Alex", destination: "Osaka", startDate: "2026-10-10",
      endDate: "2026-10-11", budget: 1500, interests: "food",
    };
    let stops = [{ id: 1, tripId: 12, day: 1, activity: "Market walk", notes: "Morning", sortOrder: 0 }];
    const fetchMock = vi.fn((url, options) => {
      if (url === "/itinerary-api/trips/12/stops" && options?.method === "POST") {
        stops.push({ id: 3, ...JSON.parse(options.body) });
        return jsonResponse(stops.at(-1), 201);
      }
      if (url === "/itinerary-api/stops/1" && options?.method === "PUT") {
        stops = [{ ...stops[0], ...JSON.parse(options.body) }];
        return jsonResponse(stops[0]);
      }
      if (url === "/itinerary-api/stops/1/regenerate") {
        stops = [{ ...stops[0], activity: "Regenerated market walk" }];
        return jsonResponse({ stop: stops[0], generationMode: "ai" });
      }
      if (url === "/itinerary-api/trips/12/regenerate") {
        stops = [{ id: 2, tripId: 12, day: 2, activity: "Castle visit", notes: "Afternoon", sortOrder: 0 }];
        return jsonResponse({ stops, generationMode: "ai" });
      }
      if (url === "/itinerary-api/stops/2" && options?.method === "DELETE") {
        stops = [];
        return jsonResponse(null, 204);
      }
      if (url === "/itinerary-api/trips/12") return jsonResponse({ ...trip, stops });
      return jsonResponse([trip]);
    });
    vi.stubGlobal("fetch", fetchMock);
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("[data-trip-id='12']")).not.toBeNull());
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#days").textContent).toContain("Market walk"));

    const stopActionsMenu = document.querySelector(".stop-action-menu");
    expect(stopActionsMenu.querySelectorAll("button")).toHaveLength(4);
    stopActionsMenu.open = true;
    document.querySelector("[data-edit-stop='1']").click();
    await nextTick();
    expect(stopActionsMenu.open).toBe(false);
    expect(document.querySelector("#stop-day").max).toBe("2");
    setValue("#stop-activity", "Edited market walk");
    document.querySelector("#stop-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await vi.waitFor(() => expect(document.querySelector("#days").textContent).toContain("Edited market walk"));
    const stopUpdate = fetchMock.mock.calls.find(([url, options]) => url === "/itinerary-api/stops/1" && options?.method === "PUT");
    expect(JSON.parse(stopUpdate[1].body)).toMatchObject({ sortOrder: 0 });
    expect(JSON.parse(stopUpdate[1].body)).not.toHaveProperty("tripId");

    document.querySelector("[data-duplicate-stop='1']").click();
    await vi.waitFor(() => expect(document.querySelector("#days").textContent).toContain("Edited market walk (copy)"));
    expect(document.querySelector("#metric-stops").textContent).toBe("2");

    document.querySelector("[data-regenerate-stop='1']").click();
    await vi.waitFor(() => expect(document.querySelector("#days").textContent).toContain("Regenerated market walk"));
    document.querySelector("#regenerate-trip").click();
    await nextTick();
    expect(document.querySelector("#feedback-title").textContent).toBe("Regenerate itinerary?");
    document.querySelector("#feedback-confirm").click();
    await vi.waitFor(() => expect(document.querySelector("#days").textContent).toContain("Castle visit"));
    document.querySelector("[data-remove-stop='2']").click();
    await nextTick();
    expect(document.querySelector("#feedback-title").textContent).toBe("Remove stop?");
    document.querySelector("#feedback-confirm").click();
    await vi.waitFor(() => expect(document.querySelector("#days").textContent).toContain("No stops yet"));
  });

  test("uses custom modals for validation, API errors, and confirmation cancellation", async () => {
    const fetchMock = vi.fn((url, options) => {
      if (options?.method === "POST") {
        return jsonResponse({ error: { message: "The planning service is unavailable." } }, 503);
      }
      return jsonResponse([]);
    });
    vi.stubGlobal("fetch", fetchMock);
    await loadApplication();

    document.querySelector("#trip-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await nextTick();
    expect(document.querySelector("#feedback-dialog").dataset.kind).toBe("validation");
    expect(document.querySelector("#feedback-title").textContent).toBe("Check details");
    expect(document.querySelector("#feedback-message").textContent).toBe("Traveller is required.");
    document.querySelector("#feedback-confirm").click();

    setValue("#user", "Alex");
    setValue("#destination", "Osaka");
    setValue("#start-date", "2026-10-10");
    setValue("#end-date", "2026-10-11");
    setValue("#budget", "1500");
    document.querySelector("#trip-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await vi.waitFor(() => expect(document.querySelector("#feedback-dialog").dataset.kind).toBe("error"));
    expect(document.querySelector("#feedback-title").textContent).toBe("Something went wrong");
    expect(document.querySelector("#feedback-message").textContent).toBe("The planning service is unavailable.");
    expect(document.querySelector("#status").textContent).toBe("");
    document.querySelector("#feedback-confirm").click();

    const trip = { id: 12, user: "Alex", destination: "Osaka", startDate: "2026-10-10", endDate: "2026-10-11", budget: 1500, stops: [] };
    fetchMock.mockImplementation((url) => jsonResponse(url.endsWith("/trips/12") ? trip : [trip]));
    document.querySelector("#refresh-trips").click();
    await vi.waitFor(() => expect(document.querySelector("[data-trip-id='12']")).not.toBeNull());
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#trip-title").textContent).toBe("Osaka itinerary"));
    document.querySelector("#delete-trip").click();
    await nextTick();
    expect(document.querySelector("#feedback-dialog").dataset.kind).toBe("confirm");
    document.querySelector("#feedback-cancel").click();
    expect(fetchMock.mock.calls.some(([url, options]) => url === "/itinerary-api/trips/12" && options?.method === "DELETE")).toBe(false);
  });

  test("adds a stop and confirms deletion of the selected trip", async () => {
    const trip = { id: 12, user: "Alex", destination: "Osaka", startDate: "2026-10-10", endDate: "2026-10-11", budget: 1500, stops: [] };
    let deleted = false;
    const fetchMock = vi.fn((url, options) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: false, mcpEnabled: false, ragEnabled: false });
      if (url.endsWith("/stops") && options?.method === "POST") {
        trip.stops.push({ id: 1, ...JSON.parse(options.body) });
        return jsonResponse(trip.stops[0], 201);
      }
      if (options?.method === "DELETE") { deleted = true; return jsonResponse(null, 204); }
      if (url.endsWith("/trips/12")) return jsonResponse(trip);
      return jsonResponse(deleted ? [] : [trip]);
    });
    vi.stubGlobal("fetch", fetchMock);
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("[data-trip-id='12']")).not.toBeNull());
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#itinerary-content").hidden).toBe(false));
    document.querySelector("#add-stop").click();
    await nextTick();
    setValue("#stop-day", "2");
    setValue("#stop-activity", "Evening walk");
    setValue("#stop-notes", "Along the river");
    document.querySelector("#stop-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await vi.waitFor(() => expect(document.querySelector("#days").textContent).toContain("Evening walk"));
    const createCall = fetchMock.mock.calls.find(([, options]) => options?.method === "POST");
    expect(createCall[0]).toBe("/itinerary-api/trips/12/stops");
    expect(JSON.parse(createCall[1].body)).toEqual({ day: 2, activity: "Evening walk", notes: "Along the river", sortOrder: 0 });
    expect(document.querySelector("#stop-dialog").open).toBe(false);
    document.querySelector("#edit-trip").click();
    await nextTick();
    document.querySelector("#delete-trip").click();
    await nextTick();
    document.querySelector("#feedback-confirm").click();
    await vi.waitFor(() => expect(document.querySelector("#status").textContent).toBe("Trip deleted."));
    expect(document.querySelector("#itinerary-content").hidden).toBe(true);
    expect(document.querySelector("#empty-state").hidden).toBe(false);
    expect(document.querySelector("#trip-count").textContent).toBe("0 saved trips");
    expect(document.querySelector("#destination").value).toBe("");
  });

  test("prints the selected itinerary", async () => {
    const printMock = vi.fn();
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse([])));
    vi.stubGlobal("print", printMock);
    await loadApplication();
    const actionsMenu = document.querySelector("#trip-actions-menu");
    expect(actionsMenu.querySelectorAll("button")).toHaveLength(3);
    actionsMenu.open = true;
    document.querySelector("#print-trip").click();
    expect(printMock).toHaveBeenCalledOnce();
    expect(actionsMenu.open).toBe(false);
  });
});
