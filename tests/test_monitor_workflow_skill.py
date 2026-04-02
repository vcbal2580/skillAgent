from skills.monitor_workflow_skill import MonitorWorkflowSkill


class _DummyWf:
    def __init__(self):
        self.fetch_fn = None
        self.called = 0

    def _do_refresh(self):
        self.called += 1


class _DummyManager:
    def __init__(self, wf):
        self.wf = wf

    def get_workflow(self, name):
        return self.wf


def test_monitor_workflow_starts(monkeypatch):
    wf = _DummyWf()

    monkeypatch.setattr(
        "skills.monitor_workflow_skill.PageGenerateSkill.execute",
        lambda self, **kwargs: "URL: http://127.0.0.1:9108",
    )
    monkeypatch.setattr(
        "skills.monitor_workflow_skill.WorkflowManager",
        lambda: _DummyManager(wf),
    )

    skill = MonitorWorkflowSkill()
    result = skill.execute(target="https://example.com", interval_minutes=5)

    assert "监控流程已启动" in result
    assert "URL: http://127.0.0.1:9108" in result
    assert wf.called == 1


def test_monitor_keyword_condition(monkeypatch):
    wf = _DummyWf()

    monkeypatch.setattr(
        "skills.monitor_workflow_skill.PageGenerateSkill.execute",
        lambda self, **kwargs: "URL: http://127.0.0.1:9108",
    )
    monkeypatch.setattr(
        "skills.monitor_workflow_skill.WorkflowManager",
        lambda: _DummyManager(wf),
    )

    texts = ["hello", "hello NEW"]

    def _scrape(self, url, extract="text", selector="", max_items=20):
        return texts.pop(0) if texts else "hello NEW"

    monkeypatch.setattr("skills.monitor_workflow_skill.WebScrapeSkill.execute", _scrape)

    skill = MonitorWorkflowSkill()
    skill.execute(target="https://example.com", interval_minutes=1, condition="keyword_appear:NEW")

    payload1 = wf.fetch_fn()
    payload2 = wf.fetch_fn()

    assert payload1["summary"].startswith("Target:")
    assert "Events:" in payload2["summary"]
