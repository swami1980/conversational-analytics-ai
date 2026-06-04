# Conversational Recruiting Analytics AI

A production-faithful prototype of a multi-agent recruiting analytics assistant, mirroring an internal system built at Amazon. Recruiters can ask natural-language questions about open reqs, candidate pipelines, headcount, and hiring metrics — the system reasons across 7 internal APIs in real time.

[![LLM-as-Judge CI](https://github.com/YOUR_USERNAME/conversational-analytics-ai/actions/workflows/llm-judge.yml/badge.svg)](https://github.com/YOUR_USERNAME/conversational-analytics-ai/actions/workflows/llm-judge.yml)

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
│  │  RBAC Middleware│───▶│  (mirrors mwinit + Bindle pattern)   │   │
│  │  (3 roles)      │    │                                      │   │
│  └─────────────────┘    │  1. search_knowledge_base            │   │
│                          │     └─▶ ChromaDB (7 OpenAPI specs)  │   │
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

## Agent Reasoning Flow

```
User Query
    │
    ▼
1. search_knowledge_base(query)
   → ChromaDB similarity search over 7 OpenAPI specs
   → Returns: endpoint paths, parameters, descriptions

    │
    ▼
2a. call_api(api, endpoint, params)          ← single-domain question
2b. call_apis_parallel([call1, call2, ...])  ← cross-domain question

    │
    ▼
3. Claude Sonnet (Summarizer)
   → Formats raw API response into recruiter-friendly markdown

    │
    ▼
4. Claude Haiku (Follow-up suggestions)
   → Generates 3 contextual follow-up questions from last 3 Q&A pairs

    │
    ▼
SSE stream → Browser (tool calls visible in real time)
```

## Quick Start (Docker — one command)

```bash
git clone https://github.com/YOUR_USERNAME/conversational-analytics-ai
cd conversational-analytics-ai
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

**Demo credentials:**

| Username | Password | Role |
|---|---|---|
| `recruiter1` | `password123` | Recruiter (full view) |
| `hm_alice` | `password123` | Hiring Manager (own reqs only) |
| `admin` | `admin123` | Admin (full access) |

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

### API Agent + ChromaDB RAG
The agent never hardcodes API endpoints. For every question it first calls `search_knowledge_base`, which performs a semantic search over the OpenAPI specs indexed in ChromaDB. The returned spec snippets tell the agent exactly which endpoint to call and what parameters to use. This mirrors how a human analyst would consult API documentation before querying a system.

### Multi-API Parallel Orchestration
Cross-domain questions (e.g., "health check for AWS: open reqs, pipeline, and time-to-hire") trigger `call_apis_parallel`, which uses `asyncio.gather` to fan out HTTP calls concurrently. A Strands orchestration callback emits each call as an SSE event, visible in the tool call transparency panel.

### JWT + RBAC
- `recruiter` / `admin`: see all data
- `hiring_manager`: data is filtered to records matching their `employee_id` as `hiring_manager_id`

Mirrors the mwinit (authentication) + Bindle (authorization scopes) pattern used internally at Amazon.

### Session Memory
SQLite stores conversation history per session. A 15-turn sliding window is enforced — older messages are pruned. In production this swaps to DynamoDB with TTL.

### GitHub Issues MCP
When the agent encounters data anomalies or errors, it can search known issues or file new ones. Currently stubbed with realistic in-memory responses. Set `GITHUB_TOKEN` and `GITHUB_REPO` in `.env` to enable real integration.

## AWS Production Migration Path

| Component | Prototype | AWS Production |
|---|---|---|
| Orchestrator | Strands Agents SDK (Anthropic API) | Strands Agents SDK (Amazon Bedrock) |
| Knowledge Base | ChromaDB (local PersistentClient) | Amazon OpenSearch Serverless |
| Session Memory | SQLite (file) | Amazon DynamoDB (TTL-enabled) |
| Auth | JWT (HS256, local secret) | Amazon Cognito + corporate SSO (Midway) |
| Auth scopes | RBAC middleware | Amazon Verified Permissions (Bindle) |
| Mock APIs | FastAPI routers (same process) | Microservices on Amazon ECS / Lambda |
| MCP | GitHub Issues stub | Internal SIM (System Issue Management) MCP |
| CI/CD | GitHub Actions | Amazon CodePipeline + CodeBuild |
| Hosting | Docker Compose (local) | Amazon ECS Fargate + CloudFront |

## Repository Structure

```
├── backend/
│   └── app/
│       ├── main.py              # FastAPI app, lifespan startup
│       ├── config.py            # Pydantic settings from .env
│       ├── seed_data/           # Amazon-style data generator (seed 42)
│       ├── mock_apis/           # 7 FastAPI routers (internal endpoints)
│       ├── openapi_specs/       # 7 YAML specs indexed into ChromaDB
│       ├── knowledge_base/      # ChromaDB indexing + search
│       ├── memory/              # SQLite 15-turn session store
│       ├── auth/                # JWT handler + RBAC middleware
│       ├── mcp/                 # GitHub Issues stub
│       └── agents/
│           ├── tools.py         # @tool definitions for Strands
│           ├── orchestrator.py  # Strands Agent + SSE streaming
│           └── summarizer.py    # Claude Sonnet format + Haiku follow-up
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
