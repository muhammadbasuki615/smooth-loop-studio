#!/usr/bin/env bash
# ============================================================
#  Smooth Loop Studio - Run (Linux / macOS)
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d venv ]; then
    echo "[WARN] venv tidak ditemukan, menjalankan setup..."
    bash setup.sh
fi

# shellcheck disable=SC1091
source venv/bin/activate

if ! python -c "import PySide6" >/dev/null 2>&1; then
    echo "[INFO] Dependency hilang, re-install otomatis..."
    python -m pip install -r requirements.txt
fi

exec python app/main.py "$@"
