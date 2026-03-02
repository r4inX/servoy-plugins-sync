"""
plugins_sync.py – Servoy Gold Plugin Sync Client
=================================================
Synchronises managed plugins from the Gold Share into the local Servoy
plugins directory.  Private / unmanaged plugins are never touched.

First-time setup:
    python plugins_sync.py --init-config

Normal usage:
    python plugins_sync.py [--dry-run] [--verbose] [--config <path>]
    python plugins_sync.py --status

Config file (default: %USERPROFILE%\\.servoy-plugin-sync.json):
    {
        "gold_root":       "K:\\\\SERVOY_GOLD\\\\",
        "servoy_home":     "C:\\\\servoys\\\\2025.12.1.4123\\\\",
        "servoy_version":  "2025.12.1.4123",
        "mode":            "quarantine",  // optional, default = quarantine
        "private_plugins": ["hvo-pdf.jar", "my-team/*"]  // optional
    }

Exit codes:
    0  – fully successful
    1  – fatal error (config missing / unreadable, manifest missing, etc.)
    2  – completed with warnings / partial failures
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import logging
import logging.handlers
import os
import shutil
import sys
import tempfile
from datetime import date, datetime


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIG_FILENAME = ".servoy-plugin-sync.json"
STATE_FILENAME  = ".gold_sync_state.json"
LOG_FILENAME    = "gold_plugins_sync.log"


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

LOG_MAX_BYTES    = 2 * 1024 * 1024   # 2 MB per log file
LOG_BACKUP_COUNT = 3                  # keep gold_plugins_sync.log + .1 .2 .3


def setup_logging(log_path: str, verbose: bool) -> logging.Logger:
    """
    Configure a logger that writes to stdout AND a size-rotating log file.
    The log file is capped at 2 MB; up to 3 backups are kept automatically
    so the total disk usage stays below ~8 MB regardless of how often the
    sync runs.
    """
    logger = logging.getLogger("plugins_sync")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler – INFO by default, DEBUG if --verbose
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG if verbose else logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Rotating file handler – always DEBUG, max 2 MB × 3 backups
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError as exc:
        logger.warning(f"Cannot open log file '{log_path}': {exc} — file logging disabled.")

    return logger


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def default_config_path() -> str:
    profile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    return os.path.join(profile, CONFIG_FILENAME)


def load_config(path: str, logger: logging.Logger) -> dict:
    """Load and validate the user config JSON. Raises SystemExit(1) on failure."""
    if not os.path.isfile(path):
        logger.error(
            f"Config file not found: '{path}'\n"
            f"  Create it with keys: gold_root, servoy_home, servoy_version [, mode]"
        )
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error(f"Cannot read config '{path}': {exc}")
        sys.exit(1)

    required = ("gold_root", "servoy_home", "servoy_version")
    missing = [k for k in required if not cfg.get(k)]
    if missing:
        logger.error(f"Config '{path}' is missing required key(s): {', '.join(missing)}")
        sys.exit(1)

    cfg.setdefault("mode", "quarantine")
    cfg.setdefault("private_plugins", [])
    return cfg


# ---------------------------------------------------------------------------
# Paths helper
# ---------------------------------------------------------------------------

def resolve_paths(cfg: dict) -> dict:
    """
    Build all relevant absolute paths from the config.
    Returns a dict of path strings.
    """
    gold_root      = os.path.abspath(cfg["gold_root"])
    servoy_home    = os.path.abspath(cfg["servoy_home"])
    version        = cfg["servoy_version"]
    version_folder = f"servoy-{version}"

    gold_version_dir = os.path.join(gold_root, "plugins", version_folder)
    today            = date.today().isoformat()

    return {
        "gold_manifest":    os.path.join(gold_version_dir, "manifest.json"),
        "gold_files_dir":   os.path.join(gold_version_dir, "files"),
        "local_plugins_dir": os.path.join(servoy_home, "application_server", "plugins"),
        "quarantine_dir":   os.path.join(
            servoy_home, "application_server", "plugins__quarantine", today
        ),
        "state_file":       os.path.join(
            servoy_home, "application_server", "plugins", STATE_FILENAME
        ),
        "log_file":         os.path.join(
            servoy_home, "application_server", "plugins", LOG_FILENAME
        ),
    }


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def load_manifest(manifest_path: str, logger: logging.Logger) -> list[dict]:
    """
    Load manifest.json from the Gold Share.
    Returns list of file entries [{path, sha256, size}, ...].
    Raises SystemExit(1) on fatal errors (share unreachable, parse error).
    """
    if not os.path.exists(manifest_path):
        # Walk up the path tree to give a precise, tiered hint about what is wrong.
        # manifest  → <version_dir>/manifest.json
        # version_dir → <gold_root>/plugins/servoy-<version>/
        # plugins_dir → <gold_root>/plugins/
        # gold_root   → e.g. K:\SERVOY_GOLD\
        version_dir = os.path.dirname(manifest_path)
        plugins_dir = os.path.dirname(version_dir)
        gold_root   = os.path.dirname(plugins_dir)

        if not os.path.isdir(gold_root):
            hint = (
                f"  Gold Share root is not accessible: '{gold_root}'\n"
                f"  → Is the network drive mapped? (e.g. K:\\)\n"
                f"  → Try opening '{gold_root}' in Windows Explorer to verify.\n"
                f"  → If the drive letter differs, update 'gold_root' in your config."
            )
        elif not os.path.isdir(plugins_dir):
            hint = (
                f"  Gold Share is reachable but the 'plugins' folder is missing: '{plugins_dir}'\n"
                f"  → Ask the Gold Maintainer to initialise the share structure."
            )
        elif not os.path.isdir(version_dir):
            hint = (
                f"  'plugins' folder exists but no folder for this Servoy version: '{version_dir}'\n"
                f"  → Is 'servoy_version' in your config correct?\n"
                f"  → Ask the Gold Maintainer to create the version folder and run build_manifest.py."
            )
        else:
            hint = (
                f"  Version folder exists but manifest.json is missing.\n"
                f"  → Expected at: {manifest_path}\n"
                f"  → Has the Gold Maintainer run build_manifest.py for this version?"
            )

        logger.error(
            f"Cannot access Gold Share manifest: '{manifest_path}'\n"
            f"{hint}"
        )
        sys.exit(1)

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error(f"Cannot read manifest '{manifest_path}': {exc}")
        sys.exit(1)

    files = data.get("files")
    if not isinstance(files, list):
        logger.error(f"Manifest '{manifest_path}' has no 'files' list.")
        sys.exit(1)

    logger.debug(
        f"Manifest loaded: version={data.get('servoy_version')}, "
        f"generated_at={data.get('generated_at')}, "
        f"entries={len(files)}"
    )
    return files


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def load_state(state_file: str, logger: logging.Logger) -> set[str]:
    """
    Load previously managed paths from the state file.
    Returns a set of path strings (forward-slash, relative to plugins dir).
    Returns empty set if file does not exist (first run).
    """
    if not os.path.isfile(state_file):
        logger.debug("No previous state file found – treating as first run.")
        return set()
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        paths = set(data.get("managed_paths", []))
        logger.debug(f"State loaded: {len(paths)} previously managed path(s).")
        return paths
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(f"Cannot read state file '{state_file}': {exc} — treating as first run.")
        return set()


def save_state(state_file: str, managed_paths: set[str], logger: logging.Logger,
               dry_run: bool) -> None:
    """Persist the current set of managed paths to the state file."""
    if dry_run:
        logger.debug("[dry-run] Would write state file.")
        return
    data = {
        "updated_at":    datetime.now().isoformat(timespec="seconds"),
        "managed_paths": sorted(managed_paths),
    }
    tmp = state_file + ".tmp"
    try:
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp, state_file)
        logger.debug(f"State saved: {len(managed_paths)} managed path(s).")
    except OSError as exc:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        logger.warning(f"Cannot write state file '{state_file}': {exc}")


# ---------------------------------------------------------------------------
# SHA-256
# ---------------------------------------------------------------------------

def compute_sha256(filepath: str) -> str:
    """Compute SHA-256 of a file, reading in 64 KB chunks."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def file_needs_update(
    dst_abs: str,
    expected_sha: str,
    expected_size: int,
    logger: logging.Logger,
    rel_path: str,
) -> tuple[bool, str | None]:
    """
    Decide whether a managed plugin file needs to be installed or updated.

    Performance strategy – size-first pre-filter:
      1. File absent              → install  (no hashing needed)
      2. Size differs from manifest → update (no hashing needed; a different
         size guarantees different content, so SHA-256 would be redundant)
      3. Size matches             → compute SHA-256 as the definitive check
         (guards against files padded to the same length with different bytes)

    For a typical plugins folder this means SHA-256 is only computed when a
    file is up-to-date (sizes agree) or when a newer version happens to have
    the same byte-count – both rare for JARs, so most runs skip all hashing.

    Returns: (needs_action: bool, action: "install" | "update" | None)
    """
    if not os.path.exists(dst_abs):
        return True, "install"

    try:
        local_size = os.path.getsize(dst_abs)
    except OSError as exc:
        logger.warning(f"  WARNING: Cannot stat local file '{rel_path}': {exc}")
        return True, "update"   # conservative: assume stale

    if local_size != expected_size:
        logger.debug(
            f"  Size mismatch ({local_size} B local vs {expected_size} B manifest): {rel_path}"
        )
        return True, "update"

    # Sizes agree – full hash check required to be certain.
    try:
        local_sha = compute_sha256(dst_abs)
    except OSError as exc:
        logger.warning(f"  WARNING: Cannot hash local file '{rel_path}': {exc}")
        return True, "update"   # conservative

    if local_sha != expected_sha:
        logger.debug(f"  Hash mismatch (size={local_size} B): {rel_path}")
        return True, "update"

    return False, None


