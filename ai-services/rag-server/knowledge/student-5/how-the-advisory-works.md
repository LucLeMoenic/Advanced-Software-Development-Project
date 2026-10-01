# How the Travel Advisory Works
Last reviewed: 2026-09. Curated demonstration content for the Travel Logistics & Advisory Service: general, non-time-sensitive guidance for Australian passport holders only. It is not legal, migration or medical advice; confirm current rules with official sources before travelling.

Non-AI lookups: the visa, weather and transit panels read the destination records in the Student 5 database directly: the country, its visa requirement category and entry notes, the seasonal weather notes, and the local transit options. These lookups work without any AI model.

AI-Mode advisory: the AI-Mode advisory sends the stored destination records, the travel month and interests to the local Ollama model and asks it to write a travel advisory checklist from those records only. If Ollama is unavailable or times out, the advisory shows an unavailable message and the non-AI lookups keep working.

MCP tools: the backend can call three read-only MCP tools on the shared MCP server: logistics.check_visa_requirement, logistics.get_weather and logistics.get_transit. The MCP tools only read the Student 5 database and never create, change or delete records.

Knowledge-base answers: questions about visas, documents, packing, transit and arrival are answered from this curated knowledge base by the shared RAG server, with citations and a confidence level. If the knowledge base does not cover a question, the answer is: Not enough information in the knowledge base to answer this.
