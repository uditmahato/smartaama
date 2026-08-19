@echo off
REM Thin wrapper around: uvicorn app.main:app --reload  (run from backend/)
REM Uses the script's own folder, so it works from any clone location.
setlocal
cd /d "%~dp0"

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY=%~dp0.venv\Scripts\python.exe"
) else if exist "%~dp0venv\Scripts\python.exe" (
    set "PY=%~dp0venv\Scripts\python.exe"
) else (
    set "PY=python"
)

if not exist "%~dp0.env" (
    echo [warn] backend\.env not found - copy .env.example to .env and set SECRET_KEY / DATABASE_URL.
)

"%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
endlocal
