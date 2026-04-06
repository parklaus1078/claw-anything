# Coding Rules: Python (FastAPI) + Next.js + PostgreSQL + Docker

> Framework-specific rules for a full-stack AI Integration Decision Support Platform with a FastAPI backend, Next.js frontend, PostgreSQL (pgvector) database, and Docker-based deployment.

---

## 1. Project Structure

```
project-root/
├── docker-compose.yml              # Orchestrates all services
├── docker-compose.override.yml     # Local dev overrides (volumes, ports, hot-reload)
├── .env.example                    # Template for required environment variables
├── .gitignore
├── README.md
│
├── backend/                        # Python FastAPI backend
│   ├── Dockerfile
│   ├── pyproject.toml              # Dependencies managed via uv or poetry
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
│   │   │   ├── reports.py          # Report generation endpoints
│   │   │   ├── cases.py            # Similar case analysis endpoints
│   │   │   ├── factcheck.py        # Fact-check engine endpoints
│   │   │   ├── costs.py            # Cost estimation endpoints
│   │   │   ├── auth.py             # Authentication endpoints
│   │   │   └── health.py           # Health check endpoint
│   │   ├── schemas/                # Pydantic request/response models
│   │   │   ├── __init__.py
│   │   │   ├── report.py
│   │   │   ├── case.py
│   │   │   ├── user.py
│   │   │   └── common.py           # Shared schemas (pagination, errors)
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Declarative base + common mixins
│   │   │   ├── user.py
│   │   │   ├── report.py
│   │   │   ├── case.py
│   │   │   └── embedding.py        # pgvector-backed embedding storage
│   │   ├── services/               # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── report_generator.py # Orchestrates report generation
│   │   │   ├── case_analyzer.py    # Similar case retrieval + analysis
│   │   │   ├── cost_estimator.py   # Cost and timeline estimation
│   │   │   ├── factcheck.py        # Fact-check against sourced data
│   │   │   ├── risk_analyzer.py    # Risk analysis logic
│   │   │   ├── ai_client.py        # Claude API wrapper
│   │   │   └── embedding.py        # OpenAI embedding generation
│   │   ├── core/                   # Cross-cutting concerns
│   │   │   ├── __init__.py
│   │   │   ├── logging.py          # Structured JSON logging
│   │   │   ├── exceptions.py       # Custom exception hierarchy
│   │   │   ├── security.py         # Password hashing, JWT utilities
│   │   │   └── constants.py        # Application-wide constants
│   │   ├── db/                     # Database layer
│   │   │   ├── __init__.py
│   │   │   ├── session.py          # AsyncSession factory, engine setup
│   │   │   └── repositories/       # Data access layer
│   │   │       ├── __init__.py
│   │   │       ├── user_repo.py
│   │   │       ├── report_repo.py
│   │   │       └── case_repo.py
│   │   └── tasks/                  # Celery async tasks
│   │       ├── __init__.py
│   │       ├── celery_app.py       # Celery configuration
│   │       ├── scraping.py         # Web scraping tasks
│   │       └── report_tasks.py     # Long-running report generation
│   └── tests/
│       ├── conftest.py             # Shared fixtures (async DB, test client)
│       ├── unit/
│       ├── integration/
│       └── factories/              # Test data factories (factory_boy)
│
├── frontend/                       # Next.js frontend
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── public/
│   ├── src/
│   │   ├── app/                    # App Router pages
│   │   │   ├── layout.tsx          # Root layout
│   │   │   ├── page.tsx            # Landing page
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx
│   │   │   ├── reports/
│   │   │   │   ├── page.tsx        # Reports list
│   │   │   │   ├── new/
│   │   │   │   │   └── page.tsx    # New report form
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx    # Report detail
│   │   │   └── auth/
│   │   │       ├── login/
│   │   │       │   └── page.tsx
│   │   │       └── register/
│   │   │           └── page.tsx
│   │   ├── components/             # Reusable UI components
│   │   │   ├── ui/                 # Primitive UI (buttons, inputs, cards)
│   │   │   ├── layout/             # Header, sidebar, footer
│   │   │   └── reports/            # Report-specific components
│   │   ├── lib/                    # Utilities and client-side logic
│   │   │   ├── api.ts              # API client (fetch wrapper)
│   │   │   ├── auth.ts             # Auth helpers
│   │   │   └── utils.ts            # Generic utility functions
│   │   ├── hooks/                  # Custom React hooks
│   │   ├── types/                  # TypeScript type definitions
│   │   └── styles/                 # Global styles
│   │       └── globals.css
│   └── tests/
│       ├── components/             # Component tests (Vitest + Testing Library)
│       └── e2e/                    # Playwright E2E tests
│
├── workers/                        # Celery workers + Scrapy spiders
│   ├── Dockerfile
│   ├── scrapy.cfg
│   └── spiders/
│       ├── __init__.py
│       ├── research_reports.py     # Public research report crawler
│       └── media_articles.py       # Tech media crawler
│
└── nginx/                          # Reverse proxy (production)
    ├── Dockerfile
    └── nginx.conf
```

