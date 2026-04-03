from fastapi.testclient import TestClient

import api.server as server


class _DummySkill:
    def __init__(self, metadata=None):
        self.last_run_metadata = metadata if metadata is not None else {"ok": True}


class _DummyRegistry:
    def __init__(self, skills):
        self.skills = skills

    def get(self, name):
        return self.skills.get(name)


class _DummyAgent:
    def __init__(self, skills):
        self.registry = _DummyRegistry(skills)


def test_workflow_metadata_endpoint_success():
    with TestClient(server.app) as client:
        server.agent = _DummyAgent({"research_workflow": _DummySkill({"query": "AI"})})
        resp = client.get("/workflows/meta/research_workflow")

    assert resp.status_code == 200
    assert resp.json()["metadata"]["query"] == "AI"


def test_workflow_metadata_endpoint_not_found():
    with TestClient(server.app) as client:
        server.agent = _DummyAgent({})
        resp = client.get("/workflows/meta/unknown_workflow")

    assert resp.status_code == 404
