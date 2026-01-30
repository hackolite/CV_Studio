#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for PyInstaller PermissionError fix

This script tests the new error handling mechanisms:
1. Process checking
2. Retry mechanism
3. Read-only file handling
4. Directory cleanup
"""

import os
import sys
import tempfile
import time
import stat
import shutil

# Add parent directory to path to import build_exe
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_exe


def test_check_running_processes():
    """Test the check_running_processes function"""
    print("\n=== Test 1: check_running_processes() ===")
    result = build_exe.check_running_processes()
    print(f"✓ Function executed successfully (result: {result})")
    assert isinstance(result, bool), "Should return boolean"
    print("✓ Returns boolean as expected")


def test_remove_readonly():
    """Test the remove_readonly function"""
    print("\n=== Test 2: remove_readonly() ===")
    
    # Create a temporary read-only file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        temp_file = f.name
        f.write("test content")
    
    try:
        # Make it read-only
        os.chmod(temp_file, stat.S_IREAD)
        print(f"✓ Created read-only file: {temp_file}")
        
        # Try to remove it using remove_readonly
        build_exe.remove_readonly(os.unlink, temp_file, None)
        print("✓ Successfully removed read-only file")
        
    except Exception as e:
        # Clean up if test fails
        if os.path.exists(temp_file):
            os.chmod(temp_file, stat.S_IWUSR | stat.S_IREAD)
            os.unlink(temp_file)
        raise


def test_remove_directory_with_retry():
    """Test the remove_directory_with_retry function"""
    print("\n=== Test 3: remove_directory_with_retry() ===")
    
    # Create a temporary directory with files
    temp_dir = tempfile.mkdtemp(prefix="cv_studio_test_")
    print(f"✓ Created test directory: {temp_dir}")
    
    # Create some test files
    test_file = os.path.join(temp_dir, "test.txt")
    with open(test_file, 'w') as f:
        f.write("test content")
    print("✓ Created test file")
    
    # Test removing the directory
    result = build_exe.remove_directory_with_retry(temp_dir, max_retries=2, initial_delay=0.1)
    assert result, "Should successfully remove directory"
    print("✓ Successfully removed directory")
    
    # Verify it's gone
    assert not os.path.exists(temp_dir), "Directory should not exist"
    print("✓ Verified directory was removed")


def test_remove_directory_with_readonly():
    """Test removing directory with read-only files"""
    print("\n=== Test 4: remove_directory_with_retry() with read-only files ===")
    
    # Create a temporary directory with read-only files
    temp_dir = tempfile.mkdtemp(prefix="cv_studio_test_ro_")
    print(f"✓ Created test directory: {temp_dir}")
    
    # Create a read-only file
    test_file = os.path.join(temp_dir, "readonly.txt")
    with open(test_file, 'w') as f:
        f.write("read-only content")
    os.chmod(test_file, stat.S_IREAD)
    print("✓ Created read-only file")
    
    # Test removing the directory (should handle read-only)
    result = build_exe.remove_directory_with_retry(temp_dir, max_retries=2, initial_delay=0.1)
    assert result, "Should successfully remove directory with read-only files"
    print("✓ Successfully removed directory with read-only files")
    
    # Verify it's gone
    assert not os.path.exists(temp_dir), "Directory should not exist"
    print("✓ Verified directory was removed")


def test_clean_build_directories():
    """Test the clean_build_directories function"""
    print("\n=== Test 5: clean_build_directories() (dry run) ===")
    
    # Save current directory
    original_dir = os.getcwd()
    
    # Create a temporary working directory
    temp_work_dir = tempfile.mkdtemp(prefix="cv_studio_work_")
    os.chdir(temp_work_dir)
    print(f"✓ Created temporary working directory: {temp_work_dir}")
    
    try:
        # Create fake build directories
        os.makedirs('build', exist_ok=True)
        os.makedirs('dist', exist_ok=True)
        print("✓ Created fake build directories")
        
        # Run clean (this should work in our temp directory)
        result = build_exe.clean_build_directories()
        print(f"✓ clean_build_directories() executed (result: {result})")
        
        # Note: In non-interactive mode, it may prompt, so we just check it ran
        print("✓ Function completed without crashing")
        
    finally:
        # Restore directory and cleanup
        os.chdir(original_dir)
        if os.path.exists(temp_work_dir):
            shutil.rmtree(temp_work_dir, onerror=build_exe.remove_readonly)
        print("✓ Cleaned up temporary working directory")


def main():
    """Run all tests"""
    print("=" * 70)
    print("  PyInstaller PermissionError Fix - Test Suite")
    print("=" * 70)
    
    tests = [
        ("Check Running Processes", test_check_running_processes),
        ("Remove Read-Only File", test_remove_readonly),
        ("Remove Directory with Retry", test_remove_directory_with_retry),
        ("Remove Directory with Read-Only Files", test_remove_directory_with_readonly),
        ("Clean Build Directories", test_clean_build_directories),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"✓ {test_name} PASSED")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print(f"  Test Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("\n✓ All tests passed!")


if __name__ == '__main__':
    main()
