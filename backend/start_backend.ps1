#!/bin/bash
cd "c:\\Users\\chhay\\Desktop\\project\\smartaama\\backend"
$env:PYTHONPATH="$PWD"
& "c:\\Users\\chhay\\Desktop\\project\\smartaama\\backend\\venv\\Scripts\\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
