"""Token-budget accounting for the evidence drill-down tool (B1 brief section 5).

SNAP pattern: passages arrive ranked (FTS bm25 order, or document order in the
fallback case) with PRECOMPUTED ``token_count`` values from ingest (Qwen3
tokenizer, see pipeline/evidence/ingest_evidence.py). We accumulate counts in
rank order and STOP -- not skip -- at 95% of the usable budget, so the model
always sees a clean prefix of the ranking rather than a gappy selection.

A fixed ``HEADER_RESERVE_TOKENS`` allowance is subtracted from the budget
BEFORE the 95% stop fraction is applied; it pays for the per-passage
``[RC ...]`` header lines, the References section and the citations JSON tail,
none of which are included in the per-passage counts.

Budget resolution order (``resolve_budget``):
  1. tool-call ``max_tokens`` argument,
  2. env ``EE_DRILLDOWN_TOKEN_BUDGET``,
  3. ``DEFAULT_TOKEN_BUDGET`` (12000).
"""

from __future__ import annotations

import os
from typing import Any

DEFAULT_TOKEN_BUDGET = 12000
ENV_BUDGET = "EE_DRILLDOWN_TOKEN_BUDGET"
HEADER_RESERVE_TOKENS = 500
BUDGET_STOP_FRACTION = 0.95


def resolve_budget(max_tokens: Any = None) -> int:
    """Resolve the token budget: tool arg -> env -> default (12000)."""
    if max_tokens is not None:
        try:
            value = int(max_tokens)
            if value > 0:
                return value
        except (TypeError, ValueError):
            pass
    env_raw = os.environ.get(ENV_BUDGET, "").strip()
    if env_raw:
        try:
            value = int(env_raw)
            if value > 0:
                return value
        except ValueError:
            pass
    return DEFAULT_TOKEN_BUDGET


def budget_passages(
    passages: list[dict[str, Any]], budget_tokens: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select a budget-bounded prefix of ranked ``passages``.

    Each passage dict must carry an integer ``token_count``. Returns
    ``(included, stats)`` where ``stats`` is the machine-readable budget block
    emitted in the tool's JSON tail::

        {"included": K, "matched": N, "tokens_used": T,
         "token_budget": B, "truncated": bool}

    Stop rule: usable = 0.95 * max(0, budget - HEADER_RESERVE_TOKENS); the
    first passage that would push the running total PAST usable ends the scan
    (no skipping ahead to smaller later passages).
    """
    matched = len(passages)
    usable = int(BUDGET_STOP_FRACTION * max(0, budget_tokens - HEADER_RESERVE_TOKENS))

    included: list[dict[str, Any]] = []
    used = 0
    for passage in passages:
        count = int(passage.get("token_count") or 0)
        if used + count > usable:
            break
        included.append(passage)
        used += count

    stats = {
        "included": len(included),
        "matched": matched,
        "tokens_used": used,
        "token_budget": budget_tokens,
        "truncated": len(included) < matched,
    }
    return included, stats


def truncation_notice(stats: dict[str, Any]) -> str:
    """The required end-of-snippets line when the budget truncated output."""
    return (
        f"[budget] included {stats['included']} of {stats['matched']} "
        f"matching passages ({stats['tokens_used']}/{stats['token_budget']} "
        "tokens) — refine the question to see more."
    )
