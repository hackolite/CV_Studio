#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify crash dump logging when multiple buzzers play simultaneously.
Simulates the scenario where 3 buzzer nodes all trigger at the same time,
which previously caused a crash due to concurrent sounddevice access.
"""
import sys
import os
import time
import threading
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock heavy dependencies not available in CI
for mod in ("sounddevice", "dearpygui", "dearpygui.dearpygui"):
    sys.modules.setdefault(mod, MagicMock())

# Mock node_editor.util and node dependencies
sys.modules.setdefault("node_editor", MagicMock())
sys.modules.setdefault("node_editor.util", MagicMock())
sys.modules.setdefault("node.node_abc", MagicMock())
sys.modules.setdefault("node.basenode", MagicMock())

# Provide a real BaseNode mock with proper __init__
class _FakeBaseNode:
    def __init__(self):
        pass

sys.modules["node.basenode"].Node = _FakeBaseNode

def test_multi_buzzer_no_crash():
    """3 buzzer nodes triggering simultaneously should not crash."""
    from node.ActionNode.node_buzzer import BuzzerNode, _sd_playback_lock, _active_buzzers, _active_buzzers_lock

    nodes = []
    for i in range(3):
        node = BuzzerNode()
        node.tag_node_name = f"{i}:Buzzer"
        nodes.append(node)

    # Register all nodes
    with _active_buzzers_lock:
        for node in nodes:
            _active_buzzers[node.tag_node_name] = node

    # Mock sd.play and sd.wait to simulate playback without audio hardware
    with patch("node.ActionNode.node_buzzer.sd") as mock_sd:
        mock_sd.play = MagicMock()
        mock_sd.wait = MagicMock(side_effect=lambda: time.sleep(0.05))

        threads = []
        for node in nodes:
            t = threading.Thread(
                target=node._play_buzz_thread,
                args=(0.1, "Default Buzzer"),
                daemon=True,
            )
            threads.append(t)

        # Start all 3 threads simultaneously
        for t in threads:
            t.start()

        # Wait for all to finish
        for t in threads:
            t.join(timeout=5)

        # All threads should have completed (no crash)
        for t in threads:
            assert not t.is_alive(), "Thread should have completed"

        # sd.play should have been called 3 times (sequentially due to lock)
        assert mock_sd.play.call_count == 3

    # Cleanup
    with _active_buzzers_lock:
        for node in nodes:
            _active_buzzers.pop(node.tag_node_name, None)


def test_crash_dump_written_on_error():
    """When sd.play raises, a crash dump file should be created."""
    from node.ActionNode.node_buzzer import BuzzerNode, _BUZZER_LOG_DIR, _active_buzzers, _active_buzzers_lock

    node = BuzzerNode()
    node.tag_node_name = "99:Buzzer"

    with _active_buzzers_lock:
        _active_buzzers[node.tag_node_name] = node

    # Make sd.play raise an exception to simulate crash
    with patch("node.ActionNode.node_buzzer.sd") as mock_sd:
        mock_sd.play = MagicMock(side_effect=RuntimeError("Device unavailable"))
        mock_sd.wait = MagicMock()

        node._play_buzz_thread(0.5, "Default Buzzer")

    # Verify crash dump was written
    dump_files = [f for f in os.listdir(_BUZZER_LOG_DIR) if f.startswith("crash_dump_")]
    assert len(dump_files) > 0, "A crash dump file should have been created"

    # Read and verify contents of the latest dump
    latest_dump = sorted(dump_files)[-1]
    dump_path = os.path.join(_BUZZER_LOG_DIR, latest_dump)
    with open(dump_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "BUZZER CRASH DUMP" in content
    assert "Device unavailable" in content
    assert "99:Buzzer" in content
    assert "Active Buzzer Nodes" in content

    # Cleanup
    os.remove(dump_path)
    with _active_buzzers_lock:
        _active_buzzers.pop(node.tag_node_name, None)


def test_lock_prevents_concurrent_sd_play():
    """The global lock ensures sd.play() is never called concurrently."""
    from node.ActionNode.node_buzzer import BuzzerNode

    call_times = []
    call_lock = threading.Lock()

    def mock_play(audio, samplerate=None):
        with call_lock:
            call_times.append(("start", time.time()))
        time.sleep(0.05)
        with call_lock:
            call_times.append(("end", time.time()))

    nodes = [BuzzerNode() for _ in range(3)]
    for i, node in enumerate(nodes):
        node.tag_node_name = f"{i}:Buzzer"

    with patch("node.ActionNode.node_buzzer.sd") as mock_sd:
        mock_sd.play = MagicMock(side_effect=mock_play)
        mock_sd.wait = MagicMock()

        threads = []
        for node in nodes:
            t = threading.Thread(
                target=node._play_buzz_thread,
                args=(0.1, "Default Buzzer"),
                daemon=True,
            )
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

    # Verify no overlapping play calls
    starts = [t for label, t in call_times if label == "start"]
    ends = [t for label, t in call_times if label == "end"]

    for i in range(1, len(starts)):
        # Each start should be after the previous end
        assert starts[i] >= ends[i - 1] - 0.001, (
            f"Concurrent sd.play detected: start[{i}]={starts[i]:.4f} < end[{i-1}]={ends[i-1]:.4f}"
        )


if __name__ == "__main__":
    test_multi_buzzer_no_crash()
    print("✓ test_multi_buzzer_no_crash passed")

    test_crash_dump_written_on_error()
    print("✓ test_crash_dump_written_on_error passed")

    test_lock_prevents_concurrent_sd_play()
    print("✓ test_lock_prevents_concurrent_sd_play passed")

    print("\nAll multi-buzzer crash tests passed!")
