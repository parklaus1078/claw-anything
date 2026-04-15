# MAD — Multi-Agent Development

A CLI tool that orchestrates multiple Claude Code agents to **plan**, **code**, and **review** entire software projects from a single idea.

You describe a project. MAD decomposes it into detailed tickets, researches official documentation, generates framework-specific coding rules, implements each ticket with self-verification, runs tests, iteratively fixes issues until a score threshold is met, writes a README, and captures learnings that improve future runs.

## How It Works

```
 "A real-time chat app with a retro terminal aesthetic"
  │
  ▼
┌──────────────────────────────────────────────────────┐
│  BRAINSTORM (optional: --brainstorm)                 │
│  16 personas available (5 default), configurable     │
│  N rounds (default 3) → Consensus document           │
│  --brainstorm-personas architect,cto,ai-engineer     │
│  --brainstorm-rounds 5                               │
└──────────────────────┬───────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────┐
│  PLANNER                                             │
│  1. Pick tech stack, generate coding rules           │
│  2. Domain research (if regulated/specialized)    ┐  │
│  3. Tech documentation research (WebSearch)       ┘  │ 
│  3.5. Spot-check research claims                     │
│  4. Write detailed, ordered tickets                  │
│     (uses brainstorm consensus if available)         │
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
│  Adaptive E2E: Playwright for web, Bash for CLI/API  │
│  Structured scoring + diff-aware on iteration 2+     │
└──────┬───────────────────────┬───────────────────────┘
       │ score < threshold     │ score >= threshold
       ▼                       │
┌──────────────┐               │
│  CODER (fix) │               │
│  Fix listed  │               │
│  issues      │               │
└──────┬───────┘               │
       └─── REVIEWER ──────────┘  (loop until pass score or max iterations)
                               │
                               ▼
┌──────────────────────────────────────────────────────┐
│  FINALIZER — Write README.md                         │
├──────────────────────────────────────────────────────┤
│  EVOLUTION — Capture learnings, validate with metrics│
└──────────────────────────────────────────────────────┘

  Discord Summary Bot posts per-phase summaries ──► SUMMARY channel
  Discord Command Bot receives commands ◄── !mad run / !mad status / ...
```

## Key Design Principles

