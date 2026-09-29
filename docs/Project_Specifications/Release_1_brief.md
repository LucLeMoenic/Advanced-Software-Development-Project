# 1. Release 1 Brief

In this assessment, each team will extend the Release 0 Agentic AI software application by integrating one shared local Model Context Protocol (MCP) server, one shared local Retrieval-Augmented Generation (RAG) server, and one shared local agentic loop. The AI Mode, MCP server, RAG server, and agentic loop are not containerised.

The project focuses on:

- Extend the integrated Release 0 microservices application by adding shared local MCP and RAG modes to the existing shared local AI-Mode.
- One shared non-containerised local MCP Server used by all student features
- One shared non-containerised local RAG Server used by all student features
- Frontend UI access to the shared MCP and RAG services through each student feature’s backend/API
- Grounded AI responses based on retrieved context, with source citations and a confidence category
- The existing Release 0 Docker Compose configuration continues to run the containerised feature microservices and is not extended to include AI-Mode, MCP, RAG, or the agentic loop
- Updated GitHub Actions workflows for the student feature microservices, with AI-Mode, MCP, and RAG disabled during CI/CD
- One shared non-containerised local agentic loop, extended with MCP and RAG validation modes in addition to the existing Release 0 modes

> **Important Rule:** An individual feature is assessed only as part of the integrated group application. A feature that is not integrated into the group application will receive zero for the Working Software criterion.

> **Important Rule:** All team members must attend the Week 9 showcase. Failure to attend results in 0 marks.

> **Important Rule:** ONE report submission per group (submitted by one person from the group). Duplicate group submission will not be marked.

Report file name: `group-<your group number>.pdf`

## 2. Team Responsibilities

### Group Responsibilities

| Responsibility | Description |
| --- | --- |
| Release 0 Extension | Extend the integrated Release 0 application while retaining each student’s containerised frontend, backend/API, and database microservices. Each feature’s frontend must access the non-containerised local AI Mode through its backend/API. |
| MCP Server | Implement and integrate one shared non-containerised MCP Server running on localhost and used by all student features. |
| RAG Server | Implement and integrate one shared non-containerised RAG Server running on localhost and used by all student features. |
| Grounded AI Responses | Generate and display answers using context retrieved from the shared RAG server. Each answer must include source citations and a confidence category. If relevant context is unavailable, display an insufficient-context response instead of generating an unsupported answer. |
| Microservices Integration | Integrate the shared MCP and RAG services into every student feature, with access provided through its frontend and backend/API. |
| Shared Agentic Loop | Extend the Release 0 agentic loop with MCP and RAG validation modes in addition to the existing Release 0 modes. The shared agentic loop must run locally and must not be containerised. |
| Docker Compose Integration | The Release 0 `docker-compose.yml` must remain operational and deploy the integrated containerised application, including each student’s frontend, backend/API, and database microservices. It must be updated to configure the backend/API microservices to connect to the shared local MCP and RAG servers, following the existing connection approach used for the local AI-Mode. AI-Mode, the MCP server, the RAG server, and the agentic loop must remain non-containerised and must not be defined as services in `docker-compose.yml`. |
| GitHub Actions Workflows | Maintain the assigned `student-x.yml` workflow to build and validate each student’s updated feature microservices. The application must retain its MCP and RAG integration, with both modes disabled during CI/CD execution. |
| Local MCP and RAG Integration Validation | On localhost, demonstrate at least one successful MCP interaction and one successful RAG interaction through each student feature’s frontend UI and backend/API. The MCP interaction must return a valid tool result. The RAG interaction must return a grounded answer with source citations and a confidence category. Run the shared agentic loop in both MCP and RAG validation modes and capture the outputs. |
| Technical Report | Submit one group PDF report (3000 words max + diagrams) containing the required Release 1 evidence. Report file name: `group-<your group number>.pdf` |
| Project Evidence | Include mandatory individual contribution logs, link to the showcase video and a link to the shared GitHub repository. The evidence must allow the tutor to verify both the quality of each student’s implemented contribution and the corresponding Release 1 commits. |
| Showcase Video | Include one showcase video URL in the technical report. The video must not exceed 10 minutes and must demonstrate the running application features showing MCP and RAG interactions through each feature’s frontend UI and backend/API, local terminal validation of the MCP and RAG servers, and execution of the shared agentic loop in both MCP and RAG validation modes. |

