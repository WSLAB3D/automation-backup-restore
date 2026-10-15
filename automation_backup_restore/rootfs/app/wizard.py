#!/usr/bin/env python3
"""Web wizard for the Automation Backup & Restore app."""

from __future__ import annotations

import json
import logging
import secrets
import sys
from pathlib import Path
from typing import Any

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
from flask import Flask, jsonify, render_template_string, request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
_LOGGER = logging.getLogger(__name__)

SECRET_PATH = Path("/data/secret.key")

if SECRET_PATH.exists():
    SECRET_KEY = SECRET_PATH.read_text(encoding="utf-8").strip()
else:
    SECRET_KEY = secrets.token_hex(32)
    SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
    SECRET_PATH.write_text(SECRET_KEY, encoding="utf-8")


class IngressMiddleware:
    """Make Flask URL generation work behind the Home Assistant Ingress proxy."""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        ingress_path = environ.get("HTTP_X_INGRESS_PATH", "")
        if ingress_path:
            environ["SCRIPT_NAME"] = ingress_path.rstrip("/")
        return self.app(environ, start_response)


app = Flask(__name__)
app.secret_key = SECRET_KEY
app.wsgi_app = IngressMiddleware(app.wsgi_app)


def get_backup_path() -> Path:
    options = load_options()
    return Path(options.get("backup_path", "/config/automation_backups.json"))


