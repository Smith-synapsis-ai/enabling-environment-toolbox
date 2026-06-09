"""Relevance classifier for the Enabling Environment Toolbox.

Reads the active prompt template from the database, substitutes document
metadata, calls the LLM, and parses the structured JSON response.
"""

import json
import re
from typing import Optional

import psycopg2

from pipeline.config import DATABASE_URL_SYNC, DEFAULT_MODEL
from pipeline.llm import LLMResult, call_llm


def get_active_prompt() -> tuple[str, str]:
    """Fetch the active relevance_classification prompt from the database.

    Returns:
        Tuple of (prompt_version_id, prompt_template_text).

    Raises:
        RuntimeError: If no active prompt is found.
    """
    conn = psycopg2.connect(DATABASE_URL_SYNC)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, prompt_text FROM prompt_versions "
            "WHERE prompt_name = 'relevance_classification' AND is_active = true "
            "ORDER BY version DESC LIMIT 1;"
        )
        row = cur.fetchone()
        cur.close()
        if row is None:
            raise RuntimeError("No active relevance_classification prompt found in the database.")
        return str(row[0]), row[1]
    finally:
        conn.close()


def _extract_json_from_text(text: str) -> Optional[dict]:
    """Extract a JSON object from LLM text that may contain markdown fences or extra text."""
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try to find JSON inside markdown code fences
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find any JSON object in the text
    brace_match = re.search(r"\{[^{}]*\"relevant\"[^{}]*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def classify_relevance(
    title: str,
    authors: str,
    date: str,
    abstract: str,
    doc_type: str,
    url: str,
    model: str = DEFAULT_MODEL,
) -> dict:
    """Classify whether a document is relevant to the Enabling Environment Toolbox.

    Args:
        title: Document title.
        authors: Authors as a comma-separated string.
        date: Publication date or year.
        abstract: Document abstract or description.
        doc_type: Document type (e.g., Framework, Method, Journal Article).
        url: Document URL.
        model: LLM model to use.

    Returns:
        Dict with keys:
            - relevant (bool): Whether the document is relevant.
            - confidence (float): Confidence score 0.0-1.0.
            - reasoning (str): Brief explanation.
            - latency_ms (int): LLM call latency in milliseconds.
            - model (str): Model used.
            - prompt_version_id (str): UUID of the prompt version used.
            - raw_response (str): Raw LLM response text.
            - error (str or None): Error message if something went wrong.
    """
    prompt_version_id, template = get_active_prompt()

    # Substitute placeholders manually (can't use str.format because the
    # template contains literal curly braces in the JSON example section)
    prompt = template
    prompt = prompt.replace("{title}", title)
    prompt = prompt.replace("{authors}", authors)
    prompt = prompt.replace("{date}", date)
    prompt = prompt.replace("{abstract}", abstract)
    prompt = prompt.replace("{doc_type}", doc_type)
    prompt = prompt.replace("{url}", url)

    # Call the LLM
    llm_result: LLMResult = call_llm(prompt, model=model)

    result = {
        "relevant": None,
        "confidence": 0.0,
        "reasoning": "",
        "latency_ms": llm_result.latency_ms,
        "model": llm_result.model,
        "prompt_version_id": prompt_version_id,
        "raw_response": llm_result.text,
        "error": llm_result.error,
    }

    if not llm_result.success:
        result["error"] = llm_result.error
        return result

    # Parse the JSON response
    parsed = _extract_json_from_text(llm_result.text)
    if parsed is None:
        result["error"] = f"Failed to parse JSON from LLM response: {llm_result.text[:300]}"
        return result

    # Extract fields
    relevant_raw = parsed.get("relevant")
    if isinstance(relevant_raw, bool):
        result["relevant"] = relevant_raw
    elif isinstance(relevant_raw, str):
        result["relevant"] = relevant_raw.lower() in ("true", "yes", "1")
    else:
        result["error"] = f"Unexpected 'relevant' value: {relevant_raw}"
        return result

    confidence_raw = parsed.get("confidence", 0.0)
    try:
        result["confidence"] = float(confidence_raw)
    except (ValueError, TypeError):
        result["confidence"] = 0.0

    result["reasoning"] = str(parsed.get("reasoning", ""))

    return result
