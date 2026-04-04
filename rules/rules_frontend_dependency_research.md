# Frontend Dependency Research: Quant Trading Dashboard

> Comprehensive documentation research for all frontend dependencies used in the React+Vite quant trading dashboard.
> Researched: 2026-04-03

---

## 1. React 19 -- UI Framework

**Official Docs:** https://react.dev
**Latest Stable:** React 19.2 (React 19 released Dec 2024, patch 19.2 released Oct 2025)
**Key Blog Post:** https://react.dev/blog/2024/12/05/react-19

### New Hooks in React 19

#### `use()` -- Read Resources in Render
Unlike other hooks, `use` can be called inside loops, conditionals, and early returns. It works with Promises (triggers Suspense) and Context.

```tsx
import { use, Suspense } from 'react';

function Comments({ commentsPromise }: { commentsPromise: Promise<Comment[]> }) {
  const comments = use(commentsPromise);
  return comments.map(comment => <p key={comment.id}>{comment.text}</p>);
}

function Page({ commentsPromise }: { commentsPromise: Promise<Comment[]> }) {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <Comments commentsPromise={commentsPromise} />
    </Suspense>
  );
}
```

Conditional context reading (not possible with `useContext`):
```tsx
function Heading({ children }: { children: React.ReactNode }) {
  if (children == null) return null;
  const theme = use(ThemeContext);
  return <h1 style={{ color: theme.color }}>{children}</h1>;
}
```

#### `useActionState` -- Form State Management
Manages pending state, errors, and return values for async form actions.

```tsx
import { useActionState } from 'react';

const [error, submitAction, isPending] = useActionState(
  async (previousState: string | null, formData: FormData) => {
    const error = await updateName(formData.get("name") as string);
    if (error) return error;
    redirect("/path");
    return null;
  },
  null,
);

return (
  <form action={submitAction}>
    <input type="text" name="name" />
    <button type="submit" disabled={isPending}>Update</button>
    {error && <p>{error}</p>}
  </form>
);
```

#### `useFormStatus` -- Access Parent Form State (No Prop Drilling)
```tsx
import { useFormStatus } from 'react-dom';

function SubmitButton() {
  const { pending } = useFormStatus();
  return <button type="submit" disabled={pending}>Submit</button>;
}
```

#### `useOptimistic` -- Optimistic UI Updates
```tsx
import { useOptimistic } from 'react';

function ChangeName({ currentName, onUpdateName }: Props) {
  const [optimisticName, setOptimisticName] = useOptimistic(currentName);

  const submitAction = async (formData: FormData) => {
    const newName = formData.get("name") as string;
    setOptimisticName(newName); // Show immediately
    const updatedName = await updateName(newName);
    onUpdateName(updatedName);
  };

  return (
    <form action={submitAction}>
      <p>Your name is: {optimisticName}</p>
      <input type="text" name="name" />
    </form>
  );
}
```

### Breaking Changes / Gotchas

- **`ref` as a prop**: Function components now accept `ref` directly -- `forwardRef` is no longer needed:
  ```tsx
  function MyInput({ placeholder, ref }: { placeholder: string; ref: React.Ref<HTMLInputElement> }) {
    return <input placeholder={placeholder} ref={ref} />;
  }
  ```

- **Ref cleanup functions**: Refs now support cleanup like `useEffect`:
  ```tsx
  <input ref={(ref) => {
    // setup
    return () => { /* cleanup when removed */ };
  }} />
  ```

- **Context as Provider**: Simplified syntax -- use `<ThemeContext value="dark">` instead of `<ThemeContext.Provider value="dark">`.

- **`useDeferredValue` initial value**: Now accepts an initial value for first render:
  ```tsx
  const value = useDeferredValue(deferredValue, '');
  ```

- **Server Components**: Render before bundling to reduce client bundle. **For Vite (non-framework) usage, Server Components are NOT directly supported** -- they require a framework like Next.js or a custom RSC setup. For our Vite dashboard, stick with Client Components.

- **Improved error reporting**: Single error log instead of duplicates, plus new root error handlers: `onCaughtError`, `onUncaughtError`, `onRecoverableError`.

---

