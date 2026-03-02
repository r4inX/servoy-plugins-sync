#!/usr/bin/env bash
# ============================================================
# start-servoy.sh
# Selects the Servoy profile (picker shown if multiple exist),
# syncs Gold Plugins, then launches Servoy Developer.
# Requires Python 3.10+.
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNC_SCRIPT="$SCRIPT_DIR/plugins_sync.py"

# Find Python 3
PYTHON_CMD=""
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null && python --version 2>&1 | grep -q 'Python 3'; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python 3 was not found." >&2
    echo "        Install Python 3 and ensure it is in your PATH." >&2
    exit 1
fi

if [ ! -f "$SYNC_SCRIPT" ]; then
    echo "[ERROR] Sync script not found: $SYNC_SCRIPT" >&2
    exit 1
fi

# Delegate everything to plugins_sync.py --launch
# (profile picker, sync, Servoy start)
exec "$PYTHON_CMD" "$SYNC_SCRIPT" --launch