#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Logging configuration for CV Studio"""

import logging
import logging.handlers
import os
import sys
from typing import Optional


def _get_default_log_file() -> Optional[str]:
    """Return a default log file path in the user data directory on Windows,
    or None on other platforms where stdout/stderr are always available."""
    if sys.platform != "win32":
        return None
    # On Windows the app may run without a console (e.g. double-clicked .exe).
    # Write logs to %APPDATA%\CV_Studio\cv_studio.log so that there is always
    # a persistent record of what happened.
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    log_dir = os.path.join(appdata, "CV_Studio")
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "cv_studio.log")


def _make_console_handler(level: int, formatter: logging.Formatter) -> logging.Handler:
    """Return a console StreamHandler that is safe on Windows.

    On Windows, ``sys.stdout`` may be ``None`` when the process has no
    attached console (e.g. a double-clicked PyInstaller .exe built with
    ``--noconsole``).  In that case we fall back to ``sys.stderr``, and if
    that is also unavailable we return a ``NullHandler`` so that the rest of
    the logging setup still works without raising.

    The stream is wrapped with ``errors='replace'`` so that Unicode characters
    that cannot be represented in the console code-page (e.g. cp850/cp1252 on
    French/English Windows) are replaced with ``?`` instead of raising a
    ``UnicodeEncodeError``.
    """
    stream = None
    for candidate in (sys.stdout, sys.stderr):
        if candidate is not None:
            stream = candidate
            break

    if stream is None:
        handler: logging.Handler = logging.NullHandler()
        handler.setLevel(level)
        return handler

    if sys.platform == "win32":
        # Wrap with a reconfigured stream that replaces un-encodable characters
        # instead of crashing.  Python 3.7+ exposes reconfigure() on TextIOWrapper.
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, OSError):
            pass

    handler = logging.StreamHandler(stream)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    return handler


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """Setup logging configuration for the application.

    Args:
        level: Logging level (default: INFO)
        log_file: Optional file path to write logs.  On Windows, when this is
            ``None`` and no explicit path is supplied, logs are automatically
            written to ``%APPDATA%\\CV_Studio\\cv_studio.log`` so that there is
            always a persistent record even when the application runs without a
            visible console.
        format_string: Custom format string for log messages

    Returns:
        Configured root logger instance
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicate output on re-configuration.
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler (Windows-safe: handles missing stdout and encoding issues)
    console_handler = _make_console_handler(level, formatter)
    root_logger.addHandler(console_handler)

    # Determine the log file to use.
    resolved_log_file = log_file or _get_default_log_file()

    if resolved_log_file:
        log_dir = os.path.dirname(resolved_log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        # RotatingFileHandler avoids unbounded log growth; keeps up to 5 × 5 MB.
        # Always write in UTF-8 so that accented characters and emoji are stored
        # correctly regardless of the Windows system code-page.
        file_handler = logging.handlers.RotatingFileHandler(
            resolved_log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.

    Args:
        name: Module name (typically ``__name__``)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
