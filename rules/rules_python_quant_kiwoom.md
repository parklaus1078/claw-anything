# Coding Rules: Python Quant Trading App (키움증권 OpenAPI+ / FastAPI / React+Vite)

> Framework-specific rules for a dual-process quant trading application with 키움증권 integration, FastAPI web server, and React dashboard.

---

## 0. Architecture Overview: Dual-Process Design

This application runs as **two separate Python processes** communicating via a shared SQLite database:

1. **Trading Engine** (32-bit Python 3.11): Handles 키움증권 OpenAPI+ COM calls, runs the PyQt5 event loop, executes trading strategies, writes market data and trade events to SQLite.
2. **Web Server** (Python 3.12, 64-bit OK): FastAPI serves the React dashboard, reads from SQLite, provides REST/WebSocket endpoints for the frontend.

**Why dual-process:**
- 키움증권 OpenAPI+ is a 32-bit COM component — **32-bit Python is mandatory** for the trading engine.
- PyQt5's event loop and asyncio do not coexist well in a single thread.
- 64-bit Python has broader library support for the web stack.
- Clean separation of concerns: trading logic vs. presentation.

```
┌─────────────────────────┐     SQLite (shared)     ┌─────────────────────────┐
│   Trading Engine (32b)  │ ──────────────────────► │   Web Server (64b)      │
│   Python 3.11 + PyQt5   │  trades, orders, OHLCV  │   Python 3.12 + FastAPI │
│   pykiwoom + strategies │ ◄────────────────────── │   React dashboard       │
│   APScheduler           │  strategy configs, cmds  │   lightweight-charts    │
└─────────────────────────┘                          └─────────────────────────┘
```

**Inter-process communication rules:**
- Use SQLite WAL mode for concurrent read/write from both processes
- Trading engine is the **sole writer** for: trades, orders, positions, market_data tables
- Web server is the **sole writer** for: strategy_configs, user_commands tables
- For near-real-time updates, web server polls an `events` table (1-2s interval) and pushes via WebSocket/SSE to the frontend
- Never have both processes write to the same table — partition write ownership clearly

---

## 1. Project Structure

