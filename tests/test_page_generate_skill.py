from skills.page_generate_skill import PageGenerateSkill


class _DummyWorkflow:
    def __init__(self, port=9123):
        self.port = port


class _DummyManager:
    def __init__(self):
        self.calls = []

    def start_workflow(self, **kwargs):
        self.calls.append(kwargs)
        return _DummyWorkflow()


def test_page_generate_success(monkeypatch):
    manager = _DummyManager()

    def _manager_factory():
        return manager

    monkeypatch.setattr("skills.page_generate_skill.WorkflowManager", _manager_factory)

    skill = PageGenerateSkill()
    result = skill.execute(
        title="Demo",
        template="cards",
        data='[{"title":"A","body":"B"}]',
        summary="summary",
        refresh_seconds=10,
        workflow_name="demo_page",
    )

    assert "页面已生成：Demo" in result
    assert "http://127.0.0.1:9123" in result
    assert len(manager.calls) == 1
    assert manager.calls[0]["name"] == "demo_page"


def test_page_generate_invalid_json():
    skill = PageGenerateSkill()
    result = skill.execute(
        title="Bad",
        data="{bad json}",
    )

    assert result.startswith("Invalid JSON in data:")
