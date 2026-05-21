"""Error handling utilities and safe call decorator."""

from __future__ import annotations

import functools
import traceback
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from .logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class ErrorReport:
    message: str
    exception_type: str
    traceback_str: str

    def short(self) -> str:
        return f"{self.exception_type}: {self.message}"


def safe_call(default: Any = None, log: bool = True) -> Callable:
    """Decorator that catches exceptions and returns ``default`` on failure."""
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if log:
                    logger.exception(f"safe_call: {fn.__name__} failed: {e}")
                return default
        return wrapper
    return decorator


def capture_exception(exc: BaseException) -> ErrorReport:
    return ErrorReport(
        message=str(exc),
        exception_type=type(exc).__name__,
        traceback_str="".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    )


def parse_ffmpeg_error(stderr: str) -> str:
    """Extract the most useful line from an ffmpeg stderr dump."""
    if not stderr:
        return "Unknown ffmpeg error"
    lines = [ln for ln in stderr.splitlines() if ln.strip()]
    keywords = ("Error", "error", "Invalid", "failed", "Failed", "Cannot", "Unable")
    for ln in reversed(lines):
        if any(k in ln for k in keywords):
            return ln.strip()
    return lines[-1].strip() if lines else "Unknown ffmpeg error"
