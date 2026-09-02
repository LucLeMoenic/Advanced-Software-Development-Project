// @vitest-environment jsdom

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, test, vi } from "vitest";

const page = readFileSync(resolve(process.cwd(), "index.html"), "utf8");
const body = page.match(/<body>([\s\S]*)<\/body>/)[1];

function jsonResponse(value, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(value),
  });
}

async function loadApplication() {
  await import("../app.js");
  window.dispatchEvent(new Event("load"));
}

beforeEach(() => {
  vi.resetModules();
  document.body.innerHTML = body;
  vi.restoreAllMocks();
  document.querySelectorAll("dialog").forEach((dialog) => {
    dialog.showModal = vi.fn(() => { dialog.open = true; });
    dialog.close = vi.fn(() => { dialog.open = false; });
  });
});

describe("Itinerary Planner", () => {
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
    document.querySelector("#user").value = "Alex";
    document.querySelector("#destination").value = "Osaka";
    document.querySelector("#start-date").value = "2026-10-10";
    document.querySelector("#end-date").value = "2026-10-11";
    document.querySelector("#budget").value = "1500";
    document.querySelector("#interests").value = "food";

    document.querySelector("#trip-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

    await vi.waitFor(() => expect(document.querySelector("#trip-title").textContent).toBe("Osaka itinerary"));
    expect(document.querySelector("#days").textContent).toContain("Market walk");
    expect(document.querySelector("#days").textContent).toContain("Museum visit");
    expect(document.querySelector("#trace-list").textContent).toContain("Adapt");
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
    expect(document.querySelector("#trip-composer").open).toBe(true);
    expect(document.querySelector("#trip-form-summary").textContent).toBe("Osaka · 2026-10-10 to 2026-10-11");
    expect(document.querySelector("#destination").value).toBe("Osaka");
    document.querySelector("#destination").value = "Kyoto";
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
    expect(stopActionsMenu.open).toBe(false);
    expect(document.querySelector("#stop-day").max).toBe("2");
    document.querySelector("#stop-activity").value = "Edited market walk";
    document.querySelector("#stop-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await vi.waitFor(() => expect(document.querySelector("#days").textContent).toContain("Edited market walk"));

    document.querySelector("[data-duplicate-stop='1']").click();
    await vi.waitFor(() => expect(document.querySelector("#days").textContent).toContain("Edited market walk (copy)"));
    expect(document.querySelector("#metric-stops").textContent).toBe("2");

    document.querySelector("[data-regenerate-stop='1']").click();
    await vi.waitFor(() => expect(document.querySelector("#days").textContent).toContain("Regenerated market walk"));
    document.querySelector("#regenerate-trip").click();
    expect(document.querySelector("#feedback-title").textContent).toBe("Regenerate itinerary?");
    document.querySelector("#feedback-confirm").click();
    await vi.waitFor(() => expect(document.querySelector("#days").textContent).toContain("Castle visit"));
    document.querySelector("[data-remove-stop='2']").click();
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
    expect(document.querySelector("#feedback-dialog").dataset.kind).toBe("validation");
    expect(document.querySelector("#feedback-title").textContent).toBe("Check details");
    expect(document.querySelector("#feedback-message").textContent).toBe("Traveller is required.");
    document.querySelector("#feedback-confirm").click();

    document.querySelector("#user").value = "Alex";
    document.querySelector("#destination").value = "Osaka";
    document.querySelector("#start-date").value = "2026-10-10";
    document.querySelector("#end-date").value = "2026-10-11";
    document.querySelector("#budget").value = "1500";
    document.querySelector("#trip-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await vi.waitFor(() => expect(document.querySelector("#feedback-dialog").dataset.kind).toBe("error"));
    expect(document.querySelector("#feedback-title").textContent).toBe("Something went wrong");
    expect(document.querySelector("#feedback-message").textContent).toBe("The planning service is unavailable.");
    document.querySelector("#feedback-confirm").click();

    const trip = { id: 12, user: "Alex", destination: "Osaka", startDate: "2026-10-10", endDate: "2026-10-11", budget: 1500, stops: [] };
    document.querySelector("#trip-list").innerHTML = '<li><button data-trip-id="12">Osaka</button></li>';
    fetchMock.mockResolvedValueOnce(await jsonResponse(trip));
    document.querySelector("[data-trip-id='12']").click();
    await vi.waitFor(() => expect(document.querySelector("#trip-title").textContent).toBe("Osaka itinerary"));
    document.querySelector("#delete-trip").click();
    expect(document.querySelector("#feedback-dialog").dataset.kind).toBe("confirm");
    document.querySelector("#feedback-cancel").click();
    expect(fetchMock.mock.calls.some(([url, options]) => url === "/itinerary-api/trips/12" && options?.method === "DELETE")).toBe(false);
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