---

## 2. Docker & Container Conventions

### Service Definitions
- Every service (backend, frontend, database, redis, worker) gets its own container
- Use multi-stage Docker builds to minimize image size
- Pin base image versions (e.g., `python:3.13-slim`, `node:22-alpine`)
- Never run containers as root in production — use a non-root user

### Docker Compose Structure
```yaml
# docker-compose.yml — production-like defaults
services:
  backend:
    build: ./backend
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    depends_on:
      - backend

  db:
    image: pgvector/pgvector:pg17
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]

  worker:
    build: ./workers
    depends_on:
      - redis
      - db

volumes:
  pgdata:
```

### Key Rules
- `docker-compose.override.yml` for local development only (bind mounts, debug ports)
- Health checks on every service — use `depends_on.condition: service_healthy`
- Named volumes for persistent data (never bind-mount DB data directories in production)
- Environment variables via `.env` file, never hardcoded in Compose files
- Use `restart: unless-stopped` in production

---

## 3. Backend — Python FastAPI Conventions

### Python Version & Tooling
- **Python 3.13** (latest stable)
- **Package manager**: `uv` (preferred) or `poetry` — pin exact versions in lockfile
- **Linter/formatter**: `ruff` (replaces black, isort, flake8)
- **Type checking**: `mypy` with strict mode

### FastAPI Patterns

#### App Initialization — Use Lifespan
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize DB pool, Redis, AI clients
    await init_db()
    yield
    # Shutdown: close connections
    await close_db()

app = FastAPI(
    title="AI Integration Evaluator API",
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

@router.get("/reports/{report_id}")
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ...
```

#### Route Organization
- Group routes by domain in separate files under `api/`
- Aggregate all routers in `api/router.py` with prefixes and tags
- Always set response_model explicitly for type safety and documentation
- Use status codes from `fastapi.status` constants

#### Pydantic Models (Schemas)
- Separate `schemas/` (API contracts) from `models/` (ORM)
- Use `model_config = ConfigDict(from_attributes=True)` for ORM-to-schema conversion
- All request bodies must use Pydantic models — never accept raw dicts
- Use `Field()` with descriptions for auto-generated API docs

### Async Everywhere
- All I/O operations must be async (database, HTTP calls, file operations)
- Use `httpx.AsyncClient` for outbound HTTP (Claude API, OpenAI API)
- Use `asyncpg` driver via SQLAlchemy async engine
- Never use synchronous `requests` or `psycopg2` in async routes
- For CPU-bound work, offload to Celery tasks

### Error Handling
```python
# core/exceptions.py
class AppError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code

class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: str | int):
        super().__init__(f"{resource} {resource_id} not found", 404)

class RateLimitError(AppError):
    def __init__(self):
        super().__init__("Rate limit exceeded", 429)

# Register global handler in main.py
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
```

---

## 4. Database — PostgreSQL + pgvector

### SQLAlchemy Async Setup
- Use SQLAlchemy 2.0+ async style with `AsyncSession`
- Define all models using `DeclarativeBase` (not legacy `declarative_base()`)
- Use `Mapped[type]` annotations for all columns

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pgvector.sqlalchemy import Vector

class Base(DeclarativeBase):
    pass

class CaseEmbedding(Base):
    __tablename__ = "case_embeddings"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    embedding: Mapped[list[float]] = mapped_column(Vector(1536))
```

