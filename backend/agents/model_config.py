"""Model tier configuration for the EE Toolbox agent team.

Pinned full model IDs (never aliases like "opus"/"sonnet") so behaviour
does not silently change when Anthropic re-points aliases.

IDs verified against the reference production system
(synapsis-agent-macos-v23, claude-agent-sdk 0.1.72, 2026-06):
  - current Opus  : claude-opus-4-8
  - current Sonnet: claude-sonnet-4-6

Override via environment for experiments:
  EE_ORCHESTRATOR_MODEL / EE_SUBAGENT_MODEL
"""

import os

ORCHESTRATOR_MODEL: str = os.getenv("EE_ORCHESTRATOR_MODEL", "claude-opus-4-8")
SUBAGENT_MODEL: str = os.getenv("EE_SUBAGENT_MODEL", "claude-sonnet-4-6")
