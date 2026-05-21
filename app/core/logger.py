"""Centralized logger using loguru with safe fallback."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

try:
    from loguru import logger as _loguru_logger
    _HAS_LOGURU = True
except Exception:  # pragma: no cover - fallback
    _HAS_LOGURU = False
    import logging

_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _LOG_DIR / "smooth_loop_studio.log"

_configured = False


def _configure_loguru() -> None:
    global _configured
    if _configured:
        return
    _loguru_logger.remove()
    level = os.environ.get("SLS_LOG_LEVEL", "INFO").upper()
    _loguru_logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        ),
        colorize=True,
        backtrace=False,
        diagnose=False,
    )
    _loguru_logger.add(
        str(_LOG_FILE),
        level="DEBUG",
        rotation="10 MB",
        retention=5,
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )
    _configured = True


def get_logger(name: str | None = None) -> Any:
    """Return a logger bound to the given name."""
    if _HAS_LOGURU:
        _configure_loguru()
        return _loguru_logger.bind(name=name or "sls")
    # Fallback to stdlib logging
    logging.basicConfig(
        level=os.environ.get("SLS_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler(str(_LOG_FILE), encoding="utf-8"),
        ],
    )
    return logging.getLogger(name or "sls")
