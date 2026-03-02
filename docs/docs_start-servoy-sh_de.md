# start-servoy.sh – Anleitung (macOS / Linux)

## Zweck

`start-servoy.sh` ist der **macOS- und Linux-Wrapper**, über den Servoy gestartet wird, anstatt die Anwendung direkt zu öffnen.

Er entspricht funktional `start-servoy.cmd` auf Windows: Er führt zuerst `plugins_sync.py` aus und startet Servoy danach – auch wenn der Sync Fehler produziert.

---

## Voraussetzungen

- Bash (macOS: vorinstalliert; Linux: vorinstalliert)
- Python 3.10+ (`python3` oder `python` mit Version 3.x)
- Mind. ein Config-Profil angelegt via `python3 plugins_sync.py --init-config`
  (siehe [docs_plugins_sync.md](docs_plugins_sync.md))
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

Keine Parameter — Profilauswahl, Sync und Servoy-Start werden vollständig von
`plugins_sync.py --launch` übernommen.

---

## Ablauf

```
start-servoy.sh
    │
    ├─ 1. Python 3 suchen  (python3 → python → Fehler)
    │
    └─ 2. plugins_sync.py --launch aufrufen
            │
            ├─ Profile automatisch erkennen
            │       ├─ 1 Profil    → direkt verwenden
            │       ├─ mehrere    → Pfeil-Auswahl-Menü anzeigen
            │       └─ kein Profil → Fehlermeldung + Exit 1
            │
            ├─ Gold-Plugins synchronisieren
            │       ├─ Share erreichbar → installieren / aktualisieren / quarantänisieren
            │       └─ Share offline    → Warnung, Sync überspringen
            │
            └─ Servoy starten (Binary/App, cwd = developer/)
```

---

## Beispiel-Ausgabe (alles OK – macOS)

```
2026-03-02 08:00:01  INFO      Config: /Users/max/.servoy-sync/stable.json
2026-03-02 08:00:01  INFO      Gold manifest: /Volumes/SERVOY_GOLD/plugins/servoy-2025.12.1.4123/manifest.json
2026-03-02 08:00:02  INFO      Result: SUCCESS (0 warnings)
2026-03-02 08:00:02  INFO      Launching: open -a '/Applications/Servoy/2025.12.1.4123/Servoy Developer.app'
```

## Beispiel-Ausgabe (mehrere Profile – Auswahl erscheint)

```
  ────────────────────────────────────────────────────────────────
  Welches Servoy möchtest du starten?
  Pfeiltasten ↑↓, Enter zum Bestätigen, Ctrl+C zum Abbrechen.
  ────────────────────────────────────────────────────────────────
  ▶ stable    Stable 2025.12     /Applications/Servoy/2025.12.1.4123/
    nightly   Nightly 2026.03    /Applications/Servoy/2026.03.0.5000/
  ────────────────────────────────────────────────────────────────
```

## Beispiel-Ausgabe (Gold-Share offline, Servoy startet trotzdem)

```
2026-03-02 08:00:01  WARNING   Gold Share is unavailable – skipping sync and launching Servoy anyway.
2026-03-02 08:00:01  INFO      Launching: open -a '/Applications/Servoy/2025.12.1.4123/Servoy Developer.app'
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
| Python 3 nicht gefunden | Fehlermeldung + `exit 1` |
| `plugins_sync.py` nicht gefunden | Fehlermeldung + `exit 1` |
| Kein Profil konfiguriert | plugins_sync.py beendet mit Exit 1 |
| Gold-Share offline | Sync wird mit Warnung übersprungen; Servoy startet trotzdem (Exit 2) |
| Sync Exit 2 (Warnungen) | Servoy startet trotzdem; Exit Code wird weitergegeben |
| Servoy-Binary nicht gefunden | plugins_sync.py loggt Fehler, Exit 1 |
