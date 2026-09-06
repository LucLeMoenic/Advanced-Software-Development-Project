# Release 0 Deliverables

An index of the Release 0 deliverables required by
[`../Project_Specifications/Release_0_brief.md`](../Project_Specifications/Release_0_brief.md),
mapped to where the evidence currently lives in this repository.

This is a map, not a claim of completeness. Rows say what exists in the
repository today. Anything not yet present is marked **Missing** with the exact
artefact needed and where it must come from - do not cite a Missing row in the
technical report until the artefact exists.

## Release 0 documents in this folder

| Document | Covers |
|---|---|
| [`integrated-architecture.md`](integrated-architecture.md) | Release 0 integrated software architecture: shared home page, all five feature sets, shared Ollama and agentic loop, request flow, database ownership rule |
| [`compose-architecture.md`](compose-architecture.md) | Docker Compose architecture: every service, ports, healthchecks, `depends_on` conditions, volumes, init containers |
| [`devops-pipeline.md`](devops-pipeline.md) | DevOps pipeline: commit to GitHub, the five path-filtered workflows, and local Compose execution with AI-Mode |

## Technical report section map

| Report section | Where the evidence lives | Status |
|---|---|---|
| Project Overview | [`../../README.md`](../../README.md) - overview and features table with owner, gateway path and ports | Present; two owner names outstanding, see Missing artefacts |
| Project Analysis and Planning | Per student: `student-N/docs/requirements.md`, `feature-plan.md` (`featureplan.md` for Student 3), `risk-plan.md` (`riskplan.md` for Student 3), and the data design inside `student-N/docs/architecture.md` (Student 5: [`student-5/docs/data-design.md`](../../student-5/docs/data-design.md)) | Partly present; sprint backlogs and an overall project plan outstanding |
| Repository Structure | [`../../README.md`](../../README.md) repository structure section | Present |
| Individual Software Architecture | `student-N/docs/architecture.md` for each of the five students | Present |
| Integrated Software Architecture | [`integrated-architecture.md`](integrated-architecture.md) | Present |
| Docker Compose Architecture | [`compose-architecture.md`](compose-architecture.md); source of truth is [`../../docker-compose.yml`](../../docker-compose.yml) | Present |
| DevOps Pipeline Architecture | [`devops-pipeline.md`](devops-pipeline.md) | Present |
| Agentic AI Workflow | [`../../ai-services/agentic-loop/README.md`](../../ai-services/agentic-loop/README.md), the prompts in [`../../ai-services/agentic-loop/prompts/`](../../ai-services/agentic-loop/prompts), and the Plan/Act/Observe/Adapt diagram in [`student-5/docs/architecture.md`](../../student-5/docs/architecture.md) | Present |
| GitHub Actions Workflows | [`../../.github/workflows/`](../../.github/workflows) plus the per-workflow description in [`devops-pipeline.md`](devops-pipeline.md) and the CI table in [`../../README.md`](../../README.md) | Present |
| Implementation Summary | Per student: `student-N/README.md` and `student-N/docs/feature-plan.md`; Students 1, 2 and 4 also keep a Release 0 checklist | Present |
| GitHub Actions Evidence | [`student-5/docs/evidence/ci-run-green.png`](../../student-5/docs/evidence/ci-run-green.png) only | Missing for Students 1, 2, 3 and 4 |
| Docker Compose Evidence | [`student-5/docs/evidence/compose-ps.txt`](../../student-5/docs/evidence/compose-ps.txt) and [`compose-build.txt`](../../student-5/docs/evidence/compose-build.txt) - Student 5 services only | Missing for the full 20-service stack and for Students 1 to 4 |
| Agentic Loop Workflow Record | [`../agentic-loop-records/`](../agentic-loop-records) - one finalised record, `20260906T053024Z-ad4b32c67df446e8af9e1fca8cc22044.json`, for a Student 5 task. Personal prompt assets: [`student-5/docs/prompt-library/reviewer-llama32-v2.md`](../../student-5/docs/prompt-library/reviewer-llama32-v2.md); [`student-1/docs/prompt-library/README.md`](../../student-1/docs/prompt-library/README.md). Review records: `student-N/docs/review-record.md` (`reviewrecord.md` for Student 3) | Present for Student 5; missing a finalised record for Students 1, 2, 3 and 4 |
| Known Issues and Limitations | `student-2/docs/known-issues.md`, `student-3/docs/knownissues.md`, `student-4/docs/known-issues.md`, `student-5/docs/known-issues.md` | Missing a dedicated Student 1 document |
| GitHub Commit Logs | Git history of this repository; per-student commit and pull-request tables in the contribution logs below | Present in git; Student 1 has no contribution-log document |
| Contribution Logs | `student-2/docs/contribution-log.md`, `student-3/docs/contributionlog.md`, `student-4/docs/contribution-log.md`, `student-5/docs/contribution-log.md` | Missing for Student 1 |
| Showcase Video URL | Not in the repository | Missing |
| Local testing evidence | [`student-5/docs/testing-evidence.md`](../../student-5/docs/testing-evidence.md) and [`student-5/docs/evidence/`](../../student-5/docs/evidence); browser screenshots in [`student-3/docs/evidence/`](../../student-3/docs/evidence). Students 1, 2 and 4 document manual browser checklists but store no captured output | Partly present |
| Attendance checkpoints | Not in the repository | Missing |

