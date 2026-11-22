#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Hard-crash diagnostics for CV Studio (segfault, abort, hangs).

Pure standard library so that it can be imported and enabled before the heavy
dependencies (OpenCV, DearPyGui, ONNX Runtime) are loaded, and tested without
them.  See :func:`configure_fault_diagnostics`.
"""

import atexit
import faulthandler
import os
import signal
import sys
import threading
import time

from src.utils.logging import (
    get_default_fault_log_file,
    get_logger,
    install_exception_hooks,
)

logger = get_logger(__name__)

_fault_log_file_handle = None
_fault_log_atexit_registered = False


def get_fault_log_path():
    """Return the path of the active fault log file, or None."""
    if _fault_log_file_handle is None:
        return None
    return _fault_log_file_handle.name


def _unique_streams(*streams):
    """Return a deduplicated list of streams, always including sys.stderr."""
    seen_fds = set()
    result = []
    for s in streams:
        if s is None:
            continue
        try:
            fd = s.fileno()
        except Exception:
            fd = id(s)
        if fd not in seen_fds:
            seen_fds.add(fd)
            result.append(s)
    # Always include stderr as a fallback if present (it is None in a
    # windowed .exe) and not already listed.
    if sys.stderr is not None:
        try:
            stderr_fd = sys.stderr.fileno()
        except Exception:
            stderr_fd = id(sys.stderr)
        if stderr_fd not in seen_fds:
            result.append(sys.stderr)
    return result


_FAULT_LOG_MAX_BYTES = 20 * 1024 * 1024


def _fault_log_housekeeping(file_handle, interval, max_bytes=_FAULT_LOG_MAX_BYTES):
    """Keep the fault log bounded: the watchdog appends a full thread dump
    every few seconds, so the file is truncated once it exceeds ``max_bytes``.
    The file is opened in append mode, so writes resume at offset 0."""
    import time as _time

    fd = file_handle.fileno()
    while True:
        _time.sleep(interval)
        try:
            if os.fstat(fd).st_size > max_bytes:
                os.ftruncate(fd, 0)
                file_handle.write(
                    f"--- fault log truncated at {_time.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"(exceeded {max_bytes // (1024 * 1024)} MB) ---\n"
                )
                file_handle.flush()
        except (OSError, ValueError):
            return


def configure_fault_diagnostics(fault_log_path=None):
    """Enable diagnostics for hard crashes (e.g., segfaults) and thread exceptions.

    ``faulthandler`` is enabled on a **file** by default
    (``cv_studio_fault.log`` in :func:`get_log_dir`, override with
    ``--fault_log`` or ``CV_STUDIO_FAULT_LOG``) so that a segfault leaves a
    full stack trace of all threads on disk whatever the launch mode: Python
    script, Linux binary, Windows .exe with or without console.  The dump is
    mirrored to stderr when a console is attached.

    SIGUSR1/SIGUSR2 (Ctrl+Break on Windows) dump all threads on demand.

    A background watchdog via faulthandler.dump_traceback_later() writes a full
    thread dump every ``CV_STUDIO_WATCHDOG_INTERVAL`` seconds (default 30, 0
    disables it); this captures the last-known state even when the process is
    killed without a signal reaching Python.  The fault log is truncated when it
    grows beyond 20 MB.
    """
    global _fault_log_file_handle, _fault_log_atexit_registered

    path = fault_log_path or os.environ.get("CV_STUDIO_FAULT_LOG") or get_default_fault_log_file()
    resolved_path = os.path.abspath(path)
    target_stream = None
    try:
        resolved_dir = os.path.dirname(resolved_path)
        if resolved_dir:
            os.makedirs(resolved_dir, exist_ok=True)
        if _fault_log_file_handle is not None:
            _close_fault_log_file()
        # Append + line-buffered: every newline flushes to the OS.
        _fault_log_file_handle = open(resolved_path, "a", buffering=1, encoding="utf-8")
        _fault_log_file_handle.write(
            f"\n===== CV_STUDIO session started {time.strftime('%Y-%m-%d %H:%M:%S')} "
            f"(pid {os.getpid()}) =====\n"
        )
        target_stream = _fault_log_file_handle
        if not _fault_log_atexit_registered:
            atexit.register(_close_fault_log_file)
            _fault_log_atexit_registered = True
    except OSError as exc:
        logger.error("Cannot open fault log %s: %s", resolved_path, exc)
        resolved_path = None

    if target_stream is None:
        target_stream = sys.stderr

    # Primary handler: dumps all threads on SIGSEGV / SIGABRT / SIGFPE / SIGBUS.
    # faulthandler.enable() accepts a single file, the last call wins, so the
    # file (persistent) is enabled last and stderr (visible) first.
    enabled_on_stderr = False
    if sys.stderr is not None:
        try:
            faulthandler.enable(file=sys.stderr, all_threads=True)
            enabled_on_stderr = True
        except Exception as exc:
            logger.warning("Failed to enable faulthandler on stderr: %s", exc)
    if target_stream is not None and target_stream is not sys.stderr:
        try:
            faulthandler.enable(file=target_stream, all_threads=True)
        except Exception as exc:
            logger.warning("Failed to enable faulthandler on %s: %s", resolved_path, exc)
    elif not enabled_on_stderr:
        logger.error("faulthandler could not be enabled: no fault log file and no stderr")

    _crash_signals = ("SIGSEGV", "SIGABRT", "SIGFPE", "SIGBUS")
    _registered_signals = [
        sig_name
        for sig_name in _crash_signals
        if getattr(signal, sig_name, None) is not None
    ]

    # SIGUSR1/SIGUSR2: on-demand dump triggered by the user, written to every
    # output stream (faulthandler.register() only supports one stream).
    _dump_streams = _unique_streams(target_stream)

    def _on_dump_signal(signum, frame, streams=_dump_streams):
        for s in streams:
            try:
                faulthandler.dump_traceback(file=s, all_threads=True)
                s.flush()
            except Exception:
                pass

    for sig_name in ("SIGUSR1", "SIGUSR2"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _on_dump_signal)
        except (OSError, ValueError) as exc:
            logger.warning("Failed to register fault dump signal %s: %s", sig_name, exc)

    # Windows has no SIGUSR1/SIGUSR2: use SIGBREAK (Ctrl+Break) instead.
    if sys.platform == "win32":
        sig_break = getattr(signal, "SIGBREAK", None)
        if sig_break is not None:
            try:
                signal.signal(sig_break, _on_dump_signal)
                logger.info("Windows: on-demand thread dump registered on SIGBREAK (Ctrl+Break)")
            except (OSError, ValueError) as exc:
                logger.warning("Failed to register SIGBREAK handler: %s", exc)

    # Watchdog: periodically write all-thread stacks so the last snapshot is
    # available even if the process dies without a Python-visible signal.
    try:
        _watchdog_interval = int(os.environ.get("CV_STUDIO_WATCHDOG_INTERVAL", "30"))
    except ValueError:
        _watchdog_interval = 30
    if _watchdog_interval > 0 and target_stream is not None:
        try:
            faulthandler.dump_traceback_later(
                _watchdog_interval, repeat=True, file=target_stream, exit=False
            )
            logger.info(
                "Fault watchdog enabled: full thread dump every %ds", _watchdog_interval
            )
            if _fault_log_file_handle is not None:
                threading.Thread(
                    target=_fault_log_housekeeping,
                    args=(_fault_log_file_handle, max(_watchdog_interval, 5)),
                    name="fault-log-housekeeping",
                    daemon=True,
                ).start()
        except Exception as exc:
            logger.warning("Failed to start faulthandler watchdog: %s", exc)

    install_exception_hooks()
    logger.info(
        "Fault diagnostics enabled (fault trace output: %s) — crash signals: %s",
        resolved_path or "stderr",
        ", ".join(_registered_signals) if _registered_signals else "none",
    )


def _close_fault_log_file():
    global _fault_log_file_handle
    if _fault_log_file_handle is not None:
        file_handle = _fault_log_file_handle
        try:
            # Cancel the watchdog before closing the file so it doesn't write to
            # the closed file descriptor after this point.
            try:
                faulthandler.cancel_dump_traceback_later()
            except Exception:
                pass
            file_handle.flush()
            file_handle.close()
            if sys.stderr is not None:
                try:
                    faulthandler.enable(file=sys.stderr, all_threads=True)
                except Exception:
                    pass
        finally:
            _fault_log_file_handle = None
