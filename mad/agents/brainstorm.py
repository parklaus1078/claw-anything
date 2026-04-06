"""Brainstorm agent — multi-persona debate before planning.

Runs 3 rounds of structured discussion:
  Round 1: Each persona independently analyzes the idea.
  Round 2: Each persona reads all Round 1 outputs and critiques/synthesizes.
  Round 3: A Facilitator merges all perspectives into a consensus document.

The consensus document feeds into the planner as additional context.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from mad.config import BRAINSTORM_TOOLS, RunConfig
from mad.console import banner, log_info, log_ok, log_warn
from mad.runner import run_agent


@dataclass(frozen=True)
class Persona:
    """A brainstorm participant with a distinct perspective."""

    name: str
    expertise: str
    thinking_style: str
    priorities: str


# Default personas — each brings a different lens to the project idea.
DEFAULT_PERSONAS = [
    Persona(
        name="Architect",
        expertise="System design, scalability, clean separation of concerns",
        thinking_style="Top-down thinker. Starts with high-level structure, then drills into components.",
        priorities="Maintainability, modularity, clear interfaces, scalability patterns",
    ),
    Persona(
        name="Pragmatist",
        expertise="Shipping fast, MVPs, practical trade-offs, developer experience",
        thinking_style="Bottom-up thinker. Focuses on what works NOW and what gets us to a working demo fastest.",
        priorities="Time-to-working-demo, simplicity, minimal dependencies, avoid over-engineering",
    ),
    Persona(
        name="Security Expert",
        expertise="Attack surfaces, authentication, data protection, OWASP Top 10",
        thinking_style="Adversarial thinker. Always asks 'how could this be exploited?'",
        priorities="Input validation, authentication, authorization, secrets management, data privacy",
    ),
    Persona(
        name="UX Advocate",
        expertise="User experience, accessibility, information architecture, error messaging",
        thinking_style="User-centric thinker. Every decision is evaluated from the end-user's perspective.",
        priorities="Intuitive flows, clear error states, accessibility (a11y), responsive design, delight",
    ),
    Persona(
        name="DevOps Engineer",
        expertise="CI/CD, deployment, monitoring, containerization, infrastructure",
        thinking_style="Operational thinker. Considers what happens AFTER the code is written.",
        priorities="Deployability, observability, configuration management, reproducible builds, logging",
    ),
]


def _round1_prompt(persona: Persona, idea: str) -> str:
    """Generate the Round 1 prompt for a persona's independent analysis."""
    return f"""\
You are {persona.name}, a brainstorm participant with the following profile:

EXPERTISE: {persona.expertise}
THINKING STYLE: {persona.thinking_style}
PRIORITIES: {persona.priorities}

PROJECT IDEA: {idea}

YOUR TASK — ROUND 1 (Independent Analysis):
Analyze this project idea from your unique perspective. Write a structured proposal covering:

1. **Key Concerns**: What are the most important considerations from your perspective?
2. **Recommended Approach**: How should this project be built? What tech choices matter most?
3. **Risks & Pitfalls**: What could go wrong if your concerns are ignored?
4. **Must-Have Requirements**: Non-negotiable requirements from your perspective.
5. **Nice-to-Have Suggestions**: Improvements that would elevate the project.

Be specific and opinionated. Disagree with conventional wisdom where your expertise warrants it.
Stay focused on YOUR perspective — other personas will bring theirs.

Write your analysis clearly and concisely."""


def _round2_prompt(persona: Persona, idea: str, round1_files: list[Path]) -> str:
    """Generate the Round 2 prompt for critique and synthesis."""
    files_block = "\n".join(f"  - {f}" for f in round1_files)
    return f"""\
You are {persona.name}, continuing the brainstorm discussion.

EXPERTISE: {persona.expertise}
THINKING STYLE: {persona.thinking_style}
PRIORITIES: {persona.priorities}

PROJECT IDEA: {idea}

ROUND 1 PROPOSALS (read ALL of these files):
{files_block}

YOUR TASK — ROUND 2 (Critique & Synthesis):
You have read all Round 1 proposals from the other personas. Now:

1. **Agreements**: Which proposals align with your perspective? Strengthen those points.
2. **Disagreements**: Where do you disagree with other personas? Explain why from your expertise.
3. **Blind Spots**: What did the other personas miss that you consider critical?
4. **Synthesis**: Propose a unified approach that incorporates the best ideas from all perspectives.
5. **Trade-offs**: Explicitly name the trade-offs in your synthesis and justify your choices.

Be constructive but honest. If a proposal is naive from your perspective, say so and explain why.
Reference specific proposals by persona name."""