# ---------------------------------------------------------------------------
# Atomic copy
# ---------------------------------------------------------------------------

def atomic_copy(src: str, dst: str) -> None:
    """
    Copy src → dst atomically via a sibling .tmp file.
    Creates destination parent directories as needed.
    Raises OSError on failure.
    """
    parent = os.path.dirname(dst)
    if parent:                          # guard: dirname("") would raise on makedirs
        os.makedirs(parent, exist_ok=True)
    tmp = dst + ".tmp"
    try:
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
    except BaseException:
        # Clean up the .tmp file so it doesn't litter the plugins folder
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Quarantine helper
# ---------------------------------------------------------------------------

def move_to_quarantine(local_path: str, rel_path: str, quarantine_dir: str,
                       logger: logging.Logger, dry_run: bool) -> bool:
    """
    Move a single file from local_path to quarantine_dir / rel_path.
    Returns True on success, False on failure.
    """
    dest = os.path.join(quarantine_dir, rel_path.replace("/", os.sep))
    if dry_run:
        logger.info(f"  [dry-run] Would quarantine: {rel_path}")
        return True
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(local_path, dest)
        logger.info(f"  Quarantined: {rel_path}  →  {dest}")
        return True
    except PermissionError as exc:
        logger.warning(
            f"  WARNING: Cannot quarantine '{rel_path}' – file is locked: {exc}\n"
            f"  → Close Servoy completely and run the sync again."
        )
        return False
    except OSError as exc:
        logger.warning(
            f"  WARNING: Cannot quarantine '{rel_path}': {exc}\n"
            f"  → Close Servoy and retry if the file may be in use."
        )
        return False


