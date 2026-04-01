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
                        _("/help              - Show help\n"
                          "/reset             - Reset conversation history\n"
                          "/skills            - Show registered skills\n"
                          "/workflows         - List running workflow services\n"
                          "/image <path|url>  - Send an image for visual analysis\n"
                          "/voice [seconds]   - Record microphone and transcribe (default 5s)\n"
                          "/doc <path|url>    - Read & analyse a document (PDF/docx/xlsx), optional save to knowledge base\n"
                          "/quit              - Exit (or press Ctrl+C twice)\n\n"
                          "Type directly to chat with the assistant.\n"
                          "The assistant can call skills for web search, knowledge management, etc."),
                        title=_("Help"),
                        border_style="green",
                    ))
                    continue
                elif cmd == "/workflows":
                    from skills.workflow_service import WorkflowManager
                    wf_manager = WorkflowManager()
                    workflows = wf_manager.list_workflows()
                    if not workflows:
                        console.print("[yellow]当前没有运行中的工作流服务。[/yellow]")
                    else:
                        lines = []
                        for wf in workflows:
                            lines.append(
                                f"• [bold]{wf['name']}[/bold] — [cyan]{wf['url']}[/cyan]\n"
                                f"  刷新间隔: {wf['refresh_seconds'] // 60}分钟 | "
                                f"最近更新: {wf['last_updated']} | "
                                f"创建时间: {wf['created_at']}"
                            )
                        console.print(Panel(
                            "\n".join(lines),
                            title="运行中的工作流",
                            border_style="blue",
                        ))
                    continue
                elif user_input.lower().startswith("/image "):
                    image_source = user_input[7:].strip()
                    if not image_source:
                        console.print("[red]Usage: /image <path or URL>[/red]")
                        continue
                    prompt = console.input("[bold green]Prompt (press Enter for default) > [/bold green]").strip()
                    if not prompt:
                        prompt = "请描述并分析这张图片"
                    with console.status(f"[bold cyan]{_('Thinking...')}[/bold cyan]", spinner="dots"):
                        reply = agent.chat_with_image(user_input=prompt, image_source=image_source)
                    console.print()
                    console.print(Markdown(reply), style="white")
                    continue
                elif user_input.lower().startswith("/voice"):
                    parts = user_input.split()
                    duration = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 5
                    try:
                        from core.stt import get_stt_engine
                        engine = get_stt_engine()
                        console.print(f"[cyan]Recording {duration}s - speak now...[/cyan]")
                        transcribed = engine.transcribe_mic(duration=duration)
                        if not transcribed.strip():
                            console.print("[yellow]No speech detected.[/yellow]")
                            continue
                        console.print(f"[dim]Transcribed: {transcribed}[/dim]")
                        with console.status(f"[bold cyan]{_('Thinking...')}[/bold cyan]", spinner="dots"):
                            reply = agent.chat(transcribed)
                        console.print()
                        console.print(Markdown(reply), style="white")
                    except Exception as exc:
                        console.print(f"[red]Voice error: {exc}[/red]")
                    continue
                elif user_input.lower().startswith("/doc "):
                    doc_source = user_input[5:].strip()
                    if not doc_source:
                        console.print("[red]Usage: /doc <path or URL>[/red]")
                        continue
                    question = console.input("[bold green]Question (press Enter to summarize) > [/bold green]").strip()
                    if not question:
                        question = "请总结这份文档的主要内容"
                    save_input = console.input("[bold green]Save to knowledge base? (y/N) > [/bold green]").strip().lower()
                    save_to_knowledge = save_input in ("y", "yes")
                    from skills.document_skill import extract_document, extract_document_from_url
                    from pathlib import Path
                    with console.status("[bold cyan]Extracting document...[/bold cyan]", spinner="dots"):
                        if doc_source.startswith("http"):
                            text = extract_document_from_url(doc_source)
                        else:
                            text = extract_document(doc_source)
                    if not text.strip():
                        console.print("[yellow]No text could be extracted from the document.[/yellow]")
                        continue
                    max_chars = 12000
                    truncated = text[:max_chars]
                    knowledge_id = None
                    if save_to_knowledge:
                        try:
                            from knowledge.knowledge_manager import KnowledgeManager
                            km = KnowledgeManager()
                            tags = ["document", Path(doc_source).stem]
                            knowledge_id = km.save(content=truncated, tags=[t for t in tags if t])
                            console.print(f"[green]已存入知识库，ID: {knowledge_id}[/green]")
                        except Exception as e:
                            console.print(f"[yellow]存入知识库失败: {e}[/yellow]")
                    prompt = f"以下是文档内容（可能已截断）：\n\n{truncated}\n\n请根据以上内容回答：{question}"
                    with console.status(f"[bold cyan]{_('Thinking...')}[/bold cyan]", spinner="dots"):
                        reply = agent.chat(prompt)
                    console.print()
                    console.print(Markdown(reply), style="white")
                    continue
                else:
                    console.print(f"[red]{user_input.split()[0]}[/red] - unknown command, type /help")
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
