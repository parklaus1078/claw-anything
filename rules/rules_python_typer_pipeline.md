# Coding Rules: Python 3.12+ CLI Pipeline (Typer + Pydantic v2 + Jinja2 + Playwright)

> Framework-specific rules for a multi-stage CLI pipeline that researches, generates, and renders SNS card news content.

---

## 1. Project Structure

```
sns-pipeline/
├── .env.example                # Required API keys with placeholders (no defaults for secrets)
├── .pre-commit-config.yaml     # detect-secrets hook
├── .python-version             # Pin Python version for uv
├── pyproject.toml              # uv-managed, all deps pinned to exact versions
├── uv.lock                     # Lockfile (committed to git)
├── config/
│   ├── brand.yaml              # Colors, fonts, logo, voice descriptors
│   ├── platforms.yaml          # Dimensions, safe zones, caption/hashtag limits per platform
│   └── engagement.yaml         # STEPPS triggers, posting windows, card count defaults
├── templates/                  # Jinja2 HTML templates per family
│   ├── base.html.j2            # Shared base layout
│   ├── editorial/
│   │   └── card.html.j2
│   ├── infographic/
│   │   └── card.html.j2
│   ├── narrative/
│   │   └── card.html.j2
│   └── comparison/
│       └── card.html.j2
├── assets/
│   └── fonts/                  # Bundled Pretendard / Noto Sans KR
├── src/
│   ├── __init__.py
│   ├── __main__.py             # `python -m src` entry point
│   ├── cli.py                  # Typer app definition, all commands
│   ├── pipeline.py             # Stage orchestrator, resume logic, cost tracking
│   ├── stages/
│   │   ├── __init__.py
│   │   ├── research.py         # Serper + Jina + Haiku summarization
│   │   ├── generate.py         # Sonnet content + captions + hashtags
│   │   └── render.py           # Jinja2 → HTML → Playwright screenshot → FFmpeg video
│   ├── models/                 # Pydantic v2 models — inter-stage contracts
│   │   ├── __init__.py
│   │   ├── research.py         # ResearchBundle, Source, SearchResult
│   │   ├── content.py          # ContentBundle, SlideContent, Caption, Hashtags
│   │   └── manifest.py         # RunManifest, StageStatus, CostRecord
│   ├── adapters/               # Per-platform output formatting
│   │   ├── __init__.py
│   │   ├── instagram.py
│   │   ├── x.py
│   │   ├── threads.py
│   │   └── youtube_shorts.py
│   ├── services/               # Shared infrastructure
│   │   ├── __init__.py
│   │   ├── llm.py              # Anthropic SDK wrapper, token tracking, budget enforcement
│   │   ├── search.py           # Serper.dev + Google CSE fallback
│   │   ├── crawler.py          # Jina Reader with SSRF protection
│   │   └── cache.py            # Hash-based LLM response cache
│   └── utils/
│       ├── __init__.py
│       ├── cost.py             # Token → dollar conversion, budget check
│       └── sanitize.py         # HTML stripping, length caps, prompt injection markers
├── runs/                       # Pipeline run artifacts (gitignored)
└── tests/
    ├── conftest.py
    ├── test_models/            # Pydantic model validation tests
    ├── test_stages/            # Stage-level integration tests
    ├── test_services/          # Service unit tests
    └── test_adapters/          # Platform adapter tests
```

### File Naming Rules
- All Python files: `snake_case.py`
- Jinja2 templates: `<purpose>.html.j2`
- YAML config files: `snake_case.yaml`
- One Pydantic model file per stage boundary — do not combine unrelated models
- Tests mirror `src/` structure with `test_` prefix on directories and files

---

## 2. Dependency Management (uv)

### pyproject.toml Conventions
```toml
[project]
requires-python = ">=3.12"
dependencies = [
    "anthropic==0.49.0",      # Pin exact versions for production deps
    "pydantic==2.10.0",
    "pydantic-settings==2.7.0",
    "typer==0.15.0",
    "rich==13.9.0",
    "jinja2==3.1.5",
    "playwright==1.50.0",
    "httpx==0.28.0",
    "pyyaml==6.0.2",
    "python-dotenv==1.0.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.8",
    "detect-secrets>=1.5",
]

[project.scripts]
sns-pipeline = "src.cli:app"
```

