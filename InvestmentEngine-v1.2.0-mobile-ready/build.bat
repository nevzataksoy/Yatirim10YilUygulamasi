@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo Rosa Investment Engine - OneFile Build
echo ============================================================

:: Build ve Inno Setup islemleri yonetici olarak calisir.
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Yonetici izinleri gerekli. Pencere yukseltiliyor...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%ComSpec%' -ArgumentList '/c ""%~f0""' -Verb RunAs"
    exit /b
)

:: Python secimi
set "PYTHON=python"
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    set "PYTHON=py -3"
    %PYTHON% --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python 3 bulunamadi.
        pause
        exit /b 1
    )
)

:: Sanal ortam yoksa olustur.
if not exist ".venv\Scripts\python.exe" (
    echo .venv olusturuluyor...
    %PYTHON% -m venv .venv
    if errorlevel 1 goto :fail
)

set "VPY=.venv\Scripts\python.exe"

echo Build bagimliliklari kuruluyor...
"%VPY%" -m pip install --upgrade pip wheel setuptools
if errorlevel 1 goto :fail
"%VPY%" -m pip install -r requirements-build.txt
if errorlevel 1 goto :fail

echo.
echo Python compile kontrolu...
"%VPY%" -m compileall -q app run.py service.py
if errorlevel 1 goto :fail

echo Testler calistiriliyor...
"%VPY%" -m pytest -q
if errorlevel 1 goto :fail

echo Release yapisi kontrol ediliyor...
"%VPY%" scripts\release_check.py
if errorlevel 1 goto :fail

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist InvestmentEngine.spec del /q InvestmentEngine.spec

set "UPX_ARG="
if exist "C:\Tools\upx-5.0.1-win64\upx.exe" set "UPX_ARG=--upx-dir C:\Tools\upx-5.0.1-win64"
if exist "C:\Tools\upx\upx.exe" set "UPX_ARG=--upx-dir C:\Tools\upx"

echo.
echo PyInstaller one-file EXE olusturuluyor...
"%VPY%" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --uac-admin ^
    --name "InvestmentEngine" ^
    --version-file "version_info.txt" ^
    --add-data "config;config" ^
    --collect-all psycopg ^
    --collect-submodules psycopg_pool ^
    --collect-submodules apscheduler ^
    --collect-all tzdata ^
    --hidden-import win32timezone ^
    --hidden-import win32service ^
    --hidden-import win32serviceutil ^
    --hidden-import servicemanager ^
    --hidden-import pywintypes ^
    --hidden-import pythoncom ^
    --hidden-import cryptography ^
    --hidden-import websocket ^
    --hidden-import websocket._app ^
    %UPX_ARG% ^
    run.py
if errorlevel 1 goto :fail

if not exist "dist\InvestmentEngine.exe" (
    echo ERROR: dist\InvestmentEngine.exe olusmadi.
    goto :fail
)

echo.
echo EXE build basarili: dist\InvestmentEngine.exe

:: Inno Setup mevcutsa installer'i de derle.
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if exist "%ISCC%" (
    echo.
    echo Inno Setup derleniyor...
    if not exist installer mkdir installer
    "%ISCC%" "investmentengine_setup.iss"
    if errorlevel 1 goto :fail
    echo Installer build basarili. installer klasorunu kontrol edin.
) else (
    echo.
    echo NOT: Inno Setup 6 bulunamadi. EXE hazirlandi, setup derlenmedi.
    echo investmentengine_setup.iss dosyasini Inno Setup Compiler ile derleyebilirsiniz.
)

echo.
echo ============================================================
echo BUILD TAMAMLANDI
echo ============================================================
echo EXE: dist\InvestmentEngine.exe
echo.
pause
exit /b 0

:fail
echo.
echo ============================================================
echo BUILD BASARISIZ
echo ============================================================
echo Yukaridaki hata mesajlarini kontrol edin.
pause
exit /b 1