# ---------------------------------------------------------------------------
# Servoy version detection
# ---------------------------------------------------------------------------

def detect_installed_version(servoy_home: str) -> str | None:
    """
    Detect the Servoy version installed in servoy_home.

    Strategy (most-reliable first):
      1. Scan developer/features/ for a directory named
         'com.servoy.eclipse.feature_<version>' and return <version>.
         This is the same information shown in Eclipse → About Servoy Developer.
      2. Read application_server/lib/version.txt – contains only the build
         number (e.g. '4123'), not the full semver string.  Returned as-is
         only when strategy 1 fails, so callers can use it as a partial match.

    Returns the version string, or None if nothing could be detected.
    """
    features_dir = os.path.join(servoy_home, "developer", "features")
    if os.path.isdir(features_dir):
        prefix = "com.servoy.eclipse.feature_"
        try:
            for entry in os.listdir(features_dir):
                if entry.startswith(prefix):
                    version = entry[len(prefix):]
                    if version:           # non-empty version suffix
                        return version
        except OSError:
            pass

    # Fallback: build-number only
    version_txt = os.path.join(servoy_home, "application_server", "lib", "version.txt")
    if os.path.isfile(version_txt):
        try:
            with open(version_txt, "r", encoding="utf-8") as f:
                return f.read().strip() or None
        except OSError:
            pass

    return None


def validate_versions(
    cfg_version:       str,
    manifest_version:  str | None,
    installed_version: str | None,
    logger:            logging.Logger,
) -> int:
    """
    Cross-check the three version sources and log warnings for mismatches.
    Returns the number of mismatches found (0 = all OK).

    Sources:
      cfg_version       – 'servoy_version' in the user config file
      manifest_version  – 'servoy_version' from manifest.json on the share
      installed_version – detected from developer/features/ on disk
    """
    issues = 0

    if manifest_version and manifest_version != cfg_version:
        logger.warning(
            f"Version mismatch – manifest says '{manifest_version}' "
            f"but config says '{cfg_version}'.\n"
            f"  → Update 'servoy_version' in your config, or ask the Gold Maintainer "
            f"to regenerate the manifest."
        )
        issues += 1

    if installed_version:
        # Full version match (e.g. '2025.12.1.4123' == '2025.12.1.4123')
        if installed_version == cfg_version:
            logger.debug(f"Installed version matches config: {installed_version}")
        # Build-number-only match (version.txt fallback gives just '4123')
        elif cfg_version.endswith(installed_version):
            logger.debug(
                f"Installed build '{installed_version}' matches suffix of "
                f"config version '{cfg_version}'."
            )
        else:
            logger.warning(
                f"Installed Servoy version '{installed_version}' does not match "
                f"config version '{cfg_version}'.\n"
                f"  → Is servoy_home pointing to the right installation?\n"
                f"  → Update 'servoy_version' in your config if you upgraded Servoy."
            )
            issues += 1
    else:
        logger.debug("Could not detect installed Servoy version – skipping version check.")

    return issues


