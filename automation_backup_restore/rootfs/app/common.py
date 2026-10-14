"""Shared helpers for the Automation Backup & Restore app."""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import requests

_LOGGER = logging.getLogger(__name__)

OPTIONS_PATH = Path("/data/options.json")
HA_CONFIG_PATH = Path("/config")
HA_AUTOMATIONS_YAML = HA_CONFIG_PATH / "automations.yaml"
HA_API_BASE = "http://supervisor/core/api"


def load_options() -> dict[str, Any]:
    """Load the app options written by the Supervisor."""
    if OPTIONS_PATH.exists():
        with OPTIONS_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def ha_token() -> str | None:
    """Return the Supervisor token that authorizes HA API calls."""
    return os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HASSIO_TOKEN")


def ha_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {ha_token() or ''}",
        "Content-Type": "application/json",
    }


def ha_request(method: str, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make an authenticated request to Home Assistant via the Supervisor proxy."""
    if not path.startswith("/"):
        path = "/" + path
    url = f"{HA_API_BASE}{path}"
    kwargs: dict[str, Any] = {"headers": ha_headers(), "timeout": 60}
    if data is not None:
        kwargs["json"] = data
    resp = requests.request(method, url, **kwargs)
    resp.raise_for_status()
    if resp.text:
        return resp.json()
    return {}


def get_yaml_automations() -> list[dict[str, Any]]:
    """Load automations from automations.yaml file."""
    if not HA_AUTOMATIONS_YAML.exists():
        _LOGGER.info("No automations.yaml file found")
        return []
    
    try:
        with HA_AUTOMATIONS_YAML.open("r", encoding="utf-8") as f:
            import yaml
            data = yaml.safe_load(f)
            if isinstance(data, list):
                return data
            _LOGGER.warning("automations.yaml is not a list, got %s", type(data))
            return []
    except Exception as exc:
        _LOGGER.error("Failed to load automations.yaml: %s", exc)
        return []


def get_ui_automations() -> list[dict[str, Any]]:
    """Get UI-created automations via Home Assistant API."""
    try:
        automations = ha_request("GET", "/config/automation/config")
        return automations if isinstance(automations, list) else []
    except Exception as exc:
        _LOGGER.warning("Failed to fetch UI automations: %s", exc)
        return []


def automation_key(automation: dict[str, Any]) -> str:
    """Return the unique key for an automation."""
    return automation.get("id") or automation.get("alias", "")


def build_backup_record(
    yaml_automations: list[dict[str, Any]],
    ui_automations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a backup record from current automations."""
    return {
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "yaml_automations": yaml_automations,
        "ui_automations": ui_automations,
    }


def get_backup_record(path: Path) -> dict[str, Any]:
    """Load the backup record, creating an empty one if necessary."""
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "recorded_at": None,
        "yaml_automations": [],
        "ui_automations": [],
    }


