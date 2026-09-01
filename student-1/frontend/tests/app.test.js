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
});

describe("Itinerary Planner", () => {
  test("loads saved trips through the same-origin backend route", async () => {
    const fetchMock = vi.fn(() => jsonResponse([
      { id: 4, destination: "Kyoto", startDate: "2026-10-10", endDate: "2026-10-12" },
    ]));
    vi.stubGlobal("fetch", fetchMock);

    await loadApplication();

    await vi.waitFor(() => expect(document.querySelector("#trip-list").textContent).toContain("Kyoto"));
    expect(fetchMock).toHaveBeenCalledWith("/itinerary-api/trips", expect.any(Object));
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
    const createCall = fetchMock.mock.calls.find(([, options]) => options?.method === "POST");
    expect(createCall[0]).toBe("/itinerary-api/trips");
    expect(JSON.parse(createCall[1].body)).toMatchObject({ destination: "Osaka", budget: 1500, interests: "food" });
  });
});
