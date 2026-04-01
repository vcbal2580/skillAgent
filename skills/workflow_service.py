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
        self._server: Optional[HTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self._refresh_thread: Optional[threading.Thread] = None
        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def start(self):
        """Start the HTTP server and background refresh thread."""
        self.running = True
        # Initial data fetch
        self._do_refresh()
        # Start refresh loop
        self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._refresh_thread.start()
        # Start HTTP server
        handler = self._make_handler()
        self._server = HTTPServer(("127.0.0.1", self.port), handler)
        self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._server_thread.start()

    def stop(self):
        """Stop the workflow service."""
        self.running = False
        if self._server:
            self._server.shutdown()

    def _do_refresh(self):
        """Fetch fresh data. fetch_fn returns {"items": [...], "summary": "..."}."""
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
        except Exception as e:
            # Keep old data, log error to data list
            self.data.insert(0, {
                "title": f"[刷新失败] {e}",
                "body": "",
                "time": datetime.now().strftime("%H:%M"),
                "url": "",
            })
            self.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _refresh_loop(self):
        """Background loop that refreshes data periodically."""
        while self.running:
            time.sleep(self.refresh_seconds)
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
        """Get next available port."""
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
        if name in self._workflows:
            self._workflows[name].stop()

        port = self._next_port()
        wf = WorkflowInstance(
            name=name,
            port=port,
            refresh_seconds=refresh_seconds,
            fetch_fn=fetch_fn,
            html_template=html_template,
        )
        wf.start()
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
            })
        return result

    def stop_all(self):
        """Stop all workflows."""
        for wf in self._workflows.values():
            wf.stop()
        self._workflows.clear()
