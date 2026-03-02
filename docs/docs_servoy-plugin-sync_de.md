# Servoy Gold Plugins – Team Sync (V1: Windows, V2: macOS/Linux)

Stand: 2026-03-02  
Team: 3 Devs (Windows primary, zusätzlich macOS & Ubuntu)  
Servoy Version (aktuell): 2025.12.1.4123  
Ziel: Einheitlicher Plugin-Stand im `servoy/application_server/plugins`, ohne private/unreleased Plugins einzelner Devs zu löschen.

---

## 1) Problem & Ziel

### Problem
Jeder Entwickler hat lokal unterschiedliche Plugins in:
- `<SERVOY_HOME>\application_server\plugins`

Das führt zu:
- "bei mir geht’s" / "bei dir nicht"
- schwer reproduzierbaren Fehlern
- mühsamem Onboarding

### Ziel
Ein zentraler "Gold"-Pluginstand liegt auf einem Share und wird lokal automatisch synchronisiert:
- **Managed**: Team-Plugins (aus Manifest) werden installiert/aktualisiert/entfernt
- **Unmanaged**: Private/unreleased Plugins bleiben unangetastet
- Sync-Fehler sollen **informativ warnen**, aber **Servoy trotzdem starten**.

---

## 2) Begriffe

- **SERVOY_HOME**: Ordner, der `developer/` und `application_server/` enthält  
  Beispiele:
  - `C:\servoys\2025.12.1.4123\`
  - `C:\Program Files\Servoy\` (variiert pro Dev)

- **Gold Root**: zentraler Share-Ordner (Windows gemappt)  
  Aktuell: `K:\SERVOY_GOLD\`

---

## 3) Architektur (V1)

### 3.1 Source of Truth (Share)
Share enthält pro Servoy-Version einen Satz Plugins + Manifest:

Beispielstruktur:

- `K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\manifest.json`
- `K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\files\...` (Plugin-Dateien)

**Hinweis:** Optional kann später ein `current\` Folder eingeführt werden. V1 ist versioniert, damit Updates kontrollierbar bleiben.

### 3.2 Client (lokal)
- Python-Script `plugins_sync.py` liest Config, Manifest und synchronisiert.
- Servoy wird über ein Wrapper-Script gestartet (V1 Windows: `.cmd`).

---

## 4) Regeln für Synchronisation

### 4.1 Managed vs Unmanaged
- **Managed Plugins** = alle Dateien, die im `manifest.json` stehen.
- **Unmanaged Plugins** = alles, was lokal im plugins-Ordner liegt, aber nicht im Manifest steht.

### 4.2 Was wird gemacht?
Für jedes Managed Plugin aus dem Manifest:
- fehlt lokal → **kopieren**
- vorhanden, aber Hash abweichend → **ersetzen** (sicher via temp-copy + rename)

Für lokale Plugins, die *früher* Managed waren, aber *jetzt nicht mehr* im Manifest stehen:
- **entfernen**, aber nicht hard-delete:
  - verschieben nach Quarantäne-Ordner

### 4.3 Quarantäne
Beim "Entfernen" wird verschoben nach:

`<SERVOY_HOME>\application_server\plugins__quarantine\YYYY-MM-DD\...`

So kann man rückgängig machen, falls das Manifest falsch war.

### 4.4 Private Plugins
Private/unreleased Plugins dürfen lokal existieren und werden **nicht** entfernt oder verändert.

---

## 5) Manifest-Format (V1)

`manifest.json` enthält:

- `servoy_version` (String)
- `generated_at` (YYYY-MM-DD)
- `files`: Liste von Einträgen:
  - `path` (relativ zu `files/`)
  - `sha256` (Hash)
  - `size` (Bytes)

Minimalbeispiel:

```json
{
  "servoy_version": "2025.12.1.4123",
  "generated_at": "2026-03-02",
  "files": [
    { "path": "myplugin.jar", "sha256": "…", "size": 12345 },
    { "path": "subfolder/another.jar", "sha256": "…", "size": 999 }
  ]
}
```

**Wichtig:** Es wird anhand `sha256` entschieden, ob eine Datei identisch ist.

---

## 6) Lokale Config (pro Entwickler)

Da jeder Servoy woanders installiert hat, brauchen wir eine lokale Config-Datei pro User.

Vorschlag Speicherort Windows:
- `%USERPROFILE%\.servoy-plugin-sync.json`

Beispiel:

```json
{
  "gold_root": "K:\\SERVOY_GOLD\\",
  "servoy_home": "C:\\servoys\\2025.12.1.4123\\",
  "servoy_version": "2025.12.1.4123",
  "mode": "quarantine"
}
```

**Felder:**
- `gold_root` (Pfad zum Share)
- `servoy_home` (lokal)
- `servoy_version` (wählt den Manifest-Ordner am Share)
- `mode`:
  - `quarantine` (Default, sicher)
  - (optional später) `delete` (hart löschen)

---

## 7) Windows Start: Wrapper statt servoy.exe direkt

### Warum?
Eclipse/Servoy `servoy.ini`/`eclipse.ini` ist nicht dafür gedacht, verlässlich externe Scripts beim Start auszuführen.

### Lösung (V1)
Wir starten Servoy über ein Script:
1) `python plugins_sync.py` ausführen
2) bei Fehler: Warnung anzeigen
3) Servoy trotzdem starten (`servoy.exe`)

---

## 8) Umsetzungsschritte (V1 Windows)

### Step 0 – Repo/Ordner lokal anlegen
Lege ein neues Arbeitsverzeichnis an, z. B.:
- `C:\dev\servoy-gold-sync\`

Empfohlene Struktur:
- `/docs/servoy-plugin-sync.md` (diese Datei)
- `/tools/plugins_sync.py`
- `/tools/build_manifest.py` (wird vom Gold-Verantwortlichen genutzt)
- `/tools/start-servoy.cmd` (Wrapper)

### Step 1 – Gold Share initialisieren
Auf `K:\SERVOY_GOLD\` anlegen:

- `K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\files\`
- `K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\manifest.json`

Dann alle gewünschten Team-Plugins nach `files\` kopieren.

### Step 2 – Manifest generieren
Mit `build_manifest.py` Manifest aus `files\` generieren:
- Hash + Size für jede Datei
- Manifest schreibt nach `.../manifest.json`

### Step 3 – Client Sync Script entwickeln
`plugins_sync.py`:
- liest `%USERPROFILE%\.servoy-plugin-sync.json`
- findet:
  - `gold_manifest = <gold_root>\plugins\servoy-<servoy_version>\manifest.json`
  - `gold_files_dir = <gold_root>\plugins\servoy-<servoy_version>\files\`
  - `local_plugins_dir = <servoy_home>\application_server\plugins\`
- synchronisiert Managed Plugins
- verschiebt „entfernte Managed“ nach Quarantäne
- schreibt Logfile (z. B. neben dem Script oder in `%LOCALAPPDATA%`)

### Step 4 – Wrapper Script
`start-servoy.cmd`:
- ruft `python plugins_sync.py`
- wenn Errorlevel != 0:
  - Hinweis ausgeben ("Sync failed: ... — starting Servoy anyway")
- startet `"<servoy_home>\developer\servoy.exe"`

### Step 5 – Rollout im Team
Jeder Dev:
1) legt lokale Config an (`.servoy-plugin-sync.json`)
2) nutzt künftig `start-servoy.cmd` statt direkt `servoy.exe`

---

## 9) Betriebsprozess (Wer pflegt Gold?)

Empfehlung:
- 1 Person ist „Gold Maintainer“ pro Änderung
- Änderungen an Gold:
  1) Plugin-Dateien in `files\` anpassen
  2) Manifest neu generieren
  3) optional `CHANGELOG.md` aktualisieren (kurz: was/warum)

---

## 10) Fehlerfälle & Verhalten

### Share nicht erreichbar (K: nicht gemappt, offline)
- Script soll:
  - klare Warnung ausgeben
  - Exitcode != 0 setzen
- Wrapper soll trotzdem `servoy.exe` starten.

### Datei in Benutzung / Copy schlägt fehl
- Script soll:
  - die Datei nennen
  - empfehlen: "Servoy schließen und erneut starten"
- Wrapper startet trotzdem.

---

## 11) V2 (macOS/Linux) – später
Sobald Startpfade bekannt sind:
- macOS: Wrapper `.command` (Shell) oder kleines Startscript, das Python ausführt und dann Servoy startet
- Linux: `start-servoy.sh`

Python-Sync bleibt gleich, nur:
- `gold_root` ist ein mount path (`/Volumes/...` bzw. `/mnt/...`)
- `servoy_home` ist anders

---

## 12) Nächste Aufgaben (ToDo)
- [ ] Gold Share Ordnerstruktur erstellen (servoy-2025.12.1.4123)
- [ ] Team-Plugins definieren und nach `files\` kopieren
- [ ] `build_manifest.py` schreiben
- [ ] `plugins_sync.py` schreiben (managed/unmanaged + quarantine)
- [ ] `start-servoy.cmd` schreiben
- [ ] 1 Dev testet (Dry Run), dann Rollout an alle
- [ ] V2: macOS/Linux Wrapper ergänzen
- [ ] V3: optional HTTP-Server statt SMB (nur Transport ändern)

---

## 13) Hinweis für Copilot in VS Code
Wenn du mit Copilot weiterarbeitest:
- Bitte dieses Dokument zuerst lesen.
- Implementierung zuerst für Windows (V1), macOS/Linux erst in V2.
- Script soll bei Fehlern warnen, aber Start nicht blockieren.
- Entfernen von Plugins nur für "Managed", und standardmäßig via Quarantäne (kein hard delete).