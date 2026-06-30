"""Tests for workflow_service robustness: non-blocking start, port retry, error handling."""

import socket
import time
import unittest
from urllib.request import urlopen

from skills.workflow_service import WorkflowInstance, WorkflowManager


HTML = "<html><body>test</body></html>"


def _wait_until(predicate, timeout=5.0, interval=0.05):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


class TestWorkflowInstance(unittest.TestCase):
    def setUp(self):
        self._instances = []

    def tearDown(self):
        for wf in self._instances:
            try:
                wf.stop()
            except Exception:
                pass

    def _track(self, wf):
        self._instances.append(wf)
        return wf

    def test_start_is_non_blocking_with_slow_fetch(self):
        """start() must return quickly even if the first fetch is slow."""
        fetch_started = threading_event()

        def slow_fetch():
            fetch_started.set()
            time.sleep(2)
            return {"items": [{"title": "late"}], "summary": "done"}

        wf = self._track(WorkflowInstance("slow", 9300, 60, slow_fetch, HTML))

        t0 = time.time()
        wf.start()
        elapsed = time.time() - t0

        # start() returned without waiting for the 2s fetch.
        self.assertLess(elapsed, 1.0)
        # HTTP server is already reachable while the fetch is in flight.
        self.assertTrue(_wait_until(lambda: fetch_started.is_set()))
        with urlopen(f"http://127.0.0.1:{wf.port}/", timeout=3) as resp:
            self.assertEqual(resp.status, 200)
        # Before the fetch completes, status is "loading".
        self.assertEqual(wf.status, "loading")
        # After it completes, data + summary populate and status flips to ok.
        self.assertTrue(_wait_until(lambda: wf.status == "ok", timeout=4))
        self.assertEqual(wf.summary, "done")
        self.assertEqual(len(wf.data), 1)

    def test_port_retry_when_busy(self):
        """If the preferred port is taken, start() binds the next free one."""
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        blocker.bind(("127.0.0.1", 9310))
        blocker.listen(1)
        try:
            wf = self._track(WorkflowInstance("busy", 9310, 60, lambda: {"items": [], "summary": ""}, HTML))
            wf.start()
            self.assertNotEqual(wf.port, 9310)
            self.assertGreater(wf.port, 9310)
        finally:
            blocker.close()

    def test_failed_refresh_preserves_previous_data(self):
        """A failing fetch keeps the last good data and records the error."""
        state = {"fail": False}

        def flaky_fetch():
            if state["fail"]:
                raise RuntimeError("boom")
            return {"items": [{"title": "good"}], "summary": "ok-summary"}

        wf = self._track(WorkflowInstance("flaky", 9320, 60, flaky_fetch, HTML))
        wf.start()
        self.assertTrue(_wait_until(lambda: wf.status == "ok", timeout=4))

        # Force a failing refresh and call directly.
        state["fail"] = True
        wf._do_refresh()

        self.assertEqual(wf.status, "error")
        self.assertIn("boom", wf.last_error)
        # Old data and summary are intact; no error row injected.
        self.assertEqual(len(wf.data), 1)
        self.assertEqual(wf.data[0]["title"], "good")
        self.assertEqual(wf.summary, "ok-summary")


class TestWorkflowManager(unittest.TestCase):
    def tearDown(self):
        WorkflowManager().stop_all()

    def test_restart_same_name_uses_new_port(self):
        manager = WorkflowManager()
        wf1 = manager.start_workflow("dup", 60, lambda: {"items": [], "summary": ""}, HTML)
        port1 = wf1.port
        wf2 = manager.start_workflow("dup", 60, lambda: {"items": [], "summary": ""}, HTML)
        self.assertNotEqual(port1, wf2.port)
        listed = manager.list_workflows()
        self.assertEqual(len(listed), 1)
        self.assertIn("status", listed[0])


def threading_event():
    import threading
    return threading.Event()


if __name__ == "__main__":
    unittest.main()
