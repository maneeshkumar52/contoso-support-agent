# Contoso Support Agent

A production-grade multi-agent customer support system for Contoso Financial Services, built with Azure OpenAI, Azure AI Search, and Cosmos DB.

This project accompanies **Chapter 17 of "Prompt to Production" by Maneesh Kumar**, demonstrating how to build enterprise-grade agentic systems with real-world architectural patterns.

---

## Architecture

```
Customer Query
      |
      v
+---------------------+
|   Orchestrator      |  :8000  (FastAPI)
|   /api/v1/query     |
+---------------------+
      |
      v
+---------------------+
|   Triage Agent      |  Classifies query into Tier 1 / 2 / 3
|   (Azure OpenAI)    |  using GPT-4o with JSON structured output
+---------------------+
      |
      +------------------+------------------+
      |                  |                  |
  Tier 1             Tier 2            Tier 3
  (Auto-resolve)     (RAG-assisted)    (Human review)
      |                  |                  |
      v                  v                  v
+----------+    +-----------------+    +------------+
|Resolution|    | Resolution      |    | Draft      |
|Agent     |    | Agent           |    | Agent      |
|(Tool     |    |(RAG + Tool      |    |(GPT-4o +   |
| Calling) |    | Calling)        |    | Review     |
+----------+    +-----------------+    | Queue)     |
      |                  |             +------------+
      |                  |                  |
      |         Azure AI Search       Cosmos DB
      |         (Hybrid Vector        (Review Queue)
      |          + Keyword)                 |
      |                  |                  |
      +------------------+------------------+
                         |
                    Cosmos DB
                  (Audit Records)
                         |
                         v
                  Final Response
```

**Four agents working in concert:**
- **Triage Agent**: Classifies incoming queries into Tier 1 (auto-resolve), Tier 2 (RAG-assisted), or Tier 3 (human escalation)
- **Resolution Agent**: Handles Tier 1 and Tier 2 cases using tool calling and hybrid vector search
- **Draft Agent**: Generates professional draft responses for Tier 3 cases and queues them for human review
- **Orchestrator**: Coordinates the full pipeline, writes audit records, and returns structured responses

---

## Prerequisites

You will need active Azure resources for full functionality:

| Service | Purpose |
|---|---|
| Azure OpenAI | GPT-4o for agent reasoning; text-embedding-3-large for embeddings |
| Azure AI Search | Hybrid vector + keyword search over the knowledge base |
| Azure Cosmos DB | Audit records and human review queue storage |

