"""Core agent runner — invokes claude -p and manages session/logging."""

from __future__ import annotations

import json
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from mad.config import RunConfig
from mad.console import console, log_err, log_ok, log_phase, log_warn, _print_lock

# Module-level cost accumulator — collects costs across all agent calls in a run
_run_costs: list[dict] = []


def get_run_costs() -> list[dict]:
    """Return accumulated costs from all agent calls since last reset."""
    return list(_run_costs)


def reset_run_costs() -> None:
    """Clear accumulated costs (call at the start of each run)."""
    _run_costs.clear()


class AgentLimitError(RuntimeError):
    """Raised when claude -p fails due to a usage limit or context error."""
    pass


class AgentError(RuntimeError):
    """Raised when claude -p fails for any other reason."""
    pass


_SESSION_EXPIRED_SIGNALS = [
    "no conversation found",
    "session not found",
    "session_id",
    "invalid session",
    "could not find",
]

_LIMIT_SIGNALS = [
    "rate limit", "rate_limit", "usage limit", "token limit",
    "quota", "exceeded", "overloaded", "529", "too many requests",
    "capacity", "context window",
]


def _build_cmd(prompt: str, tools: str, model: str, resume_session: str,
               json_schema: str = "", max_budget_usd: float = 0) -> tuple[list[str], str]:
    """Build the claude CLI command. Returns (cmd, stdin_prompt).

    The prompt is always passed via stdin to avoid OS argument length limits.
    """
    cmd = [
        "claude",
        "-p",
        "--allowedTools", tools,
        "--output-format", "json",
    ]
    if model:
        cmd += ["--model", model]
    if resume_session:
        cmd += ["--resume", resume_session]
    if json_schema:
        cmd += ["--json-schema", json_schema]
    if max_budget_usd > 0:
        cmd += ["--max-budget-usd", str(max_budget_usd)]
    return cmd, prompt


_current_role: str = ""
_live_lock = threading.Lock()
_live_active = False


