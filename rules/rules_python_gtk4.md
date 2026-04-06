# Coding Rules: Python + GTK4 + libadwaita

> Stack-specific rules for building Linux desktop applications with Python, GTK4, libadwaita, and SQLite.

---

## 1. Project Structure

```
project_root/
├── src/
│   └── <app_package>/          # Main Python package (snake_case)
│       ├── __init__.py
│       ├── main.py             # Application entry point, Adw.Application subclass
│       ├── window.py           # Main application window (Adw.ApplicationWindow)
│       ├── models/             # Data models and database layer
│       │   ├── __init__.py
│       │   ├── database.py     # SQLite connection and migrations
│       │   └── <entity>.py     # One file per domain entity
│       ├── views/              # UI components (GTK widgets/composites)
│       │   ├── __init__.py
│       │   └── <view_name>.py  # One file per major view/widget
│       ├── viewmodels/         # Presentation logic (optional, for complex UIs)
│       │   └── __init__.py
│       └── utils/              # Shared helpers
│           └── __init__.py
├── data/                       # GResource files
│   ├── <app_id>.gresource.xml
│   ├── <app_id>.gschema.xml    # GSettings schema (if needed)
│   ├── icons/
│   │   └── hicolor/
│   │       └── scalable/
│   │           └── apps/
│   │               └── <app_id>.svg
│   └── ui/                     # Blueprint or XML UI definitions
│       └── *.blp / *.ui
├── po/                         # Translations (gettext)
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_models/
│   └── test_views/
├── <app_id>.desktop.in         # Desktop entry
├── <app_id>.metainfo.xml.in    # AppStream metadata
├── meson.build                 # Build system (preferred for GNOME ecosystem)
├── pyproject.toml              # Python project metadata and tool config
├── .env.example
├── .gitignore
└── README.md
```

### File Naming
- All Python files: `snake_case.py`
- UI definition files: `snake_case.ui` or `snake_case.blp` (Blueprint)
- Application ID: reverse-DNS format (`com.example.AppName`)
- GResource XML: matches application ID

---

## 2. GTK4 + libadwaita Patterns

### Application Initialization
```python
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Gio, GLib

class Application(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="com.example.MyApp",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    def do_activate(self):
        window = self.props.active_window
        if not window:
            window = MainWindow(application=self)
        window.present()
```

### Widget Composition with `Gtk.Template`
- Prefer declarative UI (XML or Blueprint files) over building UI in Python code
- Use `@Gtk.Template` decorator to bind UI files to Python classes
- Keep widget signal handlers in the template class

```python
@Gtk.Template(resource_path="/com/example/MyApp/ui/main_window.ui")
class MainWindow(Adw.ApplicationWindow):
    __gtype_name__ = "MainWindow"

    # Bind child widgets declared in the .ui file
    task_list: Gtk.ListBox = Gtk.Template.Child()

    @Gtk.Template.Callback()
    def on_add_button_clicked(self, button: Gtk.Button) -> None:
        ...
```

### Anti-Patterns
- **Do not use GTK3 APIs** — GTK4 removed many GTK3 patterns (e.g., `Gtk.Box.pack_start` is gone; use `append` instead)
- **Do not use `Gtk.Window` directly** — use `Adw.ApplicationWindow` for proper libadwaita integration
- **Do not call `Gtk.init()`** — `Adw.Application` handles initialization
- **Do not use `set_visible(True)` on top-level windows** — use `window.present()`
- **Do not block the main thread** — use `Gio.Task`, `GLib.idle_add`, or Python threading with `GLib.idle_add` for UI updates
- **Do not mutate GTK widgets from non-main threads** — always marshal UI updates to the main thread via `GLib.idle_add`

### GTK4 Key Differences from GTK3
- Event handling uses `Gtk.EventController` subclasses (gesture controllers, key controllers), not signal-based events
- Drag-and-drop uses `Gtk.DragSource` and `Gtk.DropTarget`, not the old DnD API
- `Gtk.ListBox` and `Gtk.ListView` (with `Gtk.SignalListItemFactory` or `Gtk.BuilderListItemFactory`) for lists
- CSS node-based styling; use `add_css_class()` instead of `get_style_context().add_class()`

