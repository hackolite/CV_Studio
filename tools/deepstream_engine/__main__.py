"""
CLI __main__ entry point.

Allows: python -m tools.deepstream_engine input.json -o output/
"""
from tools.deepstream_engine.cli import main
import sys

sys.exit(main())
