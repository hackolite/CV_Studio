import importlib.util
import os

# Import YoloCls from the yolo-cls.py file (which has a hyphen)
_module_path = os.path.join(os.path.dirname(__file__), "yolo-cls.py")
_spec = importlib.util.spec_from_file_location("yolo_cls_module", _module_path)
_yolo_cls_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_yolo_cls_module)

YoloCls = _yolo_cls_module.YoloCls

