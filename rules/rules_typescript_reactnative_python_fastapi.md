# Coding Rules: TypeScript + React Native (Expo) + Python + FastAPI

> Framework-specific rules for a cross-platform (iOS, Android, Web) quant trading application with React Native frontend and Python FastAPI backend.

---

## 1. Project Structure

```
project-root/
├── apps/
│   └── mobile/                    # React Native (Expo) — iOS, Android, Web
│       ├── app/                   # Expo Router file-based routing
│       │   ├── (tabs)/            # Tab navigator group
│       │   │   ├── _layout.tsx    # Tab layout configuration
│       │   │   ├── portfolio.tsx  # Portfolio/dashboard tab
│       │   │   ├── markets.tsx    # Market data tab
│       │   │   ├── trade.tsx      # Trading tab
│       │   │   └── settings.tsx   # Settings tab
│       │   ├── (auth)/            # Auth flow group
│       │   │   ├── _layout.tsx
│       │   │   ├── login.tsx
│       │   │   └── register.tsx
│       │   ├── stock/
│       │   │   └── [symbol].tsx   # Dynamic stock detail route
│       │   ├── _layout.tsx        # Root layout
│       │   └── +not-found.tsx     # 404 fallback
│       ├── components/            # Reusable UI components
│       │   ├── ui/                # Design system primitives (Button, Card, Input, Modal)
│       │   ├── charts/            # Chart components (Candlestick, LineChart, PieChart)
│       │   ├── portfolio/         # Portfolio-specific components
│       │   ├── market/            # Market data components
│       │   └── trade/             # Trading components
│       ├── hooks/                 # Custom React hooks
│       ├── stores/                # Zustand state stores
│       ├── services/              # API client, WebSocket manager
│       ├── types/                 # TypeScript type definitions
│       ├── utils/                 # Pure utility functions
│       ├── constants/             # App constants (colors, config, endpoints)
│       ├── assets/                # Static assets (images, fonts, icons)
│       ├── app.json               # Expo configuration
│       ├── metro.config.js        # Metro bundler config
│       ├── tailwind.config.ts     # NativeWind Tailwind config
│       ├── tsconfig.json
│       └── package.json
│
├── backend/                       # Python FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app entry point
│   │   ├── config.py             # Settings via pydantic-settings
│   │   ├── dependencies.py       # FastAPI dependency injection
│   │   ├── api/                   # API route modules
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py     # v1 API router aggregator
│   │   │   │   ├── auth.py       # Authentication endpoints
│   │   │   │   ├── portfolio.py  # Portfolio endpoints
│   │   │   │   ├── market.py     # Market data endpoints
│   │   │   │   ├── trading.py    # Trading endpoints
│   │   │   │   └── simulation.py # Mock trading endpoints
│   │   ├── models/                # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── portfolio.py
│   │   │   ├── trade.py
│   │   │   ├── stock.py
│   │   │   └── simulation.py
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── portfolio.py
│   │   │   ├── trade.py
│   │   │   ├── stock.py
│   │   │   └── simulation.py
│   │   ├── services/              # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── portfolio_service.py
│   │   │   ├── market_data_service.py
│   │   │   ├── trading_service.py
│   │   │   ├── simulation_service.py
│   │   │   └── quant/             # Quant strategy modules
│   │   │       ├── __init__.py
│   │   │       ├── strategy_engine.py
│   │   │       ├── signals.py
│   │   │       ├── risk_manager.py
│   │   │       ├── backtester.py
│   │   │       └── indicators.py
│   │   ├── repositories/          # Data access layer
│   │   │   ├── __init__.py
│   │   │   ├── user_repository.py
│   │   │   ├── portfolio_repository.py
│   │   │   ├── trade_repository.py
│   │   │   └── stock_repository.py
│   │   ├── core/                  # Core utilities
│   │   │   ├── __init__.py
│   │   │   ├── security.py       # JWT, password hashing
│   │   │   ├── exceptions.py     # Custom exception classes
│   │   │   └── middleware.py     # CORS, rate limiting, logging
│   │   ├── tasks/                 # Celery async tasks
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py     # Celery configuration
│   │   │   ├── market_tasks.py   # Market data fetching
│   │   │   ├── trading_tasks.py  # Automated trade execution
│   │   │   └── simulation_tasks.py
│   │   └── websockets/            # WebSocket handlers
│   │       ├── __init__.py
│   │       ├── manager.py        # Connection manager
│   │       ├── market_feed.py    # Real-time market data
│   │       └── portfolio_feed.py # Real-time portfolio updates
│   ├── alembic/                   # Database migrations
│   │   ├── versions/
│   │   ├── env.py
│   │   └── alembic.ini
│   ├── tests/
│   │   ├── conftest.py           # Shared fixtures
│   │   ├── unit/
│   │   │   ├── test_services/
│   │   │   ├── test_quant/
│   │   │   └── test_repositories/
│   │   ├── integration/
│   │   │   ├── test_api/
│   │   │   └── test_tasks/
│   │   └── e2e/
│   ├── pyproject.toml            # Python project config (uv/poetry)
│   ├── .env.example
│   └── Dockerfile
│
├── docker-compose.yml             # PostgreSQL, Redis, backend services
├── .gitignore
└── README.md
```

