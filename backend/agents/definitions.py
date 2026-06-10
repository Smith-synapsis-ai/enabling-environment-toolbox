"""Subagent definitions for the EE Toolbox agent team (Task A2).

Four Sonnet specialists registered as Claude Agent SDK subagents on the
orchestrator session. The orchestrator (Opus) routes work to them via the
Task tool, guided by each AgentDefinition's description.

Read-only posture: every subagent gets ONLY the read-only "ee" MCP tools it
needs -- no Write/Edit/Bash. Full safety hooks land with Task A8.

System prompts are loaded from backend/agents/prompts/<name>.md (authored
by the parallel A3 workstream) with inline FALLBACK_PROMPT placeholders
until those files exist. See prompt_loader.py.
"""

from claude_agent_sdk import AgentDefinition

from agents.model_config import SUBAGENT_MODEL
from agents.prompt_loader import load_prompt
from agents.evidence_tools import TOOL_EVIDENCE_DRILLDOWN
from agents.retrieval_tools import TOOL_CORPUS_SEARCH, TOOL_GET_PROFILE
from agents.stub_tools import TOOL_ASK_USER


def build_subagents() -> dict[str, AgentDefinition]:
    """Build the 4 subagent definitions (prompts resolved at call time).

    Built lazily (not at import) so freshly-added A3 prompt files are
    picked up without a process restart in dev workflows.
    """
    return {
        "triage": AgentDefinition(
            description=(
                "Triage Specialist. ALWAYS invoke FIRST for every new scaling "
                "challenge: restates the challenge, identifies innovation, "
                "actors, geography and binding constraints, maps it to the "
                "eight EE pillars, and produces search keywords. May ask the "
                "user one clarifying question."
            ),
            prompt=load_prompt("triage"),
            tools=[TOOL_ASK_USER],
            model=SUBAGENT_MODEL,
        ),
        "corpus_search": AgentDefinition(
            description=(
                "Corpus Search Specialist. Retrieves relevant tools from the "
                "100-tool EE Toolbox catalog via hybrid semantic + keyword "
                "retrieval with relevance scores, given a triaged challenge "
                "or keywords. Use AFTER triage; returns a deduplicated "
                "candidate list of tools with relevance rationale."
            ),
            prompt=load_prompt("corpus_search"),
            tools=[TOOL_CORPUS_SEARCH, TOOL_GET_PROFILE],
            model=SUBAGENT_MODEL,
        ),
        "multi_tool_reasoning": AgentDefinition(
            description=(
                "Multi-Tool Reasoning Specialist. For multi-faceted "
                "challenges: compares candidate EE tools, finds "
                "complementarities/overlaps, and combines 2-4 tools into a "
                "sequenced intervention package. Use after corpus_search when "
                "the challenge spans multiple pillars or constraints."
            ),
            prompt=load_prompt("multi_tool_reasoning"),
            tools=[TOOL_CORPUS_SEARCH, TOOL_GET_PROFILE],
            model=SUBAGENT_MODEL,
        ),
        "evidence_drill_down": AgentDefinition(
            description=(
                "Evidence Drill-Down Specialist. Fetches deeper evidence for "
                "specific catalog tools: full wiki profile via "
                "get_tool_profile, plus full-text search over the source-"
                "document evidence corpus (47k+ passages) via "
                "evidence_drilldown. Every claim it returns carries an "
                "[RC <result-code>] citation marker resolvable to a handle "
                "URL."
            ),
            prompt=load_prompt("evidence_drill_down"),
            tools=[TOOL_EVIDENCE_DRILLDOWN, TOOL_GET_PROFILE],
            model=SUBAGENT_MODEL,
        ),
    }
