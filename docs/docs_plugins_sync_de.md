# plugins_sync.py – Anleitung

## Zweck

`plugins_sync.py` ist das **Client-Script**, das auf jedem Entwickler-Rechner läuft (typischerweise automatisch beim Servoy-Start über `start-servoy.cmd`).

Es synchronisiert die **Managed Plugins** vom zentralen Gold-Share in die lokale Servoy-Installation:

- **Fehlende Plugins** werden vom Share kopiert.
- **Veraltete Plugins** (Hash-Unterschied) werden durch die aktuelle Version ersetzt.
- **Plugins, die aus dem Manifest entfernt wurden**, werden in einen Quarantäne-Ordner verschoben (kein hard delete).
- **Private / unmanaged Plugins** (nicht im Manifest und nie als managed registriert) werden **nie angefasst**.

---

## Voraussetzungen

- Python 3.10 oder neuer
- Keine externen Packages nötig (nur Standardbibliothek)
- Gold-Share muss erreichbar sein (z. B. `K:\` gemappt)
- Lokale Config-Datei muss existieren (siehe unten)

---

## Lokale Config einrichten

Die Config-Datei wird **einmalig pro Entwickler-Rechner** angelegt. Sie wird nie ins Git eingecheckt – jeder Dev hat seine eigenen lokalen Pfade.

### Schnellweg – Setup-Wizard (empfohlen)

Der einfachste Weg ist der interaktive Wizard:

```cmd
python plugins_sync.py --init-config
```

Der Wizard:
1. Fragt `servoy_home` ab und prüft, ob der Pfad existiert und wie eine Servoy-Installation aussieht
2. Fragt `gold_root` ab und prüft, ob der Share erreichbar ist
3. Fragt `servoy_version` ab – schlägt die automatisch erkannte Version vor
4. Fragt `mode` ab (Default: `quarantine`)
5. Zeigt eine Zusammenfassung und fragt vor dem Schreiben nochmal nach

Am Ende führst du direkt einen Status-Check aus, um das Setup zu bestätigen:

```cmd
python plugins_sync.py --status
```

### Manuell – Beispieldatei kopieren

Die Datei [`docs/example.servoy-plugin-sync.json`](example.servoy-plugin-sync.json) als Vorlage verwenden:

```cmd
copy "%~dp0..\docs\example.servoy-plugin-sync.json" "%USERPROFILE%\.servoy-plugin-sync.json"
```

Oder manuell anlegen:

```cmd
notepad "%USERPROFILE%\.servoy-plugin-sync.json"
```

### Manuell – Eigene Pfade eintragen

Inhalt der Datei (Vorlage):

```json
{
  "gold_root":      "K:\\SERVOY_GOLD\\",
  "servoy_home":    "C:\\servoys\\2025.12.1.4123\\",
  "servoy_version": "2025.12.1.4123",
  "mode":           "quarantine"
}
```

### Config-Felder – was muss jeder Dev anpassen?

| Feld | Pflicht | Was eintragen? |
|---|---|---|
| `gold_root` | Ja | Pfad zum gemappten Gold-Share. Normalerweise `K:\\SERVOY_GOLD\\` für alle Windows-Devs – nur ändern, wenn dein Laufwerksbuchstabe abweicht. |
| `servoy_home` | **Ja, individuell** | Dein lokales Servoy-Installationsverzeichnis. Muss `developer\` und `application_server\` enthalten. Beispiele: `C:\\servoys\\2025.12.1.4123\\` oder `C:\\Program Files\\Servoy\\`. |
| `servoy_version` | Ja | Muss exakt mit dem Ordnernamen auf dem Share übereinstimmen (`servoy-<version>`). Aktuell: `2025.12.1.4123`. Beim Versions-Update diesen Wert anpassen. |
| `mode` | Nein | `quarantine` (Default, empfohlen) – entfernte Managed Plugins werden verschoben, nicht gelöscht. |

> **Tipp – servoy_home finden:** Öffne den Windows Explorer und navigiere zu deiner Servoy-Installation. Der gesuchte Ordner enthält zwei Unterordner: `developer` und `application_server`. Den vollständigen Pfad dieses Ordners als `servoy_home` eintragen – mit doppelten Backslashes und abschließendem `\\`.

### Beispiele (verschiedene Dev-Setups)

**Dev 1 – Standardpfad:**
```json
{
  "gold_root":      "K:\\SERVOY_GOLD\\",
  "servoy_home":    "C:\\servoys\\2025.12.1.4123\\",
  "servoy_version": "2025.12.1.4123",
  "mode":           "quarantine"
}
```

**Dev 2 – Servoy unter Program Files:**
```json
{
  "gold_root":      "K:\\SERVOY_GOLD\\",
  "servoy_home":    "C:\\Program Files\\Servoy\\2025.12.1.4123\\",
  "servoy_version": "2025.12.1.4123",
  "mode":           "quarantine"
}
```

**Dev 3 – Abweichender Laufwerksbuchstabe für Share:**
```json
{
  "gold_root":      "Z:\\SERVOY_GOLD\\",
  "servoy_home":    "D:\\dev\\servoy\\2025.12.1.4123\\",
  "servoy_version": "2025.12.1.4123",
  "mode":           "quarantine"
}
```

### Nach einem Servoy-Versionsupdate

Nur `servoy_version` (und ggf. `servoy_home`) anpassen:

```json
{
  "gold_root":      "K:\\SERVOY_GOLD\\",
  "servoy_home":    "C:\\servoys\\2026.3.0.5000\\",
  "servoy_version": "2026.3.0.5000",
  "mode":           "quarantine"
}
```

---

## Aufruf

```
python plugins_sync.py [--config <Pfad>] [--dry-run] [--verbose] [--status] [--init-config]
```

### Parameter

| Parameter | Beschreibung |
|---|---|
| `--init-config` | Interaktiver Setup-Wizard: fragt alle Config-Felder ab, validiert Eingaben und schreibt die Config-Datei |
| `--config <Pfad>` | Alternativer Pfad zur Config-Datei (Default: `%USERPROFILE%\.servoy-plugin-sync.json`) |
| `--dry-run` | Zeigt nur an, was getan würde – macht **keine** Änderungen |
| `--verbose` | Gibt DEBUG-Meldungen aus (z. B. welche Dateien bereits aktuell sind) |
| `--status` | Zeigt den aktuellen Plugin-Zustand (OK / MISSING / OUTDATED) ohne Änderungen. Exit 0 = alles aktuell, Exit 2 = Abweichungen gefunden. |

---

## Beispiele

### Erstmalige Einrichtung mit Wizard

```cmd
python plugins_sync.py --init-config
```

Beispiel-Session:

```
============================================================
 Servoy Gold Plugin Sync – Config Setup Wizard
============================================================
  Target file: C:\Users\max\.servoy-plugin-sync.json

------------------------------------------------------------
 Step 1/4 – Servoy installation folder (servoy_home)
------------------------------------------------------------
  ...
  servoy_home: C:\servoys\2025.12.1.4123
  ✓  Detected installed version: 2025.12.1.4123

------------------------------------------------------------
 Step 2/4 – Gold Share root folder (gold_root)
------------------------------------------------------------
  gold_root: K:\SERVOY_GOLD
  ✓  'plugins' sub-folder found on share.

------------------------------------------------------------
 Step 3/4 – Servoy version (servoy_version)
------------------------------------------------------------
  servoy_version [2025.12.1.4123]:
  ✓  manifest.json found on share – version matches the Gold Share.

------------------------------------------------------------
 Step 4/4 – Plugin removal mode (mode)
------------------------------------------------------------
  mode [quarantine]:

------------------------------------------------------------
 Summary – config to be written:
------------------------------------------------------------
{
  "gold_root": "K:\\SERVOY_GOLD",
  "servoy_home": "C:\\servoys\\2025.12.1.4123",
  "servoy_version": "2025.12.1.4123",
  "mode": "quarantine"
}
  Target: C:\Users\max\.servoy-plugin-sync.json

  Write this config? [Y/n]: Y
  ✓  Config written to: C:\Users\max\.servoy-plugin-sync.json
  Run 'python plugins_sync.py --status' to verify the setup.
```

Mit `--config` kann ein anderer Zielpfad angegeben werden:

```cmd
python plugins_sync.py --init-config --config "D:\team\my-config.json"
```

### Normaler Sync (Standard-Config)

```cmd
python plugins_sync.py
```

Erwartete Ausgabe (Beispiel):

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

### Dry-Run (nur anzeigen, nichts ändern)

```cmd
python plugins_sync.py --dry-run --verbose
```

Nützlich, um vor dem echten Sync zu überprüfen, was passieren würde.

### Abweichende Config verwenden

```cmd
python plugins_sync.py --config "D:\team\my-sync-config.json"
```

### Status-Report anzeigen (kein Sync)

```cmd
python plugins_sync.py --status
```

Beispielausgabe:

```
================================================================
 Servoy Gold Plugin Sync – Status Report
================================================================

  Config version (servoy_version): 2025.12.1.4123
  Installed version (detected):    2025.12.1.4123  [✓]
  Manifest version:                2025.12.1.4123  [✓]
  Manifest generated:              2026-05-15

  --------------------------------------------------------------
  PATH                                       STATUS
  --------------------------------------------------------------
  myplugin.jar                               OK
  subfolder/another.jar                      OUTDATED (size …)
  newplugin.jar                              MISSING  → will be installed on next sync

  Summary: 2 ISSUE(S) FOUND
```

Die Spalte **STATUS** zeigt:

| Wert | Bedeutung |
|---|---|
| `OK` | SHA-256 und Größe stimmen überein |
| `MISSING` | Datei fehlt lokal – wird beim nächsten Sync installiert |
| `OUTDATED` | Größe oder Hash weichen ab – wird beim nächsten Sync aktualisiert |

Auch angezeigt: Dateien, die beim nächsten Sync **quarantined** würden, und **Private Plugins** (werden nie angefasst).

---

## Versions-Validierung

Ab dieser Version erkennt das Script automatisch die installierte Servoy-Version
und vergleicht drei Quellen:

| Quelle | Woher |
|---|---|
| **Config `servoy_version`** | `~/.servoy-plugin-sync.json` des Entwicklers |
| **Manifest `servoy_version`** | Feld in `manifest.json` auf dem Gold-Share |
| **Installierte Version (auto-detect)** | Ordnername `com.servoy.eclipse.feature_<VERSION>` unter `<servoy_home>/developer/features/` |

### Erkennung der installierten Version

Das Script scannt `<servoy_home>/developer/features/` nach einem Ordner, der
mit `com.servoy.eclipse.feature_` beginnt. Aus dem Suffix des Ordnernamens
wird die vollständige Version (`2025.12.1.4123`) gelesen – dieselbe
Information, die Eclipse unter *Hilfe → Über Servoy Developer* anzeigt.

Fallback: Falls dieser Ordner nicht existiert, wird
`application_server/lib/version.txt` gelesen. Diese Datei enthält nur die
Build-Nummer (`4123`), keine vollständige Versionsnummer.

> **Wichtig:** Der Installationsordner (z. B. `C:\Servoys\servoy_4123`) enthält
> die Version im Namen, aber das ist für das Script irrelevant. Ausschlaggebend
> ist nur `servoy_home` in der Config.

### Was passiert bei einem Versions-Mismatch?

- Es werden nur **Warnungen** geloggt – kein Abbruch.
- Der Sync läuft weiter (Plugins werden aus dem Manifest installiert, egal was).
- Der Entwickler sieht die Warnung und kann reagieren:
  - Config-Version anpassen (nach eigenem Servoy-Update)
  - Gold Maintainer fragen (wenn das Manifest veraltet scheint)

---

## Wie funktioniert der State-Mechanismus?

Das Script speichert nach jedem erfolgreichen Lauf eine Liste der aktuell managed Plugins in:

```
<servoy_home>\application_server\plugins\.gold_sync_state.json
```

Beispiel-Inhalt:

```json
{
  "updated_at": "2026-03-02T08:00:02",
  "managed_paths": [
    "myplugin.jar",
    "subfolder/another.jar"
  ]
}
```

**Beim nächsten Lauf** wird verglichen:
- Was war bisher managed? → State-Datei
- Was ist jetzt managed? → aktuelles Manifest

Dateien, die **vorher** im State standen, aber **jetzt nicht mehr** im Manifest sind → werden in Quarantäne verschoben.

Dateien, die **nie** im State standen (private Plugins) → werden **nie** angefasst.

---

## Quarantäne

Plugins, die aus dem Manifest entfernt wurden, landen in:

```
<servoy_home>\application_server\plugins__quarantine\YYYY-MM-DD\
```

Beispiel: `C:\servoys\2025.12.1.4123\application_server\plugins__quarantine\2026-03-02\myplugin.jar`

Der Datumsordner erlaubt einfaches Rückgängigmachen, falls das Manifest falsch war.

---

## Logging

Das Script schreibt gleichzeitig auf **stdout** und in eine Logdatei:

```
<servoy_home>\application_server\plugins\gold_plugins_sync.log
```

Alle Läufe werden chronologisch in derselben Datei akkumuliert (kein Überschreiben).

---

## Fehlerbehandlung & Exitcodes

| Exitcode | Bedeutung |
|---|---|
| `0` | Alles erfolgreich (auch `--status` ohne Abweichungen) |
| `1` | Fataler Fehler: Config fehlt/ungültig, Manifest unerreichbar, lokaler Plugins-Ordner nicht vorhanden |
| `2` | Abgeschlossen, aber mit Warnungen (gesperrte Datei); oder `--status` hat Abweichungen gefunden |

### Häufige Fehler

**Share nicht erreichbar:**
```
ERROR  Manifest not found: 'K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\manifest.json'
       Is the Gold Share accessible? Check that the network drive is mapped.
```
→ Exitcode `1`. Das `start-servoy.cmd` startet Servoy trotzdem.

**Datei in Benutzung (Servoy noch offen):**
```
WARNING  Cannot install 'myplugin.jar': [WinError 32] The process cannot access the file ...
         Tip: Close Servoy and retry.
```
→ Exitcode `2`. Servoy wird trotzdem gestartet. Beim nächsten Start wird der Sync erneut versucht.

---

## Ablauf im Team (normaler Betrieb)

1. Dev öffnet Servoy über `start-servoy.cmd` (nicht direkt `servoy.exe`).
2. `start-servoy.cmd` ruft automatisch `python plugins_sync.py` auf.
3. Wenn Sync erfolgreich (Exit 0): Servoy startet normal.
4. Wenn Sync mit Warnungen (Exit 2) oder fatal (Exit 1): kurze Meldung in CMD-Fenster, Servoy startet trotzdem.

---

## Dateien, die das Script anlegt / verändert

| Datei / Ordner | Beschreibung |
|---|---|
| `<plugins>\.gold_sync_state.json` | State-Datei (managed paths des letzten Laufs) |
| `<plugins>\gold_plugins_sync.log` | Log aller Sync-Läufe |
| `plugins__quarantine\YYYY-MM-DD\` | Quarantäne-Ordner für entfernte managed Plugins |
| `<plugins>\<managed-dateien>` | Installierte/aktualisierte Plugins |

Das Script legt **niemals** Dateien an oder verändert Dateien, die nicht im Manifest (und im State) als managed eingetragen sind.
