# Coding Rules: Python (FastAPI) + Next.js 15 + SQLite

> Framework-specific rules for a full-stack application with a FastAPI async backend, Next.js 15 frontend, and SQLite database. Designed for personal-use tools with SSE streaming, multi-provider LLM integration, and zero-ops deployment (no Docker, no external DB).

---

## 1. Project Structure

```
project-root/
├── .env.example                    # Template for required environment variables
├── .gitignore
├── README.md
├── Makefile                        # make dev, make test, make build, make lint
│
├── backend/                        # Python FastAPI backend
│   ├── pyproject.toml              # Dependencies managed via uv (pinned versions)
│   ├── uv.lock                    # Lockfile (committed)
│   ├── alembic.ini                 # Alembic migration config
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/               # Migration files
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry, lifespan events
│   │   ├── config.py               # Settings via pydantic-settings
│   │   ├── dependencies.py         # FastAPI dependency injection
│   │   ├── api/                    # Route modules
│   │   │   ├── __init__.py
│   │   │   ├── router.py           # Top-level APIRouter aggregator
│   │   │   ├── projects.py         # Project CRUD endpoints
│   │   │   ├── personas.py         # Persona CRUD + suggestion endpoint
│   │   │   ├── sessions.py         # Session management + SSE streaming
│   │   │   ├── messages.py         # Message history endpoints
│   │   │   ├── outputs.py          # Output retrieval endpoints
│   │   │   ├── settings.py         # User settings endpoints
│   │   │   └── health.py           # Health check endpoint
│   │   ├── schemas/                # Pydantic request/response models
│   │   │   ├── __init__.py
│   │   │   ├── project.py
│   │   │   ├── persona.py
│   │   │   ├── session.py
│   │   │   ├── message.py
│   │   │   ├── output.py
│   │   │   └── common.py           # Shared schemas (pagination, errors)
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Declarative base + common mixins
│   │   │   ├── project.py
│   │   │   ├── persona.py
│   │   │   ├── session.py
│   │   │   ├── message.py
│   │   │   ├── output.py
│   │   │   └── setting.py
│   │   ├── services/               # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py     # Brainstorm orchestration engine
│   │   │   ├── output_extractor.py # Two-phase output extraction
│   │   │   ├── persona_suggester.py # Auto-suggest persona descriptions
│   │   │   └── context_manager.py  # Per-provider context window management
│   │   ├── providers/              # LLM provider adapters
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # ModelAdapter protocol
│   │   │   ├── claude.py           # Claude (Anthropic SDK) adapter
│   │   │   ├── openai.py           # OpenAI adapter
│   │   │   └── local.py            # Local model adapter (Ollama)
│   │   ├── core/                   # Cross-cutting concerns
│   │   │   ├── __init__.py
│   │   │   ├── logging.py          # Structured JSON logging via structlog
│   │   │   ├── exceptions.py       # Custom exception hierarchy
│   │   │   └── constants.py        # Application-wide constants
│   │   └── db/                     # Database layer
│   │       ├── __init__.py
│   │       ├── session.py          # AsyncSession factory, engine setup
│   │       └── repositories/       # Data access layer
│   │           ├── __init__.py
│   │           ├── project_repo.py
│   │           ├── persona_repo.py
│   │           ├── session_repo.py
│   │           ├── message_repo.py
│   │           ├── output_repo.py
│   │           └── setting_repo.py
│   └── tests/
│       ├── conftest.py             # Shared fixtures (async DB, test client)
│       ├── unit/
│       │   ├── services/
│       │   └── providers/
│       ├── integration/
│       │   ├── api/
│       │   └── db/
│       └── factories/              # Test data factories
│
├── frontend/                       # Next.js 15 frontend
│   ├── package.json
│   ├── package-lock.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── postcss.config.mjs
│   ├── components.json             # shadcn/ui configuration
│   ├── public/
│   ├── src/
│   │   ├── app/                    # App Router pages
│   │   │   ├── layout.tsx          # Root layout
│   │   │   ├── page.tsx            # Landing / project list
│   │   │   ├── globals.css         # Tailwind CSS imports
│   │   │   ├── loading.tsx
│   │   │   ├── error.tsx
│   │   │   ├── projects/
│   │   │   │   ├── new/
│   │   │   │   │   └── page.tsx    # Project setup wizard
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx    # Project detail / brainstorm
│   │   │   │       ├── chat/
│   │   │   │       │   └── page.tsx  # Live brainstorm chat
│   │   │   │       ├── outputs/
│   │   │   │       │   └── page.tsx  # Output viewer
│   │   │   │       └── history/
│   │   │   │           └── page.tsx  # Session replay
│   │   │   └── settings/
│   │   │       └── page.tsx        # Settings page
│   │   ├── components/
│   │   │   ├── ui/                 # shadcn/ui primitives
│   │   │   ├── layout/             # App shell: header, sidebar
│   │   │   ├── chat/               # Chat view components
│   │   │   │   ├── MessageList.tsx  # Virtualized message list
│   │   │   │   ├── MessageBubble.tsx
│   │   │   │   ├── MilestoneMarker.tsx
│   │   │   │   ├── TypingIndicator.tsx
│   │   │   │   └── DirectiveInput.tsx
│   │   │   ├── project/            # Project setup components
│   │   │   │   ├── ProjectWizard.tsx
│   │   │   │   └── PersonaCards.tsx
│   │   │   ├── output/             # Output viewer components
│   │   │   │   ├── FileTree.tsx
│   │   │   │   └── MarkdownPreview.tsx
│   │   │   └── settings/           # Settings components
│   │   ├── lib/
│   │   │   ├── api.ts              # API client (fetch wrapper to backend)
│   │   │   ├── sse.ts              # SSE connection manager
│   │   │   ├── utils.ts            # cn() helper, formatters
│   │   │   └── constants.ts
│   │   ├── hooks/
│   │   │   ├── use-sse.ts          # SSE subscription hook
│   │   │   ├── use-chat.ts         # Chat state management
│   │   │   └── use-settings.ts     # Settings state
│   │   ├── stores/                 # Zustand stores
│   │   │   ├── session-store.ts    # Session metadata + UI state
│   │   │   └── settings-store.ts   # Settings state
│   │   └── types/
│   │       ├── index.ts
│   │       ├── project.ts
│   │       ├── persona.ts
│   │       ├── session.ts
│   │       ├── message.ts
│   │       └── sse.ts              # SSE event type definitions
│   └── tests/
│       ├── components/
│       └── e2e/
│
└── data/                           # Runtime data (gitignored)
    └── .gitkeep
```

