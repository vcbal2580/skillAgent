"""
Workflow service manager - manages background local web services spawned by skills.

Each workflow runs a lightweight HTTP server on a random port, serving
content that can refresh at a configurable interval.
"""

import json
import os
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Callable, Optional


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
        self._lock = threading.Lock()
        self._extra_get_routes: dict[str, Callable[[], tuple[int, str, str]]] = {}
        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def start(self):
        """Start the HTTP server and background refresh thread."""
        self.running = True
        self._do_refresh()

        if self.refresh_seconds > 0:
            self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
            self._refresh_thread.start()

        handler = self._make_handler()
        self._server = HTTPServer(("127.0.0.1", self.port), handler)
        self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._server_thread.start()

    def stop(self):
        """Stop the workflow service."""
        self.running = False
        if self._server:
            self._server.shutdown()

    def _apply_refresh_result(self, result):
        if isinstance(result, dict):
            self.data = result.get("items", [])
            self.summary = result.get("summary", "")
        else:
            self.data = result
            self.summary = ""

    def _do_refresh(self):
        """Fetch fresh data. fetch_fn returns {"items": [...], "summary": "..."}."""
        try:
            result = self.fetch_fn()
            with self._lock:
                self._apply_refresh_result(result)
            self.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            with self._lock:
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

    def get_snapshot(self) -> dict:
        """Return a thread-safe snapshot of workflow state."""
        with self._lock:
            return {
                "name": self.name,
                "data": list(self.data),
                "summary": self.summary,
                "last_updated": self.last_updated,
                "refresh_seconds": self.refresh_seconds,
            }

    def add_get_route(self, path: str, handler: Callable[[], tuple[int, str, str]]):
        """Register custom GET route.

        Handler must return (status_code, content_type, body_text).
        """
        if not path.startswith("/"):
            raise ValueError("Route path must start with '/'")
        self._extra_get_routes[path] = handler

    def export_pdf(self, output_path: str | None = None) -> str:
        """Export current HTML template to PDF and return output path."""
        try:
            from weasyprint import HTML
        except ImportError as e:
            raise RuntimeError("weasyprint is required for PDF export") from e

        if not output_path:
            export_dir = Path("data") / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = self.name.replace("/", "_").replace("\\", "_")
            output_path = str(export_dir / f"{safe_name}_{ts}.pdf")

        HTML(string=self.html_template, base_url=os.getcwd()).write_pdf(output_path)
        return output_path

    def _make_handler(self):
        workflow = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/api/data":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps(workflow.get_snapshot(), ensure_ascii=False).encode("utf-8"))
                    return

                if self.path == "/export/json":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps(workflow.get_snapshot(), ensure_ascii=False).encode("utf-8"))
                    return

                if self.path == "/api/refresh":
                    workflow._do_refresh()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    payload = {"ok": True, "last_updated": workflow.last_updated}
                    self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
                    return

                if self.path == "/export/pdf":
                    try:
                        output = workflow.export_pdf()
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.end_headers()
                        payload = {"ok": True, "pdf_path": output}
                        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
                    except Exception as e:
                        self.send_response(500)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.end_headers()
                        payload = {"ok": False, "error": str(e)}
                        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
                    return

                if self.path == "/api/status":
                    snap = workflow.get_snapshot()
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
                        "item_count": len(snap.get("data", [])),
                    }
                    self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
                    return

                if self.path in workflow._extra_get_routes:
                    try:
                        status_code, content_type, body_text = workflow._extra_get_routes[self.path]()
                        self.send_response(status_code)
                        self.send_header("Content-Type", content_type)
                        self.end_headers()
                        self.wfile.write(body_text.encode("utf-8"))
                    except Exception as e:
                        self.send_response(500)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.end_headers()
                        payload = {"ok": False, "error": str(e)}
                        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
                    return

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(workflow.html_template.encode("utf-8"))

            def log_message(self, format, *args):
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
        port = self._port_counter
        self._port_counter += 1
        return port

    def start_workflow(
        self,
        name: str,
        refresh_seconds: int,
        fetch_fn: Callable[[], list[dict]],
        html_template: str,
        preferred_port: int | None = None,
    ) -> WorkflowInstance:
        """Start workflow; stop old one if same name exists."""
        if name in self._workflows:
            self._workflows[name].stop()

        port = preferred_port if preferred_port is not None else self._next_port()
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
        wf = self._workflows.pop(name, None)
        if wf:
            wf.stop()
            return True
        return False

    def get_workflow(self, name: str) -> Optional[WorkflowInstance]:
        return self._workflows.get(name)

    def list_workflows(self) -> list[dict]:
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
        for wf in self._workflows.values():
            wf.stop()
        self._workflows.clear()
