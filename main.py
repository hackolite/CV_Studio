#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import copy
import json
import asyncio
import argparse
from collections import OrderedDict
import os
import serial 
import cv2  
import dearpygui.dearpygui as dpg


from node_editor.util import check_camera_connection
from node_editor.node_editor import DpgNodeEditor


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--setting",
        type=str,
        # get abs
        default=os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         'node_editor/setting/setting.json')),
    )
    parser.add_argument("--unuse_async_draw", action="store_true")
    parser.add_argument("--use_debug_print", action="store_true")
    args = parser.parse_args()
    return args


def async_main(node_editor):

    node_image_dict = {}
    node_result_dict = {}

    while not node_editor.get_terminate_flag():
        update_node_info(node_editor, node_image_dict, node_result_dict)


def update_node_info(
    node_editor,
    node_image_dict,
    node_result_dict,
    mode_async=True,
):
        
    editor_width = dpg.get_viewport_client_width()
    editor_height = dpg.get_viewport_client_height()
    
    print(editor_width, editor_height)
    print(node_editor.window)
    
    try:
        dpg.set_item_pos(node_editor.window, [0, 0])
        dpg.set_item_width(node_editor.window, dpg.get_viewport_client_width())
        dpg.set_item_height(node_editor.window, dpg.get_viewport_client_height())
    except Exception as e:
        print(e)
		
    node_list = node_editor.get_node_list()

    sorted_node_connection_dict = node_editor.get_sorted_node_connection()

    for node_id_name in node_list:

        if node_id_name not in node_image_dict:
            node_image_dict[node_id_name] = None

        node_id, _ = node_id_name.split(':')
        connection_list = sorted_node_connection_dict.get(node_id_name, [])
        node_instance = node_editor.get_node_instances(node_id_name)

        if mode_async:
            try:
                data = node_instance.update(
                    node_id,
                    connection_list,
                    node_image_dict,
                    node_result_dict,
                )
            except Exception as e:
                print(e)
                sys.exit()
        else:
            data = node_instance.update(
                node_id,
                connection_list,
                node_image_dict,
                node_result_dict,
            )

        
        node_image_dict[node_id_name] = copy.deepcopy(data["image"])
        node_result_dict[node_id_name] = copy.deepcopy(data["json"])


    
def main():

    args = get_args()
    setting = args.setting
    unuse_async_draw = args.unuse_async_draw
    use_debug_print = args.use_debug_print


    print('**** Load Config ********')
    opencv_setting_dict = None
    with open(setting) as fp:
        opencv_setting_dict = json.load(fp)
    webcam_width = opencv_setting_dict['webcam_width']
    webcam_height = opencv_setting_dict['webcam_height']


    print('**** Check Camera Connection ********')
    device_no_list = check_camera_connection()
    camera_capture_list = []
    for device_no in device_no_list:
        video_capture = cv2.VideoCapture(device_no)
        video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, webcam_width)
        video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, webcam_height)
        camera_capture_list.append(video_capture)


    opencv_setting_dict['device_no_list'] = device_no_list
    opencv_setting_dict['camera_capture_list'] = camera_capture_list


    editor_width = opencv_setting_dict['editor_width']
    editor_height = opencv_setting_dict['editor_height']


    serial_device_no_list = []
    serial_connection_list = []
    use_serial = opencv_setting_dict['use_serial']
    if use_serial == True:
        try:
            from .node_editor.util import check_serial_connection
        except:
            from node_editor.util import check_serial_connection
        print('**** Check Serial Device Connection ********')
        serial_device_no_list = check_serial_connection()
        for serial_device_no in serial_device_no_list:
            ser = serial.Serial(serial_device_no,115200)
            serial_connection_list.append(ser)
        

    opencv_setting_dict['serial_device_no_list'] = serial_device_no_list
    opencv_setting_dict['serial_connection_list'] = serial_connection_list

    print('**** DearPyGui Setup ********')
    
    dpg.create_context()
    dpg.setup_dearpygui()
    dpg.create_viewport(
        title="CV_STUDIO",
        width=editor_width,
        height=editor_height,
    )


    current_path = os.path.dirname(os.path.abspath(__file__))
    with dpg.font_registry():
        with dpg.font(
                current_path +
                '/node_editor/font/YasashisaAntiqueFont/07YasashisaAntique.otf',
                16,
        ) as default_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Japanese)
    dpg.bind_font(default_font)

    print('**** Create NodeEditor ********')
    menu_dict = OrderedDict({
        'Input': 'InputNode',
        'VisionProcess': 'ProcessNode',
        'VisionModel': 'DLNode',
        'Stats': 'StatsNode ',
        'Trigger': 'TriggerNode',
        'Router' : 'RouterNode',
        'Action' : 'ActionNode',
        'Video' : 'VideoNode',
        'Tracking': 'TrackerNode',
        'Overlay': 'OverlayNode',
        'Viz': 'VizNode',
        'TimeseriesML': 'TimeseriesNode',

    })


    dpg.show_viewport(maximized=True)

    
    node_editor = DpgNodeEditor(
        width=editor_width,
        height=editor_height,
        opencv_setting_dict=opencv_setting_dict,
        menu_dict=menu_dict,
        use_debug_print=use_debug_print,
        node_dir=current_path + '/node',
    )

    print('**** Start Main Event Loop ********')
    if not unuse_async_draw:
        print("asyncdraw is enabled")
        event_loop = asyncio.get_event_loop()
        event_loop.run_in_executor(None, async_main, node_editor)
        dpg.start_dearpygui()
    
    else:
        print("asyncdraw is disabled")
        node_image_dict = {}
        node_result_dict = {}
        while dpg.is_dearpygui_running():
            update_node_info(
                node_editor,
                node_image_dict,
                node_result_dict,
                mode_async=False,
            )
            dpg.render_dearpygui_frame()


    print('**** Terminate process ********')

    print('**** Close All Node ********')
    node_list = node_editor.get_node_list()
    for node_id_name in node_list:
        node_id, node_name = node_id_name.split(':')
        node_instance = node_editor.get_node_instances(node_name)
        node_instance.close(node_id)

    print('**** Release All VideoCapture ********')
    for camera_capture in camera_capture_list:
        camera_capture.release()

    print('**** Stop Event Loop ********')
    node_editor.set_terminate_flag()
    event_loop.stop()

    print('**** Destroy DearPyGui Context ********')
    dpg.destroy_context()


if __name__ == '__main__':
    main()
