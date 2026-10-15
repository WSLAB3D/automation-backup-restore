# Changelog

All notable changes to this project will be documented in this file.

## [0.0.4] - 2026-10-16

### Added
- Detailed HTTP request logging to debug API issues
- JavaScript console logging for debugging web interface

## [0.0.3] - 2026-10-16

### Added
- Error handling and logging to wizard API endpoints for better debugging
- Detailed logging for GET /api/status and POST /api/backup requests

### Fixed
- Improved error reporting in web interface

## [0.0.2] - 2026-10-16

### Fixed
- Added execute permissions to service run scripts (monitor/run and wizard/run)
- Fixed case sensitivity in repository.json (URL and maintainer)

## [0.0.1] - 2026-10-15

### Added
- Initial release
- Backup and restore YAML automations from automations.yaml
- Backup and restore UI automations via Home Assistant API
- Scheduled monitoring with configurable interval (default: 60 minutes)
- Automatic restoration of missing automations
- Automatic backup of new automations
- Web interface on port 8099
- Configurable options (backup path, interval, auto-restore, auto-backup, include YAML/UI)
