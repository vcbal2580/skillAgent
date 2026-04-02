from skills.workflow_dashboard_skill import WorkflowDashboardSkill


class _DummyWf:
    def __init__(self, port=9000):
        self.port = port


class _DummyManager:
    def __init__(self):
        self.calls = []

    def start_workflow(self, **kwargs):
        self.calls.append(kwargs)
        return _DummyWf()

    def list_workflows(self):
        return []


def test_workflow_dashboard_starts_on_fixed_port(monkeypatch):
    manager = _DummyManager()

    def _manager_factory():
        return manager

    monkeypatch.setattr("skills.workflow_dashboard_skill.WorkflowManager", _manager_factory)

    skill = WorkflowDashboardSkill()
    result = skill.execute()

    assert "http://127.0.0.1:9000" in result
    assert len(manager.calls) == 1
    assert manager.calls[0]["preferred_port"] == 9000
