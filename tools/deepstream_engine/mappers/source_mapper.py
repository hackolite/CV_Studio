"""
Source element mapper.

Maps CvStudio input nodes to DeepStream source elements:
  - RTSP → nvurisrcbin / uridecodebin
  - Video → filesrc + nvv4l2decoder
  - Webcam → v4l2src + nvvideoconvert
  - HLS → uridecodebin
  - YouTube → uridecodebin (resolved URI)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tools.deepstream_engine.parser import NodeInfo


# CvStudio node tags that represent video/image sources
SOURCE_NODE_TAGS = {
    "RTSP",
    "Video",
    "Webcam",
    "HLS",
    "YouTube",
    "Image",
    "WebRTC",
}


@dataclass
class DeepStreamSource:
    """A mapped DeepStream source element configuration."""

    source_id: int
    source_type: str  # e.g., "uridecodebin", "v4l2src", "filesrc"
    uri: str = ""
    device: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    # DeepStream source-group config entries
    config_entries: dict[str, str] = field(default_factory=dict)


def map_source(node: NodeInfo, source_index: int = 0) -> DeepStreamSource | None:
    """Convert a CvStudio input node into a DeepStreamSource config."""
    tag = node.node_tag
    settings = node.settings

    if tag == "RTSP":
        uri = _extract_text_value(settings, "Input01Value", "")
        return DeepStreamSource(
            source_id=source_index,
            source_type="uridecodebin",
            uri=uri,
            config_entries={
                "type": "4",  # RTSP
                "uri": uri,
                "num-sources": "1",
                "gpu-id": "0",
                "cudadec-memtype": "0",
                "latency": "200",
                "drop-frame-interval": "0",
            },
        )

    elif tag == "Video":
        # Video file source
        filepath = _extract_text_value(settings, "Input01Value", "")
        return DeepStreamSource(
            source_id=source_index,
            source_type="filesrc",
            uri=filepath,
            config_entries={
                "type": "3",  # File
                "uri": f"file://{filepath}",
                "num-sources": "1",
                "gpu-id": "0",
                "cudadec-memtype": "0",
            },
        )

    elif tag == "Webcam":
        device = _extract_text_value(settings, "Input01Value", "/dev/video0")
        return DeepStreamSource(
            source_id=source_index,
            source_type="v4l2src",
            device=device,
            config_entries={
                "type": "1",  # Camera (V4L2)
                "camera-id": str(source_index),
                "camera-width": "1920",
                "camera-height": "1080",
                "camera-fps-n": "30",
                "camera-fps-d": "1",
                "gpu-id": "0",
            },
        )

    elif tag == "HLS":
        uri = _extract_text_value(settings, "Input01Value", "")
        return DeepStreamSource(
            source_id=source_index,
            source_type="uridecodebin",
            uri=uri,
            config_entries={
                "type": "4",  # URI
                "uri": uri,
                "num-sources": "1",
                "gpu-id": "0",
                "cudadec-memtype": "0",
            },
        )

    elif tag == "YouTube":
        uri = _extract_text_value(settings, "Input01Value", "")
        return DeepStreamSource(
            source_id=source_index,
            source_type="uridecodebin",
            uri=uri,
            config_entries={
                "type": "4",
                "uri": uri,
                "num-sources": "1",
                "gpu-id": "0",
                "cudadec-memtype": "0",
            },
        )

    return None


def _extract_text_value(settings: dict, key_suffix: str, default: str = "") -> str:
    """Extract a text value from node settings by matching key suffix."""
    for key, value in settings.items():
        if key.endswith(key_suffix):
            if isinstance(value, str) and value:
                return value
    return default
