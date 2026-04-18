# Contoso Support Agent

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

Enterprise customer support agent with 3-agent pipeline (triage → resolution → draft), knowledge base retrieval, escalation workflows, and audit logging — powered by Azure OpenAI, Azure AI Search, and Cosmos DB.

## Architecture

```
Customer Query
        │
        ▼
┌─────────────────────────────────────────┐
│  SupportPipeline (orchestrator)         │
│                                         │
│  Stage 1 ──► TriageAgent               │──► Intent + urgency classification
│       │      └── Router                │──► Route to resolution or draft
│       ▼                                 │
│  Stage 2a ──► ResolutionAgent          │──► KB retrieval + answer generation
│       │       └── Retriever + Tools    │
│  Stage 2b ──► DraftAgent               │──► Response drafting + review queue
│       │       └── ReviewQueue          │
│       ▼                                 │
│  Escalation ──► handle_escalation()    │──► P1/P2 escalation routing
│       │                                 │
│  Audit ──► AuditRecord → Cosmos DB     │
└─────────────────────────────────────────┘
        │
Knowledge Base (Azure AI Search)
```

## Key Features

- **3-Agent Pipeline** — TriageAgent classifies intent, ResolutionAgent retrieves answers, DraftAgent drafts responses
- **Smart Routing** — `Router` determines whether to resolve automatically or draft for human review based on confidence and tier
- **Knowledge Base Retrieval** — `Retriever` performs hybrid search against indexed support articles
- **Tool Integration** — ResolutionAgent uses structured tools for account lookups and transaction queries
- **Review Queue** — DraftAgent queues low-confidence responses for human review
- **Escalation Handling** — Tier-based escalation with priority routing
- **Audit Trail** — Full pipeline audit records stored in Cosmos DB

## Step-by-Step Flow

### Step 1: Customer Query
Customer submits a `CustomerQuery` via `POST /support`.

### Step 2: Triage
`TriageAgent` analyzes the query using GPT-4o, returning a `TriageResult` with intent, urgency, tier, and confidence.

### Step 3: Routing
`determine_route()` decides the path: high-confidence queries go to `ResolutionAgent`, others to `DraftAgent`.

### Step 4: Resolution or Draft
- **ResolutionAgent**: Retrieves relevant KB articles, executes tools (account lookup, transaction search), generates a grounded response
- **DraftAgent**: Creates a draft response and pushes to `ReviewQueue` for human approval

### Step 5: Escalation Check
If urgency exceeds threshold, `handle_escalation()` routes to appropriate support tier.

### Step 6: Audit & Response
`AuditRecord` logged to Cosmos DB. `PipelineResult` returned with response, confidence, and resolution path.

## Repository Structure

```
contoso-support-agent/
├── orchestrator/
│   ├── main.py              # FastAPI entry point
│   ├── pipeline.py           # SupportPipeline — 3-agent orchestration
│   └── escalation.py         # Escalation routing
├── triage_agent/
│   ├── agent.py              # TriageAgent — intent classification
│   ├── router.py             # Route determination logic
│   └── prompts.py
├── resolution_agent/
│   ├── agent.py              # ResolutionAgent — KB retrieval + answer
│   ├── retriever.py          # Azure AI Search retriever
│   ├── tools.py              # Account/transaction lookup tools
│   └── prompts.py
├── draft_agent/
│   ├── agent.py              # DraftAgent — response drafting
│   ├── review_queue.py       # Human review queue
│   └── prompts.py
├── knowledge_base/
│   ├── indexer.py            # KB article indexing
│   └── chunker.py            # Document chunking
├── shared/
│   ├── config.py, models.py, azure_clients.py, middleware.py
├── tests/
│   ├── test_triage.py, test_resolution.py, test_pipeline_e2e.py
├── demo_e2e.py
├── requirements.txt
└── .env.example
```

## Quick Start

```bash
git clone https://github.com/maneeshkumar52/contoso-support-agent.git
cd contoso-support-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn orchestrator.main:app --host 0.0.0.0 --port 8000 --reload
```

## Testing

```bash
pytest -q
python demo_e2e.py
```

## License

MIT