### Alembic Migrations
- Every schema change goes through Alembic — never modify tables manually
- Auto-generate migrations: `alembic revision --autogenerate -m "description"`
- Review generated migrations before applying — autogenerate is not perfect
- Include both `upgrade()` and `downgrade()` — every migration must be reversible
- Run migrations on container startup via entrypoint script

### Repository Pattern
- All database queries live in `db/repositories/` — never query directly in routes or services
- Repositories accept an `AsyncSession` parameter (injected via DI)
- Return domain objects or Pydantic models, not raw Row objects

### pgvector Best Practices
- Create the vector extension in an Alembic migration: `op.execute("CREATE EXTENSION IF NOT EXISTS vector")`
- Use IVFFlat or HNSW index for similarity search on tables with 1000+ rows
- Normalize embeddings before storage if using cosine distance
- Use `<=>` operator (cosine distance) for semantic similarity queries

---

## 5. Frontend — Next.js + Tailwind CSS + TypeScript

### Next.js Version & Config
- **Next.js 15** (latest stable with App Router)
- **React 19**
- **Node.js 22 LTS**
- Always use the **App Router** (`src/app/`) — do not use Pages Router

### TypeScript Strictness
- Enable `strict: true` in `tsconfig.json`
- No `any` types — use `unknown` and narrow with type guards
- Define all API response shapes in `types/`
- Use `satisfies` operator for type-safe object literals

### App Router Conventions
- Default to **Server Components** — only add `"use client"` when interactivity is needed
- Use `loading.tsx` for Suspense fallbacks per route
- Use `error.tsx` for error boundaries per route
- Use `layout.tsx` for shared UI within route groups
- Data fetching in Server Components via `fetch()` with Next.js caching

### Component Patterns
```tsx
// Server Component (default) — no "use client" directive
export default async function ReportsPage() {
  const reports = await fetchReports();
  return <ReportList reports={reports} />;
}

// Client Component — only when needed for interactivity
"use client";
export function ReportForm() {
  const [formData, setFormData] = useState<ReportInput>(initialState);
  // ...
}
```

### API Client
- Use a single `lib/api.ts` module wrapping `fetch` with base URL, auth headers, and error handling
- For server-side data fetching, call the backend directly (container-to-container via Docker network)
- For client-side data fetching, call via the Next.js API route or direct to backend through the reverse proxy
- Use `next/navigation` for programmatic navigation — never `window.location`

### Styling with Tailwind CSS
- **Tailwind CSS v4** (latest stable)
- Use `@import "tailwindcss"` in globals.css (v4 syntax)
- Use CSS-first configuration (v4 approach) instead of `tailwind.config.js` when possible
- Prefer utility classes directly in JSX over custom CSS
- Extract repeated utility combinations into components, not `@apply`
- Use `cn()` helper (from `clsx` + `tailwind-merge`) for conditional class merging

### Recommended Frontend Libraries
| Library | Purpose |
|---------|---------|
| `shadcn/ui` | Pre-built accessible UI components (copy-paste, not dependency) |
| `react-hook-form` + `zod` | Form handling with schema validation |
| `recharts` | Charts for cost estimation and risk visualization |
| `@tanstack/react-query` | Client-side data fetching, caching, and mutation |
| `next-auth` (Auth.js v5) | Authentication with JWT/session strategy |
| `vitest` + `@testing-library/react` | Unit and component testing |
| `playwright` | End-to-end testing |

---

## 6. AI Integration (Claude API + OpenAI Embeddings)

### Client Wrapper
- Wrap AI API calls in a dedicated service (`services/ai_client.py`, `services/embedding.py`)
- Never call AI APIs directly from route handlers
- Use `httpx.AsyncClient` with connection pooling and timeouts
- Set explicit timeout values (e.g., 120s for Claude, 30s for embeddings)

### Prompt Management
- Store prompt templates as constants or in separate files — never inline in service logic
- Version prompt templates alongside code (not in the database)
- Log prompt inputs and outputs for debugging (redact PII)

