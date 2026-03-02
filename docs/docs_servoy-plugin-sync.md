# Servoy Gold Plugins – Team Sync

## Overview

| | |
|---|---|
| **Goal** | Uniform plugin state in `servoy/application_server/plugins` across all developers, without touching private / unreleased plugins of individual developers. |
| **Platform** | V1: Windows · V2: macOS / Linux (already implemented via `start-servoy.sh`) |
| **Servoy version** | 2025.12.1.4123 (example) |

---

## 1. Problem & Goal

### Problem

Every developer has different plugins locally in:

```
<SERVOY_HOME>\application_server\plugins
```

This leads to:
- "works on my machine" / "doesn't work on yours"
- hard-to-reproduce bugs
- tedious onboarding

### Goal

A central "Gold" plugin baseline lives on a share and is synchronised locally
and automatically:

- **Managed**: team plugins (from the manifest) are installed / updated / removed
- **Unmanaged**: private / unreleased plugins remain untouched
- Sync errors must **warn informatively** but **still launch Servoy**

---

## 2. Terminology

| Term | Meaning |
|---|---|
| **SERVOY_HOME** | Folder containing `developer/` and `application_server/`. E.g. `C:\servoys\2025.12.1.4123\` |
| **Gold Root** | Central share folder. E.g. `K:\SERVOY_GOLD\` |
| **Managed plugin** | Any file listed in `manifest.json` on the share |
| **Unmanaged / private plugin** | Any file in the local plugins folder that is not (and was never) in the manifest |
| **Gold Maintainer** | The team member responsible for updating the Gold Share |

---

## 3. Architecture

### 3.1 Source of Truth (Share)

The share contains one set of plugins + manifest per Servoy version:

```
K:\SERVOY_GOLD\
└── plugins\
    └── servoy-2025.12.1.4123\
        ├── manifest.json
        └── files\
            ├── myplugin.jar
            └── subfolder\
                └── another.jar
```

> **Note:** V1 uses a versioned folder structure so that updates remain
> controlled. A `current\` symlink can be added later.

### 3.2 Client (local)

- `plugins_sync.py` reads the config, manifest, and synchronises.
- Servoy is launched via a wrapper script (`start-servoy.cmd` on Windows,
  `start-servoy.sh` on macOS / Linux).

---

## 4. Sync rules

### 4.1 Managed vs Unmanaged

- **Managed plugins** = all files listed in `manifest.json`
- **Unmanaged plugins** = everything in the local plugins folder that is not
  in the manifest

### 4.2 What the sync does

For each managed plugin from the manifest:

| Local state | Action |
|---|---|
| Missing | Copy from share |
| Present, hash matches | Skip (already up to date) |
| Present, hash differs | Replace (atomic: temp copy → rename) |

For local plugins that were previously managed but are no longer in the manifest:
→ **move to quarantine** (never hard-delete)

### 4.3 Quarantine

Removed managed plugins are moved to:

```
<SERVOY_HOME>\application_server\plugins__quarantine\YYYY-MM-DD\
```

This allows rollback if the manifest was wrong. Old quarantine folders can be
cleaned up with `clean_quarantine.py`.

### 4.4 Private plugins

Private / unreleased plugins may exist locally and are **never** removed or
modified.

---

## 5. Manifest format

`manifest.json` contains:

| Field | Type | Description |
|---|---|---|
| `servoy_version` | string | Servoy version this manifest targets |
| `generated_at` | string (YYYY-MM-DD) | Generation date |
| `files` | array | One entry per plugin file |
| `files[].path` | string | Relative path from `files/`, forward slashes |
| `files[].sha256` | string | SHA-256 hex hash |
| `files[].size` | integer | File size in bytes |

Minimal example:

```json
{
  "servoy_version": "2025.12.1.4123",
  "generated_at": "2026-03-02",
  "files": [
    { "path": "myplugin.jar", "sha256": "…", "size": 12345 },
    { "path": "subfolder/another.jar", "sha256": "…", "size": 999 }
  ]
}
```

Identity check is done via `sha256`. `size` is used as a fast pre-check to
avoid unnecessary hashing.

---

## 6. Local config (per developer)

Because every developer installs Servoy in a different location, a local config
file is required per user. It is **never committed to Git**.

Default location:
- Windows: `%USERPROFILE%\.servoy-plugin-sync.json`
- macOS / Linux: `~/.servoy-plugin-sync.json`

Example:

```json
{
  "gold_root":      "K:\\SERVOY_GOLD\\",
  "servoy_home":    "C:\\servoys\\2025.12.1.4123\\",
  "servoy_version": "2025.12.1.4123",
  "mode":           "quarantine"
}
```

| Field | Description |
|---|---|
| `gold_root` | Path to the share |
| `servoy_home` | Local Servoy installation folder |
| `servoy_version` | Selects the manifest folder on the share (`servoy-<version>`) |
| `mode` | `quarantine` (default, safe) or `delete` (permanent) |

The fastest way to create this file is the interactive wizard:

```cmd
python plugins_sync.py --init-config
```

---

## 7. Why a wrapper instead of launching servoy.exe directly?

Eclipse / Servoy's `servoy.ini` / `eclipse.ini` is not designed to reliably run
external scripts at startup. A wrapper script is the clean solution:

1. Run `python plugins_sync.py`
2. On error: show warning
3. Always launch Servoy (`servoy.exe` / `Servoy.app`) regardless

---

## 8. Gold Share initialisation (one-time, Gold Maintainer)

1. Create the folder structure on the share:
   ```
   K:\SERVOY_GOLD\plugins\servoy-<VERSION>\files\
   ```
2. Copy all intended team plugins into `files\`.
3. Generate the manifest:
   ```cmd
   python build_manifest.py --files-dir "K:\...\files" --out "K:\...\manifest.json" --servoy-version "2025.12.1.4123"
   ```
4. Optional: create a `CHANGELOG.md` on the share for change tracking.

---

## 9. Rollout per developer

1. Create local config (`--init-config` or manually).
2. Use `start-servoy.cmd` (Windows) or `start-servoy.sh` (macOS / Linux)
   instead of launching Servoy directly.

---

## 10. Ongoing Gold Maintainer process

For every plugin change:

1. Update plugin files in `files\`.
2. Regenerate the manifest with `build_manifest.py`.
3. Optional: update `CHANGELOG.md` (what changed and why).
4. All developers receive the new state automatically on their next launch.

---

## 11. Error behaviour

| Error | Sync behaviour | Servoy |
|---|---|---|
| Share not accessible | Clear warning, exit code ≠ 0 | Launches anyway |
| File locked (Servoy open) | Warning, name the file, suggest "close Servoy and retry" | Launches anyway |
| Manifest parse error | Fatal error, exit code 1 | Launches anyway |

---

## 12. Future / V3 ideas

- Optional HTTP server instead of SMB (only the transport changes, sync logic stays the same)
- `current\` symlink on the share for the latest version
- Webhook notification when the Gold Maintainer publishes a new manifest
