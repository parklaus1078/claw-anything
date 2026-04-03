# MAD — Multi-Agent Development

A CLI tool that orchestrates multiple Claude Code agents to **plan**, **code**, and **review** entire software projects from a single idea.

You describe a project. MAD decomposes it into detailed tickets, researches official documentation, generates framework-specific coding rules, implements each ticket with self-verification, runs tests, iteratively fixes issues until a score threshold is met, writes a README, and captures learnings that improve future runs.

## How It Works

```
 "A real-time chat app with a retro terminal aesthetic"
  │
  ▼
┌──────────────────────────────────────────────────────┐
│  PLANNER                                             │
│  1. Pick tech stack, generate coding rules           │
│  2. Domain research (if regulated/specialized)    ┐  │
│  3. Tech documentation research (WebSearch)       ┘  │  ← parallel
│  3.5. Spot-check research claims                     │
│  4. Write detailed, ordered tickets                  │
└──────────────────────┬───────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────┐
│  CODER (per-ticket sprints)                          │
│  For each ticket:                                    │
│    1. Implement in fresh context                     │
│    2. Self-verify (build + tests)                    │
│    3. Retry up to 3x on failure                      │
│    4. Git snapshot                                   │
└──────────────────────┬───────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────┐
│  REVIEWER  (fresh context — unbiased)                │
│  Static analysis + build/test + structured scoring   │
│  Diff-aware on iteration 2+ (focuses on changes)     │
└──────┬───────────────────────┬───────────────────────┘
       │ score < threshold     │ score >= threshold
       ▼                       │
┌──────────────┐               │
│  CODER (fix) │               │
│  Fix listed  │               │
│  issues      │               │
└──────┬───────┘               │
       └──► REVIEWER ──────────┘  (loop until pass score or max iterations)
                               │
                               ▼
┌──────────────────────────────────────────────────────┐
│  FINALIZER — Write README.md                         │
├──────────────────────────────────────────────────────┤
│  EVOLUTION — Capture learnings, validate with metrics│
└──────────────────────────────────────────────────────┘
```

## Key Design Principles

