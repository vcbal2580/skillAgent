"""
Page generation skill - render structured data into local workflow pages.
"""

import json
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from skills.base import BaseSkill
from skills.workflow_service import WorkflowManager


class PageGenerateSkill(BaseSkill):
    name = "page_generate"
    description = "Generate a local workflow page from structured data and return a local URL."
    parameters = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Page title",
            },
            "template": {
                "type": "string",
                "enum": ["timeline", "report", "table", "cards"],
                "default": "cards",
                "description": "Template style",
            },
            "data": {
                "type": "string",
                "description": "JSON string of list data",
            },
            "summary": {
                "type": "string",
                "description": "Optional summary text",
            },
            "refresh_seconds": {
                "type": "integer",
                "default": 0,
                "description": "Auto-refresh interval in seconds; 0 means static",
            },
            "workflow_name": {
                "type": "string",
                "description": "Optional workflow name override",
            },
        },
        "required": ["title", "data"],
    }

    def execute(
        self,
        title: str,
        data: str,
        template: str = "cards",
        summary: str = "",
        refresh_seconds: int = 0,
        workflow_name: str = "",
    ) -> str:
        try:
            items = json.loads(data)
            if not isinstance(items, list):
                return "data must be a JSON list"
        except json.JSONDecodeError as e:
            return f"Invalid JSON in data: {e}"

        template_name = f"{template}.html"
        templates_dir = Path(__file__).resolve().parent / "templates"
        env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=False)

        try:
            page_template = env.get_template(template_name)
        except Exception:
            return f"Unknown template: {template}"

        html = page_template.render(
            title=title,
            refresh_seconds=max(0, int(refresh_seconds)),
            initial_data_json=json.dumps(items, ensure_ascii=False),
            initial_summary_json=json.dumps(summary or "", ensure_ascii=False),
            initial_last_updated="",
        )

        name = workflow_name.strip() or f"page_{template}_{title}"[:48]

        def fetch_fn():
            return {
                "items": items,
                "summary": summary or "",
            }

        wf = WorkflowManager().start_workflow(
            name=name,
            refresh_seconds=max(1, int(refresh_seconds)) if refresh_seconds else 3600,
            fetch_fn=fetch_fn,
            html_template=html,
        )

        return (
            f"页面已生成：{title}\n"
            f"URL: http://127.0.0.1:{wf.port}\n"
            f"Template: {template}\n"
            f"Items: {len(items)}"
        )
