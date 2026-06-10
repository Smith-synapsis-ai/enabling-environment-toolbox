"""Real evidence drill-down tool over the B1 evidence store (brief sections 4-6).

Replaces the Task-A2 ``evidence_drilldown`` stub (formerly in stub_tools.py)
with FTS5 keyword search over the ingested source-document evidence corpus
(pipeline/evidence/schema.py + ingest_evidence.py, Wave 1). Per the locked B1
decision the 47k-row corpus is NOT vector-indexed: retrieval is SQLite FTS5
(porter unicode61) restricted to the requested Result Code(s), ranked by bm25,
then trimmed to a token budget (context_budget.py, SNAP pattern).

Connection strategy: a NEW read-only connection per tool call
(``file:...?mode=ro`` URI). The SDK may run tool handlers on different
threads/event loops across calls, and sqlite3 connections are not safely
shareable across threads without locking; a read-only open against a WAL
database costs microseconds -- negligible next to the FTS query itself -- and
it means ``set_evidence_db()`` (used by tests and the W3 loader) takes effect
immediately with no stale-handle invalidation.

DB path resolution: ``set_evidence_db(path)`` override -> env
``EE_EVIDENCE_DB`` -> ``backend/data/evidence_corpus.db``.

Output contract (single text result):
  - optional ``[fallback]`` / ``[no-evidence]`` notes,
  - one block per included passage: ``[RC <code> · ev<slot> · p<seq>]`` header
    line then the passage text,
  - a ``[budget] included K of N ...`` line when truncated,
  - a ``References`` section, one line per distinct cited Result Code
    (NULL-safe: the canonical workbook carries no Title/Year metadata, so the
    usual form is ``RC <code> — <handle_url>``),
  - a machine-readable single-line JSON tail (ALWAYS the last line):
    ``{"citations": [{result_code, handle_url, evidence_slot, seq,
    passage_id}], "budget": {included, matched, tokens_used, token_budget,
    truncated}}``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from agents.context_budget import budget_passages, resolve_budget, truncation_notice

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "evidence_corpus.db"
ENV_DB = "EE_EVIDENCE_DB"

_db_override: Path | None = None


def set_evidence_db(path: str | Path) -> None:
    """Point the drill-down tool at an evidence DB (tests, W3 loader)."""
    global _db_override
    _db_override = Path(path)


def _db_path() -> Path:
    if _db_override is not None:
        return _db_override
    env = os.environ.get(ENV_DB, "").strip()
    if env:
        return Path(env)
    return _DEFAULT_DB


def _connect() -> sqlite3.Connection:
    """Open a fresh READ-ONLY connection to the evidence store."""
    path = _db_path()
    if not path.exists():
        raise FileNotFoundError(
            f"evidence store not found at {path} -- run the B1 ingest "
            "(pipeline/evidence/ingest_evidence.py) or set EE_EVIDENCE_DB."
        )
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Input normalization
# ---------------------------------------------------------------------------

# '10568-100094', '10568/100094', or a full handle URL ending in the pair.
_HANDLE_RE = re.compile(r"(\d+)[/-](\d+)/?\s*$")


def _normalize_code(raw: str) -> str | None:
    """Normalize one tool id to canonical '<prefix>-<num>' form, or None."""
    match = _HANDLE_RE.search(str(raw).strip())
    if not match:
        return None
    return f"{match.group(1)}-{match.group(2)}"


def _coerce_tool_ids(value: Any) -> tuple[list[str], str | None]:
    """Accept a string, an array of strings, or a JSON-encoded string array.

    Same harness workaround as stub_tools._coerce_array_params (A10): the SDK
    tool harness has been observed serializing array params as JSON-encoded
    STRINGS, so a string starting with '[' is json-decoded first.

    Returns (normalized_deduped_codes, error_message).
    """
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("["):
            try:
                decoded = json.loads(stripped)
            except json.JSONDecodeError as exc:
                return [], (
                    "'tool_id' was a string that looks like a JSON array but "
                    f"is not valid JSON ({exc.msg} at pos {exc.pos})."
                )
            if not isinstance(decoded, list):
                return [], (
                    f"'tool_id' decoded to {type(decoded).__name__}, expected "
                    "a string or an array of strings."
                )
            raw_items: list[Any] = decoded
        else:
            raw_items = [stripped]
    elif isinstance(value, list):
        raw_items = value
    elif value is None:
        return [], "'tool_id' is required (a result code or array of codes)."
    else:
        return [], (
            f"'tool_id' must be a string or an array of strings, got "
            f"{type(value).__name__}."
        )

    codes: list[str] = []
    bad: list[str] = []
    for item in raw_items:
        text = str(item).strip()
        if not text:
            continue
        code = _normalize_code(text)
        if code is None:
            bad.append(text)
        elif code not in codes:
            codes.append(code)
    if bad:
        return [], (
            "unrecognized tool id(s): " + ", ".join(repr(b) for b in bad)
            + ". Use CGSpace-handle ids as returned by corpus_search "
            "(e.g. '10568-100094')."
        )
    if not codes:
        return [], "'tool_id' is required (a result code or array of codes)."
    return codes, None


# ---------------------------------------------------------------------------
# FTS query sanitization
# ---------------------------------------------------------------------------

_TERM_RE = re.compile(r"[A-Za-z0-9']+")
_STOPWORDS = frozenset(
    "a an and are as at be by for from has have how in is it its of on or "
    "that the their this to was were what when where which who will with".split()
)
_MAX_TERMS = 40


def _fts_query(question: str) -> str | None:
    """Sanitize free text into a safe FTS5 query: quoted terms joined with OR.

    Quoting each term neutralizes all FTS operators (AND/OR/NOT/NEAR, ``*``,
    ``^``, column filters); the porter tokenizer handles stemming so we pass
    terms through verbatim.
    """
    terms: list[str] = []
    for raw in _TERM_RE.findall(question):
        term = raw.strip("'").lower()
        if not term or term in _STOPWORDS or term in terms:
            continue
        terms.append(term)
        if len(terms) >= _MAX_TERMS:
            break
    if not terms:
        return None
    return " OR ".join(f'"{t}"' for t in terms)


# ---------------------------------------------------------------------------
# Core drill-down (synchronous; run via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _reference_line(meta: sqlite3.Row) -> str:
    """One References line, NULL-safe (title/year are NULL in the canonical
    workbook -- never emit 'None (None)' artifacts)."""
    code = meta["result_code"]
    title = (meta["title"] or "").strip() or None
    year = (str(meta["year"]) if meta["year"] is not None else "").strip() or None
    url = meta["handle_url"]
    if title and year:
        return f"RC {code} — {title} ({year}) — {url}"
    if title:
        return f"RC {code} — {title} — {url}"
    if year:
        return f"RC {code} — {year} — {url}"
    return f"RC {code} — {url}"


def _fetch_leading_passages(
    conn: sqlite3.Connection, code: str
) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT passage_id, result_code, evidence_slot, seq, text, token_count "
        "FROM passages WHERE result_code = ? ORDER BY evidence_slot, seq",
        (code,),
    ).fetchall()
    return [dict(r) for r in rows]


def _run_drilldown(
    codes: list[str], question: str, budget_tokens: int
) -> dict[str, Any]:
    """Synchronous search + budget + formatting. Returns either
    {"error": str} or {"text": str} (the full tool output)."""
    conn = _connect()
    try:
        placeholders = ",".join("?" for _ in codes)
        meta_rows = conn.execute(
            "SELECT result_code, handle_url, title, year, evidence_status, "
            "n_passages, n_errors FROM results "
            f"WHERE result_code IN ({placeholders})",
            codes,
        ).fetchall()
        meta = {row["result_code"]: row for row in meta_rows}
        unknown = [c for c in codes if c not in meta]
        if unknown:
            return {
                "error": (
                    "unknown result code(s): " + ", ".join(unknown)
                    + ". Use CGSpace-handle ids as returned by corpus_search "
                    "(e.g. '10568-100094')."
                )
            }

        notes: list[str] = []
        fts_match = _fts_query(question)
        fts_failed = False
        candidates: list[dict[str, Any]] = []
        matched_codes: set[str] = set()

        if fts_match is not None:
            try:
                rows = conn.execute(
                    "SELECT p.passage_id, p.result_code, p.evidence_slot, "
                    "p.seq, p.text, p.token_count "
                    "FROM passages_fts JOIN passages p "
                    "ON p.rowid = passages_fts.rowid "
                    f"WHERE passages_fts MATCH ? "
                    f"AND p.result_code IN ({placeholders}) "
                    "ORDER BY bm25(passages_fts)",
                    [fts_match, *codes],
                ).fetchall()
                candidates = [dict(r) for r in rows]
                matched_codes = {c["result_code"] for c in candidates}
            except sqlite3.OperationalError as exc:
                logger.warning("evidence_drilldown FTS failed (%s); falling "
                               "back to leading passages", exc)
                fts_failed = True
                notes.append(
                    "[fallback] full-text search could not parse the "
                    "question — showing leading passages (document order) "
                    "instead."
                )
        else:
            notes.append(
                "[fallback] the question contained no searchable terms — "
                "showing leading passages (document order) instead."
            )

        # Per-code fallback for codes the FTS pass did not cover.
        for code in codes:
            if code in matched_codes:
                continue
            if int(meta[code]["n_passages"] or 0) == 0:
                notes.append(
                    f"[no-evidence] RC {code} has no evidence passages in the "
                    f"store (evidence status: "
                    f"{meta[code]['evidence_status'] or 'unknown'}; "
                    f"{int(meta[code]['n_errors'] or 0)} extraction "
                    "error(s) recorded at ingest)."
                )
                continue
            if fts_match is not None and not fts_failed:
                notes.append(
                    f"[fallback] no passages matched the question for RC "
                    f"{code} — showing its leading passages (document order) "
                    "instead."
                )
            candidates.extend(_fetch_leading_passages(conn, code))

        included, stats = budget_passages(candidates, budget_tokens)

        # --- format output ---------------------------------------------------
        parts: list[str] = []
        parts.extend(notes)
        for p in included:
            header = (
                f"[RC {p['result_code']} · ev{p['evidence_slot']} · p{p['seq']}]"
            )
            parts.append(f"{header}\n{p['text'].strip()}")
        if not included and stats["matched"] > 0:
            parts.append("(no passages fit within the token budget)")
        if stats["truncated"]:
            parts.append(truncation_notice(stats))

        cited_codes = []
        for p in included:
            if p["result_code"] not in cited_codes:
                cited_codes.append(p["result_code"])
        ref_lines = [_reference_line(meta[c]) for c in cited_codes]
        if not ref_lines:  # nothing included -> still reference requested codes
            ref_lines = [_reference_line(meta[c]) for c in codes]
        parts.append("References\n" + "\n".join(ref_lines))

        tail = {
            "citations": [
                {
                    "result_code": p["result_code"],
                    "handle_url": meta[p["result_code"]]["handle_url"],
                    "evidence_slot": p["evidence_slot"],
                    "seq": p["seq"],
                    "passage_id": p["passage_id"],
                }
                for p in included
            ],
            "budget": stats,
        }
        parts.append(json.dumps(tail, ensure_ascii=False))
        return {"text": "\n\n".join(parts)}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

_EVIDENCE_DRILLDOWN_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_id": {
            "type": ["string", "array"],
            "items": {"type": "string"},
            "description": (
                "Result Code(s) to drill into: one id or an array of ids. "
                "Accepts '10568-100094', '10568/100094', or a full handle "
                "URL. A JSON-encoded string of an array is also accepted."
            ),
        },
        "question": {
            "type": "string",
            "description": (
                "What you want evidence about (free text). Matched against "
                "the source-document passages of the given Result Code(s)."
            ),
        },
        "max_tokens": {
            "type": "integer",
            "description": (
                "Optional token budget for the returned snippets "
                "(default 12000)."
            ),
        },
    },
    "required": ["tool_id", "question"],
}


@tool(
    "evidence_drilldown",
    "Search the FULL source-document evidence corpus (47k+ passages from the "
    "underlying CGIAR result evidence files) for one or more EE Toolbox "
    "tools, by Result Code. Full-text search scoped to the given code(s), "
    "bm25-ranked, token-budgeted. Returns passage snippets each tagged "
    "[RC <code> · ev<slot> · p<seq>], a References section with handle URLs, "
    "and a machine-readable citations JSON tail. Use after corpus_search / "
    "get_tool_profile when you need primary-source evidence for claims.",
    _EVIDENCE_DRILLDOWN_SCHEMA,
)
async def evidence_drilldown(args: dict[str, Any]) -> dict[str, Any]:
    codes, err = _coerce_tool_ids(args.get("tool_id"))
    if err:
        return {
            "content": [{"type": "text", "text": f"evidence_drilldown error: {err}"}],
            "is_error": True,
        }
    question = str(args.get("question") or "").strip()
    if not question:
        return {
            "content": [{
                "type": "text",
                "text": "Error: 'question' must be a non-empty string.",
            }],
            "is_error": True,
        }
    budget_tokens = resolve_budget(args.get("max_tokens"))

    try:
        # Off the event loop: FTS over up to 47k rows is CPU/IO-bound.
        outcome = await asyncio.to_thread(
            _run_drilldown, codes, question, budget_tokens
        )
    except Exception as exc:
        logger.exception("evidence_drilldown failed for codes %r", codes)
        return {
            "content": [{
                "type": "text",
                "text": f"evidence_drilldown error: {exc}",
            }],
            "is_error": True,
        }
    if "error" in outcome:
        return {
            "content": [{
                "type": "text",
                "text": f"evidence_drilldown error: {outcome['error']}",
            }],
            "is_error": True,
        }
    return {"content": [{"type": "text", "text": outcome["text"]}]}


# Fully-qualified tool name for AgentDefinition tool lists.
TOOL_EVIDENCE_DRILLDOWN = "mcp__ee__evidence_drilldown"
