#!/usr/bin/env python3
"""Web wizard for the Automation Backup & Restore app."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from common import (
    get_backup_record,
    get_ui_automations,
    get_yaml_automations,
    load_options,
    restore_ui_automations,
    restore_yaml_automations,
    reload_automations,
    run_backup_restore,
    save_backup_record,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
_LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Run the wizard web server."""
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    from socketserver import ThreadingMixIn
    import os

    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        """Handle requests in separate threads."""

    class APIHandler(SimpleHTTPRequestHandler):
        """Handle API requests."""

        def do_GET(self):
            """Handle GET requests."""
            try:
                if self.path == "/api/status":
                    self.send_json_response(self.get_status())
                elif self.path == "/api/options":
                    self.send_json_response(load_options())
                elif self.path == "/api/backup":
                    self.send_json_response(self.get_backup())
                else:
                    self.serve_static()
            except Exception as exc:
                _LOGGER.error("GET %s failed: %s", self.path, exc)
                self.send_error(500, str(exc))

        def do_POST(self):
            """Handle POST requests."""
            try:
                if self.path == "/api/backup":
                    self.send_json_response(self.create_backup())
                elif self.path == "/api/restore":
                    self.send_json_response(self.restore())
                elif self.path == "/api/reload":
                    self.send_json_response(self.reload())
                else:
                    self.send_error(404, "Not Found")
            except Exception as exc:
                _LOGGER.error("POST %s failed: %s", self.path, exc)
                self.send_error(500, str(exc))

        def send_json_response(self, data: dict) -> None:
            """Send a JSON response."""
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data, indent=2, default=str).encode())

        def serve_static(self):
            """Serve static files."""
            if self.path == "/":
                self.path = "/index.html"
            super().do_GET()

        def get_status(self) -> dict:
            """Get current status."""
            _LOGGER.info("GET /api/status called")
            options = load_options()
            backup_path = Path(options.get("backup_path", "/config/automation_backups.json"))
            record = get_backup_record(backup_path)

            current_yaml = get_yaml_automations()
            current_ui = get_ui_automations()

            status = {
                "backup_path": str(backup_path),
                "backup_exists": backup_path.exists(),
                "recorded_at": record.get("recorded_at"),
                "backup_yaml_count": len(record.get("yaml_automations", [])),
                "backup_ui_count": len(record.get("ui_automations", [])),
                "current_yaml_count": len(current_yaml),
                "current_ui_count": len(current_ui),
                "options": options,
            }
            _LOGGER.info("Status: %s", status)
            return status

        def get_backup(self) -> dict:
            """Get the backup record."""
            options = load_options()
            backup_path = Path(options.get("backup_path", "/config/automation_backups.json"))
            return get_backup_record(backup_path)

        def create_backup(self) -> dict:
            """Create a new backup."""
            _LOGGER.info("POST /api/backup called")
            options = load_options()
            backup_path = Path(options.get("backup_path", "/config/automation_backups.json"))

            yaml_automations = get_yaml_automations()
            ui_automations = get_ui_automations()

            record = {
                "yaml_automations": yaml_automations,
                "ui_automations": ui_automations,
            }

            save_backup_record(record, backup_path)

            return {
                "success": True,
                "message": f"Backup created with {len(yaml_automations)} YAML and {len(ui_automations)} UI automations",
            }

        def restore(self) -> dict:
            """Restore automations from backup."""
            options = load_options()
            backup_path = Path(options.get("backup_path", "/config/automation_backups.json"))
            record = get_backup_record(backup_path)
            
            results = []
            errors = []
            
            # Restore YAML automations
            if record.get("yaml_automations"):
                restored = restore_yaml_automations(record["yaml_automations"])
                results.extend([f"YAML: {r}" for r in restored])
            
            # Restore UI automations
            if record.get("ui_automations"):
                restored = restore_ui_automations(record["ui_automations"])
                results.extend([f"UI: {r}" for r in restored])
                errors.extend([r for r in restored if r.startswith("ERROR")])
            
            # Reload automations
            reload_automations()
            
            return {
                "success": not errors,
                "results": results,
                "errors": errors,
            }

        def reload(self) -> dict:
            """Reload automations."""
            success = reload_automations()
            return {"success": success}

    # Change to the directory containing static files
    os.chdir(Path(__file__).parent)
    
    server = ThreadedHTTPServer(("0.0.0.0", 8099), APIHandler)
    _LOGGER.info("Starting wizard server on port 8099")
    server.serve_forever()


if __name__ == "__main__":
    main()