### Rules
- **Pin exact versions** for all production dependencies
- **Use ranges** (`>=`) for dev dependencies only
- **Commit `uv.lock`** — reproducible builds are mandatory
- **Run `uv sync`** after any dependency change
- **No `requirements.txt`** — `pyproject.toml` + `uv.lock` is the single source of truth
- **Check compatibility** before upgrading: run full test suite after any version bump

---

## 3. Pydantic v2 Patterns

### Model Conventions
```python
from pydantic import BaseModel, Field, model_validator
from typing import Literal

class SlideContent(BaseModel):
    """Content for a single card/slide."""
    model_config = {"frozen": True}  # Immutable by default

    slide_number: int = Field(ge=1, le=10)
    headline: str = Field(max_length=40)  # Korean char limit
    body: str = Field(max_length=200)
    layout_hint: Literal["text_heavy", "visual", "data", "quote"]
```

### Rules
- **Use `model_config` dict, NOT `class Config:`** — V1 syntax is deprecated in Pydantic v2
- **`frozen=True` by default** on all inter-stage data models (immutability)
- **Use `Field()` validators** for constraints (min/max length, ge/le, pattern)
- **Use `model_validator(mode="after")`** for cross-field validation, not `@validator`
- **Use `Literal` types** for constrained string enums (platform names, layout hints, template families)
- **All stage boundaries must be Pydantic models** — raw dicts are prohibited between stages
- **JSON serialization**: use `model.model_dump_json()` and `Model.model_validate_json()` for file I/O
- **Never use `model.dict()` or `model.parse_raw()`** — these are Pydantic v1 methods

### Inter-Stage Contracts
- `ResearchBundle`: output of Research stage, input to Generate stage
- `ContentBundle`: output of Generate stage, input to Render stage
- `RunManifest`: tracks stage completion, cost, timing, errors per run
- These models are the **single source of truth** for what data flows between stages

---

## 4. Typer CLI Patterns

### Command Structure
```python
import typer
from rich.console import Console
from rich.progress import Progress

app = typer.Typer(
    name="sns-pipeline",
    help="Automated SNS card news pipeline",
    no_args_is_help=True,
)
console = Console()

@app.command()
def run(
    topic: str = typer.Argument(help="Topic or keyword to research"),
    budget: float = typer.Option(0.50, help="Max cost per run in USD"),
    platforms: list[str] = typer.Option(
        ["instagram", "x", "threads", "youtube_shorts"],
        help="Target platforms",
    ),
    template: str | None = typer.Option(None, help="Force a template family"),
) -> None:
    """Run the full pipeline for a topic."""
    ...

@app.command()
def resume(
    run_id: str = typer.Argument(help="Run ID to resume from failure"),
) -> None:
    """Resume a failed pipeline run."""
    ...
```

### Rules
- **One `app = typer.Typer()` in `cli.py`** — all commands registered there
- **Use `typer.Argument` for required positional args, `typer.Option` for flags**
- **Type hints are the API contract** — Typer infers CLI types from them
- **Use `rich.progress.Progress`** for stage progress bars (not tqdm, not print)
- **Use `rich.console.Console`** for all user-facing output (not `print()`)
- **Exit codes**: 0 = success, 1 = pipeline error, 2 = budget exceeded, 3 = invalid input
- **No interactive prompts in pipeline mode** — all inputs via CLI args/options
- **`--dry-run` flag** on the `run` command for testing without LLM calls

---

## 5. LLM Integration (Anthropic SDK)

### Client Pattern
```python
from anthropic import Anthropic

class LLMService:
    def __init__(self, client: Anthropic, budget_remaining: float):
        self._client = client
        self._budget_remaining = budget_remaining
        self._total_cost = 0.0

    def complete(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int,
        system: str | None = None,
    ) -> str:
        # Check budget before calling
        if self._budget_remaining <= 0:
            raise BudgetExceededError(self._total_cost)

        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            system=system or "",
        )
        # Track cost
        cost = self._calculate_cost(response.usage, model)
        self._total_cost += cost
        self._budget_remaining -= cost
        return response.content[0].text
```

### Rules
- **Use `anthropic.Anthropic()` (sync), not `AsyncAnthropic()`** — pipeline is sequential, async adds complexity without benefit for V1
- **Never put API keys in LLM prompts** — use `system` parameter for instructions, `messages` for content
- **Track token usage on every call** — log input_tokens, output_tokens, cost
- **Enforce per-run budget cap** — abort immediately if exceeded, emit cost summary
- **Use Claude Haiku for summarization** (research stage), **Claude Sonnet for creative generation** (content stage)
- **Cache LLM responses**: `hash(model + system + messages_json) → response.json` in `.cache/` directory
- **Parse LLM output into Pydantic models immediately** — never pass raw LLM text to next stage
- **Retry with exponential backoff** on rate limits (429) — max 3 retries, then fail

