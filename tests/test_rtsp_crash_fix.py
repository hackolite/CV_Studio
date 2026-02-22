#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests to verify that RTSP/HLS stream crashes do not kill the main application.

The fix ensures that:
1. Stream capture always runs in a subprocess (use_multiprocessing_rtsp/hls = True by default)
   so that a segfault in the native FFMPEG code only crashes the subprocess, not the main app.
2. receive_image_process is wrapped in try/except to handle Python-level errors gracefully
   and reconnect automatically.
3. The update() method monitors the subprocess health and restarts it if it has died.
"""
import sys
import os
import multiprocessing as mp
import time
import unittest.mock as mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock DearPyGUI before importing the nodes
sys.modules['dearpygui'] = mock.MagicMock()
sys.modules['dearpygui.dearpygui'] = mock.MagicMock()

import json


def test_setting_json_uses_multiprocessing_by_default():
    """Verify that setting.json enables multiprocessing for RTSP and HLS by default."""
    setting_path = os.path.join(
        os.path.dirname(__file__), '..', 'node_editor', 'setting', 'setting.json'
    )
    with open(setting_path) as f:
        settings = json.load(f)

    assert settings.get('use_multiprocessing_rtsp') is True, \
        "use_multiprocessing_rtsp should be True to isolate stream crashes from the main process"
    assert settings.get('use_multiprocessing_hls') is True, \
        "use_multiprocessing_hls should be True to isolate stream crashes from the main process"


def test_receive_image_process_rtsp_handles_exception():
    """
    Verify that receive_image_process for RTSP handles exceptions and continues running
    rather than crashing the subprocess with an unhandled exception.
    """
    from node.InputNode.node_rtsp import receive_image_process

    image_queue = mp.Queue(maxsize=1)
    request = mp.Value('i', 1)

    # Stop immediately after one iteration attempt
    def stop_soon():
        time.sleep(0.2)
        request.value = 0

    stopper = mp.Process(target=stop_soon)
    stopper.start()

    # Run in a subprocess - it should not raise an unhandled exception
    # (even with an invalid URL that causes an error)
    proc = mp.Process(
        target=receive_image_process,
        args=('rtsp://invalid-url-that-does-not-exist', image_queue, request),
    )
    proc.start()
    proc.join(timeout=3)
    stopper.join(timeout=1)

    # The process should have exited cleanly (not due to uncaught exception)
    # exit code 0 or -15 (SIGTERM) are acceptable; only non-zero codes from
    # unhandled exceptions (e.g. 1) indicate a problem
    assert proc.exitcode is not None, "Process should have exited"
    assert proc.exitcode in (0, -15, -2), \
        f"Process exit code {proc.exitcode} indicates an unhandled exception crashed it"


def test_receive_image_process_hls_handles_exception():
    """
    Verify that receive_image_process for HLS handles exceptions and continues running
    rather than crashing the subprocess with an unhandled exception.
    """
    from node.InputNode.node_hls import receive_image_process

    image_queue = mp.Queue(maxsize=1)
    request = mp.Value('i', 1)

    def stop_soon():
        time.sleep(0.2)
        request.value = 0

    stopper = mp.Process(target=stop_soon)
    stopper.start()

    proc = mp.Process(
        target=receive_image_process,
        args=('http://invalid-hls-url-that-does-not-exist/stream.m3u8', image_queue, request),
    )
    proc.start()
    proc.join(timeout=3)
    stopper.join(timeout=1)

    assert proc.exitcode is not None, "Process should have exited"
    assert proc.exitcode in (0, -15, -2), \
        f"Process exit code {proc.exitcode} indicates an unhandled exception crashed it"


def test_rtsp_node_restarts_dead_subprocess():
    """
    Verify that RtspNode.update() detects a dead subprocess and restarts it.
    """
    from node.InputNode.node_rtsp import RtspNode, receive_image_process

    node = RtspNode()
    node._opencv_setting_dict = {
        'input_window_width': 240,
        'input_window_height': 135,
        'use_pref_counter': False,
        'use_multiprocessing_rtsp': True,
    }

    rtsp_url = 'rtsp://dummy-url'

    # Simulate a dead process
    dead_process = mp.Process(target=lambda: None)
    dead_process.start()
    dead_process.join()  # Let it finish so it's "dead"

    node._image_queue[rtsp_url] = mp.Queue(maxsize=1)
    node._request[rtsp_url] = mp.Value('i', 1)
    node._process[rtsp_url] = dead_process

    assert not node._process[rtsp_url].is_alive(), "Process should be dead before test"

    # Mock dpg_get_value to return our URL
    with mock.patch('node.InputNode.node_rtsp.dpg_get_value', return_value=rtsp_url), \
         mock.patch('node.InputNode.node_rtsp.dpg_set_value'):
        # Call update - it should detect the dead process and restart it
        node.update(
            node_id=1,
            connection_list=[],
            node_image_dict={},
            node_result_dict={},
            node_audio_dict={},
        )

    # Verify a new process was created and started
    assert node._process[rtsp_url] is not dead_process, \
        "A new process should have been created to replace the dead one"
    assert node._process[rtsp_url].is_alive(), \
        "The replacement process should be running"

    # Clean up
    node._request[rtsp_url].value = 0
    node._process[rtsp_url].terminate()
    node._process[rtsp_url].join(timeout=2)


def test_hls_node_restarts_dead_subprocess():
    """
    Verify that HlsNode.update() detects a dead subprocess and restarts it.
    """
    from node.InputNode.node_hls import HlsNode, receive_image_process

    node = HlsNode()
    node._opencv_setting_dict = {
        'input_window_width': 240,
        'input_window_height': 135,
        'use_pref_counter': False,
        'use_multiprocessing_hls': True,
    }

    hls_url = 'http://dummy-hls-url/stream.m3u8'

    dead_process = mp.Process(target=lambda: None)
    dead_process.start()
    dead_process.join()

    node._image_queue[hls_url] = mp.Queue(maxsize=1)
    node._request[hls_url] = mp.Value('i', 1)
    node._process[hls_url] = dead_process

    assert not node._process[hls_url].is_alive(), "Process should be dead before test"

    with mock.patch('node.InputNode.node_hls.dpg_get_value', return_value=hls_url), \
         mock.patch('node.InputNode.node_hls.dpg_set_value'):
        node.update(
            node_id=1,
            connection_list=[],
            node_image_dict={},
            node_result_dict={},
            node_audio_dict={},
        )

    assert node._process[hls_url] is not dead_process, \
        "A new process should have been created to replace the dead one"
    assert node._process[hls_url].is_alive(), \
        "The replacement process should be running"

    # Clean up
    node._request[hls_url].value = 0
    node._process[hls_url].terminate()
    node._process[hls_url].join(timeout=2)


if __name__ == '__main__':
    print("Testing RTSP/HLS crash fix...")
    print("=" * 60)

    tests = [
        ("setting.json uses multiprocessing by default",
         test_setting_json_uses_multiprocessing_by_default),
        ("receive_image_process RTSP handles exception",
         test_receive_image_process_rtsp_handles_exception),
        ("receive_image_process HLS handles exception",
         test_receive_image_process_hls_handles_exception),
        ("RtspNode restarts dead subprocess",
         test_rtsp_node_restarts_dead_subprocess),
        ("HlsNode restarts dead subprocess",
         test_hls_node_restarts_dead_subprocess),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\nTesting {name}...")
        try:
            test_func()
            print(f"✓ {name} passed")
            passed += 1
        except AssertionError as e:
            print(f"✗ {name} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name} error: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