All services must be provisioned in an Azure subscription. See the [Azure portal](https://portal.azure.com) to create these resources.

---

## Local Development Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/your-org/contoso-support-agent.git
cd contoso-support-agent
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your Azure resource credentials
```

### 3. Index the knowledge base

```bash
python -m knowledge_base.indexer
```

### 4. Run agents locally

Run each agent in a separate terminal:

```bash
# Terminal 1 - Orchestrator (main API)
uvicorn orchestrator.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 - Triage Agent
uvicorn triage_agent.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 3 - Resolution Agent
uvicorn resolution_agent.main:app --host 0.0.0.0 --port 8002 --reload

# Terminal 4 - Draft Agent
uvicorn draft_agent.main:app --host 0.0.0.0 --port 8003 --reload
```

---

## Docker Compose

Run all four agents together with Docker Compose:

```bash
# Build and start all services
cd infra
docker-compose up --build

# Stop all services
docker-compose down
```

Services will be available at:
- Orchestrator: http://localhost:8000
- Triage Agent: http://localhost:8001
- Resolution Agent: http://localhost:8002
- Draft Agent: http://localhost:8003

---

## API Usage

### Send a customer query

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST001",
    "message": "What are the fees for sending money to Australia?",
    "channel": "chat"
  }'
```

### Example response

```json
{
  "final_response": "For international transfers to Australia, Contoso charges a flat fee of £5 per transaction plus 0.5% of the transfer amount. Processing typically takes 2 business days. [Source: Sample Policies]",
  "tier": 2,
  "agents_used": ["triage_agent", "resolution_agent"],
  "total_latency_ms": 1842.5,
  "audit_id": "3f7a1b2c-...",
  "session_id": "a1b2c3d4-...",
  "sources": ["Sample Policies"]
}
```

### Health checks

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_triage.py -v
pytest tests/test_resolution.py -v
pytest tests/test_pipeline_e2e.py -v
```

---

## Project Structure

```
contoso-support-agent/
|-- shared/                    # Shared models, config, and Azure clients
|   |-- config.py              # Pydantic settings with env var support
|   |-- models.py              # Shared Pydantic data models
|   |-- azure_clients.py       # Singleton Azure service clients
|   |-- logging_config.py      # Structlog JSON logging configuration
|   |-- middleware.py          # FastAPI tracing middleware
|
|-- triage_agent/              # Tier classification agent
|   |-- agent.py               # TriageAgent class
|   |-- prompts.py             # System prompts with few-shot examples
|   |-- router.py              # Confidence-based routing logic
|   |-- main.py                # FastAPI app (port 8001)
|
|-- resolution_agent/          # RAG + tool calling resolution
|   |-- agent.py               # ResolutionAgent with agentic loop
|   |-- retriever.py           # HybridRetriever (vector + keyword)
|   |-- tools.py               # Tool definitions and handlers
|   |-- prompts.py             # Resolution system prompts
|   |-- main.py                # FastAPI app (port 8002)
|
|-- draft_agent/               # Tier 3 draft and escalation
|   |-- agent.py               # DraftAgent class
|   |-- prompts.py             # Draft system prompt
|   |-- review_queue.py        # Cosmos DB review queue integration
|   |-- main.py                # FastAPI app (port 8003)
|
|-- orchestrator/              # Pipeline coordination
|   |-- pipeline.py            # SupportPipeline orchestration
|   |-- escalation.py          # Human escalation handler
|   |-- main.py                # FastAPI app (port 8000)
|
|-- knowledge_base/            # Document indexing pipeline
|   |-- chunker.py             # Recursive text chunker
|   |-- indexer.py             # Azure AI Search indexer
|   |-- documents/             # Source policy documents (Markdown)
|
|-- tests/                     # Test suite
|   |-- test_triage.py         # Triage agent unit tests
|   |-- test_resolution.py     # Resolution tools unit tests
|   |-- test_pipeline_e2e.py   # End-to-end pipeline tests
|   |-- eval/                  # Evaluation datasets (JSONL)
|
|-- infra/                     # Deployment configuration
|   |-- Dockerfile             # Container image definition
|   |-- docker-compose.yml     # Multi-service orchestration
|   |-- ci-cd-pipeline.yml     # GitHub Actions CI/CD
|
|-- requirements.txt           # Python dependencies
|-- pyproject.toml             # Pytest and linting configuration
|-- .env.example               # Environment variable template
```

---

## Key Design Patterns

- **Tiered Routing**: Queries are classified into three tiers with confidence-based escalation. Low-confidence Tier 1 classifications automatically escalate to Tier 2.
- **Agentic Tool Calling Loop**: The resolution agent runs up to 3 iterations of the tool-calling loop, using GPT-4o's native function calling to invoke account balance, transaction history, and policy tools.
- **Hybrid Retrieval**: Azure AI Search combines dense vector similarity (using text-embedding-3-large embeddings) with BM25 keyword search for optimal document retrieval.
- **Complete Audit Trail**: Every interaction is written to Cosmos DB with full agent chain, latency, and token usage for compliance and observability.
- **Graceful Degradation**: All agents have fallback responses. Audit write failures are logged but do not block the response path.

---

## Book Reference

This repository is the companion code for:

> **"Prompt to Production: Building Production Agentic AI Systems"**
> By Maneesh Kumar
> Chapter 17: Multi-Agent Customer Support Systems

The chapter covers the architectural decisions behind this system, including the triage-resolution-draft pattern, the tradeoffs of inline vs. microservice agent architectures, and how to design audit trails that meet FCA regulatory requirements.

---

## Contributing

Pull requests are welcome. For significant changes, please open an issue first to discuss what you would like to change.

## Licence

MIT Licence. See LICENSE file for details.
