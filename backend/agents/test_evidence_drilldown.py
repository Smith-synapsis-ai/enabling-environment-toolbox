"""Zero-API-cost tests for the REAL evidence_drilldown tool (Task B1 Wave 2).

Calls the registered SDK tool's handler DIRECTLY (same pattern as
test_report_update_coercion.py) -- no Claude API, no orchestrator session.

Database: the Wave-1 SMOKE evidence store. Path resolution:
  env EE_EVIDENCE_DB_TEST  ->  backend/data/evidence_smoke.db
NEVER points at evidence_corpus.db (the full DB may still be building).

Run as pytest:        cd backend && python3 -m pytest agents/test_evidence_drilldown.py -v -s
Run as plain script:  cd backend && python3 agents/test_evidence_drilldown.py

Smoke-DB facts these tests rely on (verified at Wave 1 handoff):
  - results: 1,112 codes; passages: 20,962; FTS in sync
  - 10568-100094: handle https://hdl.handle.net/10568/100094, title/year NULL,
    evidence slot 1 with 91 passages (seq 1..91), first passage
    '10568-100094:e1:p1' = 971 tokens, text about climate change impacts on
    human health and nutrition
  - 10568-100095 exists (10 passages)
  - title/year are NULL for ALL rows (canonical workbook carries none)
"""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents import evidence_tools  # noqa: E402
from agents.context_budget import (  # noqa: E402
    DEFAULT_TOKEN_BUDGET,
    ENV_BUDGET,
    budget_passages,
    resolve_budget,
    truncation_notice,
)

# The @tool decorator wraps the coroutine; the raw handler is exposed as
# `.handler` -- calling it directly costs zero API tokens.
_drilldown = evidence_tools.evidence_drilldown.handler

_SMOKE_DB = Path(
    os.environ.get("EE_EVIDENCE_DB_TEST")
    or Path(__file__).resolve().parents[1] / "data" / "evidence_smoke.db"
)

KNOWN_CODE = "10568-100094"
KNOWN_URL = "https://hdl.handle.net/10568/100094"
SECOND_CODE = "10568-100095"


def _call(args: dict) -> dict:
    """Run the async tool handler against the smoke DB and return its result."""
    evidence_tools.set_evidence_db(_SMOKE_DB)
    return asyncio.run(_drilldown(args))


def _text(result: dict) -> str:
    return result["content"][0]["text"]


def _tail(text: str) -> dict:
    """Parse the machine-readable JSON tail (ALWAYS the last line)."""
    return json.loads(text.splitlines()[-1])


def _references_section(text: str) -> str:
    """The References block (between 'References' and the JSON tail)."""
    body = text.split("\nReferences\n", 1)
    assert len(body) == 2, "output must contain a References section"
    return body[1].rsplit("\n\n", 1)[0]


# ---------------------------------------------------------------------------
# (a) happy path: markers, References, citations JSON
# ---------------------------------------------------------------------------

def test_happy_path_markers_references_citations():
    result = _call({
        "tool_id": KNOWN_CODE,
        "question": "impacts of climate change on health and nutrition",
    })
    assert not result.get("is_error"), _text(result)
    text = _text(result)

    # [RC ...] passage markers present, scoped to the requested code.
    assert f"[RC {KNOWN_CODE} · ev" in text

    # References section: NULL-safe line, exactly 'RC <code> — <url>',
    # and no 'None' artifacts anywhere in it.
    refs = _references_section(text)
    assert f"RC {KNOWN_CODE} — {KNOWN_URL}" in refs
    assert "None" not in refs

    # Machine-readable JSON tail on the last line.
    tail = _tail(text)
    assert "citations" in tail and "budget" in tail
    assert tail["citations"], "expected at least one citation"
    for cit in tail["citations"]:
        assert cit["result_code"] == KNOWN_CODE
        assert cit["handle_url"] == KNOWN_URL
        assert cit["passage_id"].startswith(f"{KNOWN_CODE}:e")
        assert isinstance(cit["evidence_slot"], int)
        assert isinstance(cit["seq"], int)

    budget = tail["budget"]
    assert budget["included"] == len(tail["citations"])
    assert budget["matched"] >= budget["included"] > 0
    assert budget["token_budget"] == DEFAULT_TOKEN_BUDGET
    assert 0 < budget["tokens_used"] <= budget["token_budget"]
    print(
        f"(a) happy path: {budget['included']} of {budget['matched']} passages, "
        f"{budget['tokens_used']}/{budget['token_budget']} tokens, "
        f"truncated={budget['truncated']}"
    )


