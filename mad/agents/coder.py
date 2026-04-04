"""Phase 2: Coder Agent.

Implements all tickets (full mode) or fixes reviewer issues (fix mode).
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime

from mad.config import CODER_TOOLS, RunConfig
from mad.console import banner, log_err, log_info, log_ok, log_warn
from mad.runner import run_agent


def _git_snapshot(cfg: RunConfig, label: str) -> None:
    """Commit all changes for diff-awareness in the review cycle."""
    cwd = str(cfg.project_dir)
    subprocess.run(["git", "add", "-A"], cwd=cwd, capture_output=True)
    result = subprocess.run(
        ["git", "commit", "-m", f"mad: {label}", "--allow-empty"],
        cwd=cwd, capture_output=True,
    )
    if result.returncode == 0:
        log_info(f"Git snapshot: {label}")


def _load_file(path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _find_rules_file(cfg: RunConfig) -> str | None:
    """Return the best-matching rules_*.md for the project idea."""
    matches = list(cfg.rules_dir.glob("rules_*.md"))
    if not matches:
        return None
    if len(matches) == 1:
        return str(matches[0])

    idea_lower = cfg.idea.lower() if cfg.idea else ""
    if idea_lower:
        def _score(path):
            parts = path.stem.replace("rules_", "").split("_")
            return sum(1 for p in parts if p and p in idea_lower)

        scored = [(p, _score(p)) for p in matches]
        best_score = max(s for _, s in scored)
        if best_score > 0:
            best = max((p for p, s in scored if s == best_score), key=lambda p: p.stat().st_mtime)
            return str(best)

    return str(max(matches, key=lambda p: p.stat().st_mtime))


def _build_context(cfg: RunConfig) -> tuple[str, str, str, str]:
    """Return (rules_context, research_context, domain_context, evolution_context)."""
    rules_file = _find_rules_file(cfg)
    rules_context = ""
    if rules_file:
        rules_context = (
            f"\nCODING RULES — you MUST follow these strictly:\n"
            f"File: {rules_file}\n(Read this file before writing any code)\n"
        )

    research_context = ""
    if cfg.research_file.exists():
        research_context = (
            f"\nDOCUMENTATION RESEARCH — consult this for correct APIs, versions, and patterns:\n"
            f"File: {cfg.research_file}\n(Read this file before writing any code. "
            f"Use the documented patterns and versions, not guesses. "
            f"If a '## Corrections' section exists at the bottom, those corrections OVERRIDE "
            f"the original claims above them.)\n"
        )

    domain_context = ""
    if cfg.domain_research_file.exists():
        content = _load_file(cfg.domain_research_file)
        if "Status: SKIPPED" not in content:
            domain_context = (
                f"\nDOMAIN-SPECIFIC RESEARCH — regulatory, compliance, and industry requirements:\n"
                f"File: {cfg.domain_research_file}\n(Read this file. Domain requirements are NOT optional. "
                f"Compliance features must be implemented as specified.)\n"
            )

    evolution_context = ""
    if cfg.evolution_file.exists():
        evolution_context = (
            f"\nLEARNINGS FROM PREVIOUS PROJECTS:\n"
            f"File: {cfg.evolution_file}\n(Read this file to learn from past mistakes.)\n"
        )

    return rules_context, research_context, domain_context, evolution_context


def run_coder(cfg: RunConfig, *, mode: str = "full", state=None) -> None:
    """Run the coder agent in 'full' or 'fix' mode."""

    rules_context, research_context, domain_context, evolution_context = _build_context(cfg)

    if mode == "fix":
        _run_fix(cfg, rules_context, research_context, domain_context, evolution_context)
    else:
        _run_full(cfg, rules_context, research_context, domain_context, evolution_context, state=state)


def _run_fix(cfg: RunConfig, rules_ctx: str, research_ctx: str, domain_ctx: str, evo_ctx: str) -> None:
    banner("CODER — Fix Mode", "Addressing Refinement List")

    if not cfg.refinement_file.exists():
        log_err(f"No refinement list found at {cfg.refinement_file}")
        raise FileNotFoundError(cfg.refinement_file)

    prompt = f"""\
