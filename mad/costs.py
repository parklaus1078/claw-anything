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
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    timestamp: str = ""


def _safe_int(v: object) -> int:
    """Convert a value to int, defaulting to 0."""
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


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

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    @property
    def total_cache_read_tokens(self) -> int:
        return sum(c.cache_read_tokens for c in self.calls)

    @property
    def total_cache_creation_tokens(self) -> int:
        return sum(c.cache_creation_tokens for c in self.calls)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> RunCosts | None:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            calls = []
            for c in data.get("calls", []):
                calls.append(CallCost(
                    role=c.get("role", ""),
                    cost_usd=c.get("cost_usd", 0.0),
                    duration_ms=_safe_int(c.get("duration_ms", 0)),
                    num_turns=_safe_int(c.get("num_turns", 0)),
                    input_tokens=_safe_int(c.get("input_tokens", 0)),
                    output_tokens=_safe_int(c.get("output_tokens", 0)),
                    cache_read_tokens=_safe_int(c.get("cache_read_tokens", 0)),
                    cache_creation_tokens=_safe_int(c.get("cache_creation_tokens", 0)),
                    timestamp=c.get("timestamp", ""),
                ))
            return cls(
                run_id=data.get("run_id", ""),
                project_slug=data.get("project_slug", ""),
                calls=calls,
            )
        except (json.JSONDecodeError, TypeError, KeyError):
            return None
