import json

from skills.comparison_workflow_skill import ComparisonWorkflowSkill


def test_comparison_workflow_success(monkeypatch):
    monkeypatch.setattr(
        "skills.comparison_workflow_skill.WebScrapeSkill.execute",
        lambda self, url, extract="text", selector="", max_items=20: f"CONTENT:{url}:{extract}",
    )
    monkeypatch.setattr(
        "skills.comparison_workflow_skill.PageGenerateSkill.execute",
        lambda self, **kwargs: "URL: http://127.0.0.1:9110",
    )

    skill = ComparisonWorkflowSkill()
    result = skill.execute(
        targets=json.dumps(["https://a.com", "https://b.com"]),
        focus="features",
        with_tables=True,
    )

    assert "对比流程已完成" in result
    assert "Targets: 2" in result
    assert "http://127.0.0.1:9110" in result


def test_comparison_workflow_requires_two_targets():
    skill = ComparisonWorkflowSkill()
    result = skill.execute(targets=json.dumps(["https://a.com"]))
    assert result == "targets must be a JSON list with at least 2 items"


def test_comparison_workflow_invalid_json():
    skill = ComparisonWorkflowSkill()
    result = skill.execute(targets="[bad")
    assert result.startswith("Invalid JSON in targets:")