### File Naming Conventions
- **Backend Python**: `snake_case.py` everywhere
- **Frontend Components**: `PascalCase.tsx` (e.g., `MessageBubble.tsx`)
- **Frontend utilities/hooks/stores**: `kebab-case.ts` (e.g., `use-sse.ts`, `session-store.ts`)
- **Frontend types**: `kebab-case.ts` or `camelCase.ts` in `types/`
- **Pages**: `page.tsx` (Next.js convention)
- **API routes**: `route.ts` (Next.js convention)

---

## 2. Backend — Python FastAPI Conventions

### Python Version & Tooling
- **Python 3.13** (latest stable)
- **Package manager**: `uv` — pin exact versions in lockfile, commit `uv.lock`
- **Linter/formatter**: `ruff` (replaces black, isort, flake8)
- **Type checking**: `mypy` with strict mode
- **Task runner**: `Makefile` with standard targets

### FastAPI Patterns

#### App Initialization — Use Lifespan
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize DB, validate provider config, start structlog
    await init_db()
    validate_provider_availability()
    yield
    # Shutdown: close DB connections
    await close_db()

app = FastAPI(
    title="Brainstorm Planner API",
    version="0.1.0",
    lifespan=lifespan,
)
```

#### Dependency Injection — Always Use `Depends()`
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session

@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    ...
```

