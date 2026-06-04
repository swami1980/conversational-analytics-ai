"""
GitHub Issues MCP — Stub implementation.
Mirrors the SIM (System Issue Management) MCP used internally at Amazon.

Phase 1: In-memory stub that logs calls and returns realistic fake responses.
Phase 2 (next step): Replace with real GitHub API calls using GITHUB_TOKEN.
         Each tool function has a `_real_*` counterpart showing the production path.
"""
import uuid
from datetime import datetime

_issue_log: list[dict] = []


def search_github_issues(query: str, repo: str = "") -> dict:
    """
    Search existing GitHub Issues for known errors or troubleshooting guides.
    Stub: returns a curated set of fake issues matching common recruiting AI errors.
    """
    sample_issues = [
        {
            "number": 42,
            "title": "ChromaDB connection timeout on cold start",
            "body": "If ChromaDB returns timeout on first query, ensure persist_dir has write permissions.",
            "labels": ["bug", "chromadb"],
            "state": "closed",
            "url": f"https://github.com/{repo}/issues/42",
        },
        {
            "number": 37,
            "title": "Strands agent loop limit exceeded for complex multi-API queries",
            "body": "Increase max_iterations in Agent config if queries spanning 4+ APIs time out.",
            "labels": ["performance"],
            "state": "open",
            "url": f"https://github.com/{repo}/issues/37",
        },
        {
            "number": 55,
            "title": "JWT token expiry not refreshed in frontend",
            "body": "Frontend should call /auth/refresh before expiry. Current TTL is 8 hours.",
            "labels": ["auth", "frontend"],
            "state": "open",
            "url": f"https://github.com/{repo}/issues/55",
        },
    ]
    query_lower = query.lower()
    matched = [
        i for i in sample_issues
        if any(kw in i["title"].lower() or kw in i["body"].lower() for kw in query_lower.split())
    ]
    return {
        "stub": True,
        "query": query,
        "total_matches": len(matched),
        "issues": matched or sample_issues[:1],
        "note": "Stub response — connect GITHUB_TOKEN to enable real search.",
    }


def create_github_issue(title: str, body: str, labels: list[str] | None = None) -> dict:
    """
    Create a GitHub Issue to track a recruiting AI error or anomaly.
    Stub: logs to in-memory store and returns a fake issue number.
    """
    issue_number = 100 + len(_issue_log) + 1
    issue = {
        "number": issue_number,
        "title": title,
        "body": body,
        "labels": labels or ["agent-reported"],
        "state": "open",
        "created_at": datetime.utcnow().isoformat(),
        "stub_id": str(uuid.uuid4()),
    }
    _issue_log.append(issue)
    return {
        "stub": True,
        "created": True,
        "issue": issue,
        "url": f"https://github.com/stub-repo/issues/{issue_number}",
        "note": "Stub response — set GITHUB_TOKEN and GITHUB_REPO in .env to create real issues.",
    }


def get_issue_log() -> list[dict]:
    """Return all stub issues created this session (for debugging/demo)."""
    return _issue_log


# ---------------------------------------------------------------------------
# Phase 2 production implementation (commented — requires GITHUB_TOKEN)
# ---------------------------------------------------------------------------
# import httpx
#
# def _real_create_github_issue(title, body, labels, token, repo):
#     resp = httpx.post(
#         f"https://api.github.com/repos/{repo}/issues",
#         headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
#         json={"title": title, "body": body, "labels": labels or []},
#     )
#     resp.raise_for_status()
#     data = resp.json()
#     return {"number": data["number"], "url": data["html_url"], "state": data["state"]}
