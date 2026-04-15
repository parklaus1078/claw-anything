# Coding Rules: TypeScript + Next.js Full-Stack (App Router)

> Framework-specific rules for a full-stack Next.js application with API routes, SQLite database, and web crawling capabilities. Designed for personal productivity tools with no authentication requirements.

---

## 1. Project Structure

```
project-root/
├── .env.example                    # Template for required environment variables
├── .env.local                      # Local environment variables (never commit)
├── .gitignore
├── README.md
├── package.json
├── package-lock.json
├── next.config.ts
├── tsconfig.json
├── postcss.config.mjs
├── components.json                 # shadcn/ui configuration
├── drizzle.config.ts               # Drizzle ORM configuration
│
├── public/                         # Static assets
│   ├── fonts/                      # Custom fonts (Pretendard, etc.)
│   └── images/                     # Static images
│
├── src/
│   ├── app/                        # Next.js App Router pages
│   │   ├── layout.tsx              # Root layout (fonts, global providers)
│   │   ├── page.tsx                # Home / landing page
│   │   ├── globals.css             # Tailwind CSS imports + custom styles
│   │   ├── loading.tsx             # Global loading fallback
│   │   ├── error.tsx               # Global error boundary
│   │   ├── <feature>/              # Feature-based route groups
│   │   │   ├── page.tsx
│   │   │   ├── loading.tsx
│   │   │   └── error.tsx
│   │   └── api/                    # API route handlers
│   │       └── <resource>/
│   │           └── route.ts        # GET, POST, PUT, DELETE handlers
│   │
│   ├── components/                 # React components
│   │   ├── ui/                     # shadcn/ui primitives (auto-generated)
│   │   ├── layout/                 # App shell: header, sidebar, navigation
│   │   └── <feature>/             # Feature-specific components
│   │
│   ├── lib/                        # Shared utilities and configuration
│   │   ├── db/                     # Database layer
│   │   │   ├── index.ts            # Drizzle client initialization
│   │   │   ├── schema.ts           # Drizzle table definitions
│   │   │   └── migrations/         # SQL migration files
│   │   ├── crawlers/               # Web crawling modules
│   │   │   ├── base.ts             # Base crawler interface
│   │   │   ├── pinterest.ts        # Pinterest crawler
│   │   │   └── <source>.ts         # Other source crawlers
│   │   ├── utils.ts                # Generic utility functions (cn, formatDate, etc.)
│   │   └── constants.ts            # Application-wide constants
│   │
│   ├── hooks/                      # Custom React hooks
│   │   └── use-<name>.ts
│   │
│   ├── types/                      # TypeScript type definitions
│   │   ├── index.ts                # Re-exports
│   │   └── <domain>.ts             # Domain-specific types
│   │
│   └── actions/                    # Next.js Server Actions
│       └── <feature>.ts            # Server-side mutations
│
├── drizzle/                        # Generated migration files
│   └── migrations/
│
└── tests/                          # Test files
    ├── unit/                       # Unit tests
    ├── integration/                # Integration tests
    └── e2e/                        # Playwright E2E tests
```

### File Naming Conventions
- **Components**: `PascalCase.tsx` (e.g., `SearchForm.tsx`, `ReferenceCard.tsx`)
- **Utilities/hooks/types**: `kebab-case.ts` or `camelCase.ts` (e.g., `use-search.ts`, `utils.ts`)
- **Pages**: `page.tsx` (Next.js convention)
- **API routes**: `route.ts` (Next.js convention)
- **Server Actions**: `<feature>.ts` in `src/actions/`

---

## 2. TypeScript Configuration

### tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

### Type Safety Rules
- **No `any` types** — use `unknown` and narrow with type guards
- **No type assertions (`as`)** unless proven safe — prefer type guards
- **Define all API response shapes** in `src/types/`
- **Use `satisfies` operator** for type-safe object literals
- **Use discriminated unions** for state management (loading/success/error)

```typescript
// Good — discriminated union
type SearchState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: Reference[] }
  | { status: "error"; error: string };

// Bad — optional fields
type SearchState = {
  loading?: boolean;
  data?: Reference[];
  error?: string;
};
```

---

## 3. Next.js App Router Conventions

### Server vs Client Components
- **Default to Server Components** — only add `"use client"` when interactivity is needed
- **Client Components needed for**: `useState`, `useEffect`, event handlers, browser APIs
- **Never mark a component `"use client"` just because its parent is** — compose them correctly