#### Route Organization
- Group routes by domain in separate files under `api/`
- Aggregate all routers in `api/router.py` with prefixes and tags
- Always set `response_model` explicitly
- Use status codes from `fastapi.status` constants

#### Pydantic Models (Schemas)
- Separate `schemas/` (API contracts) from `models/` (ORM)
- Use `model_config = ConfigDict(from_attributes=True)` for ORM-to-schema conversion
- All request bodies must use Pydantic models — never accept raw dicts
- Use `Field()` with descriptions for auto-generated API docs
- Use Pydantic V2 patterns: `model_dump_json()`, `model_validate_json()`, `ConfigDict(frozen=True)` for immutable schemas

### Async Everywhere
- All I/O operations must be async (database, HTTP calls, file operations)
- Use `httpx.AsyncClient` for outbound HTTP (LLM provider APIs)
- Use `aiosqlite` driver via SQLAlchemy async engine
- Never use synchronous `requests` in async routes
- For CPU-bound work, use `asyncio.to_thread()`

### SSE Streaming Pattern (Validated: Run 9)
```python
from fastapi.responses import StreamingResponse

@router.get("/sessions/{session_id}/stream")
async def stream_brainstorm(session_id: str, db: AsyncSession = Depends(get_db)):
    async def event_generator():
        async for event in orchestrator.run(session_id):
            yield f"data: {event.model_dump_json()}\n\n"
        yield "data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```
- Return the `StreamingResponse` immediately — do NOT await the generator
- Use `force-dynamic` on the Next.js page that consumes SSE
- Every message committed to SQLite BEFORE yielding to SSE

### Error Handling
```python
# core/exceptions.py
class AppError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code

class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(f"{resource} {resource_id} not found", 404)

class ProviderError(AppError):
    def __init__(self, provider: str, detail: str):
        super().__init__(f"Provider {provider} error: {detail}", 502)

class SessionCapError(AppError):
    def __init__(self, cap_type: str, limit: int):
        super().__init__(f"Session {cap_type} limit ({limit}) exceeded", 429)

# Register global handler in main.py
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
```
- Chain exceptions with `from exc` in all except blocks that re-raise
- Never silently catch and discard exceptions

---

## 3. LLM Provider Adapter Pattern

### Model Adapter Protocol (Consensus Minimal)
```python
from typing import AsyncIterator, Protocol

class ModelAdapter(Protocol):
    async def chat(
        self,
        messages: list[dict],
        system_prompt: str,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream text chunks from the model."""
        ...

    @property
    def max_context_tokens(self) -> int:
        """Maximum context window size for this provider."""
        ...
```

### Key Rules
- **Providers are "dumb inference pipes"** — `chat(messages, system_prompt) -> stream[str]`
- **All orchestration logic lives in `services/orchestrator.py`**, NOT in provider adapters
- Each adapter handles its own: authentication, retries (3 attempts, exponential backoff: 1s, 4s, 16s), timeouts (90s default), error mapping
- Adapters live in `providers/` directory, one file per provider
- The `ModelAdapter` protocol has exactly two members — do NOT add more until a real use case demands it
- Context window management is handled by `services/context_manager.py`, NOT by adapters
- Provider selection is explicit — NO auto-fallback chain

### Provider Implementation Pattern
```python
# providers/claude.py
import anthropic

class ClaudeAdapter:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def chat(
        self,
        messages: list[dict],
        system_prompt: str,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    @property
    def max_context_tokens(self) -> int:
        return 200_000
```

### Do NOT
- Import or depend on any SDK's orchestration layer (tool routing, handoffs, agent loops)
- Add `get_capabilities()` or other introspection methods until Phase 3+
- Implement auto-fallback between providers
- Store API keys in the database — env vars only

---

## 4. Database — SQLite + SQLAlchemy Async

### Why SQLite
- Personal tool, single user, zero-ops
- No external database server required
- File-based, easy to backup
- WAL mode for concurrent read/write

### SQLAlchemy Async Setup
```python
# db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

DATABASE_URL = "sqlite+aiosqlite:///data/brainstorm.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA foreign_keys=ON"))
```

