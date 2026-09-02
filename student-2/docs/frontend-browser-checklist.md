# Itinerary Planner Browser Checklist

Run this against `http://localhost:5100/itinerary/` after a clean Compose startup. Record screenshot/video paths and do not mark an item complete from automated tests alone.

## Shared Integration

- [ ] Open the shared home page on port 5100 and select Itinerary Planner.
- [ ] Confirm the route remains under `/itinerary/` and the shared header/theme is visible.
- [ ] Confirm browser requests use `/itinerary-api/` and never call the database or Ollama directly.
- [ ] Filter saved trips by destination and traveller.

## Trip and AI Flow

- [ ] Submit invalid fields and capture visible feedback without a saved trip.
- [ ] Submit a valid trip and capture loading state.
- [ ] Capture a genuine AI-generated itinerary with two stops for every day.
- [ ] Force Ollama unavailable/invalid and capture the visible fallback notice.
- [ ] Reopen the saved trip and confirm no new generation request occurs.

## CRUD and Revision

- [ ] Create a trip.
- [ ] Read it from Saved trips.
- [ ] Edit trip details and confirm the saved itinerary reflects them.
- [ ] Edit an individual stop.
- [ ] Duplicate an individual stop.
- [ ] Add an individual stop.
- [ ] Regenerate an individual stop.
- [ ] Remove an individual stop after confirmation.
- [ ] Regenerate the whole itinerary and verify replacement is complete.
- [ ] Delete a trip after confirmation and verify it leaves Saved trips.
- [ ] Restart the database/app stack and verify retained data remains.
- [ ] Open the print preview and confirm only the selected itinerary is included.

## Accessibility and Responsive Layout

- [ ] Complete the primary workflow using keyboard only.
- [ ] Confirm visible focus on links, inputs, buttons, and dialog controls.
- [ ] Confirm status changes are announced by the live region.
- [ ] Confirm labels and dialog actions have meaningful accessible names.
- [ ] At 320px, verify no horizontal page scroll or clipped controls.
- [ ] At 768px, verify form/history and itinerary remain usable.
- [ ] At 1280px, verify layout and reading order remain coherent.

## Evidence Paths

| Evidence | Path or URL |
|---|---|
| Shared home and feature route | Pending |
| AI success | Pending |
| Forced fallback | Pending |
| CRUD sequence | Pending |
| Restart persistence | Pending |
| 320px / 768px / 1280px | Pending |
