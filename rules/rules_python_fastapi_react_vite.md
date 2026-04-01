# Coding Rules: Python (FastAPI + asyncio) + React (Vite) + Claude Agent SDK

> Framework-specific rules for an async Python backend with FastAPI, Claude Agent SDK integration, chzzkpy donation streaming, and a React/Vite OBS overlay frontend.

---

## 1. Project Structure

```
project-root/
├── backend/                        # Python FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI app entry, lifespan events
│   │   ├── config.py              # Settings via pydantic-settings
│   │   ├── dependencies.py        # FastAPI dependency injection
│   │   ├── api/                   # API route modules
│   │   │   ├── __init__.py
│   │   │   ├── router.py          # Top-level router aggregator
│   │   │   ├── donation.py        # Donation event endpoint (internal)
│   │   │   ├── queue.py           # Queue state REST + WebSocket
│   │   │   ├── stats.py           # Statistics endpoints
│   │   │   └── admin.py           # Ban, manual controls
│   │   ├── models/                # Pydantic models (NOT ORM — use for schemas + domain)
│   │   │   ├── __init__.py
│   │   │   ├── donation.py        # DonationEvent, DonationTier
│   │   │   ├── queue.py           # QueueItem, QueueState
│   │   │   ├── prompt.py          # PromptRequest, PromptResult
│   │   │   └── stats.py           # CostRecord, SessionStats
│   │   ├── services/              # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py    # Central queue + state machine
│   │   │   ├── donation_listener.py  # chzzkpy event loop
│   │   │   ├── agent_runner.py    # Claude Agent SDK session management
│   │   │   ├── security.py        # 3-layer security (filter, hook, sandbox)
│   │   │   ├── git_manager.py     # Auto-commit, revert, branch management
│   │   │   ├── cooldown.py        # Per-user cooldown tracking
│   │   │   └── ban.py             # Ban list management
│   │   ├── core/                  # Core utilities
│   │   │   ├── __init__.py
│   │   │   ├── logging.py         # Structured JSON logging setup
│   │   │   ├── exceptions.py      # Custom exception hierarchy
│   │   │   └── constants.py       # Tier configs, security patterns, limits
│   │   └── db/                    # Persistence (SQLite via aiosqlite)
│   │       ├── __init__.py
│   │       ├── connection.py      # DB connection + migrations
│   │       ├── repositories/      # Data access layer
│   │       │   ├── __init__.py
│   │       │   ├── donation_repo.py
│   │       │   ├── ban_repo.py
│   │       │   └── stats_repo.py
│   │       └── migrations/        # SQL migration files
│   │           └── 001_initial.sql
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py            # Shared fixtures (test DB, mock clients)
│   │   ├── unit/
│   │   │   ├── test_security.py
│   │   │   ├── test_orchestrator.py
│   │   │   ├── test_cooldown.py
│   │   │   └── test_tier.py
│   │   └── integration/
│   │       ├── test_api.py
│   │       ├── test_agent_runner.py
│   │       └── test_donation_flow.py
│   ├── pyproject.toml             # Project metadata + dependencies (uv/pip)
│   ├── .env.example               # Template for required env vars
│   └── .python-version            # Pin Python version (3.12+)
│
├── overlay/                       # React queue UI (OBS browser source)
│   ├── src/
│   │   ├── main.tsx               # Entry point
│   │   ├── App.tsx                # Root component
│   │   ├── components/
│   │   │   ├── QueueDisplay.tsx   # Main queue list
│   │   │   ├── CurrentPrompt.tsx  # Currently executing prompt
│   │   │   ├── QueueItem.tsx      # Single queue entry
│   │   │   ├── TierBadge.tsx      # Tier visual indicator
│   │   │   ├── BanAlert.tsx       # Ban notification animation
│   │   │   └── CompletionAlert.tsx # Success/failure notification
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts    # WebSocket connection + reconnect
│   │   │   └── useQueueState.ts   # Queue state from WebSocket
│   │   ├── types/
│   │   │   └── queue.ts           # TypeScript interfaces matching backend models
│   │   ├── utils/
│   │   │   └── formatters.ts      # Time, currency formatters
│   │   └── styles/
│   │       └── index.css          # Tailwind directives + custom styles
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── unity-project/                 # Unity game project (Claude's workspace)
│   └── ...                        # Managed by Unity + Claude Agent
│
├── scripts/                       # Operational scripts
│   ├── start.sh                   # Start all services
│   └── health_check.py            # System health monitoring
│
├── .gitignore
├── .env.example                   # Root-level env template
└── README.md
```

