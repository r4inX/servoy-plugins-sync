# start-servoy.cmd – Anleitung

## Zweck

`start-servoy.cmd` ist der **Windows-Wrapper**, über den Servoy gestartet wird, anstatt `servoy.exe` direkt aufzurufen.

Er stellt sicher, dass vor dem Start automatisch `plugins_sync.py` ausgeführt wird – Sync-Fehler **blockieren den Start nicht**, sondern werden nur als Warnung angezeigt.

---

## Voraussetzungen

- Windows
- Python 3.10+ installiert (auf PATH als `python` oder `py`)
- Mind. ein Config-Profil angelegt via `python plugins_sync.py --init-config`
  (siehe [docs_plugins_sync.md](docs_plugins_sync.md))
- `plugins_sync.py` liegt im selben Ordner wie `start-servoy.cmd`

---

## Aufruf

Doppelklick auf `start-servoy.cmd` oder aus CMD/PowerShell:

```cmd
start-servoy.cmd
```

Das Script führt automatisch alle Schritte aus – kein weiterer Parameter nötig.

---

## Ablauf im Detail

```
start-servoy.cmd
    │
    ├─ 1. Python suchen  (python → py -3 → Fehler)
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
            └─ Servoy starten (servoy.exe, cwd = developer/)
                    └─ Exit ungleich 0: [WARNING] im CMD-Fenster + Pause
```

---

## Beispiel-Ausgabe (ein Profil, alles OK)

```
2026-03-02 08:00:01  INFO      Config: C:\Users\max\.servoy-sync\stable.json
2026-03-02 08:00:01  INFO      Gold manifest: K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\manifest.json
2026-03-02 08:00:02  INFO      === Phase 1: Install / Update managed plugins ===
2026-03-02 08:00:02  INFO        Nichts zu installieren oder zu aktualisieren.
2026-03-02 08:00:02  INFO      Result: SUCCESS (0 warnings)
2026-03-02 08:00:02  INFO      Launching Servoy: C:\servoys\2025.12.1.4123\developer\servoy.exe
```

## Beispiel-Ausgabe (mehrere Profile – Auswahl erscheint)

```
  ────────────────────────────────────────────────────────────────
  Welches Servoy möchtest du starten?
  Pfeiltasten ↑↓, Enter zum Bestätigen, Ctrl+C zum Abbrechen.
  ────────────────────────────────────────────────────────────────
  ▶ stable    Stable 2025.12     C:\servoys\2025.12.1.4123\
    nightly   Nightly 2026.03    C:\servoys\2026.03.0.5000\
  ────────────────────────────────────────────────────────────────
```

## Beispiel-Ausgabe (Gold-Share offline, Servoy startet trotzdem)

```
2026-03-02 08:00:01  WARNING   Gold Share is unavailable – skipping sync and launching Servoy anyway.
2026-03-02 08:00:01  INFO      Launching Servoy: C:\servoys\2025.12.1.4123\developer\servoy.exe
```

---

## Fehlerszenarien

| Situation | Verhalten |
|---|---|
| Python nicht auf PATH | Fehlermeldung + `pause` + Exit Code 1 |
| `plugins_sync.py` nicht gefunden | Fehlermeldung + `pause` + Exit Code 1 |
| Kein Profil konfiguriert | plugins_sync.py beendet mit Exit 1 → CMD zeigt `[WARNING]` + Pause |
| Gold-Share offline | Sync wird mit Warnung übersprungen; Servoy startet trotzdem (Exit 2, kein Pause) |
| Sync Exit Code 2 (Warnungen) | CMD zeigt `[WARNING]` + Pause mit Log-Hinweis |
| `servoy.exe` nicht gefunden | plugins_sync.py loggt Fehler, Exit 1 → CMD zeigt `[WARNING]` + Pause |

---

## Einrichten im Team (einmalig pro Dev)

1. Profil anlegen (falls noch nicht geschehen):
   ```cmd
   python plugins_sync.py --init-config
   ```
   Für mehrere Servoy-Installationen `--init-config --profile <name>` pro Profil.
2. Eine **Verknüpfung** zu `start-servoy.cmd` auf dem Desktop oder der Taskbar anlegen.
3. Alle bisherigen Verknüpfungen zu `servoy.exe` ersetzen.

### Verknüpfung per PowerShell erstellen

```powershell
$ws  = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut("$env:USERPROFILE\Desktop\Servoy.lnk")
$lnk.TargetPath       = "C:\dev\servoy-gold-sync\tools\start-servoy.cmd"
$lnk.WorkingDirectory = "C:\dev\servoy-gold-sync\tools"
$lnk.Save()
```

---

## Hinweise

- Das Script delegiert **alle** Logik (Profilauswahl, Sync, Start) an
  `plugins_sync.py --launch` — der CMD-Script selbst liest keine Config.
- Servoy wird mit `cwd = developer/` gestartet, sodass Laufzeit-Ordner
  (`reports/`, `tmp/`, `www/`) korrekt im `developer/`-Unterordner der
  Servoy-Installation angelegt werden.
- Nach einem Servoy-Update: Profil per `--init-config --profile <name>` aktualisieren.