def save_backup_record(record: dict[str, Any], path: Path) -> None:
    """Write the backup record to disk."""
    record["recorded_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, default=str)
    _LOGGER.info(
        "Saved backup record with %s YAML automations and %s UI automations to %s",
        len(record.get("yaml_automations", [])),
        len(record.get("ui_automations", [])),
        path,
    )


def restore_yaml_automations(automations: list[dict[str, Any]]) -> list[str]:
    """Restore YAML automations to automations.yaml."""
    if not automations:
        return []
    
    try:
        import yaml
        
        # Read existing automations
        existing = []
        if HA_AUTOMATIONS_YAML.exists():
            with HA_AUTOMATIONS_YAML.open("r", encoding="utf-8") as f:
                existing = yaml.safe_load(f) or []
        
        # Merge automations (avoid duplicates by ID)
        existing_ids = {a.get("id") for a in existing if a.get("id")}
        restored = []
        
        for automation in automations:
            if automation.get("id") and automation["id"] not in existing_ids:
                existing.append(automation)
                existing_ids.add(automation["id"])
                restored.append(automation.get("alias", automation.get("id", "unknown")))
        
        # Write back
        with HA_AUTOMATIONS_YAML.open("w", encoding="utf-8") as f:
            yaml.dump(existing, f, default_flow_style=False, sort_keys=False)
        
        _LOGGER.info("Restored %s YAML automations to automations.yaml", len(restored))
        return restored
    except Exception as exc:
        _LOGGER.error("Failed to restore YAML automations: %s", exc)
        return []


def restore_ui_automation(automation: dict[str, Any]) -> str:
    """Restore a single UI automation via API."""
    try:
        automation_id = automation.get("id")
        if not automation_id:
            return f"Skipping automation without ID: {automation.get('alias', 'unknown')}"
        
        # Check if automation already exists
        try:
            existing = ha_request("GET", f"/config/automation/config/{automation_id}")
            if existing:
                # Update existing
                ha_request("POST", f"/config/automation/config/{automation_id}", automation)
                return f"Updated: {automation.get('alias', automation_id)}"
        except:
            # Doesn't exist, create new
            pass
        
        # Create new automation
        result = ha_request("POST", "/config/automation/config", automation)
        return f"Created: {automation.get('alias', automation_id)}"
    except Exception as exc:
        _LOGGER.error("Failed to restore UI automation %s: %s", automation.get("alias", "unknown"), exc)
        return f"ERROR: {automation.get('alias', 'unknown')} - {exc}"


def restore_ui_automations(automations: list[dict[str, Any]]) -> list[str]:
    """Restore UI automations via API."""
    results = []
    for automation in automations:
        result = restore_ui_automation(automation)
        results.append(result)
    return results


def reload_automations() -> bool:
    """Reload automations in Home Assistant."""
    try:
        ha_request("POST", "/config/automation/reload")
        _LOGGER.info("Automations reloaded successfully")
        return True
    except Exception as exc:
        _LOGGER.warning("Failed to reload automations: %s", exc)
        return False


def run_backup_restore(
    backup_path: Path,
    auto_restore: bool = True,
    auto_backup_new: bool = True,
    include_ui: bool = True,
    include_yaml: bool = True,
) -> dict[str, Any]:
    """Run one backup/restore cycle."""
    record = get_backup_record(backup_path)
    _LOGGER.info(
        "Loaded backup record with %s YAML automations and %s UI automations from %s",
        len(record.get("yaml_automations", [])),
        len(record.get("ui_automations", [])),
        backup_path,
    )

    # Get current automations
    current_yaml = get_yaml_automations() if include_yaml else []
    current_ui = get_ui_automations() if include_ui else []

    _LOGGER.info(
        "Found %s current YAML automations and %s current UI automations",
        len(current_yaml),
        len(current_ui),
    )

    results: list[str] = []
    errors: list[str] = []

    # Restore missing automations
    if auto_restore:
        if include_yaml and record.get("yaml_automations"):
            restored = restore_yaml_automations(record["yaml_automations"])
            results.extend([f"YAML: {r}" for r in restored])
        
        if include_ui and record.get("ui_automations"):
            restored = restore_ui_automations(record["ui_automations"])
            results.extend([f"UI: {r}" for r in restored])
            errors.extend([r for r in restored if r.startswith("ERROR")])

    # Back up new automations
    added: list[str] = []
    if auto_backup_new:
        # Compare and add new YAML automations
        if include_yaml:
            backup_ids = {a.get("id") for a in record.get("yaml_automations", []) if a.get("id")}
            new_yaml = [a for a in current_yaml if a.get("id") and a.get("id") not in backup_ids]
            if new_yaml:
                record.setdefault("yaml_automations", []).extend(new_yaml)
                added.extend([f"YAML: {a.get('alias', a.get('id', 'unknown'))}" for a in new_yaml])
        
        # Compare and add new UI automations
        if include_ui:
            backup_ids = {a.get("id") for a in record.get("ui_automations", []) if a.get("id")}
            new_ui = [a for a in current_ui if a.get("id") and a.get("id") not in backup_ids]
            if new_ui:
                record.setdefault("ui_automations", []).extend(new_ui)
                added.extend([f"UI: {a.get('alias', a.get('id', 'unknown'))}" for a in new_ui])
        
        if added:
            save_backup_record(record, backup_path)

    # Reload automations if any changes were made
    if results or added:
        reload_automations()

    for r in results:
        _LOGGER.info(r)
    for a in added:
        _LOGGER.info(a)

    status = {
        "backup_path": str(backup_path),
        "total_yaml_automations": len(record.get("yaml_automations", [])),
        "total_ui_automations": len(record.get("ui_automations", [])),
        "current_yaml_automations": len(current_yaml),
        "current_ui_automations": len(current_ui),
        "restored_or_checked": results,
        "added": added,
        "errors": errors,
        "success": not errors,
    }
    _LOGGER.info(
        "Run complete. Backup: %s YAML, %s UI. Errors: %s",
        status["total_yaml_automations"],
        status["total_ui_automations"],
        len(errors),
    )
    return status
