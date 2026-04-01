"""
Git Daily/Weekly Summary Skill
- Supports both local paths and remote URLs (http/https/ssh/git@).
- For remote URLs it clones a bare repo to a local cache dir on first run,
  then fetches updates on subsequent runs.
- If today is Friday, summarizes the entire current week (Mon-Fri).
- Repository addresses, credentials, and cache dir are configured in
  config.yaml under the `git_summary` section.
"""

import re
import subprocess
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from skills.base import BaseSkill
from core.config import config


# ── Git helpers ────────────────────────────────────────────────────────────

def _is_remote_url(path: str) -> bool:
    return path.startswith(("http://", "https://", "git@", "ssh://", "git://"))


def _build_authed_url(url: str, username: str, token: str) -> str:
    """Inject username:token credentials into an HTTP(S) URL."""
    if not (username or token):
        return url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return url  # SSH/git urls don't use this mechanism
    userinfo = f"{username}:{token}" if (username and token) else (username or token)
    netloc = f"{userinfo}@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))


def _safe_dir_name(text: str) -> str:
    """Convert an arbitrary string to a safe directory name."""
    return re.sub(r"[^\w\-]", "_", text)[:64]


def _run_git(repo_path: str, args: list[str], env: dict | None = None) -> tuple[str, str, int]:
    """Run a git command; returns (stdout, stderr, returncode)."""
    import os
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    result = subprocess.run(
        ["git"] + args,
        cwd=repo_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=run_env,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def _ensure_bare_clone(url: str, cache_dir: Path) -> tuple[bool, str]:
    """
    Ensure a bare clone of `url` exists at `cache_dir` and is up to date.
    Returns (success, error_message).
    GIT_TERMINAL_PROMPT=0 prevents git from hanging waiting for a password.
    """
    env = {"GIT_TERMINAL_PROMPT": "0"}
    if cache_dir.exists():
        _, stderr, rc = _run_git(str(cache_dir), ["fetch", "--all", "--quiet"], env=env)
        if rc != 0:
            return False, f"fetch 失败: {stderr}"
    else:
        cache_dir.parent.mkdir(parents=True, exist_ok=True)
        _, stderr, rc = _run_git(
            str(cache_dir.parent),
            ["clone", "--bare", "--quiet", url, str(cache_dir)],
            env=env,
        )
        if rc != 0:
            return False, f"clone 失败: {stderr}"
    return True, ""


def _get_all_commits(repo_path: str, since: str, until: str) -> list[dict]:
    """Step 1: Fetch ALL commits in date range without any author filter."""
    cmd = [
        "log",
        f"--since={since} 00:00:00",
        f"--until={until} 23:59:59",
        "--format=%H|%an|%ae|%ad|%s",
        "--date=format:%Y-%m-%d %H:%M",
        "--no-merges",
        "--all",
    ]
    stdout, _, _ = _run_git(repo_path, cmd)
    commits = []
    for line in stdout.splitlines():
        parts = line.split("|", 4)
        if len(parts) == 5:
            commits.append({
                "hash": parts[0][:8],
                "author": parts[1],
                "email": parts[2],
                "date": parts[3],
                "message": parts[4],
            })
    return commits


def _filter_by_author(commits: list[dict], author: str) -> list[dict]:
    """Step 2: Filter commit list by author name or email (case-insensitive substring)."""
    if not author:
        return commits
    kw = author.lower()
    return [
        c for c in commits
        if kw in c["author"].lower() or kw in c["email"].lower()
    ]


def _format_for_llm(repo_name: str, commits: list[dict]) -> str:
    """Step 3: Format filtered commits into a block the LLM uses to produce a task list."""
    if not commits:
        return f"【{repo_name}】无提交记录"
    lines = [f"【{repo_name}】共 {len(commits)} 条提交："]
    for c in commits:
        lines.append(f"  {c['date']}  {c['message']}  ({c['hash']})")
    return "\n".join(lines)


class GitSummarySkill(BaseSkill):
    name = "git_daily_summary"
    description = (
        "读取配置的本地 Git 仓库，汇总今天的 commit 记录并生成工作总结。"
        "如果今天是周五，则总结本周（周一至今）的所有提交。"
        "当用户询问今天做了什么、工作日报、周报或 git 提交总结时使用此技能。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["auto", "today", "week"],
                "description": (
                    "汇总模式：auto=自动判断（周五自动切周报），"
                    "today=仅今日，week=本周。默认 auto。"
                ),
                "default": "auto",
            }
        },
        "required": [],
    }

    def execute(self, mode: str = "auto") -> str:
        # ── Determine date range ──────────────────────────────────────
        today = date.today()
        weekday = today.weekday()  # 0=Mon … 6=Sun

        if mode == "week":
            monday = today - timedelta(days=weekday)
            since = monday.isoformat()
            until = today.isoformat()
            period_label = f"本周（{monday} ~ {today}）"
        else:
            # auto / today: always use current day
            since = today.isoformat()
            until = today.isoformat()
            period_label = f"今日（{today}）"

        # ── Load config ───────────────────────────────────────────────
        repos_cfg: list[dict] = config.get("git_summary.repos", [])
        author_filter: str = config.get("git_summary.author", "")
        cache_root = Path(config.get("git_summary.cache_dir", "./data/git_cache"))

        if not repos_cfg:
            return (
                "⚠️  未配置 Git 仓库。请在 config.yaml 中添加 `git_summary.repos`，"
                "例如：\n\ngit_summary:\n  repos:\n    - path: http://your-server/repo.git\n      name: 项目名称"
            )

        # ── Per-repo: 3-step pipeline ─────────────────────────────────
        all_blocks: list[str] = []
        total_filtered = 0

        for repo in repos_cfg:
            raw_path: str = repo.get("path", "").strip()
            repo_name: str = repo.get("name", raw_path)
            repo_author: str = repo.get("author", author_filter)
            username: str = repo.get("username", config.get("git_summary.username", ""))
            token: str = repo.get("token", config.get("git_summary.token", ""))

            if not raw_path:
                continue

            # Resolve work_path (remote → bare clone, local → directory)
            if _is_remote_url(raw_path):
                authed_url = _build_authed_url(raw_path, username, token)
                cache_dir = cache_root / _safe_dir_name(repo_name)
                ok, err = _ensure_bare_clone(authed_url, cache_dir)
                if not ok:
                    all_blocks.append(f"【{repo_name}】⚠️  无法访问远程仓库: {err}")
                    continue
                work_path = str(cache_dir)
            else:
                if not Path(raw_path).is_dir():
                    all_blocks.append(f"【{repo_name}】⚠️  路径不存在: {raw_path}")
                    continue
                stdout, _, _ = _run_git(raw_path, ["rev-parse", "--show-toplevel"])
                if not stdout:
                    all_blocks.append(f"【{repo_name}】⚠️  不是有效的 Git 仓库: {raw_path}")
                    continue
                work_path = raw_path

            # Step 1: git log → 获取当期全部提交
            all_commits = _get_all_commits(work_path, since, until)

            # Step 2: 按 author 筛选
            filtered = _filter_by_author(all_commits, repo_author)
            total_filtered += len(filtered)

            # Step 3: 格式化为 LLM 可读的任务原料
            all_blocks.append(_format_for_llm(repo_name, filtered))

        if not all_blocks:
            return "⚠️  所有仓库均无法访问或未返回数据。"

        author_hint = f"（作者筛选：{author_filter}）" if author_filter else "（未设置作者过滤，显示所有人）"
        raw_data = "\n\n".join(all_blocks)

        if total_filtered == 0:
            return (
                f"📋 {period_label}提交记录 {author_hint}\n\n"
                f"{raw_data}\n\n"
                "本期间内没有找到符合条件的提交记录，无需生成任务列表。"
            )

        return (
            f"📋 {period_label}提交记录 {author_hint}\n\n"
            f"{raw_data}\n\n"
            "---\n"
            f"以上是 {period_label}的 git 提交明细，共 {total_filtered} 条。\n"
            "请根据这些 commit message，用中文整理成【今日完成任务列表】，"
            '要求：每条任务一行，以"- "开头，语言简洁，合并相关提交为一个任务项，去掉技术细节。'
        )