def _invoke(cmd: list[str], cwd: str, stdin_data: str = "") -> subprocess.CompletedProcess:
    """Run a subprocess with a live spinner showing elapsed time.

    When multiple invocations run in parallel (e.g., planner steps 2+3),
    only the first gets the spinner — others fall back to periodic log messages.

    Stdout/stderr are drained in background threads to prevent pipe deadlocks.
    """
    global _live_active

    try:
        proc = subprocess.Popen(
            cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.PIPE if stdin_data else None, text=True,
        )
        if stdin_data:
            proc.stdin.write(stdin_data)
            proc.stdin.close()
    except KeyboardInterrupt:
        raise AgentLimitError("Interrupted by user — resume with 'mad resume'")

    # Drain stdout/stderr in background threads to prevent pipe buffer deadlock
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    def _drain(stream, target: list[str]):
        for line in stream:
            target.append(line)

    stdout_thread = threading.Thread(target=_drain, args=(proc.stdout, stdout_chunks), daemon=True)
    stderr_thread = threading.Thread(target=_drain, args=(proc.stderr, stderr_chunks), daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    start = time.monotonic()
    role = _current_role or "agent"

    # Decide whether this call gets the spinner or falls back to periodic logs
    use_spinner = False
    with _live_lock:
        if not _live_active:
            _live_active = True
            use_spinner = True

    try:
        if use_spinner:
            _run_with_spinner(proc, role, start)
        else:
            _run_with_periodic_log(proc, role, start)

        # Wait for drain threads to finish
        stdout_thread.join(timeout=10)
        stderr_thread.join(timeout=10)

        elapsed = int(time.monotonic() - start)
        mins, secs = divmod(elapsed, 60)
        time_str = f"{mins}m{secs:02d}s" if mins else f"{secs}s"

        stdout = "".join(stdout_chunks)
        stderr = "".join(stderr_chunks)

        log_phase(role, f"Finished in {time_str}")

        return subprocess.CompletedProcess(
            args=cmd, returncode=proc.returncode, stdout=stdout, stderr=stderr,
        )
    except KeyboardInterrupt:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        raise AgentLimitError("Interrupted by user — resume with 'mad resume'")
    finally:
        if use_spinner:
            with _live_lock:
                _live_active = False


def _run_with_spinner(proc: subprocess.Popen, role: str, start: float) -> None:
    """Show a live animated spinner while the process runs."""
    spinner = Spinner("dots", text=Text(f" {role} running... 0s", style="dim"))
    live = Live(spinner, console=console, refresh_per_second=4, transient=True)
    live.start()
    try:
        while proc.poll() is None:
            elapsed = int(time.monotonic() - start)
            mins, secs = divmod(elapsed, 60)
            time_str = f"{mins}m{secs:02d}s" if mins else f"{secs}s"
            spinner.update(text=Text(f" {role} running... {time_str}", style="dim"))
            time.sleep(0.25)
    finally:
        live.stop()


def _run_with_periodic_log(proc: subprocess.Popen, role: str, start: float) -> None:
    """Print periodic status messages when spinner is unavailable (parallel runs)."""
    last_log = 0
    while proc.poll() is None:
        elapsed = int(time.monotonic() - start)
        if elapsed - last_log >= 30:  # log every 30 seconds
            mins, secs = divmod(elapsed, 60)
            time_str = f"{mins}m{secs:02d}s" if mins else f"{secs}s"
            log_phase(role, f"Still running... {time_str}")
            last_log = elapsed
        time.sleep(1)


def _parse(raw: str) -> tuple[str, str, dict]:
    """Parse JSON output, return (session_id, result_text, usage_info)."""
    try:
        data = json.loads(raw)
        usage = {
            "cost_usd": data.get("total_cost_usd", 0) or 0,
            "duration_ms": data.get("total_duration_ms", 0) or 0,
            "num_turns": data.get("num_turns", 0) or 0,
        }
        return data.get("session_id", ""), data.get("result", ""), usage
    except (json.JSONDecodeError, TypeError):
        return "", raw, {}


def _is_session_expired(output: str) -> bool:
    low = output.lower()
    return any(sig in low for sig in _SESSION_EXPIRED_SIGNALS)


def _is_limit_hit(output: str) -> bool:
    low = output.lower()
    return any(sig in low for sig in _LIMIT_SIGNALS)


def _write_log(path: Path, role: str, cfg: RunConfig, session_id: str,
               result_text: str, log_file: Path, failed: bool = False,
               exit_code: int | None = None) -> None:
    title = f"{role} (FAILED)" if failed else role
    lines = [
        f"# Agent Log: {title}",
        f"- **Run ID**: {cfg.run_id}",
        f"- **Timestamp**: {datetime.now().isoformat()}",
        f"- **Project**: {cfg.project_dir}",
    ]
    if failed and exit_code is not None:
        lines.append(f"- **Exit code**: {exit_code}")
    else:
        lines.append(f"- **Session**: {session_id or 'N/A'}")
    lines.append(f"- **Log file**: {log_file}")
    lines.append(f"\n## {'Output' if failed else 'Agent Output'}\n\n{result_text}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_agent(
    cfg: RunConfig,
    *,
    role: str,
    prompt: str,
    tools: str,
    model: str = "",
    resume_session: str = "",
    log_suffix: str = "agent",
    cwd: str = "",
) -> str:
    """Run a claude -p invocation and return the session_id.

    Args:
        cwd: Working directory for the claude process. Defaults to cfg.project_dir.
             Use cfg.specs_dir for planner agents that write to specs/.

    If --resume fails because the session expired (common after credit limit
    hits), automatically retries without --resume so the run can continue.

    Raises:
        AgentLimitError: if the failure looks like a usage limit hit.
        AgentError: for all other failures.
    """
    log_file = cfg.logs_dir / f"{cfg.run_id}_{log_suffix}.json"
    readable_log = cfg.logs_dir / f"{cfg.run_id}_{log_suffix}.md"
    work_dir = cwd or str(cfg.project_dir)

    global _current_role
    model_label = f" (model: {model})" if model else ""
    log_phase(role, f"Starting agent...{model_label}")

    _current_role = role
    budget = getattr(cfg, "budget_usd", 0) or 0
    cmd, stdin_data = _build_cmd(prompt, tools, model, resume_session, max_budget_usd=budget)
    result = _invoke(cmd, work_dir, stdin_data=stdin_data)
    raw_output = result.stdout or result.stderr or ""

    # ---- Handle expired session: retry without --resume ----
    if result.returncode != 0 and resume_session and _is_session_expired(raw_output):
        log_warn(
            f"Session {resume_session[:12]}... expired (common after credit limits). "
            "Retrying without session resumption."
        )
        cmd, stdin_data = _build_cmd(prompt, tools, model, resume_session="", max_budget_usd=budget)
        result = _invoke(cmd, work_dir, stdin_data=stdin_data)
        raw_output = result.stdout or result.stderr or ""

    # Save raw log
    log_file.write_text(raw_output, encoding="utf-8")

    session_id, result_text, usage = _parse(raw_output)

    # ---- Handle failures ----
    if result.returncode != 0 and not session_id:
        _write_log(readable_log, role, cfg, "", result_text, log_file,
                    failed=True, exit_code=result.returncode)

        # Exit code 143 = SIGTERM (killed externally), typically a rate limit kill.
        # Exit code 137 = SIGKILL (OOM or forced kill).
        is_killed = result.returncode in (137, 143)
        if _is_limit_hit(raw_output) or is_killed:
            reason = "SIGTERM (likely rate limit)" if result.returncode == 143 else \
                     "SIGKILL" if result.returncode == 137 else "usage limit"
            log_err(f"{role} killed ({reason}). State saved — run 'mad resume' to continue later.")
            raise AgentLimitError(f"{role} hit limit ({reason}) — see {log_file}")
        else:
            log_err(f"{role} agent failed (exit code {result.returncode}). Check log: {log_file}")
            raise AgentError(f"{role} agent failed — see {log_file}")

    # ---- Success: accumulate costs ----
    _run_costs.append({
        "role": role,
        "cost_usd": usage.get("cost_usd", 0),
        "duration_ms": usage.get("duration_ms", 0),
        "num_turns": usage.get("num_turns", 0),
        "timestamp": datetime.now().isoformat(),
    })

    _write_log(readable_log, role, cfg, session_id, result_text, log_file)
    log_ok(f"{role} log written to {readable_log}")
    return session_id


def run_agent_structured(
    cfg: RunConfig,
    *,
    role: str,
    prompt: str,
    tools: str,
    model: str = "",
    log_suffix: str = "agent",
    json_schema: str = "",
    cwd: str = "",
) -> tuple[str, dict]:
    """Run a claude -p invocation with --json-schema and return (session_id, parsed_data).

    The parsed_data dict comes from the structured JSON output.
    Falls back to empty dict if parsing fails.
    """
    log_file = cfg.logs_dir / f"{cfg.run_id}_{log_suffix}.json"
    readable_log = cfg.logs_dir / f"{cfg.run_id}_{log_suffix}.md"
    work_dir = cwd or str(cfg.project_dir)

    global _current_role
    model_label = f" (model: {model})" if model else ""
    log_phase(role, f"Starting structured agent...{model_label}")

    _current_role = role
    budget = getattr(cfg, "budget_usd", 0) or 0
    cmd, stdin_data = _build_cmd(prompt, tools, model, resume_session="", json_schema=json_schema, max_budget_usd=budget)
    result = _invoke(cmd, work_dir, stdin_data=stdin_data)
    raw_output = result.stdout or result.stderr or ""

    log_file.write_text(raw_output, encoding="utf-8")

    session_id, result_text, usage = _parse(raw_output)

    if result.returncode != 0 and not session_id:
        _write_log(readable_log, role, cfg, "", result_text, log_file,
                    failed=True, exit_code=result.returncode)
        if _is_limit_hit(raw_output):
            raise AgentLimitError(f"{role} hit usage limit — see {log_file}")
        else:
            raise AgentError(f"{role} agent failed — see {log_file}")

    _run_costs.append({
        "role": role,
        "cost_usd": usage.get("cost_usd", 0),
        "duration_ms": usage.get("duration_ms", 0),
        "num_turns": usage.get("num_turns", 0),
        "timestamp": datetime.now().isoformat(),
    })

    _write_log(readable_log, role, cfg, session_id, result_text, log_file)
    log_ok(f"{role} structured log written to {readable_log}")

    # Parse the structured result
    parsed = {}
    try:
        parsed = json.loads(result_text) if result_text else {}
    except (json.JSONDecodeError, TypeError):
        # result_text might be wrapped in the overall JSON envelope
        try:
            data = json.loads(raw_output)
            result_inner = data.get("result", "")
            parsed = json.loads(result_inner) if result_inner else {}
        except (json.JSONDecodeError, TypeError):
            log_warn(f"{role}: could not parse structured output — falling back to empty dict")

    return session_id, parsed
