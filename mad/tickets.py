"""Ticket parser — splits tickets.md into individual TicketInfo objects."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TicketInfo:
    """A single parsed ticket from tickets.md."""
    number: int
    title: str
    content: str  # full markdown body including the heading
    dependencies: list[int] = field(default_factory=list)


def _parse_dependencies(content: str) -> list[int]:
    """Extract dependency ticket numbers from ticket content.

    Looks for patterns like:
        - **Dependencies**: [1, 2, 3]
        - **Dependencies**: Ticket 1, Ticket 3
        - **Dependencies**: none
    """
    match = re.search(
        r"\*\*Dependencies\*\*:\s*(.+?)$", content, re.MULTILINE | re.IGNORECASE
    )
    if not match:
        return []

    dep_text = match.group(1).strip().lower()
    if dep_text in ("none", "n/a", "-", "[]", ""):
        return []

    # Extract all numbers from the dependency text
    numbers = [int(n) for n in re.findall(r"\d+", dep_text)]
    return sorted(set(numbers))


def parse_tickets(tickets_file: Path) -> list[TicketInfo]:
    """Parse tickets.md into a list of TicketInfo, ordered by ticket number.

    Splits on `### Ticket N: <title>` headings.
    """
    if not tickets_file.exists():
        return []

    text = tickets_file.read_text(encoding="utf-8")

    # Split on ### Ticket N: pattern
    pattern = r"(?=^### Ticket \d+)"
    chunks = re.split(pattern, text, flags=re.MULTILINE)

    tickets = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        heading_match = re.match(
            r"^### Ticket (\d+):\s*(.+?)$", chunk, re.MULTILINE
        )
        if not heading_match:
            continue

        number = int(heading_match.group(1))
        title = heading_match.group(2).strip()
        deps = _parse_dependencies(chunk)

        tickets.append(TicketInfo(
            number=number,
            title=title,
            content=chunk,
            dependencies=deps,
        ))

    tickets.sort(key=lambda t: t.number)
    return tickets


def build_dependency_graph(tickets: list[TicketInfo]) -> list[list[int]]:
    """Group tickets into parallelizable batches respecting dependencies.

    Returns a list of groups, where each group contains ticket numbers
    that can be executed in parallel. Groups must be executed in order.

    This is a topological sort with level grouping.
    """
    if not tickets:
        return []

    ticket_map = {t.number: t for t in tickets}
    all_numbers = {t.number for t in tickets}

    # Track which tickets are completed
    completed: set[int] = set()
    groups: list[list[int]] = []

    remaining = set(all_numbers)
    while remaining:
        # Find tickets whose dependencies are all completed
        ready = []
        for n in sorted(remaining):
            t = ticket_map[n]
            deps_met = all(d in completed or d not in all_numbers for d in t.dependencies)
            if deps_met:
                ready.append(n)

        if not ready:
            # Circular dependency or missing deps — just add remaining in order
            ready = sorted(remaining)

        groups.append(ready)
        completed.update(ready)
        remaining -= set(ready)

    return groups
