"""CLI commands for sotion."""

import asyncio
import atexit
import os
import signal
from pathlib import Path
import select
import sys

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from sotion import __version__, __logo__

app = typer.Typer(
    name="sotion",
    help=f"{__logo__} sotion - AI Agent Team Manager",
    no_args_is_help=True,
)

console = Console()
EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit", ":q"}

# ---------------------------------------------------------------------------
# CLI input helpers
# ---------------------------------------------------------------------------

_READLINE = None
_HISTORY_FILE: Path | None = None
_HISTORY_HOOK_REGISTERED = False
_USING_LIBEDIT = False
_SAVED_TERM_ATTRS = None


def _flush_pending_tty_input() -> None:
    try:
        fd = sys.stdin.fileno()
        if not os.isatty(fd):
            return
    except Exception:
        return
    try:
        import termios
        termios.tcflush(fd, termios.TCIFLUSH)
        return
    except Exception:
        pass
    try:
        while True:
            ready, _, _ = select.select([fd], [], [], 0)
            if not ready:
                break
            if not os.read(fd, 4096):
                break
    except Exception:
        return


def _save_history() -> None:
    if _READLINE is None or _HISTORY_FILE is None:
        return
    try:
        _READLINE.write_history_file(str(_HISTORY_FILE))
    except Exception:
        return


def _restore_terminal() -> None:
    if _SAVED_TERM_ATTRS is None:
        return
    try:
        import termios
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, _SAVED_TERM_ATTRS)
    except Exception:
        pass


def _enable_line_editing() -> None:
    global _READLINE, _HISTORY_FILE, _HISTORY_HOOK_REGISTERED, _USING_LIBEDIT, _SAVED_TERM_ATTRS
    try:
        import termios
        _SAVED_TERM_ATTRS = termios.tcgetattr(sys.stdin.fileno())
    except Exception:
        pass

    history_file = Path.home() / ".sotion" / "history" / "cli_history"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    _HISTORY_FILE = history_file

    try:
        import readline
    except ImportError:
        return

    _READLINE = readline
    _USING_LIBEDIT = "libedit" in (readline.__doc__ or "").lower()

    try:
        if _USING_LIBEDIT:
            readline.parse_and_bind("bind ^I rl_complete")
        else:
            readline.parse_and_bind("tab: complete")
        readline.parse_and_bind("set editing-mode emacs")
    except Exception:
        pass

    try:
        readline.read_history_file(str(history_file))
    except Exception:
        pass

    if not _HISTORY_HOOK_REGISTERED:
        atexit.register(_save_history)
        _HISTORY_HOOK_REGISTERED = True


def _prompt_text() -> str:
    if _READLINE is None:
        return "You: "
    if _USING_LIBEDIT:
        return "\033[1;34mYou:\033[0m "
    return "\001\033[1;34m\002You:\001\033[0m\002 "


def _print_agent_response(response: str, agent_name: str = "Agent", render_markdown: bool = True) -> None:
    content = response or ""
    body = Markdown(content) if render_markdown else Text(content)
    console.print()
    console.print(
        Panel(
            body,
            title=f"{__logo__} {agent_name}",
            title_align="left",
            border_style="cyan",
            padding=(0, 1),
        )
    )
    console.print()


async def _read_interactive_input_async() -> str:
    try:
        return await asyncio.to_thread(input, _prompt_text())
    except EOFError as exc:
        raise KeyboardInterrupt from exc


def version_callback(value: bool):
    if value:
        console.print(f"{__logo__} sotion v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True
    ),
):
    """sotion - AI Agent Team Manager."""
    pass


def _make_provider(config):
    """Create LiteLLMProvider from config."""
    from sotion.providers.litellm_provider import LiteLLMProvider
    p = config.get_provider()
    model = config.agents.defaults.model
    if not (p and p.api_key):
        console.print("[red]Error: No API key configured.[/red]")
        console.print("Set one in ~/.sotion/config.json under providers section")
        console.print("Or set SOTION_PROVIDERS__ANTHROPIC__API_KEY env var")
        raise typer.Exit(1)
    return LiteLLMProvider(
        api_key=p.api_key,
        api_base=config.get_api_base(),
        default_model=model,
        extra_headers=p.extra_headers if p else None,
        provider_name=config.get_provider_name(),
    )


# ============================================================================
# Serve (FastAPI server)
# ============================================================================


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Server host"),
    port: int = typer.Option(8000, "--port", "-p", help="Server port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
):
    """Start the sotion server (FastAPI + WebSocket)."""
    import uvicorn

    console.print(f"{__logo__} Starting sotion server on {host}:{port}...")
    console.print(f"  API docs: http://localhost:{port}/docs")
    console.print(f"  Health:   http://localhost:{port}/health")
    console.print()

    uvicorn.run(
        "sotion.main:app",
        host=host,
        port=port,
        reload=reload,
    )


# ============================================================================
# Agent (single-agent CLI mode)
# ============================================================================