### ORM Models — SQLAlchemy 2.0 Style
```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    goal: Mapped[str]
    # Use Mapped[type] annotations for ALL columns
```

### Key Rules
- Use SQLAlchemy 2.0 style: `select()` not `query()`, `Mapped`/`mapped_column`
- All queries in `db/repositories/` — never query directly in routes or services
- Repositories accept `AsyncSession` via DI
- Every schema change goes through Alembic migrations
- Include both `upgrade()` and `downgrade()` in every migration

### SQLite-Specific Rules
- Enable WAL mode on startup (concurrent reads during writes)
- Enable foreign keys on startup (`PRAGMA foreign_keys=ON`)
- Use `TEXT` for UUIDs (SQLite has no native UUID type)
- Use `INTEGER` with `mode: "timestamp"` for timestamps
- `.gitignore` must include `*.db`, `*.db-wal`, `*.db-shm`
- Store the database file in `data/` directory
- Use `sequence_num INTEGER NOT NULL` for message ordering — total ordering is critical for conversation replay

---

## 5. Frontend — Next.js 15 + Tailwind CSS v4

### Versions & Config
- **Next.js 15** (App Router only)
- **React 19**
- **Node.js 22 LTS**
- **TypeScript 5.7+** with `strict: true`
- **Tailwind CSS v4** — use `@import "tailwindcss"` and `@theme` directive, NOT v3 `tailwind.config.js`

### App Router Conventions
- Default to **Server Components** — only add `"use client"` when interactivity is needed
- Use `loading.tsx` for Suspense fallbacks
- Use `error.tsx` for error boundaries (must be `"use client"`)
- `params` is a Promise in Next.js 15 — must `await` it
- Use `force-dynamic` export on pages consuming SSE streams

### Next.js 15-Specific Patterns
```tsx
// params must be awaited in Next.js 15
export default async function ProjectPage(
  props: { params: Promise<{ id: string }> }
) {
  const { id } = await props.params;
  // ...
}
```

### State Management
- **Zustand** for session metadata and UI state (not message content)
- **SSE-driven append** for message list — managed directly by react-virtuoso
- Do NOT store 50K+ tokens of messages in a reactive Zustand store
- Use selector-based subscriptions to avoid unnecessary re-renders

```typescript
// stores/session-store.ts
import { create } from "zustand";

interface SessionState {
  sessionId: string | null;
  status: "idle" | "active" | "paused" | "completed" | "failed";
  currentPhase: string | null;
  setSession: (id: string) => void;
  setStatus: (status: SessionState["status"]) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  sessionId: null,
  status: "idle",
  currentPhase: null,
  setSession: (id) => set({ sessionId: id }),
  setStatus: (status) => set({ status }),
}));
```

### SSE Client Pattern
```typescript
// lib/sse.ts
export function connectSSE(
  url: string,
  onMessage: (event: SSEEvent) => void,
  onError: (error: Event) => void,
): EventSource {
  const source = new EventSource(url);
  source.onmessage = (e) => {
    const event: SSEEvent = JSON.parse(e.data);
    onMessage(event);
  };
  source.onerror = onError;
  return source;
}
```

### Chat View — Virtualized Rendering (Mandatory)
- Use **react-virtuoso** for the message list — mandatory for 1000+ messages without memory blowup
- Auto-scroll by default, pause on user scroll-up, show "Jump to latest" pill
- Per-agent visual identity: unique color + name label per persona
- Milestone markers as visual dividers at phase transitions

### Markdown Rendering
- Use **react-markdown** + **rehype-sanitize** + **rehype-highlight**
- Always sanitize agent-generated Markdown before rendering
- Generated HTML specs rendered in `sandbox` iframe (no `allow-scripts`) or as source code only

### Styling with Tailwind CSS v4
```css
/* src/app/globals.css */
@import "tailwindcss";

@theme {
  --font-sans: "Inter", "Noto Sans", system-ui, sans-serif;
  --color-primary: #2563eb;
  --color-primary-foreground: #ffffff;
}
```
- Use `@import "tailwindcss"` — NOT v3 `@tailwind base/components/utilities`
- Use `@theme` directive for design tokens — NOT `tailwind.config.js`
- Use `cn()` helper from `clsx` + `tailwind-merge` for conditional classes
- Extract repeated utility combinations into components, not `@apply`