You are the CODER agent in FIX MODE.

PROJECT DIRECTORY: {cfg.project_dir}
ORIGINAL IDEA: {cfg.idea}
TICKETS FILE: {cfg.tickets_file}

{rules_ctx}
{research_ctx}
{domain_ctx}
{evo_ctx}

Read the original tickets at {cfg.tickets_file} for full context on what was supposed to be built.
The REVIEWER agent found issues that need fixing. The refinement list is at:
{cfg.refinement_file}

Read it now, then:

1. Read the documentation research file if it exists — it contains correct APIs, versions, and patterns
2. Fix EVERY item on the refinement list, starting from the top (highest priority first)
3. For each item:
   a. Read the relevant file(s)
   b. Check research.md for the correct API/pattern if the fix involves a framework or library
   c. Implement the fix
   d. Run related tests to verify
4. After ALL fixes are applied, run the full test suite
5. If a fix requires changing multiple files, make all changes before moving to the next item

RULES:
- Do NOT add features not on the list
- Do NOT refactor code that isn't mentioned in the list
- If a fix conflicts with another item, resolve both
- Follow the coding rules strictly
- When fixing issues related to frameworks or libraries, consult research.md for the correct patterns
- After completing all fixes, output a summary of what you changed for each item"""

    ts = datetime.now().strftime("%H%M%S")
    run_agent(
        cfg,
        role="CODER-FIX",
        prompt=prompt,
        tools=CODER_TOOLS,
        model=cfg.coder_model,
        log_suffix=f"coder_fix_{ts}",
    )
    _git_snapshot(cfg, f"fix-{ts}")
    log_ok("Fixes applied")


def _verify_sprint(cfg: RunConfig, ticket_number: int, ticket_title: str) -> tuple[bool, str]:
    """Run a lightweight build/test check after a sprint. Returns (passed, details)."""
    from mad.config import VERIFIER_TOOLS

    prompt = f"""\
You are a BUILD VERIFIER. Check that the project compiles and tests pass after implementing Ticket {ticket_number}.

PROJECT DIRECTORY: {cfg.project_dir}
TICKET JUST IMPLEMENTED: Ticket {ticket_number}: {ticket_title}

YOUR PROCESS:
1. Try to build/compile the project (look for build scripts in package.json, Makefile, Cargo.toml, etc.)
2. Run the test suite — focus on tests related to Ticket {ticket_number}
3. Check that no import errors or obvious runtime crashes exist

Output EXACTLY one of:
- VERIFY: PASS
- VERIFY: FAIL: <brief description of what failed>"""

    log_file = cfg.logs_dir / f"{cfg.run_id}_verifier_T{ticket_number}.json"
    readable_log = cfg.logs_dir / f"{cfg.run_id}_verifier_T{ticket_number}.md"

    try:
        run_agent(
            cfg,
            role=f"VERIFIER-T{ticket_number}",
            prompt=prompt,
            tools=VERIFIER_TOOLS,
            model=cfg.coder_model,
            log_suffix=f"verifier_T{ticket_number}",
        )
    except Exception as e:
        return False, str(e)

    # Parse verifier output from the readable log
    if readable_log.exists():
        content = readable_log.read_text(encoding="utf-8")
        if "VERIFY: PASS" in content:
            return True, ""
        fail_match = re.search(r"VERIFY: FAIL:\s*(.+)", content)
        if fail_match:
            return False, fail_match.group(1).strip()

    # If we can't parse the output, treat as failure — don't silently skip
    return False, "Verifier produced no parseable PASS/FAIL output"


def _run_full(cfg: RunConfig, rules_ctx: str, research_ctx: str, domain_ctx: str, evo_ctx: str, *, state=None) -> None:
    """Implement all tickets via per-ticket sprints with self-verification."""
    from mad.state import RunState
    from mad.tickets import parse_tickets

    banner("CODER — Sprint-Based Implementation", "One ticket at a time with verification")

    if not cfg.tickets_file.exists():
        log_err(f"No tickets file found at {cfg.tickets_file}")
        raise FileNotFoundError(cfg.tickets_file)

    tickets = parse_tickets(cfg.tickets_file)
    if not tickets:
        log_err("No tickets parsed from tickets file")
        raise ValueError("Empty tickets file")

    log_info(f"Parsed {len(tickets)} tickets")

    # Use the pipeline's state object if provided, otherwise load from disk
    if state is None:
        state = RunState.load(cfg.state_file) or RunState()
    completed = set(state.completed_tickets)

    for ticket in tickets:
        if ticket.number in completed:
            log_info(f"Ticket {ticket.number}: {ticket.title} — already completed, skipping")
            continue

        banner(f"Sprint: Ticket {ticket.number}/{len(tickets) - 1}", ticket.title)

        # Build sprint prompt — fresh context per ticket
        sprint_prompt = f"""\
