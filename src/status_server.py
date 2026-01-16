"""
Status Server - Simple HTTP API for querying worker and scheduler status.

Runs on port 5005 (configurable) and provides endpoints:
- GET /status - Full status of app, workers, and scheduler
- GET /workers - Worker status only
- GET /scheduler - Scheduler jobs only
- GET /health - Simple health check

This server runs in a background thread and is started automatically
when the app runs (if not disabled).
"""

import json
import logging
import os
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional

debug = logging.getLogger("scoreboard")

# Default port, can be overridden via STATUS_SERVER_PORT env var
DEFAULT_PORT = 5005

# Global reference to app data (set by start_status_server)
_app_data = None
_start_time = None


class StatusHandler(BaseHTTPRequestHandler):
    """HTTP request handler for status endpoints."""

    def log_message(self, format, *args):
        """Override to use our logger instead of stderr."""
        debug.debug(f"StatusServer: {args[0]}")

    def _send_json(self, data: dict, status: int = 200):
        """Send a JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, default=str).encode())

    def _send_html(self, html: str, status: int = 200):
        """Send an HTML response."""
        self.send_response(status)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(html.encode())

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/':
            self._handle_index()
        elif self.path == '/health':
            self._handle_health()
        elif self.path == '/status':
            self._handle_status()
        elif self.path == '/workers':
            self._handle_workers()
        elif self.path == '/scheduler':
            self._handle_scheduler()
        else:
            self._send_json({"error": "Not found", "endpoints": ["/health", "/status", "/workers", "/scheduler"]}, 404)

    def _handle_index(self):
        """Render the index page with links to all endpoints."""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>NHL LED Scoreboard - Status Server</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               max-width: 600px; margin: 50px auto; padding: 20px; background: #1a1a2e; color: #eee; }
        h1 { color: #00d4ff; }
        .endpoints { list-style: none; padding: 0; }
        .endpoints li { margin: 15px 0; }
        .endpoints a { color: #00d4ff; text-decoration: none; font-size: 1.2em;
                       padding: 10px 15px; display: inline-block; background: #16213e;
                       border-radius: 5px; transition: background 0.2s; }
        .endpoints a:hover { background: #0f3460; }
        .desc { color: #888; font-size: 0.9em; margin-left: 15px; }
        .footer { margin-top: 40px; color: #666; font-size: 0.8em; }
    </style>
</head>
<body>
    <h1>NHL LED Scoreboard</h1>
    <p>Status Server API</p>
    <ul class="endpoints">
        <li>
            <a href="/status">/status</a>
            <span class="desc">Full status (app, workers, scheduler)</span>
        </li>
        <li>
            <a href="/workers">/workers</a>
            <span class="desc">Worker status only</span>
        </li>
        <li>
            <a href="/scheduler">/scheduler</a>
            <span class="desc">Scheduler jobs only</span>
        </li>
        <li>
            <a href="/health">/health</a>
            <span class="desc">Simple health check</span>
        </li>
    </ul>
    <div class="footer">
        All endpoints return JSON. Use <code>curl</code> or your browser to query them.
    </div>
</body>
</html>"""
        self._send_html(html)

    def _handle_health(self):
        """Simple health check."""
        self._send_json({
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
        })

    def _handle_status(self):
        """Full status including app, workers, and scheduler."""
        if _app_data is None:
            self._send_json({"error": "App data not available"}, 503)
            return

        status = {
            "app": self._get_app_status(),
            "workers": self._get_workers_status(),
            "scheduler": self._get_scheduler_status(),
        }
        self._send_json(status)

    def _handle_workers(self):
        """Worker status only."""
        if _app_data is None:
            self._send_json({"error": "App data not available"}, 503)
            return

        self._send_json({"workers": self._get_workers_status()})

    def _handle_scheduler(self):
        """Scheduler jobs only."""
        if _app_data is None:
            self._send_json({"error": "App data not available"}, 503)
            return

        self._send_json({"scheduler": self._get_scheduler_status()})

    def _get_app_status(self) -> dict:
        """Get general app status."""
        uptime = None
        if _start_time:
            uptime = (datetime.now() - _start_time).total_seconds()

        return {
            "running": True,
            "pid": os.getpid(),
            "start_time": _start_time.isoformat() if _start_time else None,
            "uptime_seconds": round(uptime, 1) if uptime else None,
        }

    def _get_workers_status(self) -> dict:
        """Get status from all workers."""
        workers = {}

        # Get worker instances that have get_status method
        worker_sources = [
            ("live_game_worker", getattr(_app_data, 'live_game_worker', None)),
            ("games_worker", getattr(_app_data, 'games_worker', None)),
            ("standings_worker", getattr(_app_data, 'standings_worker', None)),
            ("stats_leaders_worker", getattr(_app_data, 'stats_leaders_worker', None)),
            ("team_schedule_worker", getattr(_app_data, 'team_schedule_worker', None)),
        ]

        for name, worker in worker_sources:
            if worker and hasattr(worker, 'get_status'):
                try:
                    workers[name] = worker.get_status()
                except Exception as e:
                    workers[name] = {"error": str(e)}

        return workers

    def _get_scheduler_status(self) -> dict:
        """Get scheduler job status."""
        scheduler_manager = getattr(_app_data, 'scheduler_manager', None)
        if not scheduler_manager:
            return {"error": "Scheduler manager not available"}

        try:
            jobs = scheduler_manager.list_jobs()
            return {
                "job_count": len(jobs),
                "jobs": [
                    {
                        "id": j.get("id"),
                        "name": j.get("name"),
                        "next_run_time": j.get("next_run_time").isoformat() if j.get("next_run_time") else None,
                        "trigger": str(j.get("trigger")) if j.get("trigger") else None,
                    }
                    for j in jobs
                ]
            }
        except Exception as e:
            return {"error": str(e)}


def start_status_server(data, port: Optional[int] = None) -> Optional[threading.Thread]:
    """
    Start the status server in a background thread.

    Args:
        data: The application data object (contains workers, scheduler, etc.)
        port: Port to listen on (default: 5005 or STATUS_SERVER_PORT env var)

    Returns:
        The server thread, or None if server couldn't start
    """
    global _app_data, _start_time

    _app_data = data
    _start_time = datetime.now()

    if port is None:
        port = int(os.environ.get('STATUS_SERVER_PORT', DEFAULT_PORT))

    def run_server():
        try:
            server = HTTPServer(('0.0.0.0', port), StatusHandler)
            debug.info(f"StatusServer: Started on port {port}")
            server.serve_forever()
        except Exception as e:
            debug.error(f"StatusServer: Failed to start: {e}")

    thread = threading.Thread(target=run_server, daemon=True, name="StatusServer")
    thread.start()
    return thread
