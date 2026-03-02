# start-servoy.cmd – Reference

## Purpose

`start-servoy.cmd` is the **Windows wrapper** used to launch Servoy instead of
calling `servoy.exe` directly.

It ensures that `plugins_sync.py` runs automatically before startup — sync
errors **do not block the launch**, they are only shown as a warning.

---

## Prerequisites

- Windows
- Python 3.10+ installed (accessible on PATH as `python` or `py`)
- At least one config profile created via `python plugins_sync.py --init-config`
  (see [docs_plugins_sync.md](docs_plugins_sync.md))
- `plugins_sync.py` is in the same folder as `start-servoy.cmd`

---

## Usage

Double-click `start-servoy.cmd` or run it from CMD / PowerShell:

```cmd
start-servoy.cmd
```

The script performs all steps automatically — no additional parameters required.

---

## Flow in detail

```
start-servoy.cmd
    │
    ├─ 1. Find Python  (python → py -3 → error)
    │
    └─ 2. Run plugins_sync.py --launch
            │
            ├─ Auto-discover profiles
            │       ├─ 1 profile  → use it directly
            │       ├─ several   → arrow-key picker shown
            │       └─ none      → error message + exit 1
            │
            ├─ Sync Gold plugins
            │       ├─ Share reachable  → install / update / quarantine
            │       └─ Share offline    → warning, sync skipped
            │
            └─ Launch Servoy (servoy.exe, cwd = servoy_home)
                    └─ Exit non-zero: [WARNING] in CMD window + pause
```

---

## Example output (single profile, all OK)

```
2026-03-02 08:00:01  INFO      Config: C:\Users\max\.servoy-sync\stable.json
2026-03-02 08:00:01  INFO      Gold manifest: K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\manifest.json
2026-03-02 08:00:02  INFO      === Phase 1: Install / Update managed plugins ===
2026-03-02 08:00:02  INFO        Nothing to install or update.
2026-03-02 08:00:02  INFO      === Phase 2: Quarantine removed managed plugins ===
2026-03-02 08:00:02  INFO        Nothing to quarantine.
2026-03-02 08:00:02  INFO      Result: SUCCESS (0 warnings)
2026-03-02 08:00:02  INFO      Launching Servoy: C:\servoys\2025.12.1.4123\developer\servoy.exe
```

## Example output (multiple profiles – picker shown)

```
  ────────────────────────────────────────────────────────────────
  Which Servoy would you like to start?
  Use ↑↓ arrows, Enter to confirm, Ctrl+C to abort.
  ────────────────────────────────────────────────────────────────
  ▶ stable    Stable 2025.12     C:\servoys\2025.12.1.4123\
    nightly   Nightly 2026.03    C:\servoys\2026.03.0.5000\
  ────────────────────────────────────────────────────────────────
```

## Example output (Gold Share offline, Servoy launches anyway)

```
2026-03-02 08:00:01  WARNING   Gold Share is unavailable – skipping sync and launching Servoy anyway.
2026-03-02 08:00:01  INFO      Launching Servoy: C:\servoys\2025.12.1.4123\developer\servoy.exe
```

---

## Error scenarios

| Situation | Behaviour |
|---|---|
| Python not on PATH | Error message + `pause` + exit code 1 |
| `plugins_sync.py` not found | Error message + `pause` + exit code 1 |
| No profiles configured | plugins_sync.py exits with code 1 → CMD shows `[WARNING]` + pause |
| Gold Share offline | Sync skipped with warning; Servoy still launches (exit code 2, no pause) |
| Sync exit code 2 (warnings) | CMD shows `[WARNING]` + pause with log hint |
| `servoy.exe` not found | plugins_sync.py logs error, exits 1 → CMD shows `[WARNING]` + pause |

---

## One-time setup per developer

1. Create your profile (if not done yet):
   ```cmd
   python plugins_sync.py --init-config
   ```
   For multiple Servoy installations, run `--init-config --profile <name>` for each.
2. Create a **shortcut** to `start-servoy.cmd` on the Desktop or Taskbar.
3. Replace all existing shortcuts to `servoy.exe`.

### Create a shortcut via PowerShell

```powershell
$ws  = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut("$env:USERPROFILE\Desktop\Servoy.lnk")
$lnk.TargetPath       = "C:\dev\servoy-gold-sync\tools\start-servoy.cmd"
$lnk.WorkingDirectory = "C:\dev\servoy-gold-sync\tools"
$lnk.Save()
```

---

## Notes

- The script delegates **all** logic (profile discovery, sync, launch) to
  `plugins_sync.py --launch` — no config reading happens in the CMD script itself.
- Servoy is started with `cwd` set to `servoy_home`, so runtime folders
  (`reports/`, `tmp/`, `www/`) are created inside the Servoy installation tree,
  not in the `tools/` directory.
- After a Servoy version update: update your profile via `--init-config --profile <name>`.
