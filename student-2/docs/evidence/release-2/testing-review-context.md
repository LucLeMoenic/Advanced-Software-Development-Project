# Student 2 testing evidence for review

## Endpoint CI

- **Exact source SHA:** `4c1e71acd34793ca5a7a2171c64c3d73dbaf137d` (PR #150).
- **Successful Student 2 CI run on that exact SHA:** [run 39893621503](https://github.com/LucLeMoenic/Advanced-Software-Development-Project/actions/runs/39893621503).
- **Endpoint JUnit artifact from run 39893621503 / that same SHA:** [`student2-endpoints-39893621503.xml`](cloud/student2-endpoints-39893621503.xml). The XML records seven tests, zero failures and zero skips. The cases cover POST `/api/trips` persistence and invalid input; PUT `/api/trips/{id}` persistence, stop preservation, invalid/missing records; disabled-mode smoke/cleanup; and explicit dependency outages on both endpoints.
- The named endpoint-test step succeeded. The full student workflow's relevant service tests, shared Multi-Agent regression tests, loop-mode tests, cloud-profile tests and local integration/disabled-mode/persistence smoke steps also succeeded.

## Security scan evidence

- Student 2's prompt log reports that on 21 October Ruff security and detect-secrets passed. Other entries report Ruff security checks on selected changed Python or deployment-gate code.
- These are historical summaries, not a retained complete scan transcript tied to commit `4c1e71a`. No Student 2-specific detect-secrets output, pip-audit result/exceptions, installed-hook check or actual commit-hook execution transcript is attached. The technical report's Student 2 security row and hook figure remain placeholders.
- Do not infer pip-audit passed from Ruff/detect-secrets results or from CI success. The repository hook audits requirements files in the commit; the supplied evidence does not show a Student 2 requirements-file audit result for this commit.

## Evidence boundary

This review can verify the run and endpoint JUnit artifact. It cannot turn historical scan notes into current commit-specific security evidence. Local review/test evidence is not a substitute for the linked successful remote run.
