"""Core agent runner — invokes claude -p and manages session/logging.

Supports an optional fallback to codex exec when claude -p fails.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from mad.config import CODEX_MODEL_MAP, RunConfig, get_fallback_backend, get_webhook_url, get_webhooks_enabled
from mad.console import console, log_err, log_ok, log_phase, log_warn, _print_lock
from mad.discord import (
    format_claude_event, format_codex_event, format_prompt,
    post_message, post_message_async,
)

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
    "quota exceeded", "overloaded", "529", "too many requests",
    "capacity", "context window", "hit your limit",
]


def _build_cmd(prompt: str, tools: str, model: str, resume_session: str,
               json_schema: str = "", max_budget_usd: float = 0,
               stream: bool = False) -> tuple[list[str], str]:
    """Build the claude CLI command. Returns (cmd, stdin_prompt).

    The prompt is always passed via stdin to avoid OS argument length limits.
    When stream=True, uses stream-json format for live event inspection.
    """
    output_format = "stream-json" if stream else "json"
    cmd = [
        "claude",
        "-p",
        "--allowedTools", tools,
        "--output-format", output_format,
    ]
    if stream:
        cmd.append("--verbose")
    if model:
        cmd += ["--model", model]
    if resume_session:
        cmd += ["--resume", resume_session]
    if json_schema:
        cmd += ["--json-schema", json_schema]
    if max_budget_usd > 0:
        cmd += ["--max-budget-usd", str(max_budget_usd)]
    return cmd, prompt


def _build_codex_cmd(prompt: str, tools: str, model: str,
                     json_schema: str = "", cwd: str = "") -> tuple[list[str], str, str | None]:
    """Build a codex exec command. Returns (cmd, stdin_prompt, schema_tmpfile_path).

    The schema_tmpfile_path is non-None when --output-schema is used; caller must
    clean it up after the process completes.
    """
    codex_model = CODEX_MODEL_MAP.get(model, "gpt-5.4-mini")

    # Determine sandbox level from tool permissions
    has_write = any(t in tools for t in ("Edit", "Write", "Bash"))
    sandbox = "workspace-write" if has_write else "read-only"

    cmd = [
        "codex", "exec",
        "--full-auto",
        "--json",
        "--sandbox", sandbox,
        "-m", codex_model,
    ]
    if cwd:
        cmd += ["-C", cwd]

    schema_tmpfile: str | None = None
    if json_schema:
        # codex --output-schema requires a file path
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp.write(json_schema)
        tmp.close()
        schema_tmpfile = tmp.name
        cmd += ["--output-schema", schema_tmpfile]

    # Prompt goes via stdin (use "-" placeholder)
    cmd.append("-")
    return cmd, prompt, schema_tmpfile


def _parse_codex(raw: str) -> tuple[str, str, dict]:
    """Parse codex JSONL output into (session_id, result_text, usage).

    Codex emits one JSON object per line. We extract:
    - thread_id from thread.started event → session_id
    - text from item.completed events → result_text
    - token counts from turn.completed events → usage
    """
    session_id = ""
    text_parts: list[str] = []
    total_input = 0
    total_output = 0

    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        etype = event.get("type", "")
        if etype == "thread.started":
            session_id = event.get("thread_id", "")
        elif etype == "item.completed":
            item = event.get("item", {})
            if item.get("type") == "agent_message" and item.get("text"):
                text_parts.append(item["text"])
        elif etype == "turn.completed":
            usage_data = event.get("usage", {})
            total_input += usage_data.get("input_tokens", 0)
            total_output += usage_data.get("output_tokens", 0)

    result_text = "\n".join(text_parts)
    usage = {
        "cost_usd": 0,  # codex doesn't report cost directly
        "duration_ms": 0,
        "num_turns": len(text_parts),
        "input_tokens": total_input,
        "output_tokens": total_output,
        "backend": "codex",
    }
    return session_id, result_text, usage


_current_role: str = ""
_live_lock = threading.Lock()
_live_active = False


def _invoke(cmd: list[str], cwd: str, stdin_data: str = "",
            on_line: "callable | None" = None,
            timeout_minutes: int = 0) -> subprocess.CompletedProcess:
    """Run a subprocess with a live spinner showing elapsed time.

    When multiple invocations run in parallel (e.g., planner steps 2+3),
    only the first gets the spinner — others fall back to periodic log messages.

    Stdout/stderr are drained in background threads to prevent pipe deadlocks.

    Args:
        on_line: Optional callback invoked with each stdout line as it arrives.
                 Used for live Discord webhook posting.
        timeout_minutes: Max minutes before the process is killed. 0 = no limit.
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

    def _drain(stream, target: list[str], callback=None):
        for line in stream:
            target.append(line)
            if callback:
                callback(line)

    stdout_thread = threading.Thread(
        target=_drain, args=(proc.stdout, stdout_chunks, on_line), daemon=True,
    )
    stderr_thread = threading.Thread(target=_drain, args=(proc.stderr, stderr_chunks), daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    start = time.monotonic()
    role = _current_role or "agent"
    timeout_secs = timeout_minutes * 60 if timeout_minutes > 0 else 0

    # Decide whether this call gets the spinner or falls back to periodic logs
    use_spinner = False
    with _live_lock:
        if not _live_active:
            _live_active = True
            use_spinner = True

    try:
        if use_spinner:
            _run_with_spinner(proc, role, start, timeout_secs=timeout_secs)
        else:
            _run_with_periodic_log(proc, role, start, timeout_secs=timeout_secs)

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


def _run_with_spinner(proc: subprocess.Popen, role: str, start: float,
                      timeout_secs: int = 0) -> None:
    """Show a live animated spinner while the process runs."""
    spinner = Spinner("dots", text=Text(f" {role} running... 0s", style="dim"))
    live = Live(spinner, console=console, refresh_per_second=4, transient=True)
    live.start()
    try:
        while proc.poll() is None:
            elapsed = int(time.monotonic() - start)
            if timeout_secs and elapsed >= timeout_secs:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                log_warn(f"{role} killed after {elapsed // 60}m timeout")
                return
            mins, secs = divmod(elapsed, 60)
            time_str = f"{mins}m{secs:02d}s" if mins else f"{secs}s"
            spinner.update(text=Text(f" {role} running... {time_str}", style="dim"))
            time.sleep(0.25)
    finally:
        live.stop()


def _run_with_periodic_log(proc: subprocess.Popen, role: str, start: float,
                           timeout_secs: int = 0) -> None:
    """Print periodic status messages when spinner is unavailable (parallel runs)."""
    last_log = 0
    while proc.poll() is None:
        elapsed = int(time.monotonic() - start)
        if timeout_secs and elapsed >= timeout_secs:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            log_warn(f"{role} killed after {elapsed // 60}m timeout")
            return
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


def _parse_stream_json(raw: str) -> tuple[str, str, dict]:
    """Parse Claude stream-json output (one JSON object per line).

    Returns the same (session_id, result_text, usage) tuple as _parse.
    The 'result' event at the end contains the final aggregated data.
    """
    session_id = ""
    result_text = ""
    usage = {}

    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        etype = event.get("type", "")
        if etype == "system":
            session_id = event.get("session_id", session_id)
        elif etype == "result":
            session_id = event.get("session_id", session_id)
            result_text = event.get("result", "")
            usage = {
                "cost_usd": event.get("total_cost_usd", 0) or 0,
                "duration_ms": event.get("duration_ms", 0) or 0,
                "num_turns": event.get("num_turns", 0) or 0,
            }

    return session_id, result_text, usage


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


def _run_codex_fallback(
    cfg: RunConfig,
    *,
    role: str,
    prompt: str,
    tools: str,
    model: str,
    log_suffix: str,
    cwd: str,
    json_schema: str = "",
) -> tuple[str, str, dict]:
    """Run codex exec as a fallback. Returns (session_id, result_text, usage).

    Raises AgentError if codex also fails.
    """
    work_dir = cwd or str(cfg.project_dir)
    log_file = cfg.logs_dir / f"{cfg.run_id}_{log_suffix}_codex.json"
    readable_log = cfg.logs_dir / f"{cfg.run_id}_{log_suffix}_codex.md"

    log_warn(f"{role}: Claude failed — falling back to codex")
    codex_model = CODEX_MODEL_MAP.get(model, "gpt-5.4-mini")
    log_phase(role, f"Starting codex fallback (model: {codex_model})...")

    global _current_role
    _current_role = f"{role}[codex]"

    # Discord webhook for codex fallback
    webhook_url = get_webhook_url(role)
    on_line = None
    if webhook_url:
        post_message_async(webhook_url, format_prompt(role, prompt, codex_model, backend="codex"), role)

        def on_line(line: str, _url=webhook_url, _role=role):
            try:
                event = json.loads(line.strip())
                formatted = format_codex_event(_role, event)
                if formatted:
                    post_message_async(_url, formatted, _role)
            except (json.JSONDecodeError, TypeError):
                pass

    cmd, stdin_data, schema_tmpfile = _build_codex_cmd(
        prompt, tools, model, json_schema=json_schema, cwd=work_dir,
    )
    try:
        result = _invoke(cmd, work_dir, stdin_data=stdin_data, on_line=on_line)
    finally:
        if schema_tmpfile:
            import os
            try:
                os.unlink(schema_tmpfile)
            except OSError:
                pass

    raw_output = result.stdout or result.stderr or ""
    log_file.write_text(raw_output, encoding="utf-8")

    session_id, result_text, usage = _parse_codex(raw_output)

    if result.returncode != 0 and not session_id:
        _write_log(readable_log, role, cfg, "", result_text, log_file,
                    failed=True, exit_code=result.returncode)
        log_err(f"{role} codex fallback also failed (exit code {result.returncode})")
        raise AgentError(f"{role} codex fallback failed — see {log_file}")

    _run_costs.append({
        "role": role,
        "cost_usd": usage.get("cost_usd", 0),
        "duration_ms": usage.get("duration_ms", 0),
        "num_turns": usage.get("num_turns", 0),
        "timestamp": datetime.now().isoformat(),
        "backend": "codex",
    })

    _write_log(readable_log, role, cfg, session_id, result_text, log_file)
    log_ok(f"{role} codex fallback log written to {readable_log}")
    return session_id, result_text, usage


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
    timeout_minutes: int = 0,
) -> str:
    """Run a claude -p invocation and return the session_id.

    Args:
        cwd: Working directory for the claude process. Defaults to cfg.project_dir.
             Use cfg.specs_dir for planner agents that write to specs/.

    If --resume fails because the session expired (common after credit limit
    hits), automatically retries without --resume so the run can continue.

    When a fallback backend is configured (e.g. codex), retries with that
    backend before raising the error.

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

    # ---- Discord webhook setup ----
    webhook_url = get_webhook_url(role)
    use_stream = bool(webhook_url)
    on_line = None

    if webhook_url:
        post_message_async(webhook_url, format_prompt(role, prompt, model, backend="claude"), role)

        def on_line(line: str, _url=webhook_url, _role=role):
            try:
                event = json.loads(line.strip())
                formatted = format_claude_event(_role, event)
                if formatted:
                    post_message_async(_url, formatted, _role)
            except (json.JSONDecodeError, TypeError):
                pass

    cmd, stdin_data = _build_cmd(prompt, tools, model, resume_session, max_budget_usd=budget,
                                  stream=use_stream)
    result = _invoke(cmd, work_dir, stdin_data=stdin_data, on_line=on_line,
                     timeout_minutes=timeout_minutes)
    raw_output = result.stdout or result.stderr or ""

    # ---- Handle expired session: retry without --resume ----
    if result.returncode != 0 and resume_session and _is_session_expired(raw_output):
        log_warn(
            f"Session {resume_session[:12]}... expired (common after credit limits). "
            "Retrying without session resumption."
        )
        cmd, stdin_data = _build_cmd(prompt, tools, model, resume_session="", max_budget_usd=budget,
                                      stream=use_stream)
        result = _invoke(cmd, work_dir, stdin_data=stdin_data, on_line=on_line,
                         timeout_minutes=timeout_minutes)
        raw_output = result.stdout or result.stderr or ""

    # Save raw log
    log_file.write_text(raw_output, encoding="utf-8")

    # Use the appropriate parser based on output format
    if use_stream:
        session_id, result_text, usage = _parse_stream_json(raw_output)
    else:
        session_id, result_text, usage = _parse(raw_output)

    # ---- Handle failures (with optional codex fallback) ----
    fallback = get_fallback_backend()

    if result.returncode != 0 and not session_id:
        _write_log(readable_log, role, cfg, "", result_text, log_file,
                    failed=True, exit_code=result.returncode)

        is_killed = result.returncode in (137, 143)
        is_limit = _is_limit_hit(raw_output) or is_killed

        # Try codex fallback before giving up
        if fallback == "codex":
            try:
                fb_session_id, _, _ = _run_codex_fallback(
                    cfg, role=role, prompt=prompt, tools=tools,
                    model=model, log_suffix=log_suffix, cwd=work_dir,
                )
                return fb_session_id
            except AgentError:
                pass  # fallback also failed — raise the original error

        if is_limit:
            reason = "SIGTERM (likely rate limit)" if result.returncode == 143 else \
                     "SIGKILL" if result.returncode == 137 else "usage limit"
            log_err(f"{role} killed ({reason}). State saved — run 'mad resume' to continue later.")
            raise AgentLimitError(f"{role} hit limit ({reason}) — see {log_file}")
        else:
            log_err(f"{role} agent failed (exit code {result.returncode}). Check log: {log_file}")
            raise AgentError(f"{role} agent failed — see {log_file}")

    # ---- Check for rate limit even on exit code 0 ----
    is_empty_response = usage.get("cost_usd", 0) == 0 and usage.get("num_turns", 0) <= 1
    if is_empty_response and _is_limit_hit(result_text):
        _write_log(readable_log, role, cfg, session_id, result_text, log_file,
                    failed=True, exit_code=result.returncode)

        # Try codex fallback for soft rate limits too
        if fallback == "codex":
            try:
                fb_session_id, _, _ = _run_codex_fallback(
                    cfg, role=role, prompt=prompt, tools=tools,
                    model=model, log_suffix=log_suffix, cwd=work_dir,
                )
                return fb_session_id
            except AgentError:
                pass

        log_err(f"{role} hit usage limit (exit 0 but limit message detected). Run 'mad resume' later.")
        raise AgentLimitError(f"{role} hit usage limit — see {log_file}")

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
    timeout_minutes: int = 0,
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

    # ---- Discord webhook setup ----
    webhook_url = get_webhook_url(role)
    use_stream = bool(webhook_url)
    on_line = None

    if webhook_url:
        post_message_async(webhook_url, format_prompt(role, prompt, model, backend="claude"), role)

        def on_line(line: str, _url=webhook_url, _role=role):
            try:
                event = json.loads(line.strip())
                formatted = format_claude_event(_role, event)
                if formatted:
                    post_message_async(_url, formatted, _role)
            except (json.JSONDecodeError, TypeError):
                pass

    cmd, stdin_data = _build_cmd(prompt, tools, model, resume_session="", json_schema=json_schema,
                                  max_budget_usd=budget, stream=use_stream)
    result = _invoke(cmd, work_dir, stdin_data=stdin_data, on_line=on_line,
                     timeout_minutes=timeout_minutes)
    raw_output = result.stdout or result.stderr or ""

    log_file.write_text(raw_output, encoding="utf-8")

    if use_stream:
        session_id, result_text, usage = _parse_stream_json(raw_output)
    else:
        session_id, result_text, usage = _parse(raw_output)

    if result.returncode != 0 and not session_id:
        _write_log(readable_log, role, cfg, "", result_text, log_file,
                    failed=True, exit_code=result.returncode)

        # Try codex fallback before raising
        fallback = get_fallback_backend()
        if fallback == "codex":
            try:
                fb_session_id, fb_result_text, _ = _run_codex_fallback(
                    cfg, role=role, prompt=prompt, tools=tools,
                    model=model, log_suffix=log_suffix, cwd=work_dir,
                    json_schema=json_schema,
                )
                parsed = {}
                try:
                    parsed = json.loads(fb_result_text) if fb_result_text else {}
                except (json.JSONDecodeError, TypeError):
                    log_warn(f"{role}: could not parse codex structured output — falling back to empty dict")
                return fb_session_id, parsed
            except AgentError:
                pass

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