### Individual Responsibilities

| Responsibility | Description |
| --- | --- |
| Assigned Microservices | Extend the assigned Release 0 features, including its containerised frontend, backend/API, and database microservices. The existing feature functionality must remain operational after the Release 1 extension. |
| Frontend MCP and RAG Access | Provide access from the assigned feature’s frontend UI to the shared local MCP and RAG servers through its backend/API. Demonstrate at least one successful MCP interaction and one successful RAG interaction through the frontend UI. |
| Repository Contribution | Integrate the assigned Release 1 feature code, configuration, validation evidence, and MCP/RAG integration into the shared repository. |
| GitHub Actions Workflow | Update and maintain the assigned `student-x.yml` workflow to build and validate the updated frontend, backend/API, and database microservices. The feature must retain its MCP and RAG integration, with both modes disabled during CI/CD execution. |
| Project Evidence | Maintain an individual contribution log and identifiable Release 1 GitHub commits for the assigned feature. The evidence must demonstrate the quality of the contribution and the corresponding repository activity. |

## 3. Submission

| Deliverable | Description |
| --- | --- |
| Technical Report | Submit one group PDF technical report by **4 October 2026 at 11:59 PM AEST** (the group report must be submitted by one person in the group). The report (3000 words max + diagrams) must include the shared GitHub repository link, the showcase video URL, and all required Release 1 evidence. Report file name: `group-<your group number>.pdf` |
| Working Software | Provide an updated shared GitHub repository containing the complete integrated Release 1 application, each student’s containerised frontend, backend/API, and database microservices, the shared local MCP and RAG server implementations, the shared agentic loop, GitHub Actions workflows, configuration files, validation outputs, and required project evidence. The tutor must be able to access the repository and verify each student’s commits. |
| Showcase Video URL | Include one showcase video URL in the technical report. The video must not exceed 10 minutes and must demonstrate the running application features, including MCP and RAG interactions through each feature’s frontend UI and backend/API, local terminal validation of the MCP and RAG servers, and execution of the shared agentic loop in both MCP and RAG validation modes. |

## 4. Deliverables

### Technical Report

| Section | Description |
| --- | --- |
| Project Overview and Release 1 Scope | Provide a concise overview of the Release 0 application and the Release 1 extension. Explain the updates for each assigned features, and responsibilities for the shared MCP server, RAG server, and agentic loop. Clearly distinguish each student’s responsibilities from the shared group responsibilities. |
| Release 1 Requirements | Define the functional requirements for the shared local MCP and RAG servers, grounded RAG responses, MCP and RAG interactions through each feature’s frontend UI and backend/API, and the shared agentic loop with MCP and RAG validation modes. |
| Non-Functional Requirements | Define and justify the non-functional requirements relevant to the shared MCP and RAG services, including security, MCP tool boundaries, RAG grounding and traceability, reliability, performance, usability, maintainability, interoperability, and availability. Requirements must be measurable where practical. |
| Release 1 Architecture | Develop and document the overall software architecture, integrating the containerised Release 0 application and its existing local AI-Mode with the Release 1 shared local MCP server, RAG server, and agentic loop validation modes. Show the components, connections, and containerisation boundaries. |
| MCP and RAG Design | Develop and explain a flow diagram covering the frontend and backend/API interactions, the RAG retrieval and grounded-response process, the MCP tool layer, the tools registered and exposed through the shared MCP server, and their interactions with the application. |
| Validation and Results | Explain the Release 1 validation approach and summarise the results. Include evidence of:<br><br>- MCP and RAG interactions through every feature’s frontend UI and backend/API, local terminal validation, grounded RAG responses, and shared agentic-loop execution in both validation modes<br>- Successful `student-x.yml` workflow runs with MCP and RAG disabled during CI/CD<br>- Successful deployment using the Release 0 `docker-compose.yml` with the required local MCP and RAG connection configuration |
| Individual Contributions | Provide one contribution log for each student, identifying the assigned feature updates, completed Release 1 work, integration and validation activities, and corresponding GitHub commits. |
| Repository and Showcase Links | Provide the tutor-accessible shared GitHub repository link and the published showcase video URL. The video must not exceed 10 minutes and must satisfy the Showcase Video requirements specified under Submission. |
| Known Issues and Limitations | Document outstanding Release 1 issues and limitations, including local execution constraints for MCP, RAG, and the agentic loop |