You are the CODER agent implementing Ticket {ticket.number} of {len(tickets) - 1} total.

PROJECT DIRECTORY: {cfg.project_dir}
PROJECT IDEA: {cfg.idea}

{rules_ctx}
{research_ctx}
{domain_ctx}
{evo_ctx}

PREVIOUSLY COMPLETED TICKETS: {sorted(completed) if completed else "None (this is the first ticket)"}
Read existing project files to understand what has already been built.

YOUR TICKET:
<context name="ticket" type="data">
{ticket.content}
</context>

YOUR PROCESS:
1. Read the coding rules and research files referenced above
2. Read any existing project files that this ticket depends on
3. Implement everything specified in this ticket
4. Satisfy ALL acceptance criteria
5. Write the tests specified in the ticket
6. Run the tests for THIS ticket to verify they pass
7. If tests fail, debug and fix before finishing

RULES:
- Implement ONLY this ticket — do not work on other tickets
- Follow the coding rules file strictly
- When the ticket references documentation research, use the EXACT patterns and versions noted there
- Write clean, production-quality code
- Handle errors properly
- Output a brief summary: what you implemented, what tests you ran, any issues encountered"""

        # Sprint execution with retry on verification failure
        max_attempts = 3
        failure_context = ""
        ticket_passed = False

        for attempt in range(1, max_attempts + 1):
            if failure_context:
                sprint_prompt_with_fix = (
                    sprint_prompt + f"\n\nPREVIOUS ATTEMPT FAILED (attempt {attempt - 1}):\n"
                    f"{failure_context}\n\nFix the issues and ensure the ticket passes verification."
                )
            else:
                sprint_prompt_with_fix = sprint_prompt

            run_agent(
                cfg,
                role=f"CODER-T{ticket.number}" + (f"-A{attempt}" if attempt > 1 else ""),
                prompt=sprint_prompt_with_fix,
                tools=CODER_TOOLS,
                model=cfg.coder_model,
                log_suffix=f"coder_sprint_T{ticket.number}" + (f"_A{attempt}" if attempt > 1 else ""),
            )

            # Self-verification
            passed, details = _verify_sprint(cfg, ticket.number, ticket.title)
            if passed:
                log_ok(f"Ticket {ticket.number} verified — PASS")
                ticket_passed = True
                break
            else:
                log_warn(f"Ticket {ticket.number} verification FAILED (attempt {attempt}/{max_attempts}): {details}")
                failure_context = details

        # Git snapshot after each ticket (even failed ones, for diff visibility)
        _git_snapshot(cfg, f"ticket-{ticket.number}")

        if not ticket_passed:
            # Save progress up to this point, then stop
            state.current_ticket = ticket.number
            state.save(cfg)
            from mad.runner import AgentError
            raise AgentError(
                f"Ticket {ticket.number} failed verification after {max_attempts} attempts. "
                f"Last error: {failure_context}\n"
                f"Run 'mad resume' to retry from this ticket."
            )

        # Record progress only on success
        completed.add(ticket.number)
        state.completed_tickets = sorted(completed)
        state.current_ticket = ticket.number
        state.save(cfg)

    log_ok(f"All {len(tickets)} tickets implemented")
