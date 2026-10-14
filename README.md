# Automation Backup & Restore

Automatically back up and restore your custom Home Assistant automations.

## Features

- **Backup both YAML and UI automations**: Supports automations defined in `automations.yaml` and those created through the Home Assistant UI
- **Automatic restoration**: Automatically restores missing automations from your backup
- **Automatic backup of new automations**: Automatically adds new automations to your backup
- **Scheduled monitoring**: Runs on a configurable interval (default: 60 minutes)
- **Web interface**: Built-in web UI for manual backup/restore operations
- **Selective backup**: Choose to include YAML automations, UI automations, or both

## Installation

### Via HACS

1. Add this repository to HACS as a custom repository
2. Install the "Automation Backup & Restore" add-on
3. Configure the add-on options
4. Start the add-on

### Manual Installation

1. Copy this repository to your Home Assistant add-ons directory
2. Restart Home Assistant
3. Install the add-on from the add-on store
4. Configure and start

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `backup_path` | `/config/automation_backups.json` | Path to the backup file |
| `check_interval_minutes` | `60` | How often to check for changes (1-1440 minutes) |
| `auto_restore` | `true` | Automatically restore missing automations |
| `auto_backup_new` | `true` | Automatically backup new automations |
| `include_ui_automations` | `true` | Include UI-created automations in backup |
| `include_yaml_automations` | `true` | Include YAML automations in backup |

## Usage

### Automatic Mode

The add-on runs automatically on the configured interval, checking for:
- Missing automations in your backup (restores them if `auto_restore` is enabled)
- New automations not in your backup (adds them if `auto_backup_new` is enabled)

### Manual Mode

Access the web interface at `http://your-home-assistant:8099` to:
- View current backup status
- Create a new backup
- Restore from backup
- Reload automations

## Backup Format

The backup file is a JSON file containing:

```json
{
  "recorded_at": "2026-10-15T12:00:00Z",
  "yaml_automations": [
    {
      "id": "automation_id",
      "alias": "Automation Name",
      ...
    }
  ],
  "ui_automations": [
    {
      "id": "automation_id",
      "alias": "Automation Name",
      ...
    }
  ]
}
```

## Troubleshooting

### Automations not restoring

1. Check the add-on logs for errors
2. Ensure the backup file exists and is valid JSON
3. Verify that automation IDs in the backup are unique

### YAML automations not backing up

1. Ensure `automations.yaml` exists in your `/config` directory
2. Check that the file contains valid YAML
3. Verify `include_yaml_automations` is enabled in add-on options

## Development

This add-on is based on the Tuya Local Automated Backup & Restore add-on structure.

## License

MIT License