### Agentic AI Workflows

| Item | Description |
| --- | --- |
| AI-Mode | The Release 0 AI-Mode must remain integrated and operational in each student feature after the Release 1 extension. |
| MCP Request Flow | Each feature’s frontend UI must send MCP requests through its backend/API to the shared non-containerised local MCP server. The MCP server must execute the appropriate registered tool and return a structured result for display in the requesting frontend UI. |
| RAG and Grounded Response Flow | Each feature’s frontend UI must send RAG queries through its backend/API to the shared non-containerised local RAG server. The RAG server must retrieve relevant project context and use the selected local LLM or AI model to generate a grounded response with source citations and a confidence category. If relevant context is unavailable, the frontend UI must display an insufficient-context response. |
| Shared Agentic Loop | Extend the Release 0 agentic loop with separate MCP and RAG validation modes. The shared agentic loop must run locally, remain non-containerised, and produce validation outputs for both modes. |

### DevOps and CI/CD Workflows

| Item | Description |
| --- | --- |
| GitHub Repository | Maintain one shared GitHub repository containing the complete integrated Release 1 application, updated student feature microservices, shared MCP and RAG implementations, shared agentic loop, configuration files, validation evidence, and assigned `student-x.yml` workflows. |
| GitHub Actions Workflows | Each student must update and maintain their assigned `student-x.yml` workflow to build and validate their frontend, backend/API, and database microservices. MCP and RAG integration must be retained but disabled during CI/CD execution. Provide a successful run link or execution log for each workflow. |
| Docker Compose Deployment | The Release 0 `docker-compose.yml` must remain operational and deploy the integrated containerised student feature microservices. It must include the connection configuration required to access the shared local MCP and RAG servers. AI-Mode, the MCP server, the RAG server, and the agentic loop must run locally and must not be defined as Docker Compose services. |

### Working Software

| Item | Description |
| --- | --- |
| Student Feature Microservices | Each student’s assigned Release 0 feature must remain operational as containerised frontend, backend/API, and database microservices. The feature must retain its existing functionality and AI-Mode while adding frontend access, through its backend/API, to the shared local MCP and RAG servers. |
| Shared MCP Server | One shared non-containerised MCP server must run locally and provide registered tools for all student features. Each feature must invoke these tools through its frontend UI and backend/API and display the returned tool result. |
| Shared RAG Server and Grounded Responses | One shared non-containerised RAG server must run locally and provide retrieval and grounded-response operations for all student features. Each feature’s frontend UI must display grounded answers with source citations and a confidence category. When relevant context is unavailable, it must display an insufficient-context response. |
| Docker Compose Deployment | The Release 0 `docker-compose.yml` must remain operational and deploy the integrated containerised student feature microservices. It must include the connection configuration required for the backend/API microservices to access the shared local MCP and RAG servers. AI-Mode, the MCP server, the RAG server, and the agentic loop must remain non-containerised and must not be defined as Docker Compose services. |

## 5. Marking Criteria

