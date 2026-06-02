"""
Tracker element mapper.

Maps CvStudio TrackerNode to DeepStream nvtracker configurations.
Supports: ByteTrack, NorFair, IOU, SORT, OC-SORT, BotSORT, DeepSORT.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tools.deepstream_engine.parser import NodeInfo
from tools.deepstream_engine.hardware_profile import HardwareProfile, RTX_5070_PROFILE


TRACKER_NODE_TAGS = {"MultiObjectTracking", "ReId"}

# Map CvStudio tracker names to DeepStream low-level tracker library
_TRACKER_LIB_MAP = {
    "ByteTrack": "libnvds_nvmultiobjecttracker.so",
    "NorFair": "libnvds_nvmultiobjecttracker.so",
    "IOU": "libnvds_nvmultiobjecttracker.so",
    "SORT": "libnvds_nvmultiobjecttracker.so",
    "OC-SORT": "libnvds_nvmultiobjecttracker.so",
    "BotSORT": "libnvds_nvmultiobjecttracker.so",
    "DeepSORT": "libnvds_nvmultiobjecttracker.so",
    "CenterTrack": "libnvds_nvmultiobjecttracker.so",
    "Motpy": "libnvds_nvmultiobjecttracker.so",
    "KalmanFilter": "libnvds_nvmultiobjecttracker.so",
}

# Map to DeepStream tracker algorithm config
_TRACKER_CONFIG_MAP = {
    "ByteTrack": "config_tracker_NvDCF_accuracy.yml",
    "NorFair": "config_tracker_NvDCF_perf.yml",
    "IOU": "config_tracker_IOU.yml",
    "SORT": "config_tracker_NvSORT.yml",
    "OC-SORT": "config_tracker_NvSORT.yml",
    "BotSORT": "config_tracker_NvDCF_accuracy.yml",
    "DeepSORT": "config_tracker_DeepSORT.yml",
    "CenterTrack": "config_tracker_NvDCF_perf.yml",
    "Motpy": "config_tracker_IOU.yml",
    "KalmanFilter": "config_tracker_NvSORT.yml",
}


@dataclass
class TrackerConfig:
    """DeepStream nvtracker configuration."""

    tracker_name: str = "ByteTrack"
    tracker_lib: str = "libnvds_nvmultiobjecttracker.so"
    tracker_config_file: str = "config_tracker_NvDCF_accuracy.yml"
    tracker_width: int = 960
    tracker_height: int = 544
    gpu_id: int = 0
    enable_past_frame: bool = True
    enable_batch_process: bool = True
    config_entries: dict[str, Any] = field(default_factory=dict)


def map_tracker(
    node: NodeInfo,
    profile: HardwareProfile = RTX_5070_PROFILE,
) -> TrackerConfig | None:
    """Convert a CvStudio tracker node into DeepStream tracker config."""
    settings = node.settings

    # Try to extract tracker type from settings
    tracker_name = _extract_tracker_type(settings)

    tracker_lib = _TRACKER_LIB_MAP.get(tracker_name, "libnvds_nvmultiobjecttracker.so")
    tracker_config = _TRACKER_CONFIG_MAP.get(tracker_name, "config_tracker_NvDCF_accuracy.yml")

    config = TrackerConfig(
        tracker_name=tracker_name,
        tracker_lib=tracker_lib,
        tracker_config_file=tracker_config,
        tracker_width=960,
        tracker_height=544,
        gpu_id=profile.gpu_id,
        enable_past_frame=True,
        enable_batch_process=True,
    )

    config.config_entries = {
        "[tracker]": {
            "tracker-width": str(config.tracker_width),
            "tracker-height": str(config.tracker_height),
            "gpu-id": str(config.gpu_id),
            "ll-lib-file": f"/opt/nvidia/deepstream/deepstream/lib/{tracker_lib}",
            "ll-config-file": f"tracker/{tracker_config}",
            "enable-past-frame": "1" if config.enable_past_frame else "0",
            "enable-batch-process": "1" if config.enable_batch_process else "0",
            "display-tracking-id": "1",
        },
    }

    return config


def _extract_tracker_type(settings: dict) -> str:
    """Try to determine tracker type from node settings."""
    for key, value in settings.items():
        if key.endswith("Input02Value") or key.endswith("Input04Value"):
            if isinstance(value, str):
                # Sort by name length descending to match longer names first
                # (e.g., "OC-SORT" before "SORT")
                sorted_names = sorted(
                    _TRACKER_LIB_MAP.keys(), key=len, reverse=True
                )
                for tracker_name in sorted_names:
                    if tracker_name.lower() in value.lower():
                        return tracker_name
    return "ByteTrack"  # Default
