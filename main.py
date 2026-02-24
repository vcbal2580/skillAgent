#!/usr/bin/env python3
"""
SkillAgent - CLI Entry Point
A small extensible skill-based AI agent with knowledge base and web search.
"""

import sys
import os
import argparse

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import config


def run_cli():
    """Run the interactive CLI chat interface."""
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from core.agent import Agent

    console = Console()

    console.print(Panel.fit(
        "[bold cyan]SkillAgent[/bold cyan] v0.1.0\n"
        "智能助手 - 支持联网搜索 | 知识库管理 | 可扩展技能\n\n"
        "命令: [green]/help[/green] 帮助 | [green]/reset[/green] 重置对话 | "
        "[green]/skills[/green] 技能列表 | [green]/quit[/green] 退出",
        title="🤖 Welcome",
        border_style="cyan",
    ))

    agent = Agent()
    agent.register_default_skills()

    while True:
        try:
            console.print()
            user_input = console.input("[bold green]You > [/bold green]").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                cmd = user_input.lower()
                if cmd in ("/quit", "/exit", "/q"):
                    console.print("[dim]再见！👋[/dim]")
                    break
                elif cmd == "/reset":
                    agent.reset()
                    console.print("[yellow]对话已重置[/yellow]")
                    continue
                elif cmd == "/skills":
                    skills = agent.registry.list_skills()
                    console.print(Panel(
                        "\n".join(f"• {s}" for s in skills),
                        title="已注册技能",
                        border_style="blue",
                    ))
                    continue
                elif cmd == "/help":
                    console.print(Panel(
                        "/help   - 显示帮助\n"
                        "/reset  - 重置对话历史\n"
                        "/skills - 显示已注册技能\n"
                        "/quit   - 退出程序\n\n"
                        "直接输入文字即可与助手对话。\n"
                        "助手可以自动调用技能来联网搜索、管理知识库等。",
                        title="帮助",
                        border_style="green",
                    ))
                    continue
                else:
                    console.print(f"[red]未知命令: {cmd}[/red]，输入 /help 查看帮助")
                    continue

            # Chat with agent
            with console.status("[bold cyan]思考中...[/bold cyan]", spinner="dots"):
                reply = agent.chat(user_input)

            console.print()
            console.print(Markdown(reply), style="white")

        except KeyboardInterrupt:
            console.print("\n[dim]按 /quit 退出[/dim]")
            continue
        except Exception as e:
            console.print(f"[red]错误: {e}[/red]")
            continue


def run_server():
    """Start the API server."""
    from api.server import start_server
    start_server()


def main():
    parser = argparse.ArgumentParser(description="SkillAgent - 智能技能助手")
    parser.add_argument(
        "mode",
        nargs="?",
        default="cli",
        choices=["cli", "server"],
        help="运行模式: cli=交互式命令行(默认), server=API服务器",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="配置文件路径 (默认: config.yaml)",
    )

    args = parser.parse_args()

    # Load configuration
    config.load(args.config)

    if args.mode == "server":
        print("Starting API server...")
        run_server()
    else:
        run_cli()


if __name__ == "__main__":
    main()
