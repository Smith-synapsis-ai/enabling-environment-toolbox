"""Keyword-match corpus search over the 92-tool EE Toolbox catalog.

NOTE: superseded by retrieval_tools.py (Step 0) -- no longer imported by the
live code path; kept for history/reference only.

# STUB: replaced by A4 hybrid retrieval.
This module is a deliberately simple placeholder so the agent scaffold can be
exercised end-to-end before the real retrieval stack (pgvector hybrid search,
Task A4/B1) is wired in. It parses ``data/seed.sql`` (the canonical 92-tool
catalog dump committed in this repo) at first use and ranks tools by naive
keyword term frequency. Read-only: it never touches a database.
"""

import logging
import re
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# Repo root = backend/agents/corpus_stub.py -> parents[2]
SEED_SQL_PATH: Path = Path(__file__).resolve().parents[2] / "data" / "seed.sql"

# Column order of the INSERT INTO public.tools statements in seed.sql.
_TOOL_COLUMNS = [
    "id", "title", "summary", "what_it_does", "when_to_use_it", "who_its_for",
    "pillars", "domains", "type", "stage", "target_users", "geography",
    "authors", "date_published", "source_url", "source_organization",
    "cover_image_url", "embedding", "average_rating", "rating_count",
    "view_count", "cgspace_id", "relevance_score", "is_visible",
    "created_at", "updated_at",
]

# Field -> weight for naive keyword scoring.
_SEARCH_FIELDS = {
    "title": 5.0,
    "summary": 1.0,
    "what_it_does": 1.5,
    "when_to_use_it": 1.0,
    "who_its_for": 1.0,
    "pillars": 3.0,
    "domains": 2.0,
    "geography": 2.0,
    "target_users": 1.0,
}

_STOPWORDS = frozenset(
    "a an and are as at be but by for from has have how in is it its of on or "
    "that the their this to we what when which who with can cant cannot dont "
    "should would could".split()
)


def _split_sql_tuple(s: str) -> list[str | None]:
    """Split the inside of a SQL VALUES (...) tuple into raw values.

    Handles single-quoted strings with '' escapes; treats everything else
    (NULL, numbers, arrays-as-strings) as plain tokens. Good enough for the
    pg_dump format of seed.sql -- # STUB: replaced by A4 hybrid retrieval.
    """
    values: list[str | None] = []
    buf: list[str] = []
    in_str = False
    was_str = False
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if in_str:
            if c == "'":
                if i + 1 < n and s[i + 1] == "'":
                    buf.append("'")
                    i += 2
                    continue
                in_str = False
            else:
                buf.append(c)
            i += 1
            continue
        if c == "'":
            in_str = True
            was_str = True
            i += 1
            continue
        if c == ",":
            token = "".join(buf).strip()
            values.append(None if (not was_str and token.upper() == "NULL") else token)
            buf, was_str = [], False
            i += 1
            continue
        buf.append(c)
        i += 1
    token = "".join(buf).strip()
    values.append(None if (not was_str and token.upper() == "NULL") else token)
    return values


def _parse_pg_array(raw: str | None) -> list[str]:
    """Parse a Postgres text-array literal like '{"Market Systems",Researcher}'."""
    if not raw:
        return []
    raw = raw.strip()
    if raw.startswith("{") and raw.endswith("}"):
        raw = raw[1:-1]
    items = re.findall(r'"((?:[^"\\]|\\.)*)"|([^,]+)', raw)
    return [(_a or _b).replace('\\"', '"').strip() for _a, _b in items if (_a or _b).strip()]


@lru_cache(maxsize=1)
def load_corpus() -> list[dict]:
    """Parse the tools table from seed.sql into a list of dicts (cached)."""
    if not SEED_SQL_PATH.is_file():
        logger.error("seed.sql not found at %s -- corpus stub is empty", SEED_SQL_PATH)
        return []
    tools: list[dict] = []
    prefix = "INSERT INTO public.tools "
    with SEED_SQL_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith(prefix):
                continue
            try:
                _, values_part = line.split(" VALUES (", 1)
                values_part = values_part.rstrip().rstrip(";").rstrip(")")
                raw_values = _split_sql_tuple(values_part)
                record = dict(zip(_TOOL_COLUMNS, raw_values))
                record.pop("embedding", None)  # large vector literal, irrelevant here
                for arr_col in ("pillars", "domains", "target_users", "geography"):
                    record[arr_col] = _parse_pg_array(record.get(arr_col))
                tools.append(record)
            except Exception:  # noqa: BLE001 -- skip malformed rows, keep going
                logger.exception("Failed to parse a tools row in seed.sql")
    logger.info("Corpus stub loaded %d tools from %s", len(tools), SEED_SQL_PATH)
    return tools


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9][a-z0-9-]+", text.lower()) if t not in _STOPWORDS]


def search_corpus(query: str, top_k: int = 8) -> list[dict]:
    """Naive keyword search over the 92-tool catalog.

    # STUB: replaced by A4 hybrid retrieval (pgvector + BM25).
    Scores each tool by weighted term frequency of query tokens across
    descriptive fields. Returns the top_k tools as compact dicts.
    """
    terms = _tokenize(query)
    if not terms:
        return []
    scored: list[tuple[float, dict]] = []
    for tool in load_corpus():
        score = 0.0
        for field, weight in _SEARCH_FIELDS.items():
            value = tool.get(field)
            if not value:
                continue
            haystack = " ".join(value).lower() if isinstance(value, list) else str(value).lower()
            for term in terms:
                score += weight * haystack.count(term)
        if score > 0:
            scored.append((score, tool))
    scored.sort(key=lambda pair: pair[0], reverse=True)

    results = []
    for score, tool in scored[:top_k]:
        summary = (tool.get("summary") or "")[:400]
        results.append({
            "id": tool.get("id"),
            "title": tool.get("title"),
            "summary": summary,
            "pillars": tool.get("pillars"),
            "domains": tool.get("domains"),
            "type": tool.get("type"),
            "stage": tool.get("stage"),
            "geography": tool.get("geography"),
            "source_url": tool.get("source_url"),
            "cgspace_id": tool.get("cgspace_id"),
            "score": round(score, 2),
        })
    return results
