"""Discord webhook integration for live agent inspection."""

from __future__ import annotations

import json
import threading
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

# Discord message limit
_MAX_MSG_LEN = 1950  # leave room for markdown fences
_RATE_LIMIT_INTERVAL = 0.6  # seconds between posts (Discord allows ~30/min)

_post_lock = threading.Lock()
_last_post_time: float = 0.0


def _post(webhook_url: str, content: str, username: str = "MAD") -> None:
    """Post a message to a Discord webhook. Blocks briefly for rate limiting."""
    global _last_post_time

    if not webhook_url:
        return

    with _post_lock:
        elapsed = time.monotonic() - _last_post_time
        if elapsed < _RATE_LIMIT_INTERVAL:
            time.sleep(_RATE_LIMIT_INTERVAL - elapsed)

        payload = json.dumps({"username": username, "content": content}).encode()
        req = Request(webhook_url, data=payload, headers={
            "Content-Type": "application/json",
            "User-Agent": "MAD-Agent/1.0 (Discord Webhook)",
        })
        try:
            urlopen(req, timeout=5)
        except (URLError, OSError):
            pass  # don't crash the agent over a webhook failure
        _last_post_time = time.monotonic()


def post_message(webhook_url: str, text: str, role: str = "MAD") -> None:
    """Post a message to Discord, chunking if it exceeds the limit."""
    if not webhook_url or not text:
        return

    # Chunk long messages
    while text:
        chunk = text[:_MAX_MSG_LEN]
        text = text[_MAX_MSG_LEN:]
        _post(webhook_url, chunk, username=role)


def post_message_async(webhook_url: str, text: str, role: str = "MAD") -> None:
    """Post a message to Discord in a background thread."""
    if not webhook_url or not text:
        return
    t = threading.Thread(target=post_message, args=(webhook_url, text, role), daemon=True)
    t.start()


def format_prompt(role: str, prompt: str, model: str = "", backend: str = "claude") -> str:
    """Format an outgoing prompt for Discord display."""
    header = f"**SYSTEM -> {role}**"
    if model:
        header += f"  |  model: `{model}`"
    header += f"  |  backend: `{backend}`"

    # Truncate very long prompts for readability
    display_prompt = prompt
    if len(prompt) > 3500:
        display_prompt = prompt[:3500] + "\n\n... (truncated)"

    return f"{header}\n```\n{display_prompt}\n```"


def format_claude_event(role: str, event: dict) -> str | None:
    """Format a Claude stream-json event for Discord. Returns None to skip."""
    etype = event.get("type", "")

    if etype == "assistant":
        msg = event.get("message", {})
        content_parts = msg.get("content", [])
        lines = []
        for part in content_parts:
            if part.get("type") == "text" and part.get("text"):
                lines.append(part["text"])
            elif part.get("type") == "tool_use":
                tool_name = part.get("name", "?")
                tool_input = part.get("input", {})
                # Show key details for common tools
                detail = ""
                if "file_path" in tool_input:
                    detail = f" `{tool_input['file_path']}`"
                elif "command" in tool_input:
                    cmd = tool_input["command"]
                    if len(cmd) > 120:
                        cmd = cmd[:120] + "..."
                    detail = f" `{cmd}`"
                elif "pattern" in tool_input:
                    detail = f" `{tool_input['pattern']}`"
                lines.append(f"**tool:{tool_name}**{detail}")
        if lines:
            return f"**{role}** | " + "\n".join(lines)

    elif etype == "user":
        # Tool results — show condensed version
        msg = event.get("message", {})
        content_parts = msg.get("content", [])
        tool_result = event.get("tool_use_result", {})
        if isinstance(tool_result, dict) and tool_result.get("file"):
            fpath = tool_result["file"].get("filePath", "")
            nlines = tool_result["file"].get("totalLines", "?")
            return f"**{role}** | tool result: `{fpath}` ({nlines} lines)"
        # Generic tool result — show first 200 chars
        for part in content_parts:
            if part.get("type") == "tool_result":
                result_text = part.get("content", "")
                if isinstance(result_text, str) and result_text:
                    preview = result_text[:200]
                    if len(result_text) > 200:
                        preview += "..."
                    return f"**{role}** | tool result:\n```\n{preview}\n```"

    elif etype == "result":
        cost = event.get("total_cost_usd", 0)
        turns = event.get("num_turns", 0)
        duration = event.get("duration_ms", 0)
        result_text = event.get("result", "")
        preview = result_text[:500] if result_text else "(empty)"
        if len(result_text) > 500:
            preview += "..."
        return (
            f"**{role}** | **DONE** "
            f"({turns} turns, {duration / 1000:.1f}s, ${cost:.4f})\n"
            f"```\n{preview}\n```"
        )

    return None


def format_codex_event(role: str, event: dict) -> str | None:
    """Format a Codex JSONL event for Discord. Returns None to skip."""
    etype = event.get("type", "")

    if etype == "item.completed":
        item = event.get("item", {})
        if item.get("type") == "agent_message" and item.get("text"):
            text = item["text"][:500]
            if len(item.get("text", "")) > 500:
                text += "..."
            return f"**{role}** [codex] | {text}"
        elif item.get("type") == "tool_call":
            tool_name = item.get("name", "?")
            return f"**{role}** [codex] | **tool:{tool_name}**"

    elif etype == "turn.completed":
        usage = event.get("usage", {})
        inp = usage.get("input_tokens", 0)
        out = usage.get("output_tokens", 0)
        return f"**{role}** [codex] | turn done (in: {inp}, out: {out} tokens)"

    return None