| No. | Criteria | Description | Marks |
| --- | --- | --- | ---: |
| 1 | Release 1 Project Setup and Architecture | The shared repository must retain the Release 0 student feature microservices and include one shared non-containerised local MCP server, RAG server, and agentic loop. The repository structure, configuration, service boundaries, frontend access through each feature’s backend/API, and local LLM or AI-model connections must be correctly established. The Technical Report must include the updated repository structure, an overall Release 1 software architecture diagram, and an MCP and RAG interaction-flow diagram. | 3 |
| 2 | Student Feature Microservices | Each student’s assigned containerised frontend, backend/API, and database microservices must remain integrated and operational after the Release 1 extension. Existing Release 0 functionality and local AI-Mode must continue to work. The Technical Report must include validation evidence for every student feature, including frontend execution, backend/API responses, and database operations. | 3 |
| 3 | MCP Server Integration | The shared MCP server must run locally, expose registered tools, enforce defined tool boundaries, accept valid requests, and return structured results. Every student feature must access the shared MCP server from its frontend UI through its backend/API. The Technical Report must include the MCP interaction flow, registered tools, inputs and outputs, access boundaries, terminal validation, and frontend interaction evidence for every feature. | 3 |
| 4 | RAG Integration and Grounded Responses | The shared RAG server must run locally, retrieve relevant project context, and support every student feature from its frontend UI through its backend/API. Grounded responses must use retrieved context, display source citations and a confidence category, and return an insufficient-context response when relevant context is unavailable. The Technical Report must include the RAG interaction flow, knowledge sources, retrieval evidence, terminal validation, frontend interactions, grounded-response examples, and insufficient-context validation. | 3 |
| 5 | Shared Agentic Loop | Extend the Release 0 agentic loop with MCP and RAG validation modes. The shared agentic loop must run locally and remain non-containerised. The Technical Report must include the captured outputs from both validation modes. | 3 |
| 6 | DevOps and GitHub Actions | Each student must update and maintain their assigned `student-x.yml` workflow to build and validate their frontend, backend/API, and database microservices. MCP and RAG integration must be retained but disabled during CI/CD execution. The Technical Report must include a successful run link or execution log for every assigned workflow. | 3 |
| 7 | Docker Compose Deployment | The Release 0 `docker-compose.yml` must remain operational and deploy the integrated containerised student feature microservices. It must configure the backend/API microservices to access the shared local MCP and RAG servers. AI-Mode, the MCP server, the RAG server, and the agentic loop must remain non-containerised and must not be defined as Docker Compose services. | 3 |
| 8 | Integrated Working Software | The complete Release 1 group application must run successfully as one integrated system. Every assigned feature must remain functional and provide frontend access to the shared MCP and RAG services through its backend/API. The Technical Report must include an integration-validation summary and selected evidence showing that all student features, MCP interactions, RAG interactions, and existing Release 0 functionality work together. | 3 |
| 9 | Technical Report and Project Evidence | The report must document the Release 1 scope, requirements, software architecture, MCP and RAG interaction design, validation results, known issues and limitations. It must include the shared repository link, showcase video URL, validation evidence, contribution logs, and identifiable Release 1 commits for every student. | 3 |
| 10 | Release 1 Demonstration and Q&A | Each student must demonstrate, explain, and defend their Release 1 contribution during the Q&A. Responses must demonstrate understanding of their assigned feature, MCP and RAG integration, validation evidence, and contribution to the integrated group application. | 3 |
| **Total** | | | **30** |

## Rubric

### Assignment 2 - Release 1 Rubrics

#### Release 1 Project Setup and Architecture

This criterion is linked to a learning outcome.

The shared repository must retain the Release 0 student feature microservices and include one shared non-containerised local MCP server, RAG server, and agentic loop. The repository structure, configuration, service boundaries, frontend access through each feature’s backend/API, and local LLM or AI-model connections must be correctly established. The Technical Report must include the updated repository structure, an overall Release 1 software architecture diagram, and an MCP and RAG interaction-flow diagram.

| Pts | Rating | Description |
| ---: | --- | --- |
| 3 | Full Marks | 2 pts: The repository structure, shared components, configuration, connections, and service boundaries are complete and correct. 1 pt: The Technical Report includes the updated repository structure, overall software architecture diagram, and MCP and RAG interaction design diagram. |
| 2 | Good | 1 pt: The project setup and architecture are substantially complete but contain minor technical omissions. 1 pt: The required repository structure and diagrams are included in the Technical Report. |
| 1 | Basic | The project setup or architecture is partially completed, or the required Technical Report evidence is incomplete or inaccurate. |
| 0 | No Marks | The required project setup and architecture are missing or not demonstrated. |

**3 pts**

#### Student Feature Microservices

This criterion is linked to a learning outcome.

Each student’s assigned containerised frontend, backend/API, and database microservices must remain integrated and operational after the Release 1 extension. Existing Release 0 functionality and local AI-Mode must continue to work.

| Pts | Rating | Description |
| ---: | --- | --- |
| 3 | Full Marks | The assigned frontend, backend/API, and database microservices are fully integrated and operational. Existing Release 0 functionality and local AI-Mode continue to work correctly. |
| 2 | Good | The assigned microservices are integrated and substantially operational but contain minor integration or functionality issues. |
| 1 | Basic | The assigned microservices are only partially integrated or operational, with significant functionality issues. |
| 0 | No Marks | The assigned microservices are missing, non-operational, or not integrated into the group application. |

**3 pts**

#### MCP Server Integration

This criterion is linked to a learning outcome.

The shared non-containerised MCP server must run locally, expose registered tools, enforce defined tool boundaries, accept valid requests, and return structured results. Every student feature must access the shared MCP server from its frontend UI through its backend/API.

