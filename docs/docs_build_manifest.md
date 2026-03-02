# build_manifest.py – Reference

## Purpose

`build_manifest.py` is a tool for the **Gold Maintainer** (the person responsible
for maintaining the central plugin baseline).

It recursively scans a `files/` folder on the Gold Share and generates a
`manifest.json` file that contains the relative path, file size (bytes), and
SHA-256 hash for each plugin file.

The manifest is the **source of truth** for `plugins_sync.py`: only entries
listed in the manifest are treated as managed plugins.

---

## Prerequisites

- Python 3.10 or newer
- No external packages required (standard library only)

---

## Usage

```
python build_manifest.py --files-dir "<path to files folder>" --out "<path to manifest.json>" --servoy-version "<version>"
```

### Parameters

| Parameter | Required | Description |
|---|---|---|
| `--files-dir` | Yes | Path to the `files/` folder containing the plugin files |
| `--out` | Yes | Output path for the generated `manifest.json` |
| `--servoy-version` | Yes | Servoy version string, e.g. `2025.12.1.4123` |
| `--self-test` | No | Run the built-in self-test and exit |

---

## Examples

### Generate a manifest for Servoy 2025.12.1.4123 (Windows)

```cmd
python build_manifest.py ^
    --files-dir "K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\files" ^
    --out       "K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\manifest.json" ^
    --servoy-version "2025.12.1.4123"
```

Expected output:

```
Scanning 'K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\files' …
  Found 12 file(s).
Writing manifest to 'K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\manifest.json' …
Done. Manifest written (12 entries, version=2025.12.1.4123).
```

### Run the self-test

```cmd
python build_manifest.py --self-test
```

Expected output:

```
Running self-test …
Self-test PASSED – all assertions OK.
```

### Show help

```cmd
python build_manifest.py --help
```

---

## Generated manifest.json – structure

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

**Notes:**
- `path` always uses **forward slashes** (`/`), even on Windows.
- Entries are **sorted alphabetically by `path`** (deterministic, good for Git diffs).
- The manifest is first written as a `.tmp` file and then atomically renamed —
  a half-written manifest is never possible.

---

## Error handling & exit codes

| Exit code | Meaning |
|---|---|
| `0` | Completed successfully |
| `1` | Runtime error (e.g. `files-dir` does not exist, file unreadable, write error) |
| `2` | Missing required arguments |

Error messages are written to `stderr`, e.g.:

```
ERROR: files-dir does not exist or is not a directory: 'K:\SERVOY_GOLD\plugins\servoy-2025.12.1.4123\files'
```

---

## Typical workflow (Gold Maintainer)

1. Place or update plugin files in `K:\SERVOY_GOLD\plugins\servoy-<VERSION>\files\`.
2. Run `build_manifest.py` — generates a new `manifest.json`.
3. Optional: briefly update `CHANGELOG.md` on the share (what changed and why).
4. All developers automatically receive the new plugin state on their next
   Servoy launch via `plugins_sync.py`.

---

## Self-test – what is verified?

`--self-test` creates a temporary folder with two synthetic files:

- `alpha.jar` (flat)
- `subfolder/beta.jar` (in a sub-folder)

It then checks:

- Manifest contains exactly 2 entries
- Sort order is correct (`alpha.jar` before `subfolder/beta.jar`)
- SHA-256 hashes are correct (compared against known values)
- File sizes are correct
- Paths use only forward slashes
- `generated_at` equals today's date
- The temp folder is always cleaned up (even on error)
