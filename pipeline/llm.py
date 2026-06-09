"""LLM caller wrapper using the Anthropic Python SDK.

Replaces the previous Claude CLI subprocess approach with direct API calls,
enabling deployment to AWS (where the CLI and macOS Keychain are unavailable).
The local dev workflow is unchanged — just set ANTHROPIC_API_KEY in .env.
"""

import os
import time
from typing import Optional

import anthropic

from pipeline.config import DEFAULT_MODEL, ANTHROPIC_API_KEY, LLM_TIMEOUT_SECONDS


class LLMResult:
    """Structured result from an LLM call."""

    def __init__(self, text: str, latency_ms: int, model: str, error: Optional[str] = None):
        self.text = text
        self.latency_ms = latency_ms
        self.model = model
        self.error = error

    @property
    def success(self) -> bool:
        return self.error is None

    def __repr__(self) -> str:
        status = "OK" if self.success else f"ERROR: {self.error}"
        return f"LLMResult({status}, {self.latency_ms}ms)"


# ---------------------------------------------------------------------------
# Client (lazy-initialised to avoid import-time failures)
# ---------------------------------------------------------------------------

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. "
                "Set it in your .env file or as an environment variable."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def call_llm(
    prompt: str,
    model: str = DEFAULT_MODEL,
    timeout: int = LLM_TIMEOUT_SECONDS,
    max_tokens: int = 4096,
) -> LLMResult:
    """Call the Anthropic Messages API with a single-turn prompt.

    Args:
        prompt: The full prompt text to send (single user message).
        model: The Anthropic model identifier.
        timeout: HTTP timeout in seconds.
        max_tokens: Maximum tokens in the response.

    Returns:
        LLMResult with the text response, latency, and any error info.
    """
    start = time.time()

    try:
        client = _get_client()
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            timeout=timeout,
        )

        elapsed_ms = int((time.time() - start) * 1000)
        text = response.content[0].text if response.content else ""

        return LLMResult(text=text, latency_ms=elapsed_ms, model=model)

    except anthropic.APITimeoutError:
        elapsed_ms = int((time.time() - start) * 1000)
        return LLMResult(
            text="",
            latency_ms=elapsed_ms,
            model=model,
            error=f"Timeout after {timeout}s",
        )
    except anthropic.APIError as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return LLMResult(
            text="",
            latency_ms=elapsed_ms,
            model=model,
            error=f"API error: {str(e)[:500]}",
        )
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return LLMResult(
            text="",
            latency_ms=elapsed_ms,
            model=model,
            error=f"Exception: {str(e)[:500]}",
        )