### Recommended Frontend Libraries
| Library | Purpose |
|---------|---------|
| `shadcn/ui` | Accessible UI component primitives (copy-paste, not dependency) |
| `zustand` | State management (session/UI state only, NOT messages) |
| `react-virtuoso` | Virtualized scrolling for chat (mandatory) |
| `react-markdown` | Markdown rendering |
| `rehype-sanitize` | XSS prevention on rendered Markdown |
| `rehype-highlight` | Code syntax highlighting |
| `zod` | Schema validation |
| `react-hook-form` + `@hookform/resolvers` | Form handling with Zod |
| `lucide-react` | Icons |
| `sonner` | Toast notifications |
| `vitest` + `@testing-library/react` | Unit/component testing |
| `playwright` | E2E testing |

### Do NOT Use
- `axios` — use native `fetch`
- `styled-components` / `emotion` — use Tailwind CSS
- `socket.io` / `ws` — use SSE (EventSource)
- `framer-motion` — if animation needed, use `motion/react` (Motion v12, NOT `framer-motion`)
- `@tanstack/react-query` — unnecessary for SSE-driven data; use Zustand + fetch for simple CRUD

---

## 6. API Communication

### Frontend → Backend
- Backend runs on `http://127.0.0.1:8000`
- Frontend runs on `http://localhost:3000`
- API client in `lib/api.ts` wraps `fetch` with base URL and error handling
- SSE connections use `EventSource` to `http://127.0.0.1:8000/api/sessions/{id}/stream`

### API Response Conventions
- All success responses: `{"data": ...}`
- All error responses: `{"detail": "error message"}`
- Paginated responses: `{"data": [...], "total": int, "page": int, "page_size": int}`

### CORS Configuration
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend only — NEVER use "*"
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### Backend Binding
- Always bind to `127.0.0.1`, NEVER `0.0.0.0` — prevents local network exposure

---

## 7. Configuration & Environment

### Environment Variables
```bash
# .env.example

# Database
DATABASE_PATH=data/brainstorm.db

# LLM Providers (set the ones you use)
ANTHROPIC_API_KEY=                  # Never commit, never log
OPENAI_API_KEY=                     # Never commit, never log
OLLAMA_BASE_URL=http://localhost:11434

# Server
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000

# Session Limits
SESSION_MAX_MESSAGES=200
SESSION_MAX_TOKENS=500000
SESSION_MAX_DURATION_MINUTES=30
LLM_CALL_TIMEOUT_SECONDS=90
```

### Backend Configuration via pydantic-settings
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_path: str = "data/brainstorm.db"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    session_max_messages: int = 200
    session_max_tokens: int = 500_000
    session_max_duration_minutes: int = 30
    llm_call_timeout_seconds: int = 90

    model_config = SettingsConfigDict(env_file=".env")
