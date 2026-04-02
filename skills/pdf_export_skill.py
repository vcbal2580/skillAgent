"""
PDF export skill - export workflow pages or URLs to PDF.
"""

from datetime import datetime
from pathlib import Path
from skills.base import BaseSkill
from skills.workflow_service import WorkflowManager


class PDFExportSkill(BaseSkill):
    name = "pdf_export"
    description = "Export a workflow page or URL as PDF and return saved file path."
    parameters = {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": "Source string: workflow:<name> or url:<http_url>",
            },
            "filename": {
                "type": "string",
                "description": "Optional output filename without path",
            },
        },
        "required": ["source"],
    }

    def execute(self, source: str, filename: str = "") -> str:
        export_dir = Path("data") / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        if filename:
            safe = filename.replace("/", "_").replace("\\", "_")
            if not safe.lower().endswith(".pdf"):
                safe += ".pdf"
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe = f"export_{ts}.pdf"

        out_path = export_dir / safe

        if source.startswith("workflow:"):
            wf_name = source.split(":", 1)[1].strip()
            wf = WorkflowManager().get_workflow(wf_name)
            if not wf:
                return f"Workflow not found: {wf_name}"
            path = wf.export_pdf(str(out_path))
            return f"PDF exported: {path}"

        if source.startswith("url:"):
            url = source.split(":", 1)[1].strip()
            try:
                from weasyprint import HTML
            except Exception as e:
                return f"weasyprint unavailable: {e}"
            HTML(url=url).write_pdf(str(out_path))
            return f"PDF exported: {out_path}"

        return "Invalid source. Use workflow:<name> or url:<http_url>"
