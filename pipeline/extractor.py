"""
Metadata extractor for the Enabling Environment Toolbox.

Reads the active metadata_extraction prompt from the database, calls the LLM
via the Anthropic SDK, parses the JSON response, and validates against the
taxonomy.
"""

import json
import logging
import os
import re
import time
from typing import Any

import anthropic
import psycopg2

from pipeline.config import DATABASE_URL_SYNC, DEFAULT_MODEL, ANTHROPIC_API_KEY, LLM_TIMEOUT_SECONDS
from pipeline.taxonomy import validate_extraction

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Anthropic client (lazy-init)
# ---------------------------------------------------------------------------

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def _get_prompt_template() -> tuple[str, str]:
    """
    Fetch the active metadata_extraction prompt from the database.

    Returns (prompt_version_id, prompt_text).
    """
    conn = psycopg2.connect(DATABASE_URL_SYNC)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, prompt_text FROM prompt_versions "
            "WHERE prompt_name = 'metadata_extraction' AND is_active = true "
            "ORDER BY version DESC LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("No active metadata_extraction prompt found in database")
        return str(row[0]), row[1]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# LLM caller
# ---------------------------------------------------------------------------


def _call_llm(prompt_text: str, model: str = DEFAULT_MODEL) -> tuple[str, float]:
    """
    Call the Anthropic Messages API with the given prompt.

    Returns (response_text, latency_seconds).
    """
    start = time.time()
    client = _get_client()

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt_text}],
        timeout=LLM_TIMEOUT_SECONDS,
    )
    latency = time.time() - start

    text = response.content[0].text if response.content else ""
    if not text:
        raise RuntimeError("Empty response from Anthropic API")

    return text, latency


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------


def _parse_json_response(response_text: str) -> dict:
    """
    Parse the LLM's response text as JSON.

    Handles cases where the response contains markdown code fences.
    """
    text = response_text.strip()

    # Try to extract JSON from markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # Try to find a JSON object in the text
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            try:
                return json.loads(text[brace_start : brace_end + 1])
            except json.JSONDecodeError:
                pass
        raise RuntimeError(f"Failed to parse JSON from LLM response: {e}\nResponse: {text[:500]}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_metadata(
    title: str,
    authors: str,
    date: str,
    abstract: str,
    full_text: str = "",
    model: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    """
    Extract structured metadata from a document using the LLM.

    Returns a dict with:
      - All extraction fields (pillars, domains, type, stage, etc.)
      - '_prompt_version_id': UUID of the prompt used
      - '_latency_ms': LLM call latency in milliseconds
      - '_model': model used
      - '_warnings': list of taxonomy validation warnings
    """
    # Get prompt template
    prompt_version_id, prompt_template = _get_prompt_template()

    # Substitute placeholders
    prompt_text = prompt_template.replace("{title}", title or "")
    prompt_text = prompt_text.replace("{authors}", authors or "")
    prompt_text = prompt_text.replace("{date}", date or "")
    prompt_text = prompt_text.replace("{abstract}", abstract or "")
    prompt_text = prompt_text.replace("{full_text}", full_text or "(not available)")

    # Call LLM
    response_text, latency_secs = _call_llm(prompt_text, model=model)
    latency_ms = int(latency_secs * 1000)

    # Parse JSON
    raw_data = _parse_json_response(response_text)

    # Validate against taxonomy
    validation_result = validate_extraction(raw_data)
    cleaned_data = validation_result["data"]
    warnings = validation_result["warnings"]

    # Add metadata about the extraction
    cleaned_data["_prompt_version_id"] = prompt_version_id
    cleaned_data["_latency_ms"] = latency_ms
    cleaned_data["_model"] = model
    cleaned_data["_warnings"] = warnings

    return cleaned_data
