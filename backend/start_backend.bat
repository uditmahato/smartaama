@echo off
cd /d c:\Users\chhay\Desktop\project\smartaama\backend
set PYTHONPATH=c:\Users\chhay\Desktop\project\smartaama\backend
c:\Users\chhay\Desktop\project\smartaama\backend\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
