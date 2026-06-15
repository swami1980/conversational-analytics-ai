from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from app.config import get_settings
from app.seed_data import init_store
from app.knowledge_base import build_index
from app.memory import init_db
from app.auth.jwt_handler import authenticate_user, create_token
from app.auth.middleware import get_current_user
from app.mock_apis import (
    requisitions_router, candidates_router, employees_router,
    pending_starts_router, interview_events_router,
    interview_metrics_router, historical_data_router,
)
from app.api.chat import router as chat_router
from app.mcp.github_stub import get_issue_log
from app.mcp_server import mcp

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed data → SQLite → ChromaDB index
    init_store()
    init_db(settings.sqlite_db_path)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, build_index, settings.chroma_persist_dir)
    print("✓ Seed data loaded")
    print("✓ SQLite session store initialized")
    print("✓ ChromaDB OpenAPI specs indexed")
    yield


app = FastAPI(
    title="Conversational Recruiting Analytics AI",
    description=(
        "Multi-agent recruiting analytics assistant. "
        "Strands SDK orchestrator · ChromaDB knowledge base · 7 mock APIs · JWT auth."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth
@app.post("/api/v1/auth/token", tags=["Auth"])
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form.username, form.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_token(user, settings.jwt_secret_key, settings.jwt_algorithm, settings.jwt_expire_minutes)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user["user_id"],
            "full_name": user["full_name"],
            "role": user["role"],
            "email": user["email"],
        },
    }


@app.get("/api/v1/auth/me", tags=["Auth"])
def me(user: dict = Depends(get_current_user)):
    return user


# MCP debug endpoint (demo only)
@app.get("/api/v1/mcp/issues", tags=["MCP"])
def stub_issues(_: dict = Depends(get_current_user)):
    return {"stub_issues": get_issue_log()}


# Health
@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "version": "1.0.0"}


# Mount 7 mock API routers (internal — agent calls these via HTTP)
app.include_router(requisitions_router)
app.include_router(candidates_router)
app.include_router(employees_router)
app.include_router(pending_starts_router)
app.include_router(interview_events_router)
app.include_router(interview_metrics_router)
app.include_router(historical_data_router)

# Chat (public-facing agent endpoint)
app.include_router(chat_router)

# MCP server — SSE transport at /mcp/sse
# Claude Desktop / other MCP clients connect here
app.mount("/mcp", mcp.sse_app())
