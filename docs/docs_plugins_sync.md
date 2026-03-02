# plugins_sync.py – Reference

## Purpose

`plugins_sync.py` is the **client script** that runs on every developer's machine
(typically automatically at Servoy start via `start-servoy.cmd` / `start-servoy.sh`).

It synchronises **managed plugins** from the central Gold Share into the local
Servoy installation:

- **Missing plugins** are copied from the share.
- **Outdated plugins** (hash mismatch) are replaced with the current version.
- **Plugins removed from the manifest** are moved to a quarantine folder (no hard delete).
- **Private / unmanaged plugins** (not in the manifest, never registered as managed) are **never touched**.

---

## Prerequisites

- Python 3.10 or newer
- No external packages required (standard library only)
- Gold Share must be accessible (e.g. `K:\` mapped on Windows)
- Local config file must exist (see below)

---

## Setting up the local config

The config file is created **once per developer machine**. It is never committed
to Git — every developer has their own local paths.

### Quick way – Setup Wizard (recommended)

The easiest way is the interactive wizard:

```cmd
python plugins_sync.py --init-config
```

The wizard:
1. Asks for a **profile name** — used as the config file name under `~/.servoy-sync/<name>.json`
2. Asks for a **display name** (shown in the profile picker)
3. Asks for `servoy_home` and checks that the path exists and looks like a Servoy installation
4. Asks for `gold_root` and checks that the share is accessible
5. Asks for `servoy_version` — suggests the automatically detected version
6. Asks for `mode` (default: `quarantine`) and optional `private_plugins` patterns
7. Shows a summary and asks for confirmation before writing

**Multiple profiles** (e.g. stable + nightly):

```cmd
python plugins_sync.py --init-config --profile stable
python plugins_sync.py --init-config --profile nightly
```

Each profile is saved as `%USERPROFILE%\.servoy-sync\<name>.json`. When you run
`--launch` (or `start-servoy.cmd`) and multiple profiles exist, an arrow-key
picker is shown so you choose which Servoy to start.

Afterwards run a status check to verify the setup:

```cmd
python plugins_sync.py --status
```

### Manual – copy the example file

Use [`docs/example.servoy-plugin-sync.json`](example.servoy-plugin-sync.json) as a template:

```cmd
copy "%~dp0..\docs\example.servoy-plugin-sync.json" "%USERPROFILE%\.servoy-plugin-sync.json"
```

Or create the file from scratch:

```cmd
notepad "%USERPROFILE%\.servoy-plugin-sync.json"
```

### Manual – fill in your paths

File contents (template):

```json
{
  "gold_root":      "K:\\SERVOY_GOLD\\",
  "servoy_home":    "C:\\servoys\\2025.12.1.4123\\",
  "servoy_version": "2025.12.1.4123",
  "mode":           "quarantine"
}
```

### Config fields – what does each developer need to set?

| Field | Required | What to enter |
|---|---|---|
| `display_name` | No | Human-readable label shown in the profile picker (e.g. `"Stable 2025.12"`). Falls back to the profile filename if omitted. |
| `gold_root` | Yes | Path to the mapped Gold Share. Typically `K:\\SERVOY_GOLD\\` for all Windows developers — only change if your drive letter differs. |
| `servoy_home` | **Yes, individual** | Your local Servoy installation directory. Must contain `developer\` and `application_server\`. Examples: `C:\\servoys\\2025.12.1.4123\\` or `C:\\Program Files\\Servoy\\`. |
| `servoy_version` | Yes | Must match exactly the folder name on the share (`servoy-<version>`). Update this when upgrading Servoy. |
| `mode` | No | `quarantine` (default, recommended) — removed managed plugins are moved, not deleted. |
| `private_plugins` | No | List of fnmatch patterns for plugins to **never** touch, even if orphaned. E.g. `["hvo-pdf.jar", "drafts/*"]`. |

> **Tip – finding servoy_home:** Open Windows Explorer and navigate to your Servoy
> installation. The folder you want contains two sub-folders: `developer` and
> `application_server`. Enter the full path to that folder as `servoy_home`,
> using double backslashes and a trailing `\\`.

### Examples (different developer setups)

**Developer 1 – default path:**
```json
{
  "display_name":   "Stable 2025.12",
  "gold_root":      "K:\\SERVOY_GOLD\\",
  "servoy_home":    "C:\\servoys\\2025.12.1.4123\\",
  "servoy_version": "2025.12.1.4123",
  "mode":           "quarantine",
  "private_plugins": []
}
```

**Developer 2 – Servoy under Program Files:**
```json
{
  "display_name":   "Stable 2025.12",
  "gold_root":      "K:\\SERVOY_GOLD\\",
  "servoy_home":    "C:\\Program Files\\Servoy\\2025.12.1.4123\\",
  "servoy_version": "2025.12.1.4123",
  "mode":           "quarantine",
  "private_plugins": []
}
```

**Developer 3 – multiple profiles (stable + nightly):**

Profile `~/.servoy-sync/stable.json`:
```json
{
  "display_name":   "Stable 2025.12",
  "gold_root":      "K:\\SERVOY_GOLD\\",
  "servoy_home":    "C:\\servoys\\2025.12.1.4123\\",
  "servoy_version": "2025.12.1.4123",
  "mode":           "quarantine",
  "private_plugins": []
}
```

Profile `~/.servoy-sync/nightly.json`:
```json
{
  "display_name":   "Nightly 2026.03",
  "gold_root":      "K:\\SERVOY_GOLD\\",
  "servoy_home":    "C:\\servoys\\2026.03.0.5000\\",
  "servoy_version": "2026.03.0.5000",
  "mode":           "quarantine",
  "private_plugins": ["hvo-pdf.jar"]
}
```

### After a Servoy version update

Only `servoy_version` (and optionally `servoy_home`) needs to change:

```json
{
  "gold_root":      "K:\\SERVOY_GOLD\\",
  "servoy_home":    "C:\\servoys\\2026.3.0.5000\\",
  "servoy_version": "2026.3.0.5000",
  "mode":           "quarantine"
}
```

---

## Usage

```
python plugins_sync.py [--config <path>] [--profile <name>] [--dry-run] [--verbose]
                       [--status] [--launch] [--init-config]
```

### Parameters

| Parameter | Description |
|---|---|
| `--init-config` | Interactive setup wizard: prompts for all config fields, validates input, and writes the config file |
| `--config <path>` | Explicit path to a config file |
| `--profile <name>` | Short form: loads `%USERPROFILE%\.servoy-sync\<name>.json` |
| `--launch` | Auto-discover profile (picker if multiple), sync, then launch Servoy. Used by `start-servoy.cmd` / `.sh`. |
| `--dry-run` | Show what would be done without making any changes |
| `--verbose` | Print DEBUG-level messages (e.g. which files are already up to date) |
| `--status` | Show current plugin state (OK / MISSING / OUTDATED) without changes. Exit 0 = all current, exit 2 = issues found. |

---

## Examples

### First-time setup with the wizard

```cmd
python plugins_sync.py --init-config
```

The wizard asks for **profile name** and **display name** first, then
`servoy_home`, `gold_root`, `servoy_version`, `mode`, and optional
`private_plugins` patterns.

Example session:

```
============================================================
 Servoy Gold Plugin Sync – Config Setup Wizard
============================================================

------------------------------------------------------------
 Step 1/6 – Profile name
------------------------------------------------------------
  Profile name [default]: stable
  ✓  Will save to: C:\Users\max\.servoy-sync\stable.json

------------------------------------------------------------
 Step 2/6 – Display name
------------------------------------------------------------
  Display name [stable]: Stable 2025.12

------------------------------------------------------------
 Step 3/6 – Servoy installation folder (servoy_home)
------------------------------------------------------------
  servoy_home: C:\servoys\2025.12.1.4123
  ✓  Detected installed version: 2025.12.1.4123

------------------------------------------------------------
 Step 4/6 – Gold Share root folder (gold_root)
------------------------------------------------------------
  gold_root: K:\SERVOY_GOLD
  ✓  'plugins' sub-folder found on share.

------------------------------------------------------------
 Step 5/6 – Servoy version (servoy_version)
------------------------------------------------------------
  servoy_version [2025.12.1.4123]:
  ✓  manifest.json found on share – version matches the Gold Share.

------------------------------------------------------------
 Step 6/6 – Mode & private plugins
------------------------------------------------------------
  mode [quarantine]:
  private_plugins (comma-separated fnmatch patterns, blank = none):

------------------------------------------------------------
 Summary – config to be written:
------------------------------------------------------------
{
  "display_name": "Stable 2025.12",
  "gold_root": "K:\\SERVOY_GOLD",
  "servoy_home": "C:\\servoys\\2025.12.1.4123",
  "servoy_version": "2025.12.1.4123",
  "mode": "quarantine",
  "private_plugins": []
}
  Target: C:\Users\max\.servoy-sync\stable.json

  Write this config? [Y/n]: Y
  ✓  Config written to: C:\Users\max\.servoy-sync\stable.json
  Run 'python plugins_sync.py --status' to verify the setup.
```

To create additional profiles:

```cmd
python plugins_sync.py --init-config --profile nightly
```

### Normal sync (default config)

```cmd
python plugins_sync.py
```

Expected output (example):

```
2026-03-02 08:00:01  INFO      Config:          C:\Users\max\.servoy-plugin-sync.json
2026-03-02 08:00:01  INFO      Gold manifest:   K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\manifest.json
2026-03-02 08:00:01  INFO      Gold files dir:  K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\files
2026-03-02 08:00:01  INFO      Local plugins:   C:\servoys\2025.12.1.4123\application_server\plugins
...
2026-03-02 08:00:01  INFO      === Phase 1: Install / Update managed plugins ===
2026-03-02 08:00:02  INFO        Installed: myplugin.jar
2026-03-02 08:00:02  INFO        Updated:   subfolder/another.jar
2026-03-02 08:00:02  INFO      === Phase 2: Quarantine removed managed plugins ===
2026-03-02 08:00:02  INFO        Nothing to quarantine.
2026-03-02 08:00:02  INFO      Result: SUCCESS (0 warnings)
```

### Dry-run (show only, no changes)

```cmd
python plugins_sync.py --dry-run --verbose
```

Useful to preview what would happen before running the real sync.

### Use an alternative config

```cmd
python plugins_sync.py --config "D:\team\my-sync-config.json"
```

### Show the status report (no sync)

```cmd
python plugins_sync.py --status
```

Example output:

```
================================================================
 Servoy Gold Plugin Sync – Status Report
================================================================

  Config version (servoy_version): 2025.12.1.4123
  Installed version (detected):    2025.12.1.4123  [✓]
  Manifest version:                2025.12.1.4123  [✓]
  Manifest generated:              2026-03-02

  --------------------------------------------------------------
  PATH                                       STATUS
  --------------------------------------------------------------
  myplugin.jar                               OK
  subfolder/another.jar                      OUTDATED (size …)
  newplugin.jar                              MISSING  → will be installed on next sync

  Summary: 2 ISSUE(S) FOUND
```

The **STATUS** column shows:

| Value | Meaning |
|---|---|
| `OK` | SHA-256 and file size match |
| `MISSING` | File is absent locally — will be installed on next sync |
| `OUTDATED` | Size or hash differs — will be updated on next sync |

The report also shows plugins that would be **quarantined** on the next sync and
lists **private plugins** (never touched).

---

## Version validation

The script automatically detects the installed Servoy version and cross-checks
three sources:

| Source | Where it comes from |
|---|---|
| **Config `servoy_version`** | `~/.servoy-plugin-sync.json` of the developer |
| **Manifest `servoy_version`** | Field in `manifest.json` on the Gold Share |
| **Installed version (auto-detect)** | Folder name `com.servoy.eclipse.feature_<VERSION>` under `<servoy_home>/developer/features/` |

### How the installed version is detected

The script scans `<servoy_home>/developer/features/` for a directory whose name
starts with `com.servoy.eclipse.feature_`. The suffix of that folder name is the
full version string (e.g. `2025.12.1.4123`) — the same information shown in
Eclipse under *Help → About Servoy Developer*.

Fallback: if that folder does not exist, `application_server/lib/version.txt` is
read. That file contains only the build number (`4123`), not a full version string.

> **Note:** The installation folder name (e.g. `C:\Servoys\servoy_4123`) may
> contain a version-like string, but the script ignores it. Only `servoy_home`
> in the config matters.

### What happens on a version mismatch?

- Only **warnings** are logged — the sync does not abort.
- Plugins are installed from the manifest regardless.
- The developer sees the warning and can react:
  - Update the config version (after a local Servoy upgrade)
  - Ask the Gold Maintainer (if the manifest seems outdated)

---

## How does the state mechanism work?

After every successful run the script saves a list of currently managed plugins to:

```
<servoy_home>\application_server\plugins\.gold_sync_state.json
```

Example content:

```json
{
  "updated_at": "2026-03-02T08:00:02",
  "managed_paths": [
    "myplugin.jar",
    "subfolder/another.jar"
  ]
}
```

**On the next run** the script compares:
- What was managed last time? → state file
- What is managed now? → current manifest

Files that were **previously** in the state but are **no longer** in the manifest
→ moved to quarantine.

Files that were **never** in the state (private plugins) → **never** touched.

---

## Quarantine

Plugins removed from the manifest are moved to:

```
<servoy_home>\application_server\plugins__quarantine\YYYY-MM-DD\
```

Example: `C:\servoys\2025.12.1.4123\application_server\plugins__quarantine\2026-03-02\myplugin.jar`

The date folder makes it easy to roll back if the manifest was wrong. Use
[`clean_quarantine.py`](docs_clean_quarantine.md) to remove old quarantine
folders after the retention period.

---

## Logging

The script writes simultaneously to **stdout** and a rotating log file:

```
<servoy_home>\application_server\plugins\gold_plugins_sync.log
```

The log file is capped at 2 MB with up to 3 backups (`*.log.1`, `*.log.2`,
`*.log.3`), keeping total disk usage under ~8 MB.

---

## Error handling & exit codes

| Exit code | Meaning |
|---|---|
| `0` | Fully successful (also `--status` with no issues) |
| `1` | Fatal error: config missing/invalid, manifest unreachable, local plugins directory not found |
| `2` | Completed with warnings (locked file); or `--status` found issues |

### Common errors

**Share not accessible:**
```
ERROR  Manifest not found: 'K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\manifest.json'
       Is the Gold Share accessible? Check that the network drive is mapped.
```
→ Exit code `1`. `start-servoy.cmd` starts Servoy anyway.

**File locked (Servoy still open):**
```
WARNING  Cannot install 'myplugin.jar': [WinError 32] The process cannot access the file ...
         Tip: Close Servoy and retry.
```
→ Exit code `2`. Servoy starts anyway. The sync will be retried on the next launch.

---

## Team workflow (normal operation)

1. Developer opens Servoy via `start-servoy.cmd` (not `servoy.exe` directly).
2. `start-servoy.cmd` automatically runs `python plugins_sync.py`.
3. Sync successful (exit 0) → Servoy starts normally.
4. Sync with warnings (exit 2) or fatal (exit 1) → brief message in CMD window, Servoy starts anyway.

---

## Files created / modified by the script

| File / Folder | Description |
|---|---|
| `<plugins>\.gold_sync_state.json` | State file (managed paths from the last run) |
| `<plugins>\gold_plugins_sync.log` | Log of all sync runs |
| `plugins__quarantine\YYYY-MM-DD\` | Quarantine folder for removed managed plugins |
| `<plugins>\<managed files>` | Installed / updated plugins |

The script **never** creates or modifies files that are not listed in the manifest
(and in the state) as managed.
