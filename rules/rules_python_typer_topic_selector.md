# Coding Rules: Python 3.13+ Topic Selector CLI (Typer + Pydantic v2 + Anthropic SDK + httpx async)

> Framework-specific rules for a CLI tool that researches trending topics, ranks them with structured evidence, and outputs actionable topic lists for SNS card news creation.

---

## 1. Project Structure

**Consensus: start flat.** One `sources.py`, one `models.py`, one `pipeline.py`. Do NOT create Protocol-based adapters, `sources/base.py`, or separate stage files until 4+ sources exist. Refactoring cost is ~1 hour when needed.

```
topic_selector/
├── .env.example                # Required API keys with placeholders (no defaults for secrets)
├── .pre-commit-config.yaml     # ruff + gitleaks hooks
├── .python-version             # 3.13
├── pyproject.toml              # uv-managed, all deps pinned to exact versions
├── uv.lock                     # Lockfile (committed to git)
├── config/
│   ├── categories.yaml         # User-defined category definitions & source priorities
│   └── scoring.yaml            # Evidence scoring weights, thresholds, freshness decay
├── prompts/                    # Versioned LLM prompt files (v001_synthesis.txt, etc.)
│   └── v001_synthesis.txt      # Synthesis prompt — versioned, recorded in run output
├── src/
│   ├── __init__.py
│   ├── __main__.py             # `python -m src` entry point
│   ├── cli.py                  # Typer app definition, all commands
│   ├── pipeline.py             # Orchestrator: GATHER → SYNTHESIZE → OUTPUT
│   ├── models.py               # All Pydantic models (RawSignal, Evidence, TopicCandidate, TopicRecommendation, RunManifest)
│   ├── sources.py              # All data source functions (async, one function per provider)
│   ├── llm.py                  # Anthropic SDK wrapper, token tracking, budget enforcement
│   ├── cache.py                # Hash-based response cache (LLM + search)
│   ├── config.py               # Settings (pydantic-settings), YAML config loading
│   └── sanitize.py             # HTML stripping, length caps, prompt injection markers
├── runs/                       # Run artifacts (gitignored)
│   └── <date>/<category>/      # Per-run output: manifest.json, recommendations.json
└── tests/
    ├── conftest.py
    ├── test_models.py
    ├── test_sources.py
    ├── test_pipeline.py
    ├── test_llm.py
    └── fixtures/               # Cached API responses, sample YAML configs
```

### File Naming Rules
- All Python files: `snake_case.py`
- YAML config files: `snake_case.yaml`
- Prompt files: `v<NNN>_<purpose>.txt` — versioned, never overwrite
- Tests mirror `src/` structure with `test_` prefix
- One file per domain — do NOT split models across files until they exceed ~300 lines

---

## 2. Dependency Management (uv)

### pyproject.toml Conventions
```toml
[project]
name = "topic-selector"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "anthropic==0.91.0",
    "pydantic==2.12.5",
    "pydantic-settings==2.13.1",
    "typer==0.24.1",
    "rich==14.3.3",
    "httpx==0.28.1",
    "pyyaml==6.0.3",
    "python-dotenv==1.2.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=9.0",
    "pytest-asyncio>=1.0",
    "ruff>=0.15",
    "gitleaks>=8.0",
]

[project.scripts]
topic-selector = "src.cli:app"
```

### Rules
- **Pin exact versions** for all production dependencies
- **Use ranges** (`>=`) for dev dependencies only
- **Commit `uv.lock`** — reproducible builds are mandatory
- **Run `uv sync`** after any dependency change
- **No `requirements.txt`** — `pyproject.toml` + `uv.lock` is the single source of truth
- **Check compatibility** before upgrading: run full test suite after any version bump
- **Python 3.13+** — use modern syntax (`str | None`, `type` statement, etc.)
- **Run `pip-audit`** before accepting dependency updates (supply chain risk)

---

## 3. Pydantic v2 Patterns