### Cost Control
- Track token usage per request and per user
- Implement rate limiting per pricing tier (Free: 2 reports/month, Pro: unlimited)
- Cache embedding results — re-embed only when source content changes
- Use the cheapest sufficient model for each task (e.g., Haiku for classification, Opus for analysis)

### Error Handling for AI Calls
```python
async def generate_report(prompt: str) -> str:
    try:
        response = await ai_client.messages.create(...)
        return response.content[0].text
    except anthropic.RateLimitError:
        raise RateLimitError()
    except anthropic.APIStatusError as e:
        logger.error("Claude API error", status=e.status_code, message=str(e))
        raise AppError("AI service temporarily unavailable", 503)
```

---

## 7. Background Tasks — Celery + Redis

### Configuration
- Use Redis as both Celery broker and result backend
- Define all tasks in `backend/app/tasks/`
- Use `task_always_eager = True` in test configuration for synchronous execution
- Set `task_soft_time_limit` and `task_time_limit` on every task

### Task Patterns
```python
@celery_app.task(
    bind=True,
    max_retries=3,
    soft_time_limit=300,
    time_limit=360,
)
def scrape_research_reports(self, source_url: str) -> dict:
    try:
        return run_spider(source_url)
    except SoftTimeLimitExceeded:
        logger.warning("Scraping task timed out", url=source_url)
        return {"status": "timeout"}
    except Exception as exc:
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
```

### Workers Docker Container
- Separate container for Celery workers — shares the same codebase as backend
- Use `celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4`
- Monitor with Flower in development (optional container)

---

## 8. Authentication & Authorization

### JWT-Based Auth
- Use `python-jose` or `PyJWT` for JWT encoding/decoding
- Access tokens: short-lived (15–30 minutes)
- Refresh tokens: longer-lived (7 days), stored in httpOnly cookies
- Never store tokens in localStorage — use httpOnly, Secure, SameSite cookies

### Password Hashing
- Use `passlib[bcrypt]` or `argon2-cffi`
- Never implement custom hashing

### Authorization Middleware
```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_jwt(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await user_repo.get_by_id(db, payload["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_tier(minimum_tier: str):
    async def dependency(user: User = Depends(get_current_user)):
        if not user.has_tier(minimum_tier):
            raise HTTPException(status_code=403, detail="Upgrade required")
        return user
    return dependency
```

---

## 9. Testing

### Backend Testing
- **Framework**: `pytest` + `pytest-asyncio`
- **Database**: Use a separate test PostgreSQL database (via Docker Compose `test` profile)
- **Fixtures**: Shared in `tests/conftest.py` — async DB session, test client, authenticated user
- **Factories**: Use `factory_boy` for generating test data
- **Coverage target**: 80%+ for services, 70%+ overall

```python
# conftest.py
@pytest_asyncio.fixture
async def db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_test_session() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
```

### Frontend Testing
- **Unit/Component**: `vitest` + `@testing-library/react`
- **E2E**: `playwright`
- Test Server Components by testing their rendered output
- Test Client Components with user event simulation
- Mock API calls with `msw` (Mock Service Worker)

### Integration Testing with Docker
- Use `docker compose --profile test up` to spin up test dependencies
- Backend integration tests hit a real PostgreSQL instance
- Never mock the database in integration tests

---

## 10. Configuration & Environment Variables

### Required Environment Variables
```bash
# .env.example
# Database
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_USER=evaluator
POSTGRES_PASSWORD=           # Set in .env, never commit
POSTGRES_DB=ai_evaluator

# Redis
REDIS_URL=redis://redis:6379/0

# AI APIs
ANTHROPIC_API_KEY=           # Set in .env, never commit
OPENAI_API_KEY=              # Set in .env, never commit

# Auth
JWT_SECRET_KEY=              # Set in .env, never commit
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### Backend Configuration via pydantic-settings
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_user: str
    postgres_password: str
    postgres_db: str
    anthropic_api_key: str
    openai_api_key: str
    jwt_secret_key: str

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = SettingsConfigDict(env_file=".env")
```

---

## 11. API Documentation