## 2. Vite 8 -- Build Tool

**Official Docs:** https://vite.dev
**Latest Stable:** Vite 8.x (released early 2026)
**Announcement:** https://vite.dev/blog/announcing-vite8
**Config Reference:** https://vite.dev/config/

### Major Architecture Change: Rolldown

Vite 8 replaces the dual-bundler approach (esbuild for dev + Rollup for prod) with **Rolldown**, a single Rust-based bundler. Performance gains: **10-30x faster builds**.

- Real-world benchmarks: Linear 46s to 6s, Beehiiv 64% reduction.
- Most projects require **no configuration changes** to migrate.
- Existing `rollupOptions` configs auto-convert to Rolldown equivalents.

### Node.js Requirement
**Node.js 20.19+ or 22.12+** (dropped older Node support).

### React Plugin Setup

`@vitejs/plugin-react` v6 now uses **Oxc for React Refresh transforms** (removed Babel dependency):

```ts
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
});
```

### Proxy Configuration for FastAPI Backend

```ts
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',  // FastAPI server
        changeOrigin: true,
        // If FastAPI routes don't have /api prefix:
        // rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/ws': {
        target: 'ws://localhost:8000',    // WebSocket for real-time data
        ws: true,
      },
    },
  },
});
```

**IMPORTANT**: `server.proxy` only works in dev mode. In production, configure your reverse proxy (nginx/caddy) or deploy behind the same origin.

### Environment Variables

```ts
// .env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws

// Usage in code (must be prefixed with VITE_)
const apiUrl = import.meta.env.VITE_API_BASE_URL;
```

### New Features in Vite 8

- **TypeScript path alias resolution**: `resolve.tsconfigPaths: true` (opt-in, small perf cost)
- **Standard decorators**: Work out-of-the-box (good for metadata-heavy patterns)
- **Browser console forwarding**: `server.forwardConsole` -- forwards browser console to terminal
- **Built-in devtools**: `devtools` config option for module graph inspection
- **Install size**: ~15 MB larger than Vite 7 (lightningcss + Rolldown binary)

### Build Config

```ts
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    sourcemap: true,
    target: 'es2020',     // Match lightweight-charts target
  },
  resolve: {
    tsconfigPaths: true,  // New in Vite 8: native TS path alias support
  },
});
```

---

## 3. TypeScript 5.7

**Official Docs:** https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-7.html
**Announcement:** https://devblogs.microsoft.com/typescript/announcing-typescript-5-7/
**Latest:** TypeScript 5.7 (note: 5.8 and 5.9 also exist as of April 2026)

### Key Features

#### Checks for Never-Initialized Variables
TypeScript 5.7 now detects variables that have never been assigned a value, not just possibly-uninitialized ones:

```ts
let x: number;
function doSomething() {
  console.log(x); // Error: Variable 'x' is used before being assigned.
}
```

#### `--rewriteRelativeImportExtensions`
Automatically rewrites `.ts`/`.tsx` to `.js`/`.jsx` in relative imports during compilation. Only works for paths starting with `./` or `../`.

#### ES2024 Support (`--target es2024`)
Enables: `Object.groupBy()`, `Map.groupBy()`, `Promise.withResolvers()`, typed `SharedArrayBuffer`/`ArrayBuffer`.

#### JSON Import Enforcement (under `--module nodenext`)
```ts
import data from './data.json' with { type: "json" };
// Must use import attribute and default import only
```

#### V8 Compile Caching
Leverages Node.js 22's `module.enableCompileCache()` for ~2.5x faster startup on repeated runs.

### Recommended tsconfig.json for the Dashboard

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "jsx": "react-jsx",
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "allowImportingTsExtensions": true,
    "noEmit": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

### Breaking Changes / Gotchas
- `TypedArray` interfaces are now generic over `ArrayBufferLike` -- may need `@types/node` updates.
- Stricter implicit `any` errors for functions returning `null`/`undefined` without annotations.
- Classes with computed property names now generate index signatures.

---

## 4. lightweight-charts (TradingView)

**Official Docs:** https://tradingview.github.io/lightweight-charts/
**API Reference:** https://tradingview.github.io/lightweight-charts/docs/api
**GitHub:** https://github.com/tradingview/lightweight-charts
**Latest Stable:** v5.1
**License:** Apache 2.0

