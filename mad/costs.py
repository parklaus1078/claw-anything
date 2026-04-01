"""Cost tracking for MAD runs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class CallCost:
    role: str
    cost_usd: float = 0.0
    duration_ms: int = 0
    num_turns: int = 0
    timestamp: str = ""


@dataclass
class RunCosts:
    run_id: str
    project_slug: str
    calls: list[CallCost] = field(default_factory=list)

    @property
    def total_cost_usd(self) -> float:
        return sum(c.cost_usd for c in self.calls)

    @property
    def total_duration_ms(self) -> int:
        return sum(c.duration_ms for c in self.calls)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> RunCosts | None:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            calls = [CallCost(**c) for c in data.get("calls", [])]
            return cls(
                run_id=data.get("run_id", ""),
                project_slug=data.get("project_slug", ""),
                calls=calls,
            )
        except (json.JSONDecodeError, TypeError, KeyError):
            return None
