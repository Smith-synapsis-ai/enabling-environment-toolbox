"""EE Toolbox agent orchestration scaffold (Task A2).

Claude Agent SDK setup: Opus orchestrator + 4 Sonnet subagents
(Triage, Corpus Search, Multi-Tool Reasoning, Evidence Drill-Down).

Public entry point:

    from agents import run_challenge          # backend/ on sys.path
    async for event in run_challenge(text, session_id):
        ...

Transport-agnostic: the WebSocket layer (Task A6) consumes the same
event iterator.
"""

__all__ = ["run_challenge"]


def __getattr__(name):  # lazy import: keeps `import agents` SDK-free
    if name == "run_challenge":
        from agents.orchestrator import run_challenge
        return run_challenge
    raise AttributeError(name)
