# Student 4 Browser Validation Checklist

Run against `http://localhost:5100/budget/` after the Compose stack is healthy.
Record browser/version, date, screenshots, and failures. Do not mark an item
complete from jsdom tests alone.

## Startup and Shared Integration

- [ ] The shared home card identifies Student 4 and Budget & Expense Tracker.
- [ ] `/budget` redirects to `/budget/`.
- [ ] `/budget/` loads relative CSS, JavaScript, and local HTMX without console errors.
- [ ] Refreshing `/budget/` retains the application route.

## Dashboard and Data

- [ ] Both seeded journey labels appear in the selector.
- [ ] Planned, actual, remaining, percentage, period, and base currency are correct.
- [ ] Warning and overspent categories show distinct labels/notices.
- [ ] Expense rows show original and converted currencies and the rate date.
- [ ] The rate version and demonstration disclaimer are visible.

## Budget CRUD

- [ ] Create a budget and confirm it appears after reload.
- [ ] Edit its amount/period and confirm updated values.
- [ ] Cancel delete and confirm no request/state change.
- [ ] Confirm delete and verify linked expenses are removed.
- [ ] Duplicate and mixed-currency conflicts display useful validation.

## Expense CRUD and Conversion

- [ ] Create an expense in another supported currency.
- [ ] Preview shows converted amount, rate, and date.
- [ ] Saved conversion matches authoritative backend recomputation.
- [ ] Edit amount/currency/date and confirm a new snapshot is saved.
- [ ] Cancel then confirm expense deletion.
- [ ] Unsupported currency and outside-period date errors are understandable.

## Advice

- [ ] Valid live model output is labelled AI or AI after retry.
- [ ] Summary and one to three suggestions reference supplied categories only.
- [ ] Stopping Ollama produces labelled reliable fallback advice.
- [ ] Dashboard and CRUD remain usable while Ollama is unavailable.

## Release 1 Tools

- [ ] With MCP enabled, the selected journey check calls `/budget-api/api/budget-check` with only `journeyLabel` and identifies `budget.get_summary`.
- [ ] Budget-check planned, actual, remaining, percentage, categories, and statuses match the authoritative response, including negative remaining amounts.
- [ ] The optional raw validated response is readable and contains no executable markup.
- [ ] With MCP disabled or capabilities unavailable, the new check stays disabled while existing CRUD remains usable.
- [ ] A failed budget-check request shows an error state; a journey change or successful selected-journey mutation clears the previous result.
- [ ] Guidance calls `/budget-api/api/budget-guidance` with the entered question and remains visibly separate from journey totals.
- [ ] Supported guidance shows its confidence label and expandable source name, snippet, and chunk identifier.
- [ ] Insufficient knowledge shows the fixed abstention state without citations; dependency failures remain errors rather than abstentions.
- [ ] Guidance cancellation and edits prevent a late answer from replacing the current question state.
- [ ] MCP/RAG disabled or capability failure disables only the corresponding new control.
- [ ] Both panels remain usable without overlap at 320px, 768px, and 1280px; keyboard focus and screen-reader status are clear.

## Accessibility and Responsive Layout

- [ ] Keyboard reaches every selector, command, form field, and dialog action.
- [ ] Escape/cancel closes confirmations without deleting.
- [ ] Focus returns to a durable command after close/delete.
- [ ] Status updates are announced by a screen reader.
- [ ] Focus outline is clearly visible.
- [ ] Labels and error states are understandable without colour alone.
- [ ] No horizontal page scrolling at 320px.
- [ ] No horizontal page scrolling at 768px.
- [ ] No horizontal page scrolling at 1280px.
- [ ] Text, controls, tables, dialogs, and notices do not overlap at those widths.

Evidence location: `[pending]`