### Installation
```bash
npm install lightweight-charts
```

### Chart Creation & Candlestick Series

```ts
import { createChart, CandlestickSeries } from 'lightweight-charts';

const chart = createChart(document.getElementById('chart-container')!, {
  width: 800,
  height: 400,
  layout: {
    background: { color: '#1a1a2e' },
    textColor: '#e0e0e0',
  },
  grid: {
    vertLines: { color: '#2a2a3e' },
    horzLines: { color: '#2a2a3e' },
  },
});

const candlestickSeries = chart.addSeries(CandlestickSeries, {
  // Korean market convention: RED = up, BLUE = down
  upColor: '#ef5350',           // Red for rising candles
  downColor: '#2962FF',         // Blue for falling candles
  borderUpColor: '#ef5350',
  borderDownColor: '#2962FF',
  wickUpColor: '#ef5350',
  wickDownColor: '#2962FF',
  borderVisible: true,
  wickVisible: true,
});
```

### CandlestickStyleOptions -- All Color Properties

| Property          | Type     | Default     | Description                    |
|-------------------|----------|-------------|--------------------------------|
| `upColor`         | `string` | `'#26a69a'` | Color of rising candle body    |
| `downColor`       | `string` | `'#ef5350'` | Color of falling candle body   |
| `borderColor`     | `string` | `'#378658'` | Default border color           |
| `borderUpColor`   | `string` | `'#26a69a'` | Border color of rising candles |
| `borderDownColor` | `string` | `'#ef5350'` | Border of falling candles      |
| `wickColor`       | `string` | `'#737375'` | Default wick color             |
| `wickUpColor`     | `string` | `'#26a69a'` | Wick color of rising candles   |
| `wickDownColor`   | `string` | `'#ef5350'` | Wick color of falling candles  |
| `borderVisible`   | `boolean`| `true`      | Show/hide candle borders       |
| `wickVisible`     | `boolean`| `true`      | Show/hide wicks                |

### Setting Data

```ts
candlestickSeries.setData([
  { time: '2026-04-01', open: 75000, high: 76200, low: 74800, close: 75900 },
  { time: '2026-04-02', open: 75900, high: 77100, low: 75500, close: 76800 },
  { time: '2026-04-03', open: 76800, high: 77500, low: 76000, close: 76300 },
]);
```

### Real-Time Updates

Use `update()` for live data -- DO NOT call `setData()` repeatedly (performance killer):

```ts
// Update the last candle or add a new one
candlestickSeries.update({
  time: '2026-04-03',
  open: 76800,
  high: 77800,
  low: 76000,
  close: 77200,
});
```

### Line Series (for indicators, moving averages)

```ts
import { LineSeries } from 'lightweight-charts';

const ma20Series = chart.addSeries(LineSeries, {
  color: '#FFD700',
  lineWidth: 2,
  title: 'MA20',
});

ma20Series.setData([
  { time: '2026-04-01', value: 75500 },
  { time: '2026-04-02', value: 75800 },
  { time: '2026-04-03', value: 76100 },
]);
```

### React Integration Pattern

```tsx
import { useEffect, useRef } from 'react';
import { createChart, CandlestickSeries, type IChartApi } from 'lightweight-charts';

function CandlestickChart({ data, width, height }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, { width, height });
    chartRef.current = chart;

    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#ef5350',      // Korean: red = up
      downColor: '#2962FF',    // Korean: blue = down
      borderUpColor: '#ef5350',
      borderDownColor: '#2962FF',
      wickUpColor: '#ef5350',
      wickDownColor: '#2962FF',
    });

    series.setData(data);
    chart.timeScale().fitContent();

    return () => {
      chart.remove();       // Cleanup on unmount
    };
  }, [data, width, height]);

  return <div ref={containerRef} />;
}
```

### Gotchas
- Target is ES2020 -- ensure your build config matches.
- `setData()` replaces ALL data; use `update()` for streaming.
- Chart must be explicitly `remove()`d on unmount to prevent memory leaks.
- Time values must be in ascending order.

---

