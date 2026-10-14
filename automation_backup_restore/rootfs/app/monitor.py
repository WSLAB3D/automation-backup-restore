#!/usr/bin/env python3
"""Scheduled monitor for the Automation Backup & Restore app."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from common import load_options, run_backup_restore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
_LOGGER = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Back up and restore Home Assistant automations.")
    parser.add_argument("--run-once", action="store_true", help="Run one cycle and exit.")
    args = parser.parse_args()

    options = load_options()
    backup_path = Path(options.get("backup_path", "/config/automation_backups.json"))
    check_interval = max(1, int(options.get("check_interval_minutes", 60))) * 60
    auto_restore = bool(options.get("auto_restore", True))
    auto_backup_new = bool(options.get("auto_backup_new", True))
    include_ui = bool(options.get("include_ui_automations", True))
    include_yaml = bool(options.get("include_yaml_automations", True))

    if args.run_once:
        _LOGGER.info("Running one backup/restore cycle")
        status = run_backup_restore(backup_path, auto_restore, auto_backup_new, include_ui, include_yaml)
        print(json.dumps(status, indent=2, default=str))
        sys.exit(0 if status["success"] else 1)

    _LOGGER.info("Starting Automation monitor (interval: %s minutes)", check_interval // 60)
    while True:
        try:
            run_backup_restore(backup_path, auto_restore, auto_backup_new, include_ui, include_yaml)
        except Exception as exc:
            _LOGGER.exception("Backup/restore cycle failed: %s", exc)

        _LOGGER.info("Sleeping for %s minutes", check_interval // 60)
        time.sleep(check_interval)


if __name__ == "__main__":
    main()
