"""
Monitor workflow skill - create a local monitoring workflow with change detection.
"""

import json
from datetime import datetime
from skills.base import BaseSkill
from skills.page_generate_skill import PageGenerateSkill
from skills.web_scrape_skill import WebScrapeSkill
from skills.workflow_service import WorkflowManager


class MonitorWorkflowSkill(BaseSkill):
    name = "monitor_workflow"
    description = "Monitor a URL and build a local workflow page that records changes."
    parameters = {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target URL to monitor",
            },
            "interval_minutes": {
                "type": "integer",
                "default": 10,
                "description": "Refresh interval in minutes",
            },
            "condition": {
                "type": "string",
                "default": "any_change",
                "description": "any_change or keyword_appear:<keyword>",
            },
        },
        "required": ["target"],
    }

    def execute(self, target: str, interval_minutes: int = 10, condition: str = "any_change") -> str:
        scraper = WebScrapeSkill()
        page_skill = PageGenerateSkill()
        history: list[dict] = []
        last_text = {"value": ""}

        def _condition_hit(current: str, previous: str) -> bool:
            if condition.startswith("keyword_appear:"):
                kw = condition.split(":", 1)[1].strip()
                return bool(kw and kw in current and kw not in previous)
            return current != previous

        def fetch_fn():
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            text = scraper.execute(url=target, extract="text")
            changed = _condition_hit(text, last_text["value"])
            if changed:
                history.insert(0, {
                    "title": f"变化检测 @ {now}",
                    "content": text[:1500],
                    "time": now,
                    "target": target,
                    "condition": condition,
                })
            last_text["value"] = text

            if not history:
                history.append({
                    "title": f"监控已启动 @ {now}",
                    "content": f"目标 {target} 暂无触发变化。",
                    "time": now,
                    "target": target,
                    "condition": condition,
                })

            return {
                "items": history[:50],
                "summary": f"Target: {target} | Condition: {condition} | Events: {len(history)}",
            }

        data = json.dumps([], ensure_ascii=False)
        workflow_name = f"monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        page_result = page_skill.execute(
            title=f"Monitor - {target}",
            template="timeline",
            data=data,
            summary=f"Monitoring {target}",
            refresh_seconds=max(60, int(interval_minutes) * 60),
            workflow_name=workflow_name,
        )

        # Replace the generated workflow's fetch logic with monitoring closure.
        wf = WorkflowManager().get_workflow(workflow_name)
        if wf:
            wf.fetch_fn = fetch_fn
            wf._do_refresh()

        return (
            f"监控流程已启动\n"
            f"Target: {target}\n"
            f"Condition: {condition}\n"
            f"Interval: {interval_minutes} minutes\n"
            f"Page: {page_result}"
        )