```
quant-app/
├── engine/                            # Trading engine (32-bit Python 3.11)
│   ├── main.py                       # Entry point — starts PyQt5 event loop + scheduler
│   ├── config.py                     # Engine settings (pydantic-settings, reads .env)
│   ├── kiwoom/                       # 키움증권 API layer
│   │   ├── __init__.py
│   │   ├── connection.py             # Login, connection management, heartbeat
│   │   ├── market_data.py            # Real-time quotes, OHLCV, orderbook
│   │   ├── order.py                  # Order placement, modification, cancellation
│   │   └── account.py               # Account info, balance, positions
│   ├── strategies/                   # Trading strategy implementations
│   │   ├── __init__.py
│   │   ├── base.py                   # Abstract base strategy class
│   │   ├── registry.py              # Strategy registry (discover + load)
│   │   ├── momentum_breakout.py     # Example: custom momentum strategy
│   │   ├── mean_reversion.py        # Example: statistical arbitrage
│   │   └── composite.py             # Multi-strategy ensemble
│   ├── indicators/                   # Custom technical indicators
│   │   ├── __init__.py
│   │   ├── custom.py                # Novel/proprietary indicators
│   │   └── utils.py                 # Indicator helper functions
│   ├── risk/                         # Risk management
│   │   ├── __init__.py
│   │   ├── position_sizer.py        # Position sizing algorithms
│   │   ├── stop_loss.py             # Stop-loss / take-profit logic
│   │   └── portfolio.py             # Portfolio-level risk constraints
│   ├── scheduler.py                  # APScheduler job definitions
│   ├── db/                           # Database access (engine-side)
│   │   ├── __init__.py
│   │   ├── connection.py            # SQLite connection (WAL mode, sync)
│   │   ├── models.py                # Table schemas (dataclasses)
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── trade_repo.py
│   │       ├── order_repo.py
│   │       ├── market_data_repo.py
│   │       └── event_repo.py        # Write events for web server to poll
│   ├── backtesting/                  # Offline backtesting module
│   │   ├── __init__.py
│   │   ├── engine.py                # Backtest execution engine
│   │   ├── data_loader.py           # Load historical data (DB or CSV)
│   │   └── report.py               # Performance metrics, drawdown, Sharpe
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── unit/
│   │   │   ├── test_strategies.py
│   │   │   ├── test_indicators.py
│   │   │   ├── test_risk.py
│   │   │   └── test_backtesting.py
│   │   └── integration/
│   │       └── test_db.py
│   ├── pyproject.toml
│   ├── .env.example
│   └── .python-version               # 3.11
│
├── server/                            # Web server (Python 3.12, 64-bit OK)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app entry, lifespan events
│   │   ├── config.py                 # Server settings (pydantic-settings)
│   │   ├── dependencies.py           # FastAPI DI providers
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py            # Top-level router aggregator
│   │   │   ├── dashboard.py         # Portfolio summary, P&L
│   │   │   ├── trades.py            # Trade history, filtering
│   │   │   ├── strategies.py        # Strategy config CRUD
│   │   │   ├── market.py            # Market data endpoints
│   │   │   ├── backtest.py          # Trigger/view backtest results
│   │   │   └── ws.py                # WebSocket for real-time updates
│   │   ├── models/                   # Pydantic schemas (request/response)
│   │   │   ├── __init__.py
│   │   │   ├── trade.py
│   │   │   ├── portfolio.py
│   │   │   ├── strategy.py
│   │   │   └── market.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── portfolio_service.py  # Portfolio calculations
│   │   │   ├── analytics_service.py  # Performance analytics
│   │   │   └── event_poller.py       # Poll events table, push via WS
│   │   └── db/
│   │       ├── __init__.py
│   │       ├── connection.py         # Async SQLite (aiosqlite, WAL mode)
│   │       └── repositories/
│   │           ├── __init__.py
│   │           ├── trade_repo.py     # Read-only trade queries
│   │           ├── market_data_repo.py
│   │           └── strategy_config_repo.py  # Read-write strategy configs
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── unit/
│   │   │   ├── test_portfolio_service.py
│   │   │   └── test_analytics.py
│   │   └── integration/
│   │       └── test_api.py
│   ├── pyproject.toml
│   ├── .env.example
│   └── .python-version               # 3.12
│
├── dashboard/                         # React frontend
│   ├── src/
│   │   ├── main.tsx                  # Entry point
│   │   ├── App.tsx                   # Root component + router
│   │   ├── components/
│   │   │   ├── charts/
│   │   │   │   ├── CandlestickChart.tsx   # lightweight-charts wrapper
│   │   │   │   ├── PortfolioChart.tsx     # Equity curve
│   │   │   │   ├── DrawdownChart.tsx      # Drawdown visualization
│   │   │   │   └── VolumeChart.tsx        # Volume overlay
│   │   │   ├── dashboard/
│   │   │   │   ├── PortfolioSummary.tsx   # Key metrics cards
│   │   │   │   ├── PositionTable.tsx      # Current positions
│   │   │   │   ├── TradeHistory.tsx       # Recent trades
│   │   │   │   └── StrategyStatus.tsx     # Active strategies
│   │   │   ├── strategy/
│   │   │   │   ├── StrategyConfig.tsx     # Strategy parameter editor
│   │   │   │   ├── BacktestResult.tsx     # Backtest performance view
│   │   │   │   └── StrategyList.tsx       # Strategy selector
│   │   │   └── common/
│   │   │       ├── Header.tsx
│   │   │       ├── Sidebar.tsx
│   │   │       └── StatusIndicator.tsx    # Engine connection status
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts           # WS connection + reconnect
│   │   │   ├── usePortfolio.ts           # Portfolio data hook
│   │   │   └── useMarketData.ts          # Real-time market data
│   │   ├── stores/
│   │   │   ├── portfolioStore.ts         # Zustand portfolio state
│   │   │   ├── marketStore.ts            # Zustand market data state
│   │   │   └── strategyStore.ts          # Zustand strategy state
│   │   ├── types/
│   │   │   ├── trade.ts
│   │   │   ├── portfolio.ts
│   │   │   ├── strategy.ts
│   │   │   └── market.ts
│   │   ├── utils/
│   │   │   ├── formatters.ts             # Currency, percentage, date
│   │   │   └── api.ts                    # Axios instance + interceptors
│   │   └── styles/
│   │       └── index.css                 # Tailwind directives
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── data/                              # Shared data directory
│   ├── quant.db                      # SQLite database (shared between engine + server)
│   └── backtest/                     # Backtest result CSVs
│
├── scripts/
│   ├── start_engine.bat              # Start trading engine (Windows)
│   ├── start_server.bat              # Start web server (Windows)
│   ├── start_all.bat                 # Start both processes
│   └── setup_env.bat                 # Create conda envs (32-bit + 64-bit)
│
├── .gitignore
├── .env.example                      # Root-level env template
└── README.md
```

### File Naming Conventions