```

### Two Config Layers
1. **Runtime config** (API keys, timeouts, host/port) — via `.env` / env vars, validated at startup
2. **User preferences** (output dir, language, model provider) — via SQLite `settings` table with UI

---

## 8. Structured Logging

### structlog Configuration
```python
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()  # Use JSONRenderer() in production
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)
```

### Per-LLM-Call Logging (Mandatory)
Every LLM call MUST log:
```python
logger.info(
    "llm_call_complete",
    session_id=session_id,
    persona=persona_name,
    provider=provider_name,
    model=model_name,
    action="brainstorm_turn",  # or "persona_suggestion", "output_extraction"
    latency_ms=latency_ms,
    tokens_in=tokens_in,
    tokens_out=tokens_out,
    error=None,  # or error message string
)
```

### Logging Rules
- Use appropriate log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- NEVER log API keys, full prompts containing secrets, or user credentials
- Redact key-like strings in structured logs
- Use JSON format for production, console renderer for development

---

## 9. Security Considerations

### Must-Have
| Measure | Detail |
|---------|--------|
| API keys in env vars only | Never in DB, never in logs, never in committed files |
| Log redaction | Mask key-like strings in structured logs |
| Markdown sanitization | `rehype-sanitize` on all agent-generated Markdown |
| HTML spec sandboxing | `sandbox` iframe (no `allow-scripts`) for HTML specs |
| Output path validation | Resolve to absolute, reject `..` traversal, reject symlinks outside base dir |
| Filename sanitization | Generated filenames restricted to `[a-zA-Z0-9_-]` |
| Input length limits | All user text fields have max length |
| Language setting as enum | Dropdown — never freeform text (prompt injection vector) |
| Localhost binding | `127.0.0.1` only, not `0.0.0.0` |
| CORS restriction | Frontend origin only, never `*` |
| Session hard caps | Max messages (200), max tokens (500K), max wall-clock (30 min) |
| Agent output boundary markers | Clear delimiters between agent messages |

### Deferred
- SQLCipher / DB encryption at rest — OS-level disk encryption suffices for personal tool
- Prompt injection pattern detection — false-positive prone for personal tool
- Bearer token auth on API — decided by planner (low cost, moderate value)

---

## 10. Testing

### Backend Testing
- **Framework**: `pytest` + `pytest-asyncio`
- **Database**: In-memory SQLite for tests (`sqlite+aiosqlite:///:memory:`)
- **Fixtures**: Shared in `tests/conftest.py` — async DB session, test client
- **Coverage target**: 80%+ for services, 70%+ overall

```python
# conftest.py
@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine)() as session:
        yield session
    await engine.dispose()

@pytest_asyncio.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
```

### Frontend Testing
- **Unit/Component**: `vitest` + `@testing-library/react`
- **E2E**: `playwright`
- Mock API calls with `msw` (Mock Service Worker)

### Test Patterns
- Follow AAA: Arrange, Act, Assert
- F.I.R.S.T: Fast, Independent, Repeatable, Self-Validating, Timely
- Coverage: unit 80%+, integration covers all major flows, E2E covers critical user flows

---

## 11. Build & Development

### Makefile Targets
```makefile
.PHONY: dev dev-backend dev-frontend test lint build

dev:
	@$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	cd backend && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

dev-frontend:
	cd frontend && npm run dev

test:
	cd backend && uv run pytest
	cd frontend && npm test

lint:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy .
	cd frontend && npm run lint && npx tsc --noEmit

build:
	cd frontend && npm run build
```

### Development Workflow
- **No Docker during development** — direct execution with hot-reload
- Backend: `uv run uvicorn app.main:app --reload`
- Frontend: `npm run dev` (with Turbopack)
- Docker Compose is a Phase 4 deployment artifact

### Quality Gate (Pre-commit)
1. `ruff check .` + `ruff format --check .` — zero Python lint errors
2. `mypy .` — zero type errors
3. `pytest` — all tests pass
4. `npm run lint` + `tsc --noEmit` — zero frontend errors
5. `npm test` — all frontend tests pass

### .gitignore Must Include
```
# Python
__pycache__/
*.pyc
.venv/
.mypy_cache/
.pytest_cache/
.coverage
htmlcov/

# Database
data/*.db
data/*.db-wal
data/*.db-shm

# Environment
.env
.env.local

# Node
node_modules/
.next/
*.tsbuildinfo

# IDE
.idea/
.vscode/

# Test artifacts
coverage/
playwright-report/
test-results/
```

---

## 12. Output Structure

### Adaptive Spec Directory by Stack Type
```
{output_dir}/{project_name}/
├── plan.md
├── stacks.md
├── specs/
│   └── {stack-type-specific directories}
├── tickets/
│   └── {epic-name}/
│       └── {NNN}-{action}-{entity}.md
└── _meta/
    ├── session.json
    └── output_manifest.json
```

