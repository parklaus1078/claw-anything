"""Auto-detect project type from directory contents.

Inspects dependency files, directory structure, and framework indicators
to classify projects so the reviewer can select the right testing strategy.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path


class ProjectType(Enum):
    WEB_FULLSTACK = "web_fullstack"
    WEB_FRONTEND = "web_frontend"
    WEB_BACKEND = "web_backend"
    CLI = "cli"
    LIBRARY = "library"
    DESKTOP = "desktop"
    MOBILE = "mobile"
    UNKNOWN = "unknown"


# Indicators in package.json dependencies/devDependencies
_FRONTEND_INDICATORS = {
    "react", "react-dom", "vue", "svelte", "@sveltejs/kit",
    "next", "nuxt", "@angular/core", "solid-js", "astro",
    "vite", "@remix-run/react", "gatsby",
}
_BACKEND_JS_INDICATORS = {
    "express", "fastify", "koa", "hapi", "nest", "@nestjs/core",
    "hono", "polka",
}
_DESKTOP_INDICATORS = {"electron", "tauri", "@electron/remote", "electron-builder"}
_MOBILE_INDICATORS = {"react-native", "expo", "@react-native-community/cli"}

# Python backend frameworks
_PYTHON_BACKEND = {"fastapi", "flask", "django", "sanic", "starlette", "tornado", "aiohttp"}
_PYTHON_CLI = {"click", "typer", "argparse", "fire"}


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").lower()
    except OSError:
        return ""


def _get_npm_deps(pkg: dict) -> set[str]:
    deps: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        deps.update(pkg.get(key, {}).keys())
    return deps


def _check_subdir_package_json(project_dir: Path, indicators: set[str]) -> bool:
    """Check if any immediate subdirectory has a package.json matching indicators."""
    for sub in project_dir.iterdir():
        if sub.is_dir() and (sub / "package.json").exists():
            deps = _get_npm_deps(_read_json(sub / "package.json"))
            if deps & indicators:
                return True
    return False


def detect_project_type(project_dir: Path) -> ProjectType:
    """Inspect project_dir and return the detected ProjectType."""

    has_frontend = False
    has_backend = False
    has_desktop = False
    has_mobile = False

    # --- Check root package.json ---
    pkg_json = project_dir / "package.json"
    if pkg_json.exists():
        pkg = _read_json(pkg_json)
        deps = _get_npm_deps(pkg)

        if deps & _DESKTOP_INDICATORS:
            has_desktop = True
        if deps & _MOBILE_INDICATORS:
            has_mobile = True
        if deps & _FRONTEND_INDICATORS:
            has_frontend = True
        if deps & _BACKEND_JS_INDICATORS:
            has_backend = True

    # --- Check subdirectories (monorepo / multi-component) ---
    for sub_name in ("frontend", "client", "web", "app", "ui"):
        sub = project_dir / sub_name
        if sub.is_dir() and (sub / "package.json").exists():
            sub_deps = _get_npm_deps(_read_json(sub / "package.json"))
            if sub_deps & _FRONTEND_INDICATORS:
                has_frontend = True
            if sub_deps & _MOBILE_INDICATORS:
                has_mobile = True

    for sub_name in ("backend", "server", "api"):
        sub = project_dir / sub_name
        if sub.is_dir():
            if (sub / "package.json").exists():
                sub_deps = _get_npm_deps(_read_json(sub / "package.json"))
                if sub_deps & _BACKEND_JS_INDICATORS:
                    has_backend = True
            # Python backend in subdir
            for req_file in ("requirements.txt", "pyproject.toml"):
                content = _read_text(sub / req_file)
                if any(fw in content for fw in _PYTHON_BACKEND):
                    has_backend = True

    # --- Check Python deps at root ---
    for req_file in ("requirements.txt", "pyproject.toml", "Pipfile", "setup.py", "setup.cfg"):
        content = _read_text(project_dir / req_file)
        if content:
            if any(fw in content for fw in _PYTHON_BACKEND):
                has_backend = True
            if any(fw in content for fw in _PYTHON_CLI):
                # Only flag CLI if there's no web backend
                if not has_backend:
                    return ProjectType.CLI

    # --- Check Rust (Cargo.toml) ---
    cargo = _read_text(project_dir / "Cargo.toml")
    if cargo:
        if "clap" in cargo or "structopt" in cargo:
            return ProjectType.CLI
        if "actix" in cargo or "axum" in cargo or "rocket" in cargo or "warp" in cargo:
            has_backend = True

    # --- Check Go ---
    go_mod = _read_text(project_dir / "go.mod")
    if go_mod:
        if "cobra" in go_mod or "urfave/cli" in go_mod:
            return ProjectType.CLI
        if "gin-gonic" in go_mod or "gorilla/mux" in go_mod or "fiber" in go_mod or "echo" in go_mod:
            has_backend = True

    # --- Check Flutter ---
    if (project_dir / "pubspec.yaml").exists():
        pubspec = _read_text(project_dir / "pubspec.yaml")
        if "flutter" in pubspec:
            return ProjectType.MOBILE

    # --- Check docker-compose for multi-component ---
    for dc_name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
        dc = _read_text(project_dir / dc_name)
        if dc:
            if "frontend" in dc or "client" in dc:
                has_frontend = True
            if "backend" in dc or "server" in dc or "api" in dc:
                has_backend = True

    # --- Resolve ---
    if has_mobile:
        return ProjectType.MOBILE
    if has_desktop:
        return ProjectType.DESKTOP
    if has_frontend and has_backend:
        return ProjectType.WEB_FULLSTACK
    if has_frontend:
        return ProjectType.WEB_FRONTEND
    if has_backend:
        return ProjectType.WEB_BACKEND

    # --- Fallback: check if it's a library ---
    if (project_dir / "setup.py").exists() or (project_dir / "setup.cfg").exists():
        return ProjectType.LIBRARY
    pkg = _read_json(project_dir / "package.json") if pkg_json.exists() else {}
    if pkg.get("main") or pkg.get("exports") or pkg.get("types"):
        return ProjectType.LIBRARY

    return ProjectType.UNKNOWN
