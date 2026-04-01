"""Rich console helpers for MAD output (thread-safe)."""

from __future__ import annotations

import threading

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()
_print_lock = threading.Lock()


def _safe_print(*args, **kwargs) -> None:
    """Thread-safe wrapper around console.print."""
    with _print_lock:
        console.print(*args, **kwargs)


def banner(title: str, subtitle: str = "") -> None:
    body = Text(subtitle, style="dim") if subtitle else Text("")
    _safe_print(Panel(body, title=f"[bold magenta]{title}[/]", border_style="magenta", expand=False))


def phase_banner(phase_num: int, title: str, description: str) -> None:
    _safe_print()
    _safe_print(
        Panel(
            f"[dim]{description}[/]",
            title=f"[bold yellow]PHASE {phase_num}: {title}[/]",
            border_style="yellow",
            expand=False,
        )
    )
    _safe_print()


def log_ok(msg: str) -> None:
    _safe_print(f"[bold green]\\[OK][/] {msg}")


def log_err(msg: str) -> None:
    _safe_print(f"[bold red]\\[ERROR][/] {msg}", highlight=False)


def log_warn(msg: str) -> None:
    _safe_print(f"[bold yellow]\\[WARN][/] {msg}")


def log_info(msg: str) -> None:
    _safe_print(f"[bold blue]\\[INFO][/] {msg}")


def log_phase(phase: str, msg: str) -> None:
    _safe_print(f"[bold cyan]\\[{phase}][/] {msg}")
