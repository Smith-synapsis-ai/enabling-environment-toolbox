"""Report-draft state for the iterative report flow (Task A5).

The core Track-0 deliverable: a per-session report draft that successive
user turns refine and extend instead of restarting. This module defines:

  - ``ReportDraft``        -- the versioned draft schema + JSON (de)serialization.
  - ``ReportStore``        -- the persistence protocol (Wave-3 shared interface
                              contract, /analysis/wave3-interfaces.md SS1 -- the
                              A7 SQLite store implements the SAME protocol and
                              is swapped in via ``set_report_store`` at merge).
  - ``JsonFileReportStore``-- default store: atomic JSON files under
                              ``backend/data/report_drafts/<session_id>.json``.

The draft JSON is opaque to stores; only this module defines its schema.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

SCHEMA_VERSION = 1

# backend/data/report_drafts/ -- agent-side runtime data root per the Wave-3
# storage-path contract (backend/agents/report_state.py -> parents[1] = backend/).
DEFAULT_DRAFTS_DIR: Path = Path(__file__).resolve().parents[1] / "data" / "report_drafts"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Draft schema
# ---------------------------------------------------------------------------

@dataclass
class ReportDraft:
    """One report-in-progress, keyed by (normalized UUID) session id.

    ``sections`` entries:        {"id", "heading", "body_md", "sources": [...]}
    ``candidate_tools`` entries: {"id", "title", "status": candidate|accepted|rejected}
    ``changelog`` entries:       {"revision", "turn", "summary"}
    """

    session_id: str
    schema_version: int = SCHEMA_VERSION
    title: str = ""
    challenge_summary: str = ""
    sections: list[dict[str, Any]] = field(default_factory=list)
    candidate_tools: list[dict[str, Any]] = field(default_factory=list)
    revision: int = 0
    turn_count: int = 0
    updated_at: str = field(default_factory=_utc_now_iso)
    changelog: list[dict[str, Any]] = field(default_factory=list)

    # -- (de)serialization --------------------------------------------------

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "ReportDraft":
        data = json.loads(raw)
        known = {f for f in cls.__dataclass_fields__}  # tolerate future fields
        return cls(**{k: v for k, v in data.items() if k in known})

    # -- mutation helpers (used by the report_update tool) -------------------

    def upsert_section(
        self,
        section_id: str,
        heading: str | None = None,
        body_md: str | None = None,
        sources: list[str] | None = None,
    ) -> str:
        """Insert or update a section by id; returns "added" or "updated"."""
        for sec in self.sections:
            if sec.get("id") == section_id:
                if heading is not None:
                    sec["heading"] = heading
                if body_md is not None:
                    sec["body_md"] = body_md
                if sources is not None:
                    sec["sources"] = list(sources)
                return "updated"
        self.sections.append({
            "id": section_id,
            "heading": heading or section_id,
            "body_md": body_md or "",
            "sources": list(sources or []),
        })
        return "added"

    def remove_section(self, section_id: str) -> bool:
        before = len(self.sections)
        self.sections = [s for s in self.sections if s.get("id") != section_id]
        return len(self.sections) < before

    def upsert_candidate_tool(
        self, tool_id: str, title: str | None = None, status: str | None = None
    ) -> str:
        for entry in self.candidate_tools:
            if entry.get("id") == tool_id:
                if title is not None:
                    entry["title"] = title
                if status is not None:
                    entry["status"] = status
                return "updated"
        self.candidate_tools.append({
            "id": tool_id,
            "title": title or tool_id,
            "status": status or "candidate",
        })
        return "added"

    def remove_candidate_tool(self, tool_id: str) -> bool:
        before = len(self.candidate_tools)
        self.candidate_tools = [t for t in self.candidate_tools if t.get("id") != tool_id]
        return len(self.candidate_tools) < before

    def bump(self, turn: int, changelog_summary: str) -> None:
        """Record one applied patch: new revision + changelog entry."""
        self.revision += 1
        self.turn_count = max(self.turn_count, turn)
        self.updated_at = _utc_now_iso()
        self.changelog.append({
            "revision": self.revision,
            "turn": turn,
            "summary": changelog_summary,
        })

    # -- rendering ------------------------------------------------------------

    def render_markdown(self) -> str:
        """Render the draft as clean user-facing markdown."""
        lines: list[str] = []
        lines.append(f"# {self.title or 'Report draft (untitled)'}")
        lines.append("")
        lines.append(f"*Draft revision {self.revision} -- updated {self.updated_at}*")
        if self.challenge_summary:
            lines.append("")
            lines.append(f"**Challenge:** {self.challenge_summary}")
        if self.candidate_tools:
            lines.append("")
            lines.append("## Tools under consideration")
            lines.append("")
            for t in self.candidate_tools:
                lines.append(f"- **{t.get('title', t.get('id'))}** ({t.get('id')}) -- {t.get('status', 'candidate')}")
        for sec in self.sections:
            lines.append("")
            lines.append(f"## {sec.get('heading', sec.get('id'))}")
            lines.append("")
            lines.append(sec.get("body_md", ""))
            sources = sec.get("sources") or []
            if sources:
                lines.append("")
                lines.append("Sources: " + "; ".join(str(s) for s in sources))
        return "\n".join(lines).strip() + "\n"


# ---------------------------------------------------------------------------
# ReportStore protocol -- VERBATIM per wave3-interfaces.md SS1 (binding).
# A7's SqliteReportStore satisfies the same protocol and replaces the default
# via set_report_store() at merge time. draft_json is opaque to stores.
# ---------------------------------------------------------------------------

class ReportStore(Protocol):
    async def save_draft(self, session_id: str, draft_json: str) -> None: ...
    async def load_draft(self, session_id: str) -> str | None: ...   # None if absent
    async def list_sessions(self) -> list[str]: ...


class JsonFileReportStore:
    """Default file-backed store: backend/data/report_drafts/<session_id>.json.

    Writes are atomic (tmp file in the same directory + os.replace) so a
    crashed process never leaves a torn draft on disk.
    """

    def __init__(self, drafts_dir: Path | str = DEFAULT_DRAFTS_DIR) -> None:
        self._dir = Path(drafts_dir)

    def _path(self, session_id: str) -> Path:
        return self._dir / f"{session_id}.json"

    async def save_draft(self, session_id: str, draft_json: str) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=self._dir, prefix=f".{session_id}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(draft_json)
            os.replace(tmp_name, self._path(session_id))
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    async def load_draft(self, session_id: str) -> str | None:
        path = self._path(session_id)
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None

    async def list_sessions(self) -> list[str]:
        if not self._dir.is_dir():
            return []
        return sorted(p.stem for p in self._dir.glob("*.json"))


# ---------------------------------------------------------------------------
# Module-level store accessor -- A7's SQLite store is swapped in post-merge
# via set_report_store() without touching the orchestrator/tool logic.
# ---------------------------------------------------------------------------

_report_store: ReportStore = JsonFileReportStore()


def get_report_store() -> ReportStore:
    return _report_store


def set_report_store(store: ReportStore) -> None:
    global _report_store
    _report_store = store