@app.command()
def agent(
    message: str = typer.Option(None, "--message", "-m", help="Message to send"),
    session_id: str = typer.Option("cli:default", "--session", "-s", help="Session ID"),
    markdown: bool = typer.Option(True, "--markdown/--no-markdown", help="Render as Markdown"),
    logs: bool = typer.Option(False, "--logs/--no-logs", help="Show runtime logs"),
):
    """Chat with a single agent (CLI mode)."""
    from sotion.config.loader import load_config
    from sotion.bus.queue import MessageBus
    from sotion.agent.loop import AgentLoop
    from loguru import logger

    config = load_config()
    bus = MessageBus()
    provider = _make_provider(config)

    if logs:
        logger.enable("sotion")
    else:
        logger.disable("sotion")

    agent_loop = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=config.workspace_path,
        brave_api_key=config.tools.web.search.api_key or None,
        exec_config=config.tools.exec,
        restrict_to_workspace=config.tools.restrict_to_workspace,
    )

    def _thinking_ctx():
        if logs:
            from contextlib import nullcontext
            return nullcontext()
        return console.status("[dim]sotion is thinking...[/dim]", spinner="dots")

    if message:
        async def run_once():
            with _thinking_ctx():
                response = await agent_loop.process_direct(message, session_id)
            _print_agent_response(response, render_markdown=markdown)

        asyncio.run(run_once())
    else:
        _enable_line_editing()
        console.print(f"{__logo__} Interactive mode (type [bold]exit[/bold] or [bold]Ctrl+C[/bold] to quit)\n")

        def _exit_on_sigint(signum, frame):
            _save_history()
            _restore_terminal()
            console.print("\nGoodbye!")
            os._exit(0)

        signal.signal(signal.SIGINT, _exit_on_sigint)

        async def run_interactive():
            while True:
                try:
                    _flush_pending_tty_input()
                    user_input = await _read_interactive_input_async()
                    command = user_input.strip()
                    if not command:
                        continue
                    if command.lower() in EXIT_COMMANDS:
                        _save_history()
                        _restore_terminal()
                        console.print("\nGoodbye!")
                        break
                    with _thinking_ctx():
                        response = await agent_loop.process_direct(user_input, session_id)
                    _print_agent_response(response, render_markdown=markdown)
                except (KeyboardInterrupt, EOFError):
                    _save_history()
                    _restore_terminal()
                    console.print("\nGoodbye!")
                    break

        asyncio.run(run_interactive())


# ============================================================================
# Onboard
# ============================================================================


@app.command()
def onboard():
    """Initialize sotion configuration and workspace."""
    from sotion.config.loader import get_config_path, save_config
    from sotion.config.schema import Config
    from sotion.utils.helpers import get_workspace_path

    config_path = get_config_path()

    if config_path.exists():
        console.print(f"[yellow]Config already exists at {config_path}[/yellow]")
        if not typer.confirm("Overwrite?"):
            raise typer.Exit()

    config = Config()
    save_config(config)
    console.print(f"[green]✓[/green] Created config at {config_path}")

    workspace = get_workspace_path()
    console.print(f"[green]✓[/green] Workspace at {workspace}")

    # Create default files
    (workspace / "memory").mkdir(parents=True, exist_ok=True)
    (workspace / "skills").mkdir(parents=True, exist_ok=True)

    for name, content in {
        "AGENTS.md": "# Agent Instructions\n\nYou are a helpful AI assistant.\n",
        "SOUL.md": "# Soul\n\nI am sotion, an AI agent team manager.\n",
    }.items():
        f = workspace / name
        if not f.exists():
            f.write_text(content)

    console.print(f"\n{__logo__} sotion is ready!")
    console.print("\nNext steps:")
    console.print("  1. Set SOTION_PROVIDERS__ANTHROPIC__API_KEY or edit ~/.sotion/config.json")
    console.print("  2. Set SOTION_SUPABASE__URL and SOTION_SUPABASE__SERVICE_ROLE_KEY")
    console.print("  3. Run: [cyan]sotion serve[/cyan]")


# ============================================================================
# Status
# ============================================================================


@app.command()
def status():
    """Show sotion status."""
    from sotion.config.loader import load_config, get_config_path

    config_path = get_config_path()
    config = load_config()
    workspace = config.workspace_path

    console.print(f"{__logo__} sotion Status\n")
    console.print(f"Config: {config_path} {'[green]✓[/green]' if config_path.exists() else '[red]✗[/red]'}")
    console.print(f"Workspace: {workspace} {'[green]✓[/green]' if workspace.exists() else '[red]✗[/red]'}")

    if config_path.exists():
        console.print(f"Model: {config.agents.defaults.model}")
        console.print(f"Supabase: {'[green]✓[/green]' if config.supabase.url else '[red]not configured[/red]'}")
        console.print(f"Server: {config.server.host}:{config.server.port}")

        from sotion.providers.registry import PROVIDERS
        for spec in PROVIDERS:
            p = getattr(config.providers, spec.name, None)
            if p is None:
                continue
            has_key = bool(p.api_key)
            console.print(f"{spec.label}: {'[green]✓[/green]' if has_key else '[dim]not set[/dim]'}")


if __name__ == "__main__":
    app()
