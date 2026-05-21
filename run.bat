@echo off
REM ============================================================
REM  Smooth Loop Studio - Run (Windows)
REM ============================================================
setlocal
cd /d "%~dp0"

if not exist venv (
    echo [WARN] venv tidak ditemukan. Menjalankan setup terlebih dahulu...
    call setup.bat
)

call venv\Scripts\activate.bat

REM Auto-repair: re-check requirements if PySide6 hilang
python -c "import PySide6" 2>nul
if errorlevel 1 (
    echo [INFO] Dependency hilang, re-install otomatis...
    python -m pip install -r requirements.txt
)

python app\main.py
if errorlevel 1 (
    echo.
    echo [ERROR] Aplikasi keluar dengan error. Cek app\logs\ untuk detail.
    pause
)