```tsx
// Server Component (default) — data fetching, no interactivity
export default async function ReferencesPage() {
  const references = await db.select().from(referencesTable);
  return <ReferenceGrid references={references} />;
}

// Client Component — user interaction required
"use client";
export function SearchForm({ onSearch }: { onSearch: (query: string) => void }) {
  const [query, setQuery] = useState("");
  // ...
}
```

### Route Conventions
- Use `loading.tsx` for Suspense fallbacks per route segment
- Use `error.tsx` for error boundaries per route segment (must be `"use client"`)
- Use `layout.tsx` for shared UI within route groups
- Use `(group)` folders for layout grouping without affecting URL
- Use `[param]` for dynamic routes

### Server Actions
- Define in `src/actions/` with `"use server"` directive
- Use for form submissions and data mutations
- Validate inputs with Zod before processing
- Return typed results, not raw responses

```typescript
"use server";

import { z } from "zod";

const searchSchema = z.object({
  query: z.string().min(1).max(200),
  country: z.string().optional(),
  hasCollaboration: z.boolean().optional(),
});

export async function searchReferences(formData: FormData) {
  const parsed = searchSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) {
    return { error: "잘못된 입력입니다." };
  }
  // ... crawl and return results
}
```

### API Routes
- Use for webhook endpoints, external API proxying, and streaming responses
- Prefer Server Actions over API routes for form submissions
- Always validate request body with Zod
- Return `NextResponse.json()` with appropriate status codes

```typescript
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const parsed = schema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      { error: "유효하지 않은 요청입니다." },
      { status: 400 }
    );
  }
  // ...
  return NextResponse.json({ data: result });
}
```

---

## 4. Database — SQLite + Drizzle ORM

### Why SQLite
- Personal productivity tool, single user, no auth
- Zero configuration, no external database server
- File-based storage, easy to back up and reset

### Drizzle ORM Setup
```typescript
// src/lib/db/index.ts
import { drizzle } from "drizzle-orm/better-sqlite3";
import Database from "better-sqlite3";
import * as schema from "./schema";

const sqlite = new Database("data/references.db");
sqlite.pragma("journal_mode = WAL");
sqlite.pragma("foreign_keys = ON");

export const db = drizzle(sqlite, { schema });
```

### Schema Conventions
```typescript
// src/lib/db/schema.ts
import { sqliteTable, text, integer } from "drizzle-orm/sqlite-core";

export const references = sqliteTable("references", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  title: text("title").notNull(),
  imageUrl: text("image_url").notNull(),
  sourceUrl: text("source_url").notNull(),
  sourceSite: text("source_site").notNull(),
  country: text("country"),
  hasCollaboration: integer("has_collaboration", { mode: "boolean" }).default(false),
  characterName: text("character_name"),
  productCategory: text("product_category"),
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),
});
```

### Migration Management
- Use `drizzle-kit` for schema migrations
- Run `npx drizzle-kit generate` after schema changes
- Run `npx drizzle-kit migrate` to apply migrations
- Store the SQLite database file in a `data/` directory (add to `.gitignore`)

### Query Patterns
- Always use Drizzle's query builder — never write raw SQL strings
- Use `db.select()`, `db.insert()`, `db.update()`, `db.delete()`
- Use `.where()` with Drizzle operators (`eq`, `like`, `and`, `or`)
- Paginate results with `.limit()` and `.offset()`

---

## 5. Styling — Tailwind CSS v4 + shadcn/ui

### Tailwind CSS v4 Configuration
```css
/* src/app/globals.css */
@import "tailwindcss";

@theme {
  --font-sans: "Pretendard", "Noto Sans KR", "Apple SD Gothic Neo", sans-serif;
  --color-primary: #2563eb;
  --color-primary-foreground: #ffffff;
  /* Define design tokens here */
}
```

### shadcn/ui Usage
- Install components as needed: `npx shadcn@latest add button card input`
- Components are copied into `src/components/ui/` — they are editable, not a dependency
- Use the component API as-is; customize via Tailwind classes or variant props
- Never modify shadcn component internals unless absolutely necessary

### Styling Rules
- Prefer utility classes directly in JSX over custom CSS
- Extract repeated utility combinations into React components, not `@apply`
- Use `cn()` helper for conditional class merging:

