from fastapi.testclient import TestClient

import api.server as server


class _DummyRegistry:
    def __init__(self):
        self.calls = []

    def execute(self, name, kwargs):
        self.calls.append((name, kwargs))
        return f"ok:{name}"


class _DummyAgent:
    def __init__(self):
        self.registry = _DummyRegistry()


def _client_with_dummy_agent():
    client = TestClient(server.app)
    dummy = _DummyAgent()
    server.agent = dummy
    return client, dummy


def test_research_workflow_endpoint_success():
    client, dummy = _client_with_dummy_agent()
    resp = client.post("/workflows/research", json={
        "query": "ai chips",
        "depth": "quick",
        "with_pdf": False,
    })

    assert resp.status_code == 200
    assert resp.json()["reply"] == "ok:research_workflow"
    assert dummy.registry.calls[0][0] == "research_workflow"
    assert dummy.registry.calls[0][1]["query"] == "ai chips"


def test_monitor_workflow_endpoint_success():
    client, dummy = _client_with_dummy_agent()
    resp = client.post("/workflows/monitor", json={
        "target": "https://example.com",
        "interval_minutes": 5,
        "condition": "any_change",
    })

    assert resp.status_code == 200
    assert resp.json()["reply"] == "ok:monitor_workflow"
    assert dummy.registry.calls[0][0] == "monitor_workflow"
    assert dummy.registry.calls[0][1]["interval_minutes"] == 5


def test_compare_workflow_endpoint_requires_two_targets():
    client, _ = _client_with_dummy_agent()
    resp = client.post("/workflows/compare", json={
        "targets": ["https://a.com"],
        "focus": "features",
        "with_tables": True,
    })

    assert resp.status_code == 400


def test_compare_workflow_endpoint_success():
    client, dummy = _client_with_dummy_agent()
    resp = client.post("/workflows/compare", json={
        "targets": ["https://a.com", "https://b.com"],
        "focus": "pricing",
        "with_tables": False,
    })

    assert resp.status_code == 200
    assert resp.json()["reply"] == "ok:comparison_workflow"
    assert dummy.registry.calls[0][0] == "comparison_workflow"
    assert '"https://a.com"' in dummy.registry.calls[0][1]["targets"]
