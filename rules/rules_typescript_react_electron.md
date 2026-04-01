# Coding Rules: TypeScript + React + Electron Desktop Application

> Framework-specific rules for Electron desktop apps with React UI and SQLite storage.

---

## 1. Project Structure

```
project-root/
├── electron/                  # Electron main process
│   ├── main.ts               # Entry point (BrowserWindow, app lifecycle)
│   ├── preload.ts            # Preload script (contextBridge API)
│   ├── ipc/                  # IPC handler modules
│   │   ├── tickets.ts        # Ticket CRUD handlers
│   │   ├── comments.ts       # Comment CRUD handlers
│   │   └── boards.ts         # Board/column handlers
│   └── database/             # Database layer
│       ├── connection.ts     # SQLite connection singleton
│       ├── migrations/       # Schema migration files
│       └── repositories/     # Data access objects
├── src/                      # React renderer process
│   ├── main.tsx              # React entry point
│   ├── App.tsx               # Root component
│   ├── components/           # Reusable UI components
│   │   ├── ui/               # Generic UI primitives (Button, Modal, Input)
│   │   ├── kanban/           # Kanban-specific components
│   │   └── tickets/          # Ticket-specific components
│   ├── hooks/                # Custom React hooks
│   ├── stores/               # Zustand state stores
│   ├── types/                # TypeScript type definitions
│   ├── utils/                # Pure utility functions
│   └── styles/               # Global styles and Tailwind config
├── resources/                # App icons, assets for packaging
├── electron-builder.yml      # Electron-builder config
├── tailwind.config.ts        # Tailwind configuration
├── tsconfig.json             # TypeScript config (renderer)
├── tsconfig.node.json        # TypeScript config (main process)
├── vite.config.ts            # Vite configuration
├── package.json
└── .gitignore
```

### File Naming Conventions
- **React components:** `PascalCase.tsx` (e.g., `KanbanBoard.tsx`, `TicketCard.tsx`)
- **Hooks:** `camelCase.ts` prefixed with `use` (e.g., `useTickets.ts`, `useDragDrop.ts`)
- **Stores:** `camelCase.ts` suffixed with `Store` (e.g., `ticketStore.ts`)
- **Types:** `camelCase.ts` (e.g., `ticket.ts`, `kanban.ts`)
- **Utilities:** `camelCase.ts` (e.g., `dateFormat.ts`)
- **IPC handlers:** `camelCase.ts` matching domain (e.g., `tickets.ts`)
- **Database migrations:** `NNN_description.sql` (e.g., `001_create_tickets.sql`)

---

## 2. Electron-Specific Patterns

### Security: Context Isolation & Preload

**MANDATORY:** Always enable context isolation and disable node integration in the renderer.

```typescript
// electron/main.ts
const mainWindow = new BrowserWindow({
  webPreferences: {
    preload: path.join(__dirname, 'preload.js'),
    contextIsolation: true,    // ALWAYS true
    nodeIntegration: false,    // ALWAYS false
    sandbox: true,             // Enable sandboxing
  },
});
```

### IPC Communication Pattern

**ALWAYS** use typed IPC channels. Never expose raw `ipcRenderer` to the renderer.

```typescript
// electron/preload.ts — expose a typed API via contextBridge
import { contextBridge, ipcRenderer } from 'electron';

const api = {
  tickets: {
    getAll: (): Promise<Ticket[]> => ipcRenderer.invoke('tickets:getAll'),
    create: (data: CreateTicketDTO): Promise<Ticket> => ipcRenderer.invoke('tickets:create', data),
    update: (id: string, data: UpdateTicketDTO): Promise<Ticket> => ipcRenderer.invoke('tickets:update', id, data),
    delete: (id: string): Promise<void> => ipcRenderer.invoke('tickets:delete', id),
  },
  comments: {
    getByTicket: (ticketId: string): Promise<Comment[]> => ipcRenderer.invoke('comments:getByTicket', ticketId),
    create: (data: CreateCommentDTO): Promise<Comment> => ipcRenderer.invoke('comments:create', data),
    update: (id: string, content: string): Promise<Comment> => ipcRenderer.invoke('comments:update', id, content),
    delete: (id: string): Promise<void> => ipcRenderer.invoke('comments:delete', id),
  },
} as const;

contextBridge.exposeInMainWorld('api', api);
```

```typescript
// src/types/electron.d.ts — type the exposed API for renderer
interface ElectronAPI {
  tickets: {
    getAll(): Promise<Ticket[]>;
    create(data: CreateTicketDTO): Promise<Ticket>;
    update(id: string, data: UpdateTicketDTO): Promise<Ticket>;
    delete(id: string): Promise<void>;
  };
  comments: {
    getByTicket(ticketId: string): Promise<Comment[]>;
    create(data: CreateCommentDTO): Promise<Comment>;
    update(id: string, content: string): Promise<Comment>;
    delete(id: string): Promise<void>;
  };
}

declare global {
  interface Window {
    api: ElectronAPI;
  }
}
```

