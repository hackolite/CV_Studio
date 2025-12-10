#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for System Verification Module

Validates the system verification functionality including:
- FFmpeg detection
- Python package verification
- OpenCV module checking
- Summary reporting
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.utils.system_verification import (
        SystemVerifier,
        VerificationStatus,
        VerificationResult,
        run_system_verification
    )
    VERIFICATION_AVAILABLE = True
except ImportError as e:
    VERIFICATION_AVAILABLE = False
    print(f"Warning: system_verification module not available: {e}")


class TestSystemVerification(unittest.TestCase):
    """Test SystemVerifier implementation"""
    
    def setUp(self):
        """Set up test fixtures"""
        if not VERIFICATION_AVAILABLE:
            self.skipTest("system_verification module not available")
        
        self.verifier = SystemVerifier()
    
    def test_verifier_creation(self):
        """Test verifier can be created"""
        self.assertIsNotNone(self.verifier)
        self.assertEqual(len(self.verifier.results), 0)
    
    @patch('subprocess.run')
    def test_ffmpeg_found(self, mock_run):
        """Test FFmpeg detection when FFmpeg is installed"""
        # Mock successful FFmpeg execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ffmpeg version 4.4.2"
        mock_run.return_value = mock_result
        
        result = self.verifier.verify_ffmpeg()
        
        self.assertEqual(result.component, "FFmpeg")
        self.assertEqual(result.status, VerificationStatus.OK)
        self.assertIn("FFmpeg is installed", result.message)
    
    @patch('subprocess.run')
    def test_ffmpeg_not_found(self, mock_run):
        """Test FFmpeg detection when FFmpeg is not installed"""
        # Mock FileNotFoundError
        mock_run.side_effect = FileNotFoundError()
        
        result = self.verifier.verify_ffmpeg()
        
        self.assertEqual(result.component, "FFmpeg")
        self.assertEqual(result.status, VerificationStatus.NOT_FOUND)
        self.assertIn("not found", result.message)
    
    def test_opencv_verification(self):
        """Test OpenCV verification"""
        result = self.verifier.verify_opencv()
        
        self.assertEqual(result.component, "OpenCV")
        # Should either be OK or WARNING depending on installation
        self.assertIn(result.status, [VerificationStatus.OK, VerificationStatus.WARNING, VerificationStatus.ERROR])
    
    def test_python_packages_verification(self):
        """Test Python packages verification"""
        results = self.verifier.verify_python_packages()
        
        # Should return results for all required packages
        self.assertGreater(len(results), 0)
        
        # All results should be for packages
        for result in results:
            self.assertTrue(result.component.startswith("Package:"))
    
    def test_verify_all(self):
        """Test complete verification run"""
        success = self.verifier.verify_all()
        
        # Should have results
        self.assertGreater(len(self.verifier.results), 0)
        
        # Success should be boolean
        self.assertIsInstance(success, bool)
    
    def test_get_summary(self):
        """Test summary generation"""
        # Run verification
        self.verifier.verify_all()
        
        # Get summary
        summary = self.verifier.get_summary()
        
        # Summary should have all status types
        self.assertIn('ok', summary)
        self.assertIn('warning', summary)
        self.assertIn('error', summary)
        self.assertIn('not_found', summary)
        
        # All counts should be non-negative
        for count in summary.values():
            self.assertGreaterEqual(count, 0)
        
        # Total should match results count
        total = sum(summary.values())
        self.assertEqual(total, len(self.verifier.results))
    
    def test_verification_result_dataclass(self):
        """Test VerificationResult dataclass"""
        result = VerificationResult(
            component="TestComponent",
            status=VerificationStatus.OK,
            message="Test message",
            details="Test details"
        )
        
        self.assertEqual(result.component, "TestComponent")
        self.assertEqual(result.status, VerificationStatus.OK)
        self.assertEqual(result.message, "Test message")
        self.assertEqual(result.details, "Test details")
    
    def test_run_system_verification(self):
        """Test standalone verification function"""
        # Should return boolean
        result = run_system_verification()
        self.assertIsInstance(result, bool)


class TestVerificationStatus(unittest.TestCase):
    """Test VerificationStatus enum"""
    
    def setUp(self):
        """Set up test fixtures"""
        if not VERIFICATION_AVAILABLE:
            self.skipTest("system_verification module not available")
    
    def test_status_values(self):
        """Test all status values exist"""
        self.assertEqual(VerificationStatus.OK.value, "ok")
        self.assertEqual(VerificationStatus.WARNING.value, "warning")
        self.assertEqual(VerificationStatus.ERROR.value, "error")
        self.assertEqual(VerificationStatus.NOT_FOUND.value, "not_found")


if __name__ == '__main__':
    print("Running System Verification Tests")
    print("=" * 60)
    
    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All system verification tests passed!")
    else:
        print("❌ Some tests failed")
        if result.failures:
            print(f"Failures: {len(result.failures)}")
        if result.errors:
            print(f"Errors: {len(result.errors)}")
    
    sys.exit(0 if result.wasSuccessful() else 1)
