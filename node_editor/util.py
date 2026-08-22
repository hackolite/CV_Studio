#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cv2
import logging
import numpy as np
import threading
import dearpygui.dearpygui as dpg

# Global lock for thread-safe DearPyGUI operations
# RLock (reentrant lock) allows the same thread to acquire the lock multiple times,
# which is necessary when nested DearPyGUI calls occur within the same thread.
# This protects against race conditions between:
# - Main thread: Processing UI events via dpg.start_dearpygui()
# - Worker thread: Updating nodes via async_main() in thread executor
_dpg_lock = threading.RLock()

logger = logging.getLogger(__name__)


def check_camera_connection(max_device_count=4, is_debug=False):
    device_no_list = []

    for device_no in range(0, max_device_count):
        if is_debug:
            print('Check Device No:' + str(device_no).zfill(2), end='')

        cap = cv2.VideoCapture(device_no)
        ret, _ = cap.read()
        if ret:
            device_no_list.append(device_no)
            if is_debug:
                print(' -> Find')
        else:
            if is_debug:
                print(' -> None')

    return device_no_list

def check_serial_connection(is_debug=False):
    import glob
    import serial
    import sys
    serial_device_no_list=[]
    serial_device_no_list=[]
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            serial_device_no_list.append(port)
        except (OSError, serial.SerialException):
            pass
    return serial_device_no_list

def dpg_set_value(tag, value):
    with _dpg_lock:
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, value)


def dpg_get_value(tag):
    value = None
    with _dpg_lock:
        if dpg.does_item_exist(tag):
            value = dpg.get_value(tag)
    return value


def dpg_configure_item(tag, **kwargs):
    """Thread-safe wrapper for dpg.configure_item.

    Silently skips when the item no longer exists (e.g. the node was deleted
    between the update snapshot and the configure call) and logs all errors so
    that crashes are never silent.
    """
    with _dpg_lock:
        try:
            if dpg.does_item_exist(tag):
                dpg.configure_item(tag, **kwargs)
            else:
                logger.debug("dpg_configure_item: tag %s does not exist, skipping", tag)
        except Exception as exc:
            logger.error(
                "dpg_configure_item: failed for tag %s: %s",
                tag, exc, exc_info=True,
            )


def dpg_delete_item(tag):
    """Thread-safe wrapper for dpg.delete_item.

    Silently skips when the item no longer exists and logs all errors so that
    crashes are never silent.
    """
    with _dpg_lock:
        try:
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)
            else:
                logger.debug("dpg_delete_item: tag %s does not exist, skipping", tag)
        except Exception as exc:
            logger.error(
                "dpg_delete_item: failed for tag %s: %s",
                tag, exc, exc_info=True,
            )
