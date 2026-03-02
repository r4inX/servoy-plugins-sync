"""
build_manifest.py – Gold Share Manifest Generator
==================================================
Usage:
    python build_manifest.py --files-dir "<path>" --out "<manifest.json>" --servoy-version "2025.12.1.4123"
    python build_manifest.py --self-test

Generates a manifest.json from all files under --files-dir,
containing sha256, size, and relative path for each file.
No external dependencies required.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import date


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def compute_sha256(filepath: str) -> str:
    """Compute SHA-256 hex digest of a file, reading in chunks."""
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except OSError as exc:
        raise RuntimeError(f"Cannot read file '{filepath}': {exc}") from exc
    return h.hexdigest()


def collect_files(files_dir: str) -> list[dict]:
    """
    Recursively collect all files under files_dir.
    Returns a list of dicts sorted by 'path'.
    """
    entries = []
    files_dir = os.path.abspath(files_dir)

    for root, _dirs, files in os.walk(files_dir):
        for filename in files:
            abs_path = os.path.join(root, filename)
            # Relative path with forward slashes (as required by manifest spec)
            rel_path = os.path.relpath(abs_path, files_dir).replace(os.sep, "/")
            try:
                size = os.path.getsize(abs_path)
            except OSError as exc:
                raise RuntimeError(
                    f"Cannot stat file '{abs_path}': {exc}"
                ) from exc
            sha256 = compute_sha256(abs_path)
            entries.append({
                "path": rel_path,
                "sha256": sha256,
                "size": size,
            })

    # Deterministic output: sort by path
    entries.sort(key=lambda e: e["path"])
    return entries


def build_manifest(files_dir: str, servoy_version: str) -> dict:
    """Build the manifest dict from a files directory."""
    if not os.path.isdir(files_dir):
        raise RuntimeError(f"files-dir does not exist or is not a directory: '{files_dir}'")

    files = collect_files(files_dir)
    return {
        "servoy_version": servoy_version,
        "generated_at": date.today().isoformat(),
        "files": files,
    }


def write_manifest(manifest: dict, out_path: str) -> None:
    """Write manifest as pretty-printed JSON to out_path (creates parent dirs)."""
    out_path = os.path.abspath(out_path)
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    tmp_path = out_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            f.write("\n")
        # Atomic replace
        os.replace(tmp_path, out_path)
    except OSError as exc:
        # Clean up temp file if it exists
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise RuntimeError(f"Cannot write manifest to '{out_path}': {exc}") from exc


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def run_self_test() -> None:
    """
    Self-test: creates a temp directory with 2 files, generates a manifest,
    and verifies structure and content.
    """
    print("Running self-test …")
    tmp_dir = tempfile.mkdtemp(prefix="build_manifest_test_")
    try:
        files_dir = os.path.join(tmp_dir, "files")
        os.makedirs(files_dir)

        # Create two test files with known content
        file1 = os.path.join(files_dir, "alpha.jar")
        file2_dir = os.path.join(files_dir, "subfolder")
        os.makedirs(file2_dir)
        file2 = os.path.join(file2_dir, "beta.jar")

        content1 = b"fake jar content alpha"
        content2 = b"fake jar content beta longer"
        with open(file1, "wb") as f:
            f.write(content1)
        with open(file2, "wb") as f:
            f.write(content2)

        expected_sha1 = hashlib.sha256(content1).hexdigest()
        expected_sha2 = hashlib.sha256(content2).hexdigest()

        manifest_path = os.path.join(tmp_dir, "manifest.json")
        servoy_version = "2025.12.1.TEST"

        # Generate manifest
        manifest = build_manifest(files_dir, servoy_version)
        write_manifest(manifest, manifest_path)

        # Read back from disk
        with open(manifest_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        # --- Assertions ---
        assert loaded["servoy_version"] == servoy_version, \
            f"servoy_version mismatch: {loaded['servoy_version']}"

        assert loaded["generated_at"] == date.today().isoformat(), \
            f"generated_at mismatch: {loaded['generated_at']}"

        assert len(loaded["files"]) == 2, \
            f"Expected 2 file entries, got {len(loaded['files'])}"

        # Sorted order: alpha.jar < subfolder/beta.jar
        entry_alpha = loaded["files"][0]
        entry_beta  = loaded["files"][1]

        assert entry_alpha["path"] == "alpha.jar", \
            f"Unexpected path: {entry_alpha['path']}"
        assert entry_beta["path"] == "subfolder/beta.jar", \
            f"Unexpected path: {entry_beta['path']}"

        assert entry_alpha["sha256"] == expected_sha1, \
            f"sha256 mismatch for alpha.jar"
        assert entry_beta["sha256"] == expected_sha2, \
            f"sha256 mismatch for beta.jar"

        assert entry_alpha["sha256"] != "", "sha256 must not be empty"
        assert entry_beta["sha256"] != "",  "sha256 must not be empty"

        assert entry_alpha["size"] == len(content1), \
            f"size mismatch for alpha.jar: {entry_alpha['size']}"
        assert entry_beta["size"] == len(content2), \
            f"size mismatch for beta.jar: {entry_beta['size']}"

        # Forward slashes only in paths
        for entry in loaded["files"]:
            assert "\\" not in entry["path"], \
                f"Path must use forward slashes: {entry['path']}"

        print("Self-test PASSED – all assertions OK.")

    except AssertionError as exc:
        print(f"Self-test FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Gold Share manifest.json from a files/ directory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build_manifest.py \\
      --files-dir "K:\\SERVOY_GOLD\\plugins\\servoy-2025.12.1.4123\\files" \\
      --out       "K:\\SERVOY_GOLD\\plugins\\servoy-2025.12.1.4123\\manifest.json" \\
      --servoy-version "2025.12.1.4123"

  python build_manifest.py --self-test
""",
    )
    parser.add_argument(
        "--files-dir",
        metavar="PATH",
        help="Directory containing the plugin files to include in the manifest.",
    )
    parser.add_argument(
        "--out",
        metavar="PATH",
        help="Output path for the generated manifest.json.",
    )
    parser.add_argument(
        "--servoy-version",
        metavar="VERSION",
        help='Servoy version string, e.g. "2025.12.1.4123".',
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run built-in self-test and exit.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.self_test:
        run_self_test()
        return 0

    # Validate required args when not in self-test mode
    missing = []
    if not args.files_dir:
        missing.append("--files-dir")
    if not args.out:
        missing.append("--out")
    if not args.servoy_version:
        missing.append("--servoy-version")
    if missing:
        print(
            f"ERROR: Missing required argument(s): {', '.join(missing)}\n"
            "Use --help for usage information.",
            file=sys.stderr,
        )
        return 2

    try:
        print(f"Scanning '{args.files_dir}' …")
        manifest = build_manifest(args.files_dir, args.servoy_version)
        file_count = len(manifest["files"])
        print(f"  Found {file_count} file(s).")

        print(f"Writing manifest to '{args.out}' …")
        write_manifest(manifest, args.out)
        print(f"Done. Manifest written ({file_count} entries, version={args.servoy_version}).")
        return 0

    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
