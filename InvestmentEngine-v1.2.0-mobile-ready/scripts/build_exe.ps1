$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    & "$Root\.venv\Scripts\python.exe" -m pip install -r requirements-build.txt
    & "$Root\.venv\Scripts\python.exe" -m compileall -q app run.py service.py
    & "$Root\.venv\Scripts\python.exe" -m pytest -q
    & "$Root\.venv\Scripts\python.exe" scripts\release_check.py
    & "$Root\.venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --uac-admin --name InvestmentEngine --version-file version_info.txt --add-data "config;config" --collect-all psycopg --collect-submodules psycopg_pool --collect-submodules apscheduler --collect-all tzdata --collect-all firebase_admin --hidden-import win32timezone --hidden-import win32service --hidden-import win32serviceutil --hidden-import servicemanager --hidden-import pywintypes --hidden-import pythoncom --hidden-import cryptography --hidden-import websocket --hidden-import websocket._app run.py
    Write-Host "dist\InvestmentEngine.exe oluşturuldu."
}
finally { Pop-Location }