| Area | Convention | Example |
|------|-----------|---------|
| Python modules | `snake_case.py` | `market_data.py` |
| Python classes | `PascalCase` | `class MomentumBreakout:` |
| Python functions/vars | `snake_case` | `def calculate_rsi():` |
| Python constants | `UPPER_SNAKE_CASE` | `MAX_POSITION_SIZE = 0.1` |
| Strategy files | `snake_case.py` matching class | `momentum_breakout.py` → `MomentumBreakout` |
| TypeScript components | `PascalCase.tsx` | `CandlestickChart.tsx` |
| TypeScript hooks | `camelCase.ts` with `use` prefix | `usePortfolio.ts` |
| TypeScript stores | `camelCase.ts` with `Store` suffix | `portfolioStore.ts` |
| TypeScript types | `PascalCase` interface | `interface TradeRecord {}` |

---

## 2. Tech Stack & Versions

### Trading Engine (32-bit)

| Package | Version | Purpose |
|---------|---------|---------|
| Python | 3.11.x (32-bit) | 키움증권 OpenAPI+ requires 32-bit |
| pykiwoom | latest | 키움증권 API wrapper |
| PyQt5 | 5.15.x | COM event loop (required by pykiwoom) |
| pandas | 2.2.x | Data manipulation |
| numpy | 1.26.x | Numerical computation (1.x for 32-bit compat) |
| pandas-ta-classic | latest | Technical indicators (130+) |
| APScheduler | 3.10.x | Scheduled trading jobs |
| pydantic-settings | 2.x | Configuration management |

### Web Server (64-bit)

| Package | Version | Purpose |
|---------|---------|---------|
| Python | 3.12.x | Web server runtime |
| FastAPI | 0.135.x | Async web framework |
| uvicorn | 0.34.x | ASGI server |
| aiosqlite | 0.20.x | Async SQLite access |
| pydantic | 2.x | Request/response validation |
| pydantic-settings | 2.x | Configuration management |

### Frontend

| Package | Version | Purpose |
|---------|---------|---------|
| React | 19.x | UI framework |
| TypeScript | 5.7.x | Type safety |
| Vite | 8.x | Build tool (Rolldown bundler) |
| lightweight-charts | latest | TradingView financial charts |
| zustand | 5.x | State management |
| axios | 1.x | HTTP client |
| tailwindcss | 4.x | Utility-first CSS |
| react-router | 7.x | Client-side routing |
| @tanstack/react-table | 8.x | Data tables |

### Infrastructure

| Tool | Purpose |
|------|---------|
| Conda (Miniconda) | Manage 32-bit Python env for engine |
| uv | Package manager for 64-bit server env |
| Node.js 22 LTS | Frontend tooling |
| SQLite 3.45+ | Shared database (WAL mode) |

---

## 3. Trading Engine Patterns

### 3.1 키움증권 API Layer

Wrap all pykiwoom calls in a dedicated `kiwoom/` module. Never call pykiwoom directly from strategy code.

```python
# ✅ Correct — abstracted API layer
class KiwoomMarketData:
    def __init__(self, kiwoom: Kiwoom):
        self._kiwoom = kiwoom

    def get_ohlcv(self, code: str, period: str = "day", count: int = 100) -> pd.DataFrame:
        """Fetch OHLCV data for a stock code."""
        raw = self._kiwoom.block_request(
            "opt10081",
            종목코드=code,
            기준일자=datetime.now().strftime("%Y%m%d"),
            수정주가구분=1,
            output="주식일봉차트조회",
            next=0,
        )
        return self._parse_ohlcv(raw)

# ❌ Wrong — strategy directly calls pykiwoom
class MyStrategy:
    def run(self):
        data = self.kiwoom.block_request("opt10081", ...)  # Tight coupling
```

**Rules:**
- All pykiwoom interactions go through `kiwoom/` module classes
- Handle API rate limits: 키움증권 limits to ~3.6 requests/second (1 request per 0.28s)
- Implement retry logic with exponential backoff for transient errors
- Log every API call at DEBUG level with request params and response status
- Never store the Kiwoom object in strategy classes — inject via constructor

### 3.2 Strategy Pattern

All strategies inherit from an abstract base class. This enables the strategy registry, backtesting, and consistent lifecycle management.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