# ---------------------------------------------------------------------------
# (b) multi-code arrays + id normalization variants
# ---------------------------------------------------------------------------

def test_multi_code_real_array():
    result = _call({
        "tool_id": [KNOWN_CODE, SECOND_CODE],
        "question": "climate change adaptation evidence",
    })
    assert not result.get("is_error"), _text(result)
    text = _text(result)
    tail = _tail(text)
    cited = {c["result_code"] for c in tail["citations"]}
    assert cited <= {KNOWN_CODE, SECOND_CODE}
    assert tail["citations"], "expected citations for the multi-code call"
    refs = _references_section(text)
    assert "None" not in refs
    print(f"(b) real array: cited codes = {sorted(cited)}")


def test_multi_code_json_string_array():
    """SDK harness workaround: array serialized as a JSON-encoded STRING."""
    result = _call({
        "tool_id": json.dumps([KNOWN_CODE, SECOND_CODE]),
        "question": "climate change adaptation evidence",
    })
    assert not result.get("is_error"), _text(result)
    tail = _tail(_text(result))
    cited = {c["result_code"] for c in tail["citations"]}
    assert cited <= {KNOWN_CODE, SECOND_CODE}
    assert tail["citations"]
    print(f"(b) JSON-string array: cited codes = {sorted(cited)}")


def test_id_normalization_variants():
    """'10568/100094' and the full handle URL normalize to the same code."""
    for variant in ("10568/100094", f"https://hdl.handle.net/10568/100094"):
        result = _call({
            "tool_id": variant,
            "question": "climate change impacts on nutrition",
        })
        assert not result.get("is_error"), f"{variant!r}: {_text(result)}"
        tail = _tail(_text(result))
        assert {c["result_code"] for c in tail["citations"]} == {KNOWN_CODE}, variant
    print("(b) normalization: '10568/100094' and full handle URL both -> "
          f"{KNOWN_CODE}")


# ---------------------------------------------------------------------------
# (c) unknown code -> is_error naming the bad id
# ---------------------------------------------------------------------------

def test_unknown_code_is_error():
    bad = "10568-999999999"
    result = _call({"tool_id": bad, "question": "anything at all"})
    assert result.get("is_error") is True
    text = _text(result)
    assert bad in text, f"error text must name the bad id: {text}"
    print(f"(c) unknown code error text: {text}")


def test_unknown_code_mixed_with_known_is_error():
    bad = "10568-999999999"
    result = _call({
        "tool_id": [KNOWN_CODE, bad],
        "question": "anything at all",
    })
    assert result.get("is_error") is True
    assert bad in _text(result)
    print("(c) mixed known+unknown: errors and names the unknown id")


# ---------------------------------------------------------------------------
# (d) FTS miss -> leading-passages fallback with explicit note
# ---------------------------------------------------------------------------

def test_fts_miss_falls_back_to_leading_passages():
    result = _call({
        "tool_id": KNOWN_CODE,
        "question": "zzqx vbnmw plok",  # matches nothing in the corpus
    })
    assert not result.get("is_error"), _text(result)
    text = _text(result)
    assert "[fallback]" in text, "expected an explicit fallback note"
    assert f"RC {KNOWN_CODE}" in text.split("\n\n")[0]
    tail = _tail(text)
    assert tail["citations"], "fallback must still return leading passages"
    first = tail["citations"][0]
    assert (first["evidence_slot"], first["seq"]) == (1, 1), (
        "fallback must serve passages in document order (slot 1, seq 1 first)"
    )
    print(f"(d) FTS-miss fallback note: {text.split(chr(10) + chr(10))[0]}")


# ---------------------------------------------------------------------------
# (e) tight budget truncation (max_tokens=600)
# ---------------------------------------------------------------------------

