#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
System Verification Module

Verifies that required programs and packages are installed and properly configured.
Checks FFmpeg availability and validates Python package dependencies.
"""

import os
import sys
import subprocess
import importlib
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from .logging import get_logger

logger = get_logger(__name__)


class VerificationStatus(Enum):
    """Status of a verification check"""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    NOT_FOUND = "not_found"


@dataclass
class VerificationResult:
    """Result of a system verification check"""
    component: str
    status: VerificationStatus
    message: str
    details: Optional[str] = None


class SystemVerifier:
    """
    System verification utility for checking dependencies and programs.
    
    Performs checks for:
    - FFmpeg installation and version
    - Python package dependencies
    - OpenCV and its modules
    - Audio libraries (soundfile, sounddevice)
    """
    
    def __init__(self):
        self.results: List[VerificationResult] = []
    
    def verify_all(self) -> bool:
        """
        Run all verification checks.
        
        Returns:
            True if all critical checks pass, False otherwise
        """
        logger.info("Starting system verification...")
        
        # Check FFmpeg
        self.verify_ffmpeg()
        
        # Check Python packages
        self.verify_python_packages()
        
        # Check OpenCV
        self.verify_opencv()
        
        # Log results
        self._log_results()
        
        # Determine if all critical checks passed
        has_errors = any(r.status == VerificationStatus.ERROR for r in self.results)
        
        if has_errors:
            logger.error("System verification failed - critical issues detected")
            return False
        else:
            logger.info("System verification completed successfully")
            return True
    
    def verify_ffmpeg(self) -> VerificationResult:
        """
        Verify FFmpeg installation and version.
        
        Returns:
            VerificationResult for FFmpeg
        """
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Extract version from output
                version_line = result.stdout.split('\n')[0]
                
                verification = VerificationResult(
                    component="FFmpeg",
                    status=VerificationStatus.OK,
                    message="FFmpeg is installed and working",
                    details=version_line
                )
                logger.info(f"FFmpeg verification: OK - {version_line}")
            else:
                verification = VerificationResult(
                    component="FFmpeg",
                    status=VerificationStatus.ERROR,
                    message="FFmpeg command failed",
                    details=result.stderr
                )
                logger.error("FFmpeg command failed")
                
        except FileNotFoundError:
            verification = VerificationResult(
                component="FFmpeg",
                status=VerificationStatus.NOT_FOUND,
                message="FFmpeg not found in PATH",
                details="Please install FFmpeg: https://ffmpeg.org/download.html"
            )
            logger.error("FFmpeg not found - video encoding will not work")
            
        except subprocess.TimeoutExpired:
            verification = VerificationResult(
                component="FFmpeg",
                status=VerificationStatus.ERROR,
                message="FFmpeg command timed out",
                details="FFmpeg may be installed but not responding"
            )
            logger.error("FFmpeg command timed out")
            
        except Exception as e:
            verification = VerificationResult(
                component="FFmpeg",
                status=VerificationStatus.ERROR,
                message=f"Error checking FFmpeg: {str(e)}",
                details=None
            )
            logger.error(f"Error checking FFmpeg: {e}")
        
        self.results.append(verification)
        return verification
    
    def verify_python_packages(self) -> List[VerificationResult]:
        """
        Verify required Python packages are installed.
        
        Returns:
            List of VerificationResults for each package
        """
        required_packages = [
            ('cv2', 'opencv-contrib-python'),
            ('numpy', 'numpy'),
            ('dearpygui', 'dearpygui'),
            ('ffmpeg', 'ffmpeg-python'),
            ('soundfile', 'soundfile'),
            ('sounddevice', 'sounddevice'),
            ('librosa', 'librosa'),
        ]
        
        for import_name, package_name in required_packages:
            try:
                importlib.import_module(import_name)
                verification = VerificationResult(
                    component=f"Package: {package_name}",
                    status=VerificationStatus.OK,
                    message=f"{package_name} is installed"
                )
                logger.debug(f"Package {package_name}: OK")
                
            except ImportError:
                verification = VerificationResult(
                    component=f"Package: {package_name}",
                    status=VerificationStatus.WARNING,
                    message=f"{package_name} not found",
                    details=f"Install with: pip install {package_name}"
                )
                logger.warning(f"Package {package_name} not found")
            
            self.results.append(verification)
        
        return [r for r in self.results if r.component.startswith("Package:")]
    
    def verify_opencv(self) -> VerificationResult:
        """
        Verify OpenCV installation and available modules.
        
        Returns:
            VerificationResult for OpenCV
        """
        try:
            import cv2
            version = cv2.__version__
            
            # Check for important modules
            has_dnn = hasattr(cv2, 'dnn')
            has_video = hasattr(cv2, 'VideoCapture')
            has_writer = hasattr(cv2, 'VideoWriter')
            
            if has_dnn and has_video and has_writer:
                verification = VerificationResult(
                    component="OpenCV",
                    status=VerificationStatus.OK,
                    message=f"OpenCV {version} with required modules",
                    details=f"DNN: {has_dnn}, Video: {has_video}, Writer: {has_writer}"
                )
                logger.info(f"OpenCV verification: OK - version {version}")
            else:
                verification = VerificationResult(
                    component="OpenCV",
                    status=VerificationStatus.WARNING,
                    message=f"OpenCV {version} missing some modules",
                    details=f"DNN: {has_dnn}, Video: {has_video}, Writer: {has_writer}"
                )
                logger.warning(f"OpenCV missing modules - DNN: {has_dnn}, Video: {has_video}, Writer: {has_writer}")
                
        except ImportError:
            verification = VerificationResult(
                component="OpenCV",
                status=VerificationStatus.ERROR,
                message="OpenCV not found",
                details="Install with: pip install opencv-contrib-python"
            )
            logger.error("OpenCV not found")
        
        self.results.append(verification)
        return verification
    
    def get_results(self) -> List[VerificationResult]:
        """Get all verification results"""
        return self.results
    
    def get_summary(self) -> Dict[str, int]:
        """
        Get a summary of verification results.
        
        Returns:
            Dictionary with counts of each status
        """
        summary = {
            'ok': 0,
            'warning': 0,
            'error': 0,
            'not_found': 0
        }
        
        for result in self.results:
            summary[result.status.value] += 1
        
        return summary
    
    def _log_results(self):
        """Log all verification results"""
        logger.info("=" * 60)
        logger.info("SYSTEM VERIFICATION RESULTS")
        logger.info("=" * 60)
        
        for result in self.results:
            status_str = result.status.value.upper()
            logger.info(f"[{status_str:10}] {result.component}: {result.message}")
            if result.details:
                logger.debug(f"  Details: {result.details}")
        
        summary = self.get_summary()
        logger.info("=" * 60)
        logger.info(f"Summary - OK: {summary['ok']}, Warnings: {summary['warning']}, "
                   f"Errors: {summary['error']}, Not Found: {summary['not_found']}")
        logger.info("=" * 60)


def run_system_verification() -> bool:
    """
    Run system verification and return success status.
    
    Returns:
        True if all critical checks pass, False otherwise
    """
    verifier = SystemVerifier()
    return verifier.verify_all()


if __name__ == "__main__":
    # Run verification as standalone script
    from .logging import setup_logging
    setup_logging()
    
    success = run_system_verification()
    sys.exit(0 if success else 1)