### OpenAPI/Swagger
- FastAPI auto-generates OpenAPI docs — always accessible at `/docs` (dev) and `/redoc`
- Add descriptions to every route via docstrings or `summary=` / `description=` parameters
- Add examples to Pydantic schemas using `model_config` with `json_schema_extra`
- Disable `/docs` and `/redoc` in production via environment flag

### Response Consistency
- All success responses: `{"data": ...}`
- All error responses: `{"detail": "error message"}`
- Paginated responses: `{"data": [...], "total": int, "page": int, "page_size": int}`

---

## 12. Security Considerations

### API Security
- Enable CORS with explicit allowed origins — never use `allow_origins=["*"]` in production
- Rate limit all public endpoints (use `slowapi` or custom middleware)
- Validate all path/query parameters with Pydantic types
- Sanitize any user input before passing to AI prompts (prompt injection prevention)

### Prompt Injection Prevention
- Never pass raw user input directly into AI system prompts
- Use input/output guardrails: validate that AI responses match expected formats
- Log all AI interactions for audit

### Container Security
- Use `--read-only` filesystem where possible
- Drop all capabilities and add back only what's needed
- Scan images for vulnerabilities with `trivy` or `docker scout`
- Never store secrets in Docker images or layers

---

## 13. Performance Patterns

### Backend
- Use connection pooling for both PostgreSQL (`pool_size`, `max_overflow`) and Redis
- Cache frequently accessed data (case embeddings, report summaries) in Redis
- Use database indexes on all foreign keys and frequently queried columns
- Paginate all list endpoints — never return unbounded result sets

### Frontend
- Use Next.js Image component for optimized image loading
- Leverage Server Components to reduce client-side JavaScript
- Use `React.lazy()` / `next/dynamic` for code splitting heavy components (charts)
- Set appropriate `Cache-Control` headers for static assets

### Database
- Add GIN/GiST indexes for full-text search
- Use HNSW index for pgvector similarity search (`lists` tuned to sqrt(n))
- Use `EXPLAIN ANALYZE` to verify query plans before deploying
- Implement connection pooling via PgBouncer in production (optional container)

---

## 14. Logging & Observability

### Structured Logging
- Use `structlog` for JSON-formatted logs in the backend
- Include `request_id`, `user_id`, and `service` fields in every log entry
- Log AI API latency and token usage for cost monitoring
- Use log levels consistently: DEBUG for dev, INFO for request lifecycle, ERROR for failures

### Health Checks
- `/api/health` endpoint returns service status + dependency checks (DB, Redis, AI APIs)
- Docker health checks on every container
- Frontend: Next.js built-in health at `/api/health`

---

## 15. Build & Deployment

### CI Pipeline (GitHub Actions recommended)
1. **Lint & Type Check**: `ruff check`, `mypy`, `eslint`, `tsc --noEmit`
2. **Test**: `pytest` (backend), `vitest` (frontend)
3. **Build**: `docker compose build`
4. **Push**: Push images to container registry

### Production Deployment
- Use `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
- Run Alembic migrations before starting the backend: `alembic upgrade head`
- Use Nginx as reverse proxy for TLS termination and static file serving
- Enable gzip compression in Nginx for API responses and static assets

---

## 16. Version Summary

| Technology | Version | Notes |
|---|---|---|
| Python | 3.13 | Latest stable |
| FastAPI | 0.115+ | Latest stable |
| SQLAlchemy | 2.0+ | Async-first with `Mapped` annotations |
| Alembic | 1.14+ | Migration management |
| Pydantic | 2.10+ | V2 with `model_config` |
| PostgreSQL | 17 | Via pgvector/pgvector:pg17 image |
| pgvector | 0.8+ | Vector similarity search |
| Celery | 5.4+ | Background task processing |
| Redis | 7 | Broker + cache |
| Next.js | 15 | App Router, React 19 |
| React | 19 | Latest stable |
| TypeScript | 5.7+ | Strict mode |
| Tailwind CSS | 4.0 | CSS-first config |
| Node.js | 22 LTS | Runtime for frontend |
| Docker Compose | 2.x | Container orchestration |
| Nginx | 1.27+ | Reverse proxy |

---

**Version**: v1.0.0
**Last updated**: 2026-04-06
