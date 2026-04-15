"""MAD CLI — Multi-Agent Development System.

Usage:
    mad run      [project_dir] ["<idea>"]   Full pipeline
    mad plan     [project_dir] ["<idea>"]   Plan only
    mad code     [project_dir] ["<idea>"]   Code only
    mad review   [project_dir] ["<idea>"]   Review only
    mad fix      [project_dir] ["<idea>"]   One fix cycle
    mad finalize [project_dir] ["<idea>"]   README + evolution
    mad resume                              Resume from last crash/limit hit
    mad projects                            List all projects
    mad select   <name>                     Set active project
    mad logs                                List recent logs
    mad status                              Show run artifacts

When an active project is selected, project_dir and idea are optional.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.table import Table

from mad import __version__
from mad.config import (
    AVAILABLE_MODELS,
    RunConfig,
    _mad_home,
    get_budget,
    get_default_model,
    get_max_iterations,
    get_pass_score,
    load_settings,
    save_settings,
)
from mad.runner import get_run_costs, reset_run_costs
from mad.console import (
    banner,
    console,
    log_err,
    log_info,
    log_ok,
    log_warn,
    phase_banner,
)
from mad.projects import (
    get_active_project,
    list_projects,
    register_project,
    set_active_project,
    update_project_status,
    _slugify,
)
from mad.runner import AgentError, AgentLimitError
from mad.state import RunState


def _resolve_project_args(project_dir: str | None, idea: str | None) -> tuple[str, str, str]:
    """Resolve project_dir and idea from CLI args or active project.

    Returns (project_dir, idea, project_slug).
    """
    active = get_active_project()

    if project_dir and idea:
        # Both given — register/update project, derive slug from dir name
        name = Path(project_dir).resolve().name
        entry = register_project(name, str(Path(project_dir).resolve()), idea)
        set_active_project(entry["slug"])
        return str(Path(project_dir).resolve()), idea, entry["slug"]

    if active:
        # Fill in missing args from active project
        pd = project_dir or active["project_dir"]
        i = idea or active["idea"]
        return str(Path(pd).resolve()), i, active["slug"]

    if project_dir and not idea:
        log_err("Missing IDEA argument. Provide it or select an active project with 'mad select <name>'.")
        raise SystemExit(1)

    log_err("No project specified and no active project. Run 'mad run <dir> \"<idea>\"' or 'mad select <name>'.")
    raise SystemExit(1)


def _make_cfg(
    project_dir: str,
    idea: str,
    max_iterations: int | None = None,
    planner_model: str = "",
    coder_model: str = "",
    reviewer_model: str = "",
    pass_score: float | None = None,
    project_slug: str = "",
    budget_usd: float | None = None,
) -> RunConfig:
    p = Path(project_dir).resolve()
    cfg = RunConfig(
        project_dir=p,
        idea=idea,
        max_iterations=max_iterations if max_iterations is not None else get_max_iterations(),
        planner_model=planner_model or get_default_model("planner"),
        coder_model=coder_model or get_default_model("coder"),
        reviewer_model=reviewer_model or get_default_model("reviewer"),
        pass_score=pass_score if pass_score is not None else get_pass_score(),
        project_slug=project_slug,
        budget_usd=budget_usd if budget_usd is not None else get_budget(),
    )
    cfg.ensure_dirs()
    return cfg


def _make_cfg_from_state(state: RunState) -> RunConfig:
    # Always use current settings.json — not stale values saved in state.
    cfg = RunConfig(
        project_dir=Path(state.project_dir),
        idea=state.idea,
        max_iterations=state.max_iterations,
        run_id=state.run_id,
        planner_model=get_default_model("planner"),
        coder_model=get_default_model("coder"),
        reviewer_model=get_default_model("reviewer"),
        pass_score=get_pass_score(),
        project_slug=getattr(state, "project_slug", ""),
        budget_usd=get_budget(),
    )
    cfg.ensure_dirs()
    return cfg


# Reusable Click options for model selection.
# Defaults are read from settings.json at runtime (via callback), not at import time.
_models_help = f"Available: {', '.join(AVAILABLE_MODELS)}"


class _SettingsDefault(click.Option):
    """A Click Option that reads its default from settings.json at runtime."""

    def __init__(self, *args, settings_key: str = "", **kwargs):
        self._settings_key = settings_key
        super().__init__(*args, **kwargs)

    def get_default(self, ctx, call: bool = True):
        return get_default_model(self._settings_key)


def _opt_planner_model(fn):
    return click.option(
        "--planner-model", default=None,
        help=f"Model for the planner agent. {_models_help}  [default: from settings]",
        cls=_SettingsDefault, settings_key="planner",
    )(fn)

def _opt_coder_model(fn):
    return click.option(
        "--coder-model", default=None,
        help=f"Model for the coder agent. {_models_help}  [default: from settings]",
        cls=_SettingsDefault, settings_key="coder",
    )(fn)

def _opt_reviewer_model(fn):
    return click.option(
        "--reviewer-model", default=None,
        help=f"Model for the reviewer agent. {_models_help}  [default: from settings]",
        cls=_SettingsDefault, settings_key="reviewer",
    )(fn)

def _opt_model_all(fn):
    return click.option(
        "--model", "model_all", default=None,
        help=f"Set the same model for ALL agents (overrides per-agent options). {_models_help}",
    )(fn)


def _init_git(cfg: RunConfig) -> None:
    git_dir = cfg.project_dir / ".git"
    if not git_dir.exists():
        subprocess.run(["git", "init", "-q"], cwd=str(cfg.project_dir), check=True)
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "mad: initial"],
            cwd=str(cfg.project_dir), capture_output=True,
        )
        log_info(f"Initialized git repo at {cfg.project_dir}")
    # Ensure agent-generated directories are gitignored
    gitignore = cfg.project_dir / ".gitignore"
    mad_entries = ["logs/", "screenshots/"]
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        lines = content.splitlines()
        missing = [e for e in mad_entries if e not in lines]
        if missing:
            with open(gitignore, "a", encoding="utf-8") as f:
                f.write(f"\n# MAD agent artifacts\n" + "\n".join(missing) + "\n")
    else:
        gitignore.write_text("# MAD agent artifacts\n" + "\n".join(mad_entries) + "\n", encoding="utf-8")


def _resolve_models(
    model_all: str | None,
    planner_model: str | None,
    coder_model: str | None,
    reviewer_model: str | None,
) -> tuple[str, str, str]:
    """Resolve final model for each agent: --model > --<role>-model > settings.json > fallback."""
    if model_all:
        return model_all, model_all, model_all
    return (
        planner_model or get_default_model("planner"),
        coder_model or get_default_model("coder"),
        reviewer_model or get_default_model("reviewer"),
    )


def _print_banner(cfg: RunConfig) -> None:
    console.print()
    console.print(
        "[bold magenta]"
        "╔══════════════════════════════════════════════════╗\n"
        "║   Multi-Agent Project Development System         ║\n"
        "╚══════════════════════════════════════════════════╝"
        "[/]"
    )
    console.print(f"  [bold]Project:[/]     {cfg.project_dir}")
    console.print(f"  [bold]Idea:[/]        {cfg.idea}")
    console.print(f"  [bold]Run ID:[/]      {cfg.run_id}")
    console.print(f"  [bold]Max loops:[/]   {cfg.max_iterations}")
    console.print(f"  [bold]Models:[/]      planner={cfg.planner_model}  coder={cfg.coder_model}  reviewer={cfg.reviewer_model}")
    console.print(f"  [bold]Pass score:[/]  {cfg.pass_score}/10")
    console.print(f"  [bold]Started:[/]     {datetime.now()}")
    console.print()


def _print_summary(cfg: RunConfig, approved: bool, iterations: int) -> None:
    status = "[bold green]APPROVED[/]" if approved else "[bold yellow]MAX ITERATIONS REACHED[/]"
    console.print()
    console.print(
        "[bold magenta]"
        "╔══════════════════════════════════════════════════╗\n"
        "║   RUN COMPLETE                                   ║\n"
        "╚══════════════════════════════════════════════════╝"
        "[/]"
    )
    console.print(f"  [bold]Status:[/]        {status}")
    console.print(f"  [bold]Iterations:[/]    {iterations} review cycles")
    console.print(f"  [bold]Finished:[/]      {datetime.now()}")
    console.print()
    console.print("  [bold]Artifacts:[/]")
    console.print(f"    Tickets:       {cfg.tickets_file}")
    console.print(f"    Refinements:   {cfg.refinement_file}")
    console.print(f"    Review logs:   {cfg.specs_dir}/review_iteration_*.md")
    console.print(f"    Agent logs:    {cfg.logs_dir}/{cfg.run_id}_*.md")
    console.print(f"    Coding rules:  {cfg.rules_dir}/")
    console.print(f"    Learnings:     {cfg.evolution_file}")
    console.print(f"    README:        {cfg.project_dir}/README.md")
    console.print()


def _token_usage_file(cfg: RunConfig) -> Path:
    """Path to the cumulative token usage file for the active project."""
    if cfg.project_slug:
        return cfg.mad_home / "projects" / cfg.project_slug / "token_usage.json"
    return cfg.mad_home / "token_usage.json"


def _accumulate_tokens(cfg: RunConfig, input_tokens: int, output_tokens: int) -> None:
    """Append this run's tokens to the project's cumulative usage file."""
    import json as _json
    path = _token_usage_file(cfg)
    existing = {"input_tokens": 0, "output_tokens": 0, "runs": []}
    if path.exists():
        try:
            existing = _json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, TypeError):
            pass
    existing["input_tokens"] = existing.get("input_tokens", 0) + input_tokens
    existing["output_tokens"] = existing.get("output_tokens", 0) + output_tokens
    existing.setdefault("runs", []).append({
        "run_id": cfg.run_id,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "timestamp": datetime.now().isoformat(),
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(existing, indent=2) + "\n", encoding="utf-8")


# Global reference so _print_token_summary can persist without cfg being passed every time.
_active_cfg: RunConfig | None = None


def _print_token_summary() -> None:
    """Print token consumption for the current run and persist to project totals."""
    costs_data = get_run_costs()
    if not costs_data:
        return
    total_in = sum(c.get("input_tokens", 0) for c in costs_data)
    total_out = sum(c.get("output_tokens", 0) for c in costs_data)
    if total_in or total_out:
        console.print(f"\nTOKENS: input - {total_in:,} / output - {total_out:,}")
        if _active_cfg:
            _accumulate_tokens(_active_cfg, total_in, total_out)


def _handle_agent_error(e: AgentLimitError | AgentError, state: RunState, cfg: RunConfig) -> None:
    """Save state and print resume instructions."""
    state.save(cfg)
    console.print()
    if isinstance(e, AgentLimitError):
        console.print("[bold red]Usage limit hit. Your progress has been saved.[/]")
    else:
        console.print(f"[bold red]Agent error: {e}[/]")
    console.print()
    console.print("[bold]To resume when ready:[/]")
    console.print(f"  [cyan]mad resume[/]")
    console.print()
    console.print(f"[dim]State: {state.resume_description}[/]")


# ===========================================================================
# Core pipeline logic (shared between `run` and `resume`)
# ===========================================================================

def _run_pipeline(cfg: RunConfig, state: RunState, *, skip_plan: bool = False, skip_code: bool = False,
                   brainstorm: bool = False, brainstorm_personas=None, brainstorm_rounds: int = 3) -> None:
    """Execute the pipeline from wherever state says we left off."""
    from mad.agents import run_brainstorm, run_coder, run_evolution, run_finalizer, run_planner, run_reviewer
    from mad.summary import PhaseTimer, post_phase_summary

    try:
        # Phase 0 (optional): Brainstorm
        if brainstorm and state.phase not in ("brainstorm", "plan", "code", "review", "fix", "finalize", "evolution"):
            phase_banner(0, "BRAINSTORM", "Multi-persona debate on project approach")
            with PhaseTimer("brainstorm", cfg=cfg) as bs_pt:
                run_brainstorm(cfg, personas=brainstorm_personas, rounds=brainstorm_rounds)
            bs_pt.summary(outcome="Brainstorm consensus generated")
            state.mark(cfg, phase="brainstorm")

        # Phase 1: Plan
        if not skip_plan and state.phase not in ("plan", "code", "review", "fix", "finalize", "evolution"):
            phase_banner(1, "PLANNING", "Analyzing idea -> Coding rules -> Tickets")
            with PhaseTimer("plan_tickets", cfg=cfg) as pt:
                run_planner(cfg)
            if not cfg.tickets_file.exists():
                log_err("Planning failed — no tickets produced. Aborting.")
                raise SystemExit(1)
            log_ok("Planning complete. Tickets ready.")
            pt.summary(outcome="Planning complete — tickets generated")
            state.mark(cfg, phase="plan")

        # Phase 2: Code (initial)
        if not skip_code and state.phase not in ("code", "review", "fix", "finalize", "evolution"):
            phase_banner(2, "CODING", "Implementing all tickets")
            with PhaseTimer("code_full", cfg=cfg) as pt:
                run_coder(cfg, mode="full", state=state)
            pt.summary(outcome="Initial implementation complete")
            state.mark(cfg, phase="code", iteration=0)

        # Phase 3: Review <-> Fix loop
        if state.phase not in ("finalize", "evolution"):
            phase_banner(3, "REVIEW / REFINE LOOP", "E2E testing -> Refinement -> Fix -> Repeat")

            iteration = state.iteration + 1 if state.phase in ("fix", "code") else state.iteration
            if iteration == 0:
                iteration = 1

            # If we crashed mid-review, re-run that review iteration
            # If we crashed mid-fix, re-run that fix
            resume_from_fix = (state.phase == "review" and not state.approved and state.iteration > 0)

            if resume_from_fix:
                log_info(f"Resuming: fix for iteration {state.iteration}, then review {state.iteration + 1}")
                run_coder(cfg, mode="fix")
                state.mark(cfg, phase="fix", iteration=state.iteration)
                iteration = state.iteration + 1

            approved = False
            last_score_data = {}
            while iteration <= cfg.max_iterations:
                log_info(f"Review iteration {iteration} of {cfg.max_iterations}")
                with PhaseTimer("review", cfg=cfg) as review_pt:
                    review_approved, last_score_data = run_reviewer(cfg, iteration=iteration)
                score = last_score_data.get("overall_score")
                review_pt.summary(
                    iteration=iteration,
                    score=score,
                    approved=review_approved,
                    issues_critical=last_score_data.get("critical_count", 0),
                    issues_major=last_score_data.get("major_count", 0),
                )
                if review_approved:
                    approved = True
                    state.mark(cfg, phase="review", iteration=iteration, approved=True)
                    break
                state.mark(cfg, phase="review", iteration=iteration, approved=False)

                if iteration < cfg.max_iterations:
                    log_info("Running coder in fix mode...")
                    with PhaseTimer("code_fix", cfg=cfg) as fix_pt:
                        run_coder(cfg, mode="fix")
                    fix_pt.summary(outcome=f"Fix cycle {iteration} complete")
                    state.mark(cfg, phase="fix", iteration=iteration)
                else:
                    log_warn(f"Max iterations ({cfg.max_iterations}) reached.")
                iteration += 1
            # Save metrics after review loop
            from mad.metrics import RunMetrics, save_metrics
            learnings_count = 0
            if cfg.evolution_file.exists():
                learnings_count = cfg.evolution_file.read_text(encoding="utf-8").count("\n- ")
            save_metrics(cfg.evolution_dir, RunMetrics(
                run_id=cfg.run_id,
                project_slug=cfg.project_slug,
                total_iterations=iteration,
                final_score=last_score_data.get("overall_score"),
                scores=last_score_data.get("scores", {}),
                approved=approved,
                learnings_count=learnings_count,
            ))
        else:
            approved = state.approved
            iteration = state.iteration
            last_score_data = {}

        # Phase 4: Finalize
        if state.phase != "evolution":
            phase_banner(4, "FINALIZE", "README.md + Evolution learnings")
            with PhaseTimer("finalize", cfg=cfg) as fin_pt:
                run_finalizer(cfg)
            fin_pt.summary(outcome="README.md generated")
            state.mark(cfg, phase="finalize")

        with PhaseTimer("evolution", cfg=cfg) as evo_pt:
            run_evolution(cfg, total_iterations=iteration)
        evo_pt.summary(outcome="Learnings captured")
        state.mark(cfg, phase="evolution", finished=True)

        # Save costs
        _print_token_summary()
        _print_summary(cfg, approved, iteration)

    except AgentLimitError as e:
        _print_token_summary()  # save partial costs even on failure
        _handle_agent_error(e, state, cfg)
        raise SystemExit(1)
    except AgentError as e:
        _handle_agent_error(e, state, cfg)
        raise SystemExit(1)
    except KeyboardInterrupt:
        state.save(cfg)
        console.print()
        log_warn("Interrupted. Progress saved — run 'mad resume' to continue.")
        raise SystemExit(130)
    except Exception as e:
        _print_token_summary()
        state.save(cfg)
        console.print()
        log_err(f"Unexpected error: {e}")
        log_warn("Progress saved — run 'mad resume' to continue.")
        raise


# ===========================================================================
# CLI group
# ===========================================================================

@click.group()
@click.version_option(__version__, prog_name="mad")
def cli():
    """MAD — Multi-Agent Development System.

    Plan, code, and review entire projects using Claude Code agents.
    """


# ===========================================================================
# mad init — initialize settings.json with documented template
# ===========================================================================

# The template uses a comment-like pattern: keys ending with "_comment" are
# plain documentation strings that sit next to the real keys.  We strip them
# after the user has seen the file, or they can delete them manually — JSON
# doesn't support comments, so we write a clean file with descriptive values.

_SETTINGS_TEMPLATE: dict = {
    "models": {
        "planner": "sonnet",
        "coder": "sonnet",
        "reviewer": "sonnet",
    },
    "pass_score": 9.0,
    "max_iterations": 10,
    "budget_usd": 0,
    "language": "en",
    "fallback": "",
    "webhooks": {
        "PLANNER": "",
        "CODER": "",
        "REVIEWER": "",
        "VERIFIER": "",
        "FINALIZER": "",
        "SUMMARY": "",
    },
    "discord_bot_token": "",
    "discord_command_channel_id": "",
    "agent_overrides": {},
}

_SETTINGS_GUIDE = """\
# MAD Settings Guide
#
# This file was generated by `mad init`. Edit the values below.
# JSON does not support comments — this guide is printed for reference only.
#
# models.planner / coder / reviewer
#   Model for each agent role.
#   Options: opus, sonnet, haiku, claude-opus-4-6, claude-sonnet-4-6,
#            claude-sonnet-4-5, claude-haiku-4-5-20251001
#
# pass_score          (float, 0-10)  Review score threshold to auto-approve. Default: 9.0
# max_iterations      (int, >=1)     Max review<->fix cycles. Default: 10
# budget_usd          (float)        Per-agent-call budget in USD. 0 = unlimited.
# language            (string)       Bot response language: "en", "ko", or "zh"
# fallback            (string)       Fallback backend. Only "codex" is supported. "" = disabled.
#
# webhooks
#   Discord webhook URLs for live agent streaming and summaries.
#   Each key matches an agent role prefix.
#   SUMMARY posts per-phase summaries to a dedicated channel.
#   Leave empty ("") to disable a webhook.
#
# discord_bot_token           Discord bot token for the command bot (mad bot).
# discord_command_channel_id  Channel ID where the bot listens for !mad commands.
#
# agent_overrides
#   Override agent tools or descriptions without modifying source code.
#   Example:
#     "agent_overrides": {
#       "CODER": { "tools": "Read,Edit,Write,Bash,Grep,Glob,WebSearch" }
#     }
#   Run `mad agents` to see all available agent names.
"""


@cli.command()
@click.option("--force", is_flag=True, default=False, help="Overwrite existing settings.json.")
def init(force: bool):
    """Initialize settings.json with a documented template.

    Creates a settings.json file at MAD_HOME with all available configuration
    keys and their default values, so you know exactly what can be configured.
    """
    settings_path = _mad_home() / "settings.json"

    if settings_path.exists() and not force:
        log_warn(f"settings.json already exists at {settings_path}")
        log_info("Use --force to overwrite, or edit it directly.")
        console.print(f"\n[dim]{settings_path}[/]")
        return

    import json
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    if settings_path.exists() and force:
        # Merge: keep user values, fill in missing keys from template
        existing = load_settings()
        merged = dict(_SETTINGS_TEMPLATE)
        # Deep merge for nested dicts
        for key, value in existing.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value
        content = json.dumps(merged, indent=2) + "\n"
    else:
        content = json.dumps(_SETTINGS_TEMPLATE, indent=2) + "\n"

    settings_path.write_text(content, encoding="utf-8")

    # Write the guide as a companion file
    guide_path = _mad_home() / "settings_guide.txt"
    guide_path.write_text(_SETTINGS_GUIDE, encoding="utf-8")

    log_ok(f"Created {settings_path}")
    log_ok(f"Created {guide_path} (configuration reference)")
    console.print()
    console.print("[bold]Settings template:[/]")
    console.print(content)
    console.print(f"[dim]Edit {settings_path} to configure MAD.[/]")
    console.print(f"[dim]See {guide_path} for field descriptions.[/]")


# ===========================================================================
# mad run — full pipeline
# ===========================================================================

@cli.command()
@click.argument("project_dir", required=False)
@click.argument("idea", required=False)
@click.option("-n", "--max-iterations", default=None, type=int, help="Max coder<->reviewer loops. [default: from settings, fallback 10]")
@click.option("--pass-score", default=None, type=float, help="Score (out of 10) to auto-approve. [default: from settings, fallback 9.0]")
@click.option("--budget", default=None, type=float, help="Per-call budget in USD (0=unlimited). [default: from settings]")
@click.option("--brainstorm", is_flag=True, default=False, help="Run multi-persona brainstorm before planning.")
@click.option("--brainstorm-personas", default=None, type=str,
              help="Comma-separated persona names for brainstorm (e.g., 'architect,pragmatist,qa-strategist'). "
                   "Use 'all' for every persona. Run 'mad personas' to see available names.")
@click.option("--brainstorm-rounds", default=3, type=int, help="Number of brainstorm rounds (min 2). [default: 3]")
@_opt_model_all
@_opt_planner_model
@_opt_coder_model
@_opt_reviewer_model
def run(project_dir: str | None, idea: str | None, max_iterations: int | None, pass_score: float | None,
        budget: float | None, brainstorm: bool, brainstorm_personas: str | None, brainstorm_rounds: int,
        model_all: str | None, planner_model: str, coder_model: str, reviewer_model: str):
    """Run the full pipeline: plan -> code -> review <-> fix -> finalize.

    PROJECT_DIR and IDEA are optional if an active project is selected (mad select <name>).
    Use --brainstorm to run a multi-persona debate before planning.
    """
    from mad.agents.brainstorm import resolve_personas

    pd, i, slug = _resolve_project_args(project_dir, idea)
    pm, cm, rm = _resolve_models(model_all, planner_model, coder_model, reviewer_model)
    cfg = _make_cfg(pd, i, max_iterations, planner_model=pm, coder_model=cm, reviewer_model=rm,
                    pass_score=pass_score, project_slug=slug, budget_usd=budget)
    _init_git(cfg)
    _print_banner(cfg)

    # Resolve brainstorm personas if specified
    persona_names = [n.strip() for n in brainstorm_personas.split(",")] if brainstorm_personas else None
    personas = resolve_personas(persona_names) if brainstorm else None

    reset_run_costs()
    global _active_cfg
    _active_cfg = cfg
    update_project_status(slug, "running")
    state = RunState()
    state.save(cfg)

    _run_pipeline(cfg, state, brainstorm=brainstorm, brainstorm_personas=personas,
                  brainstorm_rounds=brainstorm_rounds)
    update_project_status(slug, "completed" if not state.finished else "completed")


# ===========================================================================
# mad resume — resume from crash/limit
# ===========================================================================

@cli.command()
@click.argument("name", required=False)
def resume(name: str | None):
    """Resume a previously interrupted run (after crash or limit hit).

    Optionally pass a project NAME to resume. Otherwise uses the active project.
    """
    # Determine which project's state to load
    slug = ""
    if name:
        from mad.projects import get_project
        proj = get_project(name)
        if not proj:
            log_err(f"Project '{name}' not found. Run 'mad projects' to list projects.")
            raise SystemExit(1)
        slug = proj["slug"]
    else:
        active = get_active_project()
        if active:
            slug = active["slug"]

    # Build a temporary config to find the state file path
    tmp_cfg = RunConfig(project_dir=Path("."), idea="", project_slug=slug)
    state = RunState.load(tmp_cfg.state_file)

    if state is None:
        log_err("No saved run state found. Nothing to resume.")
        log_info(f"Looked at: {tmp_cfg.state_file}")
        if not slug:
            log_info("Tip: select an active project with 'mad select <name>' or pass a name: 'mad resume <name>'")
        raise SystemExit(1)

    if state.finished:
        log_ok("Previous run already completed. Nothing to resume.")
        return

    cfg = _make_cfg_from_state(state)

    console.print()
    console.print("[bold magenta]Resuming interrupted run[/]")
    console.print(f"  [bold]Project:[/]   {cfg.project_dir}")
    console.print(f"  [bold]Idea:[/]      {cfg.idea}")
    console.print(f"  [bold]Run ID:[/]    {cfg.run_id}")
    console.print(f"  [bold]Status:[/]    {state.resume_description}")
    console.print()

    # Determine what to skip based on actual state
    skip_plan = state.phase in ("plan", "code", "review", "fix", "finalize", "evolution")
    skip_code = state.phase in ("code", "review", "fix", "finalize", "evolution")
    _run_pipeline(cfg, state, skip_plan=skip_plan, skip_code=skip_code)


# ===========================================================================
# mad plan — planning only
# ===========================================================================

@cli.command()
@click.argument("project_dir", required=False)
@click.argument("idea", required=False)
@_opt_model_all
@_opt_planner_model
def plan(project_dir: str | None, idea: str | None, model_all: str | None, planner_model: str):
    """Run only the planner: analyze idea, generate rules and tickets."""
    from mad.agents import run_planner

    pd, i, slug = _resolve_project_args(project_dir, idea)
    pm, _, _ = _resolve_models(model_all, planner_model, None, None)
    cfg = _make_cfg(pd, i, planner_model=pm, project_slug=slug)
    _init_git(cfg)
    _print_banner(cfg)

    state = RunState()
    state.save(cfg)

    phase_banner(1, "PLANNING", "Analyzing idea -> Coding rules -> Tickets")

    try:
        run_planner(cfg)
        state.mark(cfg, phase="plan")
    except (AgentLimitError, AgentError) as e:
        state.save(cfg)
        log_err(str(e))
        raise SystemExit(1)

    if cfg.tickets_file.exists():
        count = cfg.tickets_file.read_text(encoding="utf-8").count("### Ticket")
        log_ok(f"Planning complete. {count} tickets at {cfg.tickets_file}")
    else:
        log_err("Planning failed — no tickets produced.")


# ===========================================================================
# mad code — coding only
# ===========================================================================

@cli.command()
@click.argument("project_dir", required=False)
@click.argument("idea", required=False)
@_opt_model_all
@_opt_coder_model
def code(project_dir: str | None, idea: str | None, model_all: str | None, coder_model: str):
    """Run only the coder: implement all existing tickets."""
    from mad.agents import run_coder

    pd, i, slug = _resolve_project_args(project_dir, idea)
    _, cm, _ = _resolve_models(model_all, None, coder_model, None)
    cfg = _make_cfg(pd, i, coder_model=cm, project_slug=slug)
    _print_banner(cfg)

    if not cfg.tickets_file.exists():
        log_err(f"No tickets found at {cfg.tickets_file}. Run 'mad plan' first.")
        raise SystemExit(1)

    state = RunState.load(cfg.state_file) or RunState()
    state.save(cfg)

    phase_banner(2, "CODING", "Implementing all tickets")

    try:
        run_coder(cfg, mode="full", state=state)
        state.mark(cfg, phase="code", iteration=0)
    except (AgentLimitError, AgentError) as e:
        state.save(cfg)  # preserve ticket progress
        log_err(str(e))
        raise SystemExit(1)


# ===========================================================================
# mad review — review only
# ===========================================================================

@cli.command()
@click.argument("project_dir", required=False)
@click.argument("idea", required=False)
@click.option("-i", "--iterations", default=1, help="Max review↔fix iterations to run.")
@click.option("--pass-score", default=None, type=float, help="Score (out of 10) to auto-approve. [default: from settings, fallback 9.0]")
@_opt_model_all
@_opt_coder_model
@_opt_reviewer_model
def review(project_dir: str | None, idea: str | None, iterations: int, pass_score: float | None,
           model_all: str | None, coder_model: str, reviewer_model: str):
    """Run the review↔fix loop on existing project code.

    With -i 1 (default): runs a single review.
    With -i N: runs up to N iterations of review → fix → review → ... until approved or max reached.
    """
    from mad.agents import run_coder, run_reviewer
    from mad.summary import PhaseTimer

    pd, i, slug = _resolve_project_args(project_dir, idea)
    _, cm, rm = _resolve_models(model_all, None, coder_model, reviewer_model)
    cfg = _make_cfg(pd, i, coder_model=cm, reviewer_model=rm, pass_score=pass_score, project_slug=slug)
    _print_banner(cfg)

    state = RunState.load(cfg.state_file) or RunState()
    state.save(cfg)

    # Find the highest existing review iteration so we continue numbering
    existing = list(cfg.specs_dir.glob("review_iteration_*.md"))
    start_iteration = 1
    if existing:
        import re as _re
        nums = [int(m.group(1)) for f in existing if (m := _re.search(r"review_iteration_(\d+)\.md$", f.name))]
        if nums:
            start_iteration = max(nums) + 1
    end_iteration = start_iteration + iterations

    phase_banner(3, "REVIEW / FIX LOOP", f"Iterations {start_iteration}–{end_iteration - 1} (up to {iterations})")
    reset_run_costs()
    global _active_cfg
    _active_cfg = cfg

    approved = False
    last_score_data = {}
    iteration = start_iteration
    try:
        for iteration in range(start_iteration, end_iteration):
            log_info(f"Review iteration {iteration} (run {iteration - start_iteration + 1} of {iterations})")
            with PhaseTimer("review", cfg=cfg) as review_pt:
                approved, last_score_data = run_reviewer(cfg, iteration=iteration)
            score = last_score_data.get("overall_score")
            review_pt.summary(
                iteration=iteration,
                score=score,
                approved=approved,
                issues_critical=last_score_data.get("critical_count", 0),
                issues_major=last_score_data.get("major_count", 0),
            )
            state.mark(cfg, phase="review", iteration=iteration, approved=approved)

            if approved:
                break

            if iteration < end_iteration - 1:
                log_info(f"Running coder in fix mode (iteration {iteration})...")
                with PhaseTimer("code_fix", cfg=cfg) as fix_pt:
                    run_coder(cfg, mode="fix")
                fix_pt.summary(outcome=f"Fix cycle {iteration} complete")
                state.mark(cfg, phase="fix", iteration=iteration)
            else:
                log_warn(f"Max iterations ({iterations}) reached.")
    except (AgentLimitError, AgentError) as e:
        state.mark(cfg, phase="fix" if state.phase == "review" else "review",
                   iteration=max(0, iteration - 1))
        _print_token_summary()
        log_err(str(e))
        raise SystemExit(1)

    if approved:
        console.print(f"[bold green]Project APPROVED at iteration {iteration}.[/]")
    else:
        console.print(f"[bold yellow]Issues remain after {iterations} iteration(s).[/] See {cfg.refinement_file}")
    _print_token_summary()


# ===========================================================================
# mad fix — one fix cycle
# ===========================================================================

@cli.command()
@click.argument("project_dir", required=False)
@click.argument("idea", required=False)
@_opt_model_all
@_opt_coder_model
def fix(project_dir: str | None, idea: str | None, model_all: str | None, coder_model: str):
    """Run the coder in fix mode to address the current refinement list."""
    from mad.agents import run_coder

    pd, i, slug = _resolve_project_args(project_dir, idea)
    _, cm, _ = _resolve_models(model_all, None, coder_model, None)
    cfg = _make_cfg(pd, i, coder_model=cm, project_slug=slug)
    _print_banner(cfg)

    if not cfg.refinement_file.exists():
        log_err(f"No refinement list at {cfg.refinement_file}. Run 'mad review' first.")
        raise SystemExit(1)

    state = RunState.load(cfg.state_file) or RunState()
    state.save(cfg)

    phase_banner(2, "FIX", "Addressing refinement list")
    reset_run_costs()
    global _active_cfg
    _active_cfg = cfg

    try:
        run_coder(cfg, mode="fix")
        state.mark(cfg, phase="fix", iteration=state.iteration)
    except (AgentLimitError, AgentError) as e:
        state.mark(cfg, phase="review", iteration=state.iteration, approved=False)
        _print_token_summary()
        log_err(str(e))
        raise SystemExit(1)
    _print_token_summary()


# ===========================================================================
# mad finalize — README + evolution only
# ===========================================================================

@cli.command()
@click.argument("project_dir", required=False)
@click.argument("idea", required=False)
@_opt_model_all
@_opt_reviewer_model
def finalize(project_dir: str | None, idea: str | None, model_all: str | None, reviewer_model: str):
    """Write README.md and capture evolution learnings."""
    from mad.agents import run_evolution, run_finalizer

    pd, i, slug = _resolve_project_args(project_dir, idea)
    _, _, rm = _resolve_models(model_all, None, None, reviewer_model)
    cfg = _make_cfg(pd, i, reviewer_model=rm, project_slug=slug)
    _print_banner(cfg)

    state = RunState.load(cfg.state_file) or RunState()
    state.save(cfg)

    phase_banner(4, "FINALIZE", "README.md + Evolution learnings")
    reset_run_costs()
    global _active_cfg
    _active_cfg = cfg

    try:
        run_finalizer(cfg)
        state.mark(cfg, phase="finalize")
        run_evolution(cfg, total_iterations=0)
        state.mark(cfg, phase="evolution", finished=True)
    except (AgentLimitError, AgentError) as e:
        state.save(cfg)
        _print_token_summary()
        log_err(str(e))
        raise SystemExit(1)
    _print_token_summary()


# ===========================================================================
# mad projects — list all projects
# ===========================================================================

@cli.command("projects")
def projects_cmd():
    """List all registered projects."""
    all_projects = list_projects()

    if not all_projects:
        log_info("No projects yet. Run 'mad run <dir> \"<idea>\"' to create one.")
        return

    active = get_active_project()
    active_slug = active["slug"] if active else ""

    table = Table(title="Projects")
    table.add_column("", style="bold yellow", width=2)
    table.add_column("Name", style="bold")
    table.add_column("Directory", style="cyan")
    table.add_column("Status", style="dim")
    table.add_column("Idea", max_width=50)
    table.add_column("Updated", style="dim")

    for p in all_projects:
        marker = "*" if p["slug"] == active_slug else ""
        updated = p.get("updated_at", "")[:10]
        table.add_row(
            marker,
            p["name"],
            p["project_dir"],
            p.get("status", ""),
            p.get("idea", "")[:50],
            updated,
        )

    console.print(table)
    if active_slug:
        console.print(f"\n[dim]* = active project. Run commands without specifying dir/idea.[/]")
    else:
        console.print(f"\n[dim]Select an active project: mad select <name>[/]")


# ===========================================================================
# mad select — set active project
# ===========================================================================

@cli.command()
@click.argument("name")
def select(name: str):
    """Set the active project so you can run commands without specifying dir/idea.

    \b
    Examples:
      mad select todo-app
      mad review            # uses todo-app's dir and idea
      mad fix               # uses todo-app's dir and idea
    """
    project = set_active_project(name)
    if not project:
        log_err(f"Project '{name}' not found.")
        all_projects = list_projects()
        if all_projects:
            log_info("Available projects:")
            for p in all_projects:
                console.print(f"  - {p['name']}")
        else:
            log_info("No projects registered yet. Run 'mad run <dir> \"<idea>\"' to create one.")
        raise SystemExit(1)

    log_ok(f"Active project: [bold]{project['name']}[/]")
    console.print(f"  Directory: {project['project_dir']}")
    console.print(f"  Idea: {project['idea']}")
    console.print(f"\n[dim]You can now run 'mad review', 'mad fix', 'mad resume', etc. without args.[/]")


# ===========================================================================
# mad set-model — persist default model per agent
# ===========================================================================

@cli.command("set-model")
@click.option("--planner", default=None, help=f"Default model for the planner. {_models_help}")
@click.option("--coder", default=None, help=f"Default model for the coder. {_models_help}")
@click.option("--reviewer", default=None, help=f"Default model for the reviewer. {_models_help}")
@click.option("--all", "all_agents", default=None, help=f"Set the same default for all agents. {_models_help}")
@click.option("--pass-score", default=None, type=float, help="Review pass threshold (0-10). Default: 9.0 (90%).")
@click.option("--max-iterations", default=None, type=int, help="Max coder<->reviewer loops. Default: 10.")
def set_model(planner: str | None, coder: str | None, reviewer: str | None,
              all_agents: str | None, pass_score: float | None, max_iterations: int | None):
    """Save default models and settings so you don't have to pass them every time.

    \b
    Examples:
      mad set-model --planner opus
      mad set-model --coder claude-sonnet-4-6
      mad set-model --all opus
      mad set-model --planner opus --coder sonnet --reviewer haiku
      mad set-model --pass-score 8.5
      mad set-model --max-iterations 5
    """
    if not any([planner, coder, reviewer, all_agents, pass_score is not None, max_iterations is not None]):
        log_err("Provide at least one of: --planner, --coder, --reviewer, --all, or --pass-score")
        raise SystemExit(1)

    # Validate model names
    for label, value in [("planner", planner), ("coder", coder), ("reviewer", reviewer), ("all", all_agents)]:
        if value and value not in AVAILABLE_MODELS:
            log_err(f"Unknown model '{value}' for --{label}. {_models_help}")
            raise SystemExit(1)

    # Validate pass score
    if pass_score is not None and not (0.0 <= pass_score <= 10.0):
        log_err("--pass-score must be between 0 and 10.")
        raise SystemExit(1)

    # Validate max iterations
    if max_iterations is not None and max_iterations < 1:
        log_err("--max-iterations must be at least 1.")
        raise SystemExit(1)

    settings = load_settings()
    models = settings.get("models", {})

    if all_agents:
        models["planner"] = all_agents
        models["coder"] = all_agents
        models["reviewer"] = all_agents
    else:
        if planner:
            models["planner"] = planner
        if coder:
            models["coder"] = coder
        if reviewer:
            models["reviewer"] = reviewer

    updates: dict = {"models": models}
    if pass_score is not None:
        updates["pass_score"] = pass_score
    if max_iterations is not None:
        updates["max_iterations"] = max_iterations

    save_settings(updates)

    # Show result
    console.print()
    table = Table(title="Settings Saved")
    table.add_column("Setting", style="bold")
    table.add_column("Value", style="cyan")
    table.add_row("Planner model", models.get("planner", get_default_model("planner")))
    table.add_row("Coder model", models.get("coder", get_default_model("coder")))
    table.add_row("Reviewer model", models.get("reviewer", get_default_model("reviewer")))
    table.add_row("Pass score", f"{get_pass_score()}/10")
    table.add_row("Max iterations", str(get_max_iterations()))
    console.print(table)
    console.print(f"\n[dim]Saved to {_mad_home() / 'settings.json'}[/]")


# ===========================================================================
# mad get-model — show current default models
# ===========================================================================

@cli.command("get-model")
def get_model():
    """Show the current default models and review settings."""
    console.print()
    table = Table(title="Current Settings")
    table.add_column("Setting", style="bold")
    table.add_column("Value", style="cyan")
    table.add_column("Source", style="dim")

    settings = load_settings()
    models = settings.get("models", {})

    for role in ("planner", "coder", "reviewer"):
        model = get_default_model(role)
        source = "settings.json" if role in models else "built-in default"
        table.add_row(f"{role.capitalize()} model", model, source)

    score_source = "settings.json" if "pass_score" in settings else "built-in default (90%)"
    table.add_row("Pass score", f"{get_pass_score()}/10", score_source)

    iter_source = "settings.json" if "max_iterations" in settings else "built-in default"
    table.add_row("Max iterations", str(get_max_iterations()), iter_source)

    console.print(table)
    console.print(f"\n[dim]Settings file: {_mad_home() / 'settings.json'}[/]")
    console.print(f"[dim]Override per-run with: mad run ... --planner-model opus --pass-score 8.5 -n 5[/]")


# ===========================================================================
# mad agents — list and inspect agent definitions
# ===========================================================================

@cli.command()
@click.argument("agent_name", required=False)
def agents(agent_name: str | None):
    """List all MAD agents or show details of a specific one.

    \b
    Examples:
      mad agents              # List all agents
      mad agents CODER        # Show details for the CODER agent
      mad agents reviewer     # Case-insensitive lookup
    """
    from mad.agent_registry import get_agent, list_agents

    if agent_name:
        profile = get_agent(agent_name)
        if not profile:
            log_err(f"Unknown agent: '{agent_name}'. Run 'mad agents' to see all agents.")
            raise SystemExit(1)
        console.print()
        console.print(f"[bold cyan]{profile.name}[/]")
        console.print(f"  [bold]Phase:[/]       {profile.phase}")
        console.print(f"  [bold]Role prefix:[/] {profile.role_prefix}")
        console.print(f"  [bold]Model key:[/]   {profile.default_model_key} ({get_default_model(profile.default_model_key)})")
        console.print(f"  [bold]Tools:[/]       {profile.tools}")
        if profile.prompt_template:
            console.print(f"  [bold]Prompt:[/]      {profile.prompt_template}")
        console.print(f"  [bold]Description:[/]")
        console.print(f"    {profile.description}")
        return

    all_agents = list_agents()
    console.print()
    table = Table(title="MAD Agent Registry")
    table.add_column("Agent", style="bold cyan")
    table.add_column("Phase", style="dim")
    table.add_column("Model Key", style="green")
    table.add_column("Tools")
    table.add_column("Description", style="dim", max_width=50)

    for a in all_agents:
        table.add_row(a.name, a.phase, a.default_model_key, a.tools, a.description)

    console.print(table)
    console.print(f"\n[dim]Run 'mad agents <name>' for details. Override tools via agent_overrides in settings.json.[/]")


# ===========================================================================
# mad personas — list available brainstorm personas
# ===========================================================================

@cli.command()
def personas():
    """List all available brainstorm personas.

    \b
    Use persona names with --brainstorm-personas when running:
      mad run ./dir "idea" --brainstorm --brainstorm-personas architect,qa-strategist
      mad run ./dir "idea" --brainstorm --brainstorm-personas all
    """
    from mad.agents.brainstorm import DEFAULT_PERSONAS, PERSONA_REGISTRY

    default_names = {p.name for p in DEFAULT_PERSONAS}

    table = Table(title="Brainstorm Personas", show_lines=True)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Default", justify="center")
    table.add_column("Expertise", style="dim")
    table.add_column("Priorities")

    for key in sorted(PERSONA_REGISTRY.keys()):
        p = PERSONA_REGISTRY[key]
        is_default = "[green]yes[/]" if p.name in default_names else "no"
        table.add_row(key, is_default, p.expertise, p.priorities)

    console.print(table)
    console.print(f"\n[dim]Total: {len(PERSONA_REGISTRY)} personas ({len(DEFAULT_PERSONAS)} default)[/]")


# ===========================================================================
# mad tokens — show cumulative token usage per project
# ===========================================================================

@cli.command()
@click.argument("project_slug", required=False)
def tokens(project_slug: str | None):
    """Show cumulative token usage for a project.

    \b
    Examples:
      mad tokens               # Active project
      mad tokens my-project    # Specific project
    """
    import json as _json

    slug = project_slug
    if not slug:
        active = get_active_project()
        if not active:
            log_err("No active project. Pass a project slug or run 'mad select' first.")
            raise SystemExit(1)
        slug = active["slug"]

    cfg = RunConfig(project_dir=Path("."), idea="", project_slug=slug)
    path = _token_usage_file(cfg)

    if not path.exists():
        log_info(f"No token usage data for project '{slug}'.")
        return

    data = _json.loads(path.read_text(encoding="utf-8"))
    total_in = data.get("input_tokens", 0)
    total_out = data.get("output_tokens", 0)
    runs = data.get("runs", [])

    table = Table(title=f"Token Usage — {slug}")
    table.add_column("Run", style="dim")
    table.add_column("Input", justify="right", style="green")
    table.add_column("Output", justify="right", style="yellow")
    table.add_column("Total", justify="right", style="bold")
    table.add_column("Timestamp", style="dim")

    for r in runs:
        r_in = r.get("input_tokens", 0)
        r_out = r.get("output_tokens", 0)
        table.add_row(
            r.get("run_id", "?")[:12],
            f"{r_in:,}", f"{r_out:,}", f"{r_in + r_out:,}",
            r.get("timestamp", "")[:19],
        )

    table.add_section()
    table.add_row(
        "[bold]TOTAL[/]",
        f"[bold]{total_in:,}[/]",
        f"[bold]{total_out:,}[/]",
        f"[bold]{total_in + total_out:,}[/]",
        "",
    )
    console.print(table)
    console.print(f"\nTOKENS: input - {total_in:,} / output - {total_out:,}")


# ===========================================================================
# mad logs — list recent logs
# ===========================================================================

@cli.command()
@click.option("-n", "--limit", default=20, help="Number of logs to show.")
def logs(limit: int):
    """List recent agent logs."""
    cfg = RunConfig(project_dir=Path("."), idea="")
    log_dir = cfg.logs_dir

    if not log_dir.exists():
        log_warn("No logs directory found.")
        return

    md_logs = sorted(log_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]

    if not md_logs:
        log_info("No logs found.")
        return

    table = Table(title="Recent Agent Logs")
    table.add_column("File", style="cyan")
    table.add_column("Size", justify="right")
    table.add_column("Modified", style="dim")

    for f in md_logs:
        stat = f.stat()
        size = f"{stat.st_size:,} B"
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        table.add_row(f.name, size, mtime)

    console.print(table)


# ===========================================================================
# mad status — show run artifacts + resume info
# ===========================================================================

@cli.command()
def status():
    """Show the current state of MAD artifacts and resume info for the active project."""
    active = get_active_project()
    slug = active["slug"] if active else ""
    cfg = RunConfig(project_dir=Path("."), idea="", project_slug=slug)

    if active:
        console.print()
        console.print(f"  [bold]Active project:[/] [cyan]{active['name']}[/]")
        console.print(f"  [bold]Directory:[/]      {active['project_dir']}")
        console.print(f"  [bold]Idea:[/]           {active['idea'][:60]}")

    # Show resume state if available
    state = RunState.load(cfg.state_file)
    if state:
        console.print()
        style = "[bold green]" if state.finished else "[bold yellow]"
        console.print(f"  [bold]Last run:[/]    {state.run_id}")
        console.print(f"  [bold]Project:[/]     {state.project_dir}")
        console.print(f"  [bold]Idea:[/]        {state.idea}")
        console.print(f"  [bold]Status:[/]      {style}{state.resume_description}[/]")
        if not state.finished:
            console.print(f"  [bold]Resume:[/]      [cyan]mad resume[/]")
        console.print()

    table = Table(title="MAD Artifacts")
    table.add_column("Artifact", style="bold")
    table.add_column("Status", style="cyan")

    def _check(label: str, path: Path) -> None:
        if path.exists():
            size = f"{path.stat().st_size:,} B"
            table.add_row(label, f"[green]exists[/] ({size})")
        else:
            table.add_row(label, "[dim]not found[/]")

    _check("Tickets", cfg.tickets_file)
    _check("Refinement list", cfg.refinement_file)
    _check("Evolution learnings", cfg.evolution_file)
    _check("General rules", cfg.general_rules_file)

    rules_count = len(list(cfg.rules_dir.glob("rules_*.md"))) if cfg.rules_dir.exists() else 0
    table.add_row("Stack-specific rules", f"[green]{rules_count} file(s)[/]" if rules_count else "[dim]none[/]")

    log_count = len(list(cfg.logs_dir.glob("*.md"))) if cfg.logs_dir.exists() else 0
    table.add_row("Agent logs", f"[green]{log_count} file(s)[/]" if log_count else "[dim]none[/]")

    epoch_count = len(list(cfg.evolution_dir.glob("epoch_*.md"))) if cfg.evolution_dir.exists() else 0
    table.add_row("Completed epochs", f"[green]{epoch_count}[/]" if epoch_count else "[dim]0[/]")

    review_count = len(list(cfg.specs_dir.glob("review_iteration_*.md"))) if cfg.specs_dir.exists() else 0
    table.add_row("Review iterations", f"[green]{review_count}[/]" if review_count else "[dim]0[/]")

    console.print(table)


# ===========================================================================
# mad bot — start Discord command bot
# ===========================================================================

@cli.command()
@click.option("--daemon", is_flag=True, default=False, help="Run the bot in the background.")
def bot(daemon: bool):
    """Start the Discord bot to receive commands and supervise agents remotely.

    \b
    Requires discord.py: pip install discord.py>=2.3
    Configure in settings.json:
      {
        "discord_bot_token": "YOUR_BOT_TOKEN",
        "discord_command_channel_id": "CHANNEL_ID"
      }

    \b
    Pipeline:
      !mad run <dir> "<idea>" [--brainstorm]
      !mad resume / !mad stop

    \b
    Supervision:
      !mad status                  Show project phase and iteration
      !mad review-results          Show scores and refinement list
      !mad tickets                 Show ticket list

    \b
    Directing fixes:
      !mad fix "custom instructions"   Fix with your own feedback
      !mad reject "what's wrong"       Reject + auto-fix
      !mad approve                     Skip to finalization
      !mad rerun-ticket 3              Re-implement a ticket

    \b
    Settings:
      !mad set-language <ko|en|zh>
      !mad help
    """
    from mad.discord_bot import start_bot
    start_bot(daemon=daemon)
