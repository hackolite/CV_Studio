"""
DeepStream configuration file writer.

Generates the complete set of configuration files for a production-ready
DeepStream application from a DeepStreamPipeline object.
"""

from __future__ import annotations

import os
from pathlib import Path

from tools.deepstream_engine.pipeline_builder import DeepStreamPipeline
from tools.deepstream_engine.mappers.inference_mapper import InferenceConfig


def write_project(pipeline: DeepStreamPipeline, output_dir: str | Path) -> list[str]:
    """
    Write all DeepStream configuration files to the output directory.

    Returns a list of generated file paths (relative to output_dir).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_files = []

    # 1. Main pipeline config
    main_cfg = _write_main_config(pipeline, output_dir)
    generated_files.append(main_cfg)

    # 2. PGIE config
    if pipeline.primary_gie:
        pgie_cfg = _write_infer_config(
            pipeline.primary_gie, output_dir, "config_pgie.txt"
        )
        generated_files.append(pgie_cfg)

    # 3. SGIE configs
    for i, sgie in enumerate(pipeline.secondary_gies):
        sgie_cfg = _write_infer_config(
            sgie, output_dir, f"config_sgie_{i}.txt"
        )
        generated_files.append(sgie_cfg)

    # 4. Tracker config
    if pipeline.tracker:
        tracker_cfg = _write_tracker_config(pipeline, output_dir)
        generated_files.append(tracker_cfg)

    # 5. Labels file
    if pipeline.primary_gie and pipeline.primary_gie.class_names:
        labels_file = _write_labels_file(pipeline.primary_gie, output_dir)
        generated_files.append(labels_file)

    # 6. Message converter config (if msg sinks present)
    if any(s.sink_type == "msg" for s in pipeline.sinks):
        msg_cfg = _write_msg_conv_config(output_dir)
        generated_files.append(msg_cfg)

    return generated_files


def _write_main_config(pipeline: DeepStreamPipeline, output_dir: Path) -> str:
    """Write the main deepstream_app_config.txt."""
    lines = []
    lines.append("[application]")
    lines.append("enable-perf-measurement=1")
    lines.append("perf-measurement-interval-sec=5")
    lines.append("")

    # Sources
    for i, source in enumerate(pipeline.sources):
        lines.append(f"[source{i}]")
        lines.append("enable=1")
        for key, val in source.config_entries.items():
            lines.append(f"{key}={val}")
        lines.append("")

    # Streammux
    lines.append("[streammux]")
    for key, val in pipeline.streammux_config.items():
        lines.append(f"{key}={val}")
    lines.append("")

    # Primary GIE
    if pipeline.primary_gie:
        lines.append("[primary-gie]")
        lines.append("enable=1")
        lines.append(f"gie-unique-id={pipeline.primary_gie.gie_id}")
        lines.append(f"batch-size={pipeline.primary_gie.batch_size}")
        lines.append(f"interval={pipeline.primary_gie.interval}")
        lines.append("config-file=config_pgie.txt")
        lines.append("")

    # Secondary GIEs
    for i, sgie in enumerate(pipeline.secondary_gies):
        lines.append(f"[secondary-gie{i}]")
        lines.append("enable=1")
        lines.append(f"gie-unique-id={sgie.gie_id}")
        lines.append(f"operate-on-gie-id={sgie.operate_on_gie_id}")
        lines.append(f"batch-size={sgie.batch_size}")
        lines.append(f"config-file=config_sgie_{i}.txt")
        lines.append("")

    # Tracker
    if pipeline.tracker:
        lines.append("[tracker]")
        lines.append("enable=1")
        for key, val in pipeline.tracker.config_entries.get("[tracker]", {}).items():
            lines.append(f"{key}={val}")
        lines.append("")

    # OSD
    if pipeline.osd_enabled:
        lines.append("[osd]")
        lines.append("enable=1")
        lines.append(f"gpu-id={pipeline.profile.gpu_id}")
        lines.append(f"nvbuf-memory-type={pipeline.profile.nvbuf_memory_type}")
        lines.append("border-width=2")
        lines.append("text-size=12")
        lines.append("text-color=1;1;1;1")
        lines.append("text-bg-color=0.3;0.3;0.3;1")
        lines.append("font=Arial")
        lines.append("clock-color=1;0;0;0")
        lines.append("")

    # Tiler (multi-source)
    if pipeline.tiler_config:
        lines.append("[tiler]")
        lines.append("enable=1")
        for key, val in pipeline.tiler_config.items():
            lines.append(f"{key}={val}")
        lines.append("")

    # Sinks
    for i, sink in enumerate(pipeline.sinks):
        lines.append(f"[sink{i}]")
        lines.append("enable=1")
        for key, val in sink.config_entries.items():
            lines.append(f"{key}={val}")
        lines.append("")

    # Write file
    config_path = output_dir / "deepstream_app_config.txt"
    config_path.write_text("\n".join(lines), encoding="utf-8")
    return "deepstream_app_config.txt"


def _write_infer_config(config: InferenceConfig, output_dir: Path, filename: str) -> str:
    """Write an nvinfer configuration file."""
    lines = []

    for section, entries in config.config_entries.items():
        lines.append(section)
        for key, val in entries.items():
            lines.append(f"{key}={val}")
        lines.append("")

    config_path = output_dir / filename
    config_path.write_text("\n".join(lines), encoding="utf-8")
    return filename


def _write_tracker_config(pipeline: DeepStreamPipeline, output_dir: Path) -> str:
    """Write tracker YAML configuration."""
    tracker = pipeline.tracker
    tracker_dir = output_dir / "tracker"
    tracker_dir.mkdir(exist_ok=True)

    # Write a basic NvDCF-style tracker YAML
    yaml_content = f"""# DeepStream Tracker Configuration
