@echo off
setlocal EnableDelayedExpansion

:: ============================================================
:: start-servoy.cmd
:: Syncs Gold Plugins via plugins_sync.py, then launches Servoy.
:: Sync errors are warned about but never block the Servoy start.
:: ============================================================

set "SCRIPT_DIR=%~dp0"
set "SYNC_SCRIPT=%SCRIPT_DIR%plugins_sync.py"
set "CONFIG_FILE=%USERPROFILE%\.servoy-plugin-sync.json"

echo ============================================================
echo  Servoy Gold Plugin Sync – Wrapper
echo ============================================================

:: ------------------------------------------------------------
:: 1. Extract servoy_home from config via PowerShell
:: ------------------------------------------------------------
if not exist "%CONFIG_FILE%" (
    echo [ERROR] Config file not found: %CONFIG_FILE%
    echo         Create it with keys: gold_root, servoy_home, servoy_version
    echo         Skipping sync.
    goto :start_servoy_no_home
)

for /f "usebackq delims=" %%H in (
    `powershell -NoProfile -NonInteractive -Command ^
        "try { $c = Get-Content -Raw '%CONFIG_FILE%' | ConvertFrom-Json; Write-Output $c.servoy_home } catch { Write-Output '' }"`
) do set "SERVOY_HOME=%%H"

:: Strip trailing backslash only if present (keeps paths consistent).
:: NOTE: the old two-line form always removed the last char unconditionally,
::       which corrupted paths that did NOT end with a backslash.
if defined SERVOY_HOME (
    if "!SERVOY_HOME:~-1!"=="\" set "SERVOY_HOME=!SERVOY_HOME:~0,-1!"
)

if not defined SERVOY_HOME (
    echo [ERROR] Could not read 'servoy_home' from %CONFIG_FILE%
    echo         Skipping sync.
    goto :start_servoy_no_home
)

echo  servoy_home : %SERVOY_HOME%
echo  sync script : %SYNC_SCRIPT%
echo.

:: ------------------------------------------------------------
:: 2. Locate a working Python interpreter
::    Priority: python  →  py -3  →  warn + skip sync
:: ------------------------------------------------------------
set "PYTHON_CMD="

python --version >nul 2>&1
if %errorlevel% == 0 (
    set "PYTHON_CMD=python"
    goto :run_sync
)

py -3 --version >nul 2>&1
if %errorlevel% == 0 (
    set "PYTHON_CMD=py -3"
    goto :run_sync
)

echo [WARNING] Python 3 was not found on PATH.
echo           Please install Python 3 or add it to PATH.
echo           Plugin sync will be SKIPPED.
echo           Starting Servoy anyway...
echo.
goto :start_servoy

:: ------------------------------------------------------------
:: 3. Run the sync script
:: ------------------------------------------------------------
:run_sync
if not exist "%SYNC_SCRIPT%" (
    echo [WARNING] Sync script not found: %SYNC_SCRIPT%
    echo           Plugin sync will be SKIPPED.
    echo           Starting Servoy anyway...
    echo.
    goto :start_servoy
)

echo [INFO] Running plugin sync...
%PYTHON_CMD% "%SYNC_SCRIPT%"
set "SYNC_EXIT=%errorlevel%"

if %SYNC_EXIT% == 0 (
    echo [INFO] Plugin sync completed successfully.
) else (
    echo.
    echo [WARNING] Plugin sync finished with issues (exit code: %SYNC_EXIT%^).
    echo           Some plugins may not be up to date.
    echo           Check the log for details:
    echo           %SERVOY_HOME%\application_server\plugins\gold_plugins_sync.log
    echo           Starting Servoy anyway...
)
echo.

:: ------------------------------------------------------------
:: 4. Start Servoy
:: ------------------------------------------------------------
:start_servoy
set "SERVOY_EXE=%SERVOY_HOME%\developer\servoy.exe"
goto :launch

:start_servoy_no_home
:: Fallback: try to read servoy_home from a hardcoded default or bail out
:: gracefully – we don't know the path, so we cannot start servoy.exe.
echo [ERROR] Cannot determine servoy_home – unable to start Servoy automatically.
echo         Please set up %CONFIG_FILE% and retry.
pause
exit /b 1

:launch
if not exist "%SERVOY_EXE%" (
    echo [ERROR] servoy.exe not found at: %SERVOY_EXE%
    echo         Check 'servoy_home' in %CONFIG_FILE%
    pause
    exit /b 1
)

echo [INFO] Launching: %SERVOY_EXE%
start "" "%SERVOY_EXE%"

endlocal
exit /b 0
