"""Conversational chat service using the Anthropic Python SDK.

Manages in-memory conversation history and orchestrates the multi-turn
chat flow:

1. User describes their problem.
2. The assistant asks 2-3 clarifying questions.
3. When the assistant has enough context it outputs a search trigger
   (a JSON block with a search query).
4. The search results are incorporated, and the assistant produces a
   final answer with tailored tool recommendations.

Uses the Anthropic Messages API via the ``anthropic`` Python SDK.
Requires ANTHROPIC_API_KEY as an environment variable.

Conversations are persisted to the conversation_turns table in the
database for durability, with an in-memory dict kept as a cache.
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
import uuid as _uuid
from pathlib import Path
from typing import Optional

import anthropic
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.chat import ChatResponse, ToolRecommendation

logger = logging.getLogger(__name__)

# Ensure the pipeline package is importable
_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL = settings.DEFAULT_MODEL or "claude-sonnet-4-20250514"
LLM_TIMEOUT = settings.LLM_TIMEOUT_SECONDS or 120
MAX_TOKENS = settings.LLM_MAX_TOKENS or 4096

# ---------------------------------------------------------------------------
# Anthropic async client (lazy-initialised)
# ---------------------------------------------------------------------------

_async_client: Optional[anthropic.AsyncAnthropic] = None


def _get_async_client() -> anthropic.AsyncAnthropic:
    """Return a singleton AsyncAnthropic client."""
    global _async_client
    if _async_client is None:
        api_key = settings.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. "
                "Set it in your .env file or as an environment variable."
            )
        _async_client = anthropic.AsyncAnthropic(api_key=api_key)
    return _async_client


# ---------------------------------------------------------------------------
# In-memory conversation store (cache)
# ---------------------------------------------------------------------------

# conversation_id -> list of message dicts ({"role": ..., "content": ...})
conversations: dict[str, list[dict]] = {}

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

FALLBACK_SYSTEM_PROMPT = """You are the Enabling Environments Toolbox advisor, an expert assistant
that helps CGIAR researchers, development practitioners, and policymakers
find the right tools, frameworks, and methodologies for their work in
agricultural development, climate resilience, gender inclusion, and
related areas.

Your conversation flow:
1. When a user first describes their need, ask 2-3 focused clarifying
   questions to understand:
   - Their specific context (what project, what sector)
   - Geographic focus (which countries or regions)
   - Stage of work (design, implementation, monitoring, evaluation)
   - Target audience / stakeholders involved
2. Once you have enough context, output EXACTLY this search trigger on
   its own line:
   <!--SEARCH:{"query": "your refined search query here"}-->
   The query should synthesize the conversation into a search-optimized
   natural-language query.
3. You will then receive search results and should present the most
   relevant tools with personalized explanations of WHY each tool fits
   the user's situation. Reference specific aspects of their context.

Guidelines:
- Be concise but helpful. Do not overwhelm with too much text.
- If the user's request is very specific from the start, you may search
  after just 1 clarifying question.
- Always explain your recommendations in terms of the user's specific
  needs, not generic descriptions.