### Drag-and-Drop (Kanban-style)
```python
# Source side
drag_source = Gtk.DragSource()
drag_source.connect("prepare", self.on_drag_prepare)
drag_source.connect("drag-begin", self.on_drag_begin)
widget.add_controller(drag_source)

# Target side
drop_target = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
drop_target.connect("drop", self.on_drop)
column_widget.add_controller(drop_target)
```

---

## 3. Recommended Libraries

| Library | Purpose | Why |
|---|---|---|
| **PyGObject** (`gi`) | GTK4/libadwaita Python bindings | Official GNOME Python binding |
| **libadwaita** (`Adw`) | Adaptive GNOME widgets and styling | Provides modern GNOME look, adaptive layouts, `Adw.StatusPage`, `Adw.NavigationView` |
| **SQLite** (via `sqlite3`) | Local data persistence | Built into Python stdlib, zero-config, perfect for single-user desktop apps |
| **pytest** | Testing | Standard Python test runner, rich plugin ecosystem |
| **Blueprint** (`blueprint-compiler`) | Declarative UI | Cleaner syntax than raw XML for GTK4 UI definitions (optional) |
| **Ruff** | Linting and formatting | Fast, replaces flake8 + black + isort in one tool |

### Libraries to Avoid
- **SQLAlchemy** — overkill for a single-user SQLite desktop app; use raw `sqlite3` with a thin wrapper
- **Tkinter** — not native-looking on Linux; GTK4 integrates with the desktop
- **PyQt/PySide** — licensing complexity; GTK is the native GNOME toolkit

---

## 4. Configuration Best Practices

### GSettings (for user preferences)
- Define schema in `data/<app_id>.gschema.xml`
- Access via `Gio.Settings`
- Use GSettings for window size/state, user preferences, view options
- Never store secrets in GSettings

### Application Data Storage
- Store user data in `GLib.get_user_data_dir()` → `~/.local/share/<app_name>/`
- Store configuration in `GLib.get_user_config_dir()` → `~/.config/<app_name>/`
- Store cache in `GLib.get_user_cache_dir()` → `~/.cache/<app_name>/`
- Always use XDG base directory spec paths, never hardcode `~/.config` directly

### Environment Variables
- Use `.env` files for development-only settings
- Provide `.env.example` with placeholder values
- Never commit `.env` to Git

---

## 5. SQLite Database Patterns

### Connection Management
```python
import sqlite3
from pathlib import Path
from gi.repository import GLib

def get_db_path() -> Path:
    data_dir = Path(GLib.get_user_data_dir()) / "app_name"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "tasks.db"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
```

### Schema Migrations
- Use a `schema_version` pragma or a `migrations` table
- Apply migrations sequentially on startup
- Never modify existing migration files — add new ones

```python
MIGRATIONS = [
    """CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'planned' CHECK(status IN ('planned', 'in_progress', 'completed')),
        position INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );""",
]
```

### Parameterized Queries Only
```python
# Good
cursor.execute("SELECT * FROM tasks WHERE status = ?", (status,))

# Bad — SQL injection risk
cursor.execute(f"SELECT * FROM tasks WHERE status = '{status}'")
```

---

## 6. Testing

### Framework: pytest
```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

### Testing Strategy
- **Unit tests (models, utils):** Test database operations with an in-memory SQLite database (`":memory:"`)
- **Widget tests:** Use `Gtk.test_*` utilities sparingly; prefer testing view logic separately from widgets
- **Integration tests:** Test full flows with a temporary database file

### Fixtures
```python
# tests/conftest.py
import pytest
import sqlite3

@pytest.fixture
def db_connection():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    apply_migrations(conn)
    yield conn
    conn.close()
