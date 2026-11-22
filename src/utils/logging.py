#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Logging configuration for CV Studio.

Every way of running CV Studio (``python main.py``, frozen Windows ``.exe``,
frozen Linux binary, with or without a console) must leave an easily
accessible trace when it crashes.  This module provides:

* :func:`get_log_dir` – a writable log directory, identical for all launch
  modes: ``CV_Studio_data/logs/`` next to the executable when frozen, ``logs/``
  in the repository in development mode (override with ``CV_STUDIO_LOG_DIR``).
* :func:`setup_logging` – console + rotating file handler
  (``cv_studio.log``) on **every** platform.
* :func:`get_default_fault_log_file` – ``cv_studio_fault.log`` where
  ``faulthandler`` writes hard crashes (segfault, abort).
* :func:`install_exception_hooks` – ``sys.excepthook`` /
  ``threading.excepthook`` that record uncaught exceptions in the log file,
  even before :func:`setup_logging` has run (e.g. an ``ImportError`` while the
  frozen bundle is loading).
"""

import logging
import logging.handlers
import os
import sys
import tempfile
import threading
import traceback
from datetime import datetime
from typing import Optional

LOG_DIR_ENV = "CV_STUDIO_LOG_DIR"
LOG_FILE_NAME = "cv_studio.log"
FAULT_LOG_FILE_NAME = "cv_studio_fault.log"
_DATA_FOLDER_NAME = "CV_Studio_data"

_log_dir_cache: Optional[str] = None
_hooks_installed = False


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _user_log_dir() -> str:
    """Per-user fallback used when the application directory is read-only."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "CV_Studio", "logs")
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Logs", "CV_Studio")
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "state"
    )
    return os.path.join(base, "CV_Studio", "logs")


def _candidate_log_dirs() -> list:
    candidates = []
    env_dir = os.environ.get(LOG_DIR_ENV)
    if env_dir:
        candidates.append(os.path.abspath(env_dir))
    if _is_frozen():
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        candidates.append(os.path.join(exe_dir, _DATA_FOLDER_NAME, "logs"))
    else:
        candidates.append(os.path.join(_repo_root(), "logs"))
    candidates.append(_user_log_dir())
    candidates.append(os.path.join(tempfile.gettempdir(), "CV_Studio", "logs"))
    return candidates


def _is_writable_dir(path: str) -> bool:
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".write_test")
        with open(probe, "a", encoding="utf-8"):
            pass
        os.remove(probe)
        return True
    except OSError:
        return False


def get_log_dir() -> str:
    """Return the writable directory where all CV Studio logs are stored.

    Resolution order: ``$CV_STUDIO_LOG_DIR``, then ``CV_Studio_data/logs``
    next to the executable (frozen) or ``logs/`` in the repository (dev), then
    a per-user directory, then the system temp directory.  The first writable
    candidate wins and the result is cached for the process lifetime.
    """
    global _log_dir_cache
    if _log_dir_cache is not None:
        return _log_dir_cache
    for candidate in _candidate_log_dirs():
        if _is_writable_dir(candidate):
            _log_dir_cache = candidate
            return candidate
    _log_dir_cache = tempfile.gettempdir()
    return _log_dir_cache


def get_default_log_file() -> str:
    """Path of the application log (``cv_studio.log``)."""
    return os.path.join(get_log_dir(), LOG_FILE_NAME)


def get_default_fault_log_file() -> str:
    """Path of the hard-crash trace file written by ``faulthandler``."""
    return os.path.join(get_log_dir(), FAULT_LOG_FILE_NAME)


def _get_default_log_file() -> Optional[str]:
    """Backward-compatible alias kept for existing callers/tests."""
    return get_default_log_file()