### File Naming Conventions

#### Frontend (TypeScript / React Native)
- **Route files:** `lowercase.tsx` (Expo Router convention, e.g., `portfolio.tsx`, `[symbol].tsx`)
- **Components:** `PascalCase.tsx` (e.g., `CandlestickChart.tsx`, `TradeCard.tsx`)
- **Hooks:** `camelCase.ts` prefixed with `use` (e.g., `usePortfolio.ts`, `useWebSocket.ts`)
- **Stores:** `camelCase.ts` suffixed with `Store` (e.g., `portfolioStore.ts`, `marketStore.ts`)
- **Types:** `camelCase.ts` (e.g., `stock.ts`, `portfolio.ts`)
- **Services:** `camelCase.ts` (e.g., `apiClient.ts`, `webSocketManager.ts`)
- **Constants:** `camelCase.ts` (e.g., `colors.ts`, `endpoints.ts`)

#### Backend (Python / FastAPI)
- **All files:** `snake_case.py` (e.g., `trading_service.py`, `market_data_service.py`)
- **Migration files:** Auto-generated by Alembic with timestamp prefix
- **Test files:** `test_module_name.py` (e.g., `test_trading_service.py`)

---

## 2. React Native (Expo) Patterns

### Expo SDK & Router

**Use Expo SDK 52+ with Expo Router v4+ for file-based routing.**

```typescript
// app/(tabs)/_layout.tsx
import { Tabs } from 'expo-router';
import { PortfolioIcon, MarketsIcon, TradeIcon, SettingsIcon } from '@/components/ui/Icons';

export default function TabLayout() {
  return (
    <Tabs screenOptions={{ headerShown: false, tabBarStyle: styles.tabBar }}>
      <Tabs.Screen name="portfolio" options={{ title: 'Portfolio', tabBarIcon: PortfolioIcon }} />
      <Tabs.Screen name="markets" options={{ title: 'Markets', tabBarIcon: MarketsIcon }} />
      <Tabs.Screen name="trade" options={{ title: 'Trade', tabBarIcon: TradeIcon }} />
      <Tabs.Screen name="settings" options={{ title: 'Settings', tabBarIcon: SettingsIcon }} />
    </Tabs>
  );
}
```

### Component Structure

```typescript
// components/trade/TradeCard.tsx
interface TradeCardProps {
  trade: Trade;
  onPress: (tradeId: string) => void;
}

export function TradeCard({ trade, onPress }: TradeCardProps) {
  // 1. Hooks first
  const { colors } = useTheme();
  const profitColor = trade.profitLoss >= 0 ? colors.profit : colors.loss;

  // 2. Derived state
  const formattedPL = formatCurrency(trade.profitLoss);
  const plPercent = formatPercent(trade.profitLossPercent);

  // 3. Event handlers
  const handlePress = () => onPress(trade.id);

  // 4. Return JSX
  return (
    <Pressable onPress={handlePress} className="bg-surface rounded-2xl p-4 mb-3">
      <Text className="text-text-primary font-semibold text-lg">{trade.symbol}</Text>
      <Text style={{ color: profitColor }} className="font-bold text-xl">
        {formattedPL} ({plPercent})
      </Text>
    </Pressable>
  );
}
```

### State Management with Zustand

```typescript
// stores/portfolioStore.ts
import { create } from 'zustand';
import { apiClient } from '@/services/apiClient';

interface PortfolioState {
  holdings: Holding[];
  totalValue: number;
  dailyChange: number;
  isLoading: boolean;
  error: string | null;
  fetchPortfolio: () => Promise<void>;
  clearError: () => void;
}

export const usePortfolioStore = create<PortfolioState>((set) => ({
  holdings: [],
  totalValue: 0,
  dailyChange: 0,
  isLoading: false,
  error: null,

  fetchPortfolio: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await apiClient.get<PortfolioResponse>('/api/v1/portfolio');
      set({ holdings: data.holdings, totalValue: data.totalValue, dailyChange: data.dailyChange, isLoading: false });
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
    }
  },

  clearError: () => set({ error: null }),
}));
```

### API Client

