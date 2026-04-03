import json

from skills.comparison_workflow_skill import ComparisonWorkflowSkill
from skills.monitor_workflow_skill import MonitorWorkflowSkill
from skills.research_workflow_skill import ResearchWorkflowSkill


class _DummyWf:
    def __init__(self):
        self.fetch_fn = None

    def _do_refresh(self):
        return None


class _DummyManager:
    def __init__(self, wf=None):
        self.wf = wf or _DummyWf()

    def get_workflow(self, name):
        return self.wf


def test_research_workflow_records_metadata(monkeypatch):
    monkeypatch.setattr("ddgs.DDGS", lambda: None)
    monkeypatch.setattr(
        "skills.research_workflow_skill.ResearchWorkflowSkill._search",
        lambda self, query, max_results: [{"title": "T1", "url": "https://a.com", "snippet": "x"}],
    )
    monkeypatch.setattr(
        "skills.research_workflow_skill.WebScrapeSkill.execute",
        lambda self, url, extract="structured", selector="", max_items=20: "SCRAPED",
    )
    monkeypatch.setattr(
        "skills.research_workflow_skill.PageGenerateSkill.execute",
        lambda self, **kwargs: "URL: http://127.0.0.1:9105",
    )
    monkeypatch.setattr(
        "skills.research_workflow_skill.PDFExportSkill.execute",
        lambda self, source, filename="": "PDF skipped",
    )

    skill = ResearchWorkflowSkill()
    skill.execute(query="AI", depth="quick", with_pdf=False)

    assert skill.last_run_metadata["query"] == "AI"
    assert "search" in skill.last_run_metadata["pipeline_meta"]


def test_monitor_workflow_records_metadata(monkeypatch):
    monkeypatch.setattr(
        "skills.monitor_workflow_skill.PageGenerateSkill.execute",
        lambda self, **kwargs: "URL: http://127.0.0.1:9108",
    )
    monkeypatch.setattr("skills.monitor_workflow_skill.WorkflowManager", lambda: _DummyManager())

    skill = MonitorWorkflowSkill()
    skill.execute(target="https://example.com", interval_minutes=5, condition="any_change")

    assert skill.last_run_metadata["target"] == "https://example.com"
    assert skill.last_run_metadata["condition"] == "any_change"


def test_comparison_workflow_records_metadata(monkeypatch):
    monkeypatch.setattr(
        "skills.comparison_workflow_skill.WebScrapeSkill.execute",
        lambda self, url, extract="text", selector="", max_items=20: f"CONTENT:{url}",
    )
    monkeypatch.setattr(
        "skills.comparison_workflow_skill.PageGenerateSkill.execute",
        lambda self, **kwargs: "URL: http://127.0.0.1:9110",
    )

    skill = ComparisonWorkflowSkill()
    skill.execute(targets=json.dumps(["https://a.com", "https://b.com"]), focus="features")

    assert skill.last_run_metadata["focus"] == "features"
    assert len(skill.last_run_metadata["targets"]) == 2