```

### What to Test
- All database CRUD operations
- Data validation and constraint enforcement
- Task state transitions (planned -> in_progress -> completed)
- Position/ordering logic for kanban columns
- Edge cases: empty columns, maximum tasks, special characters in titles

### What Not to Test
- GTK/libadwaita widget rendering (that is the toolkit's responsibility)
- Python standard library behavior

---

## 7. Build and Packaging

### Meson Build System (GNOME standard)
- Use `meson.build` for building, installing, and packaging
- Compile GResources, GSettings schemas, and translations via Meson
- Install to standard Linux paths (`/usr/share/`, etc.)

### Flatpak (recommended distribution)
- Provide a `<app_id>.json` or `<app_id>.yml` Flatpak manifest
- Use `org.gnome.Platform` and `org.gnome.Sdk` runtime
- Pin runtime version to latest stable GNOME release

### pyproject.toml
```toml
[project]
name = "app-name"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "PyGObject>=3.50.0",
]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "SIM", "TCH"]
```

---

## 8. Security Considerations

### Desktop-Specific
- **Flatpak sandboxing:** request only necessary permissions (filesystem, network)
- **No network by default:** a local task manager should not require internet access
- **File access:** if importing/exporting data, use `Gtk.FileDialog` (GTK4) to let the user choose paths — never access arbitrary filesystem locations
- **Input sanitization:** validate task titles and descriptions for length and content before storing
- **Database file permissions:** ensure the SQLite file has restrictive permissions (0600)

### D-Bus
- If exposing D-Bus interfaces, validate all incoming method calls
- Prefer session bus over system bus for desktop apps

---

## 9. Performance Patterns

### GTK4-Specific
- **Use `Gtk.ListView` with factories for long lists** — it virtualizes rows, rendering only visible items
- **Use `Gtk.SignalListItemFactory`** for programmatic list items or `Gtk.BuilderListItemFactory` for template-based items
- **Avoid rebuilding widget trees** — update existing widgets instead of destroying and recreating
- **Use CSS classes for state changes** — toggling a CSS class is cheaper than swapping widgets

### SQLite-Specific
- Enable WAL mode (`PRAGMA journal_mode=WAL`) for better concurrent read performance
- Create indexes on frequently queried columns (`status`, `position`)
- Use transactions for batch operations (e.g., reordering multiple tasks)

```python
def reorder_tasks(conn: sqlite3.Connection, task_positions: list[tuple[int, int]]) -> None:
    with conn:
        conn.executemany(
            "UPDATE tasks SET position = ?, updated_at = datetime('now') WHERE id = ?",
            task_positions,
        )
```

### Threading
- Run database queries on a background thread for large datasets
- Always update the UI on the main thread via `GLib.idle_add()`
- For simple apps with small datasets, synchronous DB calls on the main thread are acceptable

---

## 10. UI/UX Conventions (GNOME HIG)

### Follow GNOME Human Interface Guidelines
- Use `Adw.HeaderBar` with title and subtitle
- Use `Adw.StatusPage` for empty states (e.g., "No tasks yet")
- Use `Adw.ActionRow` / `Adw.PreferencesRow` for list items with actions
- Use `Adw.Toast` for non-blocking notifications (e.g., "Task moved to completed")
- Use `Adw.MessageDialog` for destructive confirmations (e.g., deleting a task)
- Use `Adw.NavigationView` or `Adw.ViewStack` for multi-view layouts

### Keyboard Accessibility
- All actions must be keyboard-accessible
- Support standard shortcuts: `Ctrl+N` (new), `Delete` (remove), `Ctrl+Z` (undo)
- Use `Gtk.ShortcutController` for keyboard shortcuts in GTK4

### Responsive Layout
- Use `Adw.Clamp` to constrain content width on wide screens
- Use `Adw.Breakpoint` for adaptive layouts that rearrange at different window sizes

---

## 11. Naming Conventions (Python + GTK)

### Python Standard
- Variables/functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private members: `_leading_underscore`
- Module-level "constants" that are really config: `UPPER_SNAKE_CASE`

### GTK-Specific
- `__gtype_name__` must be `PascalCase` and unique across the app
- Signal handler methods: `on_<widget>_<signal>` (e.g., `on_add_button_clicked`)
- Action names: `app.<action>` for application-wide, `win.<action>` for window-scoped
- CSS class names: `kebab-case` (e.g., `task-card`, `column-header`)

---

## 12. Prohibited Practices

### GTK4/libadwaita Specific
- Do not use deprecated GTK3 patterns or imports
- Do not use `Gtk.main()` / `Gtk.main_quit()` — use `Adw.Application.run()`
- Do not use `Gdk.threads_init()` — it is removed in GTK4
- Do not manipulate widget styles via inline `style` properties — use CSS classes
- Do not create windows without an `Adw.Application` — always associate windows with the app
- Do not ignore `GLib.Error` exceptions from async operations
- Do not use `time.sleep()` in the main thread — it freezes the UI

---

**Version**: v1.0.0
**Last updated**: 2026-04-04