### File Naming Conventions

| Area | Convention | Example |
|------|-----------|---------|
| Python modules | `snake_case.py` | `agent_runner.py` |
| Python classes | `PascalCase` | `class DonationListener:` |
| Python functions/vars | `snake_case` | `def process_donation():` |
| Python constants | `UPPER_SNAKE_CASE` | `MAX_QUEUE_SIZE = 50` |
| TypeScript files | `PascalCase.tsx` for components, `camelCase.ts` for utils | `QueueItem.tsx`, `useWebSocket.ts` |
| TypeScript types | `PascalCase` | `interface QueueItem {}` |
| TypeScript vars/functions | `camelCase` | `const formatTime = ()` |
| CSS classes | Tailwind utilities (no custom BEM) | `className="flex gap-2"` |

---

## 2. Python / FastAPI Patterns

### 2.1 Async-First Architecture

This project is fundamentally async — chzzkpy WebSocket events, FastAPI endpoints, Claude Agent SDK queries, and WebSocket broadcasting all run on the asyncio event loop.

```python
# ✅ Correct — async throughout
async def process_queue_item(item: QueueItem) -> PromptResult:
    async for message in query(prompt=item.prompt, options=item.agent_options):
        await broadcast_progress(message)
    return PromptResult(...)

# ❌ Wrong — blocking call in async context
def process_queue_item(item: QueueItem) -> PromptResult:
    result = subprocess.run(["git", "commit", ...])  # Blocks event loop
```

**Rules:**
- Never use `time.sleep()` — use `await asyncio.sleep()`
- Never use `subprocess.run()` — use `asyncio.create_subprocess_exec()`
- Never use synchronous file I/O in request handlers — use `aiofiles` or offload to thread
- Use `asyncio.TaskGroup` (Python 3.11+) for concurrent async operations
- Use `asyncio.Queue` or `asyncio.PriorityQueue` for the donation queue (not `queue.Queue`)

### 2.2 FastAPI Specifics

**Lifespan events** for startup/shutdown:
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize DB, start donation listener, create agent session
    db = await init_database()
    donation_task = asyncio.create_task(donation_listener.run())
    yield {"db": db}
    # Shutdown: cancel tasks, close connections
    donation_task.cancel()
    await db.close()

app = FastAPI(lifespan=lifespan)
```

**Dependency injection** for shared state:
```python
from fastapi import Depends

async def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator

@router.get("/queue")
async def get_queue(orchestrator: Orchestrator = Depends(get_orchestrator)):
    return orchestrator.get_queue_state()
```

**WebSocket** for real-time queue updates:
```python
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except WebSocketDisconnect:
                self.disconnect(connection)
```

**Pydantic v2 models** for all data:
```python
from pydantic import BaseModel, Field
from enum import StrEnum

class DonationTier(StrEnum):
    ONE_LINE = "one_line"
    FEATURE = "feature"
    MAJOR = "major"
    CHAOS = "chaos"

class DonationEvent(BaseModel):
    donor_name: str
    donor_id: str
    amount: int
    message: str  # This is the prompt
    tier: DonationTier = Field(default=DonationTier.ONE_LINE)
    timestamp: datetime = Field(default_factory=datetime.now)
```

### 2.3 Configuration with pydantic-settings

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Anthropic
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-6-20250514"

    # Chzzk
    chzzk_client_id: str
    chzzk_client_secret: str

    # Paths
    unity_project_path: str
    db_path: str = "data/chzzk_plays.db"

    # Limits
    daily_budget_usd: float = 50.0
    max_queue_size: int = 50

settings = Settings()
```

**Rules:**
- All secrets go in `.env`, never hardcoded
- Provide `.env.example` with placeholder values and comments
- Use `Field(default=...)` for non-secret defaults, not environment variables
- Validate paths exist at startup, not at first use

### 2.4 Error Handling

**Custom exception hierarchy:**
```python
class ChzzkPlaysError(Exception):
    """Base exception for all project errors."""

class SecurityViolationError(ChzzkPlaysError):
    """Prompt or tool use blocked by security filter."""

class QueueFullError(ChzzkPlaysError):
    """Queue has reached maximum capacity."""

class AgentTimeoutError(ChzzkPlaysError):
    """Claude agent did not complete within the tier timeout."""

class BuildFailedError(ChzzkPlaysError):
    """Unity build failed after agent changes."""
```