| Pts | Rating | Description |
| ---: | --- | --- |
| 3 | Full Marks | 2 pts: The shared MCP server is fully operational, exposes registered tools with defined boundaries, and returns valid structured results through every feature’s frontend UI and backend/API. 1 pt: The Technical Report includes the MCP interaction flow, registered tools, inputs and outputs, access boundaries, terminal validation, and frontend interaction evidence for every feature. |
| 2 | Good | 1 pt: The MCP integration is substantially operational but contains minor tool, boundary, or feature-integration issues. 1 pt: The required MCP interaction flow and validation evidence are included in the Technical Report. |
| 1 | Basic | The MCP server or its integration with the student features is only partially operational, or the required Technical Report evidence is incomplete or inadequate. |
| 0 | No Marks | The shared MCP server is missing, non-operational, or not integrated with the student features. |

**3 pts**

#### RAG Integration and Grounded Responses

This criterion is linked to a learning outcome.

The shared non-containerised RAG server must run locally, retrieve relevant project context, and support every student feature from its frontend UI through its backend/API. Grounded responses must use retrieved context, display source citations and a confidence category, and return an insufficient-context response when relevant context is unavailable.

| Pts | Rating | Description |
| ---: | --- | --- |
| 3 | Full Marks | 2 pts: The shared RAG server retrieves relevant context and returns grounded responses through every feature’s frontend UI and backend/API, including source citations, a confidence category, and insufficient-context handling. 1 pt: The Technical Report includes the RAG interaction flow, knowledge sources, retrieval evidence, terminal validation, frontend interactions, grounded-response examples, and insufficient-context validation. |
| 2 | Good | 1 pt: The RAG integration is substantially operational but contains minor retrieval, citation, confidence, or feature-integration issues. 1 pt: The required RAG interaction flow and validation evidence are included in the Technical Report. |
| 1 | Basic | The RAG retrieval or grounded-response functionality is only partially operational, or the required Technical Report evidence is incomplete or inadequate. |
| 0 | No Marks | The shared RAG server is missing or non-operational, or grounded responses are not demonstrated. |

**3 pts**

#### Shared Agentic Loop

This criterion is linked to a learning outcome.

The shared Release 0 agentic loop must be extended with MCP and RAG validation modes. It must run locally and remain non-containerised. The Technical Report must include the captured outputs from both validation modes.

| Pts | Rating | Description |
| ---: | --- | --- |
| 3 | Full Marks | 2 pts: The shared agentic loop runs successfully in both MCP and RAG validation modes and produces valid outputs for each mode. 1 pt: The captured outputs from both validation MCP and RAG modes are included in the Technical Report. |
| 2 | Good | 1 pt: Both validation modes are substantially operational but contain minor execution or validation issues. 1 pt: Outputs from both modes are included in the Technical Report. |
| 1 | Basic | Only one validation mode or part of the shared agentic loop is operational, or the required Technical Report evidence is incomplete or inadequate. |
| 0 | No Marks | The shared agentic loop is not extended with operational MCP and RAG validation modes. |

**3 pts**

#### DevOps and GitHub Actions

This criterion is linked to a learning outcome.

Each student must update and maintain their assigned student-x.yml workflow to build and validate their frontend, backend/API, and database microservices. MCP and RAG integration must be retained but disabled during CI/CD execution. The Technical Report must include a successful run link or execution log for every assigned workflow.

| Pts | Rating | Description |
| ---: | --- | --- |
| 3 | Full Marks | 2 pts: Every assigned `student-x.yml` workflow successfully builds and validates the corresponding feature microservices with MCP and RAG disabled during CI/CD execution. 1 pt: Successful workflow run links or execution logs and evidence of the disabled MCP and RAG configuration are included in the Technical Report. |
| 2 | Good | 1 pt: The workflows are substantially operational but contain minor build, validation, or configuration issues. 1 pt: The required workflow logs or run links and configuration evidence are included in the Technical Report. |
| 1 | Basic | Only some assigned workflows are operational, or the required Technical Report evidence is incomplete or inadequate. |
| 0 | No Marks | The assigned GitHub Actions workflows are missing or non-operational. |

**3 pts**

#### Docker Compose Integration

This criterion is linked to a learning outcome.

