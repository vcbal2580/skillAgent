from fastapi.testclient import TestClient

import api.server as server


def test_api_lifespan_initializes_agent():
    server.agent = None

    with TestClient(server.app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
        assert server.agent is not None