### Core Models
```python
from pydantic import BaseModel, Field, AwareDatetime, model_validator
from typing import Literal
from datetime import datetime

class RawSignal(BaseModel):
    """A single trend signal from a data source."""
    model_config = {"frozen": True, "extra": "forbid"}

    source_name: str = Field(description="e.g., 'google_trends', 'naver_news'")
    title: str = Field(max_length=200)
    url: str | None = Field(default=None, description="Source URL if available")
    snippet: str = Field(max_length=1000)
    captured_at: AwareDatetime = Field(description="When this signal was observed")

class Evidence(BaseModel):
    """A single piece of evidence supporting topic relevance."""
    model_config = {"frozen": True, "extra": "forbid"}

    source_name: str = Field(description="e.g., 'Google Trends', 'Reddit r/AI'")
    source_url: str | None = Field(default=None, description="Direct URL to the evidence")
    summary: str = Field(max_length=500, description="Why this supports the topic")
    captured_at: AwareDatetime = Field(description="When this evidence was published/observed")
    origin: Literal["api_data", "llm_inference"] = Field(
        description="Whether this is verified API data or LLM reasoning"
    )
    credibility_score: float = Field(ge=0.0, le=1.0, description="Source reliability")

class TopicCandidate(BaseModel):
    """A candidate topic discovered and analyzed."""
    model_config = {"frozen": True, "extra": "forbid"}

    title: str = Field(max_length=100, description="Specific topic title")
    category: str = Field(description="Parent category this belongs to")
    evidence: list[Evidence] = Field(min_length=1)
    freshness: Literal["RISING", "PEAKING", "FADING", "EVERGREEN"] = Field(
        description="Trend lifecycle stage"
    )
    trending_score: float = Field(ge=0.0, le=1.0)
    virality_reason: str = Field(max_length=300, description="Why this will resonate today")
    suggested_angle: str = Field(max_length=200, description="Recommended card news angle")
    language: Literal["ko", "en", "mixed"] = Field(description="Primary language")

class TopicRecommendation(BaseModel):
    """Final ranked topic with all supporting data — output contract with sns-auto-pipeline."""
    model_config = {"frozen": True, "extra": "forbid"}

    rank: int = Field(ge=1)
    topic: TopicCandidate
    composite_score: float = Field(ge=0.0, le=1.0)
    posting_urgency: Literal["immediate", "today", "this_week"]
    competing_content_level: Literal["low", "medium", "high"]
    source_count: int = Field(ge=0, description="Number of independent sources")
    prompt_version: str = Field(description="Version of the synthesis prompt used")
```

### Rules
- **Use `model_config` dict, NOT `class Config:`** — V1 syntax is deprecated in Pydantic v2
- **`frozen=True` AND `extra="forbid"` by default** on all inter-stage data models
- **Use `Field()` validators** for constraints (min/max length, ge/le, pattern)
- **Use `model_validator(mode="after")`** for cross-field validation, not `@validator`
- **Use `Literal` types** for constrained string enums (languages, urgency levels, freshness)
- **All stage boundaries must be Pydantic models** — raw dicts are prohibited between stages
- **JSON serialization**: use `model.model_dump_json()` and `Model.model_validate_json()` for file I/O
- **Never use `model.dict()` or `model.parse_raw()`** — these are Pydantic v1 methods
- **All timestamps must be timezone-aware** — use `AwareDatetime` from Pydantic, never naive datetimes
- **Evidence must tag origin** as `api_data` or `llm_inference` — user must know what's verified

---

## 4. Typer CLI Patterns

### Command Structure
```python
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="topic-selector",
    help="Discover trending topics with structured evidence for SNS card news",
    no_args_is_help=True,
)
console = Console()

@app.command()
def discover(
    category: str = typer.Argument(help="General category (e.g., 'AI solutions', '서울 부동산')"),
    count: int = typer.Option(5, "--count", "-n", help="Number of topics to return"),
    budget: float = typer.Option(0.30, help="Max cost per run in USD"),
    language: str = typer.Option("ko", help="Output language: ko, en, mixed"),
    format: str = typer.Option("table", help="Output format: table, json, markdown"),
    detail: bool = typer.Option(False, "--detail", help="Show full evidence breakdown"),
    raw: bool = typer.Option(False, "--raw", help="Debug: show raw data + scores"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Cron mode: JSON only, no Rich"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Force fresh data"),
    pipe: bool = typer.Option(False, "--pipe", help="Output JSON for sns-auto-pipeline"),
) -> None:
    """Discover trending topics for a category with evidence."""
    ...

@app.command()
def categories() -> None:
    """List all configured categories and their search strategies."""
    ...

@app.command()
def history(
    limit: int = typer.Option(10, help="Number of recent runs to show"),
    category: str | None = typer.Option(None, help="Filter by category"),
    today: bool = typer.Option(False, "--today", help="Show today's runs only"),
) -> None:
    """Show recent discovery runs and their results."""
    ...

@app.command()
def health() -> None:
    """Validate API keys, check rate limits, report source availability."""
    ...
```

