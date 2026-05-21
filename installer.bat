@echo off
REM ============================================================
REM  Smooth Loop Studio - One-Click Installer (Windows)
REM ============================================================
REM  Combines setup + verifies + creates a desktop shortcut.
REM ============================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ===============================================
echo  Smooth Loop Studio - Installer
echo ===============================================
echo.

call setup.bat
if errorlevel 1 (
    echo [ERROR] Setup gagal.
    pause & exit /b 1
)

REM Create Start-Menu / Desktop shortcut (via PowerShell)
echo Membuat shortcut di Desktop...
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$desk = $ws.SpecialFolders('Desktop');" ^
  "$lnk = $ws.CreateShortcut(\"$desk\Smooth Loop Studio.lnk\");" ^
  "$lnk.TargetPath = \"%~dp0run.bat\";" ^
  "$lnk.WorkingDirectory = \"%~dp0\";" ^
  "$lnk.Description = 'Smooth Loop Studio';" ^
  "$lnk.Save();"

echo.
echo ===============================================
echo  INSTALASI SELESAI
echo  Shortcut sudah tersedia di Desktop
echo ===============================================
echo.
pause
