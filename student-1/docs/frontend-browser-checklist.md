# Chunk 6 Frontend Browser Checklist

Use this checklist against the running Compose application. Record screenshots or video paths beside each completed item; do not mark an item complete from component tests alone.

## Automated Baseline

- [x] `npm --prefix student-1/frontend test` - 7/7 component tests pass.
- [x] `npm --prefix student-1/frontend run build` - strict TypeScript check and Vite production build pass.
- [x] `git diff --check` - no whitespace errors.

## Search and Result States

- [ ] Submit valid criteria once and confirm the button disables while loading.
- [ ] Confirm AI-ranked cards show rank, name, destination, nightly price, capacity, and reason.
- [ ] Force Ollama failure and confirm results remain visible with the fallback notice.
- [ ] Submit criteria with no eligible candidates and confirm the explicit empty state.
- [ ] Stop the database service and confirm the dependency error is visible and focused.
- [ ] Submit invalid fields and confirm field messages, focus movement, and no completed search.

## History CRUD

- [ ] Confirm new history appears first.
- [ ] Reopen a saved search and confirm the stored snapshot appears without a new ranking request.
- [ ] Rename the displayed search and confirm both history and result headings update.
- [ ] Cancel rename and confirm focus returns to Rename.
- [ ] Reject delete confirmation and confirm the item remains.
- [ ] Confirm deletion and verify the item disappears and focus moves to a stable history target.

## Accessibility

- [ ] Complete search, reopen, rename, cancel, and delete using only the keyboard.
- [ ] Confirm focus is visibly outlined on every interactive control.
- [ ] Confirm a screen reader announces loading, validation, result, rename, and delete status changes.
- [ ] Confirm all controls have an accessible name and error text is associated with its field.
- [ ] Confirm no user or model text is rendered as HTML.

## Responsive Widths

At each width, use maximum-length or long unbroken destination, title, accommodation name, and reason values.

| Width | No horizontal page scroll | Form usable | History actions usable | Result text contained | Evidence |
|---:|---|---|---|---|---|
| 320px | [ ] | [ ] | [ ] | [ ] | Pending |
| 768px | [ ] | [ ] | [ ] | [ ] | Pending |
| 1280px | [ ] | [ ] | [ ] | [ ] | Pending |
