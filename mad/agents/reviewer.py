"""Phase 3: Reviewer Agent.

Runs E2E tests, evaluates the implementation, and produces a refinement list
or an APPROVED signal. Always runs in FRESH context (no session resumption).
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime

from mad.config import REVIEWER_TOOLS, RunConfig
from mad.console import banner, log_info, log_ok, log_warn
from mad.runner import run_agent, run_agent_structured


SCORE_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "scores": {
            "type": "object",
            "properties": {
                "ticket_compliance": {"type": "number"},
                "functionality": {"type": "number"},
                "code_quality": {"type": "number"},
                "doc_compliance": {"type": "number"},
                "domain_compliance": {"type": ["number", "null"]},
                "security": {"type": "number"},
                "testing": {"type": "number"},
                "ui_quality": {"type": ["number", "null"]},
                "dx": {"type": "number"},
            },
            "required": ["ticket_compliance", "functionality", "code_quality",
                         "security", "testing", "dx"],
        },
        "overall_score": {"type": "number"},
        "approved": {"type": "boolean"},
        "critical_count": {"type": "integer"},
        "major_count": {"type": "integer"},
        "minor_count": {"type": "integer"},
    },
    "required": ["scores", "overall_score", "approved",
                  "critical_count", "major_count", "minor_count"],
})


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


def _get_diff_since_last_review(cfg: RunConfig) -> str:
    """Get git diff from the coder's last fix commit."""
    cwd = str(cfg.project_dir)
    # Check if we have at least 2 commits
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=cwd, capture_output=True, text=True,
    )
    try:
        commit_count = int(result.stdout.strip())
    except (ValueError, AttributeError):
        return ""
    if commit_count < 2:
        return ""

    # Get stat summary
    stat_result = subprocess.run(
        ["git", "diff", "HEAD~1", "HEAD", "--stat", "--no-color"],
        cwd=cwd, capture_output=True, text=True,
    )
    # Get actual diff
    diff_result = subprocess.run(
        ["git", "diff", "HEAD~1", "HEAD", "--no-color"],
        cwd=cwd, capture_output=True, text=True,
    )
    full_diff = diff_result.stdout or ""
    if len(full_diff) > 10000:
        full_diff = full_diff[:10000] + "\n... (diff truncated — read individual files for full details)"

    return (
        f"## Changes Since Last Review\n\n"
        f"### Summary\n```\n{stat_result.stdout}\n```\n\n"
        f"### Diff\n```diff\n{full_diff}\n```"
    )


def _parse_score(content: str) -> float | None:
    """Extract the overall score from review output.

    Looks for patterns like:
        SCORE: 8.5/10
        Score: 7/10
        ## Score: 9/10
        **Overall Score**: 8/10
    """
    patterns = [
        r"(?:SCORE|Score|overall\s*score)[:\s]*(\d+(?:\.\d+)?)\s*/\s*10",
        r"##\s*Score[:\s]*(\d+(?:\.\d+)?)\s*/\s*10",
        r"\*\*(?:Overall\s*)?Score\*\*[:\s]*(\d+(?:\.\d+)?)\s*/\s*10",
    ]
    for pattern in patterns:
        m = re.search(pattern, content, re.IGNORECASE)
        if m:
            return float(m.group(1))
    return None