def test_budget_truncation_max_tokens_600():
    result = _call({
        "tool_id": KNOWN_CODE,
        "question": "impacts of climate change on health and nutrition",
        "max_tokens": 600,
    })
    assert not result.get("is_error"), _text(result)
    text = _text(result)
    tail = _tail(text)
    budget = tail["budget"]

    assert budget["token_budget"] == 600
    assert budget["truncated"] is True
    assert budget["included"] < budget["matched"]
    assert "[budget] included" in text
    # usable = 0.95 * (600 - 500 header reserve) = 95 tokens
    assert budget["tokens_used"] <= 95
    # NOTE: smoke-DB passages for this code are all > 95 tokens, so included
    # may legitimately be 0; the tool then says so explicitly.
    if budget["included"] == 0:
        assert "(no passages fit within the token budget)" in text
    # References must still resolve the requested code, NULL-safe.
    refs = _references_section(text)
    assert f"RC {KNOWN_CODE} — {KNOWN_URL}" in refs
    assert "None" not in refs
    print(
        f"(e) max_tokens=600: included={budget['included']} of "
        f"{budget['matched']}, tokens_used={budget['tokens_used']}, "
        f"truncated={budget['truncated']}"
    )


# ---------------------------------------------------------------------------
# (f) budget_passages / resolve_budget unit tests (synthetic, no DB)
# ---------------------------------------------------------------------------

def test_budget_passages_truncates_prefix():
    passages = [{"passage_id": f"p{i}", "token_count": 100} for i in range(10)]
    included, stats = budget_passages(passages, 1000)
    # usable = 0.95 * (1000 - 500) = 475 -> 4 passages of 100 fit
    assert [p["passage_id"] for p in included] == ["p0", "p1", "p2", "p3"]
    assert stats == {
        "included": 4,
        "matched": 10,
        "tokens_used": 400,
        "token_budget": 1000,
        "truncated": True,
    }
    notice = truncation_notice(stats)
    assert notice == (
        "[budget] included 4 of 10 matching passages (400/1000 tokens) "
        "— refine the question to see more."
    )
    print(f"(f) budget_passages prefix: {notice}")


def test_budget_passages_all_fit():
    passages = [{"passage_id": f"p{i}", "token_count": 100} for i in range(10)]
    included, stats = budget_passages(passages, 50_000)
    assert len(included) == 10
    assert stats["truncated"] is False
    assert stats["tokens_used"] == 1000


def test_budget_passages_empty_and_reserve_edge():
    included, stats = budget_passages([], 1000)
    assert included == [] and stats["matched"] == 0
    assert stats["truncated"] is False

    # Budget at/below the header reserve -> nothing fits.
    passages = [{"passage_id": "p0", "token_count": 10}]
    included, stats = budget_passages(passages, 500)
    assert included == []
    assert stats == {
        "included": 0,
        "matched": 1,
        "tokens_used": 0,
        "token_budget": 500,
        "truncated": True,
    }
    print("(f) edge cases: empty list ok; budget<=reserve includes nothing")


def test_resolve_budget_precedence():
    saved = os.environ.get(ENV_BUDGET)
    try:
        os.environ[ENV_BUDGET] = "7000"
        assert resolve_budget(3000) == 3000      # tool arg wins
        assert resolve_budget(None) == 7000      # env next
        assert resolve_budget(0) == 7000         # non-positive arg ignored
        assert resolve_budget("bogus") == 7000   # non-int arg ignored
        os.environ[ENV_BUDGET] = "not-a-number"
        assert resolve_budget(None) == DEFAULT_TOKEN_BUDGET
        del os.environ[ENV_BUDGET]
        assert resolve_budget(None) == DEFAULT_TOKEN_BUDGET
    finally:
        if saved is None:
            os.environ.pop(ENV_BUDGET, None)
        else:
            os.environ[ENV_BUDGET] = saved
    print("(f) resolve_budget precedence: arg > env > default")


# ---------------------------------------------------------------------------
# plain-script mode
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not _SMOKE_DB.exists():
        sys.exit(f"smoke DB not found at {_SMOKE_DB} -- set EE_EVIDENCE_DB_TEST")
    test_happy_path_markers_references_citations()
    test_multi_code_real_array()
    test_multi_code_json_string_array()
    test_id_normalization_variants()
    test_unknown_code_is_error()
    test_unknown_code_mixed_with_known_is_error()
    test_fts_miss_falls_back_to_leading_passages()
    test_budget_truncation_max_tokens_600()
    test_budget_passages_truncates_prefix()
    test_budget_passages_all_fit()
    test_budget_passages_empty_and_reserve_edge()
    test_resolve_budget_precedence()
    print("\nAll evidence_drilldown tests passed (handler-direct, zero API cost).")
