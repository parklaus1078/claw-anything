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


MAX_STEP_RETRIES = 2


def _load_file(path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _find_rules_file(cfg: RunConfig) -> str | None:
    """Return the first rules_*.md file in the rules dir, or None."""
    matches = sorted(cfg.rules_dir.glob("rules_*.md"))
    return str(matches[0]) if matches else None


def _run_with_retry(
    cfg: RunConfig,
    *,
    step_fn,
    expected_file,
    step_name: str,
    critical: bool = False,
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

    rules_prompt = f"""\
You are the PLANNER agent (Step 1/4: Tech Stack & Coding Rules).

PROJECT IDEA: {cfg.idea}
PROJECT DIRECTORY: {cfg.project_dir}

{evolution_block}

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
    )

    rules_file = _find_rules_file(cfg)
    log_info(f"Rules file: {rules_file or 'none found'}")

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
1. Identify every major dependency the project will use:
   - Core framework (e.g., Next.js, FastAPI, Express)
   - Database / ORM (e.g., Prisma, SQLAlchemy, Drizzle)
   - Authentication library (if needed)
   - UI library / component system (if needed)
   - Testing frameworks
   - Any third-party APIs or services mentioned in the idea
   - Build tools, bundlers, deployment tools

2. For EACH dependency, use WebSearch and WebFetch to find and read:
   - The official documentation site (e.g., nextjs.org/docs, fastapi.tiangolo.com)
   - The official getting-started / quickstart guide
   - API reference for the specific features you'll need
   - Known gotchas, migration guides, or breaking changes in the latest version
   - If official docs don't exist, look for well-known community resources
     (e.g., MDN for web APIs, DigitalOcean tutorials, reputable blog posts)

3. Write ALL your findings to: {cfg.research_file}

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
- This research will be read by the CODER and REVIEWER agents, so be thorough and specific"""

    def _step3_research_inner():
        run_agent(
            cfg,
            role="PLANNER-RESEARCH",
            prompt=research_prompt,
            tools=PLANNER_TOOLS,
            model=cfg.planner_model,
            log_suffix="planner_step3_research",
            cwd=planner_cwd,
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
    banner("PLANNER - Step 3/4", "Tech Documentation Research")
    _step3_research()

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
                            "claim": {"type": "string"},
                            "verified": {"type": "boolean"},
                            "correction": {"type": "string"},
                        },
                        "required": ["claim", "verified"],
                    },
                },
                "overall_reliable": {"type": "boolean"},
            },
            "required": ["checks", "overall_reliable"],
        })

        verify_prompt = f"""\
You are a RESEARCH VERIFIER. Your job is to spot-check the documentation research.

Read the research file at: {cfg.research_file}

YOUR TASK:
1. Identify 3-5 specific, verifiable claims in the research (e.g., version numbers,
   API patterns, library names, configuration syntax)
2. For each claim, use WebSearch to verify it against current official sources
3. Report whether each claim is correct or needs correction

Focus on claims that would cause bugs if wrong (version numbers, API signatures, deprecated features).
Do NOT re-research everything — just spot-check the most critical facts."""

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
            )

            checks = verify_data.get("checks", [])
            failures = [c for c in checks if not c.get("verified", True)]

            if failures:
                log_warn(f"Research verification: {len(failures)}/{len(checks)} claims need correction")
                # Append corrections to research.md
                corrections = "\n\n## Corrections (auto-verified)\n\n"
                for c in failures:
                    corrections += f"- **{c['claim']}** → {c.get('correction', 'Needs manual verification')}\n"
                with open(cfg.research_file, "a", encoding="utf-8") as f:
                    f.write(corrections)
                log_ok("Corrections appended to research.md")
            else:
                log_ok(f"Research verification: {len(checks)}/{len(checks)} claims verified")

        except Exception as e:
            log_warn(f"Research verification failed ({e}) — proceeding without verification")

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

    tickets_prompt = f"""\
You are the PLANNER agent (Step 4/4: Ticket Generation).

PROJECT IDEA: {cfg.idea}
PROJECT DIRECTORY: {cfg.project_dir}

{rules_context}

{research_context}

{domain_context}

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
