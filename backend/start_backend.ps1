# Thin wrapper around: uvicorn app.main:app --reload  (run from backend/)
# Uses the script's own folder, so it works from any clone location.
Set-Location -Path $PSScriptRoot

$py = "python"
if (Test-Path (Join-Path $PSScriptRoot ".venv\Scripts\python.exe")) {
    $py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
} elseif (Test-Path (Join-Path $PSScriptRoot "venv\Scripts\python.exe")) {
    $py = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
}

if (-not (Test-Path (Join-Path $PSScriptRoot ".env"))) {
    Write-Warning "backend\.env not found - copy .env.example to .env and set SECRET_KEY / DATABASE_URL."
}

& $py -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