def _facilitator_prompt(idea: str, round2_files: list[Path]) -> str:
    """Generate the Round 3 prompt for the facilitator."""
    files_block = "\n".join(f"  - {f}" for f in round2_files)
    return f"""\
You are the FACILITATOR, concluding a multi-persona brainstorm session.

PROJECT IDEA: {idea}

ROUND 2 CRITIQUES & SYNTHESES (read ALL of these files):
{files_block}

YOUR TASK — FINAL CONSENSUS:
Produce a consensus document that the PLANNER agent will use as input for project planning.

Structure your output as:

# Brainstorm Consensus

## Agreed Architecture
Summarize the architectural approach that all (or most) personas converged on.

## Tech Stack Recommendations
List the recommended technologies with rationale from the brainstorm.

## Critical Requirements
Non-negotiable requirements that multiple personas flagged.

## Security Considerations
Security requirements and patterns from the Security Expert's input.

## UX Requirements
User experience requirements from the UX Advocate's input.

## Deployment & Operations
Deployment and operational requirements from the DevOps Engineer's input.

## Unresolved Trade-offs
Trade-offs where personas disagreed — present both sides so the Planner can decide.

## Risk Register
Risks identified across all personas, ranked by severity.

Be concise and actionable. The Planner will use this document to generate tickets."""


def run_brainstorm(cfg: RunConfig, *, personas: list[Persona] | None = None, rounds: int = 3) -> Path:
    """Run a multi-persona brainstorm session.

    Args:
        cfg: Run configuration.
        personas: List of personas to use. Defaults to DEFAULT_PERSONAS.
        rounds: Number of rounds (default 3: independent → critique → consensus).

    Returns:
        Path to the consensus document.
    """
    if personas is None:
        personas = DEFAULT_PERSONAS

    brainstorm_dir = cfg.brainstorm_dir
    brainstorm_dir.mkdir(parents=True, exist_ok=True)

    # ================================================================
    # Round 1: Independent analysis (parallel)
    # ================================================================
    banner("BRAINSTORM — Round 1/3", "Independent persona analyses")

    round1_files: list[Path] = []

    def _run_round1(persona: Persona) -> Path:
        out_file = brainstorm_dir / f"round1_{persona.name.lower().replace(' ', '_')}.md"
        prompt = _round1_prompt(persona, cfg.idea)
        prompt += f"\n\nWrite your analysis to: {out_file}"
        run_agent(
            cfg,
            role=f"BRAINSTORM-R1-{persona.name.upper().replace(' ', '')}",
            prompt=prompt,
            tools=BRAINSTORM_TOOLS,
            model=cfg.planner_model,
            log_suffix=f"brainstorm_r1_{persona.name.lower().replace(' ', '_')}",
            cwd=str(cfg.mad_home),
            timeout_minutes=10,
        )
        return out_file

    with ThreadPoolExecutor(max_workers=len(personas)) as pool:
        futures = {pool.submit(_run_round1, p): p for p in personas}
        for future in as_completed(futures):
            persona = futures[future]
            try:
                out_file = future.result()
                round1_files.append(out_file)
                log_ok(f"Round 1 complete: {persona.name}")
            except Exception as e:
                log_warn(f"Round 1 failed for {persona.name}: {e}")

    if not round1_files:
        log_warn("No Round 1 outputs produced. Skipping brainstorm.")
        return cfg.brainstorm_consensus_file

    # ================================================================
    # Round 2: Critique & synthesis (parallel)
    # ================================================================
    banner("BRAINSTORM — Round 2/3", "Cross-persona critique & synthesis")

    round2_files: list[Path] = []

    def _run_round2(persona: Persona) -> Path:
        out_file = brainstorm_dir / f"round2_{persona.name.lower().replace(' ', '_')}.md"
        prompt = _round2_prompt(persona, cfg.idea, round1_files)
        prompt += f"\n\nWrite your synthesis to: {out_file}"
        run_agent(
            cfg,
            role=f"BRAINSTORM-R2-{persona.name.upper().replace(' ', '')}",
            prompt=prompt,
            tools=BRAINSTORM_TOOLS,
            model=cfg.planner_model,
            log_suffix=f"brainstorm_r2_{persona.name.lower().replace(' ', '_')}",
            cwd=str(cfg.mad_home),
            timeout_minutes=10,
        )
        return out_file

    with ThreadPoolExecutor(max_workers=len(personas)) as pool:
        futures = {pool.submit(_run_round2, p): p for p in personas}
        for future in as_completed(futures):
            persona = futures[future]
            try:
                out_file = future.result()
                round2_files.append(out_file)
                log_ok(f"Round 2 complete: {persona.name}")
            except Exception as e:
                log_warn(f"Round 2 failed for {persona.name}: {e}")

    if not round2_files:
        log_warn("No Round 2 outputs produced. Using Round 1 outputs for consensus.")
        round2_files = round1_files

    # ================================================================
    # Round 3: Facilitator consensus
    # ================================================================
    banner("BRAINSTORM — Round 3/3", "Facilitator consensus")

    consensus_file = cfg.brainstorm_consensus_file
    prompt = _facilitator_prompt(cfg.idea, round2_files)
    prompt += f"\n\nWrite the consensus document to: {consensus_file}"

    run_agent(
        cfg,
        role="BRAINSTORM-FACILITATOR",
        prompt=prompt,
        tools=BRAINSTORM_TOOLS,
        model=cfg.planner_model,
        log_suffix="brainstorm_r3_facilitator",
        cwd=str(cfg.mad_home),
        timeout_minutes=10,
    )

    if consensus_file.exists():
        log_ok(f"Brainstorm consensus written to {consensus_file}")
    else:
        log_warn("Facilitator did not produce a consensus file.")

    return consensus_file
