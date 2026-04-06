"""Discord bot for MAD — receive commands and supervise agents via Discord.

Requires the ``discord.py`` library: pip install discord.py>=2.3
or install MAD with: pip install -e ".[discord]"

Usage:
    mad bot              # Start the bot (foreground)
    mad bot --daemon     # Start the bot (background)

Commands:
    !mad run <dir> "<idea>" [--brainstorm]   Start a full pipeline run
    !mad resume                               Resume interrupted run
    !mad status                               Show active project status
    !mad stop                                 Stop the current pipeline

    !mad review-results                       Show latest review scores & issues
    !mad tickets                              Show current ticket list
    !mad fix "<instructions>"                 Run coder fix with custom instructions
    !mad approve                              Manually approve and skip to finalize
    !mad reject "<feedback>"                  Manually reject with custom feedback

    !mad rerun-ticket <N>                     Re-implement a specific ticket
    !mad set-language <ko|en|zh>              Change response language
    !mad help                                 Show all commands
"""

from __future__ import annotations

import asyncio
import re
import shlex
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from mad.config import (
    RunConfig,
    get_budget,
    get_default_model,
    get_max_iterations,
    get_pass_score,
    load_settings,
    save_settings,
)
from mad.console import log_err, log_info, log_ok, log_warn
from mad.i18n import SUPPORTED_LANGUAGES, get_language, t

# Lazy import — discord.py is an optional dependency
_discord = None

# Discord message limit
_MAX_MSG_LEN = 1950


def _ensure_discord():
    """Import discord.py on demand."""
    global _discord
    if _discord is None:
        try:
            import discord as _discord_lib
            _discord = _discord_lib
        except ImportError:
            raise ImportError(
                "The 'discord.py' package is required for the bot feature.\n"
                "Install it with: pip install discord.py>=2.3\n"
                "Or install MAD with Discord support: pip install -e \".[discord]\""
            )
    return _discord


def _get_bot_config() -> dict[str, Any]:
    """Read bot configuration from settings.json."""
    settings = load_settings()
    return {
        "token": settings.get("discord_bot_token", ""),
        "channel_id": settings.get("discord_command_channel_id", ""),
        "language": settings.get("language", "en"),
    }


def _get_active_cfg() -> tuple[RunConfig, dict] | None:
    """Build a RunConfig for the active project. Returns (cfg, project_dict) or None."""
    from mad.projects import get_active_project

    active = get_active_project()
    if not active:
        return None

    cfg = RunConfig(
        project_dir=Path(active["project_dir"]),
        idea=active["idea"],
        project_slug=active["slug"],
    )
    return cfg, active


