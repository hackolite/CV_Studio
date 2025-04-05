#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cv2
import numpy as np
import dearpygui.dearpygui as dpg




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
    if dpg.does_item_exist(tag):
        dpg.set_value(tag, value)


def dpg_get_value(tag):
    value = None
    if dpg.does_item_exist(tag):
        value = dpg.get_value(tag)
    return value