class Signal(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

@dataclass(frozen=True)
class TradeSignal:
    signal: Signal
    code: str              # Stock code
    price: float           # Target price
    quantity: int           # Number of shares
    reason: str            # Human-readable reason
    confidence: float       # 0.0 to 1.0

class BaseStrategy(ABC):
    """All strategies must implement this interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique strategy identifier."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""

    @abstractmethod
    def initialize(self, config: dict) -> None:
        """Called once at startup with user-provided config."""

    @abstractmethod
    def generate_signals(self, market_data: dict[str, pd.DataFrame]) -> list[TradeSignal]:
        """Analyze market data and return trade signals.

        Args:
            market_data: Dict mapping stock code to OHLCV DataFrame

        Returns:
            List of trade signals (may be empty for HOLD)
        """

    @abstractmethod
    def get_universe(self) -> list[str]:
        """Return list of stock codes this strategy monitors."""

    def on_trade_executed(self, trade: "TradeRecord") -> None:
        """Optional callback after a trade executes. Override if needed."""
```

**Rules:**
- Strategies must be **pure computation** — no direct API calls, no DB writes
- `generate_signals()` receives data, returns signals. The orchestrator handles execution
- Strategy config is a plain dict loaded from the database — no hardcoded parameters
- Every signal must include a `reason` string for audit trail
- Use `@dataclass(frozen=True)` for signals — immutable data objects

### 3.3 Risk Management

Risk checks happen **between** signal generation and order execution. Never skip them.

```python
class RiskManager:
    def __init__(self, config: RiskConfig):
        self._config = config

    def validate_signal(self, signal: TradeSignal, portfolio: Portfolio) -> TradeSignal | None:
        """Returns approved signal (possibly adjusted) or None if rejected."""
        if not self._check_position_limit(signal, portfolio):
            return None
        if not self._check_daily_loss_limit(portfolio):
            return None
        adjusted = self._apply_position_sizing(signal, portfolio)
        return adjusted
```

**Rules:**
- Maximum position size per stock: configurable (default 10% of portfolio)
- Maximum total exposure: configurable (default 80% of portfolio)
- Daily loss limit: stop all trading if portfolio drops X% in a day (default 3%)
- Never execute an order without risk validation — no exceptions
- Log every risk rejection with the specific rule that triggered it

### 3.4 Scheduler Pattern

Use APScheduler for all time-based operations. Never use `while True` + `sleep()`.

```python
from apscheduler.schedulers.qt import QtScheduler

scheduler = QtScheduler()  # Integrates with PyQt5 event loop

# Market hours check (KRX: 09:00-15:30 KST)
scheduler.add_job(
    engine.run_strategy_cycle,
    "cron",
    day_of_week="mon-fri",
    hour="9-15",
    minute="*/5",          # Every 5 minutes during market hours
    id="strategy_cycle",
)

# Pre-market data collection
scheduler.add_job(
    engine.collect_premarket_data,
    "cron",
    day_of_week="mon-fri",
    hour=8,
    minute=50,
    id="premarket_data",
)
```

**Rules:**
- Use `QtScheduler` (not `BackgroundScheduler`) to integrate with PyQt5 event loop
- Define all scheduled jobs in `scheduler.py`, not scattered across modules
- KRX trading hours: 09:00–15:30 KST, Monday–Friday
- Account for Korean holidays — use a holiday calendar or maintain a holiday list
- Log every scheduled job execution at INFO level

---

## 4. Web Server Patterns (FastAPI)

### 4.1 Async-First Architecture

The web server is fully async. Never block the event loop.

```python
# ✅ Correct — async DB access
async def get_recent_trades(db: aiosqlite.Connection, limit: int = 50) -> list[Trade]:
    async with db.execute(
        "SELECT * FROM trades ORDER BY executed_at DESC LIMIT ?", (limit,)
    ) as cursor:
        rows = await cursor.fetchall()
        return [Trade.from_row(row) for row in rows]

# ❌ Wrong — synchronous DB in async handler
def get_recent_trades(db_path: str) -> list[Trade]:
    conn = sqlite3.connect(db_path)  # Blocks event loop
```

**Rules:**
- All database access via `aiosqlite` (async wrapper)
- Use `asyncio.sleep()`, never `time.sleep()`
- Offload CPU-heavy computations (analytics) to thread pool: `await asyncio.to_thread(compute_heavy_func)`
- Use FastAPI's dependency injection for database connections

### 4.2 FastAPI Lifespan & Dependencies

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db = await aiosqlite.connect(settings.DB_PATH)
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    app.state.db = db
    app.state.event_poller = EventPoller(db)
    asyncio.create_task(app.state.event_poller.run())
    yield
    # Shutdown
    await db.close()

app = FastAPI(title="Quant Dashboard API", lifespan=lifespan)
```

### 4.3 WebSocket for Real-Time Updates

```python
@router.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            events = await event_poller.get_new_events()
            if events:
                await websocket.send_json({"type": "events", "data": events})
            await asyncio.sleep(1)  # Poll interval
    except WebSocketDisconnect:
        pass
```

**Rules:**
- One WebSocket endpoint for all real-time dashboard updates
- Send typed messages: `{"type": "trade_executed" | "position_updated" | "strategy_signal", "data": {...}}`
- Implement reconnection logic on the frontend (exponential backoff)
- Do not send raw database rows — always serialize through Pydantic models

### 4.4 API Endpoint Design

```python
# RESTful endpoints — read-heavy, write-light
GET  /api/portfolio              # Current portfolio summary
GET  /api/portfolio/history      # Historical equity curve
GET  /api/trades                 # Trade history (paginated)
GET  /api/trades/{id}            # Single trade detail
GET  /api/positions              # Current open positions
GET  /api/strategies             # List all strategies + status
PUT  /api/strategies/{id}/config # Update strategy parameters
POST /api/strategies/{id}/toggle # Enable/disable strategy
GET  /api/market/{code}/ohlcv   # Historical OHLCV for a stock
GET  /api/backtest/{id}          # Backtest results
POST /api/backtest               # Trigger new backtest
WS   /ws/dashboard               # Real-time updates
```

**Rules:**
- All list endpoints must support pagination: `?page=1&size=50`
- Date range filtering: `?from=2026-01-01&to=2026-04-01`
- Return consistent response envelope: `{"data": ..., "meta": {"page": 1, "total": 100}}`
- Use HTTP status codes correctly: 200 (OK), 201 (Created), 400 (Bad Input), 404 (Not Found)

---

## 5. Frontend Patterns (React + Vite)

### 5.1 Chart Integration (lightweight-charts)

```tsx
import { createChart, IChartApi, ISeriesApi } from "lightweight-charts";

function CandlestickChart({ data }: { data: OHLCVData[] }) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: { background: { color: "#1a1a2e" }, textColor: "#e0e0e0" },
      grid: { vertLines: { color: "#2a2a3e" }, horzLines: { color: "#2a2a3e" } },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#ef4444",      // Korean market: red = up
      downColor: "#3b82f6",    // Korean market: blue = down
      borderUpColor: "#ef4444",
      borderDownColor: "#3b82f6",
      wickUpColor: "#ef4444",
      wickDownColor: "#3b82f6",
    });

    candleSeries.setData(data);
    chartRef.current = chart;

    return () => { chart.remove(); };
  }, [data]);

  return <div ref={chartContainerRef} />;
}
```

**Rules:**
- Korean market convention: **red = price up, blue = price down** (opposite of US markets)
- Always clean up chart instances in `useEffect` return
- Use `ResizeObserver` for responsive chart sizing
- Separate chart creation from data updates — update data via `series.setData()` or `series.update()`

### 5.2 State Management (Zustand)

```typescript
import { create } from "zustand";

interface PortfolioState {
  totalValue: number;
  dailyPnL: number;
  positions: Position[];
  isLoading: boolean;
  error: string | null;
  fetchPortfolio: () => Promise<void>;
  clearError: () => void;
}

const usePortfolioStore = create<PortfolioState>((set) => ({
  totalValue: 0,
  dailyPnL: 0,
  positions: [],
  isLoading: false,
  error: null,
  fetchPortfolio: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await api.get("/api/portfolio");
      set({ ...data, isLoading: false });
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
    }
  },
  clearError: () => set({ error: null }),
}));
```

**Rules:**
- Every store must have: `isLoading`, `error`, `clearError()` fields (consistency across all stores)
- Use separate stores for separate concerns: `portfolioStore`, `marketStore`, `strategyStore`
- Never put API calls in components — always in store actions or custom hooks
- WebSocket data updates go through stores, not directly into components

### 5.3 Number Formatting (Korean Won)

```typescript
const formatKRW = (value: number): string =>
  new Intl.NumberFormat("ko-KR", { style: "currency", currency: "KRW" }).format(value);

const formatPercent = (value: number): string =>
  `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;

const formatQuantity = (value: number): string =>
  new Intl.NumberFormat("ko-KR").format(value);
```

**Rules:**
- Always show KRW amounts with comma separators: ₩1,234,567
- Percentage changes: always show sign (+2.34%, -1.56%)
- Stock prices: no decimal places (KRX stocks trade in whole won)
- Use `Intl.NumberFormat` — never manual string formatting

---

## 6. Database Schema Conventions

### 6.1 SQLite Configuration

Both processes must set these pragmas on every connection:

```sql
PRAGMA journal_mode = WAL;        -- Required for concurrent read/write
PRAGMA foreign_keys = ON;         -- Enforce referential integrity
PRAGMA busy_timeout = 5000;       -- Wait up to 5s for locks
PRAGMA synchronous = NORMAL;      -- Good balance of safety/speed for WAL mode
```

### 6.2 Table Ownership

| Table | Writer | Reader | Purpose |
|-------|--------|--------|---------|
| `trades` | Engine | Server | Executed trade log |
| `orders` | Engine | Server | Order history (pending/filled/cancelled) |
| `positions` | Engine | Server | Current open positions |
| `market_data` | Engine | Server | OHLCV cache |
| `events` | Engine | Server | Real-time event queue |
| `strategy_configs` | Server | Engine | Strategy parameters |
| `user_commands` | Server | Engine | Manual commands (toggle, force-sell) |
| `backtest_results` | Engine | Server | Backtest output |
| `portfolio_snapshots` | Engine | Server | Daily portfolio snapshots |

### 6.3 Schema Conventions

```sql
-- All tables must have these columns:
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- ... domain columns ...
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime'))
);

-- Events table for IPC
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,      -- 'trade_executed', 'position_updated', etc.
    payload TEXT NOT NULL,          -- JSON string
    consumed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime'))
);
CREATE INDEX idx_events_unconsumed ON events(consumed, created_at);
```

**Rules:**
- All timestamps in ISO 8601 format, stored as TEXT (SQLite has no native datetime)
- Use `localtime` modifier for KST timestamps
- Use parameterized queries everywhere — never string-concatenate SQL
- Implement DB migrations as numbered SQL files: `001_initial.sql`, `002_add_backtest.sql`
- Add indexes on columns used in WHERE/ORDER BY clauses

---

## 7. Quant Strategy Development Rules

### 7.1 Strategy Design Principles

- **Backtest before live trading** — every strategy must pass backtesting with positive Sharpe ratio before deployment
- **Out-of-sample testing** — split data into train (70%) and test (30%) periods. Never optimize on the full dataset
- **Transaction costs** — always include commission (0.015% buy, 0.015% + 0.18% tax sell for Korean stocks) in backtests
- **Slippage modeling** — assume 0.1% slippage per trade in backtests
- **Survivorship bias** — when backtesting, include delisted stocks if possible
- **Regime awareness** — strategies should detect market regime (bull/bear/sideways) and adjust exposure

### 7.2 Key Metrics (must compute for every strategy)

```python
@dataclass(frozen=True)
class StrategyMetrics:
    total_return: float          # Total cumulative return
    annualized_return: float     # CAGR
    sharpe_ratio: float          # Risk-adjusted return (target: > 1.5)
    sortino_ratio: float         # Downside risk-adjusted return
    max_drawdown: float          # Maximum peak-to-trough decline
    win_rate: float              # Percentage of winning trades
    profit_factor: float         # Gross profit / gross loss
    avg_trade_duration: float    # Average holding period (days)
    trade_count: int             # Total number of trades
    calmar_ratio: float          # Annualized return / max drawdown
```

**Target thresholds for live deployment:**
- Sharpe ratio > 1.5
- Max drawdown < 15%
- Win rate > 45% (with proper risk/reward ratio)
- Profit factor > 1.5
- Minimum 100 trades in backtest

### 7.3 Novel Strategy Approaches (Beyond Popular Methods)

Since popular strategies degrade as more people use them, focus on:

- **Microstructure signals**: Order flow imbalance, bid-ask spread dynamics
- **Cross-asset momentum**: Use KOSPI futures, bond yields, FX (USD/KRW) as leading indicators
- **Earnings surprise decay**: Model post-earnings drift with custom decay functions
- **Sector rotation with regime detection**: Combine sector momentum with volatility regime classification
- **Multi-timeframe confluence**: Require signal agreement across 3+ timeframes before entry
- **Adaptive parameters**: Use rolling optimization windows (not static parameters)
- **Ensemble methods**: Combine 3-5 uncorrelated strategies, weight by recent Sharpe

### 7.4 Prohibited Practices in Strategy Code

- **No lookahead bias**: Never use future data in signal generation. All indicators must use only past data
- **No curve fitting**: If a strategy has 10+ tunable parameters, it's likely overfit
- **No martingale**: Never double position size after a loss
- **No averaging down** without explicit stop-loss: Adding to losing positions must have a hard stop
- **No overnight leverage**: Close leveraged positions before market close

---

## 8. Configuration & Secrets

### 8.1 Environment Variables

```bash
# .env.example (root)
# === Database ===
DB_PATH=./data/quant.db

# === Trading Engine ===
KIWOOM_ACCOUNT_NO=1234567890       # 키움증권 계좌번호
KIWOOM_ACCOUNT_PASSWORD=****       # 계좌 비밀번호 (4자리)
TRADING_MODE=paper                  # paper | live (ALWAYS start with paper)
MAX_DAILY_LOSS_PCT=3.0             # Stop trading if daily loss exceeds this %
MAX_POSITION_PCT=10.0              # Max single position as % of portfolio

# === Web Server ===
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
CORS_ORIGINS=http://localhost:5173  # Vite dev server

# === Logging ===
LOG_LEVEL=INFO
LOG_FORMAT=json                    # json | text
```

**Rules:**
- **NEVER** commit `.env` to git — `.gitignore` must include it
- Provide `.env.example` with placeholder values
- Use `pydantic-settings` for type-safe config loading in both processes
- `TRADING_MODE=paper` must be the default — require explicit `live` switch
- All monetary thresholds in percentages, not absolute values

### 8.2 Trading Mode Safety

```python
class TradingMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"

class EngineConfig(BaseSettings):
    trading_mode: TradingMode = TradingMode.PAPER

    model_config = SettingsConfigDict(env_file=".env")
```

**Rules:**
- Paper trading mode must be functionally identical to live except for order execution
- In paper mode, simulate fills at current market price + slippage
- Log a prominent WARNING at startup if `TRADING_MODE=live`
- Require double confirmation (env var + a flag file) to switch to live mode

---

## 9. Testing

### 9.1 Testing Strategy

| Layer | Framework | Focus |
|-------|-----------|-------|
| Engine unit tests | pytest | Strategies, indicators, risk management |
| Engine integration | pytest | DB operations, scheduler |
| Server unit tests | pytest + httpx | Service logic, analytics |
| Server integration | pytest + httpx | API endpoints, WebSocket |
| Frontend unit | Vitest + React Testing Library | Component rendering, store logic |
| Frontend E2E | Playwright | Full dashboard flows |

### 9.2 Strategy Testing Pattern

```python
def test_momentum_strategy_generates_buy_signal():
    # Arrange
    strategy = MomentumBreakout()
    strategy.initialize({"lookback_period": 20, "breakout_threshold": 0.02})
    market_data = {
        "005930": create_uptrending_ohlcv(days=30),  # Samsung trending up
    }

    # Act
    signals = strategy.generate_signals(market_data)

    # Assert
    assert len(signals) == 1
    assert signals[0].signal == Signal.BUY
    assert signals[0].code == "005930"
    assert 0.0 < signals[0].confidence <= 1.0
```

**Rules:**
- Use factory functions (`create_uptrending_ohlcv`, `create_sideways_ohlcv`) for test data
- Test edge cases: empty data, single data point, market holidays
- Test risk manager rejections: position limit, daily loss limit
- Use in-memory SQLite (`:memory:`) for all DB tests
- Mock pykiwoom for integration tests — never hit real 키움 API in tests
- Backtest results must be deterministic (seed random generators)

### 9.3 Coverage Targets

- Strategy logic: 90%+ (this is the core business logic)
- Risk management: 95%+ (safety-critical code)
- API endpoints: 80%+
- Frontend components: 70%+

---

## 10. Logging & Monitoring

### 10.1 Structured Logging

```python
import structlog

logger = structlog.get_logger()

# ✅ Correct — structured with context
logger.info("trade_executed",
    strategy="momentum_breakout",
    code="005930",
    side="buy",
    quantity=100,
    price=72500,
    total_krw=7250000,
)

# ❌ Wrong — unstructured string
logger.info(f"Bought 100 shares of 005930 at 72500")
```

**Rules:**
- Use `structlog` with JSON output in production
- Every trade execution: INFO with full trade details
- Every order placement: INFO with order params
- Every risk rejection: WARNING with rejection reason
- Every API error: ERROR with full context
- Every strategy signal: DEBUG with signal details
- **Never log**: account passwords, API keys, or session tokens
- Rotate log files daily, retain 30 days

### 10.2 Key Events to Monitor

| Event | Level | When |
|-------|-------|------|
| Engine started/stopped | INFO | Startup/shutdown |
| Login success/failure | INFO/ERROR | 키움 connection |
| Strategy cycle complete | DEBUG | Every scheduler run |
| Signal generated | DEBUG | Strategy output |
| Risk check passed/failed | INFO/WARNING | Pre-order |
| Order placed | INFO | API call |
| Trade executed | INFO | Fill confirmation |
| Daily P&L summary | INFO | Market close |
| Daily loss limit hit | CRITICAL | Emergency stop |
| DB connection error | ERROR | Any DB failure |

---

## 11. Security Considerations

- **Network exposure**: Web server binds to `127.0.0.1` only — never `0.0.0.0` (personal use, no external access)
- **No authentication on local API**: Since it's localhost-only, skip auth. If ever exposed, add JWT
- **CORS**: Allow only `http://localhost:5173` (Vite dev) and `http://localhost:4173` (Vite preview)
- **SQL injection**: All queries use parameterized statements — no exceptions
- **Trading mode switch**: Require env var `TRADING_MODE=live` — never default to live
- **Account credentials**: Store only in `.env`, loaded via pydantic-settings
- **Rate limiting**: 키움 API has rate limits (~3.6 req/s). Engine must enforce this internally

---

## 12. Build & Deployment (Windows 10)

### 12.1 Environment Setup

```batch
REM setup_env.bat — Run once to create environments

REM 1. Install Miniconda (if not installed)
REM 2. Create 32-bit conda env for trading engine
conda create -n quant-engine-32 python=3.11
conda activate quant-engine-32
conda config --env --set subdir win-32
conda install python=3.11
pip install pykiwoom PyQt5 pandas numpy pandas-ta-classic apscheduler pydantic-settings structlog

REM 3. Create 64-bit env for web server (use uv for speed)
pip install uv
uv venv server/.venv
server\.venv\Scripts\activate
uv pip install fastapi uvicorn aiosqlite pydantic pydantic-settings structlog

REM 4. Install frontend dependencies
cd dashboard
npm install
```

### 12.2 Start Scripts

```batch
REM start_engine.bat
conda activate quant-engine-32
cd engine
python main.py

REM start_server.bat
call server\.venv\Scripts\activate
cd server
uvicorn app.main:app --host 127.0.0.1 --port 8000

REM start_dashboard_dev.bat
cd dashboard
npm run dev
```

### 12.3 Production Frontend Build

```batch
cd dashboard
npm run build
REM Output goes to dashboard/dist/
REM Serve via FastAPI's StaticFiles mount in production
```

**Rules:**
- Always use `.bat` scripts for Windows (not `.sh`)
- Document the full setup process in README.md
- Test start scripts on a clean Windows 10 machine
- Use `conda` for 32-bit Python env, `uv` for 64-bit Python env
- Frontend production build served as static files by FastAPI

---

## 13. Performance Patterns

### 13.1 Database Performance

- WAL mode is mandatory for concurrent access
- Create indexes on: `trades(executed_at)`, `market_data(code, date)`, `events(consumed, created_at)`
- Use `LIMIT` on all queries — never `SELECT *` without bounds
- Vacuum the database weekly (scheduled job)
- Keep `market_data` table pruned — retain only last N days of minute-level data

### 13.2 Strategy Performance

- Pre-compute indicators during data collection, not during signal generation
- Use vectorized pandas operations — avoid row-by-row iteration
- Cache computed indicators with a TTL matching the data refresh interval
- Profile slow strategies with `cProfile` before optimizing

### 13.3 Frontend Performance

- Use `React.memo` for chart components (expensive to re-render)
- Debounce WebSocket updates: batch multiple events into a single state update
- Virtualize long tables (trade history) with `@tanstack/react-virtual`
- Lazy-load backtest result pages

---

## 14. Korean Market Specific Rules

### 14.1 KRX Trading Rules

- **Trading hours**: 09:00–15:30 KST (pre-market 08:30–09:00, after-hours 15:40–16:00)
- **Price limits**: ±30% from previous close
- **Tick sizes**: Vary by price range (see KRX tick size table)
- **Settlement**: T+2
- **Lot size**: 1 share minimum
- **Trading tax**: 0.18% on sell (as of 2026, verify current rate)
- **Commission**: ~0.015% each way (varies by broker plan)

### 14.2 Stock Code Conventions

- KOSPI stocks: 6-digit codes (e.g., `005930` = Samsung Electronics)
- KOSDAQ stocks: 6-digit codes (e.g., `035720` = Kakao)
- ETFs: 6-digit codes (e.g., `069500` = KODEX 200)
- Always store and transmit stock codes as zero-padded 6-character strings

### 14.3 Holiday Handling

- Use a Korean market holiday calendar
- Before any trading operation, check if today is a trading day
- Do not generate signals or place orders on holidays/weekends

---

**Version**: v1.0.0
**Last updated**: 2026-04-03
