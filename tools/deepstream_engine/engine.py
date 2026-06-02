"""
DeepStream Engine – Main orchestrator.

Converts a CvStudio JSON save file into a complete, production-ready
DeepStream project optimized for the target hardware.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from tools.deepstream_engine.parser import parse, CvStudioProject
from tools.deepstream_engine.hardware_profile import HardwareProfile, get_profile
from tools.deepstream_engine.pipeline_builder import build_pipeline, DeepStreamPipeline
from tools.deepstream_engine.config_writer import write_project
from tools.deepstream_engine.scaffold import generate_scaffold


class DeepStreamEngine:
    """
    Main engine for converting CvStudio projects to DeepStream.

    Usage:
        engine = DeepStreamEngine()
        result = engine.convert("my_project.json", "output/my_deepstream_project")
    """

    def __init__(self, profile_name: str = "RTX_5070"):
        self.profile: HardwareProfile = get_profile(profile_name)

    def convert(
        self,
        input_json: str | Path,
        output_dir: str | Path,
        project_name: str | None = None,
        overwrite: bool = False,
    ) -> ConversionResult:
        """
        Convert a CvStudio JSON save file to a DeepStream project.

        Args:
            input_json: Path to the CvStudio JSON save file.
            output_dir: Directory where the DeepStream project will be created.
            project_name: Optional project name (defaults to JSON filename).
            overwrite: If True, overwrite existing output directory.

        Returns:
            ConversionResult with details about the generated project.
        """
        input_json = Path(input_json)
        output_dir = Path(output_dir)

        if not input_json.exists():
            raise FileNotFoundError(f"Input file not found: {input_json}")

        if project_name is None:
            project_name = input_json.stem.replace(" ", "_")

        if output_dir.exists():
            if overwrite:
                shutil.rmtree(output_dir)
            else:
                raise FileExistsError(
                    f"Output directory already exists: {output_dir}. "
                    "Use overwrite=True to replace it."
                )

        # Step 1: Parse the CvStudio JSON
        project = parse(input_json)

        # Step 2: Build the DeepStream pipeline
        pipeline = build_pipeline(project, self.profile, project_name)

        # Step 3: Write configuration files
        config_files = write_project(pipeline, output_dir)

        # Step 4: Generate project scaffolding
        scaffold_files = generate_scaffold(pipeline, output_dir)

        # Step 5: Copy ONNX models if they exist alongside the JSON
        models_copied = self._copy_models(input_json, pipeline, output_dir)

        return ConversionResult(
            project_name=project_name,
            output_dir=str(output_dir),
            pipeline=pipeline,
            config_files=config_files,
            scaffold_files=scaffold_files,
            models_copied=models_copied,
            nodes_mapped=len(project.nodes),
            links_mapped=len(project.links),
        )

    def convert_from_dict(
        self,
        data: dict,
        output_dir: str | Path,
        project_name: str = "cvstudio_deepstream",
        overwrite: bool = False,
    ) -> ConversionResult:
        """
        Convert a CvStudio project from an already-loaded dict.

        Useful when the JSON is already in memory (e.g., from an API call).
        """
        import json
        import tempfile

        # Write to temp file and use standard pipeline
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            json.dump(data, tmp)
            tmp_path = tmp.name

        try:
            return self.convert(tmp_path, output_dir, project_name, overwrite)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _copy_models(
        self,
        input_json: Path,
        pipeline: DeepStreamPipeline,
        output_dir: Path,
    ) -> list[str]:
        """Try to find and copy ONNX models referenced by the pipeline."""
        models_dir = output_dir / "models"
        models_dir.mkdir(exist_ok=True)
        copied = []

        # Look for ONNX files in common locations relative to the JSON
        search_dirs = [
            input_json.parent,
            input_json.parent / "models",
            input_json.parent.parent / "node" / "DLNode" / "object_detection",
        ]

        # Collect all ONNX paths from the pipeline
        onnx_files = set()
        if pipeline.primary_gie:
            onnx_files.add(pipeline.primary_gie.onnx_path)
        for sgie in pipeline.secondary_gies:
            onnx_files.add(sgie.onnx_path)

        for onnx_path in onnx_files:
            filename = Path(onnx_path).name
            for search_dir in search_dirs:
                # Recursive search
                for found in search_dir.rglob(filename) if search_dir.exists() else []:
                    dest = models_dir / filename
                    if not dest.exists():
                        shutil.copy2(found, dest)
                        copied.append(filename)
                    break

        return copied


class ConversionResult:
    """Result of a CvStudio → DeepStream conversion."""

    def __init__(
        self,
        project_name: str,
        output_dir: str,
        pipeline: DeepStreamPipeline,
        config_files: list[str],
        scaffold_files: list[str],
        models_copied: list[str],
        nodes_mapped: int,
        links_mapped: int,
    ):
        self.project_name = project_name
        self.output_dir = output_dir
        self.pipeline = pipeline
        self.config_files = config_files
        self.scaffold_files = scaffold_files
        self.models_copied = models_copied
        self.nodes_mapped = nodes_mapped
        self.links_mapped = links_mapped

    @property
    def all_files(self) -> list[str]:
        """All generated files."""
        return self.config_files + self.scaffold_files

    def summary(self) -> str:
        """Human-readable summary of the conversion."""
        lines = [
            f"═══ DeepStream Project: {self.project_name} ═══",
            f"Output: {self.output_dir}",
            f"",
            f"Pipeline Summary:",
            f"  Sources: {len(self.pipeline.sources)}",
            f"  Primary GIE: {self.pipeline.primary_gie.model_name if self.pipeline.primary_gie else 'None'}",
            f"  Secondary GIEs: {len(self.pipeline.secondary_gies)}",
            f"  Tracker: {self.pipeline.tracker.tracker_name if self.pipeline.tracker else 'None'}",
            f"  Sinks: {len(self.pipeline.sinks)}",
            f"",
            f"Nodes mapped: {self.nodes_mapped}",
            f"Links mapped: {self.links_mapped}",
            f"",
            f"Generated files ({len(self.all_files)}):",
        ]
        for f in sorted(self.all_files):
            lines.append(f"  • {f}")

        if self.models_copied:
            lines.append(f"")
            lines.append(f"Models copied ({len(self.models_copied)}):")
            for m in self.models_copied:
                lines.append(f"  • {m}")

        lines.append(f"")
        lines.append(f"Target: {self.pipeline.profile.name} "
                     f"({self.pipeline.profile.vram_gb}GB VRAM, "
                     f"{self.pipeline.profile.system_ram_gb}GB RAM)")
        lines.append(f"")
        lines.append("Next steps:")
        lines.append("  1. Copy ONNX models to models/")
        lines.append("  2. Run: make build && make run")

        return "\n".join(lines)