## 5. Zustand -- State Management

**Official Docs:** https://zustand.docs.pmnd.rs/
**GitHub:** https://github.com/pmndrs/zustand
**Latest Stable:** v5.x (check npm for exact)
**Demo:** https://zustand-demo.pmnd.rs/

### Basic TypeScript Store Creation

```ts
import { create } from 'zustand';

interface BearState {
  bears: number;
  increasePopulation: () => void;
  removeAllBears: () => void;
}

const useBearStore = create<BearState>()((set) => ({
  bears: 0,
  increasePopulation: () => set((state) => ({ bears: state.bears + 1 })),
  removeAllBears: () => set({ bears: 0 }),
}));

// Usage -- no Provider needed!
function BearCounter() {
  const bears = useBearStore((state) => state.bears);
  return <h1>{bears} bears around here</h1>;
}
```

**IMPORTANT TypeScript pattern**: Always use `create<State>()(...)` with the extra `()` -- this is required for proper type inference with middleware.

### Async Actions (e.g., fetching market data)

```ts
interface MarketDataState {
  ohlcv: CandlestickData[];
  isLoading: boolean;
  error: string | null;
  fetchOHLCV: (symbol: string) => Promise<void>;
}

const useMarketDataStore = create<MarketDataState>()((set) => ({
  ohlcv: [],
  isLoading: false,
  error: null,
  fetchOHLCV: async (symbol: string) => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch(`/api/market-data/${symbol}/ohlcv`);
      const data = await res.json();
      set({ ohlcv: data, isLoading: false });
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
    }
  },
}));
```

### DevTools Middleware

```ts
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface TradeState {
  trades: Trade[];
  addTrade: (trade: Trade) => void;
}

const useTradeStore = create<TradeState>()(
  devtools((set) => ({
    trades: [],
    addTrade: (trade) => set(
      (state) => ({ trades: [...state.trades, trade] }),
      undefined,
      'addTrade'  // Action name shown in Redux DevTools
    ),
  }), { name: 'TradeStore' })
);
```

### Persist Middleware

```ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsState {
  theme: 'dark' | 'light';
  setTheme: (theme: 'dark' | 'light') => void;
}

const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      theme: 'dark',
      setTheme: (theme) => set({ theme }),
    }),
    { name: 'dashboard-settings' }  // localStorage key
  )
);
```

### Combining Middleware (DevTools + Persist)

```ts
const useSettingsStore = create<SettingsState>()(
  devtools(
    persist(
      (set) => ({
        theme: 'dark',
        setTheme: (theme) => set({ theme }),
      }),
      { name: 'dashboard-settings' }
    ),
    { name: 'SettingsStore' }
  )
);
```

### Selectors with `useShallow` (Prevent Unnecessary Re-renders)

```ts
import { useShallow } from 'zustand/react/shallow';

// BAD: Re-renders on ANY state change
const state = useMarketDataStore();

// GOOD: Only re-renders when ohlcv or isLoading change
const { ohlcv, isLoading } = useMarketDataStore(
  useShallow((state) => ({ ohlcv: state.ohlcv, isLoading: state.isLoading }))
);
```

### Type Extraction

```ts
import { type ExtractState } from 'zustand';
type MarketDataState = ExtractState<typeof useMarketDataStore>;
```

### Gotchas
- No Provider/Context needed -- stores are global singletons.
- State updates must be immutable (use spread or immer middleware).
- Do NOT use Zustand stores in React Server Components.
- `useShallow` is essential for object/array selectors to avoid excess re-renders.
- The `get` parameter in `create((set, get) => ...)` reads current state without causing renders.

---

## 6. Vitest -- Unit / Component Testing

**Official Docs:** https://vitest.dev/
**Getting Started:** https://vitest.dev/guide/
**Config Reference:** https://vitest.dev/config/
**Latest Stable:** v4.1.2
**Requires:** Vite >= 6.0.0, Node >= 20.0.0

### Installation

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

### Configuration with Vite

```ts
// vite.config.ts
/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,              // No need to import describe/it/expect
    environment: 'jsdom',       // Or 'happy-dom' for faster tests
    setupFiles: ['./src/test/setup.ts'],
    css: true,
    coverage: {
      provider: 'v8',           // Or 'istanbul'
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/test/**', '**/*.d.ts'],
    },
  },
});
```