- If no tools match well, say so honestly and suggest alternatives.
- IMPORTANT: Only output the <!--SEARCH:...--> trigger when you are
  ready to search. Do not include it in your clarifying questions."""


# Regex to find the search trigger in a response
_SEARCH_TRIGGER_RE = re.compile(
    r'<!--SEARCH:\s*(\{.*?\})\s*-->',
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# DB persistence helpers
# ---------------------------------------------------------------------------


async def _persist_turn(
    conversation_id: str,
    session_id: Optional[str],
    turn_number: int,
    role: str,
    content: str,
    search_query: Optional[str] = None,
    recommended_tool_ids: Optional[list[str]] = None,
) -> None:
    """Insert a conversation turn into the database. Swallows errors."""
    try:
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            tool_ids_param = (
                [str(tid) for tid in recommended_tool_ids]
                if recommended_tool_ids
                else None
            )
            await db.execute(
                text(
                    """
                    INSERT INTO conversation_turns
                        (conversation_id, session_id, turn_number, role,
                         content, search_query, recommended_tool_ids)
                    VALUES
                        (:conversation_id, :session_id, :turn_number, :role,
                         :content, :search_query, CAST(:recommended_tool_ids AS uuid[]))
                    """
                ),
                {
                    "conversation_id": conversation_id,
                    "session_id": session_id,
                    "turn_number": turn_number,
                    "role": role,
                    "content": content,
                    "search_query": search_query,
                    "recommended_tool_ids": tool_ids_param,
                },
            )
            await db.commit()
    except Exception:
        logger.exception("Failed to persist conversation turn")


async def _load_conversation_from_db(conversation_id: str) -> list[dict]:
    """Load conversation history from the database. Returns empty list on failure."""
    try:
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text(
                    """
                    SELECT role, content
                    FROM conversation_turns
                    WHERE conversation_id = :conversation_id
                    ORDER BY turn_number ASC
                    """
                ),
                {"conversation_id": conversation_id},
            )
            rows = result.mappings().all()
            if rows:
                return [{"role": r["role"], "content": r["content"]} for r in rows]
    except Exception:
        logger.exception("Failed to load conversation from DB")
    return []


def _count_turns(messages: list[dict]) -> int:
    """Return the current turn count (number of messages)."""
    return len(messages)


# ---------------------------------------------------------------------------
# Conversation helpers
# ---------------------------------------------------------------------------


async def get_or_create_conversation(
    conversation_id: Optional[str],
    session_id: Optional[str] = None,
) -> tuple[str, list[dict]]:
    """Return (conversation_id, messages) for an existing or new conversation.

    Checks the in-memory cache first, then falls back to the database.
    """
    if conversation_id and conversation_id in conversations:
        return conversation_id, conversations[conversation_id]

    if conversation_id:
        # Try to load from database
        db_messages = await _load_conversation_from_db(conversation_id)
        if db_messages:
            conversations[conversation_id] = db_messages
            return conversation_id, db_messages

    new_id = str(_uuid.uuid4())
    conversations[new_id] = []
    return new_id, conversations[new_id]


# ---------------------------------------------------------------------------
# System prompt retrieval
# ---------------------------------------------------------------------------


async def get_system_prompt(db: AsyncSession) -> tuple[str, str]:
    """Fetch the active ``chat_system`` prompt from the DB.

    Returns (prompt_text, model_name).  Falls back to hardcoded defaults.
    """
    try:
        result = await db.execute(
            text(
                """
                SELECT prompt_text, model
                FROM prompt_versions
                WHERE prompt_name = 'chat_system' AND is_active = true
                LIMIT 1
                """
            )
        )
        row = result.fetchone()
        if row:
            return row[0], row[1] or DEFAULT_MODEL
    except Exception:
        logger.exception("Failed to fetch chat_system prompt from DB")

    return FALLBACK_SYSTEM_PROMPT, DEFAULT_MODEL


# ---------------------------------------------------------------------------
# Anthropic Messages API wrapper (async)
# ---------------------------------------------------------------------------


async def _call_anthropic(
    system_prompt: str,
    messages: list[dict],
    model: str = DEFAULT_MODEL,
) -> str:
    """Call the Anthropic Messages API and return the text response.

    Uses the native Messages API format -- no XML prompt packing needed.
    The system prompt is passed via the ``system`` parameter, and the
    conversation history is passed as structured ``messages``.
    """
    start = time.time()

    try:
        client = _get_async_client()

        # Filter messages to only include valid roles for the API
        api_messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
            if msg["role"] in ("user", "assistant")
        ]

        response = await client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=api_messages,
            timeout=LLM_TIMEOUT,
        )

        elapsed = int((time.time() - start) * 1000)
        text_content = response.content[0].text if response.content else ""

        logger.info("Anthropic API call completed in %dms (model=%s)", elapsed, model)
        return text_content

    except anthropic.APITimeoutError:
        logger.error("Anthropic API timeout after %ds", LLM_TIMEOUT)
        return ""
    except anthropic.APIError as e:
        logger.error("Anthropic API error: %s", str(e)[:300])
        return ""
    except Exception as exc:
        logger.exception("Anthropic API exception: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# Semantic search
# ---------------------------------------------------------------------------


async def _run_semantic_search(query: str, top_n: int = 8) -> list[dict]:
    """Execute a pgvector semantic search and return results as dicts."""
    from pipeline.embeddings import generate_embedding

    query_vector = await asyncio.to_thread(generate_embedding, query)
    vector_literal = "[" + ",".join(str(v) for v in query_vector) + "]"

    async with (await _get_async_session()) as db:
        result = await db.execute(
            text(
                """
                SELECT id, title, summary, what_it_does, when_to_use_it,
                       who_its_for, pillars, domains, type, stage,
                       target_users, geography, source_url, cover_image_url,
                       average_rating, rating_count,
                       1 - (embedding <=> CAST(:vec AS vector)) AS similarity
                FROM tools
                WHERE embedding IS NOT NULL AND is_visible = true
                ORDER BY embedding <=> CAST(:vec AS vector)
                LIMIT :limit
                """
            ),
            {"vec": vector_literal, "limit": top_n},
        )
        rows = result.mappings().all()

    tools = []
    for row in rows:
        sim = float(row["similarity"]) if row["similarity"] is not None else 0.0
        if sim < 0.25:
            continue
        tools.append(
            {
                "id": str(row["id"]),
                "title": row["title"],
                "summary": row["summary"] or "",
                "what_it_does": row["what_it_does"] or "",
                "when_to_use_it": row["when_to_use_it"] or "",
                "who_its_for": row["who_its_for"] or "",
                "pillars": row["pillars"] or [],
                "domains": row["domains"] or [],
                "type": row["type"] or "",
                "stage": row["stage"] or "",
                "target_users": row["target_users"] or [],
                "geography": row["geography"] or [],
                "source_url": row["source_url"] or "",
                "cover_image_url": row["cover_image_url"] or "",
                "average_rating": float(row["average_rating"] or 0),
                "rating_count": int(row["rating_count"] or 0),
                "similarity": round(sim, 4),
            }
        )
    return tools


async def _get_async_session():
    """Return a new AsyncSession from the session factory."""
    from app.database import AsyncSessionLocal
    return AsyncSessionLocal()


# ---------------------------------------------------------------------------
# Search result formatting
# ---------------------------------------------------------------------------


def _format_search_results_for_llm(results: list[dict]) -> str:
    """Format search results into a text block the LLM can use."""
    if not results:
        return "No tools were found matching the search criteria."

    lines = [f"Found {len(results)} relevant tool(s):\n"]
    for i, tool in enumerate(results, 1):
        lines.append(f"--- Tool {i} ---")
        lines.append(f"ID: {tool['id']}")
        lines.append(f"Title: {tool['title']}")
        lines.append(f"Type: {tool['type']} | Stage: {tool['stage']}")
        lines.append(f"Summary: {tool['summary']}")
        lines.append(f"What it does: {tool['what_it_does']}")
        lines.append(f"When to use it: {tool['when_to_use_it']}")
        lines.append(f"Who it's for: {tool['who_its_for']}")
        lines.append(f"Pillars: {', '.join(tool['pillars'])}")
        lines.append(f"Domains: {', '.join(tool['domains'])}")
        lines.append(f"Target users: {', '.join(tool['target_users'])}")
        lines.append(f"Geography: {', '.join(tool['geography'])}")
        lines.append(f"Similarity: {tool['similarity']}")
        if tool["source_url"]:
            lines.append(f"URL: {tool['source_url']}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main response generation
# ---------------------------------------------------------------------------


async def generate_response(
    conversation_id: Optional[str],
    user_message: str,
    db: AsyncSession,
    session_id: Optional[str] = None,
) -> ChatResponse:
    """Generate a chat response, potentially with tool recommendations.

    Flow:
    1. Add user message to conversation history.
    2. Call Anthropic Messages API with system prompt + full history.
    3. If the response contains <!--SEARCH:...-->, execute the search,
       add results to conversation, and call again for the final
       response with tool recommendations.
    """
    conv_id, messages = await get_or_create_conversation(conversation_id, session_id)

    # Add the user's message
    messages.append({"role": "user", "content": user_message})

    # Persist user turn to DB (fire and forget)
    user_turn_number = _count_turns(messages)
    asyncio.create_task(
        _persist_turn(
            conversation_id=conv_id,
            session_id=session_id,
            turn_number=user_turn_number,
            role="user",
            content=user_message,
        )
    )

    # Fetch system prompt and model from DB
    system_prompt, model_name = await get_system_prompt(db)

    # Call the Anthropic API with the full conversation
    response_text = await _call_anthropic(system_prompt, messages, model_name)

    if not response_text:
        return ChatResponse(
            conversation_id=conv_id,
            message="I apologize, but I'm having trouble processing your request right now. Please try again in a moment.",
            tools_recommended=None,
            conversation_complete=False,
        )

    # Check for search trigger
    tools_recommended: list[ToolRecommendation] | None = None
    search_match = _SEARCH_TRIGGER_RE.search(response_text)
    detected_search_query: Optional[str] = None

    if search_match:
        # Extract the search query
        try:
            search_data = json.loads(search_match.group(1))
            search_query = search_data.get("query", user_message)
        except json.JSONDecodeError:
            search_query = user_message

        detected_search_query = search_query

        # Remove the search trigger from the visible response text
        # (the part before the trigger may have introductory text)
        pre_search_text = response_text[:search_match.start()].strip()

        # Execute the semantic search
        try:
            search_results = await _run_semantic_search(
                query=search_query, top_n=8
            )
        except Exception:
            logger.exception("Search failed during chat")
            search_results = []

        # Record the assistant's pre-search message
        if pre_search_text:
            messages.append({"role": "assistant", "content": pre_search_text})

        # Add search results as context
        results_text = _format_search_results_for_llm(search_results)
        messages.append(
            {
                "role": "user",
                "content": (
                    f"[SYSTEM] Here are the search results for the query "
                    f'"{search_query}":\n\n{results_text}\n\n'
                    f"Now present the most relevant tools with personalized "
                    f"explanations tailored to the user's specific context. "
                    f"Do NOT include the <!--SEARCH:...--> trigger again."
                ),
            }
        )

        # Second API call with the search results
        response_text = await _call_anthropic(system_prompt, messages, model_name)

        if not response_text:
            response_text = "I found some tools but had trouble formatting the response. Please try again."

        # Build tool recommendations
        if search_results:
            tools_recommended = _build_recommendations(search_results)

    # Record the assistant's final message
    # Strip any accidental search triggers from the final response
    clean_response = _SEARCH_TRIGGER_RE.sub("", response_text).strip()
    messages.append({"role": "assistant", "content": clean_response})

    # Persist assistant turn to DB (fire and forget)
    assistant_turn_number = _count_turns(messages)
    recommended_ids = (
        [t.id for t in tools_recommended] if tools_recommended else None
    )
    asyncio.create_task(
        _persist_turn(
            conversation_id=conv_id,
            session_id=session_id,
            turn_number=assistant_turn_number,
            role="assistant",
            content=clean_response,
            search_query=detected_search_query,
            recommended_tool_ids=recommended_ids,
        )
    )

    return ChatResponse(
        conversation_id=conv_id,
        message=clean_response,
        tools_recommended=tools_recommended,
        conversation_complete=False,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_recommendations(search_results: list[dict]) -> list[ToolRecommendation]:
    """Convert raw search results into ToolRecommendation objects."""
    recs = []
    for tool in search_results[:5]:  # Top 5 recommendations
        recs.append(
            ToolRecommendation(
                id=tool["id"],
                title=tool["title"],
                explanation=(
                    tool["summary"][:200]
                    if tool["summary"]
                    else "Relevant tool for your needs."
                ),
                similarity=tool["similarity"],
            )
        )
    return recs
