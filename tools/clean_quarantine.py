#!/usr/bin/env python3
"""
clean_quarantine.py – Remove old date-stamped quarantine folders.

By default any subfolder under  application_server/plugins__quarantine/
whose name is a date (YYYY-MM-DD) that is older than --older-than-days days
is permanently removed.

Usage:
    python clean_quarantine.py               # defaults: 30 days, real run
    python clean_quarantine.py --dry-run     # list what would be deleted
    python clean_quarantine.py --older-than-days 90
    python clean_quarantine.py --config "D:\\myconfig.json"

The config file is the same ~/.servoy-plugin-sync.json used by plugins_sync.py.
Only the 'servoy_home' key is required.

Exit codes:
  0  – success (nothing to do counts as success)
  1  – fatal error (config missing, path not found, …)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

QUARANTINE_DIRNAME = "plugins__quarantine"
CONFIG_FILENAME    = ".servoy-plugin-sync.json"
DATE_FMT           = "%Y-%m-%d"


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def default_config_path() -> str:
    return os.path.join(os.path.expanduser("~"), CONFIG_FILENAME)


def load_config(path: str | None, logger: logging.Logger) -> dict:
    path = path or default_config_path()
    if not os.path.isfile(path):
        logger.error(
            f"Config file not found: {path}\n"
            f"  → Create '{CONFIG_FILENAME}' in your home directory.\n"
            f"  → See docs/example.servoy-plugin-sync.json for a template."
        )
        sys.exit(1)
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except json.JSONDecodeError as exc:
        logger.error(f"Cannot parse config file '{path}': {exc}")
        sys.exit(1)

    if "servoy_home" not in cfg:
        logger.error(
            f"Config '{path}' is missing required key 'servoy_home'.\n"
            f"  → Check docs/example.servoy-plugin-sync.json."
        )
        sys.exit(1)
    return cfg


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(verbose: bool) -> logging.Logger:
    logger = logging.getLogger("clean_quarantine")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s"))
    logger.addHandler(handler)
    return logger


# ---------------------------------------------------------------------------
# Core cleanup
# ---------------------------------------------------------------------------

def clean_quarantine(
    quarantine_dir: str,
    cutoff_date:    date,
    dry_run:        bool,
    logger:         logging.Logger,
) -> int:
    """
    Remove subdirectories of quarantine_dir whose name is a date older than
    cutoff_date.  Returns the number of folders removed (or that would be
    removed in dry-run mode).
    """
    if not os.path.isdir(quarantine_dir):
        logger.info(f"Quarantine directory does not exist – nothing to clean.")
        logger.debug(f"  Expected: {quarantine_dir}")
        return 0

    removed = 0

    try:
        entries = sorted(os.listdir(quarantine_dir))
    except OSError as exc:
        logger.error(f"Cannot list quarantine directory: {exc}")
        return 0

    for name in entries:
        # Only consider YYYY-MM-DD folders
        try:
            folder_date = date.fromisoformat(name)
        except ValueError:
            logger.debug(f"  Skipping non-date entry: {name}")
            continue

        if folder_date >= cutoff_date:
            logger.debug(f"  Keeping  {name}  (not yet past threshold)")
            continue

        folder_abs = os.path.join(quarantine_dir, name)
        age_days   = (date.today() - folder_date).days

        if dry_run:
            logger.info(f"  [DRY-RUN] Would delete: {name}  ({age_days} days old)")
        else:
            try:
                shutil.rmtree(folder_abs)
                logger.info(f"  Deleted: {name}  ({age_days} days old)")
            except OSError as exc:
                logger.warning(f"  WARNING: Could not delete '{folder_abs}': {exc}")
                continue

        removed += 1

    return removed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete date-stamped quarantine folders older than a threshold.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python clean_quarantine.py
  python clean_quarantine.py --dry-run
  python clean_quarantine.py --older-than-days 90
  python clean_quarantine.py --config "D:\\myconfig.json"
""",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help=(
            "Path to the user config JSON. "
            f"Default: ~/{CONFIG_FILENAME}"
        ),
    )
    parser.add_argument(
        "--older-than-days",
        metavar="N",
        type=int,
        default=30,
        help="Delete quarantine folders older than N days. Default: 30.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without removing anything.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show DEBUG-level messages.",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    args   = parse_args(argv)
    logger = setup_logging(args.verbose)

    cfg = load_config(args.config, logger)
    servoy_home    = os.path.expandvars(cfg["servoy_home"])
    quarantine_dir = os.path.join(
        servoy_home, "application_server", QUARANTINE_DIRNAME
    )

    threshold  = args.older_than_days
    cutoff     = date.today() - timedelta(days=threshold)
    mode_label = "[DRY-RUN] " if args.dry_run else ""

    logger.info(
        f"{mode_label}Cleaning quarantine folders older than {threshold} days "
        f"(before {cutoff})."
    )
    logger.info(f"Quarantine directory: {quarantine_dir}")

    removed = clean_quarantine(quarantine_dir, cutoff, args.dry_run, logger)

    if removed == 0:
        logger.info("Nothing to clean.")
    elif args.dry_run:
        logger.info(f"[DRY-RUN] {removed} folder(s) would be deleted.")
    else:
        logger.info(f"Done. {removed} folder(s) deleted.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
