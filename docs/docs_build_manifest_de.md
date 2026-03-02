# build_manifest.py – Anleitung

## Zweck

`build_manifest.py` ist ein Tool für den **Gold Maintainer** (die Person, die den zentralen Plugin-Stand pflegt).  
Es durchsucht einen `files/`-Ordner auf dem Gold-Share rekursiv und erzeugt daraus eine `manifest.json`-Datei, die für jeden Plugin-Datei den relativen Pfad, die Dateigröße (Bytes) und den SHA-256-Hash enthält.

Das Manifest ist die **Source of Truth** für `plugins_sync.py`: Nur was im Manifest steht, wird als "Managed Plugin" behandelt.

---

## Voraussetzungen

- Python 3.10 oder neuer
- Keine externen Packages nötig (nur Standardbibliothek)

---

## Aufruf

```
python build_manifest.py --files-dir "<Pfad zum files-Ordner>" --out "<Pfad zur manifest.json>" --servoy-version "<Version>"
```

### Parameter

| Parameter | Pflicht | Beschreibung |
|---|---|---|
| `--files-dir` | Ja | Pfad zum `files/`-Ordner mit den Plugin-Dateien |
| `--out` | Ja | Zielpfad für die generierte `manifest.json` |
| `--servoy-version` | Ja | Servoy-Versionsstring, z. B. `2025.12.1.4123` |
| `--self-test` | Nein | Führt den eingebauten Selbsttest aus und beendet das Script |

---

## Beispiele

### Manifest für Servoy 2025.12.1.4123 generieren (Windows)

```cmd
python build_manifest.py ^
    --files-dir "K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\files" ^
    --out       "K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\manifest.json" ^
    --servoy-version "2025.12.1.4123"
```

Erwartete Ausgabe:

```
Scanning 'K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\files' …
  Found 12 file(s).
Writing manifest to 'K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\manifest.json' …
Done. Manifest written (12 entries, version=2025.12.1.4123).
```

### Selbsttest ausführen

```cmd
python build_manifest.py --self-test
```

Erwartete Ausgabe:

```
Running self-test …
Self-test PASSED – all assertions OK.
```

### Hilfe anzeigen

```cmd
python build_manifest.py --help
```

---

## Erzeugte manifest.json – Struktur

```json
{
  "servoy_version": "2025.12.1.4123",
  "generated_at": "2026-03-02",
  "files": [
    {
      "path": "myplugin.jar",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "size": 102400
    },
    {
      "path": "subfolder/another.jar",
      "sha256": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
      "size": 4096
    }
  ]
}
```

**Hinweise:**
- `path` enthält immer **Forward Slashes** (`/`), auch auf Windows.
- Die Einträge sind **alphabetisch nach `path` sortiert** (deterministisch, gut für Git-Diffs).
- Das Manifest wird zuerst als `.tmp`-Datei geschrieben und dann atomar umbenannt – kein halb-geschriebenes Manifest möglich.

---

## Fehlerbehandlung & Exitcodes

| Exitcode | Bedeutung |
|---|---|
| `0` | Erfolgreich abgeschlossen |
| `1` | Laufzeitfehler (z. B. `files-dir` existiert nicht, Datei nicht lesbar, Schreibfehler) |
| `2` | Fehlende Pflicht-Argumente |

Fehlermeldungen werden auf `stderr` ausgegeben, z. B.:

```
ERROR: files-dir does not exist or is not a directory: 'K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\files'
```

---

## Typischer Workflow (Gold Maintainer)

1. Plugin-Dateien in `K:\SERVOY_GOLD\plugins\servoy-<VERSION>\files\` ablegen oder aktualisieren.
2. `build_manifest.py` ausführen – erzeugt neues `manifest.json`.
3. Optional: `CHANGELOG.md` auf dem Share kurz aktualisieren (was hat sich geändert, warum).
4. Alle Devs erhalten beim nächsten Servoy-Start automatisch den neuen Stand via `plugins_sync.py`.

---

## Selbsttest – Was wird geprüft?

`--self-test` legt einen temporären Ordner mit 2 synthetischen Dateien an:

- `alpha.jar` (flach)
- `subfolder/beta.jar` (in Unterordner)

Dann wird geprüft:

- Manifest enthält genau 2 Einträge
- Sortierung stimmt (`alpha.jar` vor `subfolder/beta.jar`)
- SHA-256-Hashes sind korrekt (werden gegen bekannte Werte verglichen)
- Dateigrößen stimmen
- Pfade enthalten nur Forward Slashes
- `generated_at` entspricht dem heutigen Datum
- Der Temp-Ordner wird am Ende immer aufgeräumt (auch bei Fehler)
