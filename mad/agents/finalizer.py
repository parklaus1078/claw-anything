"""Phase 4: Finalizer & Evolution agents.

Finalizer writes README.md.
Evolution captures cross-project learnings.
"""

from __future__ import annotations

from datetime import datetime

from mad.config import FINALIZER_TOOLS, RunConfig
from mad.console import banner, log_ok
from mad.runner import run_agent


def _load_file(path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def run_finalizer(cfg: RunConfig) -> None:
    """Write the project README.md."""

    banner("FINALIZER", "Writing README.md")

    prompt = f"""\
You are the FINALIZER agent. The project has passed all reviews and is ready for release.

PROJECT DIRECTORY: {cfg.project_dir}
PROJECT IDEA: {cfg.idea}
TICKETS FILE: {cfg.tickets_file}

YOUR TASK: Write a comprehensive README.md at {cfg.project_dir}/README.md

The README must include ALL of the following sections:

# <Project Name>

## Overview
A clear, concise description of what this project does and why it exists.

## Features
Bulleted list of all implemented features (derive from the tickets).

## Tech Stack
List all languages, frameworks, databases, and key libraries used.

## Prerequisites
What the user needs installed before they can run this project.

## Getting Started

### Installation
Step-by-step commands to clone, install dependencies, and set up.

### Environment Variables
A table of ALL required environment variables:
| Variable | Description | Required | Default |
|----------|-------------|----------|---------|

### Running the Project
Commands to start the project in development and production modes.

## Usage
How to use the key features. Include example API calls, CLI commands, or UI walkthrough.

## Project Structure
A tree view of the directory structure with brief descriptions of key directories/files.

## Testing
How to run the test suite. Include:
- Unit tests
- Integration tests
- E2E tests

## API Documentation (if applicable)
List all endpoints with method, path, description, request/response examples.

## Contributing
Basic contribution guidelines.

## License
MIT (unless the project specifies otherwise).

RULES:
- Be accurate — only document what actually exists in the project
- Include real, working commands (verify paths and scripts exist)
- Make it professional and well-formatted
- Read the actual project files to extract accurate information (don't guess)"""

    run_agent(
        cfg,
        role="FINALIZER-README",
        prompt=prompt,
        tools=FINALIZER_TOOLS,
        model=cfg.reviewer_model,
        log_suffix="finalizer_readme",
    )
    log_ok("README.md written")


def run_evolution(cfg: RunConfig, *, total_iterations: int) -> None:
    """Capture learnings from this project run into the evolution system."""

    banner("EVOLUTION", "Capturing Learnings")

    from mad.metrics import compute_trend

    # Gather all review logs
    all_review_logs = ""
    for review_log in sorted(cfg.specs_dir.glob("review_iteration_*.md")):
        all_review_logs += f"\n--- {review_log.name} ---\n{review_log.read_text(encoding='utf-8')}\n"

    tickets = _load_file(cfg.tickets_file) or "Not found"
    existing_learnings = _load_file(cfg.evolution_file) or "No previous learnings yet."
    metrics_trend = compute_trend(cfg.evolution_dir)
    now = datetime.now().isoformat()
    epoch_log = cfg.epoch_log()

    prompt = f"""\
You are the EVOLUTION agent. You analyze completed project runs to extract learnings
that will improve future runs. This is a meta-improvement system.

PROJECT IDEA: {cfg.idea}
PROJECT DIRECTORY: {cfg.project_dir}
TOTAL REVIEW ITERATIONS: {total_iterations}
RUN ID: {cfg.run_id}

REVIEW LOGS FROM THIS RUN:
{all_review_logs}

TICKETS USED:
{tickets}

EXISTING LEARNINGS (from previous epochs):
{existing_learnings}

{metrics_trend}

VALIDATION RULES FOR LEARNINGS:
- If a learning was present for 3+ runs and the relevant criterion has DECLINED, flag it for REMOVAL
- If a learning correlates with improving scores, mark it as VALIDATED
- Include a "## Validated Learnings" section for confirmed-useful learnings
- Include a "## Suspect Learnings" section for learnings that may be hurting quality
- If there aren't enough runs for validation (< 3), skip this section

YOUR TASK:

1. Analyze what went well and what went wrong in this project run
2. Write a detailed epoch log to: {epoch_log}
   Include:
   - Project summary
   - Number of iterations needed and why
   - Common bug patterns found by the reviewer
   - What the planner could have specified better
   - What the coder got wrong repeatedly
   - What the reviewer missed or caught late

3. UPDATE (not replace) the master learnings file at: {cfg.evolution_file}
   This file accumulates knowledge across ALL projects. Structure it as:

   # Multi-Agent System Learnings
   Last updated: {now}
   Total projects completed: <count>

   ## Planner Learnings
   - <what makes tickets better>
   - <common planning mistakes to avoid>

   ## Coder Learnings
   - <common implementation mistakes>
   - <patterns that work well>
   - <framework-specific gotchas discovered>

   ## Reviewer Learnings
   - <what to always check>
   - <commonly missed issues>

   ## Architecture Patterns
   - <project structures that worked>
   - <tech stack combinations that worked well>

   ## Anti-Patterns
   - <things that consistently failed>

RULES:
- Be specific — "write better tickets" is useless. \
"Always specify exact HTTP status codes for error responses in API tickets" is useful.
- Merge with existing learnings, don't overwrite them
- Remove learnings that turned out to be wrong
- Keep the file concise — max 200 lines. Consolidate overlapping learnings.
- Each learning should be actionable by the agent that needs it"""

    run_agent(
        cfg,
        role="EVOLUTION",
        prompt=prompt,
        tools=FINALIZER_TOOLS,
        model=cfg.reviewer_model,  # evolution uses reviewer's model
        log_suffix="evolution",
    )

    log_ok(f"Epoch learnings captured at {epoch_log}")
    if cfg.evolution_file.exists():
        log_ok(f"Master learnings updated at {cfg.evolution_file}")