### Test Setup File

```ts
// src/test/setup.ts
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

afterEach(() => {
  cleanup();
});
```

### Basic Test Example

```ts
// src/utils/formatPrice.test.ts
import { describe, it, expect } from 'vitest';
import { formatPrice } from './formatPrice';

describe('formatPrice', () => {
  it('formats Korean Won with commas', () => {
    expect(formatPrice(75000)).toBe('75,000');
  });

  it('handles negative values', () => {
    expect(formatPrice(-1200)).toBe('-1,200');
  });
});
```

### Mocking

```ts
import { vi, describe, it, expect } from 'vitest';

// Mock a module
vi.mock('./api/marketData', () => ({
  fetchOHLCV: vi.fn().mockResolvedValue([
    { time: '2026-04-01', open: 75000, high: 76200, low: 74800, close: 75900 },
  ]),
}));

// Mock fetch
globalThis.fetch = vi.fn().mockResolvedValue({
  ok: true,
  json: () => Promise.resolve({ data: [] }),
});
```

### DOM Environment Options
- **jsdom**: More mature, wider API coverage. Good default.
- **happy-dom**: Faster (~2-3x), but missing some Web APIs. Good for CI speed.

### package.json Scripts

```json
{
  "scripts": {
    "test": "vitest",
    "test:run": "vitest run",
    "test:coverage": "vitest run --coverage"
  }
}
```

---

## 7. React Testing Library -- Component Testing

**Official Docs:** https://testing-library.com/docs/react-testing-library/intro/
**GitHub:** https://github.com/testing-library/react-testing-library
**Latest Stable:** v16+ (requires `@testing-library/dom` as peer dependency)

### Installation

```bash
npm install -D @testing-library/react @testing-library/dom @testing-library/jest-dom @testing-library/user-event
```

### Core API: render, screen, userEvent

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { TradePanel } from './TradePanel';

describe('TradePanel', () => {
  it('renders stock symbol and price', () => {
    render(<TradePanel symbol="005930" name="Samsung" price={75000} />);

    expect(screen.getByText('Samsung')).toBeInTheDocument();
    expect(screen.getByText('75,000')).toBeInTheDocument();
  });

  it('submits a buy order on button click', async () => {
    const user = userEvent.setup();
    const onOrder = vi.fn();

    render(<TradePanel symbol="005930" name="Samsung" price={75000} onOrder={onOrder} />);

    await user.type(screen.getByLabelText('Quantity'), '10');
    await user.click(screen.getByRole('button', { name: /buy/i }));

    expect(onOrder).toHaveBeenCalledWith({
      symbol: '005930',
      quantity: 10,
      type: 'buy',
    });
  });
});
```

### Async Utilities

```tsx
import { render, screen, waitFor } from '@testing-library/react';