```typescript
// src/lib/utils.ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### Korean Typography
- **Font stack**: Pretendard → Noto Sans KR → Apple SD Gothic Neo → sans-serif
- **Line height**: 1.6–1.8 for Korean body text (wider than English defaults)
- **Font sizes**: Use Tailwind's scale, minimum `text-sm` (14px) for Korean readability
- Load Pretendard via `next/font/local` or CDN for optimal loading

```tsx
// src/app/layout.tsx
import localFont from "next/font/local";

const pretendard = localFont({
  src: "../fonts/PretendardVariable.woff2",
  display: "swap",
  variable: "--font-sans",
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className={pretendard.variable}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
```

---

## 6. Web Crawling

### Architecture
- Crawling runs server-side only (API routes or Server Actions)
- Each source site has its own crawler module in `src/lib/crawlers/`
- Crawlers implement a common interface for consistency
- Use Playwright for JavaScript-heavy sites, Cheerio for static HTML

### Crawler Interface
```typescript
// src/lib/crawlers/base.ts
export interface CrawlResult {
  title: string;
  imageUrl: string;
  sourceUrl: string;
  sourceSite: string;
  thumbnailUrl?: string;
  description?: string;
  country?: string;
  tags?: string[];
}

export interface CrawlerOptions {
  query: string;
  country?: string;
  maxResults?: number;
  character?: string;
  productCategory?: string;
}

export interface Crawler {
  name: string;
  crawl(options: CrawlerOptions): Promise<CrawlResult[]>;
}
```

### Playwright Crawling Best Practices (Validated)
- Use `device_scale_factor: 2` for high-quality screenshots
- Use `wait_for_load_state("networkidle")` before scraping
- Always close browser context in `finally` block
- Set explicit timeouts: `connect=10s`, `navigation=30s`
- Use headless mode in production

```typescript
import { chromium } from "playwright";

export async function crawlWithPlaywright(url: string): Promise<CrawlResult[]> {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    deviceScaleFactor: 2,
    locale: "ko-KR",
  });
  try {
    const page = await context.newPage();
    await page.goto(url, { timeout: 30000 });
    await page.waitForLoadState("networkidle");
    // ... scrape data
    return results;
  } finally {
    await context.close();
    await browser.close();
  }
}
```

### Cheerio for Static Sites
- Use for sites that render HTML server-side
- Lighter weight than Playwright — preferred when JavaScript rendering isn't needed
- Use `node-fetch` or `undici` for HTTP requests

### Rate Limiting & Politeness
- Add delays between requests (minimum 1 second per domain)
- Respect `robots.txt` where applicable
- Set a descriptive User-Agent string
- Handle HTTP 429 (Too Many Requests) with exponential backoff
- Cache crawled results in SQLite to avoid re-crawling

### Graceful Degradation (Validated)
- If a source fails, return empty results and log a warning — never crash the app
- Show partial results from successful sources even if some fail
- Display clear error messages to the user for failed sources

---

## 7. Form Handling & Validation

### Zod Schemas
- Define validation schemas in `src/types/` alongside TypeScript types
- Use `z.infer<typeof schema>` to derive types from schemas
- Validate on both client (form UX) and server (security)

```typescript
import { z } from "zod";

export const searchFormSchema = z.object({
  productCategory: z.string().min(1, "상품 카테고리를 선택해주세요"),
  hasCollaboration: z.boolean(),
  characterName: z.string().optional(),
  targetCountry: z.string().min(1, "타겟 국가를 선택해주세요"),
  planDescription: z.string().optional(),
});

export type SearchFormData = z.infer<typeof searchFormSchema>;
```

### React Hook Form Integration
```tsx
"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

