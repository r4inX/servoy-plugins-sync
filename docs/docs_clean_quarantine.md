# clean_quarantine.py – Reference

## Purpose

`clean_quarantine.py` removes old date-stamped quarantine folders under
`application_server/plugins__quarantine/`.

`plugins_sync.py` never permanently deletes removed managed plugins — they are
moved to the quarantine folder, organised by date (`YYYY-MM-DD`).
`clean_quarantine.py` is the counterpart that removes those folders after a
configurable retention period (default: **30 days**).

---

## Prerequisites

- Same config file as `plugins_sync.py`:  
  `%USERPROFILE%\.servoy-plugin-sync.json`
- Only the `servoy_home` field is required
- Python 3.10+ (no external packages)

---

## Usage

```
python clean_quarantine.py [--older-than-days N] [--dry-run] [--verbose] [--config <path>]
```

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `--older-than-days N` | `30` | Delete folders **older** than N days |
| `--dry-run` | — | Show what would be deleted without making any changes |
| `--verbose` | — | Print DEBUG-level messages |
| `--config <path>` | `~\.servoy-plugin-sync.json` | Alternative path to the config file |

---

## Examples

### Default run (30 days, real deletion)

```cmd
python clean_quarantine.py
```

Example output:

```
2026-05-20 09:00:00  INFO     Cleaning quarantine folders older than 30 days (before 2026-04-20).
2026-05-20 09:00:00  INFO     Quarantine directory: C:\Servoys\2025.12.1.4123\application_server\plugins__quarantine
2026-05-20 09:00:00  INFO       Deleted: 2026-03-10  (71 days old)
2026-05-20 09:00:00  INFO       Deleted: 2026-04-05  (45 days old)
2026-05-20 09:00:00  INFO     Done. 2 folder(s) deleted.
```

### 90-day threshold

```cmd
python clean_quarantine.py --older-than-days 90
```

### Dry-run (show only, nothing deleted)

```cmd
python clean_quarantine.py --dry-run
```

Example output:

```
2026-05-20 09:00:00  INFO     [DRY-RUN] Cleaning quarantine folders older than 30 days (before 2026-04-20).
2026-05-20 09:00:00  INFO     Quarantine directory: C:\Servoys\2025.12.1.4123\application_server\plugins__quarantine
2026-05-20 09:00:00  INFO       [DRY-RUN] Would delete: 2026-03-10  (71 days old)
2026-05-20 09:00:00  INFO     [DRY-RUN] 1 folder(s) would be deleted.
```

### As a Windows Scheduled Task

To run the cleanup weekly:

```
Action:  python C:\projects\svy-gold-script\tools\clean_quarantine.py
Trigger: Weekly, Monday 07:00
```

---

## Which folders are deleted?

Only sub-folders whose name matches the `YYYY-MM-DD` format **and** that are
older than the specified threshold are removed. All other contents of the
quarantine directory (e.g. manually created folders without a date name) are
ignored.

---

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success (including when nothing was deleted) |
| `1` | Fatal error (config missing, `servoy_home` invalid, …) |

---

## Note for Gold Maintainers

`clean_quarantine.py` is primarily a **developer tool** — each developer cleans
their own local quarantine. The Gold Share itself contains no quarantine folders.

Recommended retention period: **30 days** — enough time to roll back if a plugin
was accidentally removed from the manifest.