it('loads and displays market data', async () => {
  render(<MarketDataView symbol="005930" />);

  // waitFor -- polls until condition is met
  await waitFor(() => {
    expect(screen.getByText('75,000')).toBeInTheDocument();
  });

  // findBy* -- shorthand for waitFor + getBy
  const price = await screen.findByText('75,000');
  expect(price).toBeInTheDocument();
});
```

### Query Priority (Best Practices)

1. **getByRole** -- accessible queries (preferred)
2. **getByLabelText** -- form fields
3. **getByPlaceholderText** -- when no label
4. **getByText** -- non-interactive elements
5. **getByDisplayValue** -- current form values
6. **getByTestId** -- escape hatch (last resort)

### Gotchas
- Always use `userEvent` over `fireEvent` -- it simulates real user behavior (typing, clicking with proper event sequences).
- `userEvent.setup()` must be called before `render()` in tests.
- RTL v16+ requires `@testing-library/dom` as a separate peer dependency.
- React 19 compatibility: Ensure RTL version supports React 19's new rendering behavior.

---

## 8. Playwright -- E2E Testing

**Official Docs:** https://playwright.dev/
**Installation Guide:** https://playwright.dev/docs/intro
**GitHub:** https://github.com/microsoft/playwright
**Requires:** Node.js 20.x, 22.x, or 24.x

### Installation

```bash
npm init playwright@latest
```

This creates:
- `playwright.config.ts` -- centralized configuration
- `tests/` directory with starter tests
- Optionally installs GitHub Actions workflow

### Configuration for React + Vite + FastAPI

```ts
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],

  // Auto-start Vite dev server before tests
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
```

### Basic E2E Test

```ts
// e2e/dashboard.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Trading Dashboard', () => {
  test('displays candlestick chart on load', async ({ page }) => {
    await page.goto('/');

    // Wait for chart canvas to render
    await expect(page.locator('canvas')).toBeVisible();
    await expect(page.getByText('KOSPI')).toBeVisible();
  });

  test('can search for a stock symbol', async ({ page }) => {
    await page.goto('/');

    await page.getByPlaceholder('Search symbol...').fill('005930');
    await page.getByPlaceholder('Search symbol...').press('Enter');

    await expect(page.getByText('Samsung Electronics')).toBeVisible();
  });

  test('shows real-time price updates', async ({ page }) => {
    await page.goto('/dashboard/005930');

    const priceElement = page.getByTestId('current-price');
    await expect(priceElement).toBeVisible();

    // Verify price changes over time (WebSocket updates)
    const initialPrice = await priceElement.textContent();
    await page.waitForTimeout(3000);
    // Price element should still be visible (no crashes)
    await expect(priceElement).toBeVisible();
  });
});
```

### Key Playwright Patterns

**Auto-waiting**: Playwright auto-waits for elements to be actionable before performing actions. No need for manual `waitFor` in most cases.

**Locators** (preferred over raw selectors):
```ts
page.getByRole('button', { name: 'Buy' })
page.getByLabel('Quantity')
page.getByPlaceholder('Search symbol...')
page.getByText('Samsung Electronics')
page.getByTestId('current-price')
```

**Assertions** (auto-retry):
```ts
await expect(page.getByText('Order Placed')).toBeVisible();
await expect(page.getByText('Order Placed')).toBeHidden();
await expect(page.locator('.price')).toHaveText('75,000');
await expect(page).toHaveURL('/dashboard/005930');
```

### Running Tests

```bash
npx playwright test                     # Run all tests
npx playwright test --headed            # See the browser
npx playwright test --project=chromium  # Single browser
npx playwright test --ui                # Interactive UI mode
npx playwright show-report              # View HTML report
```

### package.json Scripts

```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:report": "playwright show-report"
  }
}
```

### Gotchas
- `webServer` config only starts the server if nothing is already listening on the port (unless in CI).
- Multiple web servers can be configured as an array (e.g., Vite + FastAPI), but `baseURL` must be set explicitly.
- `page.waitForTimeout()` is discouraged -- prefer auto-waiting locators and assertions.
- Playwright downloads browser binaries -- run `npx playwright install --with-deps` in CI.

---

## Quick Reference: Package Versions Summary

| Package                    | Version  | Docs URL                                                  |
|----------------------------|----------|-----------------------------------------------------------|
| React                      | 19.2     | https://react.dev                                         |
| Vite                       | 8.x      | https://vite.dev                                          |
| TypeScript                 | 5.7+     | https://www.typescriptlang.org                            |
| lightweight-charts         | 5.1      | https://tradingview.github.io/lightweight-charts/         |
| Zustand                    | 5.x      | https://zustand.docs.pmnd.rs/                             |
| Vitest                     | 4.1.2    | https://vitest.dev                                        |
| @testing-library/react     | 16+      | https://testing-library.com                               |
| Playwright                 | latest   | https://playwright.dev                                    |
| @vitejs/plugin-react       | 6.x      | https://github.com/vitejs/vite-plugin-react               |

---

## Korean Market Color Convention

**Critical for this dashboard**: Korean stock markets use the **opposite color convention** from US markets:

- **Red (#ef5350)** = Price UP (rising)
- **Blue (#2962FF)** = Price DOWN (falling)

This must be applied consistently across:
- Candlestick charts (upColor/downColor)
- Price change indicators
- Portfolio P&L displays
- Order book visualization
