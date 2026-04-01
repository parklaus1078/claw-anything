"""Project registry — manage multiple projects within MAD."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from mad.config import _mad_home, load_settings, save_settings


def _projects_dir() -> Path:
    return _mad_home() / "projects"


def _registry_file() -> Path:
    return _mad_home() / "projects.json"


def _load_registry() -> dict:
    p = _registry_file()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def _save_registry(data: dict) -> None:
    p = _registry_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _slugify(name: str) -> str:
    """Convert a name to a filesystem-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "unnamed"


def register_project(
    name: str,
    project_dir: str,
    idea: str,
    *,
    status: str = "active",
) -> dict:
    """Register or update a project in the registry. Returns the project entry."""
    registry = _load_registry()

    slug = _slugify(name)
    now = datetime.now().isoformat()

    if slug in registry:
        # Update existing
        registry[slug]["idea"] = idea
        registry[slug]["project_dir"] = str(project_dir)
        registry[slug]["updated_at"] = now
        if status:
            registry[slug]["status"] = status
    else:
        # Create new
        registry[slug] = {
            "name": name,
            "slug": slug,
            "project_dir": str(project_dir),
            "idea": idea,
            "status": status,
            "created_at": now,
            "updated_at": now,
        }

    # Create per-project directories
    proj_data_dir = _projects_dir() / slug
    (proj_data_dir / "specs").mkdir(parents=True, exist_ok=True)
    (proj_data_dir / "logs").mkdir(parents=True, exist_ok=True)

    _save_registry(registry)
    return registry[slug]


def get_project(name: str) -> dict | None:
    """Get a project by name or slug."""
    registry = _load_registry()
    slug = _slugify(name)
    return registry.get(slug)


def list_projects() -> list[dict]:
    """List all registered projects, sorted by last update."""
    registry = _load_registry()
    projects = list(registry.values())
    projects.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
    return projects


def set_active_project(name: str) -> dict | None:
    """Set the active project. Returns the project entry or None if not found."""
    project = get_project(name)
    if project:
        save_settings({"active_project": project["slug"]})
    return project


def get_active_project() -> dict | None:
    """Get the currently active project."""
    settings = load_settings()
    slug = settings.get("active_project")
    if not slug:
        return None
    registry = _load_registry()
    return registry.get(slug)


def project_specs_dir(slug: str) -> Path:
    """Return the per-project specs directory."""
    return _projects_dir() / slug / "specs"


def project_logs_dir(slug: str) -> Path:
    """Return the per-project logs directory."""
    return _projects_dir() / slug / "logs"


def update_project_status(name: str, status: str) -> None:
    """Update a project's status."""
    registry = _load_registry()
    slug = _slugify(name)
    if slug in registry:
        registry[slug]["status"] = status
        registry[slug]["updated_at"] = datetime.now().isoformat()
        _save_registry(registry)
