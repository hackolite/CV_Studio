#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the Clock trigger node interval logic."""
import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock external dependencies before importing the node
sys.modules['dearpygui'] = MagicMock()
sys.modules['dearpygui.dearpygui'] = MagicMock()
sys.modules['cv2'] = MagicMock()
sys.modules['numpy'] = MagicMock()
sys.modules['node_editor'] = MagicMock()
sys.modules['node_editor.util'] = MagicMock()
sys.modules['node.node_abc'] = MagicMock()

from node.TriggerNode.node_clock import _parse_hhmm, _in_interval


class TestParseHHMM:
    def test_valid(self):
        assert _parse_hhmm("08:30") == (8, 30)
        assert _parse_hhmm("00:00") == (0, 0)
        assert _parse_hhmm("23:59") == (23, 59)

    def test_with_spaces(self):
        assert _parse_hhmm(" 12:00 ") == (12, 0)

    def test_invalid_format(self):
        assert _parse_hhmm("8h30") is None
        assert _parse_hhmm("25:00") is None
        assert _parse_hhmm("12:60") is None
        assert _parse_hhmm("") is None
        assert _parse_hhmm("abc") is None


class TestInInterval:
    def test_normal_interval_inside(self):
        # 14:00 is in [08:00, 18:00]
        assert _in_interval(14, 0, 8, 0, 18, 0) is True

    def test_normal_interval_outside(self):
        # 07:59 is not in [08:00, 18:00]
        assert _in_interval(7, 59, 8, 0, 18, 0) is False

    def test_normal_interval_boundary(self):
        assert _in_interval(8, 0, 8, 0, 18, 0) is True
        assert _in_interval(18, 0, 8, 0, 18, 0) is True

    def test_overnight_interval_inside_before_midnight(self):
        # 23:00 is in [22:00, 06:00]
        assert _in_interval(23, 0, 22, 0, 6, 0) is True

    def test_overnight_interval_inside_after_midnight(self):
        # 03:00 is in [22:00, 06:00]
        assert _in_interval(3, 0, 22, 0, 6, 0) is True

    def test_overnight_interval_outside(self):
        # 12:00 is not in [22:00, 06:00]
        assert _in_interval(12, 0, 22, 0, 6, 0) is False

    def test_midnight_exact(self):
        # 00:00 is in [22:00, 06:00]
        assert _in_interval(0, 0, 22, 0, 6, 0) is True

    def test_same_start_end(self):
        # When start == end, only that exact minute matches
        assert _in_interval(12, 0, 12, 0, 12, 0) is True
        assert _in_interval(12, 1, 12, 0, 12, 0) is False
