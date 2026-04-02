"""
Workflow dashboard skill - starts a local dashboard for all running workflows.
"""

from skills.base import BaseSkill
from skills.workflow_service import WorkflowManager


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
<meta charset=\"UTF-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
<title>Workflow Dashboard</title>
<style>
  body { margin:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background:#0b1220; color:#e2e8f0; }
  .top { padding:16px 20px; border-bottom:1px solid #1f2d45; background:#111d32; position:sticky; top:0; }
  .top h1 { margin:0; font-size:1.1rem; color:#7dd3fc; }
  .meta { margin-top:4px; color:#94a3b8; font-size:0.82rem; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:12px; padding:16px; }
  .card { background:#14243a; border:1px solid #223c60; border-radius:12px; padding:14px; }
  .name { font-size:1rem; color:#38bdf8; margin:0 0 6px 0; }
  .row { color:#cbd5e1; font-size:0.88rem; margin:4px 0; }
  .link { color:#7dd3fc; text-decoration:none; }
  .empty { margin:16px; border:1px dashed #2d3f5a; border-radius:10px; padding:16px; color:#94a3b8; }
</style>
</head>
<body>
  <div class=\"top\">
    <h1>Workflow Dashboard</h1>
    <div class=\"meta\">集中查看本地工作流状态</div>
  </div>
  <div id=\"root\"></div>
  <script>
    function render(items) {
      const root = document.getElementById('root');
      if (!items.length) {
        root.innerHTML = '<div class=\"empty\">当前没有运行中的工作流</div>';
        return;
      }
      root.innerHTML = `<div class=\"grid\">${items.map((wf) => `
        <article class=\"card\">
          <h3 class=\"name\">${wf.name}</h3>
          <div class=\"row\">端口: ${wf.port}</div>
          <div class=\"row\">刷新: ${Math.round((wf.refresh_seconds || 0) / 60)} 分钟</div>
          <div class=\"row\">更新: ${wf.last_updated || '-'}</div>
          <div class=\"row\"><a class=\"link\" href=\"${wf.url}\" target=\"_blank\" rel=\"noopener noreferrer\">打开工作流</a></div>
        </article>
      `).join('')}</div>`;
    }

    async function refresh() {
      const res = await fetch('/api/data');
      const payload = await res.json();
      render(payload.data || []);
    }

    refresh();
    setInterval(refresh, 5000);
  </script>
</body>
</html>
"""


class WorkflowDashboardSkill(BaseSkill):
    name = "workflow_dashboard"
    description = "Start a local dashboard page that lists all running workflows."
    parameters = {
        "type": "object",
        "properties": {},
    }

    def execute(self) -> str:
        manager = WorkflowManager()

        def fetch_fn():
            return {
                "items": manager.list_workflows(),
                "summary": "Workflow dashboard",
            }

        wf = manager.start_workflow(
            name="workflow_dashboard",
            refresh_seconds=5,
            fetch_fn=fetch_fn,
            html_template=DASHBOARD_HTML,
            preferred_port=9000,
        )

        return (
            "工作流总控台已启动\n"
            f"URL: http://127.0.0.1:{wf.port}\n"
            "可查看所有运行中 workflow 的状态与入口。"
        )
