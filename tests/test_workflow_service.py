from skills.workflow_service import WorkflowInstance, WorkflowManager


def test_workflow_instance_refresh_updates_snapshot():
    def _fetch():
        return {
            "items": [{"title": "A"}],
            "summary": "ok",
        }

    wf = WorkflowInstance(
        name="wf_demo",
        port=0,
        refresh_seconds=0,
        fetch_fn=_fetch,
        html_template="<html></html>",
    )

    wf._do_refresh()
    snap = wf.get_snapshot()

    assert snap["name"] == "wf_demo"
    assert snap["summary"] == "ok"
    assert len(snap["data"]) == 1
    assert snap["data"][0]["title"] == "A"


def test_workflow_instance_refresh_error_keeps_failure_marker():
    def _fetch():
        raise RuntimeError("boom")

    wf = WorkflowInstance(
        name="wf_demo",
        port=0,
        refresh_seconds=0,
        fetch_fn=_fetch,
        html_template="<html></html>",
    )

    wf._do_refresh()
    snap = wf.get_snapshot()

    assert len(snap["data"]) >= 1
    assert snap["data"][0]["title"].startswith("[刷新失败]")


def test_workflow_manager_stop_workflow_calls_stop():
    manager = WorkflowManager()

    class _DummyWorkflow:
        def __init__(self):
            self.stopped = False

        def stop(self):
            self.stopped = True

    dummy = _DummyWorkflow()
    manager._workflows["demo_stop"] = dummy

    ok = manager.stop_workflow("demo_stop")

    assert ok is True
    assert dummy.stopped is True
