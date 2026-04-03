"""
Research workflow skill - end-to-end local research pipeline.
"""

import json
from datetime import datetime
from skills.base import BaseSkill
from skills.page_generate_skill import PageGenerateSkill
from skills.pdf_export_skill import PDFExportSkill
from skills.web_scrape_skill import WebScrapeSkill
from skills.workflow_pipeline import PipelineStep, WorkflowPipeline


class ResearchWorkflowSkill(BaseSkill):
    name = "research_workflow"
    description = "Run a research pipeline: search, scrape, summarize, generate page, and optional PDF."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Research topic or question",
            },
            "depth": {
                "type": "string",
                "enum": ["quick", "standard", "deep"],
                "default": "standard",
                "description": "How many sources to gather",
            },
            "with_pdf": {
                "type": "boolean",
                "default": False,
                "description": "Whether to export PDF after page generation",
            },
        },
        "required": ["query"],
    }

    def _max_results(self, depth: str) -> int:
        return {"quick": 3, "standard": 5, "deep": 8}.get(depth, 5)

    def __init__(self):
        self.last_run_metadata: dict = {}

    def _search(self, query: str, max_results: int) -> list[dict]:
        try:
            from ddgs import DDGS
        except Exception:
            return []

        try:
            with DDGS() as ddgs:
                rows = list(ddgs.text(query=query, max_results=max_results))
        except Exception:
            return []

        result = []
        for r in rows:
            result.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            })
        return [x for x in result if x.get("url")]

    def execute(self, query: str, depth: str = "standard", with_pdf: bool = False) -> str:
        max_results = self._max_results(depth)
        workflow_name = f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        scraper = WebScrapeSkill()
        page_skill = PageGenerateSkill()
        pdf_skill = PDFExportSkill()

        def step_search(ctx):
            return self._search(ctx["query"], ctx["max_results"])

        def step_scrape(ctx):
            items = []
            for row in ctx["search"]:
                text = scraper.execute(url=row["url"], extract="structured")
                items.append({
                    "title": row.get("title") or row["url"],
                    "content": text,
                    "url": row["url"],
                })
            return items

        def step_report(ctx):
            if not ctx["scrape"]:
                return [{
                    "title": "研究结果",
                    "content": f"未检索到可用来源：{ctx['query']}",
                }]
            top_titles = [x["title"] for x in ctx["search"][:3]]
            summary = "\n".join([f"- {t}" for t in top_titles])
            return [{
                "title": f"研究主题：{ctx['query']}",
                "content": (
                    f"共收集 {len(ctx['search'])} 个来源。\\n"
                    f"重点来源：\\n{summary}\\n\\n"
                    "详细抓取内容如下。"
                ),
            }] + ctx["scrape"]

        def step_page(ctx):
            data = json.dumps(ctx["report"], ensure_ascii=False)
            return page_skill.execute(
                title=f"Research - {ctx['query']}",
                template="report",
                data=data,
                summary=f"Research workflow for: {ctx['query']}",
                refresh_seconds=0,
                workflow_name=workflow_name,
            )

        def step_pdf(ctx):
            if not ctx["with_pdf"]:
                return "PDF skipped"
            return pdf_skill.execute(
                source=f"workflow:{workflow_name}",
                filename=f"research_{ctx['query']}",
            )

        pipeline = WorkflowPipeline(
            name="research_workflow",
            steps=[
                PipelineStep("search", step_search),
                PipelineStep("scrape", step_scrape, depends_on=["search"], run_in_parallel=True),
                PipelineStep("report", step_report, depends_on=["scrape", "search"]),
                PipelineStep("page", step_page, depends_on=["report"]),
                PipelineStep("pdf", step_pdf, depends_on=["page"]),
            ],
        )

        ctx = pipeline.run({
            "query": query,
            "max_results": max_results,
            "with_pdf": with_pdf,
        })

        self.last_run_metadata = {
            "query": query,
            "depth": depth,
            "max_results": max_results,
            "pipeline_meta": ctx.get("_pipeline_meta", {}),
            "page": ctx.get("page", ""),
            "pdf": ctx.get("pdf", ""),
        }

        return (
            f"研究流程已完成\n"
            f"Query: {query}\n"
            f"Depth: {depth} ({max_results} sources)\n"
            f"Page: {ctx['page']}\n"
            f"PDF: {ctx['pdf']}"
        )
