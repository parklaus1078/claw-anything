"""Run metrics tracking for evolution validation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class RunMetrics:
    run_id: str
    project_slug: str
    timestamp: str = ""
    total_iterations: int = 0
    final_score: float | None = None
    scores: dict = field(default_factory=dict)
    approved: bool = False
    learnings_count: int = 0


def _metrics_file(evolution_dir: Path) -> Path:
    return evolution_dir / "metrics.json"


def save_metrics(evolution_dir: Path, metrics: RunMetrics) -> None:
    """Append a run's metrics to the metrics history file."""
    if not metrics.timestamp:
        metrics.timestamp = datetime.now().isoformat()
    path = _metrics_file(evolution_dir)
    history = load_all_metrics(evolution_dir)
    history.append(asdict(metrics))
    path.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")


def load_all_metrics(evolution_dir: Path) -> list[dict]:
    """Load all historical run metrics."""
    path = _metrics_file(evolution_dir)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def compute_trend(evolution_dir: Path, n: int = 5) -> str:
    """Compute a human-readable trend summary over the last N runs.

    Returns a markdown block suitable for injection into the evolution prompt.
    """
    history = load_all_metrics(evolution_dir)
    if len(history) < 2:
        return "Not enough data for trend analysis (need 2+ completed runs)."

    recent = history[-n:] if len(history) >= n else history
    older = history[-2 * n:-n] if len(history) >= 2 * n else history[: max(1, len(history) - n)]

    def avg_score(runs: list[dict]) -> float:
        scores = [r.get("final_score") for r in runs if r.get("final_score") is not None]
        return sum(scores) / len(scores) if scores else 0

    def avg_iterations(runs: list[dict]) -> float:
        iters = [r.get("total_iterations", 0) for r in runs]
        return sum(iters) / len(iters) if iters else 0

    recent_avg = avg_score(recent)
    older_avg = avg_score(older)
    recent_iters = avg_iterations(recent)

    # Per-criterion trends
    all_criteria = set()
    for r in recent:
        all_criteria.update(r.get("scores", {}).keys())

    criterion_lines = []
    for c in sorted(all_criteria):
        vals = [r["scores"][c] for r in recent if c in r.get("scores", {}) and r["scores"][c] is not None]
        if vals:
            avg = sum(vals) / len(vals)
            criterion_lines.append(f"  - {c}: {avg:.1f}/10")

    direction = "improving" if recent_avg > older_avg else "declining" if recent_avg < older_avg else "stable"

    lines = [
        f"## Metrics Trend (last {len(recent)} runs)",
        f"- Average score: {older_avg:.1f} -> {recent_avg:.1f} ({direction})",
        f"- Average iterations to completion: {recent_iters:.1f}",
        f"- Total runs tracked: {len(history)}",
        "",
        "### Per-Criterion Averages (recent runs)",
    ]
    lines.extend(criterion_lines)

    return "\n".join(lines)