### Rules
- **One `app = typer.Typer()` in `cli.py`** — all commands registered there
- **Use `typer.Argument` for required positional args, `typer.Option` for flags**
- **Type hints are the API contract** — Typer infers CLI types from them
- **Use `rich.table.Table`** for topic list display, `rich.panel.Panel` for evidence details
- **Use `rich.console.Console`** for all user-facing output (not `print()`)
- **Rich progress display during execution**: `[1/3] Fetching Google Trends... done`, `[2/3] Naver... skipped (no API key)`
- **Exit codes**: 0 = success, 1 = pipeline error, 2 = budget exceeded, 3 = invalid input
- **No interactive prompts in pipeline mode** — all inputs via CLI args/options
- **JSON output mode (`--format json` or `--pipe`)** — must output valid JSON to stdout for piping
- **`--quiet` flag** for cron mode (JSON output only, no Rich formatting)
- **Progressive disclosure**: default is top 5 scannable in 30s; `--detail` for full evidence; `--raw` for debug
- **Never pad output with low-quality filler** — if fewer than `count` topics meet threshold, return fewer

---

## 5. Async Source Fetching (httpx)

### Concurrency Pattern
```python
import asyncio
import httpx

async def gather_signals(
    category_config: CategoryConfig,
    client: httpx.AsyncClient,
) -> list[RawSignal]:
    """Fetch trend signals from all configured sources concurrently."""
    tasks = []
    for source_name in category_config.sources:
        source_fn = SOURCE_REGISTRY.get(source_name)
        if source_fn:
            tasks.append(fetch_with_fallback(source_fn, category_config, client))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    signals: list[RawSignal] = []
    for source_name, result in zip(category_config.sources, results):
        if isinstance(result, Exception):
            logger.warning(f"Source {source_name} failed: {result}")
            continue
        signals.extend(result)
    return signals

async def fetch_with_fallback(
    source_fn,
    config: CategoryConfig,
    client: httpx.AsyncClient,
) -> list[RawSignal]:
    """Fetch from a single source with timeout and error handling."""
    try:
        return await asyncio.wait_for(source_fn(config, client), timeout=30.0)
    except asyncio.TimeoutError:
        logger.warning(f"Source timed out after 30s")
        return []
```

### Rules
- **Use `httpx.AsyncClient` for all outbound HTTP** — concurrent source fetching is non-negotiable
- **`asyncio.gather()` with `return_exceptions=True`** — one failing source must not break others
- **Pipeline-level is sync (Typer command)** — call `asyncio.run()` for the async gather phase only
- **Set timeouts on AsyncClient**: `timeout=httpx.Timeout(connect=5.0, read=30.0)`
- **Source functions are async** — each returns `list[RawSignal]` or raises on failure
- **Log which sources succeeded/failed and their response times**
- **Minimum viable run**: even if zero external sources respond, LLM-only should return lower-confidence topics

---

## 6. LLM Integration (Anthropic SDK)

### Client Pattern
```python
from anthropic import Anthropic

class LLMService:
    def __init__(self, client: Anthropic, budget_remaining: float):
        self._client = client
        self._budget_remaining = budget_remaining
        self._total_cost = 0.0

    def synthesize(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int,
        system: str | None = None,
    ) -> str:
        if self._budget_remaining <= 0:
            raise BudgetExceededError(self._total_cost)

        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            system=system or "",
        )
        cost = self._calculate_cost(response.usage, model)
        self._total_cost += cost
        self._budget_remaining -= cost
        return response.content[0].text
```