def _make_console_handler(level: int, formatter: logging.Formatter) -> logging.Handler:
    """Return a console StreamHandler that is safe without a console.

    ``sys.stdout`` / ``sys.stderr`` may be ``None`` when the process has no
    attached console (e.g. a double-clicked PyInstaller .exe built with
    ``--noconsole``).  In that case a ``NullHandler`` is returned so that the
    rest of the logging setup still works without raising.

    On Windows the stream is reconfigured with ``errors='replace'`` so that
    characters that cannot be represented in the console code-page are
    replaced with ``?`` instead of raising ``UnicodeEncodeError``.
    """
    stream = None
    for candidate in (sys.stderr, sys.stdout):
        if candidate is not None:
            stream = candidate
            break

    if stream is None:
        handler: logging.Handler = logging.NullHandler()
        handler.setLevel(level)
        return handler

    if sys.platform == "win32":
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, OSError, ValueError):
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
        log_file: File path to write logs.  When ``None`` the default
            ``cv_studio.log`` in :func:`get_log_dir` is used, on every
            platform, so that there is always a persistent record even when
            the application runs without a visible console.
        format_string: Custom format string for log messages

    Returns:
        Configured root logger instance
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass

    root_logger.addHandler(_make_console_handler(level, formatter))

    resolved_log_file = log_file or get_default_log_file()
    log_dir = os.path.dirname(resolved_log_file)
    try:
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        # RotatingFileHandler avoids unbounded log growth; keeps up to 5 × 5 MB.
        # Always UTF-8 so accented characters are stored correctly regardless of
        # the Windows system code-page.
        file_handler = logging.handlers.RotatingFileHandler(
            resolved_log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except OSError as exc:
        root_logger.error("Cannot open log file %s: %s", resolved_log_file, exc)

    install_exception_hooks()
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module."""
    return logging.getLogger(name)


def get_active_log_files() -> list:
    """Return the paths of the files the root logger is currently writing to."""
    return [
        handler.baseFilename
        for handler in logging.getLogger().handlers
        if hasattr(handler, "baseFilename")
    ]


# ---------------------------------------------------------------------------
# Crash hooks
# ---------------------------------------------------------------------------


def _write_raw_crash_report(header: str, exc_info) -> None:
    """Last-resort writer used when logging is not configured yet.

    Appends the traceback to the default log file and to stderr (if any).
    Never raises.
    """
    text = "".join(traceback.format_exception(*exc_info))
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    block = f"{stamp} - CRASH - {header}\n{text}"
    try:
        with open(get_default_log_file(), "a", encoding="utf-8") as fh:
            fh.write(block)
    except OSError:
        pass
    if sys.stderr is not None:
        try:
            sys.stderr.write(block)
            sys.stderr.flush()
        except Exception:
            pass


def log_uncaught_exception(header: str, exc_info) -> None:
    """Record an uncaught exception in the log file (whatever the state of logging)."""
    root_logger = logging.getLogger()
    has_file = any(hasattr(h, "baseFilename") for h in root_logger.handlers)
    if has_file:
        root_logger.critical(header, exc_info=exc_info)
    else:
        _write_raw_crash_report(header, exc_info)


def _sys_excepthook(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    log_uncaught_exception("Unhandled exception", (exc_type, exc_value, exc_tb))


def _thread_excepthook(args):
    if args.exc_type is SystemExit:
        return
    thread_name = getattr(args.thread, "name", "unknown")
    log_uncaught_exception(
        f"Unhandled exception in thread '{thread_name}'",
        (args.exc_type, args.exc_value, args.exc_traceback),
    )


def install_exception_hooks() -> None:
    """Route uncaught exceptions (main thread, worker threads, DearPyGui
    callbacks which go through ``sys.excepthook``) to the log file.

    Safe to call several times and before :func:`setup_logging`: as long as no
    file handler exists the traceback is appended to the default log file
    directly, so even an ``ImportError`` during start-up of the frozen bundle
    leaves a trace.
    """
    global _hooks_installed
    if _hooks_installed:
        return
    sys.excepthook = _sys_excepthook
    threading.excepthook = _thread_excepthook
    _hooks_installed = True