```typescript
// services/apiClient.ts
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import { API_BASE_URL } from '@/constants/endpoints';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async getToken(): Promise<string | null> {
    if (Platform.OS === 'web') {
      return localStorage.getItem('auth_token');
    }
    return SecureStore.getItemAsync('auth_token');
  }

  async get<T>(path: string): Promise<T> {
    const token = await this.getToken();
    const response = await fetch(`${this.baseUrl}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    return response.json();
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    const token = await this.getToken();
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    return response.json();
  }

  // PUT, DELETE follow same pattern
}

export const apiClient = new ApiClient(API_BASE_URL);
```

### WebSocket Manager

```typescript
// services/webSocketManager.ts
import { WS_BASE_URL } from '@/constants/endpoints';

type MessageHandler = (data: unknown) => void;

class WebSocketManager {
  private ws: WebSocket | null = null;
  private handlers: Map<string, Set<MessageHandler>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect(token: string): void {
    this.ws = new WebSocket(`${WS_BASE_URL}/ws/market?token=${token}`);

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      const handlers = this.handlers.get(message.type);
      if (handlers) {
        handlers.forEach((handler) => handler(message.data));
      }
    };

    this.ws.onclose = () => {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        setTimeout(() => this.connect(token), Math.min(1000 * 2 ** this.reconnectAttempts, 30000));
      }
    };

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
    };
  }

  subscribe(type: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set());
    }
    this.handlers.get(type)!.add(handler);

    // Return unsubscribe function
    return () => {
      this.handlers.get(type)?.delete(handler);
    };
  }

  disconnect(): void {
    this.maxReconnectAttempts = 0; // Prevent reconnection
    this.ws?.close();
    this.ws = null;
  }
}

export const wsManager = new WebSocketManager();
```

### React Native Anti-Patterns
- **NEVER** use inline styles for frequently re-rendered components — use NativeWind/StyleSheet
- **NEVER** store derived state — compute it during render
- **NEVER** use `useEffect` for event-driven logic — use event handlers
- **NEVER** use `setTimeout`/`setInterval` without cleanup in `useEffect`
- **AVOID** prop drilling deeper than 2 levels — use Zustand
- **AVOID** large `FlatList` items without `React.memo` — profile first
- **AVOID** heavy computation on the JS thread — use `runOnUI` from Reanimated for animations
- **AVOID** `expo-secure-store` on web — use `localStorage` with platform check

### Platform-Specific Code

```typescript
// Use Platform.select for small differences
import { Platform } from 'react-native';

const shadowStyle = Platform.select({
  ios: { shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 8 },
  android: { elevation: 4 },
  web: { boxShadow: '0 2px 8px rgba(0,0,0,0.1)' },
});