def get_status_context() -> dict[str, Any]:
    options = load_options()
    backup_path = get_backup_path()
    record = get_backup_record(backup_path)

    current_yaml = get_yaml_automations()
    current_ui = get_ui_automations()

    return {
        "backup_path": str(backup_path),
        "backup_exists": backup_path.exists(),
        "recorded_at": record.get("recorded_at"),
        "backup_yaml_count": len(record.get("yaml_automations", [])),
        "backup_ui_count": len(record.get("ui_automations", [])),
        "current_yaml_count": len(current_yaml),
        "current_ui_count": len(current_ui),
        "options": options,
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Automation Backup & Restore</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        h1 {
            margin-bottom: 20px;
            color: #4fc3f7;
        }
        .card {
            background: #2d2d2d;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .status-item {
            background: #3d3d3d;
            padding: 15px;
            border-radius: 6px;
        }
        .status-label {
            font-size: 12px;
            color: #888;
            margin-bottom: 5px;
        }
        .status-value {
            font-size: 24px;
            font-weight: bold;
            color: #4fc3f7;
        }
        .button-group {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        button {
            background: #4fc3f7;
            color: #1a1a1a;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            transition: background 0.2s;
        }
        button:hover {
            background: #29b6f6;
        }
        button:disabled {
            background: #555;
            cursor: not-allowed;
        }
        .message {
            margin-top: 15px;
            padding: 10px;
            border-radius: 6px;
            display: none;
        }
        .message.success {
            background: #2e7d32;
            color: white;
        }
        .message.error {
            background: #c62828;
            color: white;
        }
        .message.info {
            background: #0277bd;
            color: white;
        }
        .results {
            margin-top: 15px;
            max-height: 300px;
            overflow-y: auto;
            background: #3d3d3d;
            padding: 10px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 12px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Automation Backup & Restore</h1>

        <div class="card">
            <h2>Status</h2>
            <div class="status-grid">
                <div class="status-item">
                    <div class="status-label">Backup YAML Automations</div>
                    <div class="status-value" id="backup-yaml-count">{{ backup_yaml_count }}</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Backup UI Automations</div>
                    <div class="status-value" id="backup-ui-count">{{ backup_ui_count }}</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Current YAML Automations</div>
                    <div class="status-value" id="current-yaml-count">{{ current_yaml_count }}</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Current UI Automations</div>
                    <div class="status-value" id="current-ui-count">{{ current_ui_count }}</div>
                </div>
            </div>
            <div class="status-item" style="margin-bottom: 15px;">
                <div class="status-label">Last Backup</div>
                <div class="status-value" id="last-backup" style="font-size: 16px;">{{ recorded_at or 'No backup' }}</div>
            </div>
        </div>

        <div class="card">
            <h2>Actions</h2>
            <div class="button-group">
                <button onclick="createBackup()">💾 Create Backup</button>
                <button onclick="restoreBackup()">♻️ Restore Backup</button>
                <button onclick="reloadAutomations()">🔄 Reload Automations</button>
                <button onclick="refreshStatus()">📊 Refresh Status</button>
            </div>
            <div id="message" class="message"></div>
            <div id="results" class="results"></div>
        </div>
    </div>

    <script>
        async function refreshStatus() {
            try {
                const response = await fetch('{{ url_for("api_status") }}');
                const data = await response.json();

                document.getElementById('backup-yaml-count').textContent = data.backup_yaml_count;
                document.getElementById('backup-ui-count').textContent = data.backup_ui_count;
                document.getElementById('current-yaml-count').textContent = data.current_yaml_count;
                document.getElementById('current-ui-count').textContent = data.current_ui_count;
                document.getElementById('last-backup').textContent = data.recorded_at || 'No backup';
            } catch (error) {
                showMessage('Failed to fetch status', 'error');
            }
        }

        async function createBackup() {
            showMessage('Creating backup...', 'info');
            try {
                const response = await fetch('{{ url_for("api_backup") }}', { method: 'POST' });
                const data = await response.json();

                if (data.success) {
                    showMessage(data.message, 'success');
                    refreshStatus();
                } else {
                    showMessage('Backup failed', 'error');
                }
            } catch (error) {
                showMessage('Failed to create backup', 'error');
            }
        }

        async function restoreBackup() {
            showMessage('Restoring backup...', 'info');
            try {
                const response = await fetch('{{ url_for("api_restore") }}', { method: 'POST' });
                const data = await response.json();

                if (data.success) {
                    showMessage('Restore completed successfully', 'success');
                    showResults(data.results);
                    refreshStatus();
                } else {
                    showMessage('Restore completed with errors', 'error');
                    showResults(data.results);
                    showResults(data.errors);
                }
            } catch (error) {
                showMessage('Failed to restore backup', 'error');
            }
        }

        async function reloadAutomations() {
            showMessage('Reloading automations...', 'info');
            try {
                const response = await fetch('{{ url_for("api_reload") }}', { method: 'POST' });
                const data = await response.json();

                if (data.success) {
                    showMessage('Automations reloaded successfully', 'success');
                } else {
                    showMessage('Failed to reload automations', 'error');
                }
            } catch (error) {
                showMessage('Failed to reload automations', 'error');
            }
        }

        function showMessage(text, type) {
            const messageEl = document.getElementById('message');
            messageEl.textContent = text;
            messageEl.className = `message ${type}`;
            messageEl.style.display = 'block';

            setTimeout(() => {
                messageEl.style.display = 'none';
            }, 5000);
        }

        function showResults(items) {
            const resultsEl = document.getElementById('results');
            resultsEl.innerHTML = items.join('\\n');
            resultsEl.style.display = 'block';
        }

        // Refresh status on load
        refreshStatus();
    </script>
</body>
</html>"""


@app.route("/")
def index() -> Any:
    ctx = get_status_context()
    return render_template_string(HTML_TEMPLATE, **ctx)


@app.route("/api/status")
def api_status() -> Any:
    _LOGGER.info("GET /api/status called")
    ctx = get_status_context()
    _LOGGER.info("Status: %s", ctx)
    return jsonify(ctx)


@app.route("/api/backup", methods=["POST"])
def api_backup() -> Any:
    _LOGGER.info("POST /api/backup called")
    backup_path = get_backup_path()

    yaml_automations = get_yaml_automations()
    ui_automations = get_ui_automations()

    record = {
        "yaml_automations": yaml_automations,
        "ui_automations": ui_automations,
    }

    save_backup_record(record, backup_path)

    return jsonify({
        "success": True,
        "message": f"Backup created with {len(yaml_automations)} YAML and {len(ui_automations)} UI automations",
    })


@app.route("/api/restore", methods=["POST"])
def api_restore() -> Any:
    _LOGGER.info("POST /api/restore called")
    backup_path = get_backup_path()
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

    return jsonify({
        "success": not errors,
        "results": results,
        "errors": errors,
    })


@app.route("/api/reload", methods=["POST"])
def api_reload() -> Any:
    _LOGGER.info("POST /api/reload called")
    success = reload_automations()
    return jsonify({"success": success})


def main() -> None:
    _LOGGER.info("Starting Flask server on port 8099")
    app.run(host="0.0.0.0", port=8099, debug=False)


if __name__ == "__main__":
    main()