# Generated by CvStudio DeepStream Engine
# Optimized for {pipeline.profile.name}

%YAML:1.0
BaseConfig:
  minDetectorConfidence: 0.3
  minTrackerConfidence: 0.5
  minMatchingScore4Overall: 0.4
  minTrailLengthForVehicleReIDInFrames: 5
  maxShadowTrackingAge: 30
  probationAge: 3
  maxTargetsPerStream: 150

TargetManagement:
  enableBBoxUnClipping: 0
  maxTargetsPerStream: 150
  preserveStreamUpdateOrder: 0
  maxShadowTrackingAge: 30
  probationAge: 3
  earlyTerminationAge: 1

TrajectoryManagement:
  useUniqueID: 1
  enableTrajectorySmoothing: 0

DataAssociator:
  dataAssociatorType: 0  # 0: Hungarian, 1: Cascaded
  associationMatcherType: 1  # 0: Bipartite, 1: Cascaded
  checkClassMatch: 1
  minMatchingScore4Overall: 0.4
  minMatchingScore4SizeSimilarity: 0.6
  minMatchingScore4Locality: 0.3
  matchingScoreWeight4SizeSimilarity: 0.4
  matchingScoreWeight4Locality: 0.6

StateEstimator:
  stateEstimatorType: 2  # 1: Simple, 2: Regular Kalman
  noiseWeightVar4Loc: 0.05
  noiseWeightVar4Vel: 0.0025

ReID:
  reidType: 0  # 0: None, 1: L2Norm, 2: Custom
"""

    config_file = f"config_tracker_{tracker.tracker_name}.yml"
    (tracker_dir / config_file).write_text(yaml_content, encoding="utf-8")
    return f"tracker/{config_file}"


def _write_labels_file(config: InferenceConfig, output_dir: Path) -> str:
    """Write class labels file."""
    labels_path = output_dir / "labels.txt"
    if config.class_names:
        sorted_names = [config.class_names[k] for k in sorted(config.class_names.keys())]
        labels_path.write_text("\n".join(sorted_names) + "\n", encoding="utf-8")
    else:
        labels_path.write_text("object\n", encoding="utf-8")
    return "labels.txt"


def _write_msg_conv_config(output_dir: Path) -> str:
    """Write message converter configuration for msg sinks."""
    content = """# Message Converter Configuration
# Generated by CvStudio DeepStream Engine

[sensor]
enable=1
type=Camera
id=CAMERA_ID

[place]
enable=1
id=PLACE_ID
type=intersection/road
name=CvStudio_Deployment
coordinate=0;0;0

[analytics]
enable=1
id=ANALYTICS_ID
source=CvStudio
version=1.0
"""
    msg_path = output_dir / "msg_conv_config.txt"
    msg_path.write_text(content, encoding="utf-8")
    return "msg_conv_config.txt"
