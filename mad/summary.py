"""Discord summary bot — posts per-phase log summaries to a dedicated SUMMARY webhook channel."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from mad.config import RunConfig, get_webhook_url
from mad.discord_webhook import post_message_async


# Human-readable phase labels for each pipeline step.
PHASE_LABELS = {
    "brainstorm": "Brainstorm",
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
    "brainstorm": "\U0001f4ad",        # 💭
    "plan_rules": "\U0001f9e9",        # 🧩
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

# Maps phase keys to log_suffix patterns (glob-friendly) for finding log files.
_PHASE_LOG_PATTERNS = {
    "brainstorm": "brainstorm_r*",
    "plan_rules": "planner_step1_rules",
    "plan_domain": "planner_step2_domain",
    "plan_research": "planner_step3_research",
    "plan_spotcheck": "planner_step3_verify",
    "plan_tickets": "planner_step4_tickets",
    "code_full": "coder_sprint_T*",
    "code_fix": "coder_fix_*",
    "review": "reviewer_iteration_*",
    "finalize": "finalizer_readme",
    "evolution": "evolution",
}


def _get_summary_url() -> str | None:
    """Get the SUMMARY webhook URL, if configured."""
    return get_webhook_url("SUMMARY")


# ---------------------------------------------------------------------------
# Log summarization
# ---------------------------------------------------------------------------

def _read_log_output(log_path: Path) -> str:
    """Read the '## Agent Output' section from a markdown log file."""
    text = log_path.read_text(encoding="utf-8")
    marker = "## Agent Output"
    idx = text.find(marker)
    if idx != -1:
        return text[idx + len(marker):].strip()
    # Fallback: try "## Output" (used for failed logs)
    marker2 = "## Output"
    idx2 = text.find(marker2)
    if idx2 != -1:
        return text[idx2 + len(marker2):].strip()
    return text


def _read_log_cost(log_path: Path) -> dict:
    """Read cost data from the corresponding JSON log file."""
    json_path = log_path.with_suffix(".json")
    if not json_path.exists():
        return {}
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {
                "cost_usd": data.get("total_cost_usd") or data.get("cost_usd", 0),
                "num_turns": data.get("num_turns", 0),
                "duration_ms": data.get("total_duration_ms") or data.get("duration_ms", 0),
            }
    except (json.JSONDecodeError, TypeError):
        pass
    return {}


def _extract_files_written(text: str) -> list[str]:
    """Extract file paths that were written/created from agent output."""
    patterns = [
        r"(?:Writ|Creat|Sav)(?:e|ing|ten|ed)\s+(?:to\s+)?[`'\"]?([^\s`'\"]+\.\w+)",
        r"Write\s+tool.*?file_path['\"]:\s*['\"]([^'\"]+)",
        r"(?:rules|tickets|research|refinement|README).*?(?:at|to|:)\s+[`'\"]?([^\s`'\"]+\.(?:md|json|yaml|toml))",
    ]
    files = []
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            f = m.group(1)
            if len(f) > 5 and "/" in f:  # likely a real path
                files.append(f)
    return list(dict.fromkeys(files))[:10]  # dedupe, limit


def _extract_ticket_title(text: str) -> str | None:
    """Extract the ticket title from a coder sprint log (prompt or output)."""
    # Match "### Ticket N: Title" from the embedded ticket content
    m = re.search(r"###\s*Ticket\s*\d+\s*[:—–-]\s*(.+)", text)
    if m:
        return m.group(1).strip()
    # Fallback: "Ticket N of M" header line
    m = re.search(r"implementing Ticket\s*(\d+).*?YOUR TICKET:", text, re.DOTALL)
    return None


def _extract_tech_stack(text: str) -> str | None:
    """Extract TECH_STACK line from planner output."""
    m = re.search(r"TECH_STACK:\s*(.+)", text)
    return m.group(1).strip() if m else None


def _extract_ticket_count(text: str) -> int:
    """Count tickets in planner output."""
    return len(re.findall(r"^### Ticket \d+", text, re.MULTILINE))


def _extract_score(text: str) -> float | None:
    """Extract SCORE: X/10 from reviewer output."""
    m = re.search(r"SCORE:\s*([\d.]+)\s*/\s*10", text)
    return float(m.group(1)) if m else None


def _extract_issues(text: str) -> tuple[int, int, int]:
    """Count critical/major/minor issues from reviewer output."""
    critical = len(re.findall(r"^\d+\.\s*\[(?:BUG|CRITICAL|MISSING)", text, re.MULTILINE | re.IGNORECASE))
    major = len(re.findall(r"^\d+\.\s*\[(?:MAJOR|SHOULD)", text, re.MULTILINE | re.IGNORECASE))
    minor = len(re.findall(r"^\d+\.\s*\[(?:MINOR|NICE|STYLE)", text, re.MULTILINE | re.IGNORECASE))
    # Fallback: count numbered items under section headers
    if critical == 0 and major == 0:
        sections = re.split(r"^##\s+", text, flags=re.MULTILINE)
        for section in sections:
            lower = section.lower()
            items = len(re.findall(r"^\d+\.", section, re.MULTILINE))
            if "critical" in lower or "must fix" in lower:
                critical += items
            elif "major" in lower or "should fix" in lower:
                major += items
            elif "minor" in lower or "nice" in lower:
                minor += items
    return critical, major, minor


def _extract_commands_run(text: str) -> list[str]:
    """Extract shell commands that were run from agent output."""
    cmds = []
    for m in re.finditer(r"(?:Bash|command)['\"]?:\s*['\"]([^'\"]+)", text, re.IGNORECASE):
        cmds.append(m.group(1)[:80])
    # Also check for ``` code blocks after "Running" or "Executing"
    for m in re.finditer(r"(?:Running|Executing|Ran).*?`([^`]+)`", text, re.IGNORECASE):
        cmds.append(m.group(1)[:80])
    return list(dict.fromkeys(cmds))[:8]


def _summarize_text(text: str, max_len: int = 300) -> str:
    """Extract the first meaningful paragraph or sentence from agent output."""
    # Skip markdown headers and metadata
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            if lines:
                break
            continue
        lines.append(stripped)
    result = " ".join(lines)
    if len(result) > max_len:
        result = result[:max_len] + "..."
    return result


def summarize_phase_logs(cfg: RunConfig, phase: str) -> str | None:
    """Read agent logs for a phase and produce a condensed summary.

    Args:
        cfg: RunConfig with logs_dir and run_id.
        phase: Phase key from PHASE_LABELS.

    Returns:
        Formatted summary string, or None if no logs found.
    """
    pattern = _PHASE_LOG_PATTERNS.get(phase)
    if not pattern:
        return None

    # Find log files matching this phase for the current run
    glob_pattern = f"{cfg.run_id}_{pattern}.md"
    log_files = sorted(cfg.logs_dir.glob(glob_pattern))

    if not log_files:
        # Try without run_id prefix (some logs might have slightly different naming)
        log_files = sorted(cfg.logs_dir.glob(f"*_{pattern}.md"))
        # Filter to recent files (last hour)
        import time as _time
        cutoff = _time.time() - 3600
        log_files = [f for f in log_files if f.stat().st_mtime > cutoff]

    if not log_files:
        return None

    label = PHASE_LABELS.get(phase, phase)
    emoji = _PHASE_EMOJI.get(phase, "\u2139\ufe0f")
    sections = [f"{emoji} **{label} — Log Summary**"]

    # Aggregate cost across all logs for this phase
    total_cost = 0.0
    total_turns = 0
    total_duration_ms = 0
    for lf in log_files:
        c = _read_log_cost(lf)
        total_cost += c.get("cost_usd", 0)
        total_turns += c.get("num_turns", 0)
        total_duration_ms += c.get("duration_ms", 0)

    # --- Multi-file phases (handle all files at once) ---

    if phase == "code_full":
        sections.append(f"**Sprints completed:** {len(log_files)}")
        all_files: list[str] = []
        for sprint_log in log_files:
            full_text = sprint_log.read_text(encoding="utf-8")
            sprint_output = _read_log_output(sprint_log)
            t_match = re.search(r"_T(\d+)", sprint_log.stem)
            t_num = t_match.group(1) if t_match else "?"
            t_title = _extract_ticket_title(sprint_output) or _extract_ticket_title(full_text)
            is_retry = "_A" in sprint_log.stem
            sprint_files = _extract_files_written(sprint_output)
            all_files.extend(sprint_files)
            sprint_cost = _read_log_cost(sprint_log)
            ticket_label = f"T{t_num}"
            if t_title:
                ticket_label += f": {t_title[:60]}"
            if is_retry:
                a_match = re.search(r"_A(\d+)", sprint_log.stem)
                ticket_label += f" (retry #{a_match.group(1)})" if a_match else " (retry)"
            status_parts = []
            if sprint_files:
                status_parts.append(f"{len(sprint_files)} files")
            if sprint_cost.get("cost_usd"):
                status_parts.append(f"${sprint_cost['cost_usd']:.4f}")
            status = f" — {', '.join(status_parts)}" if status_parts else ""
            sections.append(f"  **{ticket_label}**{status}")
            for f in sprint_files[:3]:
                sections.append(f"    - `{f}`")
        unique_files = list(dict.fromkeys(all_files))
        if unique_files:
            sections.append(f"\n**Total files touched:** {len(unique_files)}")

    elif phase == "code_fix":
        all_fix_files: list[str] = []
        for fix_log in log_files:
            fix_output = _read_log_output(fix_log)
            fix_files = _extract_files_written(fix_output)
            all_fix_files.extend(fix_files)
        unique_fix = list(dict.fromkeys(all_fix_files))
        if unique_fix:
            sections.append(f"**Files modified:** {len(unique_fix)}")
            for f in unique_fix[:8]:
                sections.append(f"  - `{f}`")

    elif phase == "brainstorm":
        if len(log_files) > 1:
            sections.append(f"**Participants:** {len(log_files)} agents across all rounds")
        personas = set()
        for lf in log_files:
            name = lf.stem.replace(f"{cfg.run_id}_brainstorm_", "")
            name = re.sub(r"^r[123]_", "", name)
            if name and name != "facilitator":
                personas.add(name.replace("_", " ").title())
        if personas:
            sections.append(f"**Personas:** {', '.join(sorted(personas))}")

    # --- Single-file phases (use only the first/primary log) ---

    else:
        output = _read_log_output(log_files[0])

        if phase == "plan_rules":
            tech = _extract_tech_stack(output)
            if tech:
                sections.append(f"**Tech stack:** {tech}")
            files = _extract_files_written(output)
            if files:
                sections.append("**Files created:**")
                for f in files:
                    sections.append(f"  - `{f}`")

        elif phase == "plan_tickets":
            count = _extract_ticket_count(output)
            if count:
                sections.append(f"**Tickets generated:** {count}")
            titles = re.findall(r"^### (Ticket \d+:.+)", output, re.MULTILINE)
            for title in titles[:6]:
                sections.append(f"  - {title}")
            if len(titles) > 6:
                sections.append(f"  - ... and {len(titles) - 6} more")

        elif phase in ("plan_domain", "plan_research"):
            summary = _summarize_text(output, max_len=400)
            if summary:
                sections.append(f"> {summary}")
            files = _extract_files_written(output)
            if files:
                sections.append(f"**Written to:** `{files[0]}`")

        elif phase == "plan_spotcheck":
            corrections = output.lower().count("correction")
            if corrections:
                sections.append(f"**Corrections found:** {corrections}")
            else:
                sections.append("No corrections needed.")

        elif phase == "review":
            score = _extract_score(output)
            if score is not None:
                sections.append(f"**Score:** {score}/10")
            critical, major, minor = _extract_issues(output)
            if critical or major or minor:
                sections.append(f"**Issues:** {critical} critical, {major} major, {minor} minor")
            crit_items = re.findall(r"^\d+\.\s*(\[(?:BUG|CRITICAL|MISSING)\].+)", output, re.MULTILINE | re.IGNORECASE)
            for item in crit_items[:3]:
                sections.append(f"  - {item[:120]}")

        elif phase == "finalize":
            sections.append("README.md generated.")
            files = _extract_files_written(output)
            if files:
                for f in files[:3]:
                    sections.append(f"  - `{f}`")

        elif phase == "evolution":
            learning_count = output.count("\n- ")
            if learning_count:
                sections.append(f"**New learnings captured:** ~{learning_count}")

    # Append cost/performance footer
    meta = []
    if total_cost:
        meta.append(f"${total_cost:.4f}")
    if total_turns:
        meta.append(f"{total_turns} turns")
    if total_duration_ms:
        dur_s = total_duration_ms / 1000
        meta.append(f"{dur_s:.1f}s" if dur_s < 60 else f"{dur_s / 60:.1f}min")
    if meta:
        sections.append(f"\n*{' | '.join(meta)}*")

    return "\n".join(sections) if len(sections) > 1 else None


# ---------------------------------------------------------------------------
# Posting
# ---------------------------------------------------------------------------

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
            - log_summary: str — condensed log summary (from summarize_phase_logs)
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

    # Append log summary if provided
    if "log_summary" in details and details["log_summary"]:
        lines.append("")
        lines.append(details["log_summary"])

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


def post_log_summary(cfg: RunConfig, phase: str) -> None:
    """Summarize agent logs for a phase and post to the SUMMARY webhook.

    This is the main entry point for log summarization. Call it after a phase
    completes to post a condensed summary of what the agents actually did.

    Does nothing if no SUMMARY webhook is configured or no logs are found.
    """
    url = _get_summary_url()
    if not url:
        return

    summary = summarize_phase_logs(cfg, phase)
    if summary:
        post_message_async(url, summary, role="MAD Summary")


class PhaseTimer:
    """Context manager that tracks elapsed time for a pipeline phase."""

    def __init__(self, phase: str, cfg: RunConfig | None = None):
        self.phase = phase
        self.cfg = cfg
        self.start_time: float = 0.0
        self.elapsed: float = 0.0

    def __enter__(self) -> "PhaseTimer":
        self.start_time = time.monotonic()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.elapsed = time.monotonic() - self.start_time

    def summary(self, **details: Any) -> None:
        """Post a phase transition summary + log summary with timing included."""
        details.setdefault("duration_s", self.elapsed)

        # If cfg is available, also summarize the actual logs
        if self.cfg:
            log_text = summarize_phase_logs(self.cfg, self.phase)
            if log_text:
                details["log_summary"] = log_text

        post_phase_summary(self.phase, details)