export function SearchForm() {
  const form = useForm<SearchFormData>({
    resolver: zodResolver(searchFormSchema),
    defaultValues: {
      hasCollaboration: false,
      targetCountry: "KR",
    },
  });

  async function onSubmit(data: SearchFormData) {
    // Call server action or API route
  }

  return <form onSubmit={form.handleSubmit(onSubmit)}>...</form>;
}
```

---

## 8. Error Handling

### Client-Side
- Use `error.tsx` boundaries for route-level error catching
- Show user-friendly Korean error messages
- Provide retry actions where appropriate
- Never expose technical details in the UI

### Server-Side
- Log errors with structured context (source, URL, timestamp)
- Return typed error responses from API routes and Server Actions
- Use specific error types, not generic catches

```typescript
// API route error handling
export async function POST(request: NextRequest) {
  try {
    const result = await crawlReferences(options);
    return NextResponse.json({ data: result });
  } catch (error) {
    if (error instanceof CrawlTimeoutError) {
      return NextResponse.json(
        { error: "크롤링 시간이 초과되었습니다. 다시 시도해주세요." },
        { status: 504 }
      );
    }
    console.error("Crawl failed:", error);
    return NextResponse.json(
      { error: "레퍼런스를 가져오는 중 오류가 발생했습니다." },
      { status: 500 }
    );
  }
}
```

---

## 9. Testing

### Framework & Tools
| Tool | Purpose |
|------|---------|
| `vitest` | Unit and integration tests |
| `@testing-library/react` | Component testing |
| `playwright` | E2E testing |
| `msw` | API mocking for component tests |

### Test File Organization
- Co-locate unit tests or place in `tests/unit/`
- Integration tests in `tests/integration/`
- E2E tests in `tests/e2e/`
- Name test files: `<module>.test.ts` or `<Component>.test.tsx`

### Test Patterns
```typescript
// Unit test — crawler
import { describe, it, expect } from "vitest";

describe("parsePinterestResults", () => {
  it("extracts image URLs from HTML", () => {
    // Arrange
    const html = loadFixture("pinterest-results.html");

    // Act
    const results = parsePinterestResults(html);

    // Assert
    expect(results).toHaveLength(20);
    expect(results[0]).toMatchObject({
      imageUrl: expect.stringContaining("https://"),
      sourceSite: "pinterest",
    });
  });
});
```

### Coverage Targets
- Unit tests: 80%+ for crawlers and utilities
- Component tests: cover all interactive components
- E2E tests: cover the main search → results → save flow

---

## 10. Recommended Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| `next` | 15.x | Full-stack React framework |
| `react` | 19.x | UI library |
| `typescript` | 5.7+ | Type safety |
| `tailwindcss` | 4.x | Utility-first CSS |
| `shadcn/ui` | latest | Accessible UI component primitives |
| `drizzle-orm` | 0.38+ | Type-safe ORM for SQLite |
| `better-sqlite3` | 11.x | SQLite driver (synchronous, fast) |
| `drizzle-kit` | 0.30+ | Migration tool for Drizzle |
| `playwright` | 1.50+ | Browser automation for crawling + E2E tests |
| `cheerio` | 1.0+ | HTML parsing for static sites |
| `zod` | 3.x | Schema validation |
| `react-hook-form` | 7.x | Form state management |
| `@hookform/resolvers` | 3.x | Zod integration for react-hook-form |
| `clsx` | 2.x | Conditional class names |
| `tailwind-merge` | 2.x | Merge Tailwind classes without conflicts |
| `lucide-react` | latest | Icon library |
| `sonner` | latest | Toast notifications |
| `vitest` | 3.x | Test runner |
| `@testing-library/react` | 16.x | Component testing |
| `msw` | 2.x | API mocking |

### Do NOT Use
- `axios` — use native `fetch` (Next.js extends it with caching)
- `styled-components` / `emotion` — use Tailwind CSS
- `prisma` — use Drizzle (lighter weight, better for SQLite)
- `express` — use Next.js API routes
- `mongoose` / `mongodb` — use SQLite for this use case

---

## 11. Configuration & Environment

### Environment Variables
```bash
# .env.example

# Database
DATABASE_PATH=data/references.db

# Crawling
CRAWL_DELAY_MS=1500               # Delay between requests per domain
CRAWL_MAX_RESULTS=50              # Maximum results per crawl session
PLAYWRIGHT_HEADLESS=true          # Set to false for debugging

# Optional: Proxy for crawling
# HTTP_PROXY=
# HTTPS_PROXY=
```

### next.config.ts
```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      // Add domains for crawled image sources
      { protocol: "https", hostname: "**.pinimg.com" },
      { protocol: "https", hostname: "**.behance.net" },
    ],
  },
  experimental: {
    serverActions: {
      bodySizeLimit: "10mb", // For image-heavy responses
    },
  },
};

