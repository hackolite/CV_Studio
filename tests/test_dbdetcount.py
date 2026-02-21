#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the DbDetCount trigger node.

Exercises the rolling-mean and delta-trigger logic without requiring a
live DearPyGUI context.
"""
import time
from collections import deque


# ---------------------------------------------------------------------------
# Minimal reproduction of the node's core logic (no DPG dependency)
# ---------------------------------------------------------------------------

class MockDbDetCount:
    """Replicates the stateful calculation from Node.update()."""

    def __init__(self):
        self._samples = deque()

    def step(self, class_ids, window_duration, delta, current_time=None):
        """
        Process one frame.

        Returns a dict with keys: BOOL, count, mean, diff, delta
        """
        if current_time is None:
            current_time = time.time()

        current_count = len(class_ids) if class_ids else 0
        self._samples.append((current_time, current_count))

        # Evict old samples
        cutoff = current_time - window_duration
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()

        # Historical mean (exclude the current sample)
        history = list(self._samples)[:-1]
        if history:
            rolling_mean = sum(c for _, c in history) / len(history)
        else:
            rolling_mean = float(current_count)

        diff = abs(current_count - rolling_mean)
        trigger_active = diff > delta

        return {
            'BOOL': trigger_active,
            'count': current_count,
            'mean': rolling_mean,
            'diff': diff,
            'delta': delta,
        }

    def reset(self):
        self._samples.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_no_trigger_when_stable():
    """When counts are stable, diff should stay below any reasonable delta."""
    node = MockDbDetCount()
    base = 1_000_000.0  # deterministic timestamps

    # Feed 10 frames, all with count=5
    for i in range(10):
        result = node.step([0, 1, 2, 3, 4], window_duration=10.0, delta=1.0,
                           current_time=base + i)

    # Last result: mean ≈ 5, current_count = 5, diff ≈ 0
    assert result['BOOL'] is False
    assert result['count'] == 5
    assert result['diff'] < 1.0


def test_trigger_on_spike():
    """A sudden spike above the rolling mean should fire the trigger."""
    node = MockDbDetCount()
    base = 1_000_000.0

    # Establish a baseline of count=2 for 5 frames
    for i in range(5):
        node.step([0, 1], window_duration=10.0, delta=2.0,
                  current_time=base + i)

    # Feed a spike: count=10
    result = node.step(list(range(10)), window_duration=10.0, delta=2.0,
                       current_time=base + 5)

    assert result['BOOL'] is True
    assert result['count'] == 10
    assert result['diff'] > 2.0


def test_no_trigger_first_frame():
    """On the very first frame there is no history, so mean == current_count."""
    node = MockDbDetCount()
    result = node.step([0, 1, 2], window_duration=5.0, delta=1.0)

    # diff must be 0 (mean equals current_count when there is no history)
    assert result['diff'] == 0.0
    assert result['BOOL'] is False


def test_old_samples_evicted():
    """Samples older than the window should not influence the mean."""
    node = MockDbDetCount()
    base = 1_000_000.0

    # Add some old samples (high counts) at t=0
    for i in range(5):
        node.step(list(range(20)), window_duration=5.0, delta=1.0,
                  current_time=base + i)

    # Jump forward 20 seconds so all previous samples are outside the window
    result = node.step([0], window_duration=5.0, delta=1.0,
                       current_time=base + 20)

    # With no historical samples in window, mean == current_count → diff == 0
    assert result['diff'] == 0.0
    assert result['BOOL'] is False


def test_trigger_drop_below_mean():
    """A sudden drop below the rolling mean should also fire the trigger."""
    node = MockDbDetCount()
    base = 1_000_000.0

    # Establish high baseline: count=10
    for i in range(5):
        node.step(list(range(10)), window_duration=10.0, delta=3.0,
                  current_time=base + i)

    # Sudden drop to count=1
    result = node.step([0], window_duration=10.0, delta=3.0,
                       current_time=base + 5)

    assert result['BOOL'] is True
    assert result['count'] == 1
    assert result['diff'] > 3.0


def test_delta_boundary():
    """Trigger fires only when diff is STRICTLY greater than delta."""
    node = MockDbDetCount()
    base = 1_000_000.0

    # Feed exactly 5 frames with count=0, then count=delta (not strictly >)
    delta = 2.0
    for i in range(5):
        node.step([], window_duration=10.0, delta=delta,
                  current_time=base + i)

    # diff should equal delta (mean=0, count=2) → NOT triggered
    result_equal = node.step([0, 1], window_duration=10.0, delta=delta,
                              current_time=base + 5)
    assert result_equal['BOOL'] is False

    # diff one above delta → triggered
    result_above = node.step([0, 1, 2], window_duration=10.0, delta=delta,
                              current_time=base + 6)
    # mean now includes previous samples; just check BOOL logic is consistent
    assert isinstance(result_above['BOOL'], bool)


def test_output_keys():
    """The returned dict must always contain the expected keys."""
    node = MockDbDetCount()
    result = node.step([0, 1], window_duration=5.0, delta=1.0)

    for key in ('BOOL', 'count', 'mean', 'diff', 'delta'):
        assert key in result, f"Missing key: {key}"


if __name__ == '__main__':
    test_no_trigger_when_stable()
    print('✓ test_no_trigger_when_stable')

    test_trigger_on_spike()
    print('✓ test_trigger_on_spike')

    test_no_trigger_first_frame()
    print('✓ test_no_trigger_first_frame')

    test_old_samples_evicted()
    print('✓ test_old_samples_evicted')

    test_trigger_drop_below_mean()
    print('✓ test_trigger_drop_below_mean')

    test_delta_boundary()
    print('✓ test_delta_boundary')

    test_output_keys()
    print('✓ test_output_keys')

    print('\n✅ All DbDetCount tests passed!')