### Rules
- **Use `anthropic.Anthropic()` (sync)** — LLM calls are sequential, async adds no benefit here
- **Never put API keys in LLM prompts** — use `system` parameter for instructions, `messages` for content
- **Track token usage on every call** — log input_tokens, output_tokens, cost
- **Enforce per-run budget cap** ($0.30 default, hard abort if exceeded)
- **Single Claude Sonnet call for V1** — handles clustering, dedup, synthesis, ranking in one call
- **Add Haiku pre-filter only when** source count or signal volume justifies it (10+ sources, hundreds of signals)
- **Cache LLM responses**: `hash(model + system + messages_json) → response.json` in `.cache/`
- **Parse LLM output into Pydantic models immediately** — never pass raw LLM text to next stage
- **Retry with exponential backoff** on rate limits (429) — max 3 retries, then fail
- **LLM prompts must request structured JSON output** — parse with `model_validate_json()`

### Prompt Strategy
- **Store prompts as versioned files** in `prompts/` — record prompt version in each run's output
- **System prompt defines the role**: trending content analyst for SNS card news
- **Include current date** in every prompt — trending topics are time-sensitive
- **Request explicit evidence citations** — LLM must reference specific sources from search results
- **Ask for freshness classification** (RISING / PEAKING / FADING / EVERGREEN) per topic
- **Ask for virality reasoning** — why this topic will resonate *today*, not just generally
- **Cross-source deduplication** in prompt — "Claude 4" from Google and "클로드 4 출시" from Naver are same topic
- **Sandbox external content** with explicit delimiters and untrusted-data preamble (prompt injection protection)

---

## 7. Data Sources

### Source Function Pattern
```python
async def fetch_google_trends(
    config: CategoryConfig,
    client: httpx.AsyncClient,
) -> list[RawSignal]:
    """Fetch trending topics from Google Trends."""
    ...

async def fetch_naver_news(
    config: CategoryConfig,
    client: httpx.AsyncClient,
) -> list[RawSignal]:
    """Fetch trending news from Naver."""
    ...

# Registry — add new sources here
SOURCE_REGISTRY: dict[str, Callable] = {
    "google_trends": fetch_google_trends,
    "naver_news": fetch_naver_news,
    "serper": fetch_serper,
    "reddit": fetch_reddit,
    "rss": fetch_rss,
}
```

### Rules
- **All source functions live in `sources.py`** — flat, no base class hierarchy
- **Consistent signature**: `async def fetch_X(config, client) -> list[RawSignal]`
- **Sources return `RawSignal` (Pydantic model)** — never raw dicts
- **Source failures are logged and skipped** — one failing source must not break the pipeline
- **Graceful degradation**: pipeline must produce useful output from whatever responds
- **Set request timeouts**: 5s connect, 30s read
- **Strip HTML tags from crawled content** before passing to LLM
- **Cap input length**: max 5000 chars per source result, max 15 results per source
- **Log which sources were used and their response times**

### Source Priority by Category Type
- **Tech/AI topics**: Serper (global), Reddit, RSS (tech blogs), Google Trends
- **Korean real estate**: Naver News (discovery), Naver DataLab (validation of known keywords), Serper with Korean locale
- **General Korean trends**: Naver, Google Trends (KR), Reddit (Korean subreddits)
- **Global trends**: Serper, Google Trends, Reddit, RSS

### Important: Naver API Limitation
- **Naver DataLab has no "trending" discovery endpoint** — it requires seed keywords
- **Use Naver News trending** as the discovery source for Korean categories
- **Use Naver DataLab only** for validation of known keywords (search volume trends)

---

## 8. Evidence Scoring & Ranking

### Scoring Model (config/scoring.yaml)
```yaml
weights:
  source_diversity: 0.25       # More independent sources = higher score
  freshness: 0.25              # More recent = higher score
  search_volume_trend: 0.20    # Rising trend > steady > declining
  content_gap: 0.15            # Less existing card news content = better opportunity
  engagement_potential: 0.15   # LLM-assessed virality potential

thresholds:
  min_sources: 2               # Reject topics with fewer independent sources
  min_composite_score: 0.4     # Don't recommend topics below this
  max_age_hours: 72            # Evidence older than this gets heavily penalized
  freshness_decay_half_life_hours: 24  # Score halves every 24 hours

deduplication:
  similarity_threshold: 0.8    # Merge topics with >80% semantic similarity
```

