#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression tests for deterministic cross-platform node discovery."""

import os


def test_node_editor_discovers_only_node_modules():
    """Node menus should scan only concrete node_*.py modules."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    node_main_path = os.path.join(repo_root, "node_editor", "node_main.py")

    with open(node_main_path, "r", encoding="utf-8") as f:
        source = f.read()

    assert '"node_*.py"' in source


def test_node_editor_sorts_discovered_modules():
    """Node discovery must be sorted so Linux/Windows show the same menu order."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    node_main_path = os.path.join(repo_root, "node_editor", "node_main.py")

    with open(node_main_path, "r", encoding="utf-8") as f:
        source = f.read()

    assert "sorted(glob(node_sources_path))" in source
