from skills.research_workflow_skill import ResearchWorkflowSkill


class _DummyDDGS:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def text(self, query, max_results=5):
        return [
            {"title": "T1", "href": "https://a.com", "body": "B1"},
            {"title": "T2", "href": "https://b.com", "body": "B2"},
        ][:max_results]


def test_research_workflow_runs_without_pdf(monkeypatch):
    monkeypatch.setattr("ddgs.DDGS", _DummyDDGS)

    def _fake_scrape(self, url, extract="structured", selector="", max_items=20):
        return "SCRAPED"

    def _fake_page(self, **kwargs):
        return "URL: http://127.0.0.1:9105"

    monkeypatch.setattr("skills.research_workflow_skill.WebScrapeSkill.execute", _fake_scrape)
    monkeypatch.setattr("skills.research_workflow_skill.PageGenerateSkill.execute", _fake_page)

    skill = ResearchWorkflowSkill()
    result = skill.execute(query="AI chips", depth="quick", with_pdf=False)

    assert "研究流程已完成" in result
    assert "URL: http://127.0.0.1:9105" in result
    assert "PDF: PDF skipped" in result


def test_research_workflow_runs_with_pdf(monkeypatch):
    monkeypatch.setattr("ddgs.DDGS", _DummyDDGS)

    monkeypatch.setattr(
        "skills.research_workflow_skill.WebScrapeSkill.execute",
        lambda self, url, extract="structured", selector="", max_items=20: "SCRAPED",
    )
    monkeypatch.setattr(
        "skills.research_workflow_skill.PageGenerateSkill.execute",
        lambda self, **kwargs: "URL: http://127.0.0.1:9106",
    )
    monkeypatch.setattr(
        "skills.research_workflow_skill.PDFExportSkill.execute",
        lambda self, source, filename="": "PDF exported: data/exports/a.pdf",
    )

    skill = ResearchWorkflowSkill()
    result = skill.execute(query="AI", depth="standard", with_pdf=True)

    assert "PDF exported" in result
    assert "Depth: standard (5 sources)" in result
