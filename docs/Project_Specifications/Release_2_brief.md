# Release 2 Brief

Assessment 3 continues from the completed Release 1 application. Each team will complete and deploy its integrated Agentic AI application by extending Release 1 with a shared Multi-Agent Server, additional agentic-loop review modes, pre-commit security testing, post-commit CI/CD endpoint testing, and cloud deployment to Microsoft Azure or Amazon Web Services (AWS).

This brief sets out the Release 2 assessment requirements. The integrated group application is the unit of assessment: an individual feature that is not integrated receives zero for the relevant working-software criteria.

## 1. Release 2 Scope

The project focuses on:

- Completing the integrated application from Release 1 while retaining its existing functionality and AI services.
- Retaining the shared non-containerised local AI-Mode, MCP Server, RAG Server, and agentic loop.
- Implementing one shared, non-containerised local Multi-Agent Server that coordinates Planner, Worker, and Reviewer agents.
- Including human review in the Multi-Agent workflow.
- Extending the shared agentic loop with Multi-Agent Workflow Review, Testing Report Review, and Cloud Deployment Report Review modes while retaining Release 1 review modes.
- Running local pre-commit security scans as part of the code commit workflow.
- Testing two endpoint functions of each student’s assigned backend/API service through that student’s post-commit CI/CD workflow.
- Running the complete integrated application locally, with the Multi-Agent Server and other AI services available through the backend/API where required.
- Deploying the integrated application to either Microsoft Azure or AWS.
- Keeping AI-Mode, MCP, RAG, and the Multi-Agent Server disabled by default in the required cloud deployment. The frontend, backend/API, database, and core CRUD functions must remain operational.
- Providing optional cloud AI-service and cloud-security extensions for bonus marks.

### Cloud Baseline

The required cloud deployment keeps AI-Mode, MCP, RAG, and the Multi-Agent Server disabled by default. Cloud AI services are optional extensions and are assessed only under the bonus criteria. Their optional enablement must not be required for the baseline cloud application to function.

## 2. Team Responsibilities

### Group Responsibilities

| Responsibility | Description |
| --- | --- |
| Release 2 completion | Extend the completed Release 1 application with the Multi-Agent Server, Release 2 agentic-loop review modes, security and endpoint testing, and local and cloud deployment. |
| Release 1 AI services | Retain and integrate the shared non-containerised local AI-Mode, MCP Server, and RAG Server. Do not add these services as Docker Compose services. |
| Multi-Agent Server | Implement one shared, non-containerised local server for all student features. It must coordinate Planner, Worker, and Reviewer agents, be callable through the integrated application, and be runnable from a terminal. |
| Agent roles | Define the Planner, Worker, and Reviewer responsibilities, the information passed between them, and the evidence used by each stage. |
| Human review | Provide a human decision point in the local Multi-Agent workflow for approval, correction, partial acceptance, or rejection. |
| Shared agentic loop | Retain Release 1 review modes and add Multi-Agent Workflow Review, Testing Report Review, and Cloud Deployment Report Review. The loop remains a shared, non-containerised local service. |
| Pre-commit security testing | Configure local commit hooks to run Ruff security rules, detect-secrets, and pip-audit or approved equivalents. |
| Post-commit CI/CD testing | Each student’s assigned `student-x.yml` workflow must test two endpoint functions of that student’s assigned backend/API service after code is pushed to the shared repository. |
| Local deployment | Run the integrated application locally. Frontend, backend/API, and database microservices run through Docker Compose; AI-Mode, MCP, RAG, the Multi-Agent Server, and the shared agentic loop remain non-containerised local services. |
| Cloud platform | Select one cloud platform for the group: Microsoft Azure or AWS. |
| Cloud baseline deployment | Deploy the integrated application with AI-Mode, MCP, RAG, and the Multi-Agent Server disabled by default. Keep the frontend, backend/API, database, and core CRUD functionality operational. |
| Cloud deployment workflow | Implement `cloud-deployment.yml` and reusable deployment scripts or Infrastructure as Code for the selected platform. |
| Cloud deployment review | Use the shared agentic-loop Cloud Deployment Report Review mode to review deployment evidence, generate a review/validation log, and support a final human release decision. |
| Technical report | Submit one group PDF report of no more than 3000 words, with the required Release 2 evidence. |
| Showcase | Produce one group demonstration video of no more than 10 minutes and include its URL in the technical report. |