## Per-student evidence matrix

`y` means the artefact exists in the repository. Blank means it does not.

| Artefact | S1 | S2 | S3 | S4 | S5 |
|---|:--:|:--:|:--:|:--:|:--:|
| `README.md` for the feature | y | y | y | y | y |
| `requirements.md` | y | y | y | y | y |
| Feature plan | y | y | y | y | y |
| Risk plan | y | y | y | y | y |
| Sprint backlog document | y |  |  |  | y |
| Architecture diagram | y | y | y | y | y |
| Data design with ERD | y | y | y | y | y |
| Prompt log | y | y | y | y | y |
| Review record | y | y | y | y | y |
| Prompt-engineering / context-management document |  |  |  |  | y |
| Personal prompt library | y |  |  |  | y |
| Known issues |  | y | y | y | y |
| Contribution log |  | y | y | y | y |
| Captured test / CI / Compose evidence files |  |  | y (browser screenshots) |  | y |

File names differ between students: Student 3 uses `featureplan.md`,
`riskplan.md`, `knownissues.md`, `reviewrecord.md` and `contributionlog.md`;
everyone else uses hyphenated names. Student 1's data design sits inside
`architecture.md`; Student 5 keeps a separate `data-design.md`.

## Missing artefacts (TODO)

Each item names the artefact and where it must come from. None of these should be
described as existing until it does.

1. **Student 2 owner name.** Not recorded anywhere in `student-2/README.md` or
   `student-2/docs/`. The only source in the repository is the GitHub account
   `LucLeMoenic` in the commit history. Source: Student 2 adds their full name to
   `student-2/README.md`; the features table in the root `README.md` is then
   updated from it.
2. **Student 3 full owner name.** `student-3/docs/contributionlog.md` gives the
   first name "Khushi" only. Source: Student 3 adds their full name to
   `student-3/README.md`.
3. **Sprint backlog documents for Students 2, 3 and 4.** The brief requires each
   student to contribute functional and non-functional requirements to a sprint
   backlog. Students 1 and 5 have `sprint-backlog.md`; Students 2, 3 and 4 have
   requirements documents but no backlog document. Source: each of those students
   adds `student-N/docs/sprint-backlog.md`.
4. **Overall project plan.** The brief asks each student to contribute to an
   overall project plan. No group-level plan document exists under `docs/`.
   Source: the group, as `docs/release-0/project-plan.md` or equivalent.
5. **Student 1 known-issues document.** Source: Student 1, as
   `student-1/docs/known-issues.md`. Limitations are currently scattered through
   `feature-plan.md`, `requirements.md` and `release-0-full-marks-checklist.md`.
6. **Student 1 contribution log.** Every other student has one. Source: Student 1,
   as `student-1/docs/contribution-log.md`.
7. **GitHub Actions run evidence for Students 1, 2, 3 and 4.** Only Student 5 has
   a captured successful run (`ci-run-green.png`). Source: each student captures
   the run URL or a screenshot of their own green workflow run and stores it under
   `student-N/docs/evidence/`.
8. **Docker Compose evidence for the full integrated stack.** The only captured
   Compose output covers the three Student 5 services. Source: a `docker compose
   ps` capture of all 20 services healthy after `docker compose up -d --build
   --wait`, stored under `docs/release-0/` or a student evidence folder.
9. **Finalised agentic-loop records for Students 1, 2, 3 and 4.**
   `docs/agentic-loop-records/` holds exactly one finalised record, produced for a
   Student 5 task. Source: each remaining student runs the shared loop on a real
   bounded change and finalises the record per
   [`../agentic-loop-records/README.md`](../agentic-loop-records/README.md).
10. **Prompt-engineering and context-management documents for Students 1 to 4.**
    Marking criterion 5 asks for these explicitly. Only Student 5 has a dedicated
    `prompt-engineering.md`; the others have prompt logs. Source: each student.
11. **Application screenshots for Students 1, 2 and 4.** Criterion 9 lists
    application screenshots. Students 3 and 5 have captured screenshots; the
    others document manual browser checklists but store no images. Source: each
    student, under `student-N/docs/evidence/`.
12. **Showcase video URL.** Not present. Source: the group, once the video is
    published; it belongs in the technical report and can be indexed here.
13. **Week 6 attendance checkpoints.** Not present. Source: the group.

## Related

- Root [`README.md`](../../README.md) - how to run the whole application
- [`../agentic-loop-records/README.md`](../agentic-loop-records/README.md) - what a report-ready loop record must contain
- [`../../ai-services/README.md`](../../ai-services/README.md) - shared AI services
