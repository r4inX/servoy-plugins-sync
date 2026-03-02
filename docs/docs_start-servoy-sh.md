# start-servoy.sh – Reference (macOS / Linux)

## Purpose

`start-servoy.sh` is the **macOS and Linux wrapper** used to launch Servoy
instead of opening the application directly.

It is functionally equivalent to `start-servoy.cmd` on Windows: it runs
`plugins_sync.py` first and then launches Servoy — even if the sync produces
errors.

---

## Prerequisites

- Bash (pre-installed on macOS and Linux)
- Python 3 (`python3` or `python` ≥ 3.x)
- Local config `~/.servoy-plugin-sync.json` exists
  (see [docs_plugins_sync.md](docs_plugins_sync.md))
- Gold Share mounted (macOS: `/Volumes/...`, Linux: `/mnt/...`)
- `plugins_sync.py` is in the same folder as `start-servoy.sh`

---

## One-time setup

```bash
chmod +x ~/dev/servoy-gold-sync/tools/start-servoy.sh
```

### Optional: set up an alias

**macOS / Linux — add to `~/.zshrc` or `~/.bashrc`:**

```bash
alias start-servoy="~/dev/servoy-gold-sync/tools/start-servoy.sh"
```

Then: `source ~/.zshrc` (or `.bashrc`), after which `start-servoy` in the
terminal is enough.

### macOS – Dock launcher

1. Use **Automator**: new document → "Run Shell Script", call `start-servoy.sh`.
2. Or create a `.command` file (double-clickable):

```bash
# ~/Desktop/Servoy.command
#!/bin/bash
~/dev/servoy-gold-sync/tools/start-servoy.sh
```

```bash
chmod +x ~/Desktop/Servoy.command
```

---

## Usage

```bash
./start-servoy.sh
```

No parameters — everything is read from `~/.servoy-plugin-sync.json`.

---

## Flow

```
start-servoy.sh
    │
    ├─ 1. Find Python 3
    │       ├─ python3  (on PATH?)
    │       ├─ python   (version 3.x?)
    │       └─ neither → warning + sync skip
    │
    ├─ 2. Read config
    │       └─ extract servoy_home via Python from JSON
    │
    ├─ 3. Run plugins_sync.py
    │       ├─ Exit 0  → "Sync completed successfully"
    │       └─ Exit ≠ 0 → warning with log path + continue
    │
    └─ 4. Launch Servoy
            ├─ macOS + Servoy.app present → open "…/Servoy.app"
            ├─ Binary present             → nohup … & disown
            └─ nothing found              → error message + exit 1
```

---

## Example output (all OK – macOS)

```
============================================================
 Servoy Gold Plugin Sync – Wrapper
============================================================
 servoy_home : /Applications/Servoy/2025.12.1.4123
 sync script : /Users/max/dev/servoy-gold-sync/tools/plugins_sync.py

[INFO] Running plugin sync...
2026-03-02 08:00:01  INFO      ...
2026-03-02 08:00:02  INFO      Result: SUCCESS (0 warnings)
[INFO] Plugin sync completed successfully.

[INFO] Launching (macOS): /Applications/Servoy/2025.12.1.4123/developer/Servoy.app
```

## Example output (sync errors, Servoy launches anyway)

```
[WARNING] Plugin sync finished with issues (exit code: 2).
          Some plugins may not be up to date.
          Check the log: /Applications/Servoy/2025.12.1.4123/application_server/plugins/gold_plugins_sync.log
          Starting Servoy anyway...

[INFO] Launching (macOS): /Applications/Servoy/2025.12.1.4123/developer/Servoy.app
```

---

## Config paths for macOS and Linux

### macOS (SMB share mounted)

```json
{
  "gold_root":      "/Volumes/SERVOY_GOLD/",
  "servoy_home":    "/Applications/Servoy/2025.12.1.4123/",
  "servoy_version": "2025.12.1.4123",
  "mode":           "quarantine"
}
```

> **Mount the share:** In Finder: `Cmd+K` → `smb://<server>/SERVOY_GOLD` →
> connect.  
> Or permanently via System Settings → Users & Groups → Login Items.

### Linux (SMB share mounted via `/mnt`)

```json
{
  "gold_root":      "/mnt/servoy_gold/",
  "servoy_home":    "/opt/servoy/2025.12.1.4123/",
  "servoy_version": "2025.12.1.4123",
  "mode":           "quarantine"
}
```

> **Permanent mount (Ubuntu/Debian):** add to `/etc/fstab`:
> ```
> //server/SERVOY_GOLD  /mnt/servoy_gold  cifs  credentials=/etc/samba/servoy_creds,uid=1000,gid=1000  0 0
> ```

---

## Servoy executable – what is searched?

The script checks in this order:

| Platform | Path | Launch method |
|---|---|---|
| macOS | `<servoy_home>/developer/Servoy.app` | `open "..."` |
| macOS / Linux | `<servoy_home>/developer/servoy` | `nohup ... &` (detached) |

If neither is found: error message with the checked paths, then `exit 1`.

---

## Error scenarios

| Situation | Behaviour |
|---|---|
| Python 3 not found | Warning + sync skip + Servoy launches |
| Config missing | Warning + sync skip + no Servoy launch (no `servoy_home` known) |
| Share not mounted | `plugins_sync.py` fails (exit 1) → warning + Servoy launches |
| Sync exit 2 (warnings) | Warning with log path + Servoy launches |
| Servoy binary not found | Error message + `exit 1` |