### Individual Responsibilities

| Responsibility | Description |
| --- | --- |
| Assigned microservices | Complete and maintain the assigned frontend, backend/API, and database microservices as part of the integrated Release 2 application. |
| Release 1 integration | Retain the assigned feature’s integration with the shared local AI-Mode, MCP Server, and RAG Server. |
| Multi-Agent integration | Integrate the assigned feature with the shared local Multi-Agent Server and demonstrate the Planner, Worker, Reviewer, and human-review workflow. |
| Agentic-loop reviews | Contribute evidence for the Multi-Agent Workflow Review, Testing Report Review, and Cloud Deployment Report Review. |
| Pre-commit security testing | Configure and run the required local security scans for the assigned contribution; resolve or document relevant findings. |
| Post-commit CI/CD testing | Implement automated tests for two endpoint functions of the assigned backend/API service and run them through the assigned `student-x.yml` workflow. |
| GitHub Actions workflow | Update and maintain the assigned `student-x.yml` workflow so its Release 2 build, validation, and endpoint tests execute successfully. |
| Local deployment | Demonstrate the assigned feature in the integrated local application with the non-containerised local AI services available as required. |
| Cloud deployment | Demonstrate the assigned feature in the integrated group cloud application. AI-Mode, MCP, RAG, and Multi-Agent remain disabled by default in the baseline deployment. |
| Repository contribution | Commit the Release 2 source code, tests, workflows, deployment artefacts, configuration, documentation, and required evidence to the shared repository. |
| Showcase and project evidence | Demonstrate the assigned contribution and maintain identifiable commits, test results, and contribution records. |

## 3. Submission

Submit one group technical report (one submission per group) by **25 October 2026, 11:59 PM AEST**.

- **Report filename:** `group-<your group number>.pdf`
- **Maximum report length:** 3000 words
- **Showcase video:** One group video, maximum 10 minutes; include its URL in the report.
- **Working software:** The shared repository must contain the complete integrated Release 2 application and its required source code, tests, workflows, deployment artefacts, review outputs, evidence, and documentation.

All students must participate in the showcase. The demonstration must cover the integrated application locally and in the cloud, the Multi-Agent workflow, pre-commit security scans, post-commit endpoint tests, and the agentic-loop review modes. Each student must explain and defend their Release 2 contribution during the showcase and Q&A.

## 4. Technical Report Requirements

The group report must include the following sections and evidence:

| Section | Required content |
| --- | --- |
| Project overview | Project and team overview, individual feature allocation, and an explanation of how Release 2 extends the completed Release 1 application. |
| Final repository structure | Repository structure identifying the Release 1 artefacts and Release 2 Multi-Agent Server, tests, workflows, deployment scripts, agentic-loop additions, and evidence. |
| Release 2 design flow | Updated application flow: frontend UI → backend/API → database; retained AI-Mode, MCP, and RAG flows; and Multi-Agent flow: frontend UI → backend/API → Multi-Agent Server → Planner → Worker → Reviewer → Human Review → frontend response. |
| Cloud deployment and CI/CD architecture | The selected Azure or AWS reference architecture and DevOps deployment flow. Show frontend, backend/API, database, hosting, networking/endpoints, source control, pre-commit scans, GitHub Actions, each student’s two endpoint tests, Docker build/validation, `cloud-deployment.yml`, and cloud deployment. |
| Pre-commit security testing | A report of Ruff security scans, detect-secrets, and pip-audit (or approved equivalents) run locally during the commit workflow, including results and relevant findings. |
| Post-commit CI/CD testing | One report per student showing automated tests for two endpoint functions of that student’s assigned backend/API service, together with the assigned workflow run evidence. |
| Testing Review | The agentic-loop Testing Report Review output based on the pre-commit security and post-commit CI/CD reports, with its review/validation log. |
| Local deployment evidence | A report showing the integrated application running locally with the non-containerised Multi-Agent Server. Include multi-service system-testing logs from multiple terminals. |
| Cloud deployment report and review | Evidence of successful deployment to the selected Azure or AWS environment, access to the deployed frontend and core application functions, the agentic-loop Cloud Deployment Report Review and validation log, and the final human release decision. |
| Multi-Agent workflow evidence | Evidence of a completed Planner → Worker → Reviewer → Human Review workflow, including workflow history and coordination/audit logs. |
| GitHub commit logs | The shared GitHub repository URL and identifiable Release 2 commit history for each student. |
| Contribution logs | Each student’s Release 2 contribution record, summarising completed work and responsibilities. |
| Bonus evidence | Evidence for each cloud AI service enabled and each cloud-security control claimed for bonus marks. |
| Showcase video URL | The published group demonstration video URL (maximum 10 minutes). |

