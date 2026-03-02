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
- Python 3.10+ (`python3` or `python` ≥ 3.x)
- At least one config profile created via `python3 plugins_sync.py --init-config`
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

No parameters — profile selection, sync, and Servoy launch are all handled
automatically by `plugins_sync.py --launch`.

---

## Flow

```
start-servoy.sh
    │
    ├─ 1. Find Python 3  (python3 → python → error)
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
            └─ Launch Servoy (binary / app, cwd = servoy_home)
```

---

## Example output (all OK – macOS)

```
2026-03-02 08:00:01  INFO      Config: /Users/max/.servoy-sync/stable.json
2026-03-02 08:00:01  INFO      Gold manifest: /Volumes/SERVOY_GOLD/plugins/servoy-2025.12.1.4123/manifest.json
2026-03-02 08:00:02  INFO      === Phase 1: Install / Update managed plugins ===
2026-03-02 08:00:02  INFO        Nothing to install or update.
2026-03-02 08:00:02  INFO      Result: SUCCESS (0 warnings)
2026-03-02 08:00:02  INFO      Launching: open -a '/Applications/Servoy/2025.12.1.4123/Servoy Developer.app'
```

## Example output (multiple profiles – picker shown)

```
  ────────────────────────────────────────────────────────────────
  Which Servoy would you like to start?
  Use ↑↓ arrows, Enter to confirm, Ctrl+C to abort.
  ────────────────────────────────────────────────────────────────
  ▶ stable    Stable 2025.12     /Applications/Servoy/2025.12.1.4123/
    nightly   Nightly 2026.03    /Applications/Servoy/2026.03.0.5000/
  ────────────────────────────────────────────────────────────────
```

## Example output (Gold Share offline, Servoy launches anyway)

```
2026-03-02 08:00:01  WARNING   Gold Share is unavailable – skipping sync and launching Servoy anyway.
2026-03-02 08:00:01  INFO      Launching: open -a '/Applications/Servoy/2025.12.1.4123/Servoy Developer.app'
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
| Python 3 not found | Error message + `exit 1` |
| `plugins_sync.py` not found | Error message + `exit 1` |
| No profiles configured | plugins_sync.py exits 1, shell exits 1 |
| Gold Share offline | Sync skipped with warning; Servoy still launches (exit 2) |
| Sync exit 2 (warnings) | Servoy still launches; exit code passed through |
| Servoy binary not found | plugins_sync.py logs error, exits 1 |
