"""
Recruiting Analytics AI — MCP Server

Exposes the full recruiting AI agent as a single MCP tool: ask_recruiting_ai.
Any MCP-compatible client (Claude Desktop, custom agents) can invoke the
complete pipeline — KB lookup, API orchestration, Sonnet formatting — with
one natural language question.

Transports:
  HTTP/SSE  → mounted at /mcp/sse in the FastAPI app (for web clients)
  stdio     → scripts/mcp_stdio.py entry point (for Claude Desktop)

Production: deploy as AWS Lambda behind API Gateway instead of FastAPI mount.
"""
from queue import Queue
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="Recruiting Analytics AI",
    instructions=(
        "You have access to a recruiting analytics AI assistant that covers "
        "7 internal data domains: requisitions, candidate pipeline, employees, "
        "pending starts, interview events, interview metrics, and historical headcount data. "
        "Use ask_recruiting_ai for any recruiting question — data queries AND conceptual "
        "questions (e.g. 'what is a Bar Raiser?', 'what does this app do?'). "
        "The tool handles everything internally."
    ),
)


@mcp.tool()
def ask_recruiting_ai(question: str, role: str = "recruiter") -> str:
    """
    Ask the recruiting analytics AI a natural language question.

    Handles all recruiting questions including:
    - Data queries: open reqs, candidate pipeline, headcount, hiring metrics,
      pending starts, interview schedules, offer acceptance rates, attrition trends
    - Conceptual questions: what is a requisition, what is a Bar Raiser,
      what does this app do, how to interpret metrics
    - Cross-domain questions: health checks spanning multiple data sources

    The tool runs the full internal pipeline:
    knowledge base lookup → API orchestration → Sonnet formatting.

    Args:
        question: Natural language question about recruiting data or concepts
        role: Caller's access role — recruiter, hiring_manager, or admin.
              hiring_manager role automatically scopes data to their own reqs.
              Defaults to recruiter (full read access).

    Returns:
        Formatted markdown answer ready to present to the user
    """
    from app.agents.orchestrator import run_agent
    from app.agents.summarizer import format_response

    event_queue: Queue = Queue()

    raw = run_agent(
        user_message=question,
        history=[],
        event_queue=event_queue,
        user_role=role,
    )

    try:
        formatted = format_response(raw, question)
    except Exception:
        formatted = raw

    return formatted
