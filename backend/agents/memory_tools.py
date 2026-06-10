"""In-process MCP "memory" server for the EE Toolbox agent team (Task A7).

A SEPARATE SDK server from the "ee" tools server (stub_tools.py /
retrieval_tools.py -- neither is touched). Four tools over the SQLite-backed
``persistence.MemoryStore`` (backend/data/agent_store.db, WAL mode):

  - mcp__memory__memory_store    -- store one memory under a fixed category
  - mcp__memory__memory_recall   -- ranked FTS5/bm25 search (+ seeded taxonomy)
  - mcp__memory__memory_list     -- compact listing, newest first
  - mcp__memory__memory_forget   -- hard-delete one memory by id

Prompt routing lives in the tool DESCRIPTIONS below (the SDK surfaces them to
the model): prompts/orchestrator.md is owned by Task A5 this wave, so guidance
on WHEN to store/recall is carried here instead.

Session binding follows the pragmatic "ee"-server pattern: an optional
explicit ``session_id`` argument; default None means the memory is global.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from persistence.memory import VALID_CATEGORIES, MemoryStore

logger = logging.getLogger(__name__)

# Module-level store: connections are short-lived per operation, so sharing
# one MemoryStore across calls is safe (no event-loop-bound state).
_STORE = MemoryStore()

_CATEGORY_LIST = ", ".join(VALID_CATEGORIES)


def _ok(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": [{
            "type": "text",
            "text": json.dumps(payload, ensure_ascii=False, indent=1),
        }]
    }


def _err(message: str) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": message}],
        "is_error": True,
    }


_MEMORY_STORE_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": list(VALID_CATEGORIES),
            "description": f"Memory category. One of: {_CATEGORY_LIST}.",
        },
        "content": {
            "type": "string",
            "description": (
                "The memory text to persist (1-3 sentences; self-contained "
                "so it makes sense when recalled later without context)."
            ),
        },
        "session_id": {
            "type": "string",
            "description": (
                "Optional session UUID to bind the memory to. Omit for "
                "memories that should apply across all sessions."
            ),
        },
    },
    "required": ["category", "content"],
}


@tool(
    "memory_store",
    "Persist a durable memory across sessions and backend restarts. Use this "
    "when the user ACCEPTS a pathway or recommendation (category "
    "'accepted_pathways'), when a challenge is articulated or refined "
    "('challenge_context'), when tools are shortlisted or rejected "
    "('tool_recommendations'), when the user states preferences such as "
    "country, language or format ('user_preferences'), and for explicit "
    "positive/negative feedback ('feedback_signals'). Store concise, "
    f"self-contained statements. Valid categories: {_CATEGORY_LIST}.",
    _MEMORY_STORE_SCHEMA,
)
async def memory_store(args: dict[str, Any]) -> dict[str, Any]:
    category = str(args.get("category") or "").strip()
    content = str(args.get("content") or "").strip()
    session_id = (str(args.get("session_id") or "").strip()) or None
    try:
        result = await _STORE.store(category, content, session_id=session_id)
    except Exception as exc:
        logger.exception("memory_store failed")
        return _err(f"memory_store error: {exc}")
    if "error" in result:
        return _err(result["error"])
    return _ok(result)


_MEMORY_RECALL_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": (
                "Free-text search over stored memories (full-text, ranked). "
                "Keywords work best (e.g. 'pillar climate', 'accepted "
                "pathway Kenya')."
            ),
        },
        "category": {
            "type": "string",
            "enum": list(VALID_CATEGORIES),
            "description": (
                "Optional category filter. Omit to search everything, "
                "including seeded reference knowledge (the eight-pillar "
                "taxonomy and the tool-metadata schema)."
            ),
        },
        "limit": {
            "type": "integer",
            "description": "Maximum results to return (default 10, max 50).",
        },
    },
    "required": ["query"],
}


@tool(
    "memory_recall",
    "Search persistent memories by free text (FTS5, bm25-ranked). Call this "
    "at the START of a session with the user's topic to surface prior "
    "'challenge_context', 'accepted_pathways' and 'user_preferences' from "
    "earlier visits. Without a category filter, results also include seeded "
    "reference knowledge: the eight EE pillar definitions and the "
    "tool-metadata schema (source 'seed_knowledge').",
    _MEMORY_RECALL_SCHEMA,
)
async def memory_recall(args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query") or "").strip()
    if not query:
        return _err("Error: 'query' must be a non-empty string.")
    category = (str(args.get("category") or "").strip()) or None
    try:
        limit = int(args.get("limit") or 10)
    except (TypeError, ValueError):
        limit = 10
    try:
        result = await _STORE.recall(query, category=category, limit=limit)
    except Exception as exc:
        logger.exception("memory_recall failed for query %r", query)
        return _err(f"memory_recall error: {exc}")
    if "error" in result:
        return _err(result["error"])
    return _ok(result)


_MEMORY_LIST_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": list(VALID_CATEGORIES),
            "description": "Optional category filter. Omit to list all.",
        },
        "limit": {
            "type": "integer",
            "description": "Maximum entries to return (default 50, max 200).",
        },
    },
    "required": [],
}


@tool(
    "memory_list",
    "List stored memories (newest first), optionally filtered by category. "
    "Use to review what is already remembered -- e.g. all "
    "'accepted_pathways' before drafting a report -- or to find a memory id "
    f"for memory_forget. Valid categories: {_CATEGORY_LIST}.",
    _MEMORY_LIST_SCHEMA,
)
async def memory_list(args: dict[str, Any]) -> dict[str, Any]:
    category = (str(args.get("category") or "").strip()) or None
    try:
        limit = int(args.get("limit") or 50)
    except (TypeError, ValueError):
        limit = 50
    try:
        result = await _STORE.list(category=category, limit=limit)
    except Exception as exc:
        logger.exception("memory_list failed")
        return _err(f"memory_list error: {exc}")
    if "error" in result:
        return _err(result["error"])
    return _ok(result)


@tool(
    "memory_forget",
    "Permanently delete one memory by its numeric id (from memory_list or "
    "memory_recall results). Use when the user corrects or retracts "
    "something previously stored, or explicitly asks to forget it. Returns "
    "the deleted entry for confirmation.",
    {
        "type": "object",
        "properties": {
            "memory_id": {
                "type": "integer",
                "description": "The id of the memory to delete.",
            },
        },
        "required": ["memory_id"],
    },
)
async def memory_forget(args: dict[str, Any]) -> dict[str, Any]:
    try:
        memory_id = int(args.get("memory_id"))
    except (TypeError, ValueError):
        return _err("Error: 'memory_id' must be an integer.")
    try:
        result = await _STORE.forget(memory_id)
    except Exception as exc:
        logger.exception("memory_forget failed for id %r", memory_id)
        return _err(f"memory_forget error: {exc}")
    if "error" in result:
        return _err(result["error"])
    return _ok(result)


def build_memory_mcp_server():
    """In-process SDK MCP server exposing the four memory tools."""
    return create_sdk_mcp_server(
        name="memory",
        version="0.1.0",
        tools=[memory_store, memory_recall, memory_list, memory_forget],
    )


# Fully-qualified tool names for allowed-tools lists.
TOOL_MEMORY_STORE = "mcp__memory__memory_store"
TOOL_MEMORY_RECALL = "mcp__memory__memory_recall"
TOOL_MEMORY_LIST = "mcp__memory__memory_list"
TOOL_MEMORY_FORGET = "mcp__memory__memory_forget"

MEMORY_TOOL_NAMES = [
    TOOL_MEMORY_STORE,
    TOOL_MEMORY_RECALL,
    TOOL_MEMORY_LIST,
    TOOL_MEMORY_FORGET,
]
