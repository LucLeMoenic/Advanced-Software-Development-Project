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

## Release 1 Editor and Advice

- [ ] Request a day swap, day move and named-stop move with the real model.
- [ ] Inspect before/after preview; cancel and verify no changes are persisted.
- [ ] Confirm once, reopen the trip and verify days/order and original stop IDs.
- [ ] Change a stop after preview and verify confirmation rejects stale state.
- [ ] Change the command or selected trip and verify the preview is discarded.
- [ ] Ask an ambiguous/unsupported command and verify clarification without saving.
- [ ] Verify save failure discards the token and requests refresh without retry.
- [ ] Ask RAG for outdoor planning advice within the forecast window; verify guide
  citations/confidence and separately attributed first-match weather.
- [ ] Verify partial/outside-window/missing weather and no location picker.
- [ ] Verify unrelated questions still produce insufficient context.
- [ ] Verify trip changes clear advice and ignore late responses.
- [ ] Verify unavailable MCP/model and disabled AI/MCP states.
- [ ] Capture genuine model-to-MCP editing and generated source-support evidence.

1 October: browser fixtures passed at 320/768/1280px without overflow/page errors.
The actual gateway displayed the editor, ten saved trips, RAG abstention and
outside-window weather. These do not complete the real-model checklist above.

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