### Rules
- **All scoring weights and thresholds live in `scoring.yaml`** — never hardcode
- **Evidence must include source URLs** when available — missing URLs are a hallucination canary
- **Freshness decay is exponential** — recent evidence scores exponentially higher
- **Record `captured_at` on every evidence item** — display evidence age, flag stale evidence
- **Deduplicate similar topics** before final ranking — LLM handles semantic similarity in synthesis
- **Each recommended topic must have evidence from 2+ independent sources** — below this, mark as low confidence
- **Scoring is deterministic given the same evidence** — no randomness in ranking
- **V1: LLM populates scores** but model includes numeric fields so deterministic scoring can replace it later
- **Output posting urgency**: "Post within 6h" / "Post today" / "This topic is fading"

---

## 9. Configuration (YAML + Environment)

### Secrets (.env)
```bash
# .env.example — NO default values for secrets
ANTHROPIC_API_KEY=
SERPER_API_KEY=
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
```

### Category Configuration (config/categories.yaml)
```yaml
categories:
  ai_solutions:
    display_name: "Latest Trending AI Solutions"
    search_queries:
      - "latest AI tool release 2026"
      - "trending AI solution this week"
      - "AI 최신 솔루션"
    sources: ["serper", "google_trends", "reddit", "rss"]
    language: "mixed"
    target_timezone: "UTC"
    rss_feeds:
      - "https://techcrunch.com/category/artificial-intelligence/feed/"

  korea_real_estate:
    display_name: "한국 부동산 트렌드"
    search_queries:
      - "서울 청약 2026"
      - "부동산 급매 지역"
      - "아파트 분양 인기 지역"
    sources: ["naver_news", "serper", "google_trends"]
    language: "ko"
    target_timezone: "Asia/Seoul"
```

### Rules
- **Secrets in `.env` only** — loaded via `python-dotenv`, never committed
- **`.env.example` has empty values** — no `change-me` placeholders
- **Application config in YAML** (`config/`) — committed to git
- **Use `pydantic-settings`** for environment variable loading with validation
- **Never fall back to a default for API keys** — fail fast if missing
- **YAML config is loaded once at startup** and validated with Pydantic models
- **Categories are user-extensible** — adding a new category is just editing YAML, no code changes
- **Each category specifies its source priority, search queries, language, and target timezone**
- **Per-category `target_timezone`** — mixing UTC and KST silently degrades data quality

### Settings Pattern
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    anthropic_api_key: str          # No default — required
    serper_api_key: str             # No default — required
    naver_client_id: str = ""       # Optional — needed for Korean categories
    naver_client_secret: str = ""
    default_budget: float = 0.30
    cache_dir: str = ".cache"
    cache_ttl_hours: int = 6        # Search cache expires after 6 hours
```

---

## 10. Error Handling & Logging

### Exception Hierarchy
```python
class TopicSelectorError(Exception):
    """Base for all topic selector errors."""

class BudgetExceededError(TopicSelectorError):
    """Run cost exceeded configured budget."""

class SearchError(TopicSelectorError):
    """Search/data source failure."""

class AnalysisError(TopicSelectorError):
    """LLM analysis failure."""

class ConfigError(TopicSelectorError):
    """Invalid configuration or missing required config."""

class InsufficientEvidenceError(TopicSelectorError):
    """Not enough evidence to recommend topics."""
```

### Logging Rules
- **Use Python `logging` module** — not `print()`, not `rich.print()` for non-user-facing output
- **User-facing output via `rich.console.Console`** — tables, panels, progress, errors
- **Structured JSON lines logging** — `logging` with JSON formatter
- **Log levels**: DEBUG for LLM prompts/responses and raw search results, INFO for stage transitions, WARNING for source fallbacks, ERROR for failures
- **Never log API keys or full LLM responses at INFO level** — DEBUG only
- **Structured cost logging**: every LLM call logs `{model, input_tokens, output_tokens, cost_usd}`
- **Stage failure writes partial manifest** with error details
- **Never silently swallow errors** — at minimum, log and re-raise
- **Chain exceptions with `from exc`** in all except blocks that re-raise

### Error UX
- **Never show raw Python tracebacks** — every error suggests a next action
- **Distinguish warnings** (source failed, continuing) **from blocking errors** (nothing worked)
- **Use color**: red for blocking errors, yellow for degraded warnings, green for success
- **"Thin results" state**: honestly report low confidence and suggest broadening category or retrying later

---

## 11. Testing

### Framework: pytest
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
```

