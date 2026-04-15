"""Phase 1: Planner Agent.

Four steps:
  Step 1: Tech stack analysis & coding rules generation
  Step 2: Domain research
  Step 3: Tech doc research
  Step 3.5: Research spot-check
  Step 4: Ticket generation (referencing both research files)
"""

from __future__ import annotations

from mad.config import PLANNER_TOOLS, RunConfig
from mad.console import banner, log_info, log_ok, log_warn
from mad.runner import run_agent
from mad.summary import post_log_summary


MAX_STEP_RETRIES = 2


def _load_file(path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _find_rules_file(cfg: RunConfig, idea: str = "") -> str | None:
    """Return the best-matching rules_*.md for the project idea.

    Strategy: score each file by how many of its name parts appear in the
    idea text (case-insensitive).  Falls back to most-recently-modified if
    no keyword overlap is found.
    """
    matches = list(cfg.rules_dir.glob("rules_*.md"))
    if not matches:
        return None
    if len(matches) == 1:
        return str(matches[0])

    if idea:
        idea_lower = idea.lower()

        def _score(path):
            # Extract keywords from filename: rules_python_fastapi.md -> ["python", "fastapi"]
            stem = path.stem  # e.g. "rules_python_fastapi"
            parts = stem.replace("rules_", "").split("_")
            return sum(1 for p in parts if p and p in idea_lower)

        scored = [(p, _score(p)) for p in matches]
        best_score = max(s for _, s in scored)
        if best_score > 0:
            # Return the highest-scoring match (tie-break by newest)
            best = max((p for p, s in scored if s == best_score), key=lambda p: p.stat().st_mtime)
            return str(best)

    # No idea or no keyword match — return most recently modified
    return str(max(matches, key=lambda p: p.stat().st_mtime))


def _run_with_retry(
    cfg: RunConfig,
    *,
    step_fn,
    expected_file,
    step_name: str,
    critical: bool = False,
    step_timeout_minutes: int = 0,
) -> bool:
    """Run a planner step, retrying if the expected output file is not written.

    Returns True if the file was produced, False otherwise.
    Raises RuntimeError if critical=True and all retries fail.
    """
    for attempt in range(1, MAX_STEP_RETRIES + 2):  # 1 initial + MAX_STEP_RETRIES retries
        try:
            step_fn()
        except Exception as e:
            log_warn(f"{step_name} attempt {attempt} raised: {e}")

        if expected_file.exists() and expected_file.stat().st_size > 0:
            return True

        if attempt <= MAX_STEP_RETRIES:
            log_warn(f"{step_name}: output file not written (attempt {attempt}/{MAX_STEP_RETRIES + 1}). Retrying...")
        else:
            if critical:
                from mad.runner import AgentError
                raise AgentError(
                    f"{step_name} failed after {MAX_STEP_RETRIES + 1} attempts — "
                    f"expected file not written: {expected_file}"
                )
            else:
                log_warn(f"{step_name}: output file not written after {MAX_STEP_RETRIES + 1} attempts. Proceeding without it.")
                return False
    return False


def run_planner(cfg: RunConfig) -> None:
    """Run the four-step planner: rules, domain research, doc research, tickets."""

    evolution_block = ""
    if cfg.evolution_file.exists():
        evolution_block = (
            f"\nLEARNINGS FROM PREVIOUS PROJECTS:\n"
            f"File: {cfg.evolution_file}\n(Read this file to learn from past project mistakes and successes.)\n"
        )

    # ==================================================================
    # Step 1: Tech stack & coding rules
    # ==================================================================
    banner("PLANNER — Step 1/4", "Tech Stack Analysis & Coding Rules")

    general_rules = _load_file(cfg.general_rules_file)

    brainstorm_step1_ctx = ""
    if cfg.brainstorm_consensus_file.exists():
        brainstorm_step1_ctx = (
            f"\nBRAINSTORM CONSENSUS (read this before choosing the tech stack):\n"
            f"File: {cfg.brainstorm_consensus_file}\n"
            f"(This file contains architecture decisions and tech recommendations from a multi-persona brainstorm session. "
            f"Strongly consider the recommendations there when selecting your tech stack.)\n"
        )

    rules_prompt = f"""\
You are the PLANNER agent (Step 1/4: Tech Stack & Coding Rules).

PROJECT IDEA: {cfg.idea}
PROJECT DIRECTORY: {cfg.project_dir}

{evolution_block}

{brainstorm_step1_ctx}

YOUR TASK:
1. Analyze the project idea and determine the best tech stack (language, framework, database, etc.)
2. Always select the latest stable version of the tech stacks, and if the latest version is not stable, or there's any report about the compatibility between the stacks with the selected versions, select the compatible versions of the stacks.
3. Check if a coding rules file already exists in {cfg.rules_dir}/ for the chosen language/framework
   - Look for files named like: rules_<language>.md, rules_<framework>.md
4. If NO specific rules file exists for the chosen stack, CREATE one at:
   {cfg.rules_dir}/rules_<language>_<framework>.md

The rules file must be based on these general coding principles (originally in Korean, work in English):

{general_rules}

The language/framework-specific rules file must include:
- Project structure conventions (directory layout, file naming)
- Framework-specific patterns and anti-patterns
- Recommended libraries and why
- Configuration best practices
- Testing framework and patterns specific to the stack
- Build and deployment conventions
- Security considerations specific to the framework
- Performance patterns specific to the stack

Write ONLY the rules file in this step. End your response with a line:
TECH_STACK: <language> + <framework> + <other tools>
RULES_FILE: <path to the rules file you created or found>"""

    # All planner steps use mad_home as cwd so file writes go to the correct
    # absolute paths (rules/, projects/<slug>/specs/) instead of being relative
    # to the project directory.
    planner_cwd = str(cfg.mad_home)

    planner_session = run_agent(
        cfg,
        role="PLANNER-RULES",
        prompt=rules_prompt,
        tools=PLANNER_TOOLS,
        model=cfg.planner_model,
        log_suffix="planner_step1_rules",
        cwd=planner_cwd,
        timeout_minutes=15,
    )

    rules_file = _find_rules_file(cfg, idea=cfg.idea)
    log_info(f"Rules file: {rules_file or 'none found'}")
    post_log_summary(cfg, "plan_rules")

    # ==================================================================
    # Steps 2+3: Domain research + Tech research (parallel)
    # ==================================================================
    banner("PLANNER — Steps 2+3", "Domain Research + Tech Documentation")

    domain_prompt = f"""\
You are the PLANNER agent (Step 2/4: Domain Research).

PROJECT IDEA: {cfg.idea}
PROJECT DIRECTORY: {cfg.project_dir}

YOUR TASK:
Analyze the project idea and determine if it operates in a DOMAIN-SPECIFIC context
that requires specialized knowledge beyond general software engineering.

A project is domain-specific if it involves ANY of the following:
- **Regulated industries**: healthcare/medical (EMR, EHR, HIPAA, PIPA), finance (banking, trading, PCI-DSS),
  legal, insurance, government, education
- **Regional compliance**: country-specific laws, data residency, localization requirements
  (e.g., Korean PIPA, EU GDPR, US HIPAA, Japanese APPI)
- **Industry standards**: HL7/FHIR for healthcare, FIX protocol for finance, SCORM for education,
  ISO standards, domain-specific certifications
- **Professional workflows**: medical diagnosis flows, legal case management, accounting standards,
  supply chain logistics, manufacturing processes
- **Specialized APIs/integrations**: government APIs, medical coding systems (ICD-10, CPT),
  financial market data feeds, geospatial systems, platform-specific APIs/SDKs/Packages/Libraries, etc.
- **Safety-critical systems**: anything where incorrect behavior could harm people, finances, or legal standing

IF THE PROJECT IS NOT DOMAIN-SPECIFIC:
Write to {cfg.domain_research_file}:
---
# Domain Research

## Assessment
This project does not require domain-specific research.
The idea is a general-purpose software project with no regulated industry,
regional compliance, or specialized domain knowledge requirements.

## Status: SKIPPED
---

IF THE PROJECT IS DOMAIN-SPECIFIC:
Use WebSearch and WebFetch to thoroughly research the domain. Write to {cfg.domain_research_file}:

---
# Domain Research

## Project: <name>
## Domain: <identified domain(s)>
## Date: <today>

## Assessment
<1-2 paragraph explanation of why this project is domain-specific and what areas need research>

---

## 1. Regulatory & Legal Requirements

### <Regulation 1> (e.g., Korean Personal Information Protection Act / PIPA)
- **Official source**: <URL to the law/regulation text or authoritative summary>
- **Applicability**: <why this applies to the project>
- **Key requirements**:
  - <specific requirement 1 and how it affects the software>
  - <specific requirement 2>
- **Penalties for non-compliance**: <if documented>
- **Source reliability**: government source | legal authority | verified industry guide

### <Regulation 2>
(same format)

---

## 2. Industry Standards & Protocols

### <Standard 1> (e.g., HL7 FHIR R4 for healthcare interoperability)
- **Official source**: <URL>
- **Version**: <current version>
- **Key concepts for this project**:
  - <concept 1: what it is, how it applies>
  - <concept 2>
- **Implementation notes**:
  - <how this standard affects the software architecture>
  - <required data formats, APIs, or protocols>
- **Certification requirements**: <if any>

---

## 3. Authentication & Authorization Requirements

### Domain-Specific Auth Policies
- **Who needs access**: <roles, e.g., doctors, nurses, admins, patients>
- **Authorization levels**: <what each role can see/do>
- **Regulatory auth requirements**:
  - <e.g., multi-factor auth required for medical records access>
  - <e.g., audit logging for every data access>
- **Session management requirements**: <timeout policies, concurrent session rules>
- **Identity verification**: <e.g., medical license verification, KYC for finance>

---

## 4. Data Security & Privacy

### Data Classification
- **Sensitive data types**: <e.g., PHI, PII, financial records>
- **Encryption requirements**: <at rest, in transit, specific algorithms>
- **Data retention policies**: <how long, when to delete>
- **Data residency**: <where data must be stored geographically>
- **Access audit requirements**: <what must be logged>

### Breach Response
- **Notification requirements**: <who to notify, within what timeframe>
- **Reporting obligations**: <regulatory bodies to report to>

---

## 5. Domain-Specific Workflows & Business Logic

### <Workflow 1> (e.g., Patient Registration Flow in Korean EMR)
- **Steps**: <ordered list of steps in the workflow>
- **Validation rules**: <domain-specific validation, e.g., Korean resident registration number format>
- **Integration points**: <external systems that must be connected>
- **Edge cases**: <domain-specific edge cases>

### <Workflow 2>
(same format)

---

## 6. Third-Party Systems & Integrations

### <System 1> (e.g., Korean HIRA claims system)
- **Official docs**: <URL>
- **Purpose**: <what it does>
- **Integration method**: <API, file transfer, etc.>
- **Authentication**: <how to connect>
- **Data format**: <expected formats>

---

## 7. Terminology & Glossary

| Term | Definition | Relevance |
|------|-----------|-----------|
| <domain term> | <definition> | <how it's used in this project> |

---

## Research Summary
- Domain complexity: LOW | MEDIUM | HIGH | VERY HIGH
- Regulations identified: <count>
- Standards identified: <count>
- Integration points: <count>
- Key risks: <top 3 risks if domain requirements are not met>
- Recommendation: <brief note on what the IDEA provider should validate>

---

RULES:
- Use WebSearch for EVERY regulatory and standards topic — do not rely solely on training data for legal/compliance info
- Use WebFetch to read official regulation texts, government guidelines, and industry standard specs
- If searching for regional requirements (e.g., Korean medical regulations), search in BOTH English and the local language
- Be specific about HOW each requirement translates into software features
- If you cannot find authoritative sources for a requirement, clearly mark it as
  "Needs verification — based on training data, not confirmed from official sources"
- The IDEA provider (human) will review this file, so write for a domain expert audience
- Do NOT skip sections — write "Not applicable" if a section doesn't apply
- This is a CRITICAL step — missing a regulatory requirement could make the entire project non-compliant"""

    def _step2_domain_inner():
        run_agent(
            cfg,
            role="PLANNER-DOMAIN",
            prompt=domain_prompt,
            tools=PLANNER_TOOLS,
            model=cfg.planner_model,
            log_suffix="planner_step2_domain",
            cwd=planner_cwd,
            timeout_minutes=30,
        )

    def _step2_domain():
        produced = _run_with_retry(
            cfg,
            step_fn=_step2_domain_inner,
            expected_file=cfg.domain_research_file,
            step_name="Domain Research (Step 2)",
            critical=True,  # domain research is critical — halt if missing
        )
        if produced:
            content = _load_file(cfg.domain_research_file)
            if "Status: SKIPPED" in content:
                log_info("Domain research: SKIPPED (not domain-specific)")
            else:
                log_ok(f"Domain research written to {cfg.domain_research_file}")

    research_prompt = f"""\
You are the PLANNER agent (Step 3/4: Technical Documentation Research).

PROJECT IDEA: {cfg.idea}
PROJECT DIRECTORY: {cfg.project_dir}

You have already chosen the tech stack in Step 1. Now you MUST research official
documentation and reliable sources BEFORE planning any tickets.

YOUR TASK:
1. Identify the TOP 8 (maximum) most important dependencies the project will use.
   Focus on the ones that matter most for implementation:
   - Core framework (e.g., Next.js, FastAPI, Express)
   - Database / ORM (e.g., Prisma, SQLAlchemy, Drizzle)
   - Authentication library (if needed)
   - UI library / component system (if needed)
   - Testing frameworks
   - Any third-party APIs or services mentioned in the idea
   Do NOT research transitive dependencies, build tools, or obvious standard-library modules.

2. For EACH dependency (max 8), use WebSearch and WebFetch to find and read:
   - The official documentation site (e.g., nextjs.org/docs, fastapi.tiangolo.com)
   - The official getting-started / quickstart guide
   - API reference for the specific features you'll need
   - Known gotchas, migration guides, or breaking changes in the latest version
   Limit yourself to at most 3 WebSearch calls and 2 WebFetch calls per dependency.
   If official docs don't exist, look for well-known community resources
   (e.g., MDN for web APIs, DigitalOcean tutorials, reputable blog posts).

3. Write ALL your findings to: {cfg.research_file}

IMPORTANT: You MUST finish within a reasonable time. Do NOT exhaustively research
every sub-feature. Focus on the getting-started patterns, version numbers, and
gotchas that the coder actually needs. Once you have written the research file,
output the line "RESEARCH_COMPLETE" and stop.

The research file MUST follow this format:

# Documentation Research

## Project: <name>
## Date: <today>

---

### <Dependency 1 Name> (e.g., Next.js 15)
- **Official docs**: <URL>
- **Version**: <latest stable version found>
- **Key findings**:
  - <important pattern, API, or convention relevant to this project>
  - <another finding>
- **Gotchas / Breaking changes**:
  - <anything that could trip up the coder>
- **Relevant code patterns**:
  ```
  <short code snippet from docs showing the correct pattern>
  ```
- **Source reliability**: official docs | verified community resource | trained knowledge only

---

### <Dependency 2 Name>
(same format)

---

## Third-Party APIs
### <API Name> (if any)
- **Official docs**: <URL>
- **Authentication method**: <API key, OAuth, etc.>
- **Rate limits**: <if documented>
- **Key endpoints needed**:
  - `GET /endpoint` — description
- **SDK/client library**: <recommended official client, if any>

---

## Research Summary
- Total dependencies researched: <N>
- Docs found and verified: <N>
- Falling back to trained knowledge for: <list any where no docs were found>

---

RULES:
- You MUST use WebSearch for every major dependency — do not skip this step
- You MUST use WebFetch to read at least the getting-started page of each framework
- If a search returns no useful results, note "No official docs found — using trained knowledge"
  and explain what you know from training data
- Focus on the SPECIFIC features the project needs, not a general overview
- Include version numbers — the coder needs to know which version to install
- Include code snippets from docs when they show the correct pattern for what we're building
- This research will be read by the CODER and REVIEWER agents, so be thorough and specific
- STOP CONDITION: Once you have written the research file, output "RESEARCH_COMPLETE" and stop immediately.
  Do NOT continue researching after writing the file. Do NOT research more than 8 dependencies."""

    def _step3_research_inner():
        run_agent(
            cfg,
            role="PLANNER-RESEARCH",
            prompt=research_prompt,
            tools=PLANNER_TOOLS,
            model=cfg.planner_model,
            log_suffix="planner_step3_research",
            cwd=planner_cwd,
            timeout_minutes=15,
        )

    def _step3_research():
        _run_with_retry(
            cfg,
            step_fn=_step3_research_inner,
            expected_file=cfg.research_file,
            step_name="Tech Documentation Research (Step 3)",
            critical=False,  # can proceed without — coder will use training data
        )

    # Run steps 2 and 3 sequentially
    banner("PLANNER - Step 2/4", "Domain Research")
    _step2_domain()
    post_log_summary(cfg, "plan_domain")
    banner("PLANNER - Step 3/4", "Tech Documentation Research")
    _step3_research()
    post_log_summary(cfg, "plan_research")

    # ==================================================================
    # Step 3.5: Research spot-check (verify key claims)
    # ==================================================================
    if cfg.research_file.exists():
        banner("PLANNER — Step 3.5", "Research Spot-Check")

        import json as _json
        from mad.runner import run_agent_structured

        verify_schema = _json.dumps({
            "type": "object",
            "properties": {
                "checks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "claim": {
                                "type": "string",
                                "description": "Exact quote from research.md being verified",
                            },
                            "category": {
                                "type": "string",
                                "enum": ["version", "api_syntax", "config", "deprecation", "install_cmd", "other"],
                            },
                            "source_url": {
                                "type": "string",
                                "description": "URL of the official source you verified against",
                            },
                            "source_quote": {
                                "type": "string",
                                "description": "Exact text from the official source that confirms or contradicts the claim",
                            },
                            "verified": {"type": "boolean"},
                            "correction": {
                                "type": "string",
                                "description": "If verified=false, the correct information. Required when verified is false.",
                            },
                            "severity": {
                                "type": "string",
                                "enum": ["critical", "major", "minor"],
                                "description": "How badly this would break the build if wrong",
                            },
                        },
                        "required": ["claim", "category", "source_url", "source_quote", "verified", "severity"],
                    },
                    "minItems": 5,
                },
                "overall_reliable": {"type": "boolean"},
            },
            "required": ["checks", "overall_reliable"],
        })

        verify_prompt = f"""\
You are an ADVERSARIAL RESEARCH VERIFIER. You MUST find errors — assume the research \
contains at least 1-2 mistakes because it was generated by an AI that may hallucinate \
version numbers, API syntax, or deprecated patterns.

Read the research file at: {cfg.research_file}

YOUR TASK — follow these steps EXACTLY:

**Step 1: Extract claims** (Read the file)
Read research.md and extract at least 5 specific, falsifiable claims. Prioritize:
- Version numbers (e.g., "Next.js 15", "FastAPI 0.109")
- Install commands (e.g., "pip install fastapi[all]", "npx create-next-app@latest")
- API syntax / code patterns (e.g., "app.use(cors())", "from fastapi import FastAPI")
- Configuration file names and keys (e.g., "next.config.js", "tsconfig.json paths")
- Deprecation status (e.g., "pages/ router is deprecated in favor of app/")
- Default ports, file paths, or environment variable names

**Step 2: Verify EACH claim** (WebSearch + WebFetch)
For EACH claim you extracted:
1. WebSearch for the OFFICIAL source (npm, pypi, official docs, GitHub releases page)
2. WebFetch the official page to get the EXACT current information
3. Compare character-by-character: does the research claim EXACTLY match the official source?
4. Pay special attention to:
   - Major version mismatches (e.g., research says v14 but latest is v15)
   - Renamed or moved APIs (e.g., `getServerSideProps` → server components)
   - Changed default behavior between versions
   - Package names that have been renamed (e.g., `node-sass` → `sass`)
   - Deprecated flags or options that no longer work

**Step 3: Report honestly**
- If the research says "Next.js 15" but the latest stable is 15.3.1, that's MINOR (close enough).
- If the research says "Next.js 14" but latest stable is 15.x, that's CRITICAL (wrong major version).
- If a code pattern uses a removed/renamed API, that's CRITICAL.
- If an install command has wrong package name or flags, that's MAJOR.
- You MUST mark `verified: false` for anything that doesn't match. Do NOT give benefit of the doubt.
- Include the EXACT quote from the official source in `source_quote` so the correction is evidence-based.

IMPORTANT:
- Check AT LEAST 5 claims. More is better.
- You MUST use WebSearch and WebFetch for EVERY claim — do not verify from memory.
- If you cannot find an official source for a claim, mark it as `verified: false` with \
  severity "major" and note "No official source found to verify this claim."
- Be skeptical. Your job is to CATCH errors, not to confirm the research is correct."""

        try:
            _, verify_data = run_agent_structured(
                cfg,
                role="PLANNER-VERIFY",
                prompt=verify_prompt,
                tools="Read,WebSearch,WebFetch",
                model=cfg.planner_model,
                log_suffix="planner_step3_verify",
                json_schema=verify_schema,
                cwd=planner_cwd,
                timeout_minutes=15,
            )

            checks = verify_data.get("checks", [])
            failures = [c for c in checks if not c.get("verified", True)]
            critical_failures = [c for c in failures if c.get("severity") == "critical"]
            major_failures = [c for c in failures if c.get("severity") == "major"]

            if failures:
                log_warn(
                    f"Research verification: {len(failures)}/{len(checks)} claims incorrect "
                    f"({len(critical_failures)} critical, {len(major_failures)} major)"
                )
                # Append corrections to research.md with full evidence
                corrections = "\n\n---\n\n## ⚠️ Corrections (auto-verified)\n\n"
                corrections += f"Verified {len(checks)} claims — {len(failures)} need correction.\n\n"
                for c in failures:
                    sev = c.get("severity", "unknown").upper()
                    corrections += f"### [{sev}] {c['claim']}\n"
                    corrections += f"- **Category:** {c.get('category', 'unknown')}\n"
                    if c.get("source_url"):
                        corrections += f"- **Source:** {c['source_url']}\n"
                    if c.get("source_quote"):
                        corrections += f"- **Official says:** {c['source_quote']}\n"
                    if c.get("correction"):
                        corrections += f"- **Correction:** {c['correction']}\n"
                    corrections += "\n"
                with open(cfg.research_file, "a", encoding="utf-8") as f:
                    f.write(corrections)
                log_ok("Corrections appended to research.md")
            else:
                log_ok(f"Research verification: all {len(checks)} claims verified ✓")

        except Exception as e:
            log_warn(f"Research verification failed ({e}) — proceeding without verification")
        post_log_summary(cfg, "plan_spotcheck")

    # ==================================================================
    # Step 4: Ticket generation (referencing both research files)
    # ==================================================================
    banner("PLANNER — Step 4/4", "Ticket Generation")

    rules_context = ""
    if rules_file:
        rules_content = _load_file(cfg.rules_dir / rules_file.split("/")[-1])
        rules_context = (
            f"\nCODING RULES TO FOLLOW (the coder MUST adhere to these):\n"
            f"File: {rules_file}\nContent:\n{rules_content}"
        )

    research_context = ""
    if cfg.research_file.exists():
        research_context = (
            f"\nTECH DOCUMENTATION RESEARCH (completed in Step 3):\n"
            f"File: {cfg.research_file}\n(Read this file in full before generating tickets.)\n"
        )

    domain_context = ""
    if cfg.domain_research_file.exists():
        content = _load_file(cfg.domain_research_file)
        if "Status: SKIPPED" not in content:
            domain_context = (
                f"\nDOMAIN-SPECIFIC RESEARCH (completed in Step 2 — CRITICAL for compliance):\n"
                f"File: {cfg.domain_research_file}\n(Read this file in full. Domain requirements are NOT optional.)\n"
            )

    brainstorm_context = ""
    if cfg.brainstorm_consensus_file.exists():
        brainstorm_context = (
            f"\nBRAINSTORM CONSENSUS (multi-persona analysis of the project):\n"
            f"File: {cfg.brainstorm_consensus_file}\n(Read this file. It contains architecture decisions, "
            f"critical requirements, and trade-offs from a multi-perspective brainstorm session.)\n"
        )

    tickets_prompt = f"""\
You are the PLANNER agent (Step 4/4: Ticket Generation).

PROJECT IDEA: {cfg.idea}
PROJECT DIRECTORY: {cfg.project_dir}

{rules_context}

{research_context}

{domain_context}

{brainstorm_context}

{evolution_block}

BEFORE YOU START:
- Read {cfg.research_file} in full if you haven't already
- Read {cfg.domain_research_file} in full if it exists and is not SKIPPED
  (this file contains regulatory/compliance requirements that MUST be reflected in tickets)
- These files were written in Steps 2 and 3. If the content above is truncated, read the files directly.

YOUR TASK:
Decompose the project idea into detailed, implementation-ready tickets.
Write ALL tickets to: {cfg.tickets_file}

TICKET FORMAT — each ticket MUST follow this structure:

---

# Project: <project name>

## Tech Stack
<language, framework, database, and tools chosen in Step 1>

## Coding Rules
Reference: <path to the rules file>

## Documentation Research
Reference: {cfg.research_file}

## Domain Research
Reference: {cfg.domain_research_file}

---

### Ticket 1: <title>
- **Priority**: P0 | P1 | P2
- **Type**: setup | feature | ui | integration | testing | config | compliance
- **Dependencies**: [ticket numbers this depends on, or "none"]
- **References**: [links to specific doc sections from research.md and/or domain_research.md]
- **Files to create/modify**:
  - `path/to/file.ext` — description of what this file does
- **Acceptance Criteria**:
  - [ ] Criterion 1
  - [ ] Criterion 2
- **Implementation Details**:
  Detailed, specific instructions. Include:
  - Exact function signatures where relevant
  - Data models / schemas
  - API endpoint specs (method, path, request/response)
  - Error handling requirements
  - Edge cases to handle
  - **Reference the specific patterns and versions found in research.md**
- **Domain Requirements** (if applicable):
  - Regulatory requirements this ticket must satisfy (from domain_research.md)
  - Compliance checks to implement
  - Domain-specific validation rules
- **Testing Requirements**:
  - What tests to write
  - Expected test commands
  - Domain-specific test scenarios (if applicable)

---

RULES FOR TICKET CREATION:
1. Tickets must be ordered by dependency (setup first, then core features, then UI, then integration)
2. Each ticket must be self-contained enough for the coder to implement without guessing
3. Include a "Ticket 0: Project Setup" that initializes the project, installs dependencies, and sets up config.
   Pin dependency versions to those found in the documentation research.
4. For UI tickets: describe a UNIQUE, ARTISTIC design direction — not generic Bootstrap/Material defaults.
   The UI must have a distinct visual identity (custom color palette, typography choices, layout philosophy).
   But ALWAYS balance aesthetics with usability — never sacrifice UX for visual flair.
   Include specific CSS/design tokens where possible.
5. The last ticket must be "E2E Testing Setup" that creates end-to-end tests for all critical flows
6. Include estimated file counts and rough scope per ticket
7. Be VERY specific — "Add authentication" is too vague. "Implement JWT auth with /api/auth/login POST
   accepting {{email, password}}, returning {{token, refreshToken}}, storing refresh tokens in HttpOnly cookies
   with 7d expiry, access tokens as Bearer with 15m expiry" is the right level of detail.
8. Every ticket that touches a researched dependency MUST include a **References** field
   pointing to the specific doc sections from research.md.
9. If the research noted gotchas or breaking changes, create explicit acceptance criteria
   to avoid those pitfalls.
10. IF DOMAIN RESEARCH EXISTS AND IS NOT SKIPPED:
    - Create dedicated compliance/security tickets early in the sequence (P0 priority)
    - Every ticket that handles sensitive data MUST reference the relevant domain requirements
    - Include a "Compliance Verification" ticket that checks all regulatory requirements are met
    - Include domain-specific validation in acceptance criteria
      (e.g., "Korean resident registration number must be validated and encrypted at rest")
    - Do NOT defer compliance to "future work" — it must be built in from the start

RULES FOR MULTI-COMPONENT PROJECTS (client + server, microservices, frontend + backend, etc.):
11. If the project has MULTIPLE components that communicate (e.g., frontend + backend + DB),
    you MUST add an **Integration Contract** section at the TOP of the tickets file, BEFORE Ticket 0.
    This contract is the SINGLE SOURCE OF TRUTH for all cross-component interfaces.
    Format:

    ## Integration Contract

    ### API Endpoints
    | Method | Path | Request Body | Response Body | Auth | Component |
    |--------|------|-------------|---------------|------|-----------|
    | POST | /api/v1/auth/login | {{email, password}} | {{token, refreshToken}} | none | backend |
    | GET | /api/v1/users/me | - | {{id, email, name}} | Bearer | backend |
    (list EVERY endpoint — frontend and backend MUST use these EXACT paths)

    ### Ports & Service Names
    | Service | Port | Docker Name | Health Check |
    |---------|------|-------------|-------------|
    | backend | 8000 | backend | GET /health |
    | frontend | 3000 | frontend | - |
    | database | 5432 | db | pg_isready |
    (these names are used in docker-compose, CORS, proxy configs, and env vars)

    ### Environment Variables
    | Variable | Used By | Example Value | Description |
    |----------|---------|---------------|-------------|
    | DATABASE_URL | backend | postgresql://user:pass@db:5432/mydb | DB connection |
    | BACKEND_URL | frontend | http://backend:8000 | API proxy target |
    (every env var that crosses component boundaries)

    ### CORS Configuration
    - Allowed origins: list every origin the backend must accept
    - Include both Docker-internal (http://frontend:3000) and local dev (http://localhost:3000)

    ### Shared Types / Schemas
    - List any data types shared between frontend and backend (User, Auth response, etc.)
    - These MUST be implemented identically on both sides

12. EVERY ticket that implements a cross-component interface MUST reference the Integration Contract:
    "Implement endpoints per Integration Contract: POST /api/v1/auth/login, GET /api/v1/auth/me"
    The coder MUST read the contract and use the EXACT paths, ports, and variable names specified.
13. Include a dedicated "Integration & Connectivity" ticket (near the end, before E2E testing)
    that verifies all cross-component connections work:
    - Backend CORS accepts all specified origins
    - Frontend proxy/rewrites target the correct backend URL
    - Docker services can reach each other by service name
    - All env vars are set in docker-compose.yml and .env.example
    - Health check endpoints respond correctly
14. docker-compose.yml MUST have proper `depends_on` with health checks so services
    start in the correct order (DB → backend → frontend).

RULES FOR MINIMAL TICKET UNITS:
15. Each ticket MUST be the SMALLEST SELF-CONTAINED unit of work. A ticket that does
    multiple distinct things must be split. Examples:
    Bad: "Ticket 5: CRUD API for Users" (this is 4 tickets)
    Good: "Ticket 5: Create User (POST /api/users)", "Ticket 6: Get User (GET /api/users/:id)",
          "Ticket 7: Update User (PUT /api/users/:id)", "Ticket 8: Delete User (DELETE /api/users/:id)"
    Bad: "Ticket 3: Authentication — login, register, forgot password, JWT middleware"
    Good: "Ticket 3: Register endpoint", "Ticket 4: Login endpoint", "Ticket 5: JWT middleware",
          "Ticket 6: Forgot password flow"
    Bad: "Ticket 2: Dashboard page with charts, tables, and filters"
    Good: "Ticket 2: Dashboard layout and navigation", "Ticket 3: Dashboard data table",
          "Ticket 4: Dashboard charts", "Ticket 5: Dashboard filters"
    Each ticket = one API endpoint, one UI component/page section, one middleware, or one config step.
    The coder implements ONE ticket per sprint in a fresh context — large tickets cause context
    exhaustion and produce lower quality code.

RULES FOR E2E-TESTABLE ACCEPTANCE CRITERIA:
16. For any ticket involving UI pages or API endpoints, write acceptance criteria that
    can be verified by automated browser testing (Playwright) or curl commands.
    Bad: "The dashboard should look professional"
    Good: "Navigating to /dashboard shows a page with a table containing columns: Name, Status, Date.
           Clicking the 'Add' button opens a modal with fields: Name (text), Status (dropdown).
           Submitting the form with valid data adds a new row to the table."
    Bad: "The login should work"
    Good: "POST /api/auth/login with {{"email": "test@test.com", "password": "password"}} returns
           200 with {{"token": "...", "user": {{...}}}}. Navigating to /login, filling the email
           and password fields, and clicking 'Sign In' redirects to /dashboard."
    This is critical — the reviewer will use Playwright browser tools to test web UIs
    and curl to test APIs. Vague criteria cannot be automatically verified.
    NOTE: Playwright E2E testing is only applicable for web applications (frontend, backend,
    fullstack). For CLI tools, libraries, desktop, and mobile apps, write acceptance criteria
    that can be verified via Bash commands (run commands, check exit codes, verify output).

RULES FOR E2E TEST TICKET:
17. The last ticket before finalization must be a comprehensive **E2E Test** ticket.
    For web applications, this ticket MUST instruct the coder to write Playwright-based
    E2E tests that simulate real user interactions:
    - Navigate to each page
    - Fill forms, click buttons, select options
    - Verify page content updates correctly
    - Test the complete user journey (e.g., register → login → create item → view item → delete item)
    - Check for JavaScript console errors and failed network requests
    For non-web applications, write appropriate integration/functional tests using the project's
    test framework or Bash scripts.

RULES FOR UI/UX DESIGN:
18. For ANY ticket involving frontend UI components, pages, or layouts, instruct the coder
    to use the `frontend-design` skill (invoked via the Skill tool) to design the UI/UX.
    Include in the ticket's implementation details:
    "Use the frontend-design skill to design the UI for this component/page before implementing it.
     The skill will produce a high-quality, cohesive design that should be followed during implementation."
    This ensures the UI is designed with professional quality rather than ad-hoc styling.

Write the complete tickets file now."""

    def _step4_tickets():
        run_agent(
            cfg,
            role="PLANNER-TICKETS",
            prompt=tickets_prompt,
            tools=PLANNER_TOOLS,
            model=cfg.planner_model,
            log_suffix="planner_step4_tickets",
            cwd=planner_cwd,
            timeout_minutes=30,
        )

    _run_with_retry(
        cfg,
        step_fn=_step4_tickets,
        expected_file=cfg.tickets_file,
        step_name="Ticket Generation (Step 4)",
        critical=True,  # cannot proceed without tickets
    )

    if cfg.tickets_file.exists():
        count = cfg.tickets_file.read_text(encoding="utf-8").count("### Ticket")
        log_ok(f"Created {count} tickets at {cfg.tickets_file}")
    else:
        log_warn("Tickets file not found — check planner logs")
