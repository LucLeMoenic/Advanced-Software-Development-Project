# Release 0 Brief

In this assessment, each team will establish the foundation of an Agentic AI software application by applying the concepts covered in Weeks 1–5.

The project focuses on:

- Agentic AI software development
- Development environment setup using Visual Studio
- Microservices architecture and service design
- AI-Mode implementation using Ollama and approved Large Language Models (Llama and Qwen). You may use other AI agents for implementation and review as a team. Identify the selected Agentic AI in the group registration form.
- Docker containerisation and Docker Compose integration
- DevOps and GitHub Actions workflow automation
- An Agentic AI loop to review the database, implementation, microservices architecture, and DevOps pipeline
- Collaborative software engineering practices

Refer to the ASD 2026 Project SpecificationsDownload ASD 2026 Project Specifications for the complete project requirements, implementation requirements, and submission requirements.

> **Important:** Individual features are assessed only as part of the integrated group application. Non-integrated features receive 0 marks.

> **Important:** All team members must attend the Week 6 showcase. Failure to attend results in 0 marks.

## 2. Team Responsibilities

### Group Responsibilities

| Responsibility | Description |
|---|---|
| GitHub Repository | Shared repository containing source code, workflows, containers, agentic loop, and documentation. |
| Development Environment | Configure and maintain a common development environment using VS Code. |
| Model/API Integration | Configure AI-Mode using Ollama and approved open-source LLMs. |
| Microservices Architecture | Design the integrated frontend, backend/API, and database microservices. |
| Integrated Software Foundation | Develop the integrated multi-container Agentic AI software application. |
| DevOps and CI/CD Workflows | Implement GitHub Actions build and validation workflows. |
| YAML Workflow Files | Create and maintain the required GitHub Actions workflow files. |
| AI-Assisted Development | Apply AI-assisted software engineering throughout development and implement an agentic loop with specialised prompts. |
| Project Evidence | Maintain GitHub commit history, agentic workflow logs, and contribution logs. |
| Showcase Video | Include a 10-minute software demonstration video URL in the technical report. |

 
### Individual Responsibilities

| Responsibility | Description |
|---|---|
| Frontend Microservice | Develop and maintain the assigned frontend microservice. |
| Backend/API Microservice | Develop and maintain the assigned backend/API microservice. |
| Database Microservice | Develop and maintain the assigned database microservice. |
| CRUD Operations | Implement Create, Read, Update, and Delete operations. |
| AI Integration | Integrate the backend/API with AI-Mode and approved LLMs. |
| Repository Contribution | Integrate assigned components into the shared GitHub repository. |
| GitHub Actions Workflow | Implement and maintain the assigned GitHub Actions workflow. |
| Showcase Demonstration | Demonstrate the assigned feature in the integrated application as part of the showcase video. |
| Project Evidence | Maintain GitHub commits and contribution logs. |

 
## 3. Submission

| Deliverable | Description |
|---|---|
| Technical Report | One group PDF technical report submitted by 30 August 2026, 11:59 PM Sydney time. |
| Working Software | Shared GitHub repository containing the integrated Release 0 software project and required artefacts. |
| Presentation | Demonstration of the integrated application: 10-minute presentation video plus 5 minutes of Q&A. |
| Showcase Video URL | Include a group demonstration video URL in the technical report, up to 10 minutes. All students must participate and demonstrate their working feature as part of the integrated software. The video must also demonstrate deployment steps, AI-agentic workflow execution, and the CI/CD pipeline. |

 
## 4. Deliverables

### Technical Report

| Section | Description |
|---|---|
| Project Overview | Project overview, team members, and individual feature allocation. |
| Project Analysis and Planning | Apply Agile methods to plan the team project. Each student must contribute functional and non-functional requirements to the sprint backlog, prepare an individual feature plan and risk management plan, complete conceptual, ERD, logical, and physical data designs, and contribute to the overall project plan. |
| Repository Structure | Shared GitHub repository structure and project organisation. |
| Individual Software Architecture | Architecture diagram for each student's frontend, backend/API, and database microservices. |
| Integrated Software Architecture | Release 0 integrated software architecture diagram. |
| Docker Compose Architecture | Docker Compose architecture diagram. |
| DevOps Pipeline Architecture | DevOps architecture, including GitHub, GitHub Actions, Docker Compose, integrated microservices, and AI-Mode. |
| Agentic AI Workflow | Plan → Act → Observe → Adapt workflow diagram. |
| GitHub Actions Workflows | Description of `student-1.yml` to `student-5.yml` workflow files. |
| Implementation Summary | Summary of the Release 0 implementation. |
| GitHub Actions Evidence | Evidence of successful GitHub Actions workflow execution. |
| Docker Compose Evidence | Evidence of successful Docker Compose execution. |
| Agentic Loop Workflow Record | Contribution to shared agentic loop development, personal prompt assets, and the review record. |
| Known Issues and Limitations | Outstanding Release 0 issues and limitations. |
| GitHub Commit Logs | GitHub commit history demonstrating individual contributions. |
| Contribution Logs | Individual contribution records. |
| Showcase Video URL | Published demonstration video URL for the working integrated microservices, CI/CD pipeline, and AI-agentic loop workflow. |

 
### Agentic AI Workflows

| Item | Description |
|---|---|
| AI-Mode | AI-Mode implementation using Ollama and approved open-source LLMs. |
| Ollama Runtime | Configuration of the Ollama runtime. |
| Approved Open-Source LLM | Configuration and use of Llama and Qwen. |
| AI Request Workflow | Frontend → Backend/API → Ollama → LLM workflow. |
| Plan → Act → Observe → Adapt | Implementation of the shared Agentic AI workflow. |

 
### DevOps and CI/CD Workflows