// Use .native.tsx / .web.tsx for large divergences
// components/charts/CandlestickChart.native.tsx  — uses react-native-skia
// components/charts/CandlestickChart.web.tsx      — uses lightweight-charts
```

---

## 3. TypeScript Conventions (Frontend)

### Strict Configuration

```json
// tsconfig.json
{
  "extends": "expo/tsconfig.base",
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

### Type Definitions

```typescript
// types/stock.ts
export interface Stock {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  marketCap: number;
}

export interface OHLCV {
  timestamp: string;   // ISO 8601
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// types/portfolio.ts
export interface Holding {
  id: string;
  symbol: string;
  shares: number;
  avgCost: number;
  currentPrice: number;
  totalValue: number;
  profitLoss: number;
  profitLossPercent: number;
}

export interface Portfolio {
  id: string;
  userId: string;
  type: 'simulation' | 'live';
  balance: number;
  totalValue: number;
  holdings: Holding[];
  createdAt: string;
}

// types/trade.ts
export type OrderSide = 'buy' | 'sell';
export type OrderType = 'market' | 'limit' | 'stop' | 'stop_limit';
export type OrderStatus = 'pending' | 'filled' | 'partial' | 'cancelled' | 'rejected';

export interface Trade {
  id: string;
  portfolioId: string;
  symbol: string;
  side: OrderSide;
  type: OrderType;
  quantity: number;
  price: number;
  status: OrderStatus;
  filledAt: string | null;
  createdAt: string;
}
```

### TypeScript Rules
- **ALWAYS** use `interface` for object shapes, `type` for unions/intersections/mapped types
- **ALWAYS** use `unknown` over `any` — narrow with type guards
- **NEVER** use `@ts-ignore` — use `@ts-expect-error` with a reason if absolutely necessary
- **NEVER** use `as` type assertions to silence errors — fix the types
- **PREFER** discriminated unions over optional fields for variant types
- **PREFER** `readonly` for arrays/objects that should not be mutated

---

## 4. Python + FastAPI Patterns (Backend)

### Configuration with pydantic-settings

```python
# app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Application
    app_name: str = "QuantTrader API"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str  # postgresql+asyncpg://user:pass@host/db
    redis_url: str     # redis://localhost:6379

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Broker
    alpaca_api_key: str
    alpaca_secret_key: str
    alpaca_base_url: str = "https://paper-api.alpaca.markets"  # Paper by default

    # Celery
    celery_broker_url: str  # redis://localhost:6379/1

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### FastAPI App Entry Point

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.api.v1.router import api_v1_router
from app.core.middleware import RateLimitMiddleware
from app.websockets.market_feed import market_feed_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize DB pool, Redis, etc.
    yield
    # Shutdown: close connections

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix=settings.api_v1_prefix)
app.include_router(market_feed_router)
```

### API Route Pattern

```python
# app/api/v1/portfolio.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas.portfolio import PortfolioResponse, CreatePortfolioRequest
from app.services.portfolio_service import PortfolioService
from app.models.user import User

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

@router.get("/", response_model=PortfolioResponse)
async def get_portfolio(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PortfolioService(db)
    portfolio = await service.get_user_portfolio(current_user.id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return portfolio

@router.post("/", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    request: CreatePortfolioRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PortfolioService(db)
    return await service.create_portfolio(current_user.id, request)
```

### Service Layer Pattern

```python
# app/services/portfolio_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.portfolio_repository import PortfolioRepository
from app.schemas.portfolio import CreatePortfolioRequest, PortfolioResponse

class PortfolioService:
    def __init__(self, db: AsyncSession):
        self.repo = PortfolioRepository(db)

    async def get_user_portfolio(self, user_id: str) -> PortfolioResponse | None:
        portfolio = await self.repo.get_by_user_id(user_id)
        if not portfolio:
            return None
        holdings = await self.repo.get_holdings(portfolio.id)
        return PortfolioResponse.model_validate({
            **portfolio.__dict__,
            "holdings": [h.__dict__ for h in holdings],
        })

    async def create_portfolio(self, user_id: str, request: CreatePortfolioRequest) -> PortfolioResponse:
        portfolio = await self.repo.create(user_id=user_id, portfolio_type=request.type, initial_balance=request.initial_balance)
        return PortfolioResponse.model_validate({**portfolio.__dict__, "holdings": []})
```

### Repository Pattern

```python
# app/repositories/portfolio_repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.portfolio import Portfolio, Holding

class PortfolioRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_id(self, user_id: str) -> Portfolio | None:
        result = await self.db.execute(select(Portfolio).where(Portfolio.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_holdings(self, portfolio_id: str) -> list[Holding]:
        result = await self.db.execute(select(Holding).where(Holding.portfolio_id == portfolio_id))
        return list(result.scalars().all())

    async def create(self, user_id: str, portfolio_type: str, initial_balance: float) -> Portfolio:
        portfolio = Portfolio(user_id=user_id, type=portfolio_type, balance=initial_balance)
        self.db.add(portfolio)
        await self.db.commit()
        await self.db.refresh(portfolio)
        return portfolio
```

### Pydantic Schema Pattern

```python
# app/schemas/portfolio.py
from pydantic import BaseModel, Field
from datetime import datetime

class HoldingSchema(BaseModel):
    id: str
    symbol: str
    shares: float
    avg_cost: float
    current_price: float
    total_value: float
    profit_loss: float
    profit_loss_percent: float

    model_config = {"from_attributes": True}

class PortfolioResponse(BaseModel):
    id: str
    user_id: str
    type: str  # 'simulation' | 'live'
    balance: float
    total_value: float
    holdings: list[HoldingSchema]
    created_at: datetime

    model_config = {"from_attributes": True}

class CreatePortfolioRequest(BaseModel):
    type: str = Field(..., pattern="^(simulation|live)$")
    initial_balance: float = Field(default=100000.0, gt=0)
```

### SQLAlchemy Model Pattern

```python
# app/models/portfolio.py
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.models import Base

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String, nullable=False)  # 'simulation' | 'live'
    balance = Column(Float, nullable=False, default=0.0)
    total_value = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    user = relationship("User", back_populates="portfolios")

class Holding(Base):
    __tablename__ = "holdings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id = Column(String, ForeignKey("portfolios.id"), nullable=False, index=True)
    symbol = Column(String(10), nullable=False)
    shares = Column(Float, nullable=False)
    avg_cost = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    portfolio = relationship("Portfolio", back_populates="holdings")
```

### Python Anti-Patterns
- **NEVER** use `except Exception: pass` — always log or re-raise
- **NEVER** use `from module import *` — explicit imports only
- **NEVER** use mutable default arguments (`def f(items=[])`) — use `None` and initialize inside
- **NEVER** build SQL by string concatenation — use SQLAlchemy ORM or parameterized queries
- **NEVER** store secrets in source code — use `.env` and `pydantic-settings`
- **AVOID** sync blocking calls in async handlers — use `asyncio.to_thread()` for CPU-bound work
- **AVOID** deeply nested functions — extract to service/repository layer
- **AVOID** `time.sleep()` in async code — use `asyncio.sleep()`

---

## 5. Quant Strategy Module Patterns

### Strategy Engine Architecture

```python
# app/services/quant/strategy_engine.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
import pandas as pd

@dataclass
class Signal:
    symbol: str
    action: str  # 'buy' | 'sell' | 'hold'
    confidence: float  # 0.0 to 1.0
    reason: str
    target_price: float | None = None
    stop_loss: float | None = None

class BaseStrategy(ABC):
    """All quant strategies must inherit from this base class."""

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def analyze(self, symbol: str, data: pd.DataFrame) -> Signal:
        """Analyze OHLCV data and return a trading signal."""
        ...

    @abstractmethod
    def required_lookback_days(self) -> int:
        """Minimum days of historical data needed."""
        ...
```

### Risk Manager

```python
# app/services/quant/risk_manager.py
class RiskManager:
    """Validates trades against risk rules before execution."""

    def __init__(self, max_position_pct: float = 0.10, max_portfolio_risk_pct: float = 0.02):
        self.max_position_pct = max_position_pct
        self.max_portfolio_risk_pct = max_portfolio_risk_pct

    def validate_trade(self, portfolio_value: float, trade_value: float, current_exposure: float) -> bool:
        """Return True if trade passes risk checks."""
        # Single position must not exceed max_position_pct of portfolio
        if trade_value / portfolio_value > self.max_position_pct:
            return False
        # Total exposure must not exceed limits
        if (current_exposure + trade_value) / portfolio_value > 0.80:
            return False
        return True

    def calculate_position_size(self, portfolio_value: float, entry_price: float, stop_loss: float) -> int:
        """Calculate position size based on risk-per-trade."""
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share == 0:
            return 0
        max_risk_amount = portfolio_value * self.max_portfolio_risk_pct
        shares = int(max_risk_amount / risk_per_share)
        # Cap at max_position_pct
        max_shares = int((portfolio_value * self.max_position_pct) / entry_price)
        return min(shares, max_shares)
```

### Quant Module Rules
- **ALWAYS** validate signals through RiskManager before execution
- **ALWAYS** use stop-loss orders on live trades — no naked positions
- **ALWAYS** log every trade decision with reasoning for audit trail
- **NEVER** execute live trades without explicit user authorization
- **NEVER** risk more than 2% of portfolio on a single trade
- **NEVER** hold more than 10% of portfolio in a single position (live mode)
- **SEPARATE** simulation logic from live trading — different code paths, clearly marked
- **TEST** strategies with backtesting before deploying to live

---

## 6. Database (PostgreSQL + TimescaleDB + Redis)

### PostgreSQL with TimescaleDB

```sql
-- Time-series hypertable for OHLCV data
CREATE TABLE stock_prices (
    symbol TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume BIGINT NOT NULL
);

-- Convert to TimescaleDB hypertable for efficient time-series queries
SELECT create_hypertable('stock_prices', 'timestamp');

-- Create indexes
CREATE INDEX idx_stock_prices_symbol_time ON stock_prices (symbol, timestamp DESC);

-- Continuous aggregate for daily summaries
CREATE MATERIALIZED VIEW daily_stock_summary
WITH (timescaledb.continuous) AS
SELECT
    symbol,
    time_bucket('1 day', timestamp) AS day,
    first(open, timestamp) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, timestamp) AS close,
    sum(volume) AS volume
FROM stock_prices
GROUP BY symbol, time_bucket('1 day', timestamp);
```

### Alembic Migrations

```python
# alembic/env.py — async migration configuration
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import get_settings

settings = get_settings()
# Use async engine for migrations
```

### Redis Usage

```python
# Cache market data (TTL 15 seconds for real-time quotes)
await redis.setex(f"quote:{symbol}", 15, json.dumps(quote_data))

# Pub/Sub for real-time broadcast
await redis.publish("market:updates", json.dumps({"symbol": symbol, "price": price}))

# Celery task broker
CELERY_BROKER_URL = "redis://localhost:6379/1"
```

### Database Rules
- **ALWAYS** use Alembic for schema migrations — no manual DDL in production
- **ALWAYS** use async SQLAlchemy (`asyncpg` driver) in FastAPI
- **ALWAYS** use connection pooling (`pool_size`, `max_overflow` in engine config)
- **ALWAYS** add indexes on columns used in WHERE/ORDER BY/JOIN
- **ALWAYS** use TimescaleDB hypertables for time-series stock data
- **ALWAYS** set appropriate TTLs on Redis cache keys
- **NEVER** store financial amounts as floating point in final calculations — use `Decimal` for money
- **PREFER** database-level constraints (CHECK, UNIQUE, NOT NULL) over application-only validation

---

## 7. UI / Styling Conventions (NativeWind)

### NativeWind (Tailwind for React Native)

```typescript
// tailwind.config.ts
module.exports = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        // Trading-specific semantic colors
        profit: '#00E676',
        loss: '#FF1744',
        // Dark theme palette
        surface: {
          DEFAULT: '#1A1B2E',
          secondary: '#232440',
          tertiary: '#2D2E4A',
        },
        text: {
          primary: '#E8E8F0',
          secondary: '#9394B0',
          muted: '#5D5E7A',
        },
        accent: {
          DEFAULT: '#6C63FF',
          cyan: '#00BCD4',
          gold: '#FFD54F',
        },
        border: '#3A3B5C',
      },
      fontFamily: {
        sans: ['Inter', 'System'],
        mono: ['JetBrainsMono', 'Courier'],
      },
    },
  },
};
```

### Artistic UI Guidelines
- **Dark theme as default** — financial apps are often viewed for long periods
- Use **glassmorphism** effects: semi-transparent backgrounds + backdrop blur
- **Profit/loss color coding**: green (`#00E676`) for gains, red (`#FF1744`) for losses — universally recognized
- **Smooth transitions** on all state changes (200-400ms, spring physics via Reanimated)
- Use **React Native Skia** for custom candlestick charts and sparkline visualizations
- **Gradient accents** on key UI elements (buttons, headers, active indicators)
- **Monospace font** (JetBrains Mono) for all numbers and prices — easier to scan columns
- Minimal borders — use shadows and background contrast for separation
- **Haptic feedback** on trade execution (iOS/Android) via `expo-haptics`
- **Pull-to-refresh** on all data screens with smooth animation

### Chart Components

```typescript
// components/charts/CandlestickChart.tsx — use @shopify/react-native-skia
import { Canvas, Path, Group } from '@shopify/react-native-skia';

interface CandlestickChartProps {
  data: OHLCV[];
  width: number;
  height: number;
}

export function CandlestickChart({ data, width, height }: CandlestickChartProps) {
  // Draw candles using Skia for GPU-accelerated rendering
  // Green candle: close > open
  // Red candle: close < open
  // ...
}
```

### Responsive Design
- Use `useWindowDimensions()` for responsive layouts
- Web: wider layouts with side-by-side panels
- Mobile: stacked layouts with bottom tab navigation
- Tablet: adaptive grid that switches between layouts

---

## 8. Recommended Libraries

### Frontend (React Native / Expo)

| Purpose | Library | Why |
|---------|---------|-----|
| Framework | Expo SDK 52+ | Managed workflow, OTA updates, cross-platform |
| Routing | Expo Router v4+ | File-based routing, deep linking, web support |
| State | Zustand | Minimal boilerplate, TypeScript-first |
| Styling | NativeWind v4 | Tailwind CSS for React Native, web compatible |
| Charts | @shopify/react-native-skia | GPU-accelerated custom chart rendering |
| Animations | react-native-reanimated | Hardware-accelerated 60fps animations |
| Gestures | react-native-gesture-handler | Native gesture recognition |
| Secure storage | expo-secure-store | Keychain (iOS) / Keystore (Android) |
| HTTP client | Built-in fetch | No extra dependency needed |
| Icons | @expo/vector-icons | Large icon set included with Expo |
| Haptics | expo-haptics | Tactile feedback on trades |
| Linting | ESLint + typescript-eslint | Static analysis |
| Formatting | Prettier | Consistent code formatting |
| Testing | Jest + React Native Testing Library | Expo-compatible test runner |

### Backend (Python / FastAPI)

| Purpose | Library | Why |
|---------|---------|-----|
| Framework | FastAPI | Async, auto-docs, type validation |
| ORM | SQLAlchemy 2.0+ (async) | Mature, async support, excellent PostgreSQL integration |
| Migrations | Alembic | Standard SQLAlchemy migration tool |
| Validation | Pydantic v2 | Fast, built into FastAPI |
| Auth | python-jose + passlib[bcrypt] | JWT + secure password hashing |
| Task queue | Celery + Redis | Reliable background job processing |
| Market data | yfinance + alpaca-trade-api | Free data + paper/live trading |
| Quant | pandas + numpy + ta-lib | Industry standard for financial analysis |
| Config | pydantic-settings | Type-safe env config |
| Testing | pytest + pytest-asyncio + httpx | Async test support for FastAPI |
| Linting | ruff | Fast Python linter + formatter |
| DB driver | asyncpg | Fast async PostgreSQL driver |
| Redis | redis[hiredis] | Async Redis client with C extension |
| WebSockets | FastAPI built-in | Native WebSocket support |

### Libraries to AVOID
- **Redux / MobX** — overkill; Zustand is sufficient
- **Axios** — `fetch` is built-in and works cross-platform in React Native
- **Moment.js** — deprecated; use `date-fns` if needed
- **Django / Flask** — FastAPI is better for async + WebSocket + auto-docs
- **SQLite on backend** — not suitable for concurrent multi-user trading app
- **Mongoose / MongoDB** — relational data (portfolios, trades, users) fits PostgreSQL better
- **Socket.IO** — FastAPI native WebSockets are simpler and sufficient

---

## 9. Testing

### Frontend Testing (Jest + RNTL)

```typescript
// components/trade/__tests__/TradeCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react-native';
import { TradeCard } from '../TradeCard';

describe('TradeCard', () => {
  const mockTrade: Trade = {
    id: '1',
    portfolioId: 'p1',
    symbol: 'AAPL',
    side: 'buy',
    type: 'market',
    quantity: 10,
    price: 150.0,
    status: 'filled',
    filledAt: '2026-01-01T00:00:00Z',
    createdAt: '2026-01-01T00:00:00Z',
  };

  it('renders trade symbol and quantity', () => {
    render(<TradeCard trade={mockTrade} onPress={jest.fn()} />);
    expect(screen.getByText('AAPL')).toBeTruthy();
  });

  it('calls onPress with trade id', () => {
    const onPress = jest.fn();
    render(<TradeCard trade={mockTrade} onPress={onPress} />);
    fireEvent.press(screen.getByText('AAPL'));
    expect(onPress).toHaveBeenCalledWith('1');
  });
});
```

### Backend Testing (pytest + httpx)

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.dependencies import get_db
from app.models import Base

TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/test_quanttrader"

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()

# tests/unit/test_services/test_portfolio_service.py
@pytest.mark.asyncio
async def test_create_simulation_portfolio(db_session):
    service = PortfolioService(db_session)
    request = CreatePortfolioRequest(type="simulation", initial_balance=100000.0)
    portfolio = await service.create_portfolio("user-1", request)

    assert portfolio.type == "simulation"
    assert portfolio.balance == 100000.0
    assert portfolio.holdings == []

# tests/unit/test_quant/test_risk_manager.py
def test_reject_oversized_position():
    rm = RiskManager(max_position_pct=0.10)
    # Trade is 15% of portfolio — should reject
    assert rm.validate_trade(portfolio_value=100000, trade_value=15000, current_exposure=0) is False

def test_accept_valid_position():
    rm = RiskManager(max_position_pct=0.10)
    # Trade is 5% of portfolio — should accept
    assert rm.validate_trade(portfolio_value=100000, trade_value=5000, current_exposure=0) is True
```

### Test Organization
- **Frontend:** Co-locate tests in `__tests__/` next to source files
- **Backend:** Separate `tests/unit/`, `tests/integration/`, `tests/e2e/` directories
- **Quant strategies:** Test with historical data fixtures; verify signal accuracy

### What to Test
- **Components:** Rendering, user interactions, conditional display, color coding (profit/loss)
- **Stores:** State transitions, API call integration, error states
- **API routes:** Request validation, response format, auth enforcement, error responses
- **Services:** Business logic, edge cases (zero balance, negative values)
- **Quant strategies:** Signal generation against known historical patterns
- **Risk manager:** Position sizing, rejection of over-limit trades
- **WebSockets:** Connection lifecycle, message parsing, reconnection

---

## 10. Build & Deployment

### Frontend (Expo)

```json
// package.json scripts
{
  "scripts": {
    "start": "expo start",
    "android": "expo start --android",
    "ios": "expo start --ios",
    "web": "expo start --web",
    "lint": "eslint . --ext .ts,.tsx",
    "format": "prettier --write .",
    "test": "jest",
    "build:web": "expo export -p web",
    "build:ios": "eas build --platform ios",
    "build:android": "eas build --platform android"
  }
}
```

### Backend (FastAPI)

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for TA-Lib
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libta-lib-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: ./backend/.env
    depends_on:
      - postgres
      - redis

  celery-worker:
    build: ./backend
    command: celery -A app.tasks.celery_app worker --loglevel=info
    env_file: ./backend/.env
    depends_on:
      - postgres
      - redis

  celery-beat:
    build: ./backend
    command: celery -A app.tasks.celery_app beat --loglevel=info
    env_file: ./backend/.env
    depends_on:
      - redis

  postgres:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_USER: quanttrader
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: quanttrader
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

### Environment Variables (.env.example)

```bash
# Backend
DATABASE_URL=postgresql+asyncpg://quanttrader:password@localhost:5432/quanttrader
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=change-me-to-a-random-256-bit-key
ALPACA_API_KEY=your-alpaca-api-key
ALPACA_SECRET_KEY=your-alpaca-secret-key
ALPACA_BASE_URL=https://paper-api.alpaca.markets
CELERY_BROKER_URL=redis://localhost:6379/1
POSTGRES_PASSWORD=change-me

# Frontend
EXPO_PUBLIC_API_BASE_URL=http://localhost:8000
EXPO_PUBLIC_WS_BASE_URL=ws://localhost:8000
```

---

## 11. Security Considerations

### Frontend
- **ALWAYS** store auth tokens in `expo-secure-store` (mobile) — never `AsyncStorage`
- **ALWAYS** use HTTPS for all API calls in production
- **NEVER** store sensitive data in React state or Zustand that persists to disk
- **NEVER** log auth tokens or API keys
- **VALIDATE** all numeric inputs (trade amounts, quantities) before sending to backend
- **IMPLEMENT** biometric authentication (FaceID/TouchID) via `expo-local-authentication` for trade confirmation

### Backend
- **ALWAYS** use bcrypt/argon2 for password hashing — never MD5/SHA
- **ALWAYS** validate and sanitize all request inputs via Pydantic schemas
- **ALWAYS** use parameterized queries (SQLAlchemy ORM handles this)
- **ALWAYS** set short JWT expiry (30 min access token, 7 day refresh token)
- **ALWAYS** rate-limit sensitive endpoints (login, trade execution)
- **NEVER** include sensitive data in JWT payload — only user ID and expiry
- **NEVER** expose stack traces in production — use custom exception handlers
- **NEVER** allow trade execution without re-authentication for live accounts
- **LOG** all trade actions with user ID, timestamp, and trade details for audit
- **IMPLEMENT** CORS properly — restrict origins in production

### Trading-Specific Security
- **Paper/live mode must be clearly separated** — different API keys, different database flags
- **Double-confirm live trades** — require explicit user action, not just strategy signals
- **Maximum daily loss limit** — automatically pause trading if daily loss exceeds threshold
- **API key rotation** — broker API keys should be rotatable without downtime

---

## 12. Performance Patterns

### Frontend
- Use `React.memo()` only when profiling confirms unnecessary re-renders
- Use `useMemo`/`useCallback` only for expensive computations
- **FlatList** for all scrollable lists — never `ScrollView` with `.map()` for dynamic data
- Use `getItemLayout` on `FlatList` when item heights are fixed (trade history, holdings)
- **Throttle** WebSocket updates to UI (e.g., 250ms batching for real-time prices)
- Use `InteractionManager.runAfterInteractions()` for heavy computation after navigation
- **Skeleton screens** instead of spinners for loading states

### Backend
- **Connection pooling** for PostgreSQL (SQLAlchemy `pool_size=20, max_overflow=10`)
- **Redis caching** for frequently accessed data (stock quotes: 15s TTL, user portfolio: 60s TTL)
- **Batch database writes** — use bulk insert for historical price data
- **Pagination** for all list endpoints (trades, holdings, price history)
- **Background tasks** (Celery) for all heavy computation (backtesting, strategy analysis)
- Use `asyncio.gather()` for concurrent I/O operations
- **N+1 prevention** — use `selectinload()` or `joinedload()` in SQLAlchemy queries
- **TimescaleDB compression** for old price data (>30 days)

---

## 13. Error Handling

### Frontend

```typescript
// Global error handler for unhandled promise rejections
import { ErrorBoundary } from 'react-error-boundary';

function GlobalErrorFallback({ error, resetErrorBoundary }: { error: Error; resetErrorBoundary: () => void }) {
  return (
    <View className="flex-1 items-center justify-center bg-surface p-6">
      <Text className="text-text-primary text-xl font-semibold mb-2">Something went wrong</Text>
      <Text className="text-text-secondary mb-4">{error.message}</Text>
      <Pressable onPress={resetErrorBoundary} className="bg-accent px-6 py-3 rounded-xl">
        <Text className="text-white font-semibold">Try Again</Text>
      </Pressable>
    </View>
  );
}
```

### Backend

```python
# app/core/exceptions.py
from fastapi import HTTPException, status

class InsufficientFundsError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient funds for this trade")

class MarketClosedError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail="Market is currently closed")

class RiskLimitExceededError(HTTPException):
    def __init__(self, reason: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Risk limit exceeded: {reason}")

# app/main.py — global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

### Rules
- **NEVER** silently swallow errors — log and handle or re-raise
- **ALWAYS** show user-friendly error messages in the UI (never raw stack traces)
- **ALWAYS** log errors with context (user ID, endpoint, request body) server-side
- **USE** toast/snackbar notifications for transient errors (network failures, etc.)
- **USE** full-screen error states for critical failures (auth failure, data load failure)
- **IMPLEMENT** retry logic for transient network errors (exponential backoff, max 3 retries)

---

**Version**: v1.0.0
**Stack**: TypeScript + React Native (Expo) + Python + FastAPI + PostgreSQL + Redis
**Last Updated**: 2026-03-31
