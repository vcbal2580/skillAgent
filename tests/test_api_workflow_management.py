from fastapi.testclient import TestClient

import api.server as server


class _DummyWorkflow:
    def __init__(self):
        self.name = "demo_workflow"
        self.port = 9101
        self.running = True
        self.refresh_seconds = 60
        self.last_updated = "2026-04-03 10:00:00"
        self.created_at = "2026-04-03 09:00:00"
        self.refresh_calls = 0
        self.snapshot = {
            "name": self.name,
            "data": [{"title": "A"}],
            "summary": "ok",
            "last_updated": self.last_updated,
            "refresh_seconds": self.refresh_seconds,
        }

    def get_snapshot(self):
        return self.snapshot

    def _do_refresh(self):
        self.refresh_calls += 1
        self.last_updated = "2026-04-03 10:05:00"
        self.snapshot["last_updated"] = self.last_updated


class _DummyManager:
    def __init__(self, wf=None):
        self.wf = wf
        self.stop_calls = []

    def get_workflow(self, name):
        if self.wf and name == self.wf.name:
            return self.wf
        return None

    def stop_workflow(self, name):
        self.stop_calls.append(name)
        return bool(self.wf and name == self.wf.name)

    def list_workflows(self):
        if not self.wf:
            return []
        return [{
            "name": self.wf.name,
            "port": self.wf.port,
            "url": f"http://127.0.0.1:{self.wf.port}",
            "refresh_seconds": self.wf.refresh_seconds,
            "running": self.wf.running,
            "last_updated": self.wf.last_updated,
            "created_at": self.wf.created_at,
            "item_count": len(self.wf.snapshot["data"]),
            "summary_preview": self.wf.snapshot["summary"],
        }]


def test_get_workflow_overview(monkeypatch):
    manager = _DummyManager(_DummyWorkflow())
    monkeypatch.setattr("skills.workflow_service.WorkflowManager", lambda: manager)

    with TestClient(server.app) as client:
        resp = client.get("/workflows/demo_workflow")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["name"] == "demo_workflow"
    assert payload["status"]["item_count"] == 1


def test_list_workflows_includes_item_count(monkeypatch):
    manager = _DummyManager(_DummyWorkflow())
    monkeypatch.setattr("skills.workflow_service.WorkflowManager", lambda: manager)

    with TestClient(server.app) as client:
        resp = client.get("/workflows")

    assert resp.status_code == 200
    payload = resp.json()["workflows"]
    assert payload[0]["item_count"] == 1
    assert payload[0]["summary_preview"] == "ok"


def test_refresh_workflow_endpoint(monkeypatch):
    workflow = _DummyWorkflow()
    manager = _DummyManager(workflow)
    monkeypatch.setattr("skills.workflow_service.WorkflowManager", lambda: manager)

    with TestClient(server.app) as client:
        resp = client.post("/workflows/demo_workflow/refresh")

    assert resp.status_code == 200
    assert resp.json()["status"] == "refreshed"
    assert workflow.refresh_calls == 1


def test_export_workflow_json_endpoint(monkeypatch):
    manager = _DummyManager(_DummyWorkflow())
    monkeypatch.setattr("skills.workflow_service.WorkflowManager", lambda: manager)

    with TestClient(server.app) as client:
        resp = client.get("/workflows/demo_workflow/export/json")

    assert resp.status_code == 200
    assert resp.json()["snapshot"]["summary"] == "ok"


def test_stop_workflow_post_endpoint(monkeypatch):
    manager = _DummyManager(_DummyWorkflow())
    monkeypatch.setattr("skills.workflow_service.WorkflowManager", lambda: manager)

    with TestClient(server.app) as client:
        resp = client.post("/workflows/demo_workflow/stop")

    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"
    assert manager.stop_calls == ["demo_workflow"]


def test_workflow_management_404(monkeypatch):
    manager = _DummyManager(None)
    monkeypatch.setattr("skills.workflow_service.WorkflowManager", lambda: manager)

    with TestClient(server.app) as client:
        resp = client.get("/workflows/missing_workflow/status")

    assert resp.status_code == 404
