"""Centralized agent registry — single source of truth for all MAD agent definitions.

Provides a registry of all agents with their roles, tools, default models, and descriptions.
Supports user overrides via the ``agent_overrides`` key in settings.json.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mad.config import (
    CODER_TOOLS,
    FINALIZER_TOOLS,
    PLANNER_TOOLS,
    REVIEWER_TOOLS,
    VERIFIER_TOOLS,
    load_settings,
)


@dataclass(frozen=True)
class AgentProfile:
    """Definition of a single agent in the MAD pipeline."""

    name: str
    role_prefix: str
    tools: str
    default_model_key: str  # "planner", "coder", or "reviewer"
    description: str
    phase: str  # pipeline phase: "plan", "code", "review", "finalize", "evolution"
    prompt_template: str = ""  # optional path to external prompt template override


# ---------------------------------------------------------------------------
# Built-in agent registry
# ---------------------------------------------------------------------------

_BUILTIN_AGENTS: dict[str, AgentProfile] = {
    "PLANNER-RULES": AgentProfile(
        name="PLANNER-RULES",
        role_prefix="PLANNER",
        tools=PLANNER_TOOLS,
        default_model_key="planner",
        description="Analyzes the project idea, selects a tech stack, and generates framework-specific coding rules.",
        phase="plan",
    ),
    "PLANNER-DOMAIN": AgentProfile(
        name="PLANNER-DOMAIN",
        role_prefix="PLANNER",
        tools=PLANNER_TOOLS,
        default_model_key="planner",
        description="Researches domain-specific regulations, standards, and compliance requirements (healthcare, finance, etc.).",
        phase="plan",
    ),
    "PLANNER-RESEARCH": AgentProfile(
        name="PLANNER-RESEARCH",
        role_prefix="PLANNER",
        tools=PLANNER_TOOLS,
        default_model_key="planner",
        description="Fetches official documentation for all major dependencies — version numbers, API patterns, and gotchas.",
        phase="plan",
    ),
    "PLANNER-SPOTCHECK": AgentProfile(
        name="PLANNER-SPOTCHECK",
        role_prefix="PLANNER",
        tools=PLANNER_TOOLS,
        default_model_key="planner",
        description="Verifies 3-5 key claims from the research via fresh web searches and appends corrections.",
        phase="plan",
    ),
    "PLANNER-TICKETS": AgentProfile(
        name="PLANNER-TICKETS",
        role_prefix="PLANNER",
        tools=PLANNER_TOOLS,
        default_model_key="planner",
        description="Generates detailed, ordered tickets with acceptance criteria from research and rules.",
        phase="plan",
    ),
    "CODER": AgentProfile(
        name="CODER",
        role_prefix="CODER",
        tools=CODER_TOOLS,
        default_model_key="coder",
        description="Implements tickets one at a time in per-ticket sprints with self-verification.",
        phase="code",
    ),
    "CODER-FIX": AgentProfile(
        name="CODER-FIX",
        role_prefix="CODER",
        tools=CODER_TOOLS,
        default_model_key="coder",
        description="Addresses issues from the reviewer's refinement list in fix mode.",
        phase="code",
    ),
    "VERIFIER": AgentProfile(
        name="VERIFIER",
        role_prefix="VERIFIER",
        tools=VERIFIER_TOOLS,
        default_model_key="coder",
        description="Lightweight build verifier — checks compilation, tests, and import errors after each sprint.",
        phase="code",
    ),
    "REVIEWER": AgentProfile(
        name="REVIEWER",
        role_prefix="REVIEWER",
        tools=REVIEWER_TOOLS,
        default_model_key="reviewer",
        description="Evaluates implementations with structured scoring across 9 criteria. Runs in fresh context with no session history.",
        phase="review",
    ),
    "FINALIZER": AgentProfile(
        name="FINALIZER",
        role_prefix="FINALIZER",
        tools=FINALIZER_TOOLS,
        default_model_key="reviewer",
        description="Writes comprehensive README.md to the project root based on actual project contents.",
        phase="finalize",
    ),
    "EVOLUTION": AgentProfile(
        name="EVOLUTION",
        role_prefix="EVOLUTION",
        tools=FINALIZER_TOOLS,
        default_model_key="reviewer",
        description="Captures cross-project learnings with metrics validation. Flags suspect learnings that correlate with declining scores.",
        phase="evolution",
    ),
}


def get_agent(name: str) -> AgentProfile | None:
    """Look up an agent by name (case-insensitive).

    Also checks for user overrides in settings.json under ``agent_overrides``.
    """
    key = name.upper()
    profile = _BUILTIN_AGENTS.get(key)
    if profile is None:
        return None

    # Apply user overrides from settings.json
    overrides = _load_overrides().get(key, {})
    if not overrides:
        return profile

    return AgentProfile(
        name=profile.name,
        role_prefix=profile.role_prefix,
        tools=overrides.get("tools", profile.tools),
        default_model_key=profile.default_model_key,
        description=overrides.get("description", profile.description),
        phase=profile.phase,
        prompt_template=overrides.get("prompt_template", profile.prompt_template),
    )


def list_agents() -> list[AgentProfile]:
    """Return all registered agents (with overrides applied), ordered by pipeline phase."""
    phase_order = {"plan": 0, "code": 1, "review": 2, "finalize": 3, "evolution": 4}
    agents = [get_agent(name) for name in _BUILTIN_AGENTS]
    return sorted(agents, key=lambda a: (phase_order.get(a.phase, 99), a.name))


def get_agent_tools(name: str) -> str:
    """Get the tool string for an agent, respecting user overrides.

    Falls back to the built-in tool string if no override exists.
    """
    agent = get_agent(name)
    if agent:
        return agent.tools
    # Fallback: return empty string (caller should handle)
    return ""


def _load_overrides() -> dict[str, dict[str, Any]]:
    """Load agent overrides from settings.json."""
    settings = load_settings()
    raw = settings.get("agent_overrides", {})
    # Normalize keys to uppercase
    return {k.upper(): v for k, v in raw.items()} if isinstance(raw, dict) else {}