---

## 6. Research Stage (Web Crawling)

### SSRF Protection
```python
import ipaddress
from urllib.parse import urlparse

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
]

def is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    # Resolve and check IP
    ...
```

### Rules
- **Block private IP ranges** before any HTTP request
- **Limit redirects to 2 hops** via `httpx` `max_redirects=2`
- **Set request timeouts**: 10s connect, 30s read
- **Strip HTML tags from crawled content** before passing to LLM
- **Cap input length**: max 5000 chars per source, max 10 sources per run
- **Log which search provider was used** (Serper primary → Google CSE fallback → cached)
- **Research quality scoring**: count independent sources, flag if <3 unique domains

---

## 7. Rendering (Jinja2 + Playwright)

### Jinja2 Template Rules
```python
from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html"]),  # XSS prevention
    trim_blocks=True,
    lstrip_blocks=True,
)
```

- **Always enable `select_autoescape`** — never render user/crawled content unescaped
- **Templates receive typed Pydantic model data**, not raw dicts
- **Card dimensions are defined in `platforms.yaml`**, not hardcoded in templates
- **Font paths must be absolute** in HTML for Playwright rendering
- **All text constraints enforced before template rendering** (char limits, line counts)

### Playwright Screenshot Rules
- **Use `page.screenshot(type="png", clip={"x": 0, "y": 0, "width": w, "height": h})`** for exact dimensions
- **Set viewport to match platform dimensions** before screenshot
- **Wait for fonts to load** before capturing: `page.wait_for_load_state("networkidle")`
- **One browser context per render batch**, not per card (performance)
- **Close browser context in `finally` block** — never leak browser processes

### FFmpeg Video Rules
- **Use subprocess, not a Python FFmpeg wrapper** — fewer dependencies
- **Pin codec settings**: `-c:v libx264 -pix_fmt yuv420p` for maximum compatibility
- **Crossfade transitions**: 0.5s between cards
- **Output**: MP4 container, 1080x1920 (9:16) for YouTube Shorts

---

## 8. Configuration (YAML + Environment)

### Secrets (.env)
```bash
# .env.example — NO default values for secrets
ANTHROPIC_API_KEY=
SERPER_API_KEY=
GOOGLE_CSE_API_KEY=
GOOGLE_CSE_CX=
```

### Rules
- **Secrets in `.env` only** — loaded via `python-dotenv`, never committed
- **`.env.example` has empty values** — no `change-me` placeholders (learned from past projects)
- **Application config in YAML** (`config/`) — committed to git
- **Use `pydantic-settings`** for environment variable loading with validation
- **Never fall back to a default for API keys** — fail fast if missing
- **YAML config is loaded once at startup**, not per-request

### Settings Pattern
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    anthropic_api_key: str  # No default — required
    serper_api_key: str
    google_cse_api_key: str = ""  # Optional fallback
    google_cse_cx: str = ""
    default_budget: float = 0.50
    cache_dir: str = ".cache"
```

---

## 9. Error Handling & Logging

### Logging Setup
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
```

### Rules
- **Use Python `logging` module** — not `print()`, not `rich.print()` for non-user-facing output
- **User-facing output via `rich.console.Console`** — progress bars, final summaries, errors
- **Log levels**: DEBUG for LLM prompt/response details, INFO for stage transitions, WARNING for fallback usage, ERROR for failures
- **Never log API keys or full LLM responses at INFO level** — DEBUG only
- **Structured cost logging**: every LLM call logs `{model, input_tokens, output_tokens, cost_usd}`
- **Stage failure writes partial manifest** with error details — enables `resume`

### Exception Hierarchy
```python
class PipelineError(Exception):
    """Base for all pipeline errors."""

class BudgetExceededError(PipelineError):
    """Run cost exceeded configured budget."""

class ResearchError(PipelineError):
    """Research stage failure (no results, API errors)."""

class GenerationError(PipelineError):
    """LLM content generation failure."""

class RenderError(PipelineError):
    """Screenshot or video rendering failure."""
```

- **Custom exceptions per stage** — never catch bare `Exception` in pipeline orchestrator
- **Stage errors are caught in `pipeline.py`**, which writes manifest and suggests `resume` command
- **Never silently swallow errors** — at minimum, log and re-raise

