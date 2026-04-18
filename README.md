<div align="center">

# Contoso Support Agent

### 3-Agent Sequential Pipeline for Enterprise Customer Support with Tier-Based Routing, Tool-Calling Resolution, Human Escalation, and Full Audit Trail

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4o-0078D4?logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/en-us/products/ai-services/openai-service)
[![Azure AI Search](https://img.shields.io/badge/Azure_AI_Search-11.4-0078D4?logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/en-us/products/ai-services/ai-search)
[![Azure Cosmos DB](https://img.shields.io/badge/Cosmos_DB-4.7-0078D4?logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/en-us/products/cosmos-db)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

*A multi-agent customer support system for Contoso Financial Services that classifies incoming queries into 3 tiers via a Triage Agent (GPT-4o structured JSON output), routes them through confidence-based escalation logic, resolves Tier 1/2 queries via a Resolution Agent with 5 tool-calling functions and hybrid RAG retrieval, drafts Tier 3 responses for human review with a dedicated Draft Agent and Cosmos DB review queue, writes full audit records to Cosmos DB, and gracefully degrades when any Azure service is unavailable — all deployed as 4 independent FastAPI microservices orchestrated via Docker Compose.*

[Architecture](#architecture) · [Quick Start](#quick-start) · [API Reference](#api-reference) · [Agent Details](#agent-details) · [Tool Calling](#tool-calling) · [Deployment](#deployment)

</div>

---

## Why This Exists

Enterprise customer support requires more than a single-pass RAG chatbot. Real support organisations classify queries by urgency, route to specialised agents, perform actions on customer accounts, escalate complex issues to human reviewers, and maintain compliance audit trails.

This system solves four problems that generic chatbots cannot:

- **Intelligent triage** — A dedicated Triage Agent classifies every query into Tier 1 (auto-resolve), Tier 2 (RAG-assisted), or Tier 3 (human escalation) with confidence scoring. Queries below 0.7 confidence are automatically escalated one tier higher.
- **Tool-calling resolution** — The Resolution Agent doesn't just retrieve documents — it calls structured tools (check balance, get transactions, reset password, check card status, look up policies) in an iterative loop with up to 3 tool-call rounds.
- **Human-in-the-loop drafting** — Tier 3 queries (fraud, complaints, bereavement) go to a Draft Agent that generates empathetic responses for human review, stored in a Cosmos DB review queue with priority levels.
- **Full audit trail** — Every query, response, agent chain, latency, and token count is written to Cosmos DB for compliance and analytics.

---

## Architecture

### System Architecture

```
                         Customer Query (POST /api/v1/query)
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (port 8000)                       │
│                    SupportPipeline.run()                          │
│                                                                  │
│  ┌────────────┐    ┌──────────────────┐    ┌─────────────────┐  │
│  │ Phase 1    │    │ Phase 2          │    │ Phase 3         │  │
│  │ TRIAGE     │───▶│ ROUTING          │───▶│ RESOLVE / DRAFT │  │
│  │            │    │ determine_route() │    │                 │  │
│  │ TriageAgent│    │ confidence check  │    │ Tier 1,2 → Res. │  │
│  │ classify() │    │ tier escalation   │    │ Tier 3   → Draft│  │
│  └────────────┘    └──────────────────┘    └────────┬────────┘  │
│                                                      │           │
│  ┌────────────────────────────────────────────────────┘          │
│  │                                                               │
│  ▼                                                               │
│  ┌───────────────────────────┐  ┌────────────────────────────┐  │
│  │ RESOLUTION AGENT (8002)   │  │ DRAFT AGENT (8003)         │  │
│  │ ┌───────────────────────┐ │  │ ┌────────────────────────┐ │  │
│  │ │ HybridRetriever       │ │  │ │ DraftAgent.draft()     │ │  │
│  │ │ (Azure AI Search)     │ │  │ │ GPT-4o → JSON draft    │ │  │
│  │ │ vector + keyword      │ │  │ └────────────┬───────────┘ │  │
│  │ │ semantic ranking      │ │  │              │             │  │
│  │ └───────────┬───────────┘ │  │ ┌────────────▼───────────┐ │  │
│  │             │             │  │ │ ReviewQueue.push()     │ │  │
│  │ ┌───────────▼───────────┐ │  │ │ → Cosmos DB            │ │  │
│  │ │ ResolutionAgent       │ │  │ │ (review-queue container)│ │  │
│  │ │ tool-calling loop     │ │  │ └────────────────────────┘ │  │
│  │ │ (max 3 iterations)    │ │  └────────────────────────────┘  │
│  │ │ ┌─────────────────┐   │ │                                   │
│  │ │ │ Tools:           │   │ │  ┌────────────────────────────┐  │
│  │ │ │ • balance check  │   │ │  │ ESCALATION HANDLER         │  │
│  │ │ │ • transactions   │   │ │  │ handle_escalation()        │  │
│  │ │ │ • password reset │   │ │  │ → CRM/ticketing stub       │  │
│  │ │ │ • card status    │   │ │  │ → ESC-{session_id} ref     │  │
│  │ │ │ • policy lookup  │   │ │  └────────────────────────────┘  │
│  │ │ └─────────────────┘   │ │                                   │
│  │ └───────────────────────┘ │                                   │
│  └───────────────────────────┘                                   │
│                                                                  │
│  Phase 4: AUDIT                                                  │
│  AuditRecord → Cosmos DB (audit-records container)               │
│                                                                  │
│  Return: PipelineResult                                          │
└──────────────────────────────────────────────────────────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                ▼                   ▼                   ▼
        Azure OpenAI         Azure AI Search       Cosmos DB
        (GPT-4o +            (hybrid index         (audit-records +
         text-embedding-      content_vector        review-queue)
         3-large)             + semantic)
```

### Pipeline Data Flow

```
CustomerQuery
    → TriageAgent.classify()     → TriageResult (tier, category, confidence)
    → determine_route()          → route dict (agent, mode, effective_tier)
    → ResolutionAgent.resolve()  → ResolutionResult (answer, sources, tool_calls)
       OR DraftAgent.draft()     → DraftResult (draft, review_notes, priority)
           → handle_escalation() → escalation dict (customer_message, ESC-ref)
    → _write_audit()             → AuditRecord → Cosmos DB
    → PipelineResult             → HTTP response
```

### Confidence-Based Routing

```
TriageResult
    │
    ├── confidence ≥ 0.7?
    │   ├── YES ─── Tier 1 ──→ ResolutionAgent (auto_resolve mode)
    │   ├── YES ─── Tier 2 ──→ ResolutionAgent (rag_assisted mode)
    │   └── YES ─── Tier 3 ──→ DraftAgent → ReviewQueue → Escalation
    │
    └── NO (< 0.7) ─── Escalate one tier up
        ├── Tier 1 → becomes Tier 2 (RAG-assisted instead of auto)
        ├── Tier 2 → becomes Tier 3 (human review instead of RAG)
        └── Tier 3 → stays Tier 3 (already highest)
```

### Why Not a Generic RAG Chatbot?

| Dimension | Generic RAG Chatbot | Contoso Support Agent |
|-----------|--------------------|-----------------------|
| **Architecture** | Single retrieve-generate loop | 3-agent sequential pipeline with routing |
| **Query Classification** | All queries treated equally | Dedicated Triage Agent → 3 tiers with confidence |
| **Routing** | Direct retrieval | Confidence-based routing with automatic escalation |
| **Tool Calling** | Typically none | 5 structured tools with iterative execution (max 3 rounds) |
| **Human-in-the-Loop** | Usually absent | Draft Agent + ReviewQueue in Cosmos DB |
| **Escalation** | Not present | Tier-based with CRM integration stub |
| **Audit Trail** | Minimal | Full AuditRecord per query (agent chain, latency, tokens) |
| **Confidence Handling** | Single pass | Triage confidence < 0.7 → automatic tier escalation |
| **Error Resilience** | Typically crashes | Every agent has graceful fallback; pipeline returns apology on total failure |
| **Deployment** | Monolithic | 4 independent FastAPI services, Docker Compose |
| **Structured Output** | Free-text | Triage + Draft use `json_object` format for deterministic parsing |
| **Observability** | Basic logging | Structlog JSON with correlation IDs, latency headers, contextvars |
| **Eval Framework** | Ad-hoc | 20-case JSONL evaluation sets with expected outputs |

---

## Design Decisions

### Why 3 Separate Agents Instead of One?

| Approach | Pros | Cons |
|----------|------|------|
| Single monolithic agent | Simpler deployment | Cannot tune temperature/format per task, no separation of concerns |
| **3 specialised agents** ✅ | Each optimised for its task (triage: temp=0.1, resolution: temp=0.3, draft: temp=0.4) | More modules, but clear boundaries |
| Fully independent microservices | Maximum flexibility | Network overhead, operational complexity |

The system uses a hybrid: agents are imported in-process by the orchestrator for zero-latency calls, while also exposable as independent FastAPI services for future microservice decomposition.

### LLM Configuration Per Agent

| Agent | Temperature | Max Tokens | Response Format | Why |
|-------|-------------|------------|-----------------|-----|
| **Triage** | 0.1 | 500 | `json_object` | Deterministic classification — low creativity needed |
| **Resolution** | 0.3 | 1000 | Free text + tools | Balanced — needs some creativity for explanations |
| **Draft** | 0.4 | 1000 | `json_object` | Higher creativity for empathetic, nuanced responses |

### Why Confidence Threshold at 0.7?

```python
CONFIDENCE_THRESHOLD = 0.7

# router.py — Escalation logic
if triage_result.confidence < CONFIDENCE_THRESHOLD:
    if triage_result.tier == Tier.TIER_1:
        effective_tier = Tier.TIER_2    # Auto-resolve → RAG-assisted
    elif triage_result.tier == Tier.TIER_2:
        effective_tier = Tier.TIER_3    # RAG-assisted → Human review
```

| Threshold | Effect |
|-----------|--------|
| < 0.5 | Too permissive — many misclassified queries reach wrong agent |
| **0.7** ✅ | Balanced — catches uncertain classifications while avoiding over-escalation |
| > 0.9 | Too strict — nearly everything escalates, defeating the purpose of automation |

### Why Non-Blocking Audit and Review Writes?

```python
# pipeline.py
try:
    container.upsert_item(audit_data)
except Exception as e:
    logger.error("audit_write_failed", error=str(e))
    # Does NOT re-raise — customer still gets their response
```

| Approach | Customer Impact | Data Risk |
|----------|----------------|-----------|
| Blocking (raise on failure) | Customer sees error page | No data loss |
| **Non-blocking** ✅ | Customer gets response regardless | Audit record may be lost (log warning) |

In financial services, returning a response to the customer is higher priority than persisting an audit record. The structlog warning ensures the ops team is alerted.

### Why Triple-Mode Hybrid Search?

```python
# retriever.py — Three search modes combined
results = await self._search_client.search(
    search_text=query,                     # BM25 keyword matching
    query_type="semantic",                 # Azure semantic re-ranking
    semantic_configuration_name="default",
    vector_queries=[VectorizedQuery(       # HNSW vector similarity
        vector=embedding,                  # 3072-dim (text-embedding-3-large)
        k_nearest_neighbors=top_k,
        fields="content_vector"
    )],
    filter=f"category eq '{category}'"     # Optional category narrowing
)
```

| Search Type | Catches | Misses |
|-------------|---------|--------|
| Keyword (BM25) | Exact terms: "FSCS", "£85,000", policy numbers | Paraphrases |
| Vector (HNSW 3072d) | Semantic similarity, synonyms | Exact numbers/acronyms |
| Semantic ranking | Contextual re-ranking of combined results | — |
| **All three combined** ✅ | Everything | Slightly higher latency |

---

## Data Contracts

### 8 Pydantic v2 Models

```python
# ── Enums ─────────────────────────────────────────────────────────
class Channel(str, Enum):
    EMAIL = "email"
    CHAT = "chat"
    PHONE = "phone"

class Tier(int, Enum):
    TIER_1 = 1    # Auto-resolve
    TIER_2 = 2    # RAG-assisted
    TIER_3 = 3    # Human escalation

# ── Incoming Query ────────────────────────────────────────────────
class CustomerQuery(BaseModel):
    customer_id: str                    # "CUST001"
    message: str                        # "I forgot my password"
    session_id: str = uuid4()           # Auto-generated session
    channel: Channel = Channel.CHAT     # email | chat | phone
    correlation_id: str = uuid4()       # Distributed tracing ID

# ── Triage Output ─────────────────────────────────────────────────
class TriageResult(BaseModel):
    tier: Tier                          # 1, 2, or 3
    category: str                       # "password_reset", "fraud_report"
    confidence: float                   # 0.0–1.0
    reasoning: str                      # "Password/login issues are Tier 1"
    auto_resolve_action: Optional[str]  # "initiate_password_reset" (Tier 1 only)

# ── Retrieved Document ────────────────────────────────────────────
class RetrievedDocument(BaseModel):
    title: str                          # "IT Security Policy 2024"
    content: str                        # Full matched content
    relevance_score: float              # Azure AI Search @search.score
    source_url: Optional[str] = None    # Document source URL
    category: Optional[str] = None      # Document category

# ── Tool Call Record ──────────────────────────────────────────────
class ToolCall(BaseModel):
    tool_name: str                      # "check_account_balance"
    arguments: Dict[str, Any]           # {"customer_id": "CUST001"}
    result: Dict[str, Any]              # {"balance": 4523.67, ...}
    timestamp: datetime = datetime.utcnow()

# ── Resolution Output ─────────────────────────────────────────────
class ResolutionResult(BaseModel):
    answer: str                         # Generated response
    sources: List[str] = []             # ["Overdraft Policies"]
    confidence: float = 0.0             # 0.85 if docs found, 0.7 otherwise
    tool_calls_made: List[ToolCall] = [] # All tools invoked
    tokens_used: int = 0                # Total token consumption

# ── Draft Output ──────────────────────────────────────────────────
class DraftResult(BaseModel):
    draft_response: str                 # Empathetic draft for human review
    review_notes: str                   # Internal notes for reviewer
    suggested_tier: Optional[Tier] = None # Always Tier 3
    priority: str = "normal"            # urgent | high | normal | low

# ── Audit Record ──────────────────────────────────────────────────
class AuditRecord(BaseModel):
    id: str = uuid4()                   # Document ID
    timestamp: datetime = datetime.utcnow()
    customer_id: str                    # "CUST001"
    session_id: str                     # Session UUID
    correlation_id: str                 # Distributed tracing ID
    query: str                          # Original customer message
    response: str                       # Final response text
    tier: int                           # 1, 2, or 3
    agent_chain: List[str] = []         # ["triage_agent", "resolution_agent"]
    latency_ms: float = 0.0            # End-to-end pipeline latency
    token_usage: int = 0               # Total tokens consumed
    channel: str = "chat"              # email | chat | phone

# ── Final Pipeline Output ─────────────────────────────────────────
class PipelineResult(BaseModel):
    final_response: str                 # Customer-facing response
    tier: Tier                          # Resolved tier
    agents_used: List[str] = []         # ["triage_agent", "resolution_agent"]
    total_latency_ms: float = 0.0      # Pipeline duration
    audit_id: str                       # Cosmos DB audit record ID
    session_id: str                     # Session UUID
    sources: List[str] = []            # Document sources used
```

### Cosmos DB Document Schemas

**Container: `audit-records`**
```json
{
  "id": "a1b2c3d4-...",
  "timestamp": "2024-11-15T14:00:00Z",
  "customer_id": "CUST001",
  "session_id": "uuid",
  "correlation_id": "uuid",
  "query": "I forgot my password",
  "response": "Your password has been reset...",
  "tier": 1,
  "agent_chain": ["triage_agent", "resolution_agent"],
  "latency_ms": 1234.56,
  "token_usage": 450,
  "channel": "chat"
}
```

**Container: `review-queue`**
```json
{
  "id": "uuid",
  "customer_id": "CUST001",
  "session_id": "uuid",
  "created_at": "2024-11-15T14:00:00Z",
  "status": "pending_review",
  "draft_response": "We sincerely apologise for this experience...",
  "review_notes": "Customer reports potential fraud. Verify...",
  "priority": "urgent",
  "suggested_actions": ["verify_account", "freeze_card", "assign_investigator"]
}
```

---

## Features

| # | Feature | Description | Implementation |
|---|---------|-------------|----------------|
| 1 | **3-Agent Pipeline** | Triage → Route → Resolve/Draft → Audit | `orchestrator/pipeline.py` |
| 2 | **Tier-Based Classification** | Auto-resolve (T1), RAG-assisted (T2), Human escalation (T3) | `triage_agent/agent.py` |
| 3 | **Confidence-Based Escalation** | Queries below 0.7 confidence auto-escalate one tier | `triage_agent/router.py` |
| 4 | **5 Tool-Calling Functions** | Balance, transactions, password reset, card status, policy lookup | `resolution_agent/tools.py` |
| 5 | **Iterative Tool Loop** | Up to 3 rounds of tool calls per query | `resolution_agent/agent.py` (MAX_TOOL_ITERATIONS=3) |
| 6 | **Hybrid RAG Retrieval** | BM25 keyword + HNSW vector (3072d) + semantic ranking | `resolution_agent/retriever.py` |
| 7 | **Category-Filtered Search** | OData filter on document category for focused retrieval | `retriever.py` → `filter` param |
| 8 | **Human Review Drafts** | Empathetic Tier 3 drafts with reviewer notes and priority | `draft_agent/agent.py` |
| 9 | **Review Queue** | Drafts persisted to Cosmos DB for human reviewers | `draft_agent/review_queue.py` |
| 10 | **CRM Escalation Stub** | ESC-{session_id} reference for ticketing integration | `orchestrator/escalation.py` |
| 11 | **Full Audit Trail** | Every query logged with agent chain, latency, tokens | `AuditRecord` → Cosmos DB |
| 12 | **Structured JSON Output** | Triage and Draft agents use `json_object` response format | `response_format` param |
| 13 | **Few-Shot Triage Prompt** | 3 labelled examples in system prompt for consistent classification | `triage_agent/prompts.py` |
| 14 | **Correlation ID Tracing** | X-Correlation-ID propagated across all requests | `shared/middleware.py` |
| 15 | **Latency Headers** | X-Latency-Ms response header on every request | `TracingMiddleware` |
| 16 | **Structlog JSON Logging** | ISO timestamps, correlation IDs, contextvars propagation | `shared/logging_config.py` |
| 17 | **Azure Client Singletons** | OpenAI, Search, Cosmos clients created once, reused | `shared/azure_clients.py` |
| 18 | **Settings Singleton** | `@lru_cache` pydantic-settings configuration | `shared/config.py` |
| 19 | **Graceful Pipeline Fallback** | Total failure returns apology with 0800-CONTOSO number | `pipeline.py` error handler |
| 20 | **Graceful Agent Fallbacks** | Triage→Tier2, Resolution→generic, Draft→acknowledgement | Each agent's except block |
| 21 | **Non-Blocking Audit** | Cosmos write failures don't block customer response | `_write_audit()` |
| 22 | **Non-Blocking Review Queue** | Review push failures don't block draft return | `ReviewQueue.push()` |
| 23 | **Recursive Text Chunking** | 1000-char chunks with 200-char overlap, heading extraction | `knowledge_base/chunker.py` |
| 24 | **367-Line Policy Corpus** | 8-section UK financial services policies (FCA, FSCS, rates) | `knowledge_base/documents/` |
| 25 | **Document Indexing Pipeline** | Embed + index to Azure AI Search in batches of 100 | `knowledge_base/indexer.py` |
| 26 | **Clearance Level Field** | Document chunks tagged with access level (scaffolding for RBAC) | `DocumentChunk.clearance_level` |
| 27 | **3 Communication Channels** | Email, chat, phone — tracked per query | `Channel` enum |
| 28 | **Mock Banking Data** | 3 customer accounts with realistic balances and card statuses | `MOCK_ACCOUNTS` dict |
| 29 | **Mock Policy Data** | Overdraft, international transfers, savings rates | `tools.py` policies dict |
| 30 | **4-Service Docker Compose** | Orchestrator + 3 agents on bridge network | `infra/docker-compose.yml` |
| 31 | **CI/CD Pipeline** | GitHub Actions: test → build Docker image | `infra/ci-cd-pipeline.yml` |
| 32 | **20-Case Eval Sets** | 10 triage + 10 resolution JSONL evaluation cases | `tests/eval/` |
| 33 | **E2E Demo Script** | Full pipeline demo without Azure credentials | `demo_e2e.py` |
| 34 | **CORS Middleware** | Cross-origin support for frontend integration | `CORSMiddleware` |
| 35 | **Health Endpoints** | Liveness probes on all 4 services | `/health` per service |

---

## Agent Details

### Triage Agent

**Purpose:** Classify every incoming query into Tier 1/2/3 with confidence scoring.

**System Prompt (verbatim):**
```
You are a customer support triage specialist for Contoso Financial Services.
Your job is to classify incoming customer queries into one of three tiers:

TIER 1 - Auto-resolve (simple, common issues):
- Password resets and login issues
- Account balance inquiries
- Card activation requests
- Basic statement requests
- Contact information updates

TIER 2 - RAG-assisted resolution (policy questions, complex account issues):
- Questions about account fees and charges
- Loan and mortgage inquiries
- Investment product questions
- Policy clarifications
- Transaction disputes (non-fraudulent)

TIER 3 - Human escalation (complaints, disputes, regulatory):
- Formal complaints
- Fraud reports
- Regulatory matters
- Bereavement cases
- Legal matters
- Situations requiring empathy and human judgment
```

**Classification Examples (from prompt):**

| Query | Tier | Category | Confidence | Auto-Resolve Action |
|-------|------|----------|------------|---------------------|
| "I can't log into my account" | 1 | login_issue | 0.95 | initiate_password_reset |
| "What is the interest rate on savings?" | 2 | product_inquiry | 0.88 | null |
| "Someone stole money from my account" | 3 | fraud_report | 0.99 | null |

### Resolution Agent

**Purpose:** Resolve Tier 1 (auto) and Tier 2 (RAG-assisted) queries using knowledge base retrieval and tool calling.

**System Prompt (verbatim):**
```
You are a knowledgeable customer support specialist at Contoso Financial Services.
Your role is to provide accurate, helpful, and empathetic responses to customer queries.

CRITICAL RULES:
1. Only use information from the provided knowledge base documents and tool results
2. Always cite the specific policy document or source when referencing information
3. Never fabricate or guess at policy details, rates, or procedures
4. If you don't have enough information, say so clearly
5. Maintain a professional, empathetic tone at all times
6. For account-specific information, always use the available tools
7. Express uncertainty when confidence is low
```

**Tool-Calling Loop:**
```
messages = [system_prompt, user_context + retrieved_docs]
    │
    ▼
┌── Iteration 1 ──────────────────────────────┐
│ GPT-4o response                              │
│   ├── Has tool_calls? ──YES──→ Execute tools │
│   │   └── Append tool results to messages    │
│   └── No tool_calls? ──→ Use content as answer
└──────────────────────────────────────────────┘
    │ (if tool_calls were made)
    ▼
┌── Iteration 2 (max 3) ──────────────────────┐
│ GPT-4o with tool results                     │
│   ├── More tool_calls? ──→ Execute again     │
│   └── No more? ──→ Final answer              │
└──────────────────────────────────────────────┘
```

### Draft Agent

**Purpose:** Generate empathetic, professional drafts for Tier 3 issues requiring human review.

**System Prompt (verbatim):**
```
You are a senior customer service specialist at Contoso Financial Services,
drafting responses for complex customer issues that require human review.

Your drafts should:
1. Be professional, empathetic, and appropriately formal
2. Acknowledge the customer's concern clearly and specifically
3. Explain next steps clearly
4. Include relevant policy information where applicable
5. Avoid making promises or commitments that cannot be guaranteed
6. Use plain English — avoid jargon
```

**Output:** JSON with `draft_response`, `review_notes`, `priority`, `suggested_actions` → pushed to Cosmos DB review queue.

---

## Tool Calling

### 5 Available Tools

| # | Tool | Parameters | Returns |
|---|------|-----------|---------|
| 1 | `check_account_balance` | `customer_id` (required) | Balance, currency, account type, last updated |
| 2 | `get_recent_transactions` | `customer_id` (required), `days` (default 30) | List of transactions (max 10) |
| 3 | `initiate_password_reset` | `customer_id` (required) | Success status, reset link expiry (24h) |
| 4 | `check_card_status` | `customer_id` (required) | Card status, expiry, daily/contactless limits |
| 5 | `get_policy_details` | `policy_id` (required) | Policy content (overdraft, international_transfers, savings_rates) |

### Mock Customer Accounts

| Customer ID | Balance | Account Type | Card Status |
|-------------|---------|-------------|-------------|
| `CUST001` | £4,523.67 | Current Account | Active |
| `CUST002` | £12,890.45 | Savings Account | Blocked |
| `CUST003` | £234.12 | Current Account | Active |

### Mock Policy Data

| Policy ID | Key Details |
|-----------|------------|
| `overdraft` | Interest 39.9% EAR, no daily fee, limit up to £5,000 |
| `international_transfers` | £5 + 0.5% fee, 1–3 business days, max £25,000, 140+ currencies |
| `savings_rates` | Instant 3.5% AER, 1yr fixed 4.2%, 2yr fixed 4.5%, ISA 3.8% |

---

## Knowledge Base

### Policy Document (367 lines)

8-section UK financial services policy covering:

| Section | Content |
|---------|---------|
| Account Types | Current, Savings, ISA, Junior ISA — eligibility and features |
| Overdraft Policies | Arranged/unarranged overdraft terms, interest rates |
| International Transfers | Fees, processing times, currency support |
| Dispute Resolution | Transaction disputes, formal complaints, FOS escalation |
| Card Services | Debit card features, lost/stolen procedures, activation |
| Loans and Borrowing | Personal loans, mortgages, APR details |
| Online and Mobile Banking | 2FA, password reset flows, fraud reporting |
| Regulatory Information | FSCS £85k protection, FCA regulation, data protection |

### Chunking Strategy

```python
RecursiveTextChunker(chunk_size=1000, chunk_overlap=200)
```

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Chunk size | 1000 chars | Fits within GPT-4o context alongside other context |
| Overlap | 200 chars | Preserves cross-boundary context |
| Separators | `["\n\n", "\n", ". ", " "]` | Prefers paragraph → line → sentence → word breaks |
| Min chunk | 50 chars | Skips trivially small fragments |
| Heading extraction | First 3 lines of each chunk | Attaches section context to chunks |

### Search Index Schema

| Field | Type | Properties |
|-------|------|------------|
| `id` | String | Key |
| `title` | String | Searchable |
| `content` | String | Searchable |
| `category` | String | Filterable, Facetable |
| `source_file` | String | — |
| `clearance_level` | String | Filterable |
| `chunk_index` | Int32 | — |
| `content_vector` | Collection(Single) | Searchable, 3072-dim HNSW |

---

## Prerequisites

<details>
<summary><strong>macOS</strong></summary>

```bash
brew install python@3.11
python3.11 --version
# Python 3.11.x
```

</details>

<details>
<summary><strong>Windows</strong></summary>

```powershell
winget install Python.Python.3.11
python --version
# Python 3.11.x
```

</details>

<details>
<summary><strong>Linux (Ubuntu/Debian)</strong></summary>

```bash
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip
python3.11 --version
```

</details>

### Required Azure Services

| Service | Required | Purpose | Fallback |
|---------|----------|---------|----------|
| **Azure OpenAI** | No | GPT-4o for all 3 agents | Agents return graceful fallback responses |
| **Azure AI Search** | No | Hybrid document retrieval | Returns empty document list |
| **Azure Cosmos DB** | No | Audit records + review queue | Records lost (logged as warnings) |

---

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/maneeshkumar52/contoso-support-agent.git
cd contoso-support-agent
```

### 2. Create Virtual Environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate    # macOS/Linux
# .venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Expected output:**
```
Collecting fastapi==0.111.0
Collecting uvicorn==0.30.0
Collecting openai==1.40.0
Collecting azure-search-documents==11.4.0
Collecting azure-cosmos==4.7.0
Successfully installed fastapi-0.111.0 uvicorn-0.30.0 ...
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your Azure credentials (all services are optional — system runs with graceful fallbacks):

```env
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your-search-key
AZURE_SEARCH_INDEX_NAME=contoso-knowledge-base
COSMOS_ENDPOINT=https://your-cosmos.documents.azure.com:443/
COSMOS_KEY=your-cosmos-key
COSMOS_DATABASE=contoso-support
COSMOS_CONTAINER=audit-records
COSMOS_REVIEW_CONTAINER=review-queue
LOG_LEVEL=INFO
```

### 5. Index Knowledge Base (Optional)

```bash
python knowledge_base/indexer.py
```

Reads `knowledge_base/documents/*.md`, chunks with 1000-char windows, embeds with `text-embedding-3-large`, uploads to Azure AI Search.

### 6. Start the Orchestrator

```bash
uvicorn orchestrator.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345]
```

### 7. Query — Tier 1 (Auto-Resolve)

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST001",
    "message": "I forgot my password and cannot log in"
  }'
```

**Expected response:**
```json
{
  "final_response": "Your password has been reset. A reset link has been sent to your registered email address and will expire in 24 hours...",
  "tier": 1,
  "agents_used": ["triage_agent", "resolution_agent"],
  "total_latency_ms": 2345.67,
  "audit_id": "a1b2c3d4-...",
  "session_id": "uuid",
  "sources": []
}
```

### 8. Query — Tier 2 (RAG-Assisted)

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST002",
    "message": "What are the fees for international transfers to Australia?"
  }'
```

**Expected response:**
```json
{
  "final_response": "International transfers from Contoso carry a flat fee of £5.00 plus 0.5% of the amount...",
  "tier": 2,
  "agents_used": ["triage_agent", "resolution_agent"],
  "sources": ["International Transfers and Foreign Exchange"]
}
```

### 9. Query — Tier 3 (Human Escalation)

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST001",
    "message": "I want to make a formal complaint about unauthorised charges on my account"
  }'
```

**Expected response:**
```json
{
  "final_response": "Your request has been escalated to our specialist team. You will receive a response within 2 business hours.",
  "tier": 3,
  "agents_used": ["triage_agent", "draft_agent"]
}
```

### 10. Run E2E Demo (No Azure Required)

```bash
python demo_e2e.py
```

Tests chunking, mock tools (balance, transactions, card status), and model construction without any Azure services.

---

## Project Structure

```
contoso-support-agent/
├── .env.example                          # 18 environment variables template
├── demo_e2e.py                           # Offline demo (5 tests, no Azure needed)
├── pyproject.toml                        # pytest + ruff configuration
├── requirements.txt                      # 14 Python dependencies
│
├── orchestrator/                         # Pipeline orchestrator (port 8000)
│   ├── __init__.py
│   ├── main.py                           # FastAPI app: /health, /api/v1/query
│   ├── pipeline.py                       # SupportPipeline: triage → route → resolve/draft → audit
│   └── escalation.py                     # Human escalation handler (CRM stub)
│
├── triage_agent/                         # Query classification agent (port 8001)
│   ├── __init__.py
│   ├── agent.py                          # TriageAgent.classify() → TriageResult
│   ├── main.py                           # Standalone FastAPI: /api/v1/triage
│   ├── router.py                         # Confidence-based routing (threshold 0.7)
│   └── prompts.py                        # System prompt with 3 few-shot examples
│
├── resolution_agent/                     # RAG + tool-calling agent (port 8002)
│   ├── __init__.py
│   ├── agent.py                          # ResolutionAgent.resolve() with tool loop
│   ├── main.py                           # Standalone FastAPI: /api/v1/resolve
│   ├── retriever.py                      # HybridRetriever (vector + keyword + semantic)
│   ├── tools.py                          # 5 tools + mock data + handler functions
│   └── prompts.py                        # Resolution + auto-resolve system prompts
│
├── draft_agent/                          # Human review draft agent (port 8003)
│   ├── __init__.py
│   ├── agent.py                          # DraftAgent.draft() → DraftResult
│   ├── main.py                           # Standalone FastAPI: /api/v1/draft
│   ├── review_queue.py                   # ReviewQueue → Cosmos DB persistence
│   └── prompts.py                        # Draft system prompt
│
├── knowledge_base/                       # Document ingestion
│   ├── __init__.py
│   ├── chunker.py                        # RecursiveTextChunker (1000/200)
│   ├── indexer.py                        # Embed + index to Azure AI Search
│   └── documents/
│       └── sample_policies.md            # 367-line UK financial services policies
│
├── shared/                               # Cross-cutting concerns
│   ├── __init__.py
│   ├── config.py                         # Settings singleton (pydantic-settings)
│   ├── models.py                         # 8 Pydantic v2 models + 2 enums
│   ├── azure_clients.py                  # Singleton Azure service clients
│   ├── middleware.py                     # TracingMiddleware (correlation ID + latency)
│   └── logging_config.py                 # Structlog JSON configuration
│
├── tests/                                # Test suite
│   ├── __init__.py
│   ├── test_triage.py                    # 5 triage classification + routing tests
│   ├── test_resolution.py               # 7 tool handler unit tests
│   ├── test_pipeline_e2e.py             # 2 end-to-end pipeline tests
│   └── eval/
│       ├── triage_eval_set.jsonl         # 10 triage evaluation cases
│       └── resolution_eval_set.jsonl     # 10 resolution evaluation cases
│
└── infra/                                # Deployment
    ├── Dockerfile                        # Python 3.11-slim (shared by all services)
    ├── docker-compose.yml                # 4 services on bridge network
    └── ci-cd-pipeline.yml                # GitHub Actions: test → build
```

### Module Responsibility Matrix

| Module | Lines | Responsibility | Key Exports |
|--------|-------|---------------|-------------|
| `orchestrator/pipeline.py` | 149 | 4-phase support pipeline | `SupportPipeline` |
| `orchestrator/main.py` | 61 | FastAPI app, 2 endpoints | `app` |
| `orchestrator/escalation.py` | 36 | CRM escalation stub | `handle_escalation()` |
| `triage_agent/agent.py` | 79 | GPT-4o classification → Tier 1/2/3 | `TriageAgent` |
| `triage_agent/router.py` | 75 | Confidence-based routing | `determine_route()` |
| `triage_agent/prompts.py` | 49 | Few-shot triage system prompt | `TRIAGE_SYSTEM_PROMPT` |
| `resolution_agent/agent.py` | 156 | RAG + tool-calling loop (max 3) | `ResolutionAgent` |
| `resolution_agent/retriever.py` | 94 | Hybrid search (3 modes) | `HybridRetriever` |
| `resolution_agent/tools.py` | 193 | 5 tool definitions + mock data + handlers | `TOOL_DEFINITIONS`, `TOOL_HANDLERS` |
| `draft_agent/agent.py` | 89 | Empathetic draft generation | `DraftAgent` |
| `draft_agent/review_queue.py` | 55 | Cosmos DB review queue persistence | `ReviewQueue` |
| `knowledge_base/chunker.py` | 161 | Recursive text chunking with overlap | `RecursiveTextChunker` |
| `knowledge_base/indexer.py` | 149 | Document embedding + Azure AI Search upload | `index_documents()` |
| `shared/models.py` | 97 | 8 data models + 2 enums | All model classes |
| `shared/azure_clients.py` | 77 | Singleton Azure service clients | `AzureClients` |
| `shared/middleware.py` | 43 | Correlation ID + latency tracking | `TracingMiddleware` |

---

## API Reference

### Orchestrator (port 8000)

| Method | Path | Request Body | Response |
|--------|------|-------------|----------|
| `POST` | `/api/v1/query` | `CustomerQuery` | `PipelineResult` |
| `GET` | `/health` | — | `{"status": "healthy", "service": "orchestrator", "version": "1.0.0"}` |

### Triage Agent (port 8001)

| Method | Path | Request Body | Response |
|--------|------|-------------|----------|
| `POST` | `/api/v1/triage` | `CustomerQuery` | `{"triage_result": TriageResult, "route": dict}` |
| `GET` | `/health` | — | `{"status": "healthy", "service": "triage-agent"}` |

### Resolution Agent (port 8002)

| Method | Path | Request Body | Query Params | Response |
|--------|------|-------------|-------------|----------|
| `POST` | `/api/v1/resolve` | `CustomerQuery` | `auto_resolve: bool`, `category: str` | `ResolutionResult` |
| `GET` | `/health` | — | — | `{"status": "healthy", "service": "resolution-agent"}` |

### Draft Agent (port 8003)

| Method | Path | Request Body | Query Params | Response |
|--------|------|-------------|-------------|----------|
| `POST` | `/api/v1/draft` | `CustomerQuery` | `category: str` | `DraftResult` |
| `GET` | `/health` | — | — | `{"status": "healthy", "service": "draft-agent"}` |

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `AZURE_OPENAI_ENDPOINT` | `https://your-openai.openai.azure.com/` | Azure OpenAI endpoint |
| `AZURE_OPENAI_API_KEY` | `your-api-key` | Azure OpenAI API key |
| `AZURE_OPENAI_API_VERSION` | `2024-02-01` | API version |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4o` | Chat model deployment |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | `text-embedding-3-large` | Embedding model (3072d) |
| `AZURE_SEARCH_ENDPOINT` | `https://your-search.search.windows.net` | AI Search endpoint |
| `AZURE_SEARCH_API_KEY` | `your-search-key` | AI Search API key |
| `AZURE_SEARCH_INDEX_NAME` | `contoso-knowledge-base` | Search index name |
| `COSMOS_ENDPOINT` | `https://your-cosmos.documents.azure.com:443/` | Cosmos DB endpoint |
| `COSMOS_KEY` | `your-cosmos-key` | Cosmos DB key |
| `COSMOS_DATABASE` | `contoso-support` | Database name |
| `COSMOS_CONTAINER` | `audit-records` | Audit records container |
| `COSMOS_REVIEW_CONTAINER` | `review-queue` | Human review queue container |
| `TRIAGE_AGENT_URL` | `http://triage-agent:8001` | Triage service URL |
| `RESOLUTION_AGENT_URL` | `http://resolution-agent:8002` | Resolution service URL |
| `DRAFT_AGENT_URL` | `http://draft-agent:8003` | Draft service URL |
| `LOG_LEVEL` | `INFO` | Application log level |
| `USE_MANAGED_IDENTITY` | `false` | Use Azure Managed Identity |

---

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

**Expected output:**
```
========================= test session starts =========================
tests/test_triage.py::test_tier1_classification              PASSED
tests/test_triage.py::test_tier2_classification              PASSED
tests/test_triage.py::test_tier3_classification              PASSED
tests/test_triage.py::test_route_tier1                       PASSED
tests/test_triage.py::test_route_escalates_low_confidence    PASSED
tests/test_resolution.py::test_check_account_balance_known   PASSED
tests/test_resolution.py::test_check_account_balance_unknown PASSED
tests/test_resolution.py::test_get_recent_transactions       PASSED
tests/test_resolution.py::test_initiate_password_reset       PASSED
tests/test_resolution.py::test_check_card_status_blocked     PASSED
tests/test_resolution.py::test_get_policy_details            PASSED
tests/test_resolution.py::test_get_policy_details_unknown    PASSED
tests/test_pipeline_e2e.py::test_tier1_pipeline_flow         PASSED
tests/test_pipeline_e2e.py::test_pipeline_error_handling     PASSED

========================= 14 passed in 1.23s ============================
```

### Test Coverage

| Test File | Tests | What They Verify |
|-----------|-------|-----------------|
| `test_triage.py` | 5 | Tier 1/2/3 classification, Tier 1 routing, low-confidence escalation |
| `test_resolution.py` | 7 | All 5 tool handlers (known/unknown customers, policies) |
| `test_pipeline_e2e.py` | 2 | Full pipeline flow (mocked OpenAI), graceful error handling |

### Evaluation Datasets

**`tests/eval/triage_eval_set.jsonl`** — 10 cases:

| Message | Expected Tier | Expected Category | Min Confidence |
|---------|--------------|-------------------|----------------|
| Password forgotten | 1 | login_issue | 0.85 |
| Savings interest rate inquiry | 2 | product_inquiry | 0.80 |
| Formal mortgage complaint | 3 | formal_complaint | 0.90 |
| Unauthorised card purchases | 3 | fraud_report | 0.95 |
| Bereavement (husband passed) | 3 | bereavement | 0.95 |

**`tests/eval/resolution_eval_set.jsonl`** — 10 cases:

| Tier | Expected Tool | Expected Keywords |
|------|--------------|-------------------|
| 1 (auto) | `initiate_password_reset` | password, reset, email |
| 1 (auto) | `check_account_balance` | balance, account |
| 2 (RAG) | — (KB sources) | fee, transfer, international |
| 2 (RAG) | — (KB sources) | FSCS, 85,000, protected |

---

## Deployment

### Docker Compose (Recommended)

```bash
cd infra
docker-compose up --build
```

Starts all 4 services:

| Service | Port | Command |
|---------|------|---------|
| `orchestrator` | 8000 | `uvicorn orchestrator.main:app` |
| `triage-agent` | 8001 | `uvicorn triage_agent.main:app --port 8001` |
| `resolution-agent` | 8002 | `uvicorn resolution_agent.main:app --port 8002` |
| `draft-agent` | 8003 | `uvicorn draft_agent.main:app --port 8003` |

### Individual Docker Build

```bash
cd infra
docker build -t contoso-support .
docker run -p 8000:8000 --env-file ../.env contoso-support
```

### CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci-cd-pipeline.yml`):
1. **Test** — Python 3.11, install deps, `pytest tests/ -v --tb=short`
2. **Build** — Docker image tagged with `github.sha`

---

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|---------|
| `openai.AuthenticationError` | Invalid Azure OpenAI key | Verify `AZURE_OPENAI_API_KEY`; agents return fallback responses |
| All queries return Tier 2 | OpenAI unavailable (triage fallback) | Check OpenAI endpoint; triage defaults to Tier 2, confidence 0.5 |
| `"confidence": 0.0` in resolution | No documents in search index | Run `python knowledge_base/indexer.py` first |
| Audit records not appearing | Cosmos DB unavailable | Check `COSMOS_ENDPOINT`; pipeline continues without audit (logs warning) |
| Draft not in review queue | Cosmos review container missing | Create `review-queue` container in Cosmos DB |
| "0800-CONTOSO" apology response | Total pipeline failure | Check logs for root cause; this is the graceful last-resort |
| Port already in use | Another service on same port | Use `docker-compose` to manage all 4 services |
| `ModuleNotFoundError` | Dependencies not installed | Run `pip install -r requirements.txt` |
| Category filter returns empty | Category mismatch in search index | Verify `category` field values in indexed documents |
| Tool returns £1000 balance | Unknown customer_id | Mock data only has CUST001-003; unknown returns default |

---

## Azure Production Mapping

| Component | Azure Service | SKU/Tier | Purpose |
|-----------|--------------|----------|---------|
| **Chat LLM** | Azure OpenAI Service | GPT-4o | All 3 agents (triage, resolution, draft) |
| **Embeddings** | Azure OpenAI Service | text-embedding-3-large | 3072-dim document + query vectors |
| **Search** | Azure AI Search | Standard S1 | Hybrid vector + semantic + keyword retrieval |
| **Audit Store** | Azure Cosmos DB | Serverless | Audit records (compliance trail) |
| **Review Queue** | Azure Cosmos DB | Serverless | Human review drafts with priority |
| **Container Host** | Azure Container Apps | Consumption | 4 microservices (orchestrator + 3 agents) |
| **Identity** | Azure Managed Identity | — | Passwordless auth to all Azure services |
| **Secrets** | Azure Key Vault | Standard | API keys, connection strings |
| **Monitoring** | Azure Monitor + App Insights | — | Structured log ingestion, correlation ID tracing |
| **Registry** | Azure Container Registry | Basic | Docker image storage for CI/CD |
| **CRM Integration** | Dynamics 365 / Zendesk | — | Escalation handler (currently stubbed) |

### Production Checklist

- [ ] **Deploy GPT-4o** and `text-embedding-3-large` models in Azure OpenAI
- [ ] **Create AI Search** index with HNSW vector profile and semantic configuration
- [ ] **Create Cosmos DB** with `contoso-support` database, `audit-records` and `review-queue` containers
- [ ] **Replace mock tools** — integrate `check_account_balance`, `get_recent_transactions` etc. with real banking APIs
- [ ] **Replace mock policy corpus** — index actual corporate policies from SharePoint/Confluence
- [ ] **Enable Managed Identity** (`USE_MANAGED_IDENTITY=true`) for passwordless Azure auth
- [ ] **Restrict CORS** from `["*"]` to specific frontend domains
- [ ] **Add non-root user** to Dockerfile (`USER appuser`)
- [ ] **Implement CRM integration** in `escalation.py` (Salesforce, Zendesk, Dynamics 365)
- [ ] **Add rate limiting** on `/api/v1/query` endpoint
- [ ] **Configure App Insights** for structlog JSON ingestion
- [ ] **Set up alerts** on Tier 3 escalation volume and audit write failures
- [ ] **Add PII redaction** before writing customer messages to audit records

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.111.0 | REST API framework (all 4 services) |
| `uvicorn` | 0.30.0 | ASGI server |
| `openai` | 1.40.0 | Azure OpenAI SDK (chat + embeddings + tool calling) |
| `azure-search-documents` | 11.4.0 | Azure AI Search SDK (hybrid retrieval) |
| `azure-identity` | 1.16.0 | Azure Managed Identity support |
| `azure-cosmos` | 4.7.0 | Cosmos DB SDK (audit + review queue) |
| `pydantic` | 2.7.0 | Data validation / typed models |
| `pydantic-settings` | 2.3.0 | Settings from environment |
| `structlog` | 24.2.0 | Structured JSON logging |
| `python-dotenv` | 1.0.1 | `.env` file loading |
| `httpx` | 0.27.0 | Async HTTP client |
| `python-multipart` | 0.0.9 | Form data parsing (FastAPI) |
| `pytest` | 8.2.0 | Test framework |
| `pytest-asyncio` | 0.23.0 | Async test support |

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

**[⬆ Back to Top](#contoso-support-agent)**

*Part of [Prompt to Production](https://github.com/maneeshkumar52) — Chapter 22, Project 9*

</div>