def run_reviewer(cfg: RunConfig, *, iteration: int) -> tuple[bool, dict]:
    """Run the reviewer.  Returns (approved, score_data)."""

    banner(f"REVIEWER — Iteration {iteration}", "E2E Testing & Evaluation")
    log_info(f"Pass threshold: {cfg.pass_score}/10")

    evolution_block = ""
    if cfg.evolution_file.exists():
        evolution_block = (
            f"\nLEARNINGS FROM PREVIOUS PROJECTS:\n"
            f"File: {cfg.evolution_file}\n(Read this file to catch recurring issues.)\n"
        )

    rules_file = _find_rules_file(cfg)
    rules_block = ""
    if rules_file:
        rules_block = (
            f"\nCODING RULES the coder was supposed to follow:\n"
            f"File: {rules_file}\n(Read this to verify compliance)\n"
        )

    research_block = ""
    if cfg.research_file.exists():
        research_block = (
            f"\nDOCUMENTATION RESEARCH — verified API patterns and versions the coder should have used:\n"
            f"File: {cfg.research_file}\n(Read this to verify the coder used correct APIs and versions)\n"
        )

    domain_block = ""
    if cfg.domain_research_file.exists():
        content = _load_file(cfg.domain_research_file)
        if "Status: SKIPPED" not in content:
            domain_block = (
                f"\nDOMAIN-SPECIFIC RESEARCH — regulatory and compliance requirements:\n"
                f"File: {cfg.domain_research_file}\n(Read this to verify compliance. "
                f"Non-compliance with domain requirements is a CRITICAL issue.)\n"
            )

    prev_list_block = ""
    if iteration > 1 and cfg.refinement_file.exists():
        prev_list_block = (
            f"\nPREVIOUS REFINEMENT LIST (verify these were actually fixed):\n"
            f"File: {cfg.refinement_file}\n(Read this file to check what was supposed to be fixed.)\n"
        )

    diff_block = ""
    if iteration > 1:
        diff = _get_diff_since_last_review(cfg)
        if diff:
            diff_block = (
                f"\n{diff}\n\n"
                "IMPORTANT: Focus your verification on the CHANGED files listed above. "
                "For unchanged files, you may reference your previous assessment unless "
                "you have reason to re-evaluate.\n"
            )

    now = datetime.now().isoformat()
    review_log = cfg.review_log(iteration)

    prompt = f"""\
You are the REVIEWER agent. You evaluate project implementations with ZERO prior bias.
This is iteration {iteration} of the review cycle.

PROJECT DIRECTORY: {cfg.project_dir}
PROJECT IDEA: {cfg.idea}
TICKETS FILE: {cfg.tickets_file}

{rules_block}
{research_block}
{domain_block}
{evolution_block}
{prev_list_block}
{diff_block}

YOUR PROCESS:

1. READ the tickets file to understand what should have been built
2. READ the coding rules to understand quality expectations
3. READ the documentation research file ({cfg.research_file}) if it exists —
   it contains the correct APIs, versions, and patterns the coder was supposed to use.
   Verify the coder actually used them.
4. EXPLORE the project structure:
   - Check all files created
   - Verify directory structure matches conventions
   - Check .gitignore, .env.example exist
5. BUILD & TEST:
   - Install dependencies
   - Build/compile the project (npm run build, cargo build, go build, etc.)
   - Run the full test suite and record pass/fail results
   - Start the server/app and verify it launches without errors
   - For API projects: use curl/wget via Bash to test key endpoints against a running instance
6. STATIC CODE REVIEW:
   - Read every source file and check for bugs, anti-patterns, missing error handling
   - Verify each ticket's acceptance criteria against the actual implementation
   - Check code paths for logic errors, missing edge cases, incorrect API usage

NOTE: You CANNOT perform browser-based visual testing. Score UI quality based on
code review of components/templates/styles, not visual inspection. Be honest about
what you tested versus what you could only review statically.
7. EVALUATE against these criteria (each scored 0-10):
   a. **Ticket compliance**: Was every ticket fully implemented? Check each acceptance criterion.
   b. **Functionality**: Does the project actually work? Can it start, serve requests, render pages?
   c. **Code quality**: Does it follow the coding rules? Clean structure? Proper error handling?
   d. **Doc compliance**: Did the coder use the correct APIs, patterns, and versions documented in research.md?
      Check for outdated patterns, wrong API usage, or version mismatches.
   e. **Domain compliance** (if domain_research.md exists and is not SKIPPED):
      Are all regulatory requirements implemented? Data encryption, access controls, audit logging,
      required workflows, mandatory validations? Non-compliance is ALWAYS a CRITICAL issue.
   f. **Security**: Hardcoded secrets? Input validation? OWASP top 10 risks?
   g. **Testing**: Are tests present, passing, and covering critical paths?
   h. **UI quality** (if applicable): Is the UI unique/artistic yet usable? Or is it generic/broken?
   i. **DX**: Can a new developer clone, install, configure, and run this project easily?

SCORING — You MUST include this exact format in BOTH the refinement file and the review log:

## Scores
- Ticket compliance: X/10
- Functionality: X/10
- Code quality: X/10
- Doc compliance: X/10
- Domain compliance: X/10 (or N/A if not domain-specific)
- Security: X/10
- Testing: X/10
- UI quality: X/10
- DX: X/10

SCORE: X/10

Where the final SCORE line is the weighted overall score (average of all applicable criteria).
This score determines whether the project passes. The current pass threshold is {cfg.pass_score}/10.

AFTER EVALUATION, you must produce ONE of two outcomes:

OUTCOME A — Issues found OR score below {cfg.pass_score}/10 → Write a refinement list to: {cfg.refinement_file}
Format:
---
# Refinement List — Iteration {iteration}
Date: {now}

## Scores
(include all scores as above)

SCORE: X/10

## Critical (must fix)
1. [BUG] <description> — File: <path>, Line: ~<number>
2. [MISSING] <description> — Expected by Ticket N

## Major (should fix)
3. [QUALITY] <description> — File: <path>
4. [SECURITY] <description>

## Minor (nice to fix)
5. [IMPROVE] <description>
---

OUTCOME B — No critical/major issues AND score >= {cfg.pass_score}/10 → Write to {cfg.refinement_file}:
---
# Refinement List — Iteration {iteration}
Date: {now}

## Scores
(include all scores as above)

SCORE: X/10

## Status: APPROVED

No remaining issues. The project is ready for finalization.
---

ALSO write a detailed review log to: {review_log}
This log should include:
- What you tested and how
- Test output (pass/fail)
- Specific observations per ticket
- All scores with justification for each
- The final SCORE: X/10 line

TOOL RESTRICTIONS:
- Do NOT use Write to modify any files inside {cfg.project_dir}
- You may ONLY write to: {cfg.refinement_file} and {review_log}
- Use Bash ONLY for: build commands, test commands, and curl/wget for API testing
- Do NOT use Bash to modify project files (no sed, no tee, no redirects into project paths)

RULES:
- Be THOROUGH — a lazy review that misses bugs is worse than no review
- Be SPECIFIC — "code quality could be better" is useless. \
"UserService.create() doesn't validate email format before DB insert (line ~45)" is useful
- Be FAIR — don't flag subjective style preferences if the coding rules don't specify them
- If this is iteration > 1, VERIFY that previously listed items were actually fixed. Re-list any that weren't.
- The project must actually run. "It looks correct" is not sufficient — try to build and start it.
- You MUST include the SCORE: X/10 line — the system parses it to decide pass/fail."""

    # INTENTIONALLY no resume_session: fresh context for unbiased review
    run_agent(
        cfg,
        role=f"REVIEWER-I{iteration}",
        prompt=prompt,
        tools=REVIEWER_TOOLS,
        model=cfg.reviewer_model,
        log_suffix=f"reviewer_iteration_{iteration}",
    )

    # ---- Extract structured scores ----
    score = None
    score_data = {}

    try:
        score_prompt = f"""\
Read the review log at {review_log} and the refinement list at {cfg.refinement_file}.
Extract all scores and issue counts into the required JSON format.
The overall_score should be the average of all applicable numeric scores (skip null values).
Set approved to true if overall_score >= {cfg.pass_score} and critical_count == 0."""

        _, score_data = run_agent_structured(
            cfg,
            role=f"SCORER-I{iteration}",
            prompt=score_prompt,
            tools="Read,Grep,Glob",
            model=cfg.reviewer_model,
            log_suffix=f"scorer_iteration_{iteration}",
            json_schema=SCORE_SCHEMA,
        )
        score = score_data.get("overall_score")
    except Exception as e:
        log_warn(f"Structured scoring failed ({e}) — falling back to regex")

    # Fallback: regex-based score parsing
    if score is None:
        if cfg.refinement_file.exists():
            score = _parse_score(cfg.refinement_file.read_text(encoding="utf-8"))
        if score is None and review_log.exists():
            score = _parse_score(review_log.read_text(encoding="utf-8"))

    # Check for explicit APPROVED marker as last resort
    explicitly_approved = False
    if cfg.refinement_file.exists():
        content = cfg.refinement_file.read_text(encoding="utf-8")
        explicitly_approved = bool(re.search(r"Status:\s*APPROVED", content, re.IGNORECASE))

    # Decision logic
    if score is not None:
        critical = score_data.get("critical_count", 0)
        major = score_data.get("major_count", 0)
        log_info(f"Review score: {score}/10 (pass threshold: {cfg.pass_score}/10, "
                 f"critical: {critical}, major: {major})")
        if score >= cfg.pass_score and critical == 0:
            log_ok(f"Score {score}/10 meets threshold — APPROVED (iteration {iteration})")
            return True, score_data
        else:
            reason = f"score {score}/10 below threshold" if score < cfg.pass_score else f"{critical} critical issues"
            log_warn(f"{reason} (iteration {iteration})")
            return False, score_data

    if explicitly_approved:
        log_ok(f"Reviewer APPROVED the project (iteration {iteration}) — no score parsed")
        return True, score_data

    if cfg.refinement_file.exists():
        content = cfg.refinement_file.read_text(encoding="utf-8")
        issue_count = len(re.findall(r"^\d+\.", content, re.MULTILINE))
        log_warn(f"Reviewer found {issue_count} issues, no score parsed (iteration {iteration})")
    else:
        log_warn("No refinement file produced — treating as needs-review")

    return False, score_data
