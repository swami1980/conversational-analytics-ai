#!/usr/bin/env python3
"""
stdio entry point for Claude Desktop and local MCP clients.

Claude Desktop config (~/.claude/claude_desktop_config.json):
{
  "mcpServers": {
    "recruiting-ai": {
      "command": "python3",
      "args": ["/absolute/path/to/scripts/mcp_stdio.py"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}

See mcp_config/claude_desktop_config.json for a ready-to-use example.
"""
import sys
import os

# Add backend to path so app.* imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

# Boot the seed data + knowledge base before serving
from app.seed_data import init_store
from app.knowledge_base import build_index

init_store()
build_index()

# Run MCP server over stdio
from app.mcp_server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
