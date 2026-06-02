#!/usr/bin/env python3
"""
CvStudio DeepStream Engine – Command Line Interface.

Converts CvStudio JSON save files into production-ready DeepStream projects.

Usage:
    python -m tools.deepstream_engine.cli input.json -o output_dir/
    python -m tools.deepstream_engine.cli input.json --profile RTX_5070
    python -m tools.deepstream_engine.cli input.json -o my_project --overwrite
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="cvstudio-deepstream",
        description="Convert CvStudio JSON projects to production-ready DeepStream pipelines.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s my_project.json
  %(prog)s my_project.json -o deepstream_output/
  %(prog)s my_project.json --profile RTX_5070_HIGH_BATCH
  %(prog)s my_project.json -o project/ --overwrite --name my_app

Target Profiles:
  RTX_5070            Default (FP16, batch=8, 4GB TRT workspace)
  RTX_5070_HIGH_BATCH High throughput (FP16, batch=16, 6GB TRT workspace)
  RTX_5070_INT8       Maximum performance (INT8, requires calibration)
""",
    )

    parser.add_argument(
        "input",
        type=str,
        help="Path to CvStudio JSON save file",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output directory (default: <input_stem>_deepstream/)",
    )
    parser.add_argument(
        "-n", "--name",
        type=str,
        default=None,
        help="Project name (default: derived from input filename)",
    )
    parser.add_argument(
        "-p", "--profile",
        type=str,
        default="RTX_5070",
        choices=["RTX_5070", "RTX_5070_HIGH_BATCH", "RTX_5070_INT8"],
        help="Hardware optimization profile (default: RTX_5070)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output directory",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )

    args = parser.parse_args(argv)

    # Validate input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    if not input_path.suffix.lower() == ".json":
        print(f"Warning: Input file does not have .json extension: {input_path}",
              file=sys.stderr)

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = input_path.parent / f"{input_path.stem}_deepstream"

    # Run conversion
    from tools.deepstream_engine.engine import DeepStreamEngine

    engine = DeepStreamEngine(profile_name=args.profile)

    try:
        result = engine.convert(
            input_json=input_path,
            output_dir=output_dir,
            project_name=args.name,
            overwrite=args.overwrite,
        )
    except FileExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

    # Print results
    print(result.summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())
