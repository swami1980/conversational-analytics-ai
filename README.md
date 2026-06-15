# Conversational Recruiting Analytics AI

A production-faithful prototype of a multi-agent recruiting analytics assistant. Recruiters can ask natural-language questions about open reqs, candidate pipelines, headcount, and hiring metrics — the system reasons across 7 internal APIs in real time.

[![LLM-as-Judge CI](https://github.com/swami1980/conversational-analytics-ai/actions/workflows/llm-judge.yml/badge.svg)](https://github.com/swami1980/conversational-analytics-ai/actions/workflows/llm-judge.yml)

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Browser (React + Vite)                       │
│  ┌────────────────────────┐   ┌──────────────────────────────────┐  │
│  │     Chat Window        │   │   Agent Reasoning Panel (SSE)    │  │
│  │  • Message thread      │   │  • Live tool call transparency   │  │
│  │  • Follow-up chips     │   │  • search_knowledge_base calls   │  │
│  │    (Claude Haiku)      │   │  • call_api / call_apis_parallel │  │
│  └────────────────────────┘   └──────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTPS (SSE stream)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (port 8000)                     │
│                                                                      │
│  ┌─────────────────┐    ┌──────────────────────────────────────┐   │
│  │  JWT Auth +     │    │        Strands Agent Orchestrator     │   │
│  │  RBAC Middleware│───▶│         (Claude Sonnet 4.6)           │   │
│  │  (3 roles)      │    │                                      │   │
│  └─────────────────┘    │  1. search_knowledge_base            │   │
│                          │     └─▶ TF-IDF Vector Store          │   │
│                          │        (7 OpenAPI specs, in-memory)  │   │
│                          │  2. call_api / call_apis_parallel    │   │
│                          │     └─▶ 7 Mock REST APIs (internal) │   │
│                          │  3. search/create GitHub Issues      │   │
│                          │     └─▶ GitHub MCP (stubbed)         │   │
│                          └──────────────┬───────────────────────┘   │
│                                         │                            │
│  ┌──────────────────┐    ┌──────────────▼────────────────────┐     │
│  │  SQLite Session  │    │   Claude Sonnet (Summarizer pass)  │     │
│  │  Memory          │    │   Claude Haiku  (Follow-up sugg.)  │     │
│  │  (15-turn window)│    └───────────────────────────────────┘     │
│  └──────────────────┘                                               │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    7 Mock REST APIs                           │  │
│  │  /internal/v1/requisitions    /internal/v1/candidates        │  │
│  │  /internal/v1/employees       /internal/v1/pending-starts    │  │
│  │  /internal/v1/interview-events                               │  │
│  │  /internal/v1/interview-metrics  /internal/v1/historical-data│  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      GitHub Actions CI/CD                            │
│  LLM-as-Judge: 25 representative questions → Claude Sonnet scores   │
│  each answer on Correctness + Recruiter-friendliness + Groundedness │
│  Fails CI if pass rate < 80%                                        │
└─────────────────────────────────────────────────────────────────────┘
```

## End-to-End Request Flow

```
User types question → hits Ask
         │
         ▼
[Browser] POST /api/v1/chat/stream
  • JWT token in Authorization header
  • {session_id, message} in body
         │
         ▼
[FastAPI Auth Middleware] — AuthN + AuthZ gate
  • Verifies JWT signature and expiry                    ← Authentication
  • Extracts: user_id, role (recruiter/hiring_manager/admin)
  • Role check: only authenticated roles reach the agent  ← Authorization
  • Attaches user context to request state
  • 401 if token invalid → 403 if role not permitted
         │
         ▼
[FastAPI] Session setup
  • Loads last 15 turns from SQLite (conversation context)
  • Opens SSE pipe back to browser
  • Spins up Strands agent in background thread
  • Passes role into agent system prompt context
         │
         ▼
[Strands Agent] — Step 1: Knowledge Base Lookup
  • Calls search_knowledge_base("open SDE L5 reqs Seattle")
  • TF-IDF cosine search over 7 indexed OpenAPI specs
  • Returns: endpoint path, parameters, description
  ─── SSE event: tool_call ──────────────────────▶ Browser (Tool Panel)
  ─── SSE event: tool_result ────────────────────▶ Browser (Tool Panel)
         │
         ▼
[Strands Agent] — Step 2: API Call(s)
  • Single domain → call_api(endpoint, params)
  • Multi domain  → call_apis_parallel([...])  via asyncio.gather
  • httpx hits /internal/v1/requisitions?job_family=SDE&level=L5&location=Seattle
  ─── SSE event: tool_call ──────────────────────▶ Browser (Tool Panel)
  ─── SSE event: tool_result ────────────────────▶ Browser (Tool Panel)
         │
         ▼
[RBAC Data Filter] — Row-level permission enforcement  ← Authorization
  • recruiter / admin  → full dataset returned as-is
  • hiring_manager     → results filtered to rows where
                         hiring_manager_id = user's employee_id
  • Ensures a hiring manager never sees another manager's
    candidates, reqs, or pipeline data
         │
         ▼
[Claude Sonnet] — Summarizer pass
  • Raw (already filtered) API JSON → recruiter-friendly markdown
  • Bold numbers, tables, Key Takeaway line
  ─── SSE event: final_answer ───────────────────▶ Browser (Chat Window)
         │
         ▼
[SQLite] Message persisted
  • User message + assistant response saved
  • Window enforced: oldest turn dropped if > 15
         │
         ▼
[Claude Haiku] — Follow-up suggestions
  • Looks at last 3 Q&A pairs
  • Generates 3 contextual next questions
  ─── SSE event: follow_up_questions ────────────▶ Browser (Chips below answer)
         │
         ▼
  ─── SSE event: done ───────────────────────────▶ Browser closes pipe
```

## Quick Start (Docker — one command)

```bash
git clone https://github.com/swami1980/conversational-analytics-ai
cd conversational-analytics-ai
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

**Demo credentials:**

| Username     | Password      | Role                           |
| ------------ | ------------- | ------------------------------ |
| `recruiter1` | `password123` | Recruiter (full view)          |
| `hm_alice`   | `password123` | Hiring Manager (own reqs only) |
| `admin`      | `admin123`    | Admin (full access)            |

## Local Development (no Docker)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env  # edit and add ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev  # http://localhost:3000
```

## Example Questions

- "How many open SDE L5 reqs do we have in Seattle?"
- "What is the offer acceptance rate trend for AWS this year?"
- "Which candidates are closest to receiving an offer?"
- "Show me the Bar Raiser schedule for the next two weeks."
- "Give me a full recruiting health check for Prime Video."
- "Which orgs are behind on their hiring plan?"
- "Are there any onboarding risks — pending starts without a laptop?"

## Key Design Decisions

### Wiki Knowledge Base

The knowledge base indexes two document types — OpenAPI specs
(chunked per endpoint)
and wiki pages (chunked per H2 section). This means the agent
can answer both data
questions ("how many open reqs?") and conceptual questions
("what is a requisition?",
"what does this app do?") from the same search. A balanced
search ensures at least one
result from each source type is always returned.

### API Agent + TF-IDF Knowledge Base

The agent never hardcodes API endpoints. For every question it first calls `search_knowledge_base`, which runs a TF-IDF cosine similarity search over the 7 OpenAPI specs indexed in memory at startup. The returned spec snippets tell the agent exactly which endpoint to call and what parameters to use — no guessing, no hardcoding.

The knowledge base is built entirely in pure Python (numpy) with no native binary dependencies, making it compatible with any Python 3.11+ environment. In production this swaps to a managed vector store such as Amazon OpenSearch Serverless.

### Multi-API Parallel Orchestration

Cross-domain questions (e.g., "health check for AWS: open reqs, pipeline, and time-to-hire") trigger `call_apis_parallel`, which uses `asyncio.gather` to fan out HTTP calls concurrently. A Strands callback emits each call as an SSE event, visible in the tool call transparency panel in real time.

### JWT + RBAC

- `recruiter` / `admin`: see all data across all orgs
- `hiring_manager`: data is automatically filtered to records matching their `employee_id`

### Session Memory

SQLite stores conversation history per session with a 15-turn sliding window — older messages are pruned automatically. In production this swaps to DynamoDB with TTL.

### GitHub Issues MCP

When the agent encounters data anomalies or errors, it can search known issues or file new ones. Currently stubbed with realistic in-memory responses. Set `GITHUB_TOKEN` and `GITHUB_REPO` in `.env` to enable real integration.

## AWS Production Migration Path

| Component      | Prototype                              | AWS Production                        |
| -------------- | -------------------------------------- | ------------------------------------- |
| Orchestrator   | Strands Agents SDK (Anthropic API)     | Strands Agents SDK (Amazon Bedrock)   |
| Knowledge Base | TF-IDF vector store (numpy, in-memory) | Amazon OpenSearch Serverless          |
| Session Memory | SQLite (file)                          | Amazon DynamoDB (TTL-enabled)         |
| Auth           | JWT (HS256, local secret)              | Amazon Cognito + corporate SSO        |
| Auth scopes    | RBAC middleware                        | Amazon Verified Permissions           |
| Mock APIs      | FastAPI routers (same process)         | Microservices on Amazon ECS / Lambda  |
| MCP            | GitHub Issues stub                     | Issue tracking MCP (real integration) |
| CI/CD          | GitHub Actions                         | Amazon CodePipeline + CodeBuild       |
| Hosting        | Docker Compose (local)                 | Amazon ECS Fargate + CloudFront       |

## Repository Structure

```
├── backend/
│   └── app/
│       ├── main.py              # FastAPI app, lifespan startup
│       ├── config.py            # Pydantic settings from .env
│       ├── seed_data/           # Realistic data generator (seed 42)
│       ├── mock_apis/           # 7 FastAPI routers (internal endpoints)
│       ├── openapi_specs/       # 7 YAML specs indexed at startup
│       ├── knowledge_base/      # TF-IDF vector store (numpy)
│       ├── memory/              # SQLite 15-turn session store
│       ├── auth/                # JWT handler + RBAC middleware
│       ├── mcp/                 # GitHub Issues stub
│       └── agents/
│           ├── tools.py         # @tool definitions for Strands
│           ├── orchestrator.py  # Strands Agent + SSE streaming
│           └── summarizer.py    # Claude Sonnet format + Haiku follow-up
│       ├── wiki/                # Markdown pages: app
|           |__overview, glossary, data guide
├── frontend/
│   └── src/
│       ├── App.jsx              # Root — auth gate + layout
│       ├── components/          # ChatWindow, Message, ToolCallPanel, etc.
│       ├── hooks/useChat.js     # SSE state machine
│       └── api/client.js        # Fetch wrappers
├── judge/
│   ├── questions.json           # 25 representative questions
│   └── run_judge.py            # LLM-as-judge harness
└── .github/workflows/
    └── llm-judge.yml           # CI: runs judge, posts results to PR
```

## GitHub Actions Setup

Add `ANTHROPIC_API_KEY` as a repository secret:
**Settings → Secrets and variables → Actions → New repository secret**

The LLM judge runs on every push to `main` and posts a results table to pull requests.