## 5. Release 2 Workflows and Deployment

### Agentic AI Workflows

| Component or mode | Requirement |
| --- | --- |
| AI-Mode | Retain the shared non-containerised local AI-Mode from Release 0. |
| MCP Server | Retain the shared non-containerised local MCP Server from Release 1. |
| RAG Server | Retain the shared non-containerised local RAG Server from Release 1. |
| Multi-Agent Server | Provide one shared, non-containerised local server coordinating the Planner, Worker, and Reviewer agents. |
| Planner Agent | Develops the workflow plan, identifies required evidence, and defines the work to be performed. |
| Worker Agent | Performs the assigned task using the supplied application evidence. |
| Reviewer Agent | Checks the Worker’s output against the plan and evidence, identifies risks, and provides recommendations. |
| Human Review | Makes the final approval, correction, partial-acceptance, or rejection decision. |
| Multi-Agent Workflow Review | Reviews Multi-Agent workflow evidence and produces implementation/review recommendations and a review/validation log. |
| Testing Report Review | Reviews pre-commit security-scan and post-commit CI/CD test evidence and produces a review/validation log. |
| Cloud Deployment Report Review | Reviews cloud deployment and validation evidence, produces a review/validation log, and supports the human release decision. |

### Software Testing

| Activity | Requirement |
| --- | --- |
| Pre-commit security scans | Run local scans as part of the commit workflow. Required coverage includes Ruff security rules, detect-secrets, and pip-audit or approved equivalents. |
| Post-commit endpoint tests | Each student’s assigned `student-x.yml` workflow tests two endpoint functions of that student’s assigned backend/API service after code is pushed to the shared repository. |
| Testing Review | The shared agentic loop reviews security-scan and endpoint-test results and generates the corresponding review/validation log. |
| Testing evidence | Store the scan and endpoint-test results, CI/CD execution logs, and agentic-loop review/validation log in identifiable project files and include the required evidence in the technical report. |

### DevOps and CI/CD

- Maintain one shared GitHub repository containing the integrated Release 2 application, tests, workflows, deployment configuration and scripts, and required evidence.
- Maintain the assigned `student-x.yml` workflow for each student.
- Run local pre-commit security scans in the commit workflow.
- Run each student’s two required endpoint tests through that student’s `student-x.yml` workflow after pushing changes.
- Implement `cloud-deployment.yml` to deploy the integrated group application to the selected Azure or AWS environment after required CI/CD validation succeeds.
- Provide reusable deployment scripts or Infrastructure as Code and successful execution evidence.

### Local and Cloud Deployment

| Environment | Requirement |
| --- | --- |
| Local | Run frontend, backend/API, and database microservices through Docker Compose. Keep AI-Mode, MCP, RAG, the Multi-Agent Server, and the shared agentic loop as non-containerised local services. Where required, make the AI services accessible from the frontend through the backend/API. |
| Cloud baseline | Deploy to Azure or AWS. The frontend UI, backend/API, database, and core CRUD functions must work. AI-Mode, MCP, RAG, and the Multi-Agent Server must be disabled by default. |
| Optional cloud extensions | Selected AI services may be enabled for bonus marks. Cloud endpoint and data security controls may also be implemented for bonus marks. Each claimed extension must be functional, demonstrated, and supported by report evidence. |

## 6. Marking Criteria

The assessment is worth **30 marks**. Each criterion is worth 3 marks.

