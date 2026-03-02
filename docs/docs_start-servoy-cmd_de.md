# start-servoy.cmd – Anleitung

## Zweck

`start-servoy.cmd` ist der **Windows-Wrapper**, über den Servoy gestartet wird, anstatt `servoy.exe` direkt aufzurufen.

Er stellt sicher, dass vor dem Start automatisch `plugins_sync.py` ausgeführt wird – Sync-Fehler **blockieren den Start nicht**, sondern werden nur als Warnung angezeigt.

---

## Voraussetzungen

- Windows (V1; macOS/Linux folgt in V2 als `start-servoy.sh`)
- Python 3 installiert (auf PATH als `python` oder `py`)
- Lokale Config `%USERPROFILE%\.servoy-plugin-sync.json` angelegt (siehe [docs_plugins_sync.md](docs_plugins_sync.md))
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
    ├─ 1. Config lesen  (%USERPROFILE%\.servoy-plugin-sync.json)
    │       └─ via PowerShell: servoy_home extrahieren
    │
    ├─ 2. Python suchen
    │       ├─ python  (auf PATH?)
    │       ├─ py -3   (Python Launcher?)
    │       └─ keines → Warnung, Sync überspringen
    │
    ├─ 3. plugins_sync.py ausführen
    │       ├─ Exit 0  → "Sync completed successfully"
    │       └─ Exit ≠ 0 → Warnung + Exitcode + Logpfad anzeigen
    │
    └─ 4. Servoy starten
            ├─ servoy.exe gefunden → start "" "<pfad>\developer\servoy.exe"
            └─ nicht gefunden → Fehlermeldung + exit /b 1
```

---

## Beispiel-Ausgabe (alles OK)

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

## Beispiel-Ausgabe (Sync-Fehler, Servoy startet trotzdem)

```
[WARNING] Plugin sync finished with issues (exit code: 2).
          Some plugins may not be up to date.
          Check the log for details:
          C:\servoys\2025.12.1.4123\application_server\plugins\gold_plugins_sync.log
          Starting Servoy anyway...

[INFO] Launching: C:\servoys\2025.12.1.4123\developer\servoy.exe
```

## Beispiel-Ausgabe (Python nicht gefunden)

```
[WARNING] Python 3 was not found on PATH.
          Please install Python 3 or add it to PATH.
          Plugin sync will be SKIPPED.
          Starting Servoy anyway...

[INFO] Launching: C:\servoys\2025.12.1.4123\developer\servoy.exe
```

---

## Fehlerszenarien

| Situation | Verhalten |
|---|---|
| Config-Datei fehlt | Warnung + Sync skip + Servoy startet |
| `servoy_home` nicht in Config | Warnung + Sync skip + Servoy startet |
| Python nicht auf PATH | Warnung + Sync skip + Servoy startet |
| `plugins_sync.py` nicht gefunden | Warnung + Sync skip + Servoy startet |
| Sync Exit Code 2 (Warnungen) | Warnung mit Logpfad + Servoy startet |
| `servoy.exe` nicht gefunden | Fehlermeldung + `pause` + Exit Code 1 |

---

## Einrichten im Team (einmalig pro Dev)

1. Config anlegen (falls noch nicht geschehen): `%USERPROFILE%\.servoy-plugin-sync.json`
2. Eine **Verknüpfung** zu `start-servoy.cmd` auf dem Desktop oder Taskbar anlegen.
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

- Servoy wird mit `start "" "…\servoy.exe"` gestartet – das CMD-Fenster schließt sich danach sofort. Falls du die Sync-Ausgabe lesen möchtest, starte `start-servoy.cmd` aus einem offenen CMD-Fenster.
- Der Wrapper liest den `servoy_home`-Pfad **immer frisch** aus der Config – kein Hardcoding nötig.
- Bei einem Servoy-Versions-Update: nur `servoy_version` (und ggf. `servoy_home`) in der Config anpassen.