### Rules
- **Test Pydantic models first** — validate all constraints, serialization, edge cases
- **Mock LLM calls in unit tests** — return fixture JSON, never call real API in CI
- **Mock source API calls in unit tests** — return fixture responses
- **Integration tests use cached responses** — run once with real APIs, cache, replay
- **Test each pipeline stage independently** — input a fixture Pydantic model, assert output model
- **Test scoring determinism** — same evidence in = same scores out
- **Test deduplication logic** — similar topics must merge, distinct topics must not
- **Test source failures** — verify graceful degradation when 1, 2, or all sources fail
- **Test freshness classification** — RISING/PEAKING/FADING/EVERGREEN correctly assigned
- **Minimum 80% coverage on `models.py` and `llm.py`**
- **Use `tmp_path` fixture** for any test that writes files (runs, cache)
- **Use `pytest-asyncio`** for testing async source functions

### Test Naming Convention
```python
def test_<unit>_<scenario>_<expected>():
    """e.g., test_topic_candidate_rejects_empty_evidence"""
```

---

## 12. Run Lifecycle & Caching

### Run Directory Structure
```
runs/<date>/<category>/
├── manifest.json           # RunManifest — stage status, cost, timing, prompt version, sources used
├── raw_signals.json        # RawSignal list from all sources
├── recommendations.json    # Final TopicRecommendation list
└── cost_summary.json       # Detailed cost breakdown
```

### Rules
- **Run path = `runs/<YYYYMMDD>/<category_slug>/`** — sortable, human-readable
- **Persist Pydantic model JSON after each stage** — enables debugging and auditing
- **Manifest tracks**: stage status, timestamps, cost per stage, error messages, prompt version, sources used/failed
- **`runs/` directory is gitignored** — artifacts are local only
- **Run cleanup**: entries older than 30 days (`make clean-runs`)

### Caching Strategy
- **Search results cached for `cache_ttl_hours`** (default 6h) — trending topics change fast
- **LLM responses cached by content hash** — same input = same output, save money
- **Cache key**: `SHA256(source_name + query + date_hour)` for search, `SHA256(model + system + messages)` for LLM
- **`--no-cache` flag** to force fresh data
- **Cache is per-category** — different categories don't pollute each other

---

## 13. Output Formats

### Table Output (default)
```
┌──────┬──────────────────────────────────┬───────┬──────────┬───────────┬──────────┐
│ Rank │ Topic                            │ Score │ Freshness│ Urgency   │ Sources  │
├──────┼──────────────────────────────────┼───────┼──────────┼───────────┼──────────┤
│  1   │ Gemma 4 vs Claude Opus 4         │ 0.92  │ RISING   │ immediate │ 5        │
│  2   │ OpenAI Codex Release             │ 0.85  │ PEAKING  │ today     │ 4        │
└──────┴──────────────────────────────────┴───────┴──────────┴───────────┴──────────┘
```

### Rules
- **Default format is `table`** — quick visual scan in under 30 seconds
- **`--format json` or `--pipe` outputs ONLY valid JSON to stdout** — no Rich formatting mixed in
- **Separate user-facing output (stdout) from logging (stderr)** when `--format json`
- **All formats include the same data** — just different presentations
- **`--detail` shows full evidence breakdown** per topic
- **`--raw` shows debug data**: raw signals, scores, source timing
- **Freshness urgency in output**: "Post within 6h" / "Post today" / "This topic is fading"
- **Source count and confidence visible per topic**

---

## 14. Deployment & Operations

### Scheduling
- **`crontab` for scheduled runs** — different categories may need different schedules/timezones
- **`--quiet` flag** for cron mode (JSON output only, no Rich formatting)
- **Discord webhook notification on failure** — sanitize payload, never include API keys or error details

### Operational Safety
- **File-based run lock** (`~/.topic-selector/run.lock`) — prevents concurrent cron executions
- **Auto-expire lock after 10 minutes** — prevents stale locks from blocking all runs
- **All timestamps timezone-aware** (`AwareDatetime` in Pydantic)

