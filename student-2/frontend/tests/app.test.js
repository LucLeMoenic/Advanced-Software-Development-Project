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

  test("ignores a pending summary after a successful 204 stop deletion", async () => {
    const trip = { id: 12, user: "Alex", destination: "Tokyo", startDate: "2026-10-10", endDate: "2026-10-12", budget: 900,
      stops: [{ id: 1, tripId: 12, day: 1, activity: "Walk", notes: "", sortOrder: 0 }] };
    let resolveSummary;
    let deleted = false;
    vi.stubGlobal("fetch", vi.fn((url, options) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: false, mcpEnabled: true, ragEnabled: false });
      if (url.endsWith("/mcp-overview")) return new Promise((resolve) => { resolveSummary = resolve; });
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
    resolveSummary(await jsonResponse({ summary: { stopCount: 1, dayCount: 3, plannedDayCount: 1, unplannedDays: [2, 3], dailyBudgetAllocation: 300 } }));
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

  test("shows MCP summary and safely renders cited RAG answers and insufficient context", async () => {
    const trip = { id: 12, user: "Alex", destination: "Tokyo", startDate: "2026-10-10", endDate: "2026-10-12", budget: 900, stops: [] };
    let insufficient = false;
    vi.stubGlobal("fetch", vi.fn((url) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: true, mcpEnabled: true, ragEnabled: true });
      if (url.endsWith("/mcp-overview")) return jsonResponse({ summary: { stopCount: 0, dayCount: 3, plannedDayCount: 0, unplannedDays: [1, 2, 3], dailyBudgetAllocation: 300 } });
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
    expect(document.querySelector("#mcp-result").textContent).toContain("1, 2, 3");
    setValue("#advice-question", "Budget?");
    document.querySelector("#advice-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await vi.waitFor(() => expect(document.querySelector("#advice-result").hidden).toBe(false));
    expect(document.querySelector("#advice-confidence").textContent).toBe("Confidence: high");
    expect(document.querySelector("#advice-citations img")).toBeNull();
    insufficient = true;
    document.querySelector("#advice-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await vi.waitFor(() => expect(document.querySelector("#advice-status").textContent).toBe("Insufficient context."));
    expect(document.querySelector("#advice-citations").textContent).toBe("");
  });

  test("combines summary with location selection and a partial forecast", async () => {
    const trip = { id: 12, user: "Alex", destination: "Tokyo", startDate: "2026-10-10", endDate: "2026-10-12", budget: 900, stops: [] };
    const locations = [{ id: 1, name: "Tokyo", admin1: "Tokyo", country: "Japan" }, { id: 2, name: "Tokyo", admin1: "Central", country: "Papua New Guinea" }];
    const summary = { stopCount: 0, dayCount: 3, plannedDayCount: 0, unplannedDays: [1, 2, 3], dailyBudgetAllocation: 300 };
    const fetchMock = vi.fn((url, options) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: false, mcpEnabled: true, ragEnabled: false });
      if (url.endsWith("/mcp-overview")) {
        const selected = JSON.parse(options.body).locationId;
        return jsonResponse({ summary, weather: selected ? {
          status: "partial", locations, location: locations[0], retrievedAt: "2026-09-28T10:00:00Z", unavailableDates: ["2026-10-12"],
          days: [{ date: "2026-10-10", weatherCode: 63, minTemperature: 12, maxTemperature: 20, precipitationProbability: 80 },
            { date: "2026-10-11", weatherCode: null, minTemperature: 13, maxTemperature: 21, precipitationProbability: null }],
        } : { status: "choose_location", locations, location: null, retrievedAt: null, days: [], unavailableDates: [] } });
      }
      return jsonResponse(url.endsWith("/trips/12") ? trip : [trip]);
    });
    vi.stubGlobal("fetch", fetchMock);
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("[data-trip-id='12']")).not.toBeNull());
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#mcp-summary").disabled).toBe(false));
    document.querySelector("#mcp-summary").click();
    await vi.waitFor(() => expect(document.querySelector("#weather-location")).not.toBeNull());
    expect(document.querySelector("#mcp-result").textContent).toContain("300.00");
    expect(document.activeElement.id).toBe("weather-location");
    const select = document.querySelector("#weather-location");
    select.value = "1";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    await nextTick();
    document.querySelector("#weather-location-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await vi.waitFor(() => expect(document.querySelector(".weather-days")).not.toBeNull());
    expect(document.querySelector("#weather-status").textContent).toContain("part of this trip");
    expect(document.querySelector(".weather-days").textContent).toContain("80%");
    expect(document.querySelector(".weather-days").textContent).toContain("Not available");
    expect(document.querySelector(".weather-days").textContent).not.toContain("null");
    expect(document.querySelector(".weather-missing").textContent).toContain("2026-10-12");
    expect(document.querySelector(".weather-attribution").textContent).toContain("Open-Meteo");
    expect(JSON.parse(fetchMock.mock.calls.filter(([url]) => url.endsWith("/mcp-overview"))[1][1].body)).toEqual({ locationId: 1 });
    expect(fetchMock.mock.calls.every(([url]) => url.startsWith("/itinerary-api/"))).toBe(true);
  });

  test.each([
    ["unavailable", "Weather is currently unavailable"],
    ["outside_window", "outside the current forecast window"],
    ["not_found", "No matching weather location"],
  ])("retains summary when weather is %s", async (weatherStatus, message) => {
    const trip = { id: 12, user: "Alex", destination: "Tokyo", startDate: "2026-10-10", endDate: "2026-10-12", budget: 900, stops: [] };
    vi.stubGlobal("fetch", vi.fn((url) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: false, mcpEnabled: true, ragEnabled: false });
      if (url.endsWith("/mcp-overview")) return jsonResponse({
        summary: { stopCount: 0, dayCount: 3, plannedDayCount: 0, unplannedDays: [1, 2, 3], dailyBudgetAllocation: 300 },
        weather: { status: weatherStatus, locations: [], location: null, days: [], unavailableDates: ["2026-10-10"], retrievedAt: null },
      });
      return jsonResponse(url.endsWith("/trips/12") ? trip : [trip]);
    }));
    await loadApplication();
    await vi.waitFor(() => expect(document.querySelector("[data-trip-id='12']")).not.toBeNull());
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#mcp-summary").disabled).toBe(false));
    document.querySelector("#mcp-summary").click();
    await vi.waitFor(() => expect(document.querySelector("#weather-status")?.textContent).toContain(message));
    expect(document.querySelector("#mcp-result").hidden).toBe(false);
    expect(document.querySelector("#mcp-result").textContent).toContain("1, 2, 3");
    expect(document.querySelector(".weather-days")).toBeNull();
  });

  test("drops overview and location selection when switching trips during a request", async () => {
    const trip = { id: 12, user: "Alex", destination: "Tokyo", startDate: "2026-10-10", endDate: "2026-10-12", budget: 900, stops: [] };
    const other = { ...trip, id: 13, destination: "Paris" };
    let resolveOverview;
    vi.stubGlobal("fetch", vi.fn((url) => {
      if (url.endsWith("/capabilities")) return jsonResponse({ aiEnabled: false, mcpEnabled: true, ragEnabled: false });
      if (url.endsWith("/mcp-overview")) return new Promise((resolve) => { resolveOverview = resolve; });
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
    resolveOverview(await jsonResponse({ summary: { stopCount: 99 }, weather: { status: "available" } }));
    await nextTick();
    expect(document.querySelector("#mcp-result").hidden).toBe(true);
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