The Release 0 docker-compose.yml must remain operational and deploy the integrated containerised student feature microservices. It must configure the backend/API microservices to access the shared local MCP and RAG servers. AI-Mode, the MCP server, the RAG server, and the agentic loop must remain non-containerised and must not be defined as Docker Compose services.

| Pts | Rating | Description |
| ---: | --- | --- |
| 3 | Full Mark | 2 pts: The Release 0 `docker-compose.yml` successfully deploys all integrated student feature microservices and correctly configures backend/API access to the shared local MCP and RAG servers. AI-Mode, MCP, RAG, and the agentic loop remain outside Docker Compose. 1 pt: Docker Compose execution logs, running-container status, and successful application-access evidence are included in the Technical Report. |
| 2 | Good | 1 pt: The Docker Compose deployment is substantially operational but contains minor deployment, configuration, or connectivity issues. 1 pt: The required deployment and application-access evidence is included in the Technical Report. |
| 1 | Basic | Only part of the containerised application is successfully deployed, local service access is incomplete, or the required Technical Report evidence is inadequate. |
| 0 | No Marks | The Release 0 Docker Compose deployment is missing or non-operational. |

**3 pts**

#### Integrated Working Software

This criterion is linked to a learning outcome.

The complete Release 1 group application must run successfully as one integrated system. Every assigned feature must remain functional and provide frontend access to the shared local MCP and RAG services through its backend/API. The Technical Report must include an integration-validation summary and selected evidence showing that all student features, MCP interactions, RAG interactions, and existing Release 0 functionality work together.

| Pts | Rating | Description |
| ---: | --- | --- |
| 3 | Full Marks | 2 pts: The integrated application and all student features are fully operational, with successful MCP and RAG interactions through every feature’s frontend UI and backend/API. 1 pt: The Technical Report includes an integration-validation summary and evidence of the running features, existing Release 0 functionality, MCP interactions, and RAG interactions. |
| 2 | Good | 1 pt: The integrated application is substantially operational but contains minor feature or MCP/RAG integration issues. 1 pt: The required integration-validation summary and supporting evidence are included in the Technical Report. |
| 1 | Basic | Only part of the integrated application is operational, or the required Technical Report evidence is incomplete or inadequate. |
| 0 | No Marks | The group application is non-operational, or the assigned features are not integrated. |

**3 pts**

#### Technical Report and Project Evidence

This criterion is linked to a learning outcome.

The Technical Report must document the Release 1 scope, requirements, software architecture, MCP and RAG interaction design, validation results, known issues, and limitations. It must include the shared repository link, showcase video URL, validation evidence, contribution logs, and identifiable Release 1 commits for every student.

| Pts | Rating | Description |
| ---: | --- | --- |
| 3 | Full Marks | 2 pts: The Technical Report clearly and completely documents the required Release 1 scope, requirements, software architecture, MCP and RAG interaction design, validation results, known issues, and limitations. 1 pt: The repository link, showcase video URL, validation evidence, contribution logs, and identifiable commits are complete and traceable. |
| 2 | Good | 1 pt: The Technical Report addresses most required areas but contains minor omissions or inaccuracies. 1 pt: The required links, evidence, contribution logs, and commit records are substantially complete and traceable. |
| 1 | Basic | The Technical Report provides limited Release 1 content, or the required project evidence and contribution records are incomplete or inadequately traceable. |
| 0 | No Marks | The Technical Report is missing or does not provide assessable Release 1 content and project evidence. |

**3 pts**

#### Release 1 Demonstration and Q&A

This criterion is linked to a learning outcome.

Each student must demonstrate, explain, and defend their Release 1 contribution during the Q&A. Responses must demonstrate understanding of their assigned feature, MCP and RAG integration, validation evidence, and contribution to the integrated group application.

| Pts | Rating | Description |
| ---: | --- | --- |
| 3 | Full Marks | The student clearly demonstrates, explains, and defends their Release 1 contribution. Responses demonstrate accurate understanding of the assigned feature, MCP and RAG integration, validation evidence, and contribution to the integrated group application. |
| 2 | Good | The student demonstrates and explains their Release 1 contribution but shows minor gaps in understanding or provides incomplete answers during the Q&A. |
| 1 | Basic | The student provides a limited demonstration or explanation and shows significant gaps in understanding their contribution or the integrated application. |
| 0 | No Marks | The student does not participate in the demonstration and Q&A or cannot explain their Release 1 contribution. |

**3 pts**

**Total points: 30**