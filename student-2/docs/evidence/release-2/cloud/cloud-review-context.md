# Student 2 cloud review evidence

## Deployment

- Protected AI deployment: [Cloud Deployment run 39893640923](https://github.com/LucLeMoenic/Advanced-Software-Development-Project/actions/runs/39893640923), completed successfully on `main` at `4c1e71acd34793ca5a7a2171c64c3d73dbaf137d` (PR #150).
- The run's exact-revision CI gate, preparation, build, deploy, HTTPS readiness, protected AI smoke, and evidence-upload steps all completed successfully.
- The retained [`cloud-smoke-39893640923.txt`](cloud-smoke-39893640923.txt) records Student 2 capability/generation and trip/stop CRUD checks. The actual Student 2 multi-agent workflow reached human review, but no human approval was submitted. Persistence across redeploy and rollback were explicitly not established.
- The [earlier baseline run 39741981906](https://github.com/LucLeMoenic/Advanced-Software-Development-Project/actions/runs/39741981906) succeeded on `851bdd7f4a7bc455e751b020c05a977608989e3a`; the cloud runbook says it predates the corrected CI gate, so it is not complete current-baseline acceptance evidence.

## Report sections 4-6

- Section 4 describes the AWS EC2 host, Caddy as the only public TLS gateway, internal application services, and the exact-revision CI/deployment flow. The successful AI run confirms that the application profile deployed and smoke checks completed, but is not evidence of a fresh AI-off baseline.
- Section 5 documents the group scan policy, but the Student 2 row and its hook-output figure are still placeholders. Earlier prompt-log notes mention selected Ruff and detect-secrets passes; a complete Student 2 scan transcript including dependency audit is not attached here.
- Section 6 still has a Student 2 run-URL placeholder. The [Student 2 CI run 39893621503](https://github.com/LucLeMoenic/Advanced-Software-Development-Project/actions/runs/39893621503) completed successfully on the same SHA. Its retained [`student2-endpoints-39893621503.xml`](student2-endpoints-39893621503.xml) records seven passing create/update endpoint tests (zero failures or skips), including persistence, invalid input, AI-disabled smoke, cleanup and explicit dependency-outage cases.

The local endpoint transcript is copied from the workflow artifact `student-2-tests-4c1e71acd34793ca5a7a2171c64c3d73dbaf137d`. The cloud transcript is copied from artifact `cloud-ai-evidence-4c1e71acd34793ca5a7a2171c64c3d73dbaf137d`.