---

## 10. Testing

### Framework: pytest
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

### Rules
- **Test Pydantic models first** — validate all constraints, serialization, edge cases
- **Mock LLM calls in unit tests** — return fixture JSON, never call real API in CI
- **Integration tests use cached LLM responses** — run once with real API, cache responses, replay
- **Test each stage independently** — input a fixture Pydantic model, assert output model
- **Test adapters with snapshot testing** — platform-specific output should not change unexpectedly
- **Minimum 80% coverage on `models/` and `services/`**
- **Use `tmp_path` fixture** for any test that writes files (runs, cache, screenshots)
- **Test SSRF protection explicitly** — verify blocked IPs are rejected

### Test Naming Convention
```python
def test_<unit>_<scenario>_<expected>():
    """e.g., test_research_bundle_rejects_empty_sources"""
```

---

## 11. Run Lifecycle & Resumability

### Run Directory Structure
```
runs/<run_id>/
├── manifest.json           # RunManifest — stage status, cost, timing
├── research/
│   └── bundle.json         # ResearchBundle (Pydantic serialized)
├── content/
│   └── bundle.json         # ContentBundle
├── render/
│   ├── instagram/
│   │   ├── card_01.png
│   │   ├── card_02.png
│   │   └── ...
│   ├── x/
│   ├── threads/
│   └── youtube_shorts/
│       └── video.mp4
├── preview.html            # Auto-opened after pipeline completes
└── posting_guide.md        # Copy-paste instructions per platform
```

### Rules
- **`run_id` = `YYYYMMDD_HHMMSS_<topic_slug>`** — sortable, human-readable
- **Persist Pydantic model JSON after each stage** — enables resume from any point
- **Manifest tracks**: stage status (pending/running/completed/failed), start/end timestamps, cost per stage, error messages
- **`resume` command reads manifest**, skips completed stages, retries from failure point
- **3 consecutive failures on same stage → mark run as failed**, emit cost summary
- **`runs/` directory is gitignored** — artifacts are local only

---

## 12. Performance Patterns

- **Single Playwright browser instance** shared across all card renders in a run
- **Batch HTTP requests** for search results (Serper returns multiple results per call)
- **LLM response caching** prevents redundant API calls during development/iteration
- **Jinja2 template compilation is cached** by the Environment — no per-render overhead
- **Target: full pipeline under 3 minutes** — measure and log wall time per stage
- **Do not prematurely parallelize** — sequential stages are simpler and sufficient for V1

---

## 13. Security Checklist (V1)

- [ ] `detect-secrets` pre-commit hook installed before writing any code
- [ ] `.env` in `.gitignore` — verified with `git status` after creation
- [ ] No API keys in LLM prompts, logs (INFO level), or error messages
- [ ] SSRF protection on all outbound HTTP requests
- [ ] HTML autoescape enabled in all Jinja2 templates
- [ ] Crawled content stripped of HTML tags and length-capped before LLM input
- [ ] Per-run budget cap enforced with hard abort
- [ ] No `eval()`, `exec()`, or `subprocess` with user-controlled input
- [ ] Pydantic validation on all LLM output before use

---

## 14. Linting & Formatting

### Ruff Configuration
```toml
[tool.ruff]
target-version = "py312"
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
- **Run `ruff check --fix` and `ruff format`** before every commit
- **Type hints on all function signatures** — use `str | None` syntax (Python 3.10+ union)
- **No `# type: ignore` without an adjacent comment explaining why**

---

## 15. Anti-Patterns (Prohibited)

- **Raw dicts between pipeline stages** — use Pydantic models
- **`print()` for user output** — use `rich.console.Console`
- **`class Config:` in Pydantic models** — use `model_config` dict (v2)
- **`model.dict()` or `model.parse_raw()`** — use `model_dump()` / `model_validate_json()` (v2)
- **Async for V1** — sync is simpler, pipeline is sequential
- **Auto-publishing to any platform** — manual posting only in V1
- **Hardcoded platform dimensions** — use `platforms.yaml`
- **Single template for all platforms** — each platform gets content tailored to its norms
- **`requirements.txt`** — use `pyproject.toml` + `uv.lock`
- **Default values for API key environment variables** — fail fast if missing
- **`passlib` for any purpose** — incompatible with Python 3.13+ (crypt module removed)

---

**Version**: v1.0.0
**Last updated**: 2026-04-07
