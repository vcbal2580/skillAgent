#!/usr/bin/env python3
"""
SkillAgent - CLI Entry Point
A small extensible skill-based AI agent with knowledge base and web search.
"""

import sys
import os
import argparse

# Ensure project root is on sys.path when run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import config


def run_cli():
    """Run the interactive CLI chat interface."""
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from core.agent import Agent
    from core.i18n import _

    console = Console()

    console.print(Panel.fit(
        "[bold cyan]SkillAgent[/bold cyan] v0.1.0\n"
        + _("AI Assistant - Web Search | Knowledge Base | Extensible Skills") + "\n\n"
        + _("Commands: [green]/help[/green] help | [green]/reset[/green] reset | "
            "[green]/skills[/green] skill list | [green]/quit[/green] exit"),
        title="🤖 Welcome",
        border_style="cyan",
    ))

    agent = Agent()
    agent.register_default_skills()

    _ctrl_c_count = 0  # track consecutive Ctrl+C presses

    while True:
        try:
            console.print()
            user_input = console.input("[bold green]You > [/bold green]").strip()
            _ctrl_c_count = 0  # reset on successful input

            if not user_input:
                continue

            # Handle slash commands
            if user_input.startswith("/"):
                cmd = user_input.lower()
                if cmd in ("/quit", "/exit", "/q"):
                    console.print(f"[dim]{_('Goodbye! 👋')}[/dim]")
                    break
                elif cmd == "/reset":
                    agent.reset()
                    console.print(f"[yellow]{_('Conversation reset')}[/yellow]")
                    continue
                elif cmd == "/skills":
                    skills = agent.registry.list_skills()
                    console.print(Panel(
                        "\n".join(f"• {s}" for s in skills),
                        title=_("Registered Skills"),
                        border_style="blue",
                    ))
                    continue
                elif cmd == "/help":
                    console.print(Panel(
                        _("/help   - Show help\n"
                          "/reset  - Reset conversation history\n"
                          "/skills - Show registered skills\n"
                          "/quit   - Exit (or press Ctrl+C twice)\n\n"
                          "Type directly to chat with the assistant.\n"
                          "The assistant can call skills for web search, knowledge management, etc."),
                        title=_("Help"),
                        border_style="green",
                    ))
                    continue
                else:
                    console.print(f"[red]{cmd}[/red] - unknown command, type /help")
                    continue

            # Send message to agent
            with console.status(f"[bold cyan]{_('Thinking...')}[/bold cyan]", spinner="dots"):
                reply = agent.chat(user_input)

            console.print()
            console.print(Markdown(reply), style="white")

        except KeyboardInterrupt:
            _ctrl_c_count += 1
            if _ctrl_c_count >= 2:
                console.print(f"\n[dim]{_('Goodbye! 👋')}[/dim]")
                break
            console.print(f"\n[dim]{_('Press Ctrl+C again (or /quit) to exit')}[/dim]")
            continue
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            continue


def run_server():
    """Start the FastAPI server."""
    from api.server import start_server
    start_server()


def main():
    parser = argparse.ArgumentParser(description="SkillAgent - AI Skill Assistant")
    parser.add_argument(
        "mode",
        nargs="?",
        default="cli",
        choices=["cli", "server"],
        help="Running mode: cli=interactive CLI (default), server=API server",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Config file path (default: config.yaml)",
    )

    args = parser.parse_args()

    # Load config first so i18n can read the language setting
    config.load(args.config)

    # Initialise i18n (UI strings) and prompt_loader (LLM-facing prompts)
    from core.i18n import setup as i18n_setup
    from core.prompt_loader import setup as prompt_setup
    lang = config.get("language", "en")
    i18n_setup(lang)
    prompt_setup(lang)

    if args.mode == "server":
        print("Starting API server...")
        run_server()
    else:
        run_cli()


if __name__ == "__main__":
    main()