| No. | Criterion | Full-mark requirement | Marks |
| ---: | --- | --- | ---: |
| 1 | Integrated Local Application and AI Services | The complete integrated application runs locally. Every student’s frontend, backend/API, and database microservices are operational and support required CRUD functionality. Release 0/1 AI-Mode, MCP, and RAG remain integrated as shared local services, together with the Release 2 Multi-Agent Server. | 3 |
| 2 | Multi-Agent Server and Workflow | The shared local Multi-Agent Server successfully executes Planner → Worker → Reviewer → Human Review through the terminal and frontend UI. The report includes workflow history and coordination/audit evidence. | 3 |
| 3 | Pre-Commit Security Testing | Local commit hooks run Ruff security rules, detect-secrets, and pip-audit or approved equivalents. The report includes the security-testing report and results. | 3 |
| 4 | Post-Commit CI/CD Endpoint Testing | Each assigned `student-x.yml` workflow tests two endpoint functions of that student’s backend/API service. The report includes test results and successful workflow evidence. | 3 |
| 5 | Cloud Deployment Scripts | Reusable scripts or Infrastructure as Code for the selected Azure or AWS environment successfully support deployment of the integrated Release 2 application. The report includes the artefacts and execution evidence. | 3 |
| 6 | Cloud Deployment CI/CD Workflow | `cloud-deployment.yml` deploys the integrated application through GitHub Actions after required CI/CD validation succeeds. The report includes successful deployment workflow logs. | 3 |
| 7 | Integrated Cloud Application – CRUD | The integrated application is deployed to Azure or AWS. The frontend UI, backend/API, database, and required CRUD functions are operational. AI-Mode, MCP, RAG, and Multi-Agent are disabled by default. | 3 |
| 8 | Agentic-Loop Review Modes | The shared local agentic loop runs Multi-Agent Workflow Review, Testing Report Review, and Cloud Deployment Report Review against the required evidence and generates the corresponding review/validation logs. Include the outputs in the report. | 3 |
| 9 | Technical Report and Evidence | The report includes the required Release 2 design and cloud/CI architecture, testing and deployment reports, Multi-Agent evidence, review outputs and logs, GitHub URL, contribution logs, and project evidence. | 3 |
| 10 | Showcase and Q&A | All students participate in the maximum 10-minute showcase and Q&A. Demonstrate the Multi-Agent workflow through the frontend, local and cloud application, pre-commit scans, post-commit endpoint testing, and agentic-loop review modes. Each student explains and defends their contribution. | 3 |
|  | **Total** |  | **30** |

### Performance Levels

Apply the following scale to each 3-mark criterion:

| Mark | Rating | General standard |
| ---: | --- | --- |
| 3 | Full Marks | The required functionality is complete, integrated, operational, demonstrated, and supported by the specified evidence. |
| 2 | Mostly Complete | The requirement is substantially operational, with minor integration, execution, configuration, coverage, or evidence limitations. |
| 1 | Partial | The requirement is only partly implemented or demonstrated; significant functionality or evidence is missing. |
| 0 | No Marks | The required functionality or evidence is missing, non-operational, or not integrated into the group application. |

Criterion-specific full-mark requirements are stated in the marking table above. A feature that is not integrated into the group application receives zero for the relevant working-software criteria.

## 7. Bonus Marks – Cloud Extension (Maximum +6)

Bonus marks are awarded only after the required baseline cloud deployment is operational. The AI services remain disabled by default in the baseline deployment. Each bonus item must be deployed or implemented, functional, demonstrated, and supported by evidence in the technical report and showcase.

| No. | Bonus criterion | Requirement | Bonus |
| --- | --- | --- | ---: |
| B1 | Cloud AI-Mode | Enable and demonstrate AI-Mode in Azure or AWS, including a successful interaction through the application. | +1 |
| B2 | Cloud MCP | Enable and demonstrate the MCP Server in Azure or AWS, including a successful MCP tool interaction through the application. | +1 |
| B3 | Cloud RAG | Enable and demonstrate the RAG Server in Azure or AWS, including a grounded response using retrieved context. | +1 |
| B4 | Cloud Multi-Agent Server | Enable and demonstrate the Multi-Agent Server in Azure or AWS, including a successful Planner → Worker → Reviewer workflow. | +1 |
| B5 | Cloud Endpoint Security | Implement and demonstrate security controls protecting exposed cloud frontend/API endpoints, with configuration and validation evidence. | +1 |
| B6 | Cloud Data Security | Implement and demonstrate controls protecting cloud application data, secrets, credentials, and stored data, with configuration and validation evidence. | +1 |
|  | **Maximum Bonus** |  | **+6** |

**Assessment base mark:** 30. **Maximum bonus:** +6.