class MADBot:
    """Discord bot that listens for MAD commands in a configured channel."""

    def __init__(self, token: str, channel_id: int | str):
        discord = _ensure_discord()

        self.token = token
        self.channel_id = int(channel_id)
        self._pipeline_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)

        # Register event handlers
        self.client.event(self.on_ready)
        self.client.event(self.on_message)

    @property
    def _is_running(self) -> bool:
        return self._pipeline_thread is not None and self._pipeline_thread.is_alive()

    def _run_subprocess(self, cmd: list[str], label: str, channel_id: int) -> None:
        """Run a MAD CLI subprocess in a thread, streaming output to terminal
        and posting a completion/error message back to Discord.

        Args:
            cmd: The command to run (e.g., ["mad", "run", ...]).
            label: Human-readable label for the command (e.g., "run my-app").
            channel_id: Discord channel ID to post completion message to.
        """
        log_info(f"[bot] Subprocess started: {' '.join(cmd)}")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # line-buffered
            )

            # Stream output to terminal in real time
            last_lines: list[str] = []
            for line in proc.stdout:
                line = line.rstrip("\n")
                print(f"[bot|{label}] {line}", flush=True)
                last_lines.append(line)
                if len(last_lines) > 20:
                    last_lines.pop(0)

            proc.wait()
            exit_code = proc.returncode

            # Post result back to Discord
            if exit_code == 0:
                discord_msg = f"\u2705 **{label}** completed successfully."
            else:
                tail = "\n".join(last_lines[-10:]) if last_lines else "(no output)"
                discord_msg = (
                    f"\u274c **{label}** exited with code {exit_code}.\n"
                    f"```\n{tail}\n```"
                )

            log_info(f"[bot] Subprocess finished: {label} (exit code {exit_code})")

        except Exception as e:
            discord_msg = f"\u274c **{label}** failed: {e}"
            log_err(f"[bot] Subprocess error: {label} — {e}")

        # Post back to Discord from the thread
        self._post_to_channel(channel_id, discord_msg)

    def _post_to_channel(self, channel_id: int, text: str) -> None:
        """Schedule a message to be sent to a Discord channel from a non-async thread."""
        fut = asyncio.run_coroutine_threadsafe(
            self._send_to_channel(channel_id, text),
            self.client.loop,
        )
        try:
            fut.result(timeout=10)
        except Exception as e:
            log_warn(f"[bot] Failed to post completion to Discord: {e}")

    async def _send_to_channel(self, channel_id: int, text: str) -> None:
        """Send a message to a channel (async, called from event loop)."""
        channel = self.client.get_channel(channel_id)
        if not channel:
            return
        while text:
            chunk = text[:_MAX_MSG_LEN]
            text = text[_MAX_MSG_LEN:]
            await channel.send(chunk)

    def _start_pipeline(self, cmd: list[str], label: str, channel_id: int) -> None:
        """Launch a MAD CLI subprocess in a background thread."""
        self._stop_event.clear()
        self._pipeline_thread = threading.Thread(
            target=self._run_subprocess,
            args=(cmd, label, channel_id),
            daemon=True,
        )
        self._pipeline_thread.start()

    async def on_ready(self):
        log_ok(f"MAD Bot connected as {self.client.user}")
        channel = self.client.get_channel(self.channel_id)
        if channel:
            log_ok(f"Listening for commands in #{channel.name}")
        else:
            log_warn(f"Could not find channel {self.channel_id} — bot will listen but can't post.")

    async def on_message(self, message):
        if message.author == self.client.user:
            return
        if message.channel.id != self.channel_id:
            return

        content = message.content.strip()
        if not content.startswith("!mad"):
            return

        parts = content[4:].strip()
        await self._dispatch(message, parts)

    async def _dispatch(self, message, command_str: str):
        """Parse and dispatch a !mad command."""
        if not command_str:
            await self._handle_help(message)
            return

        tokens = command_str.split(None, 1)
        cmd = tokens[0].lower()
        args_str = tokens[1] if len(tokens) > 1 else ""

        handlers = {
            "run": self._handle_run,
            "resume": lambda m, _: self._handle_resume(m),
            "status": lambda m, _: self._handle_status(m),
            "stop": lambda m, _: self._handle_stop(m),
            "set-language": self._handle_set_language,
            "help": lambda m, _: self._handle_help(m),
            # Supervision commands
            "review-results": lambda m, _: self._handle_review_results(m),
            "tickets": lambda m, _: self._handle_tickets(m),
            "fix": self._handle_fix,
            "approve": lambda m, _: self._handle_approve(m),
            "reject": self._handle_reject,
            "rerun-ticket": self._handle_rerun_ticket,
        }

        handler = handlers.get(cmd)
        if handler:
            await handler(message, args_str)
        else:
            await message.reply(t("bot.unknown_command"))

    # ------------------------------------------------------------------
    # Helper: send long text as chunked messages
    # ------------------------------------------------------------------

    async def _send_long(self, message, text: str, prefix: str = ""):
        """Reply with a potentially long text, chunking at Discord's limit."""
        if prefix:
            text = f"{prefix}\n{text}"
        while text:
            chunk = text[:_MAX_MSG_LEN]
            text = text[_MAX_MSG_LEN:]
            await message.reply(chunk)

    # ------------------------------------------------------------------
    # Pipeline commands
    # ------------------------------------------------------------------

    async def _handle_run(self, message, args_str: str):
        """Handle !mad run <dir> "<idea>" [--brainstorm]"""
        if self._is_running:
            await message.reply(t("bot.already_running"))
            return

        try:
            tokens = shlex.split(args_str)
        except ValueError:
            await message.reply("Invalid arguments. Usage: `!mad run <dir> \"<idea>\" [--brainstorm]`")
            return

        if len(tokens) < 2:
            await message.reply("Usage: `!mad run <dir> \"<idea>\" [--brainstorm]`")
            return

        project_dir = tokens[0]
        idea = tokens[1]
        brainstorm = "--brainstorm" in tokens

        cmd = ["mad", "run", str(project_dir), idea]
        if brainstorm:
            cmd.append("--brainstorm")

        project_name = Path(project_dir).resolve().name
        label = f"run {project_name}"
        self._start_pipeline(cmd, label, message.channel.id)

        reply = t("bot.started", project=project_name)
        if brainstorm:
            reply += " (with brainstorm)"
        await message.reply(reply)

    async def _handle_resume(self, message):
        if self._is_running:
            await message.reply(t("bot.already_running"))
            return

        from mad.projects import get_active_project
        active = get_active_project()
        if not active:
            await message.reply(t("bot.no_active"))
            return

        cmd = ["mad", "resume"]
        self._start_pipeline(cmd, f"resume {active['name']}", message.channel.id)
        await message.reply(t("bot.resumed", project=active["name"]))

    async def _handle_status(self, message):
        from mad.state import RunState

        result = _get_active_cfg()
        if not result:
            await message.reply(t("bot.no_active"))
            return
        cfg, active = result

        state = RunState.load(cfg.state_file)
        lang = get_language()

        lines = [f"**{active['name']}**"]
        lines.append(f"Directory: `{active['project_dir']}`")

        if state:
            phase_label = t(f"phase.{state.phase}", lang=lang) if state.phase else "-"
            lines.append(f"Phase: **{phase_label}**")
            lines.append(f"Iteration: **{state.iteration}**")
            if state.finished:
                lines.append(f"Status: **{t('status.completed')}**")
            elif state.approved:
                lines.append(f"Status: **{t('status.approved')}**")
            lines.append(f"Completed tickets: {state.completed_tickets or 'none'}")
            lines.append(state.resume_description)
        else:
            lines.append("No run state found.")

        if self._is_running:
            lines.append("\n_Pipeline is currently running._")

        await message.reply("\n".join(lines))

    async def _handle_stop(self, message):
        self._stop_event.set()
        await message.reply(t("bot.stopped"))

    # ------------------------------------------------------------------
    # Supervision commands
    # ------------------------------------------------------------------

    async def _handle_review_results(self, message):
        """Post the latest refinement list and scores to Discord."""
        result = _get_active_cfg()
        if not result:
            await message.reply(t("bot.no_active"))
            return
        cfg, active = result

        # Find the latest review iteration
        review_files = sorted(cfg.specs_dir.glob("review_iteration_*.md"))
        refinement = cfg.refinement_file

        lines = [f"**Review Results — {active['name']}**\n"]

        # Show scores from latest review log
        if review_files:
            latest_review = review_files[-1]
            content = latest_review.read_text(encoding="utf-8")
            lines.append(f"_Latest review: `{latest_review.name}`_\n")

            # Extract score lines
            score_lines = [l for l in content.splitlines()
                           if re.match(r"^-?\s*(Ticket|Functionality|Code|Doc|Domain|Security|Testing|UI|DX|SCORE)", l, re.IGNORECASE)]
            if score_lines:
                lines.append("**Scores:**")
                lines.extend(score_lines)
                lines.append("")
        else:
            lines.append("_No review logs found._\n")

        # Show refinement list (the actionable issues)
        if refinement.exists():
            ref_content = refinement.read_text(encoding="utf-8")
            lines.append("**Refinement List:**")
            lines.append(f"```\n{ref_content}\n```")
        else:
            lines.append("_No refinement list found._")

        await self._send_long(message, "\n".join(lines))

    async def _handle_tickets(self, message):
        """Post the current ticket list to Discord."""
        result = _get_active_cfg()
        if not result:
            await message.reply(t("bot.no_active"))
            return
        cfg, active = result

        if not cfg.tickets_file.exists():
            await message.reply(f"No tickets found for **{active['name']}**. Run `!mad run` first.")
            return

        content = cfg.tickets_file.read_text(encoding="utf-8")

        # Extract ticket headers for a summary view
        headers = [l for l in content.splitlines() if l.startswith("### Ticket")]
        summary = "\n".join(headers) if headers else "(no ticket headers found)"

        lines = [
            f"**Tickets — {active['name']}** ({len(headers)} tickets)\n",
            summary,
            f"\n_Full tickets file: `{cfg.tickets_file}`_",
        ]
        await self._send_long(message, "\n".join(lines))

    async def _handle_fix(self, message, args_str: str):
        """Run coder fix with custom instructions written to refinement_list.md.

        Usage: !mad fix "fix the auth middleware, ignore CSS issues"
        If no instructions given, runs fix with the existing refinement list.
        """
        if self._is_running:
            await message.reply(t("bot.already_running"))
            return

        result = _get_active_cfg()
        if not result:
            await message.reply(t("bot.no_active"))
            return
        cfg, active = result

        # If custom instructions provided, write them as the refinement list
        instructions = args_str.strip().strip('"').strip("'")
        if instructions:
            # Preserve original refinement list as backup
            if cfg.refinement_file.exists():
                backup = cfg.refinement_file.with_suffix(".md.bak")
                backup.write_text(cfg.refinement_file.read_text(encoding="utf-8"), encoding="utf-8")

            # Write custom instructions as the refinement list
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            custom_content = (
                f"# Refinement List — Custom (via Discord)\n"
                f"# Written: {timestamp}\n\n"
                f"## Critical (must fix)\n"
                f"1. {instructions}\n"
            )
            cfg.refinement_file.write_text(custom_content, encoding="utf-8")
            await message.reply(f"Custom refinement list written. Starting fix...")
        else:
            if not cfg.refinement_file.exists():
                await message.reply("No refinement list found and no instructions given.\n"
                                    "Usage: `!mad fix \"fix the auth middleware\"`")
                return
            await message.reply("Starting fix with existing refinement list...")

        cmd = ["mad", "fix"]
        self._start_pipeline(cmd, f"fix {active['name']}", message.channel.id)

    async def _handle_approve(self, message):
        """Manually approve the project and skip to finalization.

        Writes 'Status: APPROVED' to refinement_list.md and runs finalize.
        """
        if self._is_running:
            await message.reply(t("bot.already_running"))
            return

        result = _get_active_cfg()
        if not result:
            await message.reply(t("bot.no_active"))
            return
        cfg, active = result

        from mad.state import RunState
        state = RunState.load(cfg.state_file)
        if not state:
            await message.reply("No run state found. Nothing to approve.")
            return

        # Write approved refinement list
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        cfg.refinement_file.write_text(
            f"# Refinement List — Manual Approval\n"
            f"# Approved via Discord: {timestamp}\n\n"
            f"Status: APPROVED\n\n"
            f"Manually approved by user via Discord bot.\n",
            encoding="utf-8",
        )

        # Update state to approved
        state.mark(cfg, phase="review", iteration=state.iteration or 1, approved=True)

        await message.reply(
            f"**{active['name']}** manually approved. Running finalization..."
        )

        cmd = ["mad", "finalize"]
        self._start_pipeline(cmd, f"finalize {active['name']}", message.channel.id)

    async def _handle_reject(self, message, args_str: str):
        """Manually reject with custom feedback, then run fix.

        Usage: !mad reject "the API routes don't match the spec in ticket 4"
        """
        instructions = args_str.strip().strip('"').strip("'")
        if not instructions:
            await message.reply('Usage: `!mad reject "description of what needs fixing"`')
            return

        if self._is_running:
            await message.reply(t("bot.already_running"))
            return

        result = _get_active_cfg()
        if not result:
            await message.reply(t("bot.no_active"))
            return
        cfg, active = result

        # Preserve original refinement list
        if cfg.refinement_file.exists():
            backup = cfg.refinement_file.with_suffix(".md.bak")
            backup.write_text(cfg.refinement_file.read_text(encoding="utf-8"), encoding="utf-8")

        # Write rejection feedback as refinement list
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        cfg.refinement_file.write_text(
            f"# Refinement List — Manual Rejection (via Discord)\n"
            f"# Written: {timestamp}\n\n"
            f"## Critical (must fix)\n"
            f"1. {instructions}\n",
            encoding="utf-8",
        )

        from mad.state import RunState
        state = RunState.load(cfg.state_file)
        if state:
            state.mark(cfg, phase="review", iteration=state.iteration or 1, approved=False)

        await message.reply(f"Rejection recorded. Starting fix...")

        cmd = ["mad", "fix"]
        self._start_pipeline(cmd, f"fix {active['name']} (rejected)", message.channel.id)

    async def _handle_rerun_ticket(self, message, args_str: str):
        """Re-implement a specific ticket.

        Usage: !mad rerun-ticket 3
        """
        if self._is_running:
            await message.reply(t("bot.already_running"))
            return

        ticket_num = args_str.strip()
        if not ticket_num.isdigit():
            await message.reply("Usage: `!mad rerun-ticket <number>` (e.g., `!mad rerun-ticket 3`)")
            return

        result = _get_active_cfg()
        if not result:
            await message.reply(t("bot.no_active"))
            return
        cfg, active = result

        if not cfg.tickets_file.exists():
            await message.reply(f"No tickets found for **{active['name']}**.")
            return

        # Write a refinement list that targets this specific ticket
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        cfg.refinement_file.write_text(
            f"# Refinement List — Ticket Re-implementation (via Discord)\n"
            f"# Written: {timestamp}\n\n"
            f"## Critical (must fix)\n"
            f"1. [RE-IMPLEMENT] Re-implement Ticket {ticket_num} from scratch. "
            f"Read the ticket from {cfg.tickets_file}, delete the existing implementation "
            f"for this ticket, and re-implement it completely following the ticket spec "
            f"and coding rules.\n",
            encoding="utf-8",
        )

        await message.reply(f"Re-implementing ticket {ticket_num} for **{active['name']}**...")

        cmd = ["mad", "fix"]
        self._start_pipeline(cmd, f"rerun ticket {ticket_num} ({active['name']})", message.channel.id)

    # ------------------------------------------------------------------
    # Utility commands
    # ------------------------------------------------------------------

    async def _handle_set_language(self, message, lang: str):
        lang = lang.strip().lower()
        if lang not in SUPPORTED_LANGUAGES:
            await message.reply(f"Supported languages: {', '.join(SUPPORTED_LANGUAGES)}")
            return
        save_settings({"language": lang})
        await message.reply(t("bot.language_set", lang=lang))

    async def _handle_help(self, message):
        help_text = """\
**MAD Bot Commands**

**Pipeline:**
`!mad run <dir> "<idea>" [--brainstorm]` — Start a full pipeline run
`!mad resume` — Resume interrupted run
`!mad stop` — Stop the current pipeline

**Supervision:**
`!mad status` — Show project status, phase, and iteration
`!mad review-results` — Show latest review scores and issues
`!mad tickets` — Show current ticket list

**Directing Fixes:**
`!mad fix` — Run fix with existing refinement list
`!mad fix "fix the auth middleware"` — Run fix with custom instructions
`!mad reject "API routes don't match spec"` — Reject with feedback, then fix
`!mad approve` — Manually approve and skip to finalize
`!mad rerun-ticket 3` — Re-implement a specific ticket

**Settings:**
`!mad set-language <ko|en|zh>` — Change response language
`!mad help` — Show this message"""
        await message.reply(help_text)

    def run(self):
        """Start the bot (blocking)."""
        self.client.run(self.token)

    async def close(self):
        """Gracefully shut down the bot."""
        await self.client.close()


def start_bot(*, daemon: bool = False) -> None:
    """Start the MAD Discord bot.

    Args:
        daemon: If True, run in a background thread.
    """
    config = _get_bot_config()

    if not config["token"]:
        log_err(
            "No Discord bot token configured.\n"
            "Set it in settings.json:\n"
            '  { "discord_bot_token": "YOUR_BOT_TOKEN", "discord_command_channel_id": "CHANNEL_ID" }'
        )
        raise SystemExit(1)

    if not config["channel_id"]:
        log_err(
            "No command channel ID configured.\n"
            "Set 'discord_command_channel_id' in settings.json."
        )
        raise SystemExit(1)

    bot = MADBot(token=config["token"], channel_id=config["channel_id"])

    if daemon:
        thread = threading.Thread(target=bot.run, daemon=True)
        thread.start()
        log_ok(f"MAD Bot started in background (channel: {config['channel_id']})")
        return

    log_info("Starting MAD Bot (press Ctrl+C to stop)...")
    try:
        bot.run()
    except KeyboardInterrupt:
        log_info("Bot shutting down...")