| Item | Description |
|---|---|
| GitHub Repository | Shared GitHub repository for source code management. |
| GitHub Actions Workflow Files | `student-1.yml`, `student-2.yml`, `student-3.yml`, `student-4.yml`, and `student-5.yml`. |
| Build and Validation | Automated build and validation of assigned microservices. |
| Docker Compose | Execution of the integrated multi-container application. |
| Workflow Execution | Evidence of successful GitHub Actions workflow execution. |

### Working Software

| Item | Description |
|---|---|
| Frontend Microservice | Implemented and integrated frontend microservices for each assigned feature. |
| Backend/API Microservice | Implemented and integrated backend/API microservices with AI-Mode for each assigned feature. |
| SQLite Database Microservice | Implemented and integrated SQLite database microservices supporting CRUD operations for each assigned feature. |
| Shared HTMX Index | Implement a shared containerised HTMX `index.html` that provides a single entry point and routes users to all five student frontend microservices. |
| Cross-Feature Database API Integration | Each database container owns and manages its assigned SQLite schema and exposes CRUD operations through its database API service. Other backend/API microservices must retrieve or update its data exclusively through the exposed API and must not access its SQLite file, tables, or schema directly. |
| Docker Containerisation | Containerise all frontend, backend/API, database, shared front-end index container, and AI services using Docker. |
| Docker Compose Integration | Execute the integrated team application using one shared Docker Compose configuration. |

 
## 5. Marking Criteria

| No. | Criteria | Description | Marks |
|---:|---|---|---:|
| 1 | Project Setup | Shared repository structure, integrated microservices, populated databases, AI-Mode, GitHub Actions workflows, Docker Compose, unified `index.html`, shared CSS theme, and required project directories are correctly configured. | 2 |
| 2 | Service Implementation | Frontend, backend/API, and database containers are integrated and operational within the group application. | 2 |
| 3 | AI-Mode Integration | AI-Mode using Ollama and the approved LLMs is integrated into the application and callable from the frontend. | 2 |
| 4 | Agentic AI Workflow | The Plan → Act → Observe → Adapt loop is implemented, demonstrated in the terminal, and logged in the technical report. | 2 |
| 5 | Prompt Engineering and Context Management | Prompt engineering artefacts and AI context management used during software development are documented. | 2 |
| 6 | DevOps and GitHub Actions | GitHub Actions workflows build and validate each student's assigned microservices in the shared repository. | 2 |
| 7 | Docker Compose Integration | One shared Docker Compose configuration builds and runs all individual microservices and shared AI services as one group application. | 2 |
| 8 | Working Software | The assigned feature provides working CRUD operations through the frontend, backend/API, and database microservices. | 2 |
| 9 | Technical Report | Includes the repository structure, software architecture, DevOps pipeline architecture, Docker Compose architecture, local testing evidence, GitHub Actions evidence, Docker Compose evidence, application screenshots, AI workflow logs, commit logs, contribution logs, attendance checkpoints, and known issues. | 2 |
| 10 | Project Demonstration | Demonstrates, in a published video of up to 10 minutes, the complete assigned feature, AI-Mode integration, and the Agentic AI loop within the integrated group application. | 2 |
| **Total** |  |  | **20** |

### Rubric

| Criteria | Full Marks (2 pts) | Average (1 pt) | No Marks (0 pts) |
|---|---|---|---|
| Project Setup | Repository structure, project directories, integrated microservices, populated databases, AI-Mode, GitHub Actions workflows, Docker Compose, unified `index.html`, and shared CSS theme are correctly configured. | Most required project setup components are configured with minor omissions or integration issues. | Project setup is incomplete or does not satisfy the Release 0 requirements. |
| Service Implementation | Frontend, backend/API, and database microservices are integrated and operational within the group application. | Services are partially implemented or partially integrated. | Services are missing or non-functional. |
| AI-Mode Integration | AI-Mode is integrated using Ollama and an approved LLM and is callable from the frontend. | AI-Mode is partially configured or only partially functional. | AI-Mode is missing or non-functional. |
| Agentic AI Workflow | The Plan → Act → Observe → Adapt workflow is implemented, demonstrated, and documented. | The workflow is partially implemented or only partially demonstrated. | The workflow is missing or non-functional. |
| Prompt Engineering and Context Management | Prompt engineering artefacts and AI context management are documented and clearly support software development. | Basic prompt engineering or context management evidence is provided. | No prompt engineering or context management evidence is provided. |
| DevOps and GitHub Actions | GitHub Actions workflows successfully build and validate the assigned microservices. | GitHub Actions workflows are partially implemented or partially operational. | GitHub Actions workflows are missing or non-functional. |
| Docker Compose Integration | One shared Docker Compose configuration successfully builds and runs the integrated group application. | Docker Compose executes only part of the integrated application. | Docker Compose configuration is missing or non-functional. |
| Working Software | The assigned feature provides fully functional CRUD operations through the frontend, backend/API, and database microservices. | CRUD functionality is partially implemented or partially operational. | CRUD functionality is missing or non-functional. |
| Technical Report | The technical report includes all required Release 0 documentation and evidence. | The technical report is incomplete or contains minor omissions. | The technical report is missing or substantially incomplete. |
| Project Demonstration | The assigned feature, AI-Mode integration, and Agentic AI workflow are successfully demonstrated. | The demonstration is partially completed or demonstrates limited functionality. | The demonstration is not completed or is non-functional. |

**Total points: 20**