# ---------------------------------------------------------------------------
# Private-plugin pattern matching
# ---------------------------------------------------------------------------

def is_private(rel_path: str, private_patterns: list[str]) -> bool:
    """
    Return True if *rel_path* matches any pattern in *private_patterns*.

    Patterns use :mod:`fnmatch` syntax, e.g.::

        "hvo-pdf.jar"   – exact filename anywhere in the plugins dir
        "ai/*"          – all files inside the ai/ subfolder
        "dev-*.jar"     – any jar whose name starts with dev-
    """
    for pattern in private_patterns:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
    return False


# ---------------------------------------------------------------------------
# Status report  (--status)
# ---------------------------------------------------------------------------

def status_report(
    cfg:     dict,
    paths:   dict,
    logger:  logging.Logger,
) -> int:
    """
    Print a human-readable summary of the current plugin state WITHOUT making
    any changes.  Returns exit code (0 = all OK, 2 = issues found).
    """
    issues = 0
    SEP = "-" * 62

    print()
    print("=" * 62)
    print(" Servoy Gold Plugin Sync – Status Report")
    print("=" * 62)

    # ---- Version info -------------------------------------------------- #
    cfg_version = cfg["servoy_version"]
    installed   = detect_installed_version(cfg["servoy_home"])
    inst_str    = installed if installed else "(could not detect)"
    inst_ok     = installed and (installed == cfg_version or cfg_version.endswith(installed))
    inst_mark   = "✓" if inst_ok else ("!" if installed else "?")

    print(f"\n  Config version (servoy_version): {cfg_version}")
    print(f"  Installed version (detected):    {inst_str}  [{inst_mark}]")
    if not inst_ok and installed:
        print(f"  WARNING: Installed version does not match config version!")
        issues += 1

    # ---- Manifest ------------------------------------------------------ #
    if not os.path.exists(paths["gold_manifest"]):
        print(f"\n  Gold Share manifest: NOT ACCESSIBLE")
        print(f"  Expected: {paths['gold_manifest']}")
        print(f"  → Is the Gold Share mounted/mapped?")
        print()
        return 1

    try:
        with open(paths["gold_manifest"], "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"\n  ERROR reading manifest: {exc}")
        return 1

    mf_version  = manifest_data.get("servoy_version", "?")
    mf_date     = manifest_data.get("generated_at", "?")
    mf_entries  = manifest_data.get("files", [])
    mf_ok       = mf_version == cfg_version
    mf_mark     = "✓" if mf_ok else "!"

    print(f"  Manifest version:                {mf_version}  [{mf_mark}]")
    print(f"  Manifest generated:              {mf_date}")
    if not mf_ok:
        print(f"  WARNING: Manifest version does not match config version!")
        issues += 1

    # ---- Plugin-by-plugin status --------------------------------------- #
    print(f"\n  {SEP}")
    print(f"  {'PATH':<42} STATUS")
    print(f"  {SEP}")

    local_plugins_dir = paths["local_plugins_dir"]
    col = 42

    for entry in mf_entries:
        rel_path     = entry["path"]
        expected_sha = entry["sha256"]
        expected_size = entry.get("size", -1)
        dst_abs = os.path.join(local_plugins_dir, rel_path.replace("/", os.sep))

        if not os.path.exists(dst_abs):
            status = "MISSING  → will be installed on next sync"
            issues += 1
        else:
            local_size = os.path.getsize(dst_abs)
            if local_size != expected_size:
                status = f"OUTDATED (size {local_size} B → {expected_size} B)"
                issues += 1
            else:
                local_sha = compute_sha256(dst_abs)
                if local_sha != expected_sha:
                    status = "OUTDATED (hash mismatch, same size)"
                    issues += 1
                else:
                    status = "OK"

        label = rel_path if len(rel_path) <= col else "…" + rel_path[-(col - 1):]
        print(f"  {label:<{col}} {status}")

    # ---- State: will-be-quarantined ------------------------------------ #
    previous_managed = load_state(paths["state_file"], logger)
    current_manifest_paths = {e["path"] for e in mf_entries}
    to_quarantine = previous_managed - current_manifest_paths

    if to_quarantine:
        print(f"\n  {SEP}")
        print("  Previously managed, will be QUARANTINED on next sync:")
        print(f"  {SEP}")
        for p in sorted(to_quarantine):
            local_abs = os.path.join(local_plugins_dir, p.replace("/", os.sep))
            exists = "(present)" if os.path.exists(local_abs) else "(already gone)"
            print(f"  {p}  {exists}")
        issues += len([p for p in to_quarantine
                       if os.path.exists(os.path.join(local_plugins_dir, p.replace("/", os.sep)))])

    # ---- Unmanaged plugins: explicitly private vs. orphaned ------------ #
    private_patterns      = cfg.get("private_plugins", [])
    all_managed_and_state = current_manifest_paths | previous_managed
    explicitly_private    = []
    orphaned              = []
    for root, _dirs, files in os.walk(local_plugins_dir):
        for fname in files:
            abs_path = os.path.join(root, fname)
            rel = os.path.relpath(abs_path, local_plugins_dir).replace(os.sep, "/")
            # Skip internal files
            if rel in (STATE_FILENAME, LOG_FILENAME) or rel.endswith(".log"):
                continue
            if rel in all_managed_and_state:
                continue
            if is_private(rel, private_patterns):
                explicitly_private.append(rel)
            else:
                orphaned.append(rel)

    if orphaned:
        print(f"\n  {SEP}")
        print("  Orphaned plugins (not in manifest, not private) – will be QUARANTINED on next sync:")
        print(f"  {SEP}")
        for p in sorted(orphaned):
            print(f"  {p}")
        issues += len(orphaned)

    if explicitly_private:
        print(f"\n  {SEP}")
        print("  Private plugins (explicitly protected – will never be touched):")
        print(f"  {SEP}")
        for p in sorted(explicitly_private):
            print(f"  {p}")

    print(f"\n  {SEP}")
    summary = "ALL OK" if issues == 0 else f"{issues} ISSUE(S) FOUND"
    print(f"  Summary: {summary}")
    print(f"  {SEP}")
    print()

    return 0 if issues == 0 else 2


# ---------------------------------------------------------------------------
# Core sync logic
# ---------------------------------------------------------------------------


def sync(
    manifest_entries: list[dict],
    gold_files_dir:   str,
    local_plugins_dir: str,
    quarantine_dir:   str,
    state_file:       str,
    previous_managed: set[str],
    private_patterns: list[str],
    logger:           logging.Logger,
    dry_run:          bool,
) -> tuple[int, set[str]]:
    """
    Perform the full sync operation.

    Returns:
        (warning_count, new_managed_paths)
    """
    warnings = 0
    current_manifest_paths: set[str] = {e["path"] for e in manifest_entries}

    # ------------------------------------------------------------------ #
    # 1. Install / Update managed plugins                                 #
    # ------------------------------------------------------------------ #
    logger.info("=== Phase 1: Install / Update managed plugins ===")

    for entry in manifest_entries:
        rel_path  = entry["path"]          # forward-slash relative
        expected_sha = entry["sha256"]
        src_abs   = os.path.join(gold_files_dir, rel_path.replace("/", os.sep))
        dst_abs   = os.path.join(local_plugins_dir, rel_path.replace("/", os.sep))

        # Verify source exists on share
        if not os.path.isfile(src_abs):
            logger.warning(
                f"  WARNING: Source file missing on Gold Share: '{rel_path}'\n"
                f"  Expected at: {src_abs}"
            )
            warnings += 1
            continue

        # Decide action – size-first fast path (see file_needs_update docstring)
        needs_action, action = file_needs_update(
            dst_abs, expected_sha, entry.get("size", -1), logger, rel_path
        )
        if not needs_action:
            logger.debug(f"  OK (up-to-date): {rel_path}")
            continue

        # Execute action
        if dry_run:
            logger.info(f"  [dry-run] Would {action}: {rel_path}")
        else:
            try:
                atomic_copy(src_abs, dst_abs)
                verb = "Installed" if action == "install" else "Updated"
                logger.info(f"  {verb}: {rel_path}")
            except PermissionError as exc:
                logger.warning(
                    f"  WARNING: Cannot {action} '{rel_path}' – file is locked: {exc}\n"
                    f"  → Close Servoy completely and run the sync again."
                )
                warnings += 1
            except OSError as exc:
                logger.warning(
                    f"  WARNING: Cannot {action} '{rel_path}': {exc}\n"
                    f"  → Close Servoy and retry if the file may be in use."
                )
                warnings += 1


    # ------------------------------------------------------------------ #
    # 2. Quarantine: previously managed, now removed from manifest        #
    # ------------------------------------------------------------------ #
    logger.info("=== Phase 2: Quarantine removed managed plugins ===")

    removed_paths = previous_managed - current_manifest_paths
    if not removed_paths:
        logger.info("  Nothing to quarantine.")
    else:
        for rel_path in sorted(removed_paths):
            local_abs = os.path.join(local_plugins_dir, rel_path.replace("/", os.sep))
            if not os.path.exists(local_abs):
                logger.debug(f"  Already gone (skip quarantine): {rel_path}")
                continue
            ok = move_to_quarantine(
                local_abs, rel_path, quarantine_dir, logger, dry_run
            )
            if not ok:
                warnings += 1

    # ------------------------------------------------------------------ #
    # 3. Quarantine orphaned plugins (present locally, not in manifest,   #
    #    not previously managed, not in private_patterns)                 #
    # ------------------------------------------------------------------ #
    logger.info("=== Phase 3: Quarantine orphaned plugins ===")
    orphan_found = False
    for root, _dirs, files in os.walk(local_plugins_dir):
        for fname in files:
            abs_path = os.path.join(root, fname)
            rel = os.path.relpath(abs_path, local_plugins_dir).replace(os.sep, "/")
            if rel in (STATE_FILENAME, LOG_FILENAME) or rel.endswith(".log"):
                continue
            if rel in current_manifest_paths:
                continue   # handled by Phase 1
            if rel in previous_managed:
                continue   # handled by Phase 2
            if is_private(rel, private_patterns):
                logger.debug(f"  Private (skip): {rel}")
                continue
            orphan_found = True
            ok = move_to_quarantine(abs_path, rel, quarantine_dir, logger, dry_run)
            if not ok:
                warnings += 1
    if not orphan_found:
        logger.info("  No orphaned plugins found.")

    logger.info("=== Sync complete ===")
    return warnings, current_manifest_paths


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Interactive config wizard  (--init-config)
# ---------------------------------------------------------------------------

def _ask(
    prompt:    str,
    default:   str | None = None,
    validator: "Callable[[str], str | None] | None" = None,
    allow_empty: bool = False,
) -> str:
    """
    Print *prompt*, optionally show a default, then read one line from stdin.
    *validator* receives the (stripped) answer and must return either:
      - None  → answer is accepted
      - str   → error message to display; the question is asked again
    """
    if default:
        display = f"{prompt} [{default}]: "
    else:
        display = f"{prompt}: "

    while True:
        try:
            raw = input(display).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(1)

        value = raw if raw else (default or "")
        if not value and not allow_empty:
            print("  ✗  This field is required.")
            continue

        if validator:
            err = validator(value)
            if err:
                print(f"  ✗  {err}")
                continue

        return value


def _validate_servoy_home(path: str) -> str | None:
    path = os.path.expandvars(path)
    if not os.path.isdir(path):
        return f"Directory not found: {path}"
    plugins_dir = os.path.join(path, "application_server", "plugins")
    if not os.path.isdir(plugins_dir):
        return (
            f"'{path}' does not look like a Servoy installation\n"
            f"  (expected sub-folder: application_server{os.sep}plugins)"
        )
    return None


def _validate_gold_root(path: str) -> str | None:
    path = os.path.expandvars(path)
    if not os.path.isdir(path):
        return f"Directory not found or not accessible: {path}"
    return None


def _validate_servoy_version(version: str) -> str | None:
    if not version.strip():
        return "Version must not be empty."
    # Accept any non-empty string; we warn later if manifest can't be reached.
    return None


def init_config(config_path: str) -> int:
    """
    Interactive wizard that creates (or overwrites) the user config file.
    Returns an exit code (0 = success, 1 = aborted / error).
    """
    SEP = "-" * 60

    print()
    print("=" * 60)
    print(" Servoy Gold Plugin Sync – Config Setup Wizard")
    print("=" * 60)
    print(f"  Target file: {config_path}")
    print()

    # ---- Check for existing config ------------------------------------- #
    if os.path.isfile(config_path):
        print(f"  A config file already exists at:")
        print(f"  {config_path}")
        try:
            answer = input("  Overwrite it? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return 1
        if answer not in ("y", "yes"):
            print("  Keeping existing config. Nothing changed.")
            return 0
        print()

    # ---- Step 1: servoy_home ------------------------------------------- #
    print(SEP)
    print(" Step 1/5 – Servoy installation folder (servoy_home)")
    print(SEP)
    print("  The root folder of your local Servoy installation.")
    print("  It must contain the sub-folder application_server/plugins.")
    print("  Example: C:\\Servoys\\2025.12.1.4123")
    print()

    servoy_home_raw = _ask(
        "  servoy_home",
        validator=lambda p: _validate_servoy_home(os.path.expandvars(p)),
    )
    servoy_home = os.path.expandvars(servoy_home_raw)

    # Auto-detect version
    detected_version = detect_installed_version(servoy_home)
    if detected_version:
        print(f"  ✓  Detected installed version: {detected_version}")
    else:
        print("  ⚠  Could not auto-detect the Servoy version from this folder.")
    print()

    # ---- Step 2: gold_root --------------------------------------------- #
    print(SEP)
    print(" Step 2/5 – Gold Share root folder (gold_root)")
    print(SEP)
    print("  The root of the shared folder maintained by the Gold Maintainer.")
    print("  Example: K:\\SERVOY_GOLD  or  \\\\server\\share\\SERVOY_GOLD")
    print()

    gold_root_raw = _ask(
        "  gold_root",
        validator=lambda p: _validate_gold_root(os.path.expandvars(p)),
    )
    gold_root = os.path.expandvars(gold_root_raw)
    plugins_share_dir = os.path.join(gold_root, "plugins")
    if os.path.isdir(plugins_share_dir):
        print(f"  ✓  'plugins' sub-folder found on share.")
    else:
        print(f"  ⚠  Sub-folder 'plugins' not found under '{gold_root}'.")
        print( "     This is expected if the Gold Maintainer hasn't set it up yet.")
    print()

    # ---- Step 3: servoy_version ---------------------------------------- #
    print(SEP)
    print(" Step 3/5 – Servoy version (servoy_version)")
    print(SEP)
    print("  Must match exactly what the Gold Maintainer uses in the share.")
    print("  Format: YYYY.M.P.BBBB  e.g. 2025.12.1.4123")
    print()

    version = _ask(
        "  servoy_version",
        default=detected_version,
        validator=_validate_servoy_version,
    )
    version = version.strip()

    # Check if manifest is reachable
    manifest_path = os.path.join(gold_root, "plugins", f"servoy-{version}", "manifest.json")
    if os.path.isfile(manifest_path):
        print(f"  ✓  manifest.json found on share – version matches the Gold Share.")
    else:
        print(f"  ⚠  manifest.json not found at:")
        print(f"       {manifest_path}")
        print( "     This may be OK if the share isn't set up yet, or you're offline.")
    print()

    # ---- Step 4: mode -------------------------------------------------- #
    print(SEP)
    print(" Step 4/5 – Plugin removal mode (mode)")
    print(SEP)
    print("  What should happen to managed plugins that are no longer in the manifest?")
    print("    quarantine  – move them to plugins__quarantine/YYYY-MM-DD/  (recommended)")
    print("    delete      – permanently delete them (no recovery)")
    print()

    mode = _ask(
        "  mode",
        default="quarantine",
        validator=lambda m: None if m in ("quarantine", "delete")
                            else "Enter 'quarantine' or 'delete'.",
    )
    print()

    # ---- Step 5: private_plugins --------------------------------------- #
    print(SEP)
    print(" Step 5/5 \u2013 Private plugin patterns (private_plugins)  [optional]")
    print(SEP)
    print("  Plugins matching these patterns will NEVER be touched by the sync,")
    print("  even if they are not in the manifest. Useful for plugins you are")
    print("  developing locally or that are specific to your machine.")
    print()
    print("  Enter fnmatch-style patterns, separated by commas.")
    print("  Examples:  hvo-pdf.jar")
    print("             my-team/*")
    print("             dev-*.jar, drafts/*")
    print("  Leave blank if you have no private plugins.")
    print()

    private_raw = _ask("  private_plugins (comma-separated)", default="", allow_empty=True)
    if private_raw.strip():
        private_plugins = [p.strip() for p in private_raw.split(",") if p.strip()]
    else:
        private_plugins = []
    print()

    # ---- Summary + confirm --------------------------------------------- #
    cfg = {
        "gold_root":       gold_root_raw,
        "servoy_home":     servoy_home_raw,
        "servoy_version":  version,
        "mode":            mode,
        "private_plugins": private_plugins,
    }

    print(SEP)
    print(" Summary – config to be written:")
    print(SEP)
    print(json.dumps(cfg, indent=2, ensure_ascii=False))
    print(f"  Target: {config_path}")
    print()

    try:
        answer = input("  Write this config? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        return 1

    if answer in ("n", "no"):
        print("  Aborted – nothing written.")
        return 1

    # ---- Write config -------------------------------------------------- #
    try:
        os.makedirs(os.path.dirname(config_path) or ".", exist_ok=True)
        tmp = config_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, config_path)
    except OSError as exc:
        print(f"  ERROR: Could not write '{config_path}': {exc}")
        return 1

    print(f"  ✓  Config written to: {config_path}")
    print( "  Run 'python plugins_sync.py --status' to verify the setup.")
    print()
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync managed plugins from Gold Share to local Servoy installation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python plugins_sync.py --init-config
  python plugins_sync.py
  python plugins_sync.py --status
  python plugins_sync.py --dry-run --verbose
  python plugins_sync.py --config "D:\\myconfig.json"
""",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help=(
            "Path to the user config JSON. "
            f"Default: %%USERPROFILE%%\\{CONFIG_FILENAME}"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be done without making any changes.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show DEBUG-level messages.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help=(
            "Show current plugin status (installed / outdated / missing) "
            "without making any changes. Exits 0 if everything is up-to-date, "
            "2 if there are issues."
        ),
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help=(
            "Interactive wizard: asks for servoy_home, gold_root, version, mode, "
            "validates each answer, and writes the config file. "
            "Use --config to specify a non-default target path."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    config_path = args.config or default_config_path()

    # Bootstrap logger with a temporary stderr handler until we know the log path
    bootstrap_logger = logging.getLogger("plugins_sync")
    if not bootstrap_logger.handlers:
        bootstrap_logger.setLevel(logging.DEBUG)
        _bch = logging.StreamHandler(sys.stdout)
        _bch.setLevel(logging.DEBUG if args.verbose else logging.INFO)
        _bch.setFormatter(logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        ))
        bootstrap_logger.addHandler(_bch)

    logger = bootstrap_logger

    # ---- --init-config: run wizard and exit ----------------------------- #
    if args.init_config:
        return init_config(config_path)

    if args.dry_run:
        logger.info("*** DRY-RUN mode – no changes will be made ***")

    # --- Load config ------------------------------------------------------ #
    cfg   = load_config(config_path, logger)
    paths = resolve_paths(cfg)

    # --- Re-init logger now that we know the log file path --------------- #
    for h in logger.handlers[:]:
        logger.removeHandler(h)
    logger = setup_logging(paths["log_file"], args.verbose)

    # ---- --status: show report and exit --------------------------------- #
    if args.status:
        return status_report(cfg, paths, logger)

    logger.info(f"Config:          {config_path}")
    logger.info(f"Gold manifest:   {paths['gold_manifest']}")
    logger.info(f"Gold files dir:  {paths['gold_files_dir']}")
    logger.info(f"Local plugins:   {paths['local_plugins_dir']}")
    logger.info(f"State file:      {paths['state_file']}")
    if args.dry_run:
        logger.info("Mode:            DRY-RUN")
    else:
        logger.info(f"Mode:            {cfg['mode']}")

    # --- Detect + validate installed Servoy version ---------------------- #
    installed_version = detect_installed_version(cfg["servoy_home"])
    if installed_version:
        logger.info(f"Installed Servoy: {installed_version}")
    else:
        logger.debug("Installed Servoy version could not be detected.")

    # --- Ensure local plugins dir exists --------------------------------- #
    if not os.path.isdir(paths["local_plugins_dir"]):
        logger.error(
            f"Local plugins directory does not exist: '{paths['local_plugins_dir']}'\n"
            f"  Check 'servoy_home' in your config."
        )
        return 1

    # --- Load manifest ---------------------------------------------------- #
    manifest_entries = load_manifest(paths["gold_manifest"], logger)

    # --- Validate versions ----------------------------------------------- #
    manifest_version = None
    try:
        with open(paths["gold_manifest"], "r", encoding="utf-8") as f:
            manifest_version = json.load(f).get("servoy_version")
    except (OSError, json.JSONDecodeError):
        pass   # already loaded above; errors caught there
    validate_versions(cfg["servoy_version"], manifest_version, installed_version, logger)

    # --- Load previous state ---------------------------------------------- #
    previous_managed = load_state(paths["state_file"], logger)

    # --- Run sync --------------------------------------------------------- #
    try:
        warnings, new_managed = sync(
            manifest_entries  = manifest_entries,
            gold_files_dir    = paths["gold_files_dir"],
            local_plugins_dir = paths["local_plugins_dir"],
            quarantine_dir    = paths["quarantine_dir"],
            state_file        = paths["state_file"],
            previous_managed  = previous_managed,
            private_patterns  = cfg.get("private_plugins", []),
            logger            = logger,
            dry_run           = args.dry_run,
        )
    except Exception as exc:                 # unexpected / unhandled
        logger.error(f"Unexpected error during sync: {exc}", exc_info=True)
        return 1

    # --- Persist state ---------------------------------------------------- #
    save_state(paths["state_file"], new_managed, logger, dry_run=args.dry_run)

    # --- Summary ---------------------------------------------------------- #
    if warnings == 0:
        logger.info(f"Result: SUCCESS (0 warnings)")
        return 0
    else:
        logger.warning(
            f"Result: COMPLETED WITH {warnings} WARNING(S) — "
            f"check log: {paths['log_file']}"
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
