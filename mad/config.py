"""Configuration and path management for MAD."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


def _mad_home() -> Path:
    """Root directory where MAD stores its own data (specs, logs, rules, evolution)."""
    return Path(os.environ.get("MAD_HOME", Path(__file__).resolve().parent.parent))


# Available models for Claude Code's --model flag.
AVAILABLE_MODELS = [
    "claude-opus-4-6",
    "claude-sonnet-4-6",
    "claude-sonnet-4-5",
    "claude-haiku-4-5-20251001",
    "opus",
    "sonnet",
    "haiku",
]

# Hard-coded fallback defaults (used when no settings.json exists)
_FALLBACK_PLANNER_MODEL = "sonnet"
_FALLBACK_CODER_MODEL = "sonnet"
_FALLBACK_REVIEWER_MODEL = "sonnet"

# Map Claude model names to Codex-compatible model names.
CODEX_MODEL_MAP = {
    "claude-opus-4-6": "gpt-5.4",
    "claude-sonnet-4-6": "gpt-5.4-mini",
    "claude-sonnet-4-5": "gpt-5.3-codex",
    "claude-haiku-4-5-20251001": "gpt-5.3-codex-spark",
    "opus": "gpt-5.4",
    "sonnet": "gpt-5.4-mini",
    "haiku": "gpt-5.3-codex-spark",
}

# Valid fallback backends
VALID_FALLBACK_BACKENDS = {"codex"}


def _settings_path() -> Path:
    return _mad_home() / "settings.json"


def load_settings() -> dict:
    """Load persistent settings from settings.json."""
    p = _settings_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def save_settings(data: dict) -> None:
    """Save persistent settings to settings.json."""
    p = _settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    # Merge with existing settings so unrelated keys are preserved
    existing = load_settings()
    existing.update(data)
    p.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")


def get_default_model(role: str) -> str:
    """Get the default model for a role, reading from settings.json first."""
    settings = load_settings()
    models = settings.get("models", {})
    fallbacks = {
        "planner": _FALLBACK_PLANNER_MODEL,
        "coder": _FALLBACK_CODER_MODEL,
        "reviewer": _FALLBACK_REVIEWER_MODEL,
    }
    return models.get(role, fallbacks.get(role, "sonnet"))


# Default pass score: 9/10 (90%)
_FALLBACK_PASS_SCORE = 9.0


def get_pass_score() -> float:
    """Get the review pass threshold from settings.json, or fallback to 9.0."""
    settings = load_settings()
    try:
        return float(settings.get("pass_score", _FALLBACK_PASS_SCORE))
    except (ValueError, TypeError):
        return _FALLBACK_PASS_SCORE


def get_fallback_backend() -> str | None:
    """Get the fallback backend from settings.json (e.g. 'codex'), or None if disabled."""
    settings = load_settings()
    backend = settings.get("fallback")
    if backend and backend in VALID_FALLBACK_BACKENDS:
        return backend
    return None


def get_webhook_url(role: str) -> str | None:
    """Get the Discord webhook URL for an agent role, or None if not configured.

    Matches the role prefix against webhook keys (e.g. role 'CODER-T1' matches key 'CODER').
    """
    settings = load_settings()
    webhooks = settings.get("webhooks", {})
    # Exact match first, then prefix match (CODER-T1 → CODER, REVIEWER-I2 → REVIEWER)
    role_upper = role.upper()
    if role_upper in webhooks and webhooks[role_upper]:
        return webhooks[role_upper]
    for key, url in webhooks.items():
        if role_upper.startswith(key.upper()) and url:
            return url
    return None


def get_webhooks_enabled() -> bool:
    """Return True if any webhook URL is configured."""
    settings = load_settings()
    webhooks = settings.get("webhooks", {})
    return any(bool(url) for url in webhooks.values())


def get_budget() -> float:
    """Get the per-call budget in USD from settings.json, or 0 (unlimited)."""
    settings = load_settings()
    try:
        return float(settings.get("budget_usd", 0))
    except (ValueError, TypeError):
        return 0.0


# These are read dynamically so they reflect settings.json at import time.
# CLI commands call get_default_model() for runtime defaults.
DEFAULT_PLANNER_MODEL = _FALLBACK_PLANNER_MODEL
DEFAULT_CODER_MODEL = _FALLBACK_CODER_MODEL
DEFAULT_REVIEWER_MODEL = _FALLBACK_REVIEWER_MODEL


@dataclass
class RunConfig:
    """Immutable configuration for a single orchestrator run."""

    project_dir: Path
    idea: str
    max_iterations: int = 10
    run_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))

    # Per-agent model selection
    planner_model: str = DEFAULT_PLANNER_MODEL
    coder_model: str = DEFAULT_CODER_MODEL
    reviewer_model: str = DEFAULT_REVIEWER_MODEL

    # Review pass threshold (score out of 10; default 9 = 90%)
    pass_score: float = 9.0

    # Per-call budget limit in USD (0 = unlimited)
    budget_usd: float = 0.0

    # Project slug — when set, specs/logs are scoped per-project
    project_slug: str = ""

    # ----- derived paths -----
    @property
    def mad_home(self) -> Path:
        return _mad_home()

    @property
    def specs_dir(self) -> Path:
        if self.project_slug:
            return self.mad_home / "projects" / self.project_slug / "specs"
        return self.mad_home / "specs"

    @property
    def logs_dir(self) -> Path:
        if self.project_slug:
            return self.mad_home / "projects" / self.project_slug / "logs"
        return self.mad_home / "logs"

    @property
    def rules_dir(self) -> Path:
        return self.mad_home / "rules"

    @property
    def evolution_dir(self) -> Path:
        return self.mad_home / "evolution"

    # ----- well-known file paths -----
    @property
    def tickets_file(self) -> Path:
        return self.specs_dir / "tickets.md"

    @property
    def research_file(self) -> Path:
        return self.specs_dir / "research.md"

    @property
    def domain_research_file(self) -> Path:
        return self.specs_dir / "domain_research.md"

    @property
    def refinement_file(self) -> Path:
        return self.specs_dir / "refinement_list.md"

    @property
    def session_file(self) -> Path:
        return self.specs_dir / ".session_id"

    @property
    def coder_session_file(self) -> Path:
        return self.specs_dir / ".session_id.coder"

    @property
    def state_file(self) -> Path:
        return self.specs_dir / ".run_state.json"

    @property
    def evolution_file(self) -> Path:
        return self.evolution_dir / "learnings.md"

    @property
    def general_rules_file(self) -> Path:
        return self.rules_dir / "general_coding_rules.md"

    def review_log(self, iteration: int) -> Path:
        return self.specs_dir / f"review_iteration_{iteration}.md"

    def epoch_log(self) -> Path:
        return self.evolution_dir / f"epoch_{self.run_id}.md"

    def ensure_dirs(self) -> None:
        """Create all required directories."""
        for d in (self.specs_dir, self.logs_dir, self.rules_dir, self.evolution_dir):
            d.mkdir(parents=True, exist_ok=True)
        self.project_dir.mkdir(parents=True, exist_ok=True)


# Tool permissions per agent role
PLANNER_TOOLS = "Read,Grep,Glob,Write,WebSearch,WebFetch,Skill"
CODER_TOOLS = "Read,Edit,Write,Bash,Grep,Glob"
REVIEWER_TOOLS = "Read,Bash,Grep,Glob,Write,Skill"
FINALIZER_TOOLS = "Read,Write,Grep,Glob"
VERIFIER_TOOLS = "Read,Bash,Grep,Glob,Skill"
