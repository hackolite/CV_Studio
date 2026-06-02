"""
Inference element mapper.

Maps CvStudio DL nodes to DeepStream nvinfer / nvinferserver configurations:
  - ObjectDetection → Primary GIE (PGIE)
  - Classification → Secondary GIE (SGIE)
  - PoseEstimation → Secondary GIE (SGIE) with custom post-processing
  - FaceDetection → Primary/Secondary GIE
  - SemanticSegmentation → Primary GIE with segmentation output
  - AudioClassification → Separate audio pipeline branch (metadata only)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from tools.deepstream_engine.parser import NodeInfo
from tools.deepstream_engine.hardware_profile import HardwareProfile, RTX_5070_PROFILE


# Map CvStudio model output_format to DeepStream network-type + parse config
_OUTPUT_FORMAT_MAP = {
    "yolox": {
        "network_type": "0",  # Detector
        "parse_func": "NvDsInferParseYoloX",
        "custom_lib": "libnvdsinfer_custom_impl_Yolo.so",
    },
    "yolo11": {
        "network_type": "0",  # Detector
        "parse_func": "NvDsInferParseYoloV8",
        "custom_lib": "libnvdsinfer_custom_impl_Yolo.so",
    },
}

INFERENCE_NODE_TAGS = {
    "ObjectDetection",
    "Classification",
    "PoseEstimation",
    "FaceDetection",
    "SemanticSegmentation",
}


@dataclass
class InferenceConfig:
    """DeepStream nvinfer configuration for a single model."""

    gie_id: int
    gie_type: str  # "primary" or "secondary"
    node_tag: str
    model_name: str = ""
    onnx_path: str = ""
    trt_engine_path: str = ""
    input_width: int = 640
    input_height: int = 640
    num_classes: int = 80
    output_format: str = "yolo11"
    score_threshold: float = 0.4
    nms_threshold: float = 0.45
    class_names: dict[int, str] = field(default_factory=dict)
    # DeepStream specifics
    network_type: int = 0  # 0=Detector, 1=Classifier, 2=Segmentation, 100=Other
    cluster_mode: int = 2  # NMS
    batch_size: int = 1
    interval: int = 0
    operate_on_gie_id: int = -1  # For SGIE: which PGIE to operate on
    config_entries: dict[str, Any] = field(default_factory=dict)


def map_inference(
    node: NodeInfo,
    gie_index: int = 0,
    is_primary: bool = True,
    profile: HardwareProfile = RTX_5070_PROFILE,
) -> InferenceConfig | None:
    """Convert a CvStudio DL node into DeepStream inference configuration."""
    tag = node.node_tag
    settings = node.settings

    if tag == "ObjectDetection":
        return _map_object_detection(node, gie_index, is_primary, profile)
    elif tag == "Classification":
        return _map_classification(node, gie_index, profile)
    elif tag == "PoseEstimation":
        return _map_pose_estimation(node, gie_index, profile)
    elif tag == "FaceDetection":
        return _map_face_detection(node, gie_index, is_primary, profile)
    elif tag == "SemanticSegmentation":
        return _map_segmentation(node, gie_index, is_primary, profile)

    return None


def _map_object_detection(
    node: NodeInfo,
    gie_index: int,
    is_primary: bool,
    profile: HardwareProfile,
) -> InferenceConfig:
    """Map ObjectDetection node to PGIE config."""
    settings = node.settings

    # Extract model info from settings
    model_name = _extract_combo_value(settings, "Input02Value", "YOLOX-Nano(416x416)")
    score_th = _extract_float_value(settings, "Input03Value", 0.4)

    # Determine model properties from name heuristics
    input_w, input_h = 640, 640
    output_format = "yolo11"
    num_classes = 80

    if "416" in model_name:
        input_w, input_h = 416, 416
    elif "608" in model_name:
        input_w, input_h = 608, 608
    elif "192" in model_name:
        input_w, input_h = 192, 192

    if "YOLOX" in model_name or "FreeYOLO" in model_name:
        output_format = "yolox"
    elif "YOLO11" in model_name or "YOLOTENNIS" in model_name:
        output_format = "yolo11"

    if "CrowdHuman" in model_name or "Person" in model_name:
        num_classes = 1
    elif "TENNIS" in model_name.upper():
        num_classes = 3

    format_info = _OUTPUT_FORMAT_MAP.get(output_format, _OUTPUT_FORMAT_MAP["yolo11"])

    config = InferenceConfig(
        gie_id=gie_index + 1,
        gie_type="primary" if is_primary else "secondary",
        node_tag=tag,
        model_name=model_name,
        onnx_path=f"models/{_sanitize_filename(model_name)}.onnx",
        trt_engine_path=f"models/{_sanitize_filename(model_name)}.engine",
        input_width=input_w,
        input_height=input_h,
        num_classes=num_classes,
        output_format=output_format,
        score_threshold=score_th,
        nms_threshold=0.45,
        network_type=0,
        cluster_mode=2,
        batch_size=min(profile.max_batch_size, 4),
        interval=profile.infer_interval - 1,
    )

    config.config_entries = _build_nvinfer_config(config, profile, format_info)
    return config


def _map_classification(
    node: NodeInfo,
    gie_index: int,
    profile: HardwareProfile,
) -> InferenceConfig:
    """Map Classification node to SGIE config."""
    settings = node.settings
    model_name = _extract_combo_value(settings, "Input02Value", "classifier")

    config = InferenceConfig(
        gie_id=gie_index + 1,
        gie_type="secondary",
        node_tag="Classification",
        model_name=model_name,
        onnx_path=f"models/{_sanitize_filename(model_name)}.onnx",
        trt_engine_path=f"models/{_sanitize_filename(model_name)}.engine",
        input_width=224,
        input_height=224,
        num_classes=1000,
        network_type=1,  # Classifier
        cluster_mode=2,
        batch_size=min(profile.max_batch_size, 8),
        interval=0,
        operate_on_gie_id=1,
    )

    config.config_entries = _build_sgie_config(config, profile)
    return config


def _map_pose_estimation(
    node: NodeInfo,
    gie_index: int,
    profile: HardwareProfile,
) -> InferenceConfig:
    """Map PoseEstimation node to SGIE config."""
    config = InferenceConfig(
        gie_id=gie_index + 1,
        gie_type="secondary",
        node_tag="PoseEstimation",
        model_name="pose_estimation",
        onnx_path="models/pose_estimation.onnx",
        trt_engine_path="models/pose_estimation.engine",
        input_width=256,
        input_height=192,
        num_classes=17,  # COCO keypoints
        network_type=100,  # Other (custom post-process)
        cluster_mode=2,
        batch_size=min(profile.max_batch_size, 8),
        interval=0,
        operate_on_gie_id=1,
    )

    config.config_entries = _build_sgie_config(config, profile)
    return config


def _map_face_detection(
    node: NodeInfo,
    gie_index: int,
    is_primary: bool,
    profile: HardwareProfile,
) -> InferenceConfig:
    """Map FaceDetection node to GIE config."""
    config = InferenceConfig(
        gie_id=gie_index + 1,
        gie_type="primary" if is_primary else "secondary",
        node_tag="FaceDetection",
        model_name="face_detection",
        onnx_path="models/face_detection.onnx",
        trt_engine_path="models/face_detection.engine",
        input_width=320,
        input_height=240,
        num_classes=1,
        network_type=0,
        cluster_mode=2,
        batch_size=min(profile.max_batch_size, 4),
        interval=0,
    )

    format_info = _OUTPUT_FORMAT_MAP["yolox"]
    config.config_entries = _build_nvinfer_config(config, profile, format_info)
    return config


def _map_segmentation(
    node: NodeInfo,
    gie_index: int,
    is_primary: bool,
    profile: HardwareProfile,
) -> InferenceConfig:
    """Map SemanticSegmentation node to GIE config."""
    config = InferenceConfig(
        gie_id=gie_index + 1,
        gie_type="primary" if is_primary else "secondary",
        node_tag="SemanticSegmentation",
        model_name="semantic_segmentation",
        onnx_path="models/semantic_segmentation.onnx",
        trt_engine_path="models/semantic_segmentation.engine",
        input_width=512,
        input_height=512,
        num_classes=21,
        network_type=2,  # Segmentation
        cluster_mode=2,
        batch_size=min(profile.max_batch_size, 2),
        interval=0,
    )

    format_info = {"network_type": "2", "parse_func": "", "custom_lib": ""}
    config.config_entries = _build_nvinfer_config(config, profile, format_info)
    config.config_entries["[property]"]["network-type"] = "2"
    config.config_entries["[property]"]["segmentation-threshold"] = "0.5"
    config.config_entries["[property]"]["output-blob-names"] = "output"
    return config


def _build_nvinfer_config(
    config: InferenceConfig,
    profile: HardwareProfile,
    format_info: dict,
) -> dict:
    """Build nvinfer configuration sections."""
    precision = "1" if profile.fp16_enabled else "0"  # 0=FP32, 1=FP16, 2=INT8
    if profile.int8_enabled:
        precision = "2"

    entries = {
        "[property]": {
            "gpu-id": str(profile.gpu_id),
            "net-scale-factor": "1.0",
            "onnx-file": config.onnx_path,
            "model-engine-file": config.trt_engine_path,
            "batch-size": str(config.batch_size),
            "network-mode": precision,
            "num-detected-classes": str(config.num_classes),
            "interval": str(config.interval),
            "gie-unique-id": str(config.gie_id),
            "network-type": format_info["network_type"],
            "cluster-mode": str(config.cluster_mode),
            "maintain-aspect-ratio": "1",
            "workspace-size": str(profile.tensorrt_workspace_mb),
            "infer-dims": f"3;{config.input_height};{config.input_width}",
            "parse-bbox-func-name": format_info["parse_func"],
            "custom-lib-path": format_info["custom_lib"],
        },
        "[class-attrs-all]": {
            "pre-cluster-threshold": str(config.score_threshold),
            "nms-iou-threshold": str(config.nms_threshold),
            "topk": "200",
        },
    }

    if config.gie_type == "secondary":
        entries["[property]"]["process-mode"] = "2"  # Secondary
        entries["[property]"]["operate-on-gie-id"] = str(config.operate_on_gie_id)
    else:
        entries["[property]"]["process-mode"] = "1"  # Primary

    return entries


def _build_sgie_config(config: InferenceConfig, profile: HardwareProfile) -> dict:
    """Build SGIE-specific config."""
    precision = "1" if profile.fp16_enabled else "0"
    if profile.int8_enabled:
        precision = "2"

    return {
        "[property]": {
            "gpu-id": str(profile.gpu_id),
            "net-scale-factor": "1.0",
            "onnx-file": config.onnx_path,
            "model-engine-file": config.trt_engine_path,
            "batch-size": str(config.batch_size),
            "network-mode": precision,
            "num-detected-classes": str(config.num_classes),
            "interval": str(config.interval),
            "gie-unique-id": str(config.gie_id),
            "network-type": str(config.network_type),
            "process-mode": "2",
            "operate-on-gie-id": str(config.operate_on_gie_id),
            "workspace-size": str(profile.tensorrt_workspace_mb),
            "infer-dims": f"3;{config.input_height};{config.input_width}",
        },
    }


def _extract_combo_value(settings: dict, key_suffix: str, default: str = "") -> str:
    """Extract combo/text value from settings."""
    for key, value in settings.items():
        if key.endswith(key_suffix):
            if isinstance(value, str) and value:
                return value
    return default


def _extract_float_value(settings: dict, key_suffix: str, default: float = 0.0) -> float:
    """Extract a float value from settings."""
    for key, value in settings.items():
        if key.endswith(key_suffix):
            try:
                return float(value)
            except (ValueError, TypeError):
                pass
    return default


def _sanitize_filename(name: str) -> str:
    """Convert a model name to a safe filename."""
    return name.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")

# Alias for backward compat
tag = "ObjectDetection"
