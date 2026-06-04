"""
Strands @tool definitions.
The agent retrieves OpenAPI specs from ChromaDB at runtime, then constructs
HTTP requests from those specs — it never generates raw SQL or hardcoded queries.
"""
import json
import asyncio
from typing import Any
import httpx
from strands import tool

from app.knowledge_base import search as kb_search
from app.mcp.github_stub import search_github_issues as _gh_search, create_github_issue as _gh_create
from app.config import get_settings

_settings = get_settings()


@tool
def search_knowledge_base(query: str, top_k: int = 4) -> str:
    """
    Search the OpenAPI specification knowledge base to find relevant API endpoints.
    Always call this FIRST before making any API call so you know the correct
    endpoint path, parameters, and expected response shape.

    Args:
        query: Natural language description of the data you need (e.g.
               "open SDE L5 requisitions in Seattle", "offer acceptance rate by quarter")
        top_k: Number of relevant spec snippets to return (default 4)

    Returns:
        Relevant OpenAPI spec snippets showing endpoint paths, parameters, and descriptions
    """
    hits = kb_search(query, n_results=top_k, persist_dir=_settings.chroma_persist_dir)
    if not hits:
        return "No matching API specs found. The recruiting system has 7 APIs: Requisitions, Candidates, Employees, Pending Starts, Interview Events, Interview Metrics, and Historical Data."
    lines = []
    for i, hit in enumerate(hits, 1):
        lines.append(f"[Result {i}]\n{hit['text']}\n")
    return "\n".join(lines)


@tool
def call_api(
    api_name: str,
    endpoint: str,
    method: str = "GET",
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> str:
    """
    Call a single recruiting mock API endpoint. Always call search_knowledge_base
    first to verify the correct endpoint path and parameters before calling this.

    Args:
        api_name: Human-readable API name for logging (e.g. "Requisitions API")
        endpoint: Full endpoint path from the spec (e.g. "/internal/v1/requisitions",
                  "/internal/v1/candidates/pipeline/summary",
                  "/internal/v1/interview-metrics/conversion-funnel")
        method: HTTP method — GET (default) or POST
        params: Query parameters as a dict (e.g. {"status": "Open", "location": "Seattle"})
        body: Request body for POST requests (optional)

    Returns:
        JSON response from the API as a formatted string
    """
    base = _settings.mock_api_base_url.rstrip("/")
    url = f"{base}{endpoint}"
    # Remove None values from params
    clean_params = {k: v for k, v in (params or {}).items() if v is not None}
    try:
        with httpx.Client(timeout=10.0) as client:
            if method.upper() == "GET":
                resp = client.get(url, params=clean_params)
            else:
                resp = client.post(url, json=body or {}, params=clean_params)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                count = data.get("total", len(data["data"]))
                preview = data["data"][:20]
                return json.dumps({"total": count, "returned": len(preview), "data": preview}, indent=2, default=str)
            return json.dumps(data, indent=2, default=str)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"HTTP {e.response.status_code}", "detail": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def call_apis_parallel(calls: list[dict[str, Any]]) -> str:
    """
    Execute multiple API calls in parallel for cross-domain questions.
    Use this when a question requires data from 2 or more different APIs simultaneously.
    This is more efficient than calling each API sequentially.

    Args:
        calls: List of API call specs. Each dict must have:
               - api_name (str): Human-readable name for logging
               - endpoint (str): Full endpoint path from the spec
               - method (str, optional): "GET" or "POST", defaults to "GET"
               - params (dict, optional): Query parameters
               - body (dict, optional): POST body

    Returns:
        Combined JSON results from all API calls, labeled by api_name
    """
    async def _fetch_one(call: dict) -> dict:
        base = _settings.mock_api_base_url.rstrip("/")
        url = f"{base}{call['endpoint']}"
        clean_params = {k: v for k, v in (call.get("params") or {}).items() if v is not None}
        method = call.get("method", "GET").upper()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if method == "GET":
                    resp = await client.get(url, params=clean_params)
                else:
                    resp = await client.post(url, json=call.get("body") or {}, params=clean_params)
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                    count = data.get("total", len(data["data"]))
                    return {"api": call["api_name"], "total": count, "data": data["data"][:20]}
                return {"api": call["api_name"], "data": data}
        except Exception as e:
            return {"api": call["api_name"], "error": str(e)}

    async def _run_all():
        return await asyncio.gather(*[_fetch_one(c) for c in calls])

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _run_all())
                results = future.result(timeout=30)
        else:
            results = loop.run_until_complete(_run_all())
    except Exception as e:
        results = [{"error": str(e)}]

    combined = {r.get("api", f"call_{i}"): r for i, r in enumerate(results)}
    return json.dumps(combined, indent=2, default=str)


@tool
def search_github_issues(query: str) -> str:
    """
    Search GitHub Issues for known errors, bugs, or troubleshooting guides related
    to the recruiting analytics system. Use this when the user reports an error
    or when API calls return unexpected results.

    Args:
        query: Description of the error or issue to search for

    Returns:
        Matching GitHub Issues with titles, descriptions, and links
    """
    result = _gh_search(query, repo=_settings.github_repo)
    return json.dumps(result, indent=2)


@tool
def create_github_issue(title: str, body: str, labels: list[str] | None = None) -> str:
    """
    Create a GitHub Issue to track a data anomaly, system error, or unexpected
    behavior discovered during a recruiting analytics session.

    Args:
        title: Short, descriptive issue title (e.g. "API returns 0 candidates for open SDE L5 reqs")
        body: Detailed description including the query, expected result, and actual result
        labels: Optional list of labels (e.g. ["data-quality", "api-bug"])

    Returns:
        Confirmation with issue number and URL
    """
    result = _gh_create(title, body, labels)
    return json.dumps(result, indent=2)


ALL_TOOLS = [search_knowledge_base, call_api, call_apis_parallel, search_github_issues, create_github_issue]
