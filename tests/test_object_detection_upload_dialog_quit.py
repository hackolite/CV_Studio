#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the object detection upload preview quit button."""

import os


def _read_object_detection_source():
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    with open(file_path, 'r') as f:
        return f.read()


def test_upload_preview_defines_quit_button():
    """The upload preview should define a dedicated Quit button."""
    content = _read_object_detection_source()

    assert 'preview_quit_tag' in content, "Should define a tag for the Quit button"
    assert 'label="  Quit  "' in content, "Should create a Quit button in the preview dialog"
    assert 'show=False' in content, "Quit button should stay hidden until upload succeeds"


def test_upload_preview_toggles_buttons_after_success():
    """The dialog should switch from confirm/cancel to quit after success."""
    content = _read_object_detection_source()

    assert 'def _set_upload_preview_actions' in content, "Should centralize preview button visibility"
    assert 'dpg.configure_item(self.tag_preview_confirm, show=not upload_succeeded)' in content
    assert 'dpg.configure_item(self.tag_preview_cancel, show=not upload_succeeded)' in content
    assert 'dpg.configure_item(self.tag_preview_quit, show=upload_succeeded)' in content
    assert 'self._set_upload_preview_actions(upload_succeeded=True)' in content, \
        "Successful uploads should expose the Quit button"


def test_quit_button_closes_preview_dialog():
    """The Quit action should reuse the preview close handler."""
    content = _read_object_detection_source()

    assert 'def _close_upload_preview' in content, "Should provide a preview close helper"
    assert 'dpg.hide_item(self.tag_preview_window)' in content, \
        "Closing the dialog should hide the preview window"
