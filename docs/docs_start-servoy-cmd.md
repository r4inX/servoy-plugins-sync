# start-servoy.cmd – Reference

## Purpose

`start-servoy.cmd` is the **Windows wrapper** used to launch Servoy instead of
calling `servoy.exe` directly.

It ensures that `plugins_sync.py` runs automatically before startup — sync
errors **do not block the launch**, they are only shown as a warning.

---

## Prerequisites

- Windows
- Python 3 installed (accessible on PATH as `python` or `py`)
- Local config `%USERPROFILE%\.servoy-plugin-sync.json` exists
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
    ├─ 1. Read config  (%USERPROFILE%\.servoy-plugin-sync.json)
    │       └─ via PowerShell: extract servoy_home
    │
    ├─ 2. Find Python
    │       ├─ python  (on PATH?)
    │       ├─ py -3   (Python Launcher?)
    │       └─ neither → warning, skip sync
    │
    ├─ 3. Run plugins_sync.py
    │       ├─ Exit 0  → "Sync completed successfully"
    │       └─ Exit ≠ 0 → warning + exit code + log path shown
    │
    └─ 4. Launch Servoy
            ├─ servoy.exe found → start "" "<path>\developer\servoy.exe"
            └─ not found → error message + exit /b 1
```

---

## Example output (all OK)

```
============================================================
 Servoy Gold Plugin Sync – Wrapper
============================================================
 servoy_home : C:\servoys\2025.12.1.4123
 sync script : C:\dev\servoy-gold-sync\tools\plugins_sync.py

[INFO] Running plugin sync...
2026-03-02 08:00:01  INFO      ...
2026-03-02 08:00:02  INFO      Result: SUCCESS (0 warnings)
[INFO] Plugin sync completed successfully.

[INFO] Launching: C:\servoys\2025.12.1.4123\developer\servoy.exe
```

## Example output (sync errors, Servoy launches anyway)

```
[WARNING] Plugin sync finished with issues (exit code: 2).
          Some plugins may not be up to date.
          Check the log for details:
          C:\servoys\2025.12.1.4123\application_server\plugins\gold_plugins_sync.log
          Starting Servoy anyway...

[INFO] Launching: C:\servoys\2025.12.1.4123\developer\servoy.exe
```

## Example output (Python not found)

```
[WARNING] Python 3 was not found on PATH.
          Please install Python 3 or add it to PATH.
          Plugin sync will be SKIPPED.
          Starting Servoy anyway...

[INFO] Launching: C:\servoys\2025.12.1.4123\developer\servoy.exe
```

---

## Error scenarios

| Situation | Behaviour |
|---|---|
| Config file missing | Warning + sync skip + Servoy launches |
| `servoy_home` not in config | Warning + sync skip + Servoy launches |
| Python not on PATH | Warning + sync skip + Servoy launches |
| `plugins_sync.py` not found | Warning + sync skip + Servoy launches |
| Sync exit code 2 (warnings) | Warning with log path + Servoy launches |
| `servoy.exe` not found | Error message + `pause` + exit code 1 |

---

## One-time setup per developer

1. Create the config (if not done yet): `%USERPROFILE%\.servoy-plugin-sync.json`
   (or run `python plugins_sync.py --init-config`)
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

- Servoy is launched with `start "" "…\servoy.exe"` — the CMD window closes
  immediately afterwards. To read the sync output, run `start-servoy.cmd` from
  an already-open CMD window.
- The wrapper always reads `servoy_home` **fresh** from the config — no
  hardcoding required.
- After a Servoy version update: only change `servoy_version` (and optionally
  `servoy_home`) in the config.
