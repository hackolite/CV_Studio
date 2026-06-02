"""
DeepStream pipeline builder.

Assembles a complete DeepStream pipeline configuration from the mapped elements.
Handles the topology: sources → streammux → PGIE → tracker → SGIE(s) → OSD → sinks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tools.deepstream_engine.parser import CvStudioProject, NodeInfo
from tools.deepstream_engine.hardware_profile import HardwareProfile, RTX_5070_PROFILE
from tools.deepstream_engine.mappers.source_mapper import (
    DeepStreamSource,
    SOURCE_NODE_TAGS,
    map_source,
)
from tools.deepstream_engine.mappers.inference_mapper import (
    InferenceConfig,
    INFERENCE_NODE_TAGS,
    map_inference,
)
from tools.deepstream_engine.mappers.tracker_mapper import (
    TrackerConfig,
    TRACKER_NODE_TAGS,
    map_tracker,
)
from tools.deepstream_engine.mappers.sink_mapper import (
    SinkConfig,
    SINK_NODE_TAGS,
    DISPLAY_NODE_TAGS,
    map_sink,
    map_display_sink,
    map_fake_sink,
)


@dataclass
class DeepStreamPipeline:
    """Complete DeepStream pipeline configuration."""

    name: str = "cvstudio_deepstream"
    sources: list[DeepStreamSource] = field(default_factory=list)
    primary_gie: InferenceConfig | None = None
    secondary_gies: list[InferenceConfig] = field(default_factory=list)
    tracker: TrackerConfig | None = None
    sinks: list[SinkConfig] = field(default_factory=list)
    osd_enabled: bool = True
    streammux_config: dict[str, str] = field(default_factory=dict)
    tiler_config: dict[str, str] = field(default_factory=dict)
    profile: HardwareProfile = field(default_factory=lambda: RTX_5070_PROFILE)
    # Metadata
    source_node_tags_found: list[str] = field(default_factory=list)
    inference_node_tags_found: list[str] = field(default_factory=list)


def build_pipeline(
    project: CvStudioProject,
    profile: HardwareProfile = RTX_5070_PROFILE,
    project_name: str = "cvstudio_deepstream",
) -> DeepStreamPipeline:
    """
    Analyze a CvStudio project and build the corresponding DeepStream pipeline.

    The pipeline follows standard DeepStream topology:
      sources → streammux → PGIE → tracker → SGIE(s) → OSD → tiler → sinks
    """
    pipeline = DeepStreamPipeline(name=project_name, profile=profile)

    # --- 1. Map sources ---
    source_idx = 0
    for node in project.nodes.values():
        if node.node_tag in SOURCE_NODE_TAGS:
            source = map_source(node, source_idx)
            if source:
                pipeline.sources.append(source)
                pipeline.source_node_tags_found.append(node.node_tag)
                source_idx += 1

    # --- 2. Map inference nodes ---
    gie_idx = 0
    pgie_assigned = False

    # Walk the graph to determine primary vs secondary inference
    # First detector found becomes PGIE; classifiers/pose become SGIEs
    for node in project.nodes.values():
        if node.node_tag in INFERENCE_NODE_TAGS:
            is_primary = (
                not pgie_assigned
                and node.node_tag in ("ObjectDetection", "FaceDetection", "SemanticSegmentation")
            )

            infer_config = map_inference(node, gie_idx, is_primary, profile)
            if infer_config:
                if is_primary:
                    pipeline.primary_gie = infer_config
                    pgie_assigned = True
                else:
                    infer_config.operate_on_gie_id = 1  # Operate on PGIE
                    pipeline.secondary_gies.append(infer_config)
                pipeline.inference_node_tags_found.append(node.node_tag)
                gie_idx += 1

    # --- 3. Map tracker ---
    for node in project.nodes.values():
        if node.node_tag in TRACKER_NODE_TAGS:
            pipeline.tracker = map_tracker(node, profile)
            break  # Only one tracker in DeepStream pipeline

    # --- 4. Map sinks ---
    sink_idx = 0
    has_display_node = any(
        n.node_tag in DISPLAY_NODE_TAGS for n in project.nodes.values()
    )
    has_sink_node = any(
        n.node_tag in SINK_NODE_TAGS for n in project.nodes.values()
    )

    for node in project.nodes.values():
        if node.node_tag in SINK_NODE_TAGS:
            sink = map_sink(node, sink_idx, profile)
            if sink:
                pipeline.sinks.append(sink)
                sink_idx += 1

    # Default sinks if none mapped
    if not pipeline.sinks:
        if has_display_node:
            pipeline.sinks.append(map_display_sink(sink_idx, profile))
        else:
            pipeline.sinks.append(map_fake_sink(sink_idx))

    # --- 5. Streammux config (optimized for RTX 5070) ---
    num_sources = max(len(pipeline.sources), 1)
    pipeline.streammux_config = {
        "batch-size": str(num_sources),
        "batched-push-timeout": "40000",
        "width": "1920",
        "height": "1080",
        "enable-padding": "0",
        "gpu-id": str(profile.gpu_id),
        "nvbuf-memory-type": str(profile.nvbuf_memory_type),
        "live-source": "1" if _has_live_sources(pipeline) else "0",
    }

    # --- 6. Tiler config (for multi-source) ---
    if num_sources > 1:
        cols = _compute_tiler_cols(num_sources)
        rows = (num_sources + cols - 1) // cols
        pipeline.tiler_config = {
            "rows": str(rows),
            "columns": str(cols),
            "width": "1920",
            "height": "1080",
            "gpu-id": str(profile.gpu_id),
            "nvbuf-memory-type": str(profile.nvbuf_memory_type),
        }

    # --- 7. OSD ---
    pipeline.osd_enabled = bool(pipeline.primary_gie or pipeline.secondary_gies)

    return pipeline


def _has_live_sources(pipeline: DeepStreamPipeline) -> bool:
    """Check if any source is a live stream (RTSP, Webcam, etc.)."""
    live_types = {"uridecodebin", "v4l2src"}
    return any(s.source_type in live_types for s in pipeline.sources)


def _compute_tiler_cols(num_sources: int) -> int:
    """Compute optimal number of tiler columns."""
    if num_sources <= 2:
        return num_sources
    elif num_sources <= 4:
        return 2
    elif num_sources <= 9:
        return 3
    else:
        return 4