### Anti-Patterns (Electron)
- **NEVER** use `remote` module — it is deprecated and insecure
- **NEVER** use `nodeIntegration: true` in production windows
- **NEVER** load external URLs in BrowserWindow without validation
- **NEVER** use `shell.openExternal()` with unsanitized URLs
- **NEVER** disable `webSecurity` in production

---

## 3. React Patterns

### Component Structure

```typescript
// Preferred component structure
interface TicketCardProps {
  ticket: Ticket;
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
}

export function TicketCard({ ticket, onEdit, onDelete }: TicketCardProps) {
  // 1. Hooks first
  const [isExpanded, setIsExpanded] = useState(false);

  // 2. Derived state
  const formattedDate = formatDate(ticket.createdAt);

  // 3. Event handlers
  const handleEdit = () => onEdit(ticket.id);

  // 4. Return JSX
  return (/* ... */);
}
```

### State Management with Zustand

```typescript
// src/stores/ticketStore.ts
import { create } from 'zustand';

interface TicketState {
  tickets: Ticket[];
  isLoading: boolean;
  error: string | null;
  fetchTickets: () => Promise<void>;
  createTicket: (data: CreateTicketDTO) => Promise<void>;
  updateTicket: (id: string, data: UpdateTicketDTO) => Promise<void>;
  deleteTicket: (id: string) => Promise<void>;
  moveTicket: (id: string, targetColumn: ColumnId) => Promise<void>;
}

export const useTicketStore = create<TicketState>((set, get) => ({
  tickets: [],
  isLoading: false,
  error: null,

  fetchTickets: async () => {
    set({ isLoading: true, error: null });
    try {
      const tickets = await window.api.tickets.getAll();
      set({ tickets, isLoading: false });
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
    }
  },

  // ... other actions
}));
```

### React Anti-Patterns
- **NEVER** store derived state — compute it during render
- **NEVER** use `useEffect` for event-driven logic — use event handlers
- **NEVER** mutate state directly — always use immutable updates
- **AVOID** prop drilling deeper than 2 levels — use Zustand or context
- **AVOID** anonymous components in JSX — extract named components
- **AVOID** large monolithic components — split at ~100 JSX lines

### Custom Hooks Pattern
Extract reusable logic into custom hooks:

```typescript
// src/hooks/useDragDrop.ts
export function useDragDrop(onDrop: (ticketId: string, targetColumn: ColumnId) => void) {
  // Encapsulate drag-and-drop logic
  // Return handlers: { onDragStart, onDragOver, onDrop }
}
```

---

## 4. TypeScript Conventions

### Strict Configuration

```json
// tsconfig.json — ALWAYS enable strict mode
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "exactOptionalPropertyTypes": false
  }
}
```

### Type Definitions

```typescript
// src/types/ticket.ts
export interface Ticket {
  id: string;
  title: string;
  description: string;
  acceptanceCriteria: string;
  status: ColumnId;
  createdAt: string;   // ISO 8601 string from SQLite
  updatedAt: string;   // ISO 8601 string from SQLite
}

export type ColumnId = 'planned' | 'in-progress' | 'completed';

export interface Column {
  id: ColumnId;
  title: string;
  tickets: Ticket[];
}

export interface Comment {
  id: string;
  ticketId: string;
  content: string;
  createdAt: string;
  updatedAt: string;
}

// DTOs for creation/update — omit server-generated fields
export type CreateTicketDTO = Pick<Ticket, 'title' | 'description' | 'acceptanceCriteria' | 'status'>;
export type UpdateTicketDTO = Partial<CreateTicketDTO>;
export type CreateCommentDTO = Pick<Comment, 'ticketId' | 'content'>;
```

### TypeScript Rules
- **ALWAYS** use `interface` for object shapes, `type` for unions/intersections
- **ALWAYS** use `unknown` over `any` — narrow with type guards
- **NEVER** use `@ts-ignore` — use `@ts-expect-error` with a reason comment if absolutely necessary
- **NEVER** use `as` type assertions to silence errors — fix the types
- **PREFER** discriminated unions over optional fields for variant types
- **PREFER** `readonly` for arrays/objects that should not be mutated

---

## 5. Database Layer (SQLite)

### Library: better-sqlite3
- Synchronous API — simpler code in Electron main process
- Excellent performance for local desktop apps
- WAL mode for better concurrent read performance

### Schema Conventions

