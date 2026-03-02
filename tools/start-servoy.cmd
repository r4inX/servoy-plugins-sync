@echo off
setlocal

:: ============================================================
:: start-servoy.cmd
:: Selects the Servoy profile (picker shown if multiple exist),
:: syncs Gold Plugins, then launches Servoy Developer.
:: Requires Python 3.10+.
:: ============================================================

set "SCRIPT_DIR=%~dp0"
set "SYNC_SCRIPT=%SCRIPT_DIR%plugins_sync.py"

:: ------------------------------------------------------------
:: 1. Find a working Python 3 interpreter
:: ------------------------------------------------------------
set "PYTHON_CMD="

python --version >nul 2>&1
if %errorlevel% == 0 (
    set "PYTHON_CMD=python"
    goto :run
)

py -3 --version >nul 2>&1
if %errorlevel% == 0 (
    set "PYTHON_CMD=py -3"
    goto :run
)

echo [ERROR] Python 3 was not found on PATH.
echo         Download from https://python.org and tick "Add to PATH" during install.
pause
exit /b 1

:: ------------------------------------------------------------
:: 2. Delegate everything to plugins_sync.py --launch
::    (profile picker, sync, Servoy start)
:: ------------------------------------------------------------
:run
if not exist "%SYNC_SCRIPT%" (
    echo [ERROR] Sync script not found: %SYNC_SCRIPT%
    pause
    exit /b 1
)

%PYTHON_CMD% "%SYNC_SCRIPT%" --launch
set "RC=%errorlevel%"
if %RC% neq 0 (
    echo.
    echo [WARNING] Script exited with code %RC%.
    echo           Check the log for details.
    pause
)

endlocal
exit /b %RC%