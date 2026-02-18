#!/usr/bin/env python3
"""
Syntax validation script for PySide6 migration files.
This checks that all PySide6-related files have valid Python syntax.
"""
import py_compile
import sys

files_to_check = [
    'node_editor/pyside6_adapter.py',
    'main_pyside6.py',
]

print("Checking Python syntax for PySide6 migration files...\n")

all_valid = True
for filepath in files_to_check:
    try:
        py_compile.compile(filepath, doraise=True)
        print(f"✅ {filepath} - Syntax OK")
    except py_compile.PyCompileError as e:
        print(f"❌ {filepath} - Syntax Error:")
        print(f"   {e}")
        all_valid = False

print()
if all_valid:
    print("✅ All files have valid Python syntax")
    sys.exit(0)
else:
    print("❌ Some files have syntax errors")
    sys.exit(1)
