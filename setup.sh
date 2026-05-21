#!/usr/bin/env bash
# ============================================================
#  Smooth Loop Studio - Setup (Linux / macOS)
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

echo
echo "==============================================="
echo "  Smooth Loop Studio - Setup"
echo "==============================================="
echo

# 1. Verify Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 tidak ditemukan. Install Python 3.12+."
    exit 1
fi
echo "[1/6] Python: $(python3 --version)"

# 2. venv
if [ ! -d venv ]; then
    echo "[2/6] Membuat virtual environment..."
    python3 -m venv venv
else
    echo "[2/6] venv sudah ada"
fi

# shellcheck disable=SC1091
source venv/bin/activate

# 3. pip upgrade
echo "[3/6] Upgrade pip..."
python -m pip install --upgrade pip setuptools wheel >/dev/null

# 4. requirements
echo "[4/6] Install dependencies..."
python -m pip install -r requirements.txt

# 5. ffmpeg
echo "[5/6] Verifikasi / install FFmpeg..."
python -c "
from pathlib import Path
from app.core.ffmpeg_installer import FFmpegInstaller
from app.core.ffmpeg_utils import FFmpeg
ff = FFmpeg()
if ff.is_available():
    print('FFmpeg system OK:', ff.binary)
else:
    print('System ffmpeg tidak ada, install lokal...')
    FFmpegInstaller(Path('app/ffmpeg')).install()
"

# 6. GPU detection
echo "[6/6] Detect GPU encoders..."
python -c "
from app.core.ffmpeg_utils import FFmpeg, detect_gpu
info = detect_gpu(FFmpeg())
print('  NVENC:', info.has_nvidia)
print('  QSV  :', info.has_intel)
print('  AMF  :', info.has_amd)
"

echo
echo "==============================================="
echo "  SETUP SELESAI"
echo "  Jalankan: ./run.sh"
echo "==============================================="
echo