export default nextConfig;
```

---

## 12. Security Considerations

### Crawling Security
- **SSRF protection**: Resolve hostname → check against blocked IP ranges (private IPs) → then request
- Never allow user-provided URLs to be crawled without validation
- Sanitize all crawled HTML before rendering (prevent stored XSS)
- Do not store or execute JavaScript from crawled pages

### Input Validation
- Validate all form inputs with Zod on both client and server
- Sanitize search queries before passing to crawlers
- Limit query length and character set

### Data Storage
- SQLite file stored in `data/` directory, excluded from Git
- No user credentials stored (no auth required)
- Crawled images stored as URLs, not downloaded (to avoid copyright issues)

---

## 13. Performance Patterns

### Next.js Optimizations
- Use Server Components by default to reduce client JS bundle
- Use `next/image` for all image rendering (lazy loading, format optimization)
- Use `next/dynamic` for heavy client components (image galleries, modals)
- Leverage Next.js `fetch` caching for repeated API calls

### Crawling Performance
- Run crawlers in parallel when targeting multiple sources
- Cache results in SQLite with TTL-based invalidation
- Use `Promise.allSettled()` for concurrent crawls (graceful degradation)
- Stream results to the client as they arrive (React Server Components + Suspense)

### Database Performance
- Enable WAL mode for SQLite (concurrent reads during writes)
- Add indexes on frequently queried columns (`country`, `source_site`, `character_name`)
- Use pagination for all list queries
- Implement full-text search with SQLite FTS5 if needed

### Image Loading
- Use blur placeholders for crawled images
- Implement lazy loading with `loading="lazy"` via `next/image`
- Set appropriate `sizes` attribute for responsive images
- Consider using `unoptimized` for external crawled images if domains change frequently

---

## 14. UX Conventions (Korean Web Designer Tool)

### Language
- All UI text in Korean
- Error messages in Korean with actionable guidance
- Use formal-polite speech level (합니다/해주세요)

### Layout
- Clean, minimal design — no visual clutter
- Card-based grid layout for reference results (Pinterest-style masonry)
- Sticky sidebar for filters, scrollable main content for results
- Responsive: optimized for desktop (primary), usable on tablet

### Interaction Patterns
- Instant search feedback (loading spinners, skeleton cards)
- Toast notifications for success/error states (using `sonner`)
- Drag-to-select for batch operations on results
- Keyboard shortcuts for power users (optional, progressive enhancement)

### Visual Design
- Neutral color palette (grays, whites) to not compete with reference images
- Accent color for CTAs and active states
- Consistent spacing using Tailwind's spacing scale
- Smooth transitions with `transition-all duration-200`

---

## 15. Build & Development

### Development
```bash
npm run dev        # Start Next.js dev server (http://localhost:3000)
npm run db:push    # Push schema changes to SQLite
npm run db:studio  # Open Drizzle Studio (database browser)
npm run lint       # ESLint
npm run type-check # TypeScript compiler check (tsc --noEmit)
```

### Package.json Scripts
```json
{
  "scripts": {
    "dev": "next dev --turbopack",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "type-check": "tsc --noEmit",
    "db:generate": "drizzle-kit generate",
    "db:migrate": "drizzle-kit migrate",
    "db:push": "drizzle-kit push",
    "db:studio": "drizzle-kit studio",
    "test": "vitest",
    "test:e2e": "playwright test"
  }
}
```

### Quality Gate (Pre-commit)
1. `npm run lint` — zero ESLint errors
2. `npm run type-check` — zero TypeScript errors
3. `npm run test` — all tests pass

### .gitignore Must Include
```
node_modules/
.next/
data/*.db
.env.local
.env
*.tsbuildinfo
coverage/
playwright-report/
test-results/
```

---

## 16. Version Summary

| Technology | Version | Notes |
|---|---|---|
| Node.js | 22 LTS | Runtime |
| Next.js | 15.x | App Router, full-stack |
| React | 19.x | Latest stable |
| TypeScript | 5.7+ | Strict mode |
| Tailwind CSS | 4.x | CSS-first configuration |
| Drizzle ORM | 0.38+ | Type-safe SQLite ORM |
| better-sqlite3 | 11.x | SQLite driver |
| Playwright | 1.50+ | Web crawling + E2E tests |
| Cheerio | 1.0+ | HTML parsing |
| Zod | 3.x | Schema validation |
| react-hook-form | 7.x | Form management |
| shadcn/ui | latest | UI component library |
| Vitest | 3.x | Unit testing |

---

**Version**: v1.0.0
**Last updated**: 2026-04-10
