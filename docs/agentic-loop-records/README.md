# Agentic Loop Records

Store finalised JSON execution records from the shared two-model loop here.

Each report-ready record must contain:

- bounded task and allow-listed context files;
- exact implementer and reviewer model tags;
- prompt file/version references and SHA-256 hashes;
- context-file SHA-256 hashes, Ollama version, and generation options;
- pre-test command and result;
- Plan/Act proposal;
- reviewer Observe verdict and findings;
- adapted proposal when revision was required;
- reviewer verdict on the adapted proposal;
- human kept/changed/rejected decision and notes;
- post-test command and result.

Do not commit records containing secrets, personal data, proprietary external code, or unnecessary source content.