```sql
-- migrations/001_create_tickets.sql
CREATE TABLE IF NOT EXISTS tickets (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  acceptance_criteria TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'planned' CHECK(status IN ('planned', 'in-progress', 'completed')),
  position INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS comments (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
  ticket_id TEXT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_comments_ticket_id ON comments(ticket_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
```

### Repository Pattern

```typescript
// electron/database/repositories/ticketRepository.ts
export class TicketRepository {
  constructor(private db: Database) {}

  getAll(): Ticket[] {
    return this.db.prepare('SELECT * FROM tickets ORDER BY position ASC').all() as Ticket[];
  }

  create(data: CreateTicketDTO): Ticket {
    const stmt = this.db.prepare(
      'INSERT INTO tickets (title, description, acceptance_criteria, status) VALUES (?, ?, ?, ?) RETURNING *'
    );
    return stmt.get(data.title, data.description, data.acceptanceCriteria, data.status) as Ticket;
  }

  // Always use parameterized queries — NEVER concatenate user input into SQL
}
```

### Database Rules
- **ALWAYS** use parameterized queries — no string interpolation in SQL
- **ALWAYS** use transactions for multi-statement operations
- **ALWAYS** enable WAL mode: `db.pragma('journal_mode = WAL')`
- **ALWAYS** enable foreign keys: `db.pragma('foreign_keys = ON')`
- **ALWAYS** store dates as ISO 8601 strings in TEXT columns
- **STORE** the database in `app.getPath('userData')` — never in the app bundle

---

## 6. UI / Styling Conventions

### Tailwind CSS
- Use Tailwind utility classes for all styling
- Extract repeated patterns into component abstractions, not CSS classes
- Use CSS variables for theme colors (futuristic palette)
- Use `@apply` sparingly — only in global styles for base elements

### Futuristic UI Guidelines
- Dark theme as default with high-contrast accent colors (cyan, violet, electric blue)
- Use `backdrop-blur` and glass-morphism effects for panels
- Subtle glow effects on interactive elements (`box-shadow` with accent colors)
- Smooth transitions on all state changes (150-300ms)
- Use Framer Motion for drag-and-drop animations and page transitions
- Monospace or geometric sans-serif fonts (e.g., Inter, JetBrains Mono for accents)
- Minimal borders — use shadows and background contrast for separation

### Animation with Framer Motion

```typescript
// Use layout animations for kanban card reordering
<motion.div layout layoutId={ticket.id} transition={{ type: 'spring', stiffness: 300, damping: 30 }}>
  <TicketCard ticket={ticket} />
</motion.div>
```

### Accessibility
- All interactive elements must be keyboard accessible
- Use semantic HTML (`button`, `dialog`, `main`, `section`)
- Provide `aria-label` for icon-only buttons
- Maintain color contrast ratio of at least 4.5:1 for text

---

## 7. Recommended Libraries

| Purpose | Library | Why |
|---------|---------|-----|
| Framework | React 18+ | Component model, ecosystem, hooks |
| Desktop shell | Electron 30+ | Mature, excellent Windows support |
| Build tool | Vite + electron-vite | Fast HMR, optimized Electron builds |
| State management | Zustand | Minimal boilerplate, TypeScript-first |
| Database | better-sqlite3 | Synchronous, fast, no native compile issues with Electron |
| Styling | Tailwind CSS 3+ | Utility-first, rapid UI development |
| Animation | Framer Motion | Declarative animations, layout transitions |
| Drag & drop | @dnd-kit/core | Accessible, performant, React-native DnD |
| Icons | Lucide React | Consistent, tree-shakeable icon set |
| Date formatting | date-fns | Lightweight, tree-shakeable date utils |
| Forms | React Hook Form | Performant form management |
| Unique IDs | nanoid | Small, fast, URL-safe IDs |
| Linting | ESLint + typescript-eslint | Static analysis |
| Formatting | Prettier | Consistent code formatting |
| Testing | Vitest + Testing Library | Fast, Vite-native test runner |
| E2E testing | Playwright | Electron-compatible E2E tests |
| Packaging | electron-builder | Windows installer creation (NSIS) |

### Libraries to AVOID
- **Redux** — overkill for this app size; use Zustand
- **MobX** — unnecessary complexity
- **Sequelize/TypeORM** — too heavy for local SQLite; use raw better-sqlite3
- **Moment.js** — deprecated, use date-fns
- **jQuery** — not needed with React
- **react-beautiful-dnd** — unmaintained; use @dnd-kit

---

## 8. Testing

### Framework: Vitest + React Testing Library

