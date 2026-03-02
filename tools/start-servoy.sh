#!/usr/bin/env bash
# =============================================================================
# start-servoy.sh – Servoy Gold Plugin Sync Wrapper (macOS / Linux)
# =============================================================================
# Runs plugins_sync.py before launching Servoy.
# Sync errors produce a warning but never block the Servoy start.
#
# Usage: just run this script instead of launching Servoy directly.
#   chmod +x start-servoy.sh   (once)
#   ./start-servoy.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNC_SCRIPT="$SCRIPT_DIR/plugins_sync.py"
CONFIG_FILE="$HOME/.servoy-plugin-sync.json"

echo "============================================================"
echo " Servoy Gold Plugin Sync – Wrapper"
echo "============================================================"

# -----------------------------------------------------------------------------
# 1. Find Python 3
# -----------------------------------------------------------------------------
PYTHON_CMD=""
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null && python --version 2>&1 | grep -q "^Python 3"; then
    PYTHON_CMD="python"
fi

if [[ -z "$PYTHON_CMD" ]]; then
    echo "[WARNING] Python 3 not found."
    echo "          macOS: install via 'brew install python' or https://python.org"
    echo "          Linux: install via 'sudo apt install python3' (or your package manager)"
    echo "          Plugin sync will be SKIPPED. Starting Servoy anyway..."
    echo ""
    SKIP_SYNC=1
else
    SKIP_SYNC=0
fi

# -----------------------------------------------------------------------------
# 2. Extract servoy_home from config (using Python to parse JSON – no jq needed)
# -----------------------------------------------------------------------------
SERVOY_HOME=""

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "[ERROR] Config file not found: $CONFIG_FILE"
    echo "        Create it with keys: gold_root, servoy_home, servoy_version"
    echo "        See docs/example.servoy-plugin-sync.json for a template."
    echo "        Skipping sync."
    SKIP_SYNC=1
elif [[ -n "$PYTHON_CMD" ]]; then
    SERVOY_HOME="$($PYTHON_CMD - <<'PYEOF'
import json, os, sys
cfg_path = os.path.expanduser("~/.servoy-plugin-sync.json")
try:
    with open(cfg_path) as f:
        d = json.load(f)
    print(d.get("servoy_home", ""))
except Exception as e:
    print("", end="")
PYEOF
)"
    # Strip trailing slash
    SERVOY_HOME="${SERVOY_HOME%/}"

    if [[ -z "$SERVOY_HOME" ]]; then
        echo "[ERROR] Could not read 'servoy_home' from $CONFIG_FILE"
        echo "        Skipping sync."
        SKIP_SYNC=1
    fi
fi

if [[ -n "$SERVOY_HOME" ]]; then
    echo " servoy_home : $SERVOY_HOME"
fi
echo " sync script : $SYNC_SCRIPT"
echo ""

# -----------------------------------------------------------------------------
# 3. Run plugin sync
# -----------------------------------------------------------------------------
SYNC_EXIT=0

if [[ "$SKIP_SYNC" -eq 0 ]]; then
    if [[ ! -f "$SYNC_SCRIPT" ]]; then
        echo "[WARNING] Sync script not found: $SYNC_SCRIPT"
        echo "          Plugin sync will be SKIPPED. Starting Servoy anyway..."
        echo ""
        SKIP_SYNC=1
    else
        echo "[INFO] Running plugin sync..."
        set +e
        "$PYTHON_CMD" "$SYNC_SCRIPT"
        SYNC_EXIT=$?
        set -e

        if [[ "$SYNC_EXIT" -eq 0 ]]; then
            echo "[INFO] Plugin sync completed successfully."
        else
            echo ""
            echo "[WARNING] Plugin sync finished with issues (exit code: $SYNC_EXIT)."
            echo "          Some plugins may not be up to date."
            if [[ -n "$SERVOY_HOME" ]]; then
                echo "          Check the log: $SERVOY_HOME/application_server/plugins/gold_plugins_sync.log"
            fi
            echo "          Starting Servoy anyway..."
        fi
        echo ""
    fi
fi

# -----------------------------------------------------------------------------
# 4. Locate and launch Servoy
# -----------------------------------------------------------------------------
if [[ -z "$SERVOY_HOME" ]]; then
    echo "[ERROR] Cannot determine servoy_home – unable to start Servoy automatically."
    echo "        Please set up $CONFIG_FILE and retry."
    exit 1
fi

# Detect OS and preferred executable
OS_TYPE="$(uname -s)"
SERVOY_APP="$SERVOY_HOME/developer/Servoy.app"      # macOS .app bundle
SERVOY_BIN="$SERVOY_HOME/developer/servoy"          # Linux / macOS binary fallback

if [[ "$OS_TYPE" == "Darwin" ]] && [[ -d "$SERVOY_APP" ]]; then
    echo "[INFO] Launching (macOS): $SERVOY_APP"
    open "$SERVOY_APP"

elif [[ -f "$SERVOY_BIN" ]]; then
    echo "[INFO] Launching: $SERVOY_BIN"
    # Launch detached so the terminal is not blocked
    nohup "$SERVOY_BIN" &>/dev/null &
    disown

else
    echo "[ERROR] Servoy executable not found."
    echo "        Tried:"
    [[ "$OS_TYPE" == "Darwin" ]] && echo "          $SERVOY_APP  (macOS .app)"
    echo "          $SERVOY_BIN"
    echo "        Check 'servoy_home' in $CONFIG_FILE"
    exit 1
fi
