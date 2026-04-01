"""Run state persistence — allows resuming after crashes or limit hits."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List

from mad.config import RunConfig


# Phases in execution order
PHASES = ("plan", "code", "review", "fix", "finalize", "evolution")


@dataclass
class RunState:
    """Tracks where a run left off so it can be resumed."""

    idea: str = ""
    project_dir: str = ""
    run_id: str = ""
    max_iterations: int = 10

    # Model selection (persisted for resume)
    planner_model: str = ""
    coder_model: str = ""
    reviewer_model: str = ""

    # Project identity
    project_slug: str = ""

    # Progress tracking
    phase: str = ""          # last COMPLETED phase
    iteration: int = 0       # current review/fix iteration (0 = not started)
    approved: bool = False   # whether the reviewer approved
    finished: bool = False   # entire run completed

    # Sprint-level tracking (for per-ticket coding)
    completed_tickets: List[int] = field(default_factory=list)
    current_ticket: int = -1  # -1 = not started

    def save(self, cfg: RunConfig) -> None:
        """Persist state to disk."""
        self.idea = cfg.idea
        self.project_dir = str(cfg.project_dir)
        self.run_id = cfg.run_id
        self.max_iterations = cfg.max_iterations
        self.planner_model = cfg.planner_model
        self.coder_model = cfg.coder_model
        self.reviewer_model = cfg.reviewer_model
        self.project_slug = cfg.project_slug
        cfg.state_file.write_text(
            json.dumps(asdict(self), indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls, state_file: Path) -> RunState | None:
        """Load state from disk. Returns None if no state file exists."""
        if not state_file.exists():
            return None
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except (json.JSONDecodeError, TypeError):
            return None

    def mark(self, cfg: RunConfig, *, phase: str, iteration: int | None = None,
             approved: bool | None = None, finished: bool = False) -> None:
        """Update and persist state after completing a step."""
        self.phase = phase
        if iteration is not None:
            self.iteration = iteration
        if approved is not None:
            self.approved = approved
        self.finished = finished
        self.save(cfg)

    @property
    def resume_description(self) -> str:
        """Human-readable description of where to resume from."""
        if self.finished:
            return "Run already completed."
        if not self.phase:
            return "No progress — starting from the beginning."
        if self.phase == "plan":
            return "Planning complete. Resuming from coding phase."
        if self.phase == "code":
            return f"Coding complete. Resuming from review (iteration {self.iteration + 1})."
        if self.phase == "review":
            if self.approved:
                return "Review approved. Resuming from finalization."
            return f"Review iteration {self.iteration} found issues. Resuming from fix."
        if self.phase == "fix":
            return f"Fix applied. Resuming from review (iteration {self.iteration + 1})."
        if self.phase == "finalize":
            return "Finalization complete. Resuming from evolution capture."
        return f"Resuming after phase '{self.phase}'."
