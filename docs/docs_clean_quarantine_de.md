# clean_quarantine.py – Dokumentation

## Zweck

Das Script löscht alte datumsstempelbasierte Quarantäne-Ordner unterhalb von
`application_server/plugins__quarantine/`.

`plugins_sync.py` verschiebt entfernte verwaltete Plugins niemals endgültig –
sie landen im Quarantäne-Ordner, organisiert nach Datum (`YYYY-MM-DD`).
`clean_quarantine.py` ist das Gegenstück, das diese Ordner nach einer
konfigurierbaren Aufbewahrungszeit (Standard: **30 Tage**) entfernt.

---

## Voraussetzungen

- dieselbe Config-Datei wie `plugins_sync.py`:
  `%USERPROFILE%\.servoy-plugin-sync.json`
- nur das Feld `servoy_home` wird benötigt
- Python 3.10+ (keine externen Pakete)

---

## Aufruf

```
python clean_quarantine.py [--older-than-days N] [--dry-run] [--verbose] [--config <Pfad>]
```

### Parameter

| Parameter | Default | Beschreibung |
|---|---|---|
| `--older-than-days N` | `30` | Lösche Ordner, die **älter** als N Tage sind |
| `--dry-run` | – | Zeigt nur an, was gelöscht werden würde – macht **keine** Änderungen |
| `--verbose` | – | Gibt DEBUG-Meldungen aus |
| `--config <Pfad>` | `~\.servoy-plugin-sync.json` | Alternativer Pfad zur Config-Datei |

---

## Beispiele

### Standard-Lauf (30 Tage, echtes Löschen)

```cmd
python clean_quarantine.py
```

Beispielausgabe:

```
2026-05-20 09:00:00  INFO     Cleaning quarantine folders older than 30 days (before 2026-04-20).
2026-05-20 09:00:00  INFO     Quarantine directory: C:\Servoys\2025.12.1.4123\application_server\plugins__quarantine
2026-05-20 09:00:00  INFO       Deleted: 2026-03-10  (71 days old)
2026-05-20 09:00:00  INFO       Deleted: 2026-04-05  (45 days old)
2026-05-20 09:00:00  INFO     Done. 2 folder(s) deleted.
```

### 90-Tage-Grenze

```cmd
python clean_quarantine.py --older-than-days 90
```

### Dry-Run (nur anzeigen, nichts löschen)

```cmd
python clean_quarantine.py --dry-run
```

Beispielausgabe:

```
2026-05-20 09:00:00  INFO     [DRY-RUN] Cleaning quarantine folders older than 30 days (before 2026-04-20).
2026-05-20 09:00:00  INFO     Quarantine directory: C:\Servoys\2025.12.1.4123\application_server\plugins__quarantine
2026-05-20 09:00:00  INFO       [DRY-RUN] Would delete: 2026-03-10  (71 days old)
2026-05-20 09:00:00  INFO     [DRY-RUN] 1 folder(s) would be deleted.
```

### Als Scheduled Task (Windows)

Um die Bereinigung wöchentlich auszuführen, kann ein Windows Scheduled Task
angelegt werden:

```
Aktion: python C:\projects\svy-gold-script\tools\clean_quarantine.py
Auslöser: Wöchentlich, Montag 07:00
```

---

## Welche Ordner werden gelöscht?

Es werden **ausschließlich** Unterordner gelöscht, deren Name dem Format
`YYYY-MM-DD` entspricht und die älter als der angegebene Schwellwert sind.
Alle anderen Inhalte des Quarantäne-Verzeichnisses (z. B. manuell angelegte
Ordner ohne Datumsnamen) werden ignoriert.

---

## Exitcodes

| Code | Bedeutung |
|---|---|
| `0` | Erfolg (auch wenn nichts zu löschen war) |
| `1` | Fataler Fehler (Config fehlt, `servoy_home` ungültig, …) |

---

## Hinweis für Gold-Maintainer

`clean_quarantine.py` ist primär ein **Entwickler-Tool** – jeder Entwickler
bereinigt seine eigene lokale Quarantäne. Der Gold-Share selbst enthält keine
Quarantäne-Ordner.

Empfohlene Aufbewahrungszeit: **30 Tage** (genug Zeit für Rollback, falls ein
Plugin versehentlich aus dem Manifest entfernt wurde).
