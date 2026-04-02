"""
Comparison workflow skill - compare multiple targets and render a local report page.
"""

import json
from datetime import datetime
from skills.base import BaseSkill
from skills.page_generate_skill import PageGenerateSkill
from skills.web_scrape_skill import WebScrapeSkill


class ComparisonWorkflowSkill(BaseSkill):
    name = "comparison_workflow"
    description = "Compare multiple URLs/topics, summarize differences, and generate a local comparison page."
    parameters = {
        "type": "object",
        "properties": {
            "targets": {
                "type": "string",
                "description": "JSON array of URLs or short targets to compare",
            },
            "focus": {
                "type": "string",
                "description": "Comparison focus, e.g. pricing/features/updates",
                "default": "overview",
            },
            "with_tables": {
                "type": "boolean",
                "description": "Whether to render in table template",
                "default": True,
            },
        },
        "required": ["targets"],
    }

    def execute(self, targets: str, focus: str = "overview", with_tables: bool = True) -> str:
        try:
            parsed = json.loads(targets)
        except json.JSONDecodeError as e:
            return f"Invalid JSON in targets: {e}"

        if not isinstance(parsed, list) or len(parsed) < 2:
            return "targets must be a JSON list with at least 2 items"

        items = [str(x).strip() for x in parsed if str(x).strip()]
        if len(items) < 2:
            return "targets must contain at least 2 non-empty items"

        scraper = WebScrapeSkill()
        rows = []
        for i, target in enumerate(items, start=1):
            # URL-like targets use structured scraping, others use plain text search summary style.
            mode = "structured" if target.startswith("http://") or target.startswith("https://") else "text"
            content = scraper.execute(url=target, extract=mode)
            rows.append({
                "target": target,
                "focus": focus,
                "summary": content[:1200],
                "rank": i,
            })

        template = "table" if with_tables else "cards"
        workflow_name = f"compare_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        page_result = PageGenerateSkill().execute(
            title=f"Comparison - {focus}",
            template=template,
            data=json.dumps(rows, ensure_ascii=False),
            summary=f"Compared {len(rows)} targets with focus: {focus}",
            refresh_seconds=0,
            workflow_name=workflow_name,
        )

        return (
            "对比流程已完成\n"
            f"Focus: {focus}\n"
            f"Targets: {len(rows)}\n"
            f"Page: {page_result}"
        )
