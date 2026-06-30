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
from datetime import datetime, timedelta, timezone
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
  .age-badge {
    display: inline-block; font-size: 0.7rem; padding: 2px 8px;
    border-radius: 4px; margin-left: 8px; font-weight: 500;
    vertical-align: middle;
  }
  .age-today  { background: #059669; color: #d1fae5; }
  .age-3days  { background: #d97706; color: #fef3c7; }
  .age-week   { background: #6366f1; color: #e0e7ff; }
  .age-older  { background: #475569; color: #cbd5e1; }
  .news-item.item-today::before  { background: #34d399; }
  .news-item.item-3days::before  { background: #fbbf24; }
  .news-item.item-week::before   { background: #818cf8; }
  .news-item.item-older::before  { background: #64748b; }
  .section-header {
    font-size: 1rem; font-weight: 600; color: var(--accent);
    margin: 28px 0 16px 0; padding: 8px 0;
    border-bottom: 1px solid var(--border);
  }
  .section-header:first-child { margin-top: 0; }
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
  .error-card {
    background: rgba(220, 38, 38, 0.12); border: 1px solid #dc2626;
    color: #fca5a5; border-radius: 10px; padding: 14px 18px;
    margin-bottom: 20px; font-size: 0.88rem; line-height: 1.6;
  }
  .error-card .error-detail {
    color: var(--muted); font-size: 0.78rem; margin-top: 6px;
    word-break: break-all;
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
  <div id="error-section"></div>
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
    const status = json.status || 'ok';
    const data = json.data || [];

    // Status indicator in the header
    const statusText = document.getElementById('status-text');
    if (status === 'loading') {
      statusText.textContent = '首次抓取中';
    } else if (status === 'error') {
      statusText.textContent = data.length ? '刷新失败(显示历史数据)' : '抓取失败';
    } else {
      statusText.textContent = '运行中';
    }
    document.getElementById('update-time').textContent =
      json.last_updated ? ('更新于 ' + json.last_updated) : '尚未更新';

    renderError(status, json.last_error || '', data.length);
    renderSummary(json.summary || '');
    renderTimeline(data, status);
  } catch(e) {
    document.getElementById('status-text').textContent = '连接失败';
  }
}

function renderError(status, msg, hasData) {
  const el = document.getElementById('error-section');
  if (status !== 'error' || !msg) {
    el.innerHTML = '';
    return;
  }
  const note = hasData ? '本次刷新失败，下方为上一次成功抓取的内容。' : '抓取失败，将在下次刷新时重试。';
  el.innerHTML = `<div class="error-card">⚠️ ${note}<div class="error-detail">${escHtml(msg)}</div></div>`;
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

function renderTimeline(items, status) {
  const el = document.getElementById('timeline');
  if (!items.length) {
    if (status === 'loading') {
      el.className = 'loading';
      el.innerHTML = '<div class="spinner"></div><div>正在获取最新资讯，请稍候...</div>';
    } else if (status === 'error') {
      el.className = 'empty-state';
      el.innerHTML = '<div class="empty-state"><div class="icon">⚠️</div><div>抓取失败，等待下次刷新重试...</div></div>';
    } else {
      el.className = 'empty-state';
      el.innerHTML = '<div class="empty-state"><div class="icon">📭</div><div>暂无新闻数据，等待下次刷新...</div></div>';
    }
    return;
  }
  el.className = 'timeline';

  const ageLabels = {
    today: '📌 今日要闻',
    '3days': '📰 近三天动态',
    week: '📋 本周概览',
    older: '🗂️ 更早资讯'
  };
  const ageBadge = {
    today: '今日', '3days': '3天内', week: '本周', older: '更早'
  };
  const ageOrder = ['today', '3days', 'week', 'older'];

  // Group items by age
  const groups = {};
  items.forEach(item => {
    const age = item.age || 'today';
    if (!groups[age]) groups[age] = [];
    groups[age].push(item);
  });

  let html = '';
  ageOrder.forEach(age => {
    const list = groups[age];
    if (!list || !list.length) return;
    html += `<div class="section-header">${ageLabels[age] || age}（${list.length}条）</div>`;
    html += list.map((item, i) => `
      <div class="news-item item-${age}" style="animation: fadeIn 0.3s ease ${i*0.05}s both">
        <div class="news-time">${item.time || ''}<span class="age-badge age-${age}">${ageBadge[age]}</span></div>
        <div class="news-title">
          ${item.url ? `<a href="${item.url}" target="_blank" rel="noopener">${escHtml(item.title)}</a>` : escHtml(item.title)}
        </div>
        ${item.body ? `<div class="news-body">${escHtml(item.body)}</div>` : ''}
        ${item.url ? `<div class="news-source"><a href="${item.url}" target="_blank">${new URL(item.url).hostname}</a></div>` : ''}
      </div>
    `).join('');
  });

  el.innerHTML = html;
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
            f"首次新闻抓取与 AI 总结正在后台进行，页面会显示加载状态并在完成后自动刷新（通常 10~60 秒）。\n"
            f"使用 `stop` 动作可停止该服务。"
        )

    @staticmethod
    def _search_news(query: str, max_results: int = 20) -> list[dict]:
        """Search for news using DuckDuckGo with time-stratified fetching.

        Fetches news in three time windows (day / week / month) and tags
        each item with an age category so the summariser can give different
        levels of detail:
          - "today"   : published within the last 24 hours
          - "3days"   : published within the last 3 days
          - "week"    : published within the last 7 days
          - "older"   : everything else
        """
        try:
            import os as _os
            from ddgs import DDGS

            now = datetime.now()
            all_results: list[dict] = []
            seen_urls: set[str] = set()

            old_stderr_fd = _os.dup(2)
            devnull_fd = _os.open(_os.devnull, _os.O_WRONLY)
            _os.dup2(devnull_fd, 2)
            try:
                with DDGS() as ddgs:
                    # ── Phase 1: today's news (timelimit='d') ──
                    for fetcher, kw in [
                        (ddgs.news, {"query": query, "max_results": max_results, "timelimit": "d"}),
                        (ddgs.text, {"query": f"{query} 最新新闻", "max_results": max_results, "timelimit": "d"}),
                    ]:
                        try:
                            for r in fetcher(**kw):
                                url = r.get("url") or r.get("href", "")
                                if url and url not in seen_urls:
                                    seen_urls.add(url)
                                    all_results.append(r)
                            if all_results:
                                break
                        except Exception:
                            continue

                    # ── Phase 2: past week (timelimit='w') ──
                    for fetcher, kw in [
                        (ddgs.news, {"query": query, "max_results": max_results, "timelimit": "w"}),
                        (ddgs.text, {"query": f"{query} 新闻", "max_results": max_results, "timelimit": "w"}),
                    ]:
                        try:
                            for r in fetcher(**kw):
                                url = r.get("url") or r.get("href", "")
                                if url and url not in seen_urls:
                                    seen_urls.add(url)
                                    all_results.append(r)
                            break
                        except Exception:
                            continue

                    # ── Phase 3: past month as background (timelimit='m') ──
                    if len(all_results) < max_results:
                        for fetcher, kw in [
                            (ddgs.news, {"query": query, "max_results": max_results, "timelimit": "m"}),
                        ]:
                            try:
                                for r in fetcher(**kw):
                                    url = r.get("url") or r.get("href", "")
                                    if url and url not in seen_urls:
                                        seen_urls.add(url)
                                        all_results.append(r)
                                break
                            except Exception:
                                continue
            finally:
                _os.dup2(old_stderr_fd, 2)
                _os.close(old_stderr_fd)
                _os.close(devnull_fd)

            if not all_results:
                return []

            # ── Parse & categorise by age ──
            items = []
            now_str = now.strftime("%Y-%m-%d %H:%M")
            cutoff_today = now - timedelta(days=1)
            cutoff_3days = now - timedelta(days=3)
            cutoff_week = now - timedelta(days=7)

            for r in all_results:
                date_str = r.get("date", "")
                dt = None
                time_display = ""
                if date_str:
                    try:
                        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        if dt.tzinfo is not None:
                            dt = dt.replace(tzinfo=None)
                        time_display = dt.strftime("%Y-%m-%d %H:%M")
                    except (ValueError, TypeError):
                        time_display = str(date_str)[:19]
                if not time_display:
                    time_display = now_str

                # Determine age category
                if dt:
                    if dt >= cutoff_today:
                        age = "today"
                    elif dt >= cutoff_3days:
                        age = "3days"
                    elif dt >= cutoff_week:
                        age = "week"
                    else:
                        age = "older"
                else:
                    age = "today"   # no date → assume recent

                items.append({
                    "title": r.get("title", "无标题"),
                    "body": r.get("body", ""),
                    "url": r.get("url") or r.get("href", ""),
                    "time": time_display,
                    "source": r.get("source", ""),
                    "age": age,
                })

            # Sort: newest first
            def _sort_key(it):
                try:
                    return datetime.strptime(it["time"], "%Y-%m-%d %H:%M")
                except Exception:
                    return datetime.min
            items.sort(key=_sort_key, reverse=True)

            return items

        except Exception as e:
            return [{
                "title": f"新闻获取失败: {e}",
                "body": "将在下次刷新时重试。",
                "url": "",
                "time": datetime.now().strftime("%H:%M"),
                "source": "",
                "age": "today",
            }]

    @staticmethod
    def _summarize_news(topic: str, items: list[dict]) -> str:
        """Use the LLM to generate a time-stratified Chinese summary.

        Detail levels:
        - today  : full detailed summary
        - 3 days : moderate detail
        - week   : brief summary
        - older  : one-line mentions only
        """
        if not items or (len(items) == 1 and "获取失败" in items[0].get("title", "")):
            return ""
        try:
            from core.llm import LLMClient

            # Group by age category
            groups = {"today": [], "3days": [], "week": [], "older": []}
            for it in items[:40]:
                age = it.get("age", "today")
                groups.setdefault(age, []).append(it)

            def _fmt(lst, max_body=200):
                lines = []
                for i, it in enumerate(lst, 1):
                    line = f"{i}. [{it.get('time','')}] {it.get('title','')}"
                    body = it.get("body", "")
                    if body:
                        line += f" — {body[:max_body]}"
                    lines.append(line)
                return "\n".join(lines)

            sections = []
            if groups["today"]:
                sections.append(f"【今日新闻（24小时内，共{len(groups['today'])}条）】\n{_fmt(groups['today'], 200)}")
            if groups["3days"]:
                sections.append(f"【近三天新闻（共{len(groups['3days'])}条）】\n{_fmt(groups['3days'], 120)}")
            if groups["week"]:
                sections.append(f"【近一周新闻（共{len(groups['week'])}条）】\n{_fmt(groups['week'], 80)}")
            if groups["older"]:
                sections.append(f"【更早新闻（共{len(groups['older'])}条）】\n{_fmt(groups['older'], 50)}")

            if not sections:
                return ""

            news_text = "\n\n".join(sections)

            prompt = (
                f"你是一位专业的新闻分析师。以下是关于「{topic}」的新闻列表，已按时间分层：\n\n"
                f"{news_text}\n\n"
                "请 **严格按照以下分层结构** 输出总结：\n\n"
                "### 📌 今日要闻（最近24小时）\n"
                "对今日新闻做 **详细** 总结，每条重要新闻都要提及，分析其影响和意义。"
                "如果没有今日新闻，写「暂无今日新闻」。\n\n"
                "### 📰 近三天动态\n"
                "用 **适中篇幅** 总结近三天的关键新闻，提炼 3-5 个要点即可。"
                "如果没有此时段新闻，写「暂无近三天新闻」。\n\n"
                "### 📋 本周概览\n"
                "用 **简短** 的方式概括本周新闻趋势，2-3 句话即可。"
                "如果没有此时段新闻，写「暂无本周新闻」。\n\n"
                "### 🗂️ 更早资讯\n"
                "对超过一周的旧闻，仅用一两句话 **简述** 背景即可。"
                "如果没有更早新闻，可省略本节。\n\n"
                "### 📊 趋势判断\n"
                "基于所有新闻，简要判断该话题的走向和发展趋势。\n\n"
                "请用简洁的中文回答，使用 Markdown 格式。"
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
