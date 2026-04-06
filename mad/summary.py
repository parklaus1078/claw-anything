"""Discord summary bot — posts per-phase summaries to a dedicated SUMMARY webhook channel."""

from __future__ import annotations

import time
from typing import Any

from mad.config import get_webhook_url
from mad.discord_webhook import post_message_async


# Human-readable phase labels for each pipeline step.
PHASE_LABELS = {
    "plan_rules": "Stack Selection & Coding Rules",
    "plan_domain": "Domain Research",
    "plan_research": "Stack Research",
    "plan_spotcheck": "Plan Verification",
    "plan_tickets": "Ticket Planning",
    "code_full": "Ticket Implementation",
    "code_fix": "Fix Implementation",
    "review": "Review",
    "finalize": "Finalization",
    "evolution": "Evolution",
}

# Emoji mapping for visual clarity in Discord
_PHASE_EMOJI = {
    "plan_rules": "\U0001f9e9",       # 🧩
    "plan_domain": "\U0001f50d",       # 🔍
    "plan_research": "\U0001f4da",     # 📚
    "plan_spotcheck": "\u2705",        # ✅
    "plan_tickets": "\U0001f3ab",      # 🎫
    "code_full": "\U0001f528",         # 🔨
    "code_fix": "\U0001f527",          # 🔧
    "review": "\U0001f50e",            # 🔎
    "finalize": "\U0001f4dd",          # 📝
    "evolution": "\U0001f9ec",         # 🧬
}


def _get_summary_url() -> str | None:
    """Get the SUMMARY webhook URL, if configured."""
    return get_webhook_url("SUMMARY")


def format_phase_summary(phase: str, details: dict[str, Any]) -> str:
    """Format a phase summary as a Discord-friendly markdown message.

    Args:
        phase: Phase key from PHASE_LABELS.
        details: Dict with phase-specific info. Common keys:
            - duration_s: float — elapsed seconds
            - cost_usd: float — cost in USD
            - outcome: str — short description of what happened
            - score: float — review score (for review phase)
            - approved: bool — whether review passed
            - tickets_total: int — total tickets
            - tickets_done: int — tickets completed
            - iteration: int — review iteration number
            - issues_critical: int — critical issues found
            - issues_major: int — major issues found
    """
    label = PHASE_LABELS.get(phase, phase)
    emoji = _PHASE_EMOJI.get(phase, "\u2139\ufe0f")  # ℹ️ default

    lines = [f"{emoji} **{label}**"]

    # Duration and cost
    meta_parts = []
    if "duration_s" in details:
        dur = details["duration_s"]
        if dur >= 60:
            meta_parts.append(f"{dur / 60:.1f}min")
        else:
            meta_parts.append(f"{dur:.1f}s")
    if "cost_usd" in details and details["cost_usd"]:
        meta_parts.append(f"${details['cost_usd']:.4f}")
    if meta_parts:
        lines.append(f"*{' | '.join(meta_parts)}*")

    # Phase-specific details
    if "outcome" in details:
        lines.append(f"> {details['outcome']}")

    if "iteration" in details:
        lines.append(f"Iteration: **{details['iteration']}**")

    if "score" in details:
        score = details["score"]
        approved = details.get("approved", False)
        status = "APPROVED \u2705" if approved else "NEEDS WORK \u274c"
        lines.append(f"Score: **{score}/10** — {status}")

    if "issues_critical" in details or "issues_major" in details:
        crit = details.get("issues_critical", 0)
        major = details.get("issues_major", 0)
        if crit or major:
            lines.append(f"Issues: {crit} critical, {major} major")

    if "tickets_total" in details:
        done = details.get("tickets_done", details["tickets_total"])
        lines.append(f"Tickets: {done}/{details['tickets_total']}")

    return "\n".join(lines)


def post_phase_summary(phase: str, details: dict[str, Any]) -> None:
    """Post a phase summary to the SUMMARY Discord webhook (async, non-blocking).

    Does nothing if no SUMMARY webhook is configured.
    """
    url = _get_summary_url()
    if not url:
        return

    text = format_phase_summary(phase, details)
    post_message_async(url, text, role="MAD Summary")


class PhaseTimer:
    """Context manager that tracks elapsed time for a pipeline phase."""

    def __init__(self, phase: str):
        self.phase = phase
        self.start_time: float = 0.0
        self.elapsed: float = 0.0

    def __enter__(self) -> "PhaseTimer":
        self.start_time = time.monotonic()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.elapsed = time.monotonic() - self.start_time

    def summary(self, **details: Any) -> None:
        """Post a summary for this phase with timing included."""
        details.setdefault("duration_s", self.elapsed)
        post_phase_summary(self.phase, details)