- **Generator-Evaluator pattern**: The Reviewer always runs in a fresh context with no session history, preventing self-confirmation bias. Based on [Anthropic's harness design](https://www.anthropic.com/engineering/harness-design-long-running-apps).
- **Per-ticket sprints**: Each ticket gets its own `claude -p` call with fresh context, avoiding context exhaustion on large projects. A verifier checks build/tests after each sprint.
- **File-based communication**: All state passes through files (tickets, research, refinement lists), not session history. Every agent works correctly even after a crash and cold restart.
- **Diff-aware reviews**: On iteration 2+, the reviewer sees a `git diff` of what changed, focusing verification on fixes instead of re-reading everything.
- **Structured scoring**: Review scores are extracted via `--json-schema` for deterministic pass/fail decisions. Regex fallback for robustness.
- **Evolution with validation**: Cross-project learnings are tracked alongside metrics. Learnings that correlate with declining scores get flagged for removal.

## Prerequisites

- **Python 3.10+**
- **Claude Code CLI** installed and authenticated (`claude` must be available in your PATH)
  - [Claude Code installation guide](https://docs.anthropic.com/en/docs/claude-code)
  - You need an active **Claude Pro**, **Max**, or **API** plan
- **Git**
- Python packages: `click` and `rich` (installed automatically if using pip)

## Installation

### Option A: pip install (recommended)

```bash
git clone https://github.com/<your-username>/multi-agent-dev.git
cd multi-agent-dev
pip install -e .
```

This installs `mad` as a global command.

### Option B: Run without pip

```bash
git clone https://github.com/<your-username>/multi-agent-dev.git
cd multi-agent-dev
./bin/mad --help

# Or add to your PATH
export PATH="$PWD/bin:$PATH"
```

The only requirement is that `click` and `rich` are importable by your Python 3. If they aren't:

```bash
pip install click rich
```

### Option C: Symlink to PATH

```bash
git clone https://github.com/<your-username>/multi-agent-dev.git
cd multi-agent-dev
ln -s "$PWD/bin/mad" ~/.local/bin/mad
mad --version
```

## Quick Start

```bash
# Build an entire project from a single idea
mad run ./my-project "A REST API for a bookstore with inventory management, search, and user reviews"

# Or select a project first, then run commands without repeating args
mad select my-project
mad run
```

## Commands

### `mad run` — Full pipeline

```bash
mad run [project_dir] ["<idea>"] [OPTIONS]

# Options:
#   -n, --max-iterations INTEGER   Max review<->fix cycles (default: 10)
#   --pass-score FLOAT             Score to auto-approve (default: 9.0/10)
#   --budget FLOAT                 Per-call budget in USD (default: unlimited)
#   --model TEXT                   Set same model for all agents
#   --planner-model TEXT           Model for planner
#   --coder-model TEXT             Model for coder
#   --reviewer-model TEXT          Model for reviewer
```

`project_dir` and `idea` are optional when an active project is selected.

**Examples:**

```bash
mad run ~/projects/chat-app "A real-time chat app with rooms and a retro terminal aesthetic"
mad run ./todo-app "A minimalist todo app with brutalist UI" -n 3 --pass-score 8.5
mad run --budget 10.0 --model opus
```

### `mad plan` — Planning only

Runs the 4-step Planner: tech stack analysis, domain research (if applicable), documentation research, ticket generation.

```bash
mad plan [project_dir] ["<idea>"]
```

### `mad code` — Coding only

Implements all tickets via per-ticket sprints with self-verification.

```bash
mad code [project_dir] ["<idea>"]
```

### `mad review` — Review only

```bash
mad review [project_dir] ["<idea>"] [-i ITERATION] [--pass-score FLOAT]
```

### `mad fix` — Fix one cycle

```bash
mad fix [project_dir] ["<idea>"]
```

### `mad resume` — Resume after crash or limit hit

```bash
mad resume [project_name]
```

MAD saves state after every completed step. On crash, limit hit, or Ctrl+C, resume exactly where you left off. Pass a project name, or it uses the active project.

### `mad finalize` — README + Evolution

```bash
mad finalize [project_dir] ["<idea>"]
```

### Project Management

```bash
mad projects            # List all registered projects
mad select <name>       # Set active project (skip dir/idea on future commands)
mad status              # Show artifacts and resume info for active project
mad logs [-n 50]        # List recent agent logs
mad costs               # Show cost breakdown for last run
```

### Configuration

```bash
mad set-model --planner opus --coder sonnet --reviewer opus
mad set-model --all opus
mad set-model --pass-score 8.5
mad set-model --budget 5.0
mad get-model           # Show current defaults
```

## Step-by-Step Workflow

```bash
# 1. Plan — review tickets before committing to code
mad plan ./my-project "A task management API with priorities and Slack notifications"

# 2. Review the generated artifacts
cat projects/my-project/specs/tickets.md
cat projects/my-project/specs/research.md
cat projects/my-project/specs/domain_research.md  # if domain-specific

# 3. (Optional) Edit tickets
vim projects/my-project/specs/tickets.md

# 4. Code — implement all tickets (per-ticket sprints)
mad code

# 5. Review — build, test, evaluate
mad review -i 1

# 6. Fix — address issues
mad fix

# 7. Review again
mad review -i 2

# 8. Finalize — write README and capture learnings
mad finalize

# 9. Check costs
mad costs
```

## Project Structure

```
multi-agent-dev/
├── bin/mad                        # CLI entry point
├── pyproject.toml                 # Package metadata
├── README.md
│
├── mad/                           # Python package
│   ├── cli.py                     # Click commands (run, plan, code, review, fix, etc.)
│   ├── config.py                  # RunConfig, paths, tool permissions, settings
│   ├── console.py                 # Thread-safe Rich terminal output
│   ├── runner.py                  # Core agent runner (claude -p), cost tracking
│   ├── state.py                   # Run state persistence for crash recovery
│   ├── projects.py                # Multi-project registry
│   ├── tickets.py                 # Ticket parser with dependency graph
│   ├── costs.py                   # Per-run cost tracking
│   ├── metrics.py                 # Cross-project metrics for evolution validation
│   ├── discord.py                 # Discord webhook integration (live streaming)
│   └── agents/
│       ├── planner.py             # 4-step: rules → domain research → tech research → tickets
│       ├── coder.py               # Per-ticket sprints with self-verification
│       ├── reviewer.py            # Structured scoring, diff-aware reviews
│       └── finalizer.py           # README generation + evolution with metrics
│
├── rules/                         # Coding rules (shared across projects)
│   ├── general_coding_rules.md    # Base principles (all languages)
│   └── rules_*.md                 # Auto-generated per stack
│
├── projects/                      # Per-project data
│   └── <project-slug>/
│       ├── specs/                 # Tickets, research, refinement lists, review logs, state
│       └── logs/                  # Agent logs (JSON + human-readable .md)
│
├── evolution/                     # Cross-project (shared)
│   ├── learnings.md               # Master learnings file (validated over time)
│   ├── metrics.json               # Score history for trend analysis
│   └── epoch_<run_id>.md          # Per-run analysis
│
└── webhook-icons/                 # Discord webhook agent icons (512x512)
    ├── planner_icon.{png,svg}
    ├── coder_icon.{png,svg}
    ├── reviewer_icon.{png,svg}
    ├── verifier_icon.{png,svg}
    └── finalizer_icon.{png,svg}
```

## Planner Pipeline

The Planner runs 4 steps before any code is written:

1. **Tech Stack & Coding Rules** — Analyzes the idea, picks a stack, generates framework-specific coding rules (or reuses existing ones)
2. **Domain Research** (parallel) — If the project is domain-specific (healthcare, finance, legal, etc.), researches regulations, industry standards, auth policies, and compliance requirements via WebSearch
3. **Tech Documentation Research** (parallel) — Fetches official docs for every major dependency, records version numbers, API patterns, gotchas, and code snippets
4. **Research Spot-Check** — Verifies 3-5 key claims from the research via fresh web searches. Appends corrections if anything is outdated.
5. **Ticket Generation** — Produces detailed, ordered tickets with acceptance criteria, file lists, implementation details, and references to research findings

Steps 2 and 3 run in **parallel** via ThreadPoolExecutor.

Domain research produces a `domain_research.md` file structured for human review: regulatory requirements, industry standards, auth/authorization policies, data security requirements, domain workflows, and a terminology glossary.

## Coding: Per-Ticket Sprints

Instead of implementing the entire project in one shot (which exhausts context on large projects), the Coder runs **one `claude -p` call per ticket**:

1. Each sprint gets fresh context with only: the specific ticket, coding rules, research references
2. After each sprint, a **Verifier** agent checks that the project builds and tests pass
3. On failure, the sprint retries up to 3 times with the error context
4. A git commit is created after each ticket for diff tracking

Sprint progress is tracked in the state file, so `mad resume` picks up at the exact ticket where a crash occurred.

## Reviewer: Structured Scoring

The Reviewer evaluates against these criteria (each scored 0-10):

| Criterion | What it checks |
|---|---|
| Ticket compliance | Were all acceptance criteria met? |
| Functionality | Does the project build, start, and serve requests? |
| Code quality | Follows coding rules? Clean structure? Error handling? |
| Doc compliance | Used correct APIs/versions from research.md? |
| Domain compliance | Regulatory requirements implemented? (if applicable) |
| Security | No hardcoded secrets? Input validation? OWASP risks? |
| Testing | Tests present, passing, covering critical paths? |
| UI quality | Unique/artistic yet usable? (code review, not visual) |
| DX | Can a new developer clone, install, and run it? |

Scores are extracted via `--json-schema` for deterministic parsing. The overall score determines pass/fail against the configurable threshold (default: 9.0/10).

On iteration 2+, the reviewer receives a `git diff` showing exactly what the Coder changed, so it can focus verification on the fixes.

## Evolution System

MAD improves across projects:

1. After each run, the **Evolution agent** analyzes review logs and produces an epoch report
2. It updates `evolution/learnings.md` with role-specific insights (Planner, Coder, Reviewer)
3. **Metrics validation**: scores are tracked in `evolution/metrics.json`. The evolution agent compares trends — learnings that correlate with declining scores get flagged as "suspect," while those correlated with improvement are marked "validated"
4. All agents read the learnings file on future runs

## Cost Tracking

Every `claude -p` call's cost, duration, and turn count are tracked automatically.

```bash
# View costs for the last run
mad costs

# Set a per-call budget limit
mad set-model --budget 5.0
mad run --budget 10.0
```

## Crash Recovery

MAD runs can take hours. The state system handles crashes:

```bash
mad run ./my-app "A chat app"
# -> [ERROR] CODER-T5 hit a usage limit. State saved.

mad status
# -> Coding complete up to ticket 4. Resuming from ticket 5.

mad resume
# -> Picks up from ticket 5. Skips plan and tickets 0-4.
```

State is saved after every completed step — including individual ticket sprints. Resume granularity:

| Crashed during | `mad resume` starts from |
|---|---|
| Planning | Plan phase |
| Coding (ticket N) | Ticket N (skips 0 to N-1) |
| Review (iteration N) | Review iteration N |
| Fix (iteration N) | Fix for iteration N |
| Finalization | Finalization |

## Configuration

### Settings

```bash
mad set-model --planner opus --coder sonnet --reviewer opus
mad set-model --pass-score 8.5
mad set-model --budget 5.0
mad get-model
```

Settings are saved to `settings.json` and apply to all future runs. Override per-run with CLI flags.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MAD_HOME` | Directory where MAD stores projects, rules, and evolution data | The cloned repo directory |

### Customization

- **Edit `rules/general_coding_rules.md`** to change base coding principles
- **Edit generated `rules/rules_*.md`** to adjust stack-specific conventions
- **Edit `projects/<slug>/specs/tickets.md`** after `mad plan` to adjust tickets before coding
- **Edit `evolution/learnings.md`** to seed the system with your own learnings

## How It Uses Claude Code

MAD invokes `claude -p` (headless mode). Each agent call:

1. Constructs a prompt with role, file references (not inline content), and instructions
2. Runs `claude -p "<prompt>" --allowedTools "<tools>" --output-format json [--model X] [--json-schema Y] [--max-budget-usd Z]`
3. Parses the JSON response for result, session_id, and cost data
4. Writes both a raw JSON log and a human-readable Markdown log

Every agent invocation is **self-contained from files** — no session resumption dependency. This means any agent can restart cleanly after a crash.

### Tool Permissions per Agent

| Agent | Tools | Rationale |
|-------|-------|-----------|
| Planner | Read, Grep, Glob, Write, WebSearch, WebFetch, Skill | Research + write specs. Skills for specialized workflows. |
| Coder | Read, Edit, Write, Bash, Grep, Glob | Full implementation capabilities. |
| Verifier | Read, Bash, Grep, Glob, Skill | Build + test only. Skills for specialized checks. |
| Reviewer | Read, Bash, Grep, Glob, Write, Skill | Test + write reports. Skills for advanced evaluation. |
| Finalizer | Read, Write, Grep, Glob | Write README + learnings. No Bash needed. |

## Skills Integration

Agents with the `Skill` tool can invoke Claude Code skills at runtime. Skills are modular capability packages installed at `~/.claude/skills/` or via plugins. Claude decides whether to invoke a skill based on task relevance — no manual triggering needed.

**How it works:**

1. Every installed skill's metadata (name + description) is loaded into the agent's context
2. If the agent's task matches a skill's description, it invokes the `Skill` tool automatically
3. The full skill instructions are injected only on invocation (progressive disclosure)

**Example:** If the `frontend-design` plugin is installed, the Planner will automatically invoke it when designing a web frontend — producing higher-quality UI code without any prompt changes.

Skills are available to Planner, Reviewer, and Verifier. The Coder and Finalizer operate without skills to keep their tool surface minimal and focused.

## Discord Webhooks

MAD streams live agent output to Discord channels via webhooks, with per-agent channels and custom icons.

### Setup

Configure webhook URLs in `settings.json`:

```json
{
  "webhooks": {
    "PLANNER": "https://discord.com/api/webhooks/...",
    "CODER": "https://discord.com/api/webhooks/...",
    "REVIEWER": "https://discord.com/api/webhooks/...",
    "VERIFIER": "https://discord.com/api/webhooks/...",
    "FINALIZER": "https://discord.com/api/webhooks/..."
  }
}
```

When webhooks are configured, agents run with `--output-format stream-json --verbose`, and each event (tool use, assistant messages, errors) is posted to the corresponding Discord channel in real time.

**Features:**
- Rate-limited posting (30 messages/min) to stay within Discord limits
- Automatic message chunking for long outputs (>1950 chars)
- Agent-specific webhook icons in `webhook-icons/` (PNG + SVG, 512x512)

## Limitations

- **Requires Claude Code CLI** — orchestrates `claude` commands; does not call the Anthropic API directly
- **Long-running** — a full `mad run` can take 30 minutes to several hours depending on project complexity
- **Token usage** — each sprint, review, and fix cycle consumes tokens; per-ticket sprints use more calls but produce better code
- **No visual testing** — the Reviewer does static analysis and runs test suites; browser-based visual testing via Playwright MCP is available as a plugin but not yet integrated into the review pipeline
- **Research accuracy** — WebSearch results are spot-checked but not guaranteed; domain research should be human-reviewed for regulated industries

## License

MIT
