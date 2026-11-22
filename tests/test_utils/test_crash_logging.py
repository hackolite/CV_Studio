#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Crash traces must always reach an easily accessible log file.

The scenarios run in subprocesses because they terminate the interpreter
(segfault, uncaught exception) and because they cover the "no console"
situation (``sys.stderr is None``) of a windowed executable.
"""

import os
import subprocess
import sys
import textwrap

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _run(script, log_dir, extra_env=None):
    env = dict(os.environ, CV_STUDIO_LOG_DIR=str(log_dir), CV_STUDIO_WATCHDOG_INTERVAL="0")
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_log_dir_honours_environment_variable(tmp_path, monkeypatch):
    import src.utils.logging as cvlog

    monkeypatch.setenv(cvlog.LOG_DIR_ENV, str(tmp_path / "custom"))
    monkeypatch.setattr(cvlog, "_log_dir_cache", None)
    assert cvlog.get_log_dir() == str(tmp_path / "custom")
    assert os.path.isdir(cvlog.get_log_dir())
    assert cvlog.get_default_log_file().endswith("cv_studio.log")
    assert cvlog.get_default_fault_log_file().endswith("cv_studio_fault.log")


def test_setup_logging_writes_a_file_on_every_platform(tmp_path, monkeypatch):
    import logging
    import src.utils.logging as cvlog

    monkeypatch.setenv(cvlog.LOG_DIR_ENV, str(tmp_path))
    monkeypatch.setattr(cvlog, "_log_dir_cache", None)
    logger = cvlog.setup_logging(level=logging.INFO)
    try:
        logger.info("hello from test")
        for handler in logger.handlers:
            handler.flush()
        assert cvlog.get_active_log_files() == [str(tmp_path / "cv_studio.log")]
        assert "hello from test" in (tmp_path / "cv_studio.log").read_text(encoding="utf-8")
    finally:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()


def test_uncaught_exception_before_logging_setup_is_recorded(tmp_path):
    result = _run(
        """
        import sys
        sys.path.insert(0, ".")
        from src.utils.logging import install_exception_hooks
        install_exception_hooks()
        raise RuntimeError("boom before setup_logging")
        """,
        tmp_path,
    )
    assert result.returncode == 1
    content = (tmp_path / "cv_studio.log").read_text(encoding="utf-8")
    assert "CRASH - Unhandled exception" in content
    assert "RuntimeError: boom before setup_logging" in content
    assert "boom before setup_logging" in result.stderr


def test_thread_exception_is_recorded_in_log_file(tmp_path):
    result = _run(
        """
        import sys, threading, logging
        sys.path.insert(0, ".")
        from src.utils.logging import setup_logging
        setup_logging(level=logging.INFO)
        def worker():
            raise ValueError("worker exploded")
        t = threading.Thread(target=worker, name="worker-1")
        t.start(); t.join()
        logging.shutdown()
        """,
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    content = (tmp_path / "cv_studio.log").read_text(encoding="utf-8")
    assert "Unhandled exception in thread 'worker-1'" in content
    assert "ValueError: worker exploded" in content


@pytest.mark.skipif(sys.platform == "win32", reason="ctypes segfault semantics differ on Windows")
@pytest.mark.parametrize("console", [True, False], ids=["console", "no-console"])
def test_segfault_trace_is_written_to_fault_log(tmp_path, console):
    result = _run(
        f"""
        import sys, ctypes, logging
        sys.path.insert(0, ".")
        if not {console!r}:
            sys.stderr = None
            sys.stdout = None
        from src.utils.logging import setup_logging
        from src.utils.fault_diagnostics import configure_fault_diagnostics, get_fault_log_path
        setup_logging(level=logging.INFO)
        configure_fault_diagnostics()
        logging.getLogger("t").info("fault log: %s", get_fault_log_path())
        ctypes.string_at(0)
        """,
        tmp_path,
    )
    assert result.returncode != 0
    app_log = (tmp_path / "cv_studio.log").read_text(encoding="utf-8")
    assert f"fault log: {tmp_path / 'cv_studio_fault.log'}" in app_log
    fault_log = (tmp_path / "cv_studio_fault.log").read_text(encoding="utf-8")
    assert "CV_STUDIO session started" in fault_log
    assert "Segmentation fault" in fault_log
    assert "string_at" in fault_log


def test_explicit_fault_log_path_is_used(tmp_path):
    custom = tmp_path / "sub" / "my_fault.log"
    result = _run(
        f"""
        import sys, logging
        sys.path.insert(0, ".")
        from src.utils.logging import setup_logging
        from src.utils.fault_diagnostics import configure_fault_diagnostics, get_fault_log_path
        setup_logging(level=logging.INFO)
        configure_fault_diagnostics({str(custom)!r})
        print(get_fault_log_path())
        """,
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(custom)
    assert custom.exists()