```typescript
// src/components/kanban/__tests__/TicketCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { TicketCard } from '../TicketCard';

describe('TicketCard', () => {
  const mockTicket: Ticket = {
    id: '1',
    title: 'Test ticket',
    description: 'Description',
    acceptanceCriteria: 'AC',
    status: 'planned',
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
  };

  it('renders ticket title', () => {
    render(<TicketCard ticket={mockTicket} onEdit={vi.fn()} onDelete={vi.fn()} />);
    expect(screen.getByText('Test ticket')).toBeInTheDocument();
  });

  it('calls onEdit when edit button is clicked', () => {
    const onEdit = vi.fn();
    render(<TicketCard ticket={mockTicket} onEdit={onEdit} onDelete={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /edit/i }));
    expect(onEdit).toHaveBeenCalledWith('1');
  });
});
```

### Test Organization
- Co-locate tests in `__tests__/` folders next to source files
- Name test files: `ComponentName.test.tsx` or `moduleName.test.ts`
- Mock IPC calls by mocking `window.api` in test setup
- Test main process logic (repositories, IPC handlers) with Vitest directly

### What to Test
- **Components:** Rendering, user interactions, conditional display
- **Stores:** State transitions, async operations
- **Repositories:** CRUD operations against an in-memory SQLite
- **IPC handlers:** Request/response mapping, error handling

---

## 9. Build & Packaging

### electron-builder Configuration

```yaml
# electron-builder.yml
appId: com.kanban.todoapp
productName: Kanban Todo
win:
  target:
    - target: nsis
      arch: [x64]
  icon: resources/icon.ico
nsis:
  oneClick: false
  allowToChangeInstallationDirectory: true
directories:
  output: dist-electron
  buildResources: resources
```

### Scripts

```json
{
  "scripts": {
    "dev": "electron-vite dev",
    "build": "electron-vite build",
    "preview": "electron-vite preview",
    "package": "electron-vite build && electron-builder --win",
    "lint": "eslint . --ext .ts,.tsx",
    "format": "prettier --write .",
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

---

## 10. Performance Patterns

### React Performance
- Use `React.memo()` only when profiling confirms unnecessary re-renders
- Use `useMemo`/`useCallback` only for expensive computations or stable references passed to memoized children
- Virtualize long lists (unlikely needed for a todo app, but available via `@tanstack/react-virtual`)
- Avoid creating new objects/arrays in render — define constants outside

### Electron Performance
- Minimize IPC calls — batch reads where possible
- Load the database lazily on first access
- Use `requestIdleCallback` for non-critical background tasks
- Keep the main process lean — heavy computation stays in workers if needed

### SQLite Performance
- Use `BEGIN IMMEDIATE` transactions for write batches
- Add indexes on columns used in WHERE/ORDER BY clauses
- Use `EXPLAIN QUERY PLAN` to verify index usage on slow queries

---

## 11. Error Handling

### Renderer Process (React)

```typescript
// Use error boundaries for component trees
import { ErrorBoundary } from 'react-error-boundary';

function ErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  return (
    <div role="alert">
      <p>Something went wrong</p>
      <button onClick={resetErrorBoundary}>Try again</button>
    </div>
  );
}

// Wrap top-level routes/panels
<ErrorBoundary FallbackComponent={ErrorFallback}>
  <KanbanBoard />
</ErrorBoundary>
```

### IPC Error Handling

```typescript
// electron/ipc/tickets.ts — always wrap handlers
ipcMain.handle('tickets:create', async (_event, data: CreateTicketDTO) => {
  try {
    return ticketRepo.create(data);
  } catch (error) {
    console.error('Failed to create ticket:', error);
    throw new Error('Failed to create ticket');  // Sanitized error to renderer
  }
});
```

### Rules
- **NEVER** expose raw database errors to the renderer process
- **ALWAYS** log errors with context in the main process
- **ALWAYS** show user-friendly error messages in the UI
- **USE** toast notifications for transient errors (failed save, etc.)

---

## 12. Security Checklist (Electron-Specific)

- [x] `contextIsolation: true`
- [x] `nodeIntegration: false`
- [x] `sandbox: true`
- [x] No `remote` module usage
- [x] All IPC channels use `invoke/handle` (not `send/on` for request-response)
- [x] Input validated in IPC handlers before database operations
- [x] CSP (Content Security Policy) headers configured
- [x] No `eval()` or `new Function()` in renderer
- [x] Database stored in user data directory, not app bundle
- [x] No sensitive data logged to console in production builds

### Content Security Policy

```typescript
// Set CSP in main process
session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
  callback({
    responseHeaders: {
      ...details.responseHeaders,
      'Content-Security-Policy': ["default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'"],
    },
  });
});
```

---

**Version**: v1.0.0
**Stack**: TypeScript + React + Electron + SQLite
**Last Updated**: 2026-03-30
