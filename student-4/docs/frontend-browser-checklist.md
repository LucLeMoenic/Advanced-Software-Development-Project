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