- **Generator-Evaluator pattern**: The Reviewer always runs in a fresh context with no session history, preventing self-confirmation bias. Based on [Anthropic's harness design](https://www.anthropic.com/engineering/harness-design-long-running-apps).
- **Per-ticket sprints**: Each ticket gets its own `claude -p` call with fresh context, avoiding context exhaustion on large projects. A verifier checks build/tests after each sprint.
- **File-based communication**: All state passes through files (tickets, research, refinement lists), not session history. Every agent works correctly even after a crash and cold restart.
- **Diff-aware reviews**: On iteration 2+, the reviewer sees a `git diff` of what changed, focusing verification on fixes instead of re-reading everything.
- **Structured scoring**: Review scores are extracted via `--json-schema` for deterministic pass/fail decisions. Regex fallback for robustness.
- **Evolution with validation**: Cross-project learnings are tracked alongside metrics. Learnings that correlate with declining scores get flagged for removal.
- **Multi-persona brainstorm**: Optional `--brainstorm` mode runs configurable persona-agents through N rounds of structured debate before planning. 16 personas available (5 default), selectable via `--brainstorm-personas`.
- **Adaptive E2E testing**: The Reviewer auto-detects project type (web, CLI, API, library, desktop, mobile) and uses Playwright browser automation for web apps, Bash-based functional testing for CLIs/APIs, and build verification for other types.

## Prerequisites

- **Python 3.10+**
- **Claude Code CLI** installed and authenticated (`claude` must be available in your PATH)
  - [Claude Code installation guide](https://docs.anthropic.com/en/docs/claude-code)
  - You need an active **Claude Pro**, **Max**, or **API** plan
- **Git**
- Python packages: `click` and `rich` (installed automatically if using pip)
- **Optional**: `discord.py>=2.3` for the Discord command bot (`pip install mad[discord]`)

## Installation

### Option A: pip install (recommended)

```bash
git clone https://github.com/<your-username>/multi-agent-dev.git
cd multi-agent-dev
pip install -e .

# With Discord bot support:
pip install -e ".[discord]"
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

# With multi-persona brainstorm before planning
mad run ./my-project "A real-time chat app" --brainstorm

# Or select a project first, then run commands without repeating args
mad select my-project
mad run
```

When you run `mad run` with a new project directory and idea, the project is **automatically registered and set as active** — no separate `mad select` needed.

## Commands

### `mad run` — Full pipeline

```bash
mad run [project_dir] ["<idea>"] [OPTIONS]

# Options:
#   -n, --max-iterations INTEGER   Max review<->fix cycles [default: from settings, fallback 10]
#   --pass-score FLOAT             Score to auto-approve [default: from settings, fallback 9.0]
#   --budget FLOAT                 Per-call budget in USD [default: from settings]
#   --brainstorm                   Run multi-persona brainstorm before planning
#   --brainstorm-personas TEXT     Comma-separated persona names (e.g., 'architect,cto,ai-engineer')
#   --brainstorm-rounds INTEGER    Number of brainstorm rounds [default: 3]
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
mad run ./my-app "A task manager" --brainstorm
mad run ./ml-app "An ML pipeline" --brainstorm --brainstorm-personas architect,ai-engineer,mlops,cto --brainstorm-rounds 5
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

### `mad review` — Review/fix loop

```bash
mad review [project_dir] ["<idea>"] [-i ITERATIONS] [--pass-score FLOAT]
```

Runs up to N iterations of review → fix → review → ... until approved or max reached. Iteration numbering **continues from previous runs** — if you already ran 10 iterations, `mad review -i 5` runs iterations 11–15.

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
mad tokens              # Show cumulative token usage for active project
mad personas            # List all available brainstorm personas
```

### Agent Registry

```bash
mad agents              # List all agents with their roles, tools, and models
mad agents <name>       # Show full details of a specific agent (e.g., mad agents CODER)
```

Agents can be customized via `agent_overrides` in `settings.json`:

```json
{
  "agent_overrides": {
    "CODER": {
      "tools": "Read,Edit,Write,Bash,Grep,Glob,WebSearch"
    }
  }
}
```

### Configuration

```bash
mad set-model --planner opus --coder sonnet --reviewer opus
mad set-model --all opus
mad set-model --pass-score 8.5
mad set-model --max-iterations 5
mad get-model           # Show current defaults
```

Settings are saved to `settings.json` and apply to all future runs. Override per-run with CLI flags.

### Discord Bot

```bash
mad bot                 # Start the Discord command bot (foreground)
mad bot --daemon        # Start in background
```

See [Discord Integration](#discord-integration) for full setup.

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

# 5. Review — build, test, evaluate (iterative review↔fix loop)
mad review -i 5

# 6. Finalize — write README and capture learnings
mad finalize

# 7. Check token usage
mad tokens
```

## Project Structure

```
multi-agent-dev/
├── bin/mad                        # CLI entry point
├── pyproject.toml                 # Package metadata
├── README.md
│
├── mad/                           # Python package
│   ├── __init__.py                # Version
│   ├── cli.py                     # Click commands (run, plan, code, review, fix, etc.)
│   ├── config.py                  # RunConfig, paths, tool permissions, settings
│   ├── console.py                 # Thread-safe Rich terminal output
│   ├── runner.py                  # Core agent runner (claude -p), cost tracking
│   ├── state.py                   # Run state persistence for crash recovery
│   ├── projects.py                # Multi-project registry
│   ├── tickets.py                 # Ticket parser with dependency graph
│   ├── costs.py                   # Per-run cost tracking
│   ├── metrics.py                 # Cross-project metrics for evolution validation
│   ├── summary.py                 # Discord summary bot (per-phase summaries)
│   ├── agent_registry.py          # Centralized agent definitions and overrides
│   ├── i18n.py                    # Internationalization (Korean, English, Chinese)
│   ├── discord_webhook.py         # Discord webhook integration (live streaming)
│   ├── discord_bot.py             # Discord command bot (receive commands via Discord)
│   ├── project_detect.py           # Auto-detect project type for adaptive testing
│   └── agents/
│       ├── brainstorm.py          # Multi-persona brainstorm (16 personas, configurable rounds)
│       ├── planner.py             # 4-step: rules → domain research → tech research → tickets
│       ├── coder.py               # Per-ticket sprints with self-verification
│       ├── reviewer.py            # Adaptive E2E testing + structured scoring
│       └── finalizer.py           # README generation + evolution with metrics
│
├── rules/                         # Coding rules (shared across projects)
│   ├── general_coding_rules.md    # Base principles (all languages)
│   └── rules_*.md                 # Auto-generated per stack
│
├── projects/                      # Per-project data
│   └── <project-slug>/
│       ├── specs/                 # Tickets, research, refinement lists, review logs, state
│       │   └── brainstorm/        # Brainstorm round outputs and consensus (if --brainstorm)
│       └── logs/                  # Agent logs (JSON + human-readable .md)
│
├── evolution/                     # Cross-project (shared)
    ├── learnings.md               # Master learnings file (validated over time)
    ├── metrics.json               # Score history for trend analysis
    └── epoch_<run_id>.md          # Per-run analysis
```

## Brainstorm Mode

The optional `--brainstorm` flag runs a multi-persona debate before the planning phase. 16 personas are available (5 run by default), and you can select specific ones with `--brainstorm-personas`.

### Default Personas (run with `--brainstorm`)

| Persona | Focus |
|---------|-------|
| **Architect** | System design, scalability, clean separation of concerns |
| **Pragmatist** | Shipping fast, MVPs, practical trade-offs |
| **Security Expert** | Attack surfaces, authentication, OWASP Top 10 |
| **UX Advocate** | User experience, accessibility, information architecture |
| **DevOps Engineer** | CI/CD, deployment, monitoring, infrastructure |

### Additional Personas (opt-in via `--brainstorm-personas`)

| Persona | Focus |
|---------|-------|
| **AI Engineer** | ML model integration, LLM APIs, vector databases, RAG pipelines |
| **CTO** | Technical strategy, build-vs-buy, tech debt, stakeholder communication |
| **MLOps** | ML pipelines, model versioning, experiment tracking, GPU infrastructure |
| **Performance Engineer** | Profiling, caching, database optimization, load testing |
| **Data Engineer** | Data modeling, ETL pipelines, schema design, migrations |
| **QA Strategist** | Testing strategy, automation, edge cases, regression prevention |
| **Accessibility Expert** | WCAG compliance, screen readers, keyboard navigation |
| **API Designer** | REST/GraphQL design, versioning, pagination, error contracts |
| **Mobile Specialist** | Mobile UX, offline-first, push notifications, platform conventions |
| **Domain Expert** | Business logic, regulatory compliance, domain-driven design |
| **Cost Optimizer** | Cloud costs, resource sizing, serverless trade-offs |

Run `mad personas` to see the full list with details.

### Rounds

The brainstorm runs in **N rounds** (default 3, configurable via `--brainstorm-rounds`):

1. **Round 1** (parallel): Each persona independently analyzes the idea
2. **Rounds 2..N-1** (parallel per round): Each persona reads all previous outputs, critiques and synthesizes
3. **Round N**: A Facilitator merges all perspectives into a consensus document

More rounds = deeper debate. Minimum 2 (independent analysis + consensus).

The consensus document is then used by the Planner for tech stack selection and ticket generation.

```bash
# Default: 5 personas, 3 rounds
mad run ./my-app "A healthcare patient portal" --brainstorm

# Custom: pick specific personas for an ML project
mad run ./ml-app "A recommendation engine" --brainstorm --brainstorm-personas architect,ai-engineer,mlops,data-engineer,cto

# All personas with 5 rounds of debate
mad run ./my-app "A fintech platform" --brainstorm --brainstorm-personas all --brainstorm-rounds 5
```

## Planner Pipeline

The Planner runs 4 steps before any code is written:

1. **Tech Stack & Coding Rules** — Analyzes the idea, picks a stack, generates framework-specific coding rules (or reuses existing ones). Uses brainstorm consensus if available.
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

## Reviewer: Adaptive E2E Testing & Structured Scoring

The Reviewer **auto-detects the project type** and adapts its testing strategy:

| Project Type | Detection | Testing Strategy |
|---|---|---|
| **Web (fullstack/frontend/backend)** | React, Vue, Next.js, Express, FastAPI, etc. | Playwright browser automation: navigate pages, fill forms, click buttons, take screenshots, monitor network requests and console errors |
| **CLI** | click, argparse, typer, clap | Bash functional testing: run commands, verify exit codes, test error cases |
| **Library** | setup.py, package exports | Run test suite, verify imports |
| **Desktop** | Electron, Tauri | Build verification + Playwright for Electron web views |
| **Mobile** | React Native, Flutter | Build verification |

For web projects, the reviewer is granted **Playwright MCP tools** (`browser_navigate`, `browser_click`, `browser_fill_form`, `browser_take_screenshot`, etc.) and performs real browser-based E2E testing. Screenshots are saved to `{project_dir}/screenshots/`.

The Reviewer evaluates against these criteria (each scored 0-10):

| Criterion | What it checks |
|---|---|
| Ticket compliance | Were all acceptance criteria met? |
| Functionality | Does the project build, start, and serve requests? |
| Code quality | Follows coding rules? Clean structure? Error handling? |
| Doc compliance | Used correct APIs/versions from research.md? |
| Domain compliance | Regulatory requirements implemented? (if applicable) |
| Integration | API routes, CORS, ports, env vars consistent across components? (if multi-component) |
| Security | No hardcoded secrets? Input validation? OWASP risks? |
| Testing | Tests present, passing, covering critical paths? |
| UI quality | Unique/artistic yet usable? Verified via Playwright for web projects |
| DX | Can a new developer clone, install, and run it? |

Scores are extracted via `--json-schema` for deterministic parsing. The overall score determines pass/fail against the configurable threshold (default: 9.0/10).

On iteration 2+, the reviewer receives a `git diff` showing exactly what the Coder changed, so it can focus verification on the fixes.

## Evolution System

MAD improves across projects:

1. After each run, the **Evolution agent** analyzes review logs and produces an epoch report
2. It updates `evolution/learnings.md` with role-specific insights (Planner, Coder, Reviewer)
3. **Metrics validation**: scores are tracked in `evolution/metrics.json`. The evolution agent compares trends — learnings that correlate with declining scores get flagged as "suspect," while those correlated with improvement are marked "validated"
4. All agents read the learnings file on future runs

## Token Tracking

Every `claude -p` call's input and output token counts are tracked automatically. At the end of each command, MAD prints a summary:

```
TOKENS: input - 1,234,567 / output - 456,789
```

Token usage is accumulated per-project across runs:

```bash
# View cumulative token usage for the active project
mad tokens

# View for a specific project
mad tokens my-project
```

The `mad tokens` command shows per-run breakdowns and cumulative totals (input/output).

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
| Brainstorm | Brainstorm phase |
| Planning | Plan phase |
| Coding (ticket N) | Ticket N (skips 0 to N-1) |
| Review (iteration N) | Review iteration N |
| Fix (iteration N) | Fix for iteration N |
| Finalization | Finalization |

## Agent Registry

MAD includes a centralized agent registry that defines all agents, their tools, and their roles. View it with:

```bash
mad agents
```

| Agent | Phase | Tools | Description |
|-------|-------|-------|-------------|
| PLANNER-RULES | plan | Read,Grep,Glob,Write,WebSearch,WebFetch,Skill | Tech stack analysis & coding rules |
| PLANNER-DOMAIN | plan | Read,Grep,Glob,Write,WebSearch,WebFetch,Skill | Domain-specific compliance research |
| PLANNER-RESEARCH | plan | Read,Grep,Glob,Write,WebSearch,WebFetch,Skill | Official documentation research |
| PLANNER-SPOTCHECK | plan | Read,Grep,Glob,Write,WebSearch,WebFetch,Skill | Research claim verification |
| PLANNER-TICKETS | plan | Read,Grep,Glob,Write,WebSearch,WebFetch,Skill | Ticket generation |
| CODER | code | Read,Edit,Write,Bash,Grep,Glob | Per-ticket implementation |
| CODER-FIX | code | Read,Edit,Write,Bash,Grep,Glob | Fix mode (post-review) |
| VERIFIER | code | Read,Bash,Grep,Glob,Skill | Build & test verification |
| REVIEWER | review | Read,Bash,Grep,Glob,Write,Skill | Structured scoring (9 criteria) |
| FINALIZER | finalize | Read,Write,Grep,Glob | README generation |
| EVOLUTION | evolution | Read,Write,Grep,Glob | Cross-project learnings |

Override agent tools via `agent_overrides` in `settings.json` for customization without modifying source code.

## Configuration

### Settings

```bash
mad set-model --planner opus --coder sonnet --reviewer opus
mad set-model --pass-score 8.5
mad set-model --max-iterations 5
mad set-model --budget 5.0
mad get-model
```

Settings are saved to `settings.json` and apply to all future runs. Override per-run with CLI flags.

### Full `settings.json` Reference

```json
{
  "models": {
    "planner": "opus",
    "coder": "sonnet",
    "reviewer": "opus"
  },
  "pass_score": 9.0,
  "max_iterations": 10,
  "budget_usd": 0,
  "fallback": "codex",
  "language": "en",
  "webhooks": {
    "PLANNER": "https://discord.com/api/webhooks/...",
    "CODER": "https://discord.com/api/webhooks/...",
    "REVIEWER": "https://discord.com/api/webhooks/...",
    "VERIFIER": "https://discord.com/api/webhooks/...",
    "FINALIZER": "https://discord.com/api/webhooks/...",
    "SUMMARY": "https://discord.com/api/webhooks/..."
  },
  "discord_bot_token": "YOUR_BOT_TOKEN",
  "discord_command_channel_id": "CHANNEL_ID",
  "agent_overrides": {
    "CODER": {
      "tools": "Read,Edit,Write,Bash,Grep,Glob,WebSearch"
    }
  }
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MAD_HOME` | Directory where MAD stores projects, rules, and evolution data | The cloned repo directory |

### Customization

- **Edit `rules/general_coding_rules.md`** to change base coding principles
- **Edit generated `rules/rules_*.md`** to adjust stack-specific conventions
- **Edit `projects/<slug>/specs/tickets.md`** after `mad plan` to adjust tickets before coding
- **Edit `evolution/learnings.md`** to seed the system with your own learnings
- **Override agent tools** via `agent_overrides` in `settings.json`

## Discord Integration

MAD has two Discord integration modes: **webhook streaming** (send-only, real-time agent output) and **command bot** (bidirectional, receive commands via Discord).

### Webhook Streaming (Live Agent Output)

Configure per-agent webhook URLs in `settings.json`:

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

### Summary Bot (Per-Phase Summaries)

Add a `SUMMARY` webhook to get clean per-phase summaries in a dedicated channel:

```json
{
  "webhooks": {
    "SUMMARY": "https://discord.com/api/webhooks/..."
  }
}
```

The summary bot posts after each pipeline phase completes, including:
- Phase name and duration
- Key outcomes (tickets created, review scores, issues found)
- Cost per phase

### Command Bot (Receive Commands via Discord)

The command bot lets you control MAD from Discord. It supports multilingual responses (English, Korean, Chinese).

#### Step 1: Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** in the top right
3. Give it a name (e.g., `MAD Bot`) and click **Create**
4. You'll land on the **General Information** page — you can optionally upload an icon and add a description

#### Step 2: Create the Bot User

1. In the left sidebar, click **"Bot"**
2. Click **"Add Bot"** → confirm with **"Yes, do it!"**
3. Under the bot's username, click **"Reset Token"** → confirm
4. **Copy the token** — you'll need this for `settings.json`. This is the only time you'll see it; if you lose it, you'll need to reset it again.

> **Keep this token secret.** Anyone with the token can control your bot. Never commit it to git.

#### Step 3: Enable Required Intents

Still on the **Bot** page, scroll down to **Privileged Gateway Intents**:

1. Enable **"Message Content Intent"** — the bot needs this to read `!mad` commands
2. (Optional) Enable **"Server Members Intent"** if you want the bot to see member info
3. Click **"Save Changes"**

#### Step 4: Generate an Invite URL and Add the Bot to Your Server

1. In the left sidebar, click **"OAuth2"** → **"URL Generator"**
2. Under **Scopes**, check: `bot`
3. Under **Bot Permissions**, check:
   - **Send Messages**
   - **Read Messages/View Channels**
   - **Read Message History**
   - **Embed Links** (for formatted responses)
4. Copy the **Generated URL** at the bottom
5. Open the URL in your browser → select your Discord server → click **"Authorize"**

The bot should now appear in your server's member list (offline until you start it).

#### Step 5: Get the Command Channel ID

1. In Discord, go to **User Settings** (gear icon) → **Advanced** → enable **"Developer Mode"**
2. Right-click the channel where you want the bot to listen for commands
3. Click **"Copy Channel ID"**

#### Step 6: Install the Discord Dependency

```bash
# If you installed MAD via pip:
pip install -e ".[discord]"

# Or install discord.py separately:
pip install "discord.py>=2.3"
```

#### Step 7: Configure MAD

Run `mad init` to generate a settings template (if you haven't already), then edit `settings.json`:

```json
{
  "discord_bot_token": "MTIzNDU2Nzg5MDEyMzQ1Njc4OQ.XXXXXX.XXXXXXXXXXXXXXXXXXXXXXXXXX",
  "discord_command_channel_id": "1234567890123456789",
  "language": "en"
}
```

| Key | Value |
|-----|-------|
| `discord_bot_token` | The bot token you copied in Step 2 |
| `discord_command_channel_id` | The channel ID you copied in Step 5 |
| `language` | `"en"` (English), `"ko"` (Korean), or `"zh"` (Chinese) |

#### Step 8: Start the Bot

```bash
# Foreground (see logs in terminal, Ctrl+C to stop):
mad bot

# Background (runs as a daemon):
mad bot --daemon
```

You should see:
```
[OK] MAD Bot connected as MAD Bot#1234
[OK] Listening for commands in #mad-commands
```

#### Using the Bot

Type commands in the configured Discord channel:

**Pipeline control:**

| Command | Description |
|---------|-------------|
| `!mad run <dir> "<idea>" [--brainstorm]` | Start a full pipeline run |
| `!mad resume` | Resume an interrupted run |
| `!mad stop` | Stop the current pipeline |

**Remote supervision:**

| Command | Description |
|---------|-------------|
| `!mad status` | Show project status, phase, iteration, completed tickets |
| `!mad review-results` | Show latest review scores and the full refinement list |
| `!mad tickets` | Show the current ticket list |

**Directing fixes:**

| Command | Description |
|---------|-------------|
| `!mad fix` | Run fix with the existing refinement list |
| `!mad fix "fix the auth middleware"` | Run fix with your own custom instructions |
| `!mad reject "API routes don't match spec"` | Reject with your feedback, then auto-run fix |
| `!mad approve` | Manually approve and skip to finalization |
| `!mad rerun-ticket 3` | Re-implement a specific ticket from scratch |

**Settings:**

| Command | Description |
|---------|-------------|
| `!mad set-language <ko\|en\|zh>` | Change response language |
| `!mad help` | Show all commands |

**Examples:**

```
!mad run ./my-app "A REST API for a bookstore with search and reviews"
!mad run ./chat-app "Real-time chat with rooms" --brainstorm
!mad status
!mad review-results
!mad fix "the JWT token validation is missing expiry check, and the /users endpoint returns 500"
!mad reject "ticket 4 acceptance criteria not met — search doesn't support filtering by author"
!mad approve
!mad rerun-ticket 3
!mad set-language ko
```

#### Troubleshooting

| Problem | Solution |
|---------|----------|
| Bot appears offline | Make sure `mad bot` is running and the token is correct |
| Bot doesn't respond | Check that `discord_command_channel_id` matches the channel you're typing in. Enable Developer Mode to verify the ID. |
| "Message Content Intent" error | Go back to Step 3 and enable the intent in the Developer Portal |
| `ImportError: discord` | Run `pip install "discord.py>=2.3"` or `pip install -e ".[discord]"` |
| Bot responds but pipeline fails | The MAD CLI must be installed in the same environment where `mad bot` runs. Check that `mad --version` works. |

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
| Brainstorm | Read, Grep, Glob, Write, WebSearch, WebFetch | Persona analysis + consensus writing. |
| Coder | Read, Edit, Write, Bash, Grep, Glob | Full implementation capabilities. |
| Verifier | Read, Bash, Grep, Glob, Skill | Build + test only. Skills for specialized checks. |
| Reviewer | Read, Bash, Grep, Glob, Write, Skill + Playwright (web) | Test + write reports. Playwright browser tools added for web projects. |
| Finalizer | Read, Write, Grep, Glob | Write README + learnings. No Bash needed. |

Tool permissions can be overridden per-agent via `agent_overrides` in `settings.json`.

## Skills Integration

Agents with the `Skill` tool can invoke Claude Code skills at runtime. Skills are modular capability packages installed at `~/.claude/skills/` or via plugins. Claude decides whether to invoke a skill based on task relevance — no manual triggering needed.

**How it works:**

1. Every installed skill's metadata (name + description) is loaded into the agent's context
2. If the agent's task matches a skill's description, it invokes the `Skill` tool automatically
3. The full skill instructions are injected only on invocation (progressive disclosure)

**Example:** If the `frontend-design` plugin is installed, the Planner will automatically invoke it when designing a web frontend — producing higher-quality UI code without any prompt changes.

Skills are available to Planner, Reviewer, and Verifier. The Coder and Finalizer operate without skills to keep their tool surface minimal and focused.

## Limitations

- **Requires Claude Code CLI** — orchestrates `claude` commands; does not call the Anthropic API directly
- **Long-running** — a full `mad run` can take 30 minutes to several hours depending on project complexity
- **Token usage** — each sprint, review, and fix cycle consumes tokens; per-ticket sprints use more calls but produce better code
- **Visual testing (web only)** — Playwright browser automation is integrated for web projects (fullstack, frontend, backend). Desktop, mobile, and CLI projects rely on Bash-based testing and build verification
- **Research accuracy** — WebSearch results are spot-checked but not guaranteed; domain research should be human-reviewed for regulated industries
- **Discord bot** — requires a separate long-running process (`mad bot`); the bot dispatches commands via subprocess, so the MAD CLI must be installed in the same environment

## License

MIT