### Health Check
- `topic-selector health` — validate API keys, check rate limits, report source availability

---

## 15. Performance Patterns

- **Async concurrent source fetching** — calling APIs sequentially wastes 15-25s of wall time
- **Batch HTTP requests** where possible (Serper returns multiple results per call)
- **LLM + search response caching** prevents redundant API calls during development
- **Target: full discovery under 60 seconds** — measure and log wall time per stage
- **Single Sonnet call for V1** — most runs should cost under $0.10
- **Budget default is $0.30** — hard abort if exceeded

---

## 16. Linting & Formatting

### Ruff Configuration
```toml
[tool.ruff]
target-version = "py313"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "SIM", "TCH"]
ignore = ["E501"]  # Line length handled by formatter

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

### Rules
- **Ruff for both linting and formatting** — no black, no isort, no flake8
- **Run `ruff check --fix && ruff format` on ALL `src/` and `tests/` files as the LAST step before every commit** — this is a gate, not a guideline
- **Type hints on all function signatures** — use `str | None` syntax (Python 3.10+ union)
- **No `# type: ignore` without an adjacent comment explaining why**

---

## 17. Security Checklist

- [ ] `gitleaks` pre-commit hook installed before writing any code
- [ ] `.env` in `.gitignore` — verified with `git status` after creation
- [ ] No API keys in LLM prompts, logs (INFO level), or error messages
- [ ] Crawled content stripped of HTML tags and length-capped before LLM input
- [ ] External content sandboxed in LLM prompts with explicit untrusted-data delimiters
- [ ] Per-run budget cap enforced with hard abort
- [ ] Input validation on category strings: max 200 chars, Unicode NFC normalization, control char stripping
- [ ] No `eval()`, `exec()`, or `subprocess` with user-controlled input
- [ ] Pydantic `frozen=True` + `extra="forbid"` on all models
- [ ] Pydantic validation on all LLM output before use
- [ ] HTTP timeouts on all outbound requests (connect: 5s, read: 30s)
- [ ] Log sanitization — structured logs never contain API keys or full request headers
- [ ] All dependency versions pinned in `uv.lock`, periodic `pip-audit`

---

## 18. Anti-Patterns (Prohibited)

- **Raw dicts between pipeline stages** — use Pydantic models
- **`print()` for user output** — use `rich.console.Console`
- **`class Config:` in Pydantic models** — use `model_config` dict (v2)
- **`model.dict()` or `model.parse_raw()`** — use `model_dump()` / `model_validate_json()` (v2)
- **Protocol-based adapters or base classes for V1** — start flat, refactor when 4+ sources exist
- **Hardcoded search queries** — use `categories.yaml`
- **Hardcoded scoring weights** — use `scoring.yaml`
- **`requirements.txt`** — use `pyproject.toml` + `uv.lock`
- **Default values for API key environment variables** — fail fast if missing
- **`passlib` for any purpose** — incompatible with Python 3.13+ (crypt module removed)
- **Unsourced topic recommendations** — every topic must have verifiable evidence URLs
- **Single-source topics** — minimum 2 independent sources for any recommendation
- **Mixing Rich output with JSON on stdout** — when `--format json`, all non-JSON goes to stderr
- **Naive (timezone-unaware) datetimes** — always use `AwareDatetime`
- **Overwriting prompt files** — version them, never mutate existing versions
- **Sequential source fetching** — use async httpx with `asyncio.gather()`

---

## 19. Integration with sns-auto-pipeline

### Output Contract
- The `--pipe` or `--format json` output of `topic-selector discover` must be directly consumable by sns-auto-pipeline
- JSON schema matches `list[TopicRecommendation]` serialized via `model_dump_json()`
- Each recommendation includes enough context (title, angle, evidence) for card news generation without additional research
- Shared output contract validated via JSON Schema file or shared fixture files (not a shared Python package)

### Design Principle
- **Topic selector is a standalone tool** — it does NOT depend on sns-auto-pipeline code
- **Communication is via JSON on stdout** — Unix pipe philosophy
- **No shared database or state** — each tool manages its own runs/ directory
- **Integration test validates `TopicRecommendation` against pipeline's expected input**

---

**Version**: v1.1.0
**Last updated**: 2026-04-08