**FastAPI exception handlers:**
```python
@app.exception_handler(SecurityViolationError)
async def security_violation_handler(request: Request, exc: SecurityViolationError):
    logger.warning("Security violation", extra={"detail": str(exc)})
    return JSONResponse(status_code=403, content={"detail": "Blocked by security filter"})
```

**Rules:**
- Catch specific exceptions, never bare `except:`
- Always log errors with structured context (donor_id, prompt summary, tier)
- Use `asyncio.timeout()` (Python 3.11+) for agent execution timeouts
- Never swallow exceptions silently — at minimum, log them

### 2.5 Structured Logging

```python
import structlog

logger = structlog.get_logger()

# ✅ Good — structured context
logger.info("donation_received", donor_id=event.donor_id, amount=event.amount, tier=event.tier)
logger.error("agent_failed", prompt_id=item.id, error=str(exc), duration_ms=elapsed)

# ❌ Bad — unstructured string
logger.info(f"Received donation from {event.donor_id} for {event.amount}")
```

**Rules:**
- Use `structlog` with JSON output for production
- Add `donor_id`, `prompt_id`, `tier` as context to every log in the donation pipeline
- Never log the full prompt text at INFO level (it's user content — log at DEBUG only)
- Never log API keys, tokens, or session IDs

---

## 3. Claude Agent SDK Patterns

### 3.1 Session Management

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, HookMatcher

class AgentRunner:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: ClaudeSDKClient | None = None

    async def start_session(self):
        options = ClaudeAgentOptions(
            model=self.settings.claude_model,
            cwd=self.settings.unity_project_path,
            system_prompt=self._build_system_prompt(),
            permission_mode="bypassPermissions",
            hooks={
                "PreToolUse": [
                    HookMatcher(matcher="Bash", hooks=[self._security_hook])
                ],
                "PostToolUse": [
                    HookMatcher(matcher=".*", hooks=[self._post_tool_hook])
                ],
            },
        )
        self._client = ClaudeSDKClient(options=options)
        await self._client.__aenter__()

    async def execute_prompt(self, item: QueueItem) -> PromptResult:
        """Execute a donation prompt with tier-specific constraints."""
        tier_options = TIER_CONFIGS[item.tier]
        self._client.set_options(
            max_turns=tier_options.max_turns,
            allowed_tools=tier_options.allowed_tools,
        )

        messages = []
        async with asyncio.timeout(tier_options.timeout_seconds):
            await self._client.query(item.prompt)
            async for msg in self._client.receive_response():
                messages.append(msg)

        return PromptResult(
            prompt_id=item.id,
            messages=messages,
            cost_usd=messages[-1].total_cost_usd if messages else 0,
        )
```

### 3.2 Tier Configuration

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class TierConfig:
    max_turns: int
    allowed_tools: list[str]
    timeout_seconds: int
    cooldown_seconds: int
    min_amount: int  # in KRW

TIER_CONFIGS: dict[DonationTier, TierConfig] = {
    DonationTier.ONE_LINE: TierConfig(
        max_turns=1,
        allowed_tools=["Read", "Edit"],
        timeout_seconds=60,
        cooldown_seconds=60,
        min_amount=1_000,
    ),
    DonationTier.FEATURE: TierConfig(
        max_turns=3,
        allowed_tools=["Read", "Edit", "Write", "Bash"],
        timeout_seconds=120,
        cooldown_seconds=180,
        min_amount=5_000,
    ),
    DonationTier.MAJOR: TierConfig(
        max_turns=8,
        allowed_tools=["Read", "Edit", "Write", "Bash", "Glob"],
        timeout_seconds=180,
        cooldown_seconds=300,
        min_amount=10_000,
    ),
    DonationTier.CHAOS: TierConfig(
        max_turns=15,
        allowed_tools=["Read", "Edit", "Write", "Bash", "Glob", "Grep"],
        timeout_seconds=300,
        cooldown_seconds=600,
        min_amount=30_000,
    ),
}
```

### 3.3 Security Hooks

```python
import re

BLOCKED_PATTERNS = [
    r"\.\./",                    # Directory traversal
    r"(?:^|[;&|])\s*(?:curl|wget|ssh|nc|ncat)\b",  # Network commands
    r"(?:^|[;&|])\s*(?:rm\s+-rf|chmod|chown)\b",   # Destructive commands
    r"/(?:etc|home|root|var|tmp)/",                  # System paths
    r"(?:API_KEY|SECRET|TOKEN|PASSWD|PASSWORD)",      # Secret references
    r"\b(?:eval|exec)\s*\(",                         # Code execution
    r"\bimport\s+(?:os|subprocess|shutil)\b",        # Dangerous imports
]
BLOCKED_RE = re.compile("|".join(BLOCKED_PATTERNS), re.IGNORECASE)

async def security_hook(input_data: dict, tool_use_id: str | None, context) -> dict:
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Check Bash commands
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if BLOCKED_RE.search(command):
            return _deny(f"Blocked dangerous pattern in command")

    # Check file paths for all file tools
    if tool_name in ("Read", "Edit", "Write", "Glob", "Grep"):
        file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
        if file_path and not _is_within_project(file_path):
            return _deny(f"Access outside project directory")

    return {}

def _deny(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
```

**Rules:**
- Security hooks must be fast — no I/O, no async calls, regex only
- Log every denial with full context (tool_name, input summary, reason)
- Test security hooks extensively — one missed pattern = system compromise
- Update `BLOCKED_PATTERNS` when new attack vectors are discovered

### 3.4 Cost Tracking

```python
from claude_agent_sdk import ResultMessage

async def track_cost(result: ResultMessage, item: QueueItem):
    """Record cost after each prompt execution."""
    await stats_repo.record(CostRecord(
        prompt_id=item.id,
        donor_id=item.donor_id,
        tier=item.tier,
        cost_usd=result.total_cost_usd,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        duration_ms=result.duration_ms,
        timestamp=datetime.now(),
    ))

    daily_total = await stats_repo.get_daily_cost_usd()
    if daily_total >= settings.daily_budget_usd:
        logger.critical("daily_budget_exceeded", total=daily_total, limit=settings.daily_budget_usd)
        # Pause queue processing, notify operator
```

---

## 4. chzzkpy Integration Patterns

### 4.1 Donation Listener

```python
from chzzkpy import Client, UserClient, Donation, UserPermission

class DonationListener:
    def __init__(self, settings: Settings, on_donation: Callable):
        self._settings = settings
        self._on_donation = on_donation
        self._client: Client | None = None

    async def run(self):
        """Long-running task — start in asyncio.create_task()."""
        self._client = Client(
            self._settings.chzzk_client_id,
            self._settings.chzzk_client_secret,
        )

        @self._client.event
        async def on_donation(donation: Donation):
            event = DonationEvent(
                donor_name=donation.profile.nickname,
                donor_id=donation.profile.user_id_hash,
                amount=donation.pay_amount,
                message=donation.message,
                tier=classify_tier(donation.pay_amount),
            )
            await self._on_donation(event)

        user_client = await self._client.generate_user_client(code, state)
        await user_client.connect(UserPermission(donation=True))
```

**Rules:**
- Run the donation listener as a background `asyncio.Task`, not in the main thread
- Implement exponential backoff on disconnection (1s, 2s, 4s, 8s... max 60s)
- Log all reconnection attempts with attempt count
- Never trust donation message content — always filter before passing to Claude

---

## 5. Database (SQLite + aiosqlite)

### 5.1 Why SQLite

This is a single-server application with low write volume (~50 donations/day). SQLite is the correct choice:
- No external DB process to manage
- File-based — easy backup, easy deployment
- `aiosqlite` provides async interface over `sqlite3`
- WAL mode handles concurrent reads from API + agent

### 5.2 Connection Setup

```python
import aiosqlite

async def init_database(db_path: str) -> aiosqlite.Connection:
    db = await aiosqlite.connect(db_path)
    await db.execute("PRAGMA journal_mode = WAL")
    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute("PRAGMA busy_timeout = 5000")
    db.row_factory = aiosqlite.Row
    await run_migrations(db)
    return db
```

### 5.3 Repository Pattern

```python
class DonationRepository:
    def __init__(self, db: aiosqlite.Connection):
        self._db = db

    async def record(self, event: DonationEvent, result: PromptResult | None) -> int:
        cursor = await self._db.execute(
            """INSERT INTO donations (donor_id, donor_name, amount, prompt, tier, status, commit_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (event.donor_id, event.donor_name, event.amount, event.message,
             event.tier, "completed" if result else "failed",
             result.commit_id if result else None, event.timestamp.isoformat()),
        )
        await self._db.commit()
        return cursor.lastrowid
```

**Rules:**
- Always use parameterized queries (`?` placeholders) — never string interpolation
- Always `await db.commit()` after writes
- Use `db.row_factory = aiosqlite.Row` for dict-like access
- Put migration SQL in numbered files: `001_initial.sql`, `002_add_stats.sql`

---

## 6. React / Vite / TailwindCSS (OBS Overlay)

### 6.1 Key Constraints

The overlay runs in an **OBS Browser Source** — this is a Chromium-based browser with constraints:
- Transparent background required (`background: transparent` in CSS, not `body { background: white }`)
- No user interaction (no click handlers, no forms) — display only
- Fixed dimensions (set in OBS, typically 400x800 or similar)
- WebSocket is the only data source
- Must be lightweight — OBS shares GPU with the game/stream

### 6.2 Tech Choices

| Library | Version | Purpose |
|---------|---------|---------|
| React | 18+ | UI rendering |
| Vite | 5+ | Build tool |
| TailwindCSS | 3+ | Utility-first styling |
| TypeScript | 5+ | Type safety |
| framer-motion | 11+ | Entry/exit animations for queue items |

**No other dependencies.** No state management library (React state + useReducer is sufficient for a display-only overlay). No routing library. No HTTP client (WebSocket only).

### 6.3 WebSocket Hook

```typescript
import { useState, useEffect, useRef, useCallback } from "react";

interface QueueState {
  current: QueueItem | null;
  pending: QueueItem[];
  recentCompleted: CompletedItem | null;
  recentBan: BanEvent | null;
}

export function useQueueWebSocket(url: string): QueueState {
  const [state, setState] = useState<QueueState>(INITIAL_STATE);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectDelay = useRef(1000);

  const connect = useCallback(() => {
    const ws = new WebSocket(url);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setState(data);
      reconnectDelay.current = 1000; // Reset on success
    };

    ws.onclose = () => {
      setTimeout(() => {
        reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30000);
        connect();
      }, reconnectDelay.current);
    };

    wsRef.current = ws;
  }, [url]);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return state;
}
```

### 6.4 Component Patterns

```tsx
// ✅ Correct — simple, display-only components
function QueueItem({ item }: { item: QueueItemData }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="flex items-center gap-3 p-3 rounded-lg bg-black/60 backdrop-blur"
    >
      <TierBadge tier={item.tier} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-bold text-white truncate">{item.donorName}</p>
        <p className="text-xs text-gray-300 truncate">{item.prompt}</p>
      </div>
    </motion.div>
  );
}

// ❌ Wrong — unnecessary state management, API calls, complex logic
function QueueItem({ item }: { item: QueueItemData }) {
  const [expanded, setExpanded] = useState(false); // No interaction in OBS
  useEffect(() => { fetch("/api/details/" + item.id) }, []); // Use WebSocket, not REST
}
```

**Rules:**
- No `useState` beyond what's set by the WebSocket hook
- No `useEffect` for data fetching — all data comes from WebSocket
- No click handlers, hover states, or interactive elements
- Use `AnimatePresence` + `motion.div` for enter/exit animations
- Use `truncate` (Tailwind) for long prompt text — never let text overflow
- All colors should have transparency for OBS compositing (`bg-black/60`, not `bg-black`)

### 6.5 Build Configuration

```typescript
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],
  base: "./", // Relative paths for OBS file:// loading
  build: {
    outDir: "dist",
    assetsDir: "assets",
  },
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"), // Always use __dirname
    },
  },
});
```

**Rules:**
- `base: "./"` is mandatory — OBS loads via `file://` protocol, not a web server
- Always use `resolve(__dirname, ...)` in config files, never `resolve("...")`
- Build output goes to `dist/` — point OBS browser source to `dist/index.html`

---

## 7. State Machine for Queue Processing

The orchestrator follows a strict state machine:

```
IDLE → FILTERING → QUEUED → RUNNING → BUILDING → DONE
                     ↓         ↓          ↓
                   REJECTED  TIMEOUT    FAILED → REVERTING → REVERTED
```

```python
from enum import StrEnum

class PromptState(StrEnum):
    IDLE = "idle"
    FILTERING = "filtering"
    QUEUED = "queued"
    RUNNING = "running"
    BUILDING = "building"
    DONE = "done"
    FAILED = "failed"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    REVERTING = "reverting"
    REVERTED = "reverted"
```

**Rules:**
- State transitions must be explicit — no implicit state changes
- Log every state transition with prompt_id and old→new state
- Broadcast state changes to WebSocket clients immediately
- On FAILED: auto-trigger `git revert HEAD`, transition to REVERTING → REVERTED
- On TIMEOUT: cancel the agent task, transition to FAILED

---

## 8. Git Automation

```python
import asyncio

class GitManager:
    def __init__(self, repo_path: str):
        self._repo_path = repo_path

    async def auto_commit(self, donor_name: str, prompt_summary: str) -> str:
        """Commit after successful prompt execution. Returns commit hash."""
        await self._run("git", "add", "-A")
        message = f"[auto] {donor_name}: {prompt_summary[:80]}"
        await self._run("git", "commit", "-m", message)
        result = await self._run("git", "rev-parse", "HEAD")
        return result.strip()

    async def revert_last(self) -> bool:
        """Revert the last commit. Returns True if successful."""
        try:
            await self._run("git", "revert", "HEAD", "--no-edit")
            return True
        except subprocess.CalledProcessError:
            logger.error("git_revert_failed")
            return False

    async def _run(self, *args: str) -> str:
        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=self._repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, args, stdout, stderr)
        return stdout.decode()
```

**Rules:**
- Always use `asyncio.create_subprocess_exec` for git commands (not `subprocess.run`)
- Commit message format: `[auto] {donor_name}: {prompt_summary}` (max 80 char summary)
- Auto-revert on build failure — never leave a broken state
- The Unity project repo is separate from the system repo

---

## 9. Testing

### 9.1 Framework: pytest + pytest-asyncio

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### 9.2 Test Structure

```python
# tests/conftest.py
import pytest
import aiosqlite

@pytest.fixture
async def db():
    """In-memory SQLite for tests."""
    conn = await aiosqlite.connect(":memory:")
    await conn.execute("PRAGMA foreign_keys = ON")
    await run_migrations(conn)
    yield conn
    await conn.close()

@pytest.fixture
def mock_agent_options():
    """Agent options with no actual API calls."""
    return ClaudeAgentOptions(
        model="claude-sonnet-4-6-20250514",
        cwd="/tmp/test-project",
        max_turns=1,
        allowed_tools=["Read"],
    )
```

### 9.3 What to Test

| Layer | Test Type | Coverage Target |
|-------|-----------|----------------|
| Security filters (regex, hooks) | Unit | 100% — every blocked pattern must have a test |
| Tier classification | Unit | 100% — every amount boundary |
| Cooldown logic | Unit | 100% — edge cases at boundaries |
| Queue priority ordering | Unit | All tier combinations |
| State machine transitions | Unit | Every valid + invalid transition |
| API endpoints | Integration | All endpoints + error cases |
| Donation → Queue → Execute flow | Integration | Happy path + failure paths |
| WebSocket broadcast | Integration | Connection, disconnection, reconnection |

### 9.4 Security Test Examples

```python
# tests/unit/test_security.py
import pytest
from app.services.security import BLOCKED_RE, security_hook

@pytest.mark.parametrize("command,should_block", [
    ("echo hello", False),
    ("cat Assets/Scripts/Player.cs", False),
    ("curl https://evil.com", True),
    ("rm -rf /", True),
    ("cat /etc/passwd", True),
    ("cd ../../../etc", True),
    ("echo $API_KEY", True),
    ("python -c 'import os; os.system(\"rm -rf /\")'", True),
    # Edge cases
    ("echo 'curl is a nice word'", True),  # Acceptable false positive — security first
    ("git commit -m 'update'", False),
])
async def test_bash_security_filter(command, should_block):
    input_data = {"tool_name": "Bash", "tool_input": {"command": command}}
    result = await security_hook(input_data, None, None)
    is_blocked = "permissionDecision" in result.get("hookSpecificOutput", {})
    assert is_blocked == should_block, f"Command {'should' if should_block else 'should not'} be blocked: {command}"
```

### 9.5 Testing Rules

- **Every security pattern must have at least one test** — if you add a pattern to `BLOCKED_PATTERNS`, add a test
- **Test boundary conditions** for tier classification (999 KRW → rejected, 1000 → one_line, 4999 → one_line, 5000 → feature)
- **Test cooldown timing** with mocked clocks, not `await asyncio.sleep()`
- **Never mock the database in integration tests** — use in-memory SQLite
- **Test WebSocket reconnection** — simulate disconnection and verify auto-reconnect

### 9.6 React Overlay Tests

Minimal testing for the overlay — it's a display-only component:

```typescript
// overlay/src/__tests__/QueueDisplay.test.tsx
import { render, screen } from "@testing-library/react";
import { QueueDisplay } from "../components/QueueDisplay";

test("renders current prompt with donor name", () => {
  render(<QueueDisplay state={mockState} />);
  expect(screen.getByText("TestDonor")).toBeInTheDocument();
});

test("renders up to 8 pending items", () => {
  const state = { ...mockState, pending: Array(12).fill(mockItem) };
  render(<QueueDisplay state={state} />);
  expect(screen.getAllByTestId("queue-item")).toHaveLength(8);
});
```

Use **Vitest + React Testing Library**. No E2E tests needed for the overlay.

---

## 10. Dependency Management

### 10.1 Python (pyproject.toml with uv)

```toml
[project]
name = "chzzk-plays-gamedev"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0,<1.0",
    "uvicorn[standard]>=0.32.0,<1.0",
    "claude-agent-sdk>=0.1.48,<1.0",
    "chzzkpy>=2.0.0,<3.0",
    "pydantic>=2.10.0,<3.0",
    "pydantic-settings>=2.7.0,<3.0",
    "aiosqlite>=0.20.0,<1.0",
    "structlog>=24.4.0,<26.0",
    "websockets>=13.0,<15.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0,<9.0",
    "pytest-asyncio>=0.24.0,<1.0",
    "httpx>=0.28.0,<1.0",       # For FastAPI TestClient
    "ruff>=0.8.0,<1.0",         # Linter + formatter
    "mypy>=1.13.0,<2.0",
]
```

### 10.2 React Overlay (package.json)

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "framer-motion": "^11.15.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.4.0",
    "typescript": "^5.7.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "@testing-library/react": "^16.1.0",
    "vitest": "^2.1.0",
    "jsdom": "^25.0.0"
  }
}
```

**Rules:**
- Pin minimum versions with upper bound (`>=X,<Y`) for Python
- Use `^` (caret) ranges for npm (allows minor updates)
- `uv` for Python dependency management (fast, lockfile-based)
- Run `uv lock` / `npm install` to generate lockfiles — commit lockfiles to Git
- No utility libraries (lodash, etc.) in the overlay — it's too small to need them

---

## 11. Security Considerations

### 11.1 Prompt Injection Defense

This system accepts **untrusted user input** (donation messages) and passes them to an AI agent that can execute code. This is the highest-risk scenario for prompt injection.

**Defense layers (ALL required):**

1. **Pre-filter**: Regex-based keyword/pattern blocking before Claude sees the prompt
2. **Tool-level hooks**: PreToolUse hooks inspect every tool call Claude attempts
3. **Filesystem sandbox**: Claude's cwd is locked to the Unity project directory
4. **Network isolation**: No network tools allowed (curl, wget blocked)
5. **Budget cap**: Daily USD limit prevents cost-based attacks (infinite loop prompts)
6. **Turn limit**: max_turns per tier prevents runaway agent loops

### 11.2 Security Checklist (ALL REQUIRED)

```
- [ ] BLOCKED_PATTERNS regex tested with 20+ attack vectors
- [ ] PreToolUse hook denies all Bash commands matching dangerous patterns
- [ ] File path validation ensures all file access is within unity-project/
- [ ] No network tools in any tier's allowed_tools
- [ ] daily_budget_usd set and enforced
- [ ] max_turns enforced per tier
- [ ] Timeout enforced per tier (asyncio.timeout)
- [ ] Ban system stores blocked user IDs
- [ ] .env file in .gitignore
- [ ] API keys loaded from environment, never hardcoded
- [ ] CORS restricted to localhost only (overlay is local)
- [ ] WebSocket endpoints validate origin header
```

### 11.3 What NOT to Trust

- Donation message content (the prompt) — always filter
- Donor nickname — could contain XSS payloads if displayed in HTML
- Any path generated by Claude — always validate against project root
- Claude's Bash commands — always inspect via hooks
- WebSocket messages from unknown origins — validate origin header

---

## 12. Performance Patterns

### 12.1 Async Queue Processing

```python
# ✅ Correct — process one at a time, non-blocking
async def queue_processor(queue: asyncio.PriorityQueue, runner: AgentRunner):
    while True:
        item = await queue.get()  # Blocks until item available (async, not busy-wait)
        try:
            result = await runner.execute_prompt(item)
            await on_success(item, result)
        except asyncio.TimeoutError:
            await on_timeout(item)
        except Exception as exc:
            await on_failure(item, exc)
        finally:
            queue.task_done()
