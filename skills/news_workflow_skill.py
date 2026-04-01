"""
News workflow skill - creates a local live-updating news timeline web service.

When triggered, this skill:
1. Searches for news via DuckDuckGo
2. Starts a local HTTP server with a beautiful timeline page
3. Refreshes news at a configurable interval (default: 60 minutes)
4. Returns the local URL to the user

The LLM decides the refresh interval based on the nature of the query.
"""

import os
from datetime import datetime
from skills.base import BaseSkill
from skills.workflow_service import WorkflowManager


# ── HTML Template ──────────────────────────────────────────
NEWS_TIMELINE_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📰 {title} - SkillAgent 新闻时间轴</title>
<style>
  :root {
    --bg: #0f172a; --card: #1e293b; --accent: #38bdf8;
    --text: #e2e8f0; --muted: #94a3b8; --border: #334155;
    --success: #34d399; --warn: #fbbf24;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: var(--bg); color: var(--text); min-height: 100vh;
  }
  .header {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-bottom: 1px solid var(--border);
    padding: 20px 0; position: sticky; top: 0; z-index: 100;
    backdrop-filter: blur(10px);
  }
  .header-inner {
    max-width: 900px; margin: 0 auto; padding: 0 24px;
    display: flex; justify-content: space-between; align-items: center;
  }
  .header h1 { font-size: 1.4rem; font-weight: 600; }
  .header h1 span { color: var(--accent); }
  .status {
    display: flex; align-items: center; gap: 8px;
    font-size: 0.85rem; color: var(--muted);
  }
  .status-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--success); animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; } 50% { opacity: 0.4; }
  }
  .container { max-width: 900px; margin: 0 auto; padding: 32px 24px; }
  .timeline { position: relative; padding-left: 32px; }
  .timeline::before {
    content: ''; position: absolute; left: 7px; top: 0; bottom: 0;
    width: 2px; background: var(--border);
  }
  .news-item {
    position: relative; margin-bottom: 24px;
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px; transition: all 0.3s;
  }
  .news-item:hover {
    border-color: var(--accent); transform: translateX(4px);
    box-shadow: 0 4px 20px rgba(56, 189, 248, 0.1);
  }
  .news-item::before {
    content: ''; position: absolute; left: -29px; top: 24px;
    width: 12px; height: 12px; border-radius: 50%;
    background: var(--accent); border: 2px solid var(--bg);
  }
  .news-time {
    font-size: 0.8rem; color: var(--accent); font-weight: 500;
    margin-bottom: 8px; letter-spacing: 0.5px;
  }
  .news-title {
    font-size: 1.1rem; font-weight: 600; margin-bottom: 8px;
    line-height: 1.5;
  }
  .news-title a {
    color: var(--text); text-decoration: none; transition: color 0.2s;
  }
  .news-title a:hover { color: var(--accent); }
  .news-body {
    font-size: 0.9rem; color: var(--muted); line-height: 1.7;
  }
  .news-source {
    font-size: 0.75rem; color: var(--border); margin-top: 10px;
  }
  .news-source a { color: var(--muted); text-decoration: none; }
  .news-source a:hover { color: var(--accent); }
  .empty-state {
    text-align: center; padding: 60px 20px; color: var(--muted);
  }
  .empty-state .icon { font-size: 3rem; margin-bottom: 16px; }
  .summary-card {
    background: linear-gradient(135deg, #1e3a5f 0%, #1e293b 100%);
    border: 1px solid var(--accent); border-radius: 14px;
    padding: 24px 28px; margin-bottom: 32px;
    box-shadow: 0 4px 24px rgba(56, 189, 248, 0.08);
  }
  .summary-card .summary-header {
    display: flex; align-items: center; gap: 10px;
    font-size: 1rem; font-weight: 600; color: var(--accent);
    margin-bottom: 16px; padding-bottom: 12px;
    border-bottom: 1px solid rgba(56, 189, 248, 0.2);
  }
  .summary-card .summary-body {
    font-size: 0.92rem; color: var(--text); line-height: 1.8;
  }
  .summary-card .summary-body h3 {
    color: var(--accent); font-size: 0.95rem; margin: 16px 0 8px 0;
  }
  .summary-card .summary-body ul,
  .summary-card .summary-body ol {
    padding-left: 20px; margin: 8px 0;
  }
  .summary-card .summary-body li { margin-bottom: 4px; }
  .summary-card .summary-body strong { color: #7dd3fc; }
  .summary-card .summary-body p { margin: 8px 0; }
  .summary-loading {
    color: var(--muted); font-style: italic; font-size: 0.88rem;
  }
  .refresh-bar {
    text-align: center; padding: 16px; color: var(--muted);
    font-size: 0.8rem;
  }
  .manual-refresh {
    background: none; border: 1px solid var(--border); color: var(--accent);
    padding: 6px 16px; border-radius: 6px; cursor: pointer;
    font-size: 0.8rem; margin-left: 12px; transition: all 0.2s;
  }
  .manual-refresh:hover {
    background: var(--accent); color: var(--bg);
  }
  .loading { text-align: center; padding: 40px; color: var(--muted); }
  .loading .spinner {
    display: inline-block; width: 24px; height: 24px;
    border: 3px solid var(--border); border-top-color: var(--accent);
    border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 12px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  @media (max-width: 640px) {
    .header-inner { flex-direction: column; gap: 8px; }
    .container { padding: 20px 16px; }
    .timeline { padding-left: 24px; }
    .news-item::before { left: -21px; width: 10px; height: 10px; }
  }
</style>
</head>
<body>
<div class="header">
  <div class="header-inner">
    <h1>📰 <span>{title}</span></h1>
    <div class="status">
      <div class="status-dot"></div>
      <span id="status-text">运行中</span>
      <span>|</span>
      <span id="update-time">加载中...</span>
    </div>
  </div>
</div>
<div class="container">
  <div id="summary-section"></div>
  <div id="timeline" class="loading">
    <div class="spinner"></div>
    <div>正在获取最新资讯...</div>
  </div>
  <div class="refresh-bar">
    <span id="next-refresh"></span>
    <button class="manual-refresh" onclick="fetchData()">🔄 手动刷新</button>
  </div>
</div>
<script>
let refreshSeconds = 3600;
let countdown = 0;

async function fetchData() {
  try {
    const resp = await fetch('/api/data');
    const json = await resp.json();
    refreshSeconds = json.refresh_seconds || 3600;
    countdown = refreshSeconds;
    document.getElementById('update-time').textContent = '更新于 ' + json.last_updated;
    renderSummary(json.summary || '');
    renderTimeline(json.data || []);
  } catch(e) {
    document.getElementById('status-text').textContent = '连接失败';
  }
}

function renderSummary(md) {
  const el = document.getElementById('summary-section');
  if (!md) {
    el.innerHTML = '';
    return;
  }
  el.innerHTML = `
    <div class="summary-card" style="animation: fadeIn 0.4s ease both">
      <div class="summary-header">🤖 AI 新闻总结</div>
      <div class="summary-body">${mdToHtml(md)}</div>
    </div>`;
}

function mdToHtml(md) {
  // Lightweight Markdown → HTML (handles ###, **bold**, lists, paragraphs)
  let html = escHtml(md);
  // headings
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
  // bold
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // unordered list items
  html = html.replace(/^[-*] (.+)$/gm, '<li>$1</li>');
  // ordered list items
  html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');
  // wrap consecutive <li> in <ul>
  html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');
  // paragraphs: double newlines
  html = html.replace(/\n{2,}/g, '</p><p>');
  // single newlines inside text to <br>
  html = html.replace(/\n/g, '<br>');
  // clean up empty tags
  html = html.replace(/<p><\/p>/g, '');
  html = html.replace(/<br><h3>/g, '<h3>');
  html = html.replace(/<\/h3><br>/g, '</h3>');
  html = html.replace(/<br><ul>/g, '<ul>');
  html = html.replace(/<\/ul><br>/g, '</ul>');
  return '<p>' + html + '</p>';
}

function renderTimeline(items) {
  const el = document.getElementById('timeline');
  if (!items.length) {
    el.innerHTML = '<div class="empty-state"><div class="icon">📭</div><div>暂无新闻数据，等待下次刷新...</div></div>';
    return;
  }
  el.className = 'timeline';
  el.innerHTML = items.map((item, i) => `
    <div class="news-item" style="animation: fadeIn 0.3s ease ${i*0.05}s both">
      <div class="news-time">${item.time || ''}</div>
      <div class="news-title">
        ${item.url ? `<a href="${item.url}" target="_blank" rel="noopener">${escHtml(item.title)}</a>` : escHtml(item.title)}
      </div>
      ${item.body ? `<div class="news-body">${escHtml(item.body)}</div>` : ''}
      ${item.url ? `<div class="news-source"><a href="${item.url}" target="_blank">${new URL(item.url).hostname}</a></div>` : ''}
    </div>
  `).join('');
}

function escHtml(t) {
  const d = document.createElement('div');
  d.textContent = t || '';
  return d.innerHTML;
}

function updateCountdown() {
  countdown--;
  if (countdown <= 0) { fetchData(); return; }
  const m = Math.floor(countdown / 60);
  const s = countdown % 60;
  document.getElementById('next-refresh').textContent =
    `每 ${Math.round(refreshSeconds/60)} 分钟自动刷新 · 下次刷新: ${m}分${s}秒`;
}

// Add fade-in animation
const style = document.createElement('style');
style.textContent = '@keyframes fadeIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }';
document.head.appendChild(style);

fetchData();
setInterval(updateCountdown, 1000);
</script>
</body>
</html>"""


class NewsWorkflowSkill(BaseSkill):
    name = "news_workflow"
    description = (
        "Create a live-updating local news timeline web service. "
        "When the user wants to monitor news or track a topic, use this skill to "
        "launch a local web page that automatically refreshes with the latest news. "
        "The user can then open the URL in their browser to view a continuously updated "
        "news timeline. Also supports listing and stopping running workflow services."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["start", "stop", "list"],
                "description": (
                    "Action to perform: "
                    "'start' to create a new news monitoring service, "
                    "'stop' to stop a running service, "
                    "'list' to list all running workflow services."
                ),
                "default": "start",
            },
            "topic": {
                "type": "string",
                "description": (
                    "The news topic or search query, e.g. 'AI latest news', "
                    "'tech industry', 'crypto market'. Required for 'start' action."
                ),
            },
            "refresh_minutes": {
                "type": "integer",
                "description": (
                    "How often to refresh the news (in minutes). "
                    "Default: 60. For breaking news use 15-30, for general topics use 60-120. "
                    "Decide based on the urgency of the topic."
                ),
                "default": 60,
            },
            "max_results": {
                "type": "integer",
                "description": "Max news items per refresh. Default: 20.",
                "default": 20,
            },
            "workflow_name": {
                "type": "string",
                "description": "Name of the workflow to stop (for 'stop' action).",
            },
        },
        "required": ["action"],
    }

    def execute(
        self,
        action: str = "start",
        topic: str = "",
        refresh_minutes: int = 60,
        max_results: int = 20,
        workflow_name: str = "",
    ) -> str:
        manager = WorkflowManager()

        if action == "list":
            workflows = manager.list_workflows()
            if not workflows:
                return "当前没有运行中的工作流服务。"
            lines = ["当前运行中的工作流服务：\n"]
            for wf in workflows:
                lines.append(
                    f"• **{wf['name']}** — {wf['url']}\n"
                    f"  刷新间隔: {wf['refresh_seconds'] // 60}分钟 | "
                    f"最近更新: {wf['last_updated']} | "
                    f"创建时间: {wf['created_at']}"
                )
            return "\n".join(lines)

        if action == "stop":
            name = workflow_name or topic
            if not name:
                return "请指定要停止的工作流名称。使用 list 查看所有运行中的工作流。"
            # Try exact match first, then partial match
            if manager.stop_workflow(name):
                return f"✅ 工作流 **{name}** 已停止。"
            # Try partial match
            for wf in manager.list_workflows():
                if name in wf["name"]:
                    manager.stop_workflow(wf["name"])
                    return f"✅ 工作流 **{wf['name']}** 已停止。"
            return f"未找到名为 '{name}' 的工作流。"

        # action == "start"
        if not topic:
            return "请告诉我你想要监控什么新闻主题。"

        refresh_seconds = max(refresh_minutes, 1) * 60

        # Build the fetch function
        search_query = topic
        search_max = max_results

        def fetch_news() -> dict:
            items = self._search_news(search_query, search_max)
            summary = self._summarize_news(search_query, items)
            return {"items": items, "summary": summary}

        # Generate a workflow name based on topic
        wf_name = f"news_{topic[:20].replace(' ', '_')}"

        html = NEWS_TIMELINE_HTML.replace("{title}", _escape_html(topic))

        wf = manager.start_workflow(
            name=wf_name,
            refresh_seconds=refresh_seconds,
            fetch_fn=fetch_news,
            html_template=html,
        )

        url = f"http://127.0.0.1:{wf.port}"
        return (
            f"✅ 新闻监控工作流已启动！\n\n"
            f"• **主题**: {topic}\n"
            f"• **访问地址**: {url}\n"
            f"• **刷新间隔**: 每 {refresh_minutes} 分钟\n"
            f"• **工作流名称**: {wf_name}\n\n"
            f"请在浏览器中打开 {url} 查看实时新闻时间轴。\n"
            f"使用 `stop` 动作可停止该服务。"
        )

    @staticmethod
    def _search_news(query: str, max_results: int = 20) -> list[dict]:
        """Search for news using DuckDuckGo and return formatted items.

        Strategy: try ddgs.news() first; if a DecodeError / connection error
        occurs (common on Windows with primp/curl_cffi), fall back to
        ddgs.text() with a news-oriented query.
        """
        try:
            import os as _os
            from ddgs import DDGS

            results = None

            old_stderr_fd = _os.dup(2)
            devnull_fd = _os.open(_os.devnull, _os.O_WRONLY)
            _os.dup2(devnull_fd, 2)
            try:
                with DDGS() as ddgs:
                    # Attempt 1: ddgs.news() — gives richer metadata
                    try:
                        results = list(ddgs.news(query, max_results=max_results))
                    except Exception:
                        results = None

                    # Attempt 2: fall back to ddgs.text() with news keywords
                    if not results:
                        news_query = f"{query} 最新新闻 news"
                        try:
                            results = list(ddgs.text(news_query, max_results=max_results))
                        except Exception:
                            results = None
            finally:
                _os.dup2(old_stderr_fd, 2)
                _os.close(old_stderr_fd)
                _os.close(devnull_fd)

            if not results:
                return []

            items = []
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            for r in results:
                # ddgs.news fields: title, body, url, date, source, image
                # ddgs.text fields: title, body, href
                date_str = r.get("date", "")
                time_display = ""
                if date_str:
                    try:
                        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        time_display = dt.strftime("%Y-%m-%d %H:%M")
                    except (ValueError, TypeError):
                        time_display = str(date_str)[:19]
                if not time_display:
                    time_display = now_str

                items.append({
                    "title": r.get("title", "无标题"),
                    "body": r.get("body", ""),
                    "url": r.get("url") or r.get("href", ""),
                    "time": time_display,
                    "source": r.get("source", ""),
                })

            return items

        except Exception as e:
            return [{
                "title": f"新闻获取失败: {e}",
                "body": "将在下次刷新时重试。",
                "url": "",
                "time": datetime.now().strftime("%H:%M"),
                "source": "",
            }]

    @staticmethod
    def _summarize_news(topic: str, items: list[dict]) -> str:
        """Use the LLM to generate a Chinese summary of the collected news."""
        if not items or (len(items) == 1 and "获取失败" in items[0].get("title", "")):
            return ""
        try:
            from core.llm import LLMClient

            # Build a concise text of all headlines + bodies for the LLM
            lines = []
            for i, it in enumerate(items[:30], 1):
                line = f"{i}. [{it.get('time','')}] {it.get('title','')}"
                body = it.get("body", "")
                if body:
                    line += f" — {body[:120]}"
                lines.append(line)
            news_text = "\n".join(lines)

            prompt = (
                f"你是一位专业的新闻分析师。以下是关于「{topic}」的最新新闻列表：\n\n"
                f"{news_text}\n\n"
                "请完成以下任务：\n"
                "1. **总览**：用 2-3 句话概括当前该话题的整体态势\n"
                "2. **关键要点**：提炼 3-5 个最重要的要点，每个要点一句话\n"
                "3. **趋势判断**：基于这些新闻，简要判断该话题的走向\n\n"
                "请用简洁的中文回答，使用 Markdown 格式（标题用 ###）。"
            )

            llm = LLMClient()
            response = llm.chat(
                messages=[{"role": "user", "content": prompt}],
                tools=None,
            )
            return response.content or ""
        except Exception as e:
            return f"（AI 总结生成失败：{e}）"


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
