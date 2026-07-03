#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Legacy Wrapper - Maintains compatibility with old build.py usage

This script wraps build_unified.py to maintain backward compatibility
with the old build.py interface while encouraging migration to the new system.

Usage:
    python build.py              # Uses unified system with clean flag
    python build_legacy.py       # Alternative explicit name
"""

import sys
import subprocess
from pathlib import Path

print("=" * 70)
print("⚠️  DEPRECATION NOTICE")
print("=" * 70)
print()
print("The old build.py interface is deprecated.")
print("This script now redirects to the unified build system.")
print()
print("Recommended usage:")
print("  python build_unified.py --clean")
print()
print("See doc/BUILD_GUIDE.md for complete documentation.")
print("=" * 70)
print()
print("Continuing with unified build system...")
print()

# Get the script directory
script_dir = Path(__file__).parent.absolute()
unified_script = script_dir / "build_unified.py"

# Check if unified script exists
if not unified_script.exists():
    print(f"ERROR: Cannot find {unified_script}")
    print("Please ensure build_unified.py is in the same directory.")
    sys.exit(1)

# Run unified build with clean flag
cmd = [sys.executable, str(unified_script), "--clean"]

try:
    result = subprocess.run(cmd)
    sys.exit(result.returncode)
except KeyboardInterrupt:
    print("\n\nBuild cancelled by user.")
    sys.exit(130)
except Exception as e:
    print(f"\nERROR: Failed to run unified build: {e}")
    sys.exit(1)
