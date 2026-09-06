# Known Issues and Limitations

Student 5 (Alex Chen), Release 0. Honest limitations of the delivered feature.
Each entry says what the problem is, what it costs, and what would fix it.

## Development and tooling

### The two pytest suites cannot be run in one invocation

`student-5/database/app.py` and `student-5/backend/app.py` are both modules
named `app`, and each suite's `conftest.py` imports `app`. A single combined
`pytest` run collides on that name during collection and fails.

**Cost:** anyone running `pytest student-5/` sees a confusing import error
rather than 94 passing tests. Both suites are green on their own.

**Workaround, and what CI does:** run them separately, each from its own
directory - `.github/workflows/student-5.yml` has two distinct test steps for
exactly this reason. Commands are in `testing-evidence.md`.

**Fix, not done:** rename the modules (`database_app.py`, `backend_app.py`), or
add a `pyproject.toml` per service so each has its own import root. Deferred
because both changes touch the Dockerfiles' entrypoints and the module name is
referenced from `create_app` imports across the backend; the cost of the bug is
a documented command, and the cost of the fix is a rebuild of both images late
in the release.

## Service boundaries and error handling

### The backend forwards database 5xx verbatim

`relay()` in `backend/app.py` forwards the database service's status code
unchanged. That is deliberately right for 4xx - a `404` is a real answer, and
re-deciding validation in two places creates two sources of truth. But it means
a `500` originating **inside the database service** reaches the frontend
indistinguishable from a `500` originating in the backend itself.

**Cost:** the frontend cannot tell "the backend broke" from "the backend's
dependency broke". Only the transport-failure case is distinguished, via
`DatabaseUnavailable` -> `503 {"error": "database service unavailable"}`. A
reader of the page is largely protected, because the `/ui/` fragment layer shows
a readable notice either way; an operator or another service reading the JSON
API is not.

**Fix, not done:** have `relay()` map an upstream 5xx to `502 Bad Gateway` with
a body naming the dependency, keeping 2xx and 4xx passthrough as-is. It is a
small change in one function, but it alters the passthrough contract that other
students may already be reading, so it is being carried into Release 1 rather
than changed the night before submission.

## AI behaviour

### The model occasionally adds an unrecorded detail

The advisory prompt grounds every fact in the stored rows and instructs the
model that every fact, number and length of stay it states must appear in the
recorded text. It is not perfect. During development the model twice added a
six-month passport-validity rule to Japan's advisory - a rule that belongs to
Indonesia's seeded note - and once wrote "up to 90 days" for a destination where
no such number is recorded.

Tightening the instruction to cover the whole class (every *number* must appear
above) removed both. A negative instruction made it worse rather than better:
naming the concept primed it. Low-severity drift of this kind is still possible
on any given generation.

**Cost:** an advisory can contain a plausible sentence that no stored row
supports. In a travel-documents context that is the most consequential failure
mode this feature has, which is why it is mitigated in three independent places
rather than one.

**Mitigations in place:** grounding is asserted by tests in
`backend/tests/test_advisory.py`; the Smartraveller disclaimer is rendered as
markup in `advisory_result.html` rather than requested from the model, so it
appears whether or not the model complies; and the seed data itself carries a
comment stating it is illustrative.

**Not fixed:** there is no post-generation check that every claim in the output
traces back to a stored row. A validator of that kind is Release 1 work.

### Advisories are generated fresh every time and are not stored

There is no cache. Two generations for the same destination will differ. This is
a deliberate choice - stored advice would go stale silently when a visa rule is
corrected - but it means the advisory in a screenshot cannot be reproduced
exactly, and every request pays the full generation cost.

## User interface

### The destination dropdown does not refresh after a create or delete

`#destination-select` loads its options once, on page load
(`hx-trigger="load"`). The Manage destinations section writes through
`/ui/destinations...` endpoints that re-render the manage table, but nothing
re-triggers the options fetch.

**Cost:** after adding a destination it is visible in the manage table but not
selectable in the picker until the page is reloaded. After deleting one, the
picker still offers it, and choosing it produces a "could not be found" notice
from the visa panel rather than a crash.

**Fix, not done:** have the write endpoints return an `HX-Trigger` response
header and give the select an `hx-trigger` on that event, so one server response
refreshes both. Roughly a three-line change on each side. Deferred to keep the
manage-write path unchanged through the release-evidence window; the admin
section is collapsed by default and is not on the traveller's path.

### `shared/style.css` references were removed from Student 5

The frontend originally linked `/shared/style.css`, which was not present in the
Student 5 image and broke the page under CI. The reference was removed in commit
`9e894c9` and the feature now ships its own `frontend/style.css`.

**Cost:** Student 5's styling is a *reimplementation* of Student 2's design
system, not a shared import. If the team's tokens change, this file has to be
updated by hand and can drift.

**Fix, not done:** a genuinely shared stylesheet would need to be copied into
each frontend image at build time or served from the shared nginx with a stable
path. That is a group-level decision, not a Student 5 one.

## Agentic loop

### The 3B reviewer echoes the worked examples in its prompt

`reviewer-llama32-v2.md` fixed the shared prompt's template-echoing defect, but
the model now reproduces the prompt's *worked examples* instead. On the recorded
run it returned a REQUIRED finding about a division-by-zero on a `count`
variable - copied word-for-word from Example 2 - describing code that does not
exist in the proposal.

**Cost:** a reviewer verdict cannot be trusted on its own at this model size.
The finding is well-formed and confidently stated, and only inspection against
the actual proposal reveals it as an echo.

**Why this is survivable:** the loop does not self-apply. `ParseVerdict` caught
the model's first attempt at pairing that finding with an `ACCEPT` verdict, the
run stopped awaiting human finalisation, and the human Adapt phase rejected the
finding on inspection. Full analysis in `review-record.md`; candidate fixes for
a v3 prompt in `prompt-engineering.md`.

**Not fixed:** the residual echo remains. The two candidate mitigations -
examples drawn from an obviously unrelated domain, and requiring `Evidence:` to
open with a verbatim quotation from the proposal - are untested.

### Only one agentic-loop run has saved artefacts

Three earlier attempts (see `prompt-log.md`) failed or were abandoned before any
record was written, so they are documented from the working session with no
evidence file to cite.

## Release 0 scope

- **No MCP tools.** `get_weather` and `check_visa_requirement` are Release 1;
  nothing in this release depends on them.
- **No authentication and no per-user data.** Anyone reaching the page can edit
  the destination list.
- **No live data.** Visa requirements, weather notes and transit options are
  seeded sample data written from an Australian passport holder's perspective.
  They are illustrative for the assignment and must not be relied on for travel.
- **Single SQLite file, synchronous HTTP throughout.** Sized for a local
  classroom demonstration, not for concurrent production use.
- **No RAG, no multi-agent application behaviour, no cloud deployment.**
