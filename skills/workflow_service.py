"""
Workflow service manager - manages background local web services spawned by skills.

Each workflow runs a lightweight HTTP server on a random port, serving
dynamic content that refreshes at a configurable interval via a background thread.
"""

import threading
import time
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Callable, Optional
from datetime import datetime

# Max attempts to bind an HTTP port before giving up.
_PORT_BIND_ATTEMPTS = 50


class _ExclusiveHTTPServer(HTTPServer):
    """HTTPServer that refuses to share a port.

    ``HTTPServer`` defaults ``allow_reuse_address`` to 1 (SO_REUSEADDR). On
    Windows that lets a second server bind a port already in use instead of
    failing, which would silently break our port-collision retry. Disabling it
    makes ``bind`` raise ``OSError`` on a real collision so we can retry upward.
    """

    allow_reuse_address = False


class WorkflowInstance:
    """Represents a single running workflow service."""

    def __init__(
        self,
        name: str,
        port: int,
        refresh_seconds: int,
        fetch_fn: Callable[[], dict],
        html_template: str,
    ):
        self.name = name
        self.port = port
        self.refresh_seconds = refresh_seconds
        self.fetch_fn = fetch_fn
        self.html_template = html_template
        self.data: list[dict] = []
        self.summary: str = ""
        self.last_updated: str = ""
        self.running = False
        # status: "loading" (no successful fetch yet) | "ok" | "error"
        self.status = "loading"
        self.last_error = ""
        self.refresh_count = 0
        self._server: Optional[HTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self._refresh_thread: Optional[threading.Thread] = None
        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def start(self):
        """Start the HTTP server first, then fetch data in the background.

        The HTTP server is bound before any data fetching so the page (with its
        loading state) is reachable immediately and the caller is never blocked
        by a slow first fetch. ``self.port`` is updated to the port actually
        bound, in case the preferred port was taken.
        """
        self.running = True

        # Bind the HTTP server, retrying upward if the port is in use.
        handler = self._make_handler()
        bound = False
        last_err: Optional[Exception] = None
        for offset in range(_PORT_BIND_ATTEMPTS):
            candidate = self.port + offset
            try:
                self._server = _ExclusiveHTTPServer(("127.0.0.1", candidate), handler)
                self.port = candidate
                bound = True
                break
            except OSError as e:
                last_err = e
                continue
        if not bound:
            self.running = False
            raise OSError(
                f"无法为工作流 '{self.name}' 绑定端口（尝试 {self.port}~"
                f"{self.port + _PORT_BIND_ATTEMPTS - 1}）：{last_err}"
            )

        self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._server_thread.start()

        # Fetch data in the background so start() returns immediately. The first
        # refresh runs right away inside the loop (no initial sleep).
        self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._refresh_thread.start()

    def stop(self):
        """Stop the workflow service."""
        self.running = False
        if self._server:
            self._server.shutdown()
            self._server.server_close()

    def _do_refresh(self):
        """Fetch fresh data. fetch_fn returns {"items": [...], "summary": "..."}.

        On failure the previous (good) data and summary are preserved; the error
        is recorded in ``last_error`` / ``status`` instead of being injected into
        the news list.
        """
        try:
            result = self.fetch_fn()
            if isinstance(result, dict):
                self.data = result.get("items", [])
                self.summary = result.get("summary", "")
            else:
                # Backward compat: plain list
                self.data = result
                self.summary = ""
            self.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.last_error = ""
            self.status = "ok"
            self.refresh_count += 1
        except Exception as e:
            # Keep old data/summary intact; surface the error via status only.
            self.last_error = str(e)
            self.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.status = "error"

    def _refresh_loop(self):
        """Background loop: fetch immediately, then refresh on the interval.

        Sleeps in 1-second slices so a stopped workflow exits promptly instead
        of blocking for the whole refresh interval.
        """
        self._do_refresh()
        while self.running:
            for _ in range(self.refresh_seconds):
                if not self.running:
                    return
                time.sleep(1)
            if not self.running:
                break
            self._do_refresh()

    def _make_handler(self):
        """Create an HTTP request handler bound to this workflow instance."""
        workflow = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/api/data":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    payload = {
                        "name": workflow.name,
                        "data": workflow.data,
                        "summary": workflow.summary,
                        "last_updated": workflow.last_updated,
                        "refresh_seconds": workflow.refresh_seconds,
                        "status": workflow.status,
                        "last_error": workflow.last_error,
                        "refresh_count": workflow.refresh_count,
                    }
                    self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
                elif self.path == "/api/status":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    payload = {
                        "name": workflow.name,
                        "running": workflow.running,
                        "port": workflow.port,
                        "refresh_seconds": workflow.refresh_seconds,
                        "last_updated": workflow.last_updated,
                        "created_at": workflow.created_at,
                        "item_count": len(workflow.data),
                        "status": workflow.status,
                        "last_error": workflow.last_error,
                        "refresh_count": workflow.refresh_count,
                    }
                    self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
                else:
                    # Serve the HTML page
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(workflow.html_template.encode("utf-8"))

            def log_message(self, format, *args):
                # Suppress request logs
                pass

        return Handler


class WorkflowManager:
    """Singleton that manages all running workflow instances."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._workflows: dict[str, WorkflowInstance] = {}
                    cls._instance._port_counter = 9100
        return cls._instance

    def _next_port(self) -> int:
        """Get the next candidate port. Actual binding (with retry) happens in
        ``WorkflowInstance.start``; this only provides a starting point."""
        port = self._port_counter
        self._port_counter += 1
        return port

    def start_workflow(
        self,
        name: str,
        refresh_seconds: int,
        fetch_fn: Callable[[], list[dict]],
        html_template: str,
    ) -> WorkflowInstance:
        """Start a new workflow service. If one with the same name exists, stop it first."""
        with self._lock:
            if name in self._workflows:
                self._workflows[name].stop()
                del self._workflows[name]

            port = self._next_port()
            wf = WorkflowInstance(
                name=name,
                port=port,
                refresh_seconds=refresh_seconds,
                fetch_fn=fetch_fn,
                html_template=html_template,
            )
            wf.start()
            # Advance the counter past the port actually bound to avoid clashes.
            self._port_counter = max(self._port_counter, wf.port + 1)
            self._workflows[name] = wf
            return wf

    def stop_workflow(self, name: str) -> bool:
        """Stop a running workflow."""
        wf = self._workflows.pop(name, None)
        if wf:
            wf.stop()
            return True
        return False

    def get_workflow(self, name: str) -> Optional[WorkflowInstance]:
        return self._workflows.get(name)

    def list_workflows(self) -> list[dict]:
        """List all running workflows."""
        result = []
        for name, wf in self._workflows.items():
            result.append({
                "name": name,
                "port": wf.port,
                "url": f"http://127.0.0.1:{wf.port}",
                "refresh_seconds": wf.refresh_seconds,
                "running": wf.running,
                "last_updated": wf.last_updated,
                "created_at": wf.created_at,
                "status": wf.status,
                "last_error": wf.last_error,
                "item_count": len(wf.data),
            })
        return result

    def stop_all(self):
        """Stop all workflows."""
        for wf in self._workflows.values():
            wf.stop()
        self._workflows.clear()
