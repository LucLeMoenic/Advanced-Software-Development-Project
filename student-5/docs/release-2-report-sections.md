# Student 5 - Release 2 Report Sections (draft)

Draft of my individual sections for the group PDF (Release 2 brief, section 4), for the
group to merge. Only "Report text" counts towards the 3000-word limit. "Figures and
evidence" and "Before submission" are notes for whoever assembles the PDF.

**Word count of "Report text": 498** (headings excluded; counted with a whitespace split
of the section's paragraphs, so `PUT /api/destinations/<id>` counts as two words).

## Report text

### Student 5 - Travel Logistics & Advisory (Alex Chen)

**Design flow.** The Student 5 page reaches `student5-frontend` (nginx) through the shared
gateway. nginx proxies to the Flask backend, the only Student 5 code that calls the SQLite
database service and the native AI services. The trip readiness review builds bounded
evidence from the destination's stored records and sends it to the Multi-Agent Server
(Planner, Worker, automatic checks, Reviewer). The page polls every 2 s, shows the plan,
checklist and findings, and records a human decision in the server's hash-chained audit
log. Each AI service has its own flag, checked before any network call (Figure S5-1).

**Pre-commit security testing.** Ruff security rules and detect-secrets passed on all 111
Student 5 files, and pip-audit on both requirements files. pip-audit found
`PYSEC-2026-1845` in pytest, so both pins were raised to `>=9.0.3` and the Student 5
exception was removed. 369 test `assert`s, 2 container binds to `0.0.0.0` and 5
constant-only SQL f-strings were accepted with reasons; the 4 detect-secrets candidates
were hashes. A deliberately insecure commit was blocked.

**Post-commit endpoint tests.** `student-5.yml` tests `POST /api/destinations` and
`PUT /api/destinations/<id>` with all four AI flags off: 13 mocked tests
(forwarding, error relay, database-down `503`) and 12 live checks
against the running containers. Run 39698558980 on `main`: 13 passed, 12/12 checks, JUnit
artifact published. Four injected bugs were all caught.

**Local deployment.** Docker Compose ran 17 containers. Ollama, MCP and RAG (started by
the launcher in terminal 1) and the Multi-Agent Server (terminal 2) ran natively. Through the gateway, the advisory returned in 3.4 s, the
MCP visa tool and a cited RAG answer succeeded, and destination CRUD passed.

**Multi-Agent workflow.** Five real workflows ran on live data. Thailand was run entirely
in the browser (22 s to human review, partially accepted) and Vietnam from the terminal.
On Indonesia the Reviewer passed a checklist that only copied the records. I corrected all
five items, and the server re-checked the correction. Final `GET /audit/verify`: valid, 50
entries.

**Cloud deployment.** `cloud-deployment.yml` run 39741981906 deployed with AI off.
`check_student5` confirmed the four `*_disabled` responses, then create, read, update,
delete and `404` through the public HTTPS gateway: PASS. The deployed page showed the
"switched off" notices. Limits: the shared runbook says this run deployed before the CI
gate required all six workflows, and persistence and rollback evidence is with the cloud
workflow owner. The later protected-AI run (39893640923), now the live deployment, passed
Student 5's advisory, MCP and RAG checks, and a readiness review reached human review;
its decision is pending.

**Agentic-loop reviews.** `review-testing`, `review-cloud` and `review-multi-agent` each
returned ACCEPT with one suggestion. I rejected the testing finding, which misread the
pytest floor. My release decision on the cloud review was `changed`: screenshots
were added and the remaining gaps stated. The multi-agent review was also `changed`
(report corrected). The loop refused four reviewer attempts that echoed
prompt examples or produced malformed findings; they are kept as evidence.

**Contribution.** 19 commits in 6 pull requests (#129, #132, #133, #135, #137, #145) on
https://github.com/LucLeMoenic/Advanced-Software-Development-Project, each with
prompt-log and review-record entries.

## Figures and evidence (not counted)

Paths are relative to `student-5/docs/`.

| Figure or table | Source |
|---|---|
| S5-1 Release 2 design flow | `architecture.md`, "Release 2" - "Design flow" (Mermaid; export as an image) |
| S5-2 Local and cloud boundary | `architecture.md`, "Local and cloud boundary" |
| S5-3 DevOps flow, if the group figure does not already show Student 5 | `architecture.md`, "DevOps flow" |
| Pre-commit results table | `evidence/release-2/precommit-security-report.md`, "Results" |
| Endpoint CI run | `evidence/release-2/endpoint-tests/08-ci-run-overview.jpg`, `09-ci-job-summary.jpg` |
| Local multi-terminal logs | `evidence/release-2/local-deployment-report.md`, "What ran, and where" |
| Multi-Agent UI | `evidence/release-2/multi-agent-server/screenshots/05`-`08` |
| Audit verification | `evidence/release-2/multi-agent-server/transcripts/audit-verify-final.txt` |
| Cloud page and AI-off notices | `evidence/release-2/cloud/05`-`07`, `cloud/03-cloud-smoke.txt` |
| Loop review outputs and logs | `evidence/release-2/loop/README.md`, `loop/*-review-record.json` |
| Contribution log | `contribution-log.md`, "Release 2" |

## Before submission (not counted)

Not in the repository yet. Do not claim these until they exist:

- An AI-off baseline `cloud-deployment.yml` run after the CI-gate fix (cloud workflow
  owner). If one succeeds, replace run 39741981906 in "Cloud deployment" and drop the
  limit sentence.
- A human decision on the cloud readiness review `wf-20261023T035316Z-6feb1b81`, with a
  screenshot, if the group claims bonus B4 for Student 5. No protected-AI Student 5
  screenshot exists yet.
- The group showcase video URL and the group number for the PDF filename.
- Figure numbers, which depend on the group's layout.