```

### 12.2 WebSocket Broadcasting

- Use `asyncio.gather()` with `return_exceptions=True` for broadcasting to multiple clients
- Remove disconnected clients immediately — don't let the list grow unbounded
- Send only changed data (queue diff), not the full state, if queue grows large

### 12.3 Database Performance

- WAL mode for concurrent reads (API serving queue state) while agent writes donation records
- Use `busy_timeout = 5000` to handle write contention gracefully
- No indexes needed at this scale (~50 records/day) beyond primary keys
- Vacuum periodically (weekly cron or manual) to reclaim space

---

## 13. Deployment & Operations

### 13.1 Target Environment

This runs on a **local Windows machine** (the streaming PC), with development happening in WSL.

- Backend: Run via `uvicorn` in a terminal/tmux session
- Overlay: Build with Vite, serve `dist/index.html` as OBS browser source (file:// protocol)
- Unity: Runs natively on Windows, monitored by the backend
- OBS: Captures Unity window + overlay + Claude Code terminal

### 13.2 Process Management

```bash
# scripts/start.sh — start all backend services
#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Activate venv
source .venv/bin/activate

# Start FastAPI server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload &

echo "Backend started on :8000"
echo "Overlay: open overlay/dist/index.html in OBS browser source"
```

### 13.3 Health Monitoring

- Watchdog script checks: FastAPI responding, WebSocket connected, chzzkpy connected, queue not stalled
- Discord webhook alerts for: queue processing failure, budget threshold (80%), chzzkpy disconnect
- All metrics logged to SQLite stats table for post-stream analysis

---

## 14. Anti-Patterns to Avoid

### Python

| Anti-Pattern | Why | Do Instead |
|-------------|-----|------------|
| `asyncio.run()` inside FastAPI | Blocks the event loop | Use `await` directly |
| `subprocess.run()` in async code | Blocks the event loop | Use `asyncio.create_subprocess_exec()` |
| `time.sleep()` in async code | Blocks the event loop | Use `await asyncio.sleep()` |
| Bare `except:` or `except Exception:` | Hides bugs | Catch specific exceptions |
| `os.getenv()` for config | No validation, no typing | Use `pydantic-settings` |
| Global mutable state | Race conditions in async | Use dependency injection |
| `print()` for logging | No levels, no structure | Use `structlog` |
| String formatting in SQL | SQL injection | Use parameterized queries (`?`) |

### React Overlay

| Anti-Pattern | Why | Do Instead |
|-------------|-----|------------|
| REST polling | Wasteful, laggy | WebSocket push |
| Complex state management (Redux) | Overkill for display-only | `useState` + WebSocket |
| Click handlers / forms | OBS browser has no interaction | Display-only components |
| External fonts / large assets | Slows OBS rendering | System fonts + Tailwind |
| `background: white` | Breaks OBS transparency | `background: transparent` + semi-transparent containers |

### Claude Agent SDK

| Anti-Pattern | Why | Do Instead |
|-------------|-----|------------|
| No PreToolUse hooks | Untrusted prompts can execute anything | Always hook Bash + file tools |
| No max_turns | Runaway agent loops burn budget | Set per tier |
| No timeout | Hung agent blocks queue | Use `asyncio.timeout()` |
| Trusting file paths from Claude | Agent might access system files | Validate against project root |
| Logging full prompts at INFO | User content in logs | Log at DEBUG only, summarize at INFO |

---

## 15. Linting & Formatting

### Python: Ruff

```toml
# pyproject.toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "UP",   # pyupgrade
    "ASYNC", # flake8-async
]

[tool.ruff.lint.isort]
known-first-party = ["app"]
```

### TypeScript: ESLint + Prettier (via Vite plugin)

```json
// overlay/.eslintrc.json
{
  "extends": ["eslint:recommended", "plugin:@typescript-eslint/recommended", "plugin:react-hooks/recommended"],
  "rules": {
    "no-unused-vars": "off",
    "@typescript-eslint/no-unused-vars": "error"
  }
}
```

### Pre-commit Checks

```bash
# Before every commit (manual or CI):
ruff check backend/ --fix
ruff format backend/
cd overlay && npx eslint src/ --fix && npx prettier --write src/
```

---

**Version**: v1.0.0
**Last updated**: 2026-03-31
