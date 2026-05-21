@echo off
REM ============================================================
REM  Smooth Loop Studio - Setup (Windows)
REM ============================================================
REM  - Verify Python
REM  - Create virtual environment
REM  - Install dependencies
REM  - Install FFmpeg locally (portable)
REM  - Verify GPU
REM ============================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ===============================================
echo  Smooth Loop Studio - Setup
echo ===============================================
echo.

REM --- 1. Verify Python ----------------------------------------
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan di PATH.
    echo Download Python 3.12+ dari https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version') do set PYV=%%v
echo [1/6] Python found: !PYV!

REM --- 2. Virtual env ------------------------------------------
if not exist venv (
    echo [2/6] Membuat virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Gagal membuat venv.
        pause & exit /b 1
    )
) else (
    echo [2/6] Virtual environment sudah ada
)

call venv\Scripts\activate.bat

REM --- 3. Upgrade pip ------------------------------------------
echo [3/6] Upgrade pip / setuptools / wheel...
python -m pip install --upgrade pip setuptools wheel

REM --- 4. Install requirements ---------------------------------
echo [4/6] Install dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Gagal install dependencies. Periksa koneksi internet.
    pause & exit /b 1
)

REM --- 5. Install FFmpeg ---------------------------------------
echo [5/6] Verifikasi / install FFmpeg...
python -c "from app.core.ffmpeg_installer import FFmpegInstaller; from pathlib import Path; FFmpegInstaller(Path('app/ffmpeg')).install()"

REM --- 6. Verify GPU -------------------------------------------
echo [6/6] Detect GPU encoders...
python -c "from app.core.ffmpeg_utils import FFmpeg, detect_gpu; info = detect_gpu(FFmpeg()); print('Encoders ditemukan:'); print('  NVENC:', info.has_nvidia); print('  QSV  :', info.has_intel); print('  AMF  :', info.has_amd)"

echo.
echo ===============================================
echo  SETUP SELESAI
echo  Jalankan run.bat untuk membuka aplikasi
echo ===============================================
echo.
pause
