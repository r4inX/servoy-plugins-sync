# start-servoy.sh – Anleitung (macOS / Linux)

## Zweck

`start-servoy.sh` ist der **macOS- und Linux-Wrapper**, über den Servoy gestartet wird, anstatt die Anwendung direkt zu öffnen.

Er entspricht funktional `start-servoy.cmd` auf Windows: Er führt zuerst `plugins_sync.py` aus und startet Servoy danach – auch wenn der Sync Fehler produziert.

---

## Voraussetzungen

- Bash (macOS: vorinstalliert; Linux: vorinstalliert)
- Python 3 (`python3` oder `python` mit Version 3.x)
- Lokale Config `~/.servoy-plugin-sync.json` angelegt (siehe [docs_plugins_sync.md](docs_plugins_sync.md))
- Gold-Share gemountet (macOS: `/Volumes/...`, Linux: `/mnt/...`)
- `plugins_sync.py` liegt im selben Ordner wie `start-servoy.sh`

---

## Einmalige Einrichtung

```bash
chmod +x ~/dev/servoy-gold-sync/tools/start-servoy.sh
```

### Alias einrichten (optional, empfohlen)

**macOS / Linux – in `~/.zshrc` oder `~/.bashrc` eintragen:**

```bash
alias start-servoy="~/dev/servoy-gold-sync/tools/start-servoy.sh"
```

Danach: `source ~/.zshrc` (bzw. `.bashrc`), dann reicht `start-servoy` im Terminal.

### macOS – Launcher im Dock

1. `start-servoy.sh` in **Automator** einbinden: neues Dokument → "Shell-Skript ausführen"
2. Oder: `.command`-Datei erstellen, die das Script aufruft – `.command`-Dateien sind per Doppelklick ausführbar.

```bash
# ~/Desktop/Servoy.command
#!/bin/bash
~/dev/servoy-gold-sync/tools/start-servoy.sh
```

```bash
chmod +x ~/Desktop/Servoy.command
```

---

## Aufruf

```bash
./start-servoy.sh
```

Das Script hat keine Parameter – alles wird aus `~/.servoy-plugin-sync.json` gelesen.

---

## Ablauf

```
start-servoy.sh
    │
    ├─ 1. Python 3 suchen
    │       ├─ python3  (auf PATH?)
    │       ├─ python   (Version 3.x?)
    │       └─ keines → Warnung + Sync-Skip
    │
    ├─ 2. Config lesen
    │       └─ servoy_home via Python aus JSON extrahieren
    │
    ├─ 3. plugins_sync.py ausführen
    │       ├─ Exit 0  → "Sync completed successfully"
    │       └─ Exit ≠ 0 → Warnung mit Logpfad + weiter
    │
    └─ 4. Servoy starten
            ├─ macOS + Servoy.app vorhanden → open "…/Servoy.app"
            ├─ Binary vorhanden            → nohup + disown
            └─ nichts gefunden             → Fehlermeldung + exit 1
```

---

## Beispiel-Ausgabe (alles OK – macOS)

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

## Beispiel-Ausgabe (Sync-Fehler, Servoy startet trotzdem)

```
[WARNING] Plugin sync finished with issues (exit code: 2).
          Some plugins may not be up to date.
          Check the log: /Applications/Servoy/2025.12.1.4123/application_server/plugins/gold_plugins_sync.log
          Starting Servoy anyway...

[INFO] Launching (macOS): /Applications/Servoy/2025.12.1.4123/developer/Servoy.app
```

---

## Config-Pfade für macOS und Linux

### macOS (SMB Share gemountet)

```json
{
  "gold_root":      "/Volumes/SERVOY_GOLD/",
  "servoy_home":    "/Applications/Servoy/2025.12.1.4123/",
  "servoy_version": "2025.12.1.4123",
  "mode":           "quarantine"
}
```

> **Share mounten:** In Finder: `Cmd+K` → `smb://<server>/SERVOY_GOLD` → verbinden.  
> Oder dauerhaft via Systemeinstellungen → Benutzer & Gruppen → Anmeldeobjekte.

### Linux (SMB Share gemountet via `/mnt`)

```json
{
  "gold_root":      "/mnt/servoy_gold/",
  "servoy_home":    "/opt/servoy/2025.12.1.4123/",
  "servoy_version": "2025.12.1.4123",
  "mode":           "quarantine"
}
```

> **Share permanent mounten (Ubuntu/Debian):** `/etc/fstab` Eintrag:
> ```
> //server/SERVOY_GOLD  /mnt/servoy_gold  cifs  credentials=/etc/samba/servoy_creds,uid=1000,gid=1000  0 0
> ```

---

## Servoy-Executable – was wird gesucht?

Das Script prüft in dieser Reihenfolge:

| Plattform | Pfad | Start-Methode |
|---|---|---|
| macOS | `<servoy_home>/developer/Servoy.app` | `open "..."` |
| macOS/Linux | `<servoy_home>/developer/servoy` | `nohup ... &` (detached) |

Falls keines gefunden wird: Fehlermeldung mit den geprüften Pfaden, dann `exit 1`.

---

## Fehlerszenarien

| Situation | Verhalten |
|---|---|
| Python 3 nicht gefunden | Warnung + Sync-Skip + Servoy startet |
| Config fehlt | Warnung + Sync-Skip + kein Servoy-Start (kein `servoy_home` bekannt) |
| Share nicht gemountet | `plugins_sync.py` schlägt fehl (Exit 1) → Warnung + Servoy startet |
| Sync Exit 2 (Warnungen) | Warnung mit Logpfad + Servoy startet |
| Servoy-Binary nicht gefunden | Fehlermeldung + `exit 1` |