### Stack-Type Templates
- **Web App**: `specs/api/`, `specs/ui/`, `specs/database/`
- **CLI**: `specs/commands/`, `specs/config/`
- **Library/SDK**: `specs/api-reference/`, `specs/usage/`
- **Mobile**: `specs/screens/`, `specs/api/`, `specs/navigation/`
- **Data Pipeline**: `specs/stages/`, `specs/schemas/`, `specs/scheduling/`

### Rules
- Technical identifiers and file names always in English regardless of language setting
- Filenames restricted to `[a-zA-Z0-9_-]`
- CRUD operations = 4 separate tickets (Create, Read, Update, Delete)
- Output Extractor validates ticket granularity and re-prompts if tickets are too coarse

---

## 13. Performance Patterns

### Backend
- Use connection pooling for SQLite (via SQLAlchemy engine)
- Sequential turn-taking (one agent at a time) — quality over speed
- Per-call timeout: 90s default, configurable per provider
- Retry: 3 attempts with exponential backoff (1s, 4s, 16s)

### Frontend
- **react-virtuoso** for chat — no DOM nodes for off-screen messages
- Use Server Components by default to reduce client JS
- Use `next/dynamic` for heavy components (MarkdownPreview, FileTree)
- SSE-driven append — never re-render the entire message list on new message

### Database
- WAL mode (concurrent reads during writes)
- Index on `messages(session_id, sequence_num)` — critical for conversation replay
- Paginate all list queries
- `sequence_num` for total message ordering

---

## 14. Orchestration Engine

### Phase-Driven Protocol
The brainstorm proceeds through structured phases:
1. **Stack Discussion** (2-3 rounds)
2. **Architecture** (2-3 rounds)
3. **Spec Detailing** (2-3 rounds)
4. **Ticket Breakdown** (2-3 rounds)
5. **Output Extraction** (separate phase, can use different model)

### Rules
- Strict round-robin within each phase (MVP — moderator-directed is v2)
- Orchestrator emits `MilestoneEvent` markers at phase transitions
- Every message committed to SQLite BEFORE SSE broadcast
- Session tracks: `status`, `last_completed_turn`, `next_persona_id`
- User directive injection: user messages injected into context as course corrections
- Context window management: full history for high-context models, sliding window for low-context
- Session hard caps enforced: 200 messages, 500K tokens, 30 minutes

---

## 15. Version Summary

| Technology | Version | Notes |
|---|---|---|
| Python | 3.13 | Latest stable |
| FastAPI | 0.115+ | Latest stable, async-native |
| SQLAlchemy | 2.0+ | Async with aiosqlite, `Mapped`/`mapped_column` |
| Alembic | 1.14+ | Migration management |
| Pydantic | 2.10+ | V2 with `ConfigDict`, `model_dump_json()` |
| pydantic-settings | 2.7+ | Environment config |
| structlog | 24.x+ | Structured JSON logging |
| httpx | 0.28+ | Async HTTP client |
| aiosqlite | 0.20+ | Async SQLite driver |
| anthropic | 0.43+ | Claude SDK (inference only, no orchestration) |
| openai | 1.60+ | OpenAI SDK |
| ruff | 0.9+ | Linter + formatter |
| mypy | 1.14+ | Type checker |
| pytest | 8.x | Test framework |
| pytest-asyncio | 0.25+ | Async test support |
| uvicorn | 0.34+ | ASGI server |
| Next.js | 15.x | App Router, React 19 |
| React | 19.x | Latest stable |
| TypeScript | 5.7+ | Strict mode |
| Tailwind CSS | 4.x | CSS-first config, `@theme` directive |
| Node.js | 22 LTS | Runtime |
| zustand | 4.5+ | State management |
| react-virtuoso | 4.12+ | Virtualized scrolling |
| react-markdown | 9.x | Markdown rendering |
| rehype-sanitize | 6.x | XSS prevention |
| shadcn/ui | latest | UI component library |
| zod | 3.x | Schema validation |
| vitest | 3.x | Frontend test runner |
| playwright | 1.50+ | E2E testing |

---

**Version**: v1.0.0
**Last updated**: 2026-04-13
