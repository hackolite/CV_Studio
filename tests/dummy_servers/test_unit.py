#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for server classes (no server startup required)
"""

import unittest
import sys
import os

# Add dummy_servers directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestServerClasses(unittest.TestCase):
    """Test server class instantiation and configuration"""
    
    def test_api_server_import(self):
        """Test that API server can be imported"""
        from api_server import DummyAPIServer, APIHandler
        self.assertIsNotNone(DummyAPIServer)
        self.assertIsNotNone(APIHandler)
    
    def test_api_server_initialization(self):
        """Test API server initialization"""
        from api_server import DummyAPIServer
        server = DummyAPIServer(host='localhost', port=9999)
        self.assertEqual(server.host, 'localhost')
        self.assertEqual(server.port, 9999)
        self.assertIsNone(server.server)
    
    def test_websocket_server_import(self):
        """Test that WebSocket server can be imported"""
        try:
            from websocket_server import DummyWebSocketServer
            self.assertIsNotNone(DummyWebSocketServer)
        except ImportError:
            self.skipTest("websockets library not installed")
    
    def test_websocket_server_initialization(self):
        """Test WebSocket server initialization"""
        try:
            from websocket_server import DummyWebSocketServer
            server = DummyWebSocketServer(
                host='localhost',
                port=9999,
                interval=1.0
            )
            self.assertEqual(server.host, 'localhost')
            self.assertEqual(server.port, 9999)
            self.assertEqual(server.interval, 1.0)
            self.assertEqual(len(server.clients), 0)
        except ImportError:
            self.skipTest("websockets library not installed")
    
    def test_websocket_server_float_initialization(self):
        """Test WebSocket server with float data type"""
        try:
            from websocket_server import DummyWebSocketServer
            server = DummyWebSocketServer(
                host='localhost',
                port=9999,
                interval=0.5
            )
            self.assertEqual(server.interval, 0.5)
        except ImportError:
            self.skipTest("websockets library not installed")
    
    def test_webrtc_server_import(self):
        """Test that WebRTC server can be imported"""
        self.skipTest("WebRTC libraries not required for basic testing")
    
    def test_webrtc_server_initialization(self):
        """Test WebRTC server initialization"""
        self.skipTest("WebRTC libraries not required for basic testing")


class TestAPIServerHandlers(unittest.TestCase):
    """Test API server handler logic"""
    
    def test_handler_exists(self):
        """Test that APIHandler class exists"""
        from api_server import APIHandler
        self.assertTrue(hasattr(APIHandler, 'do_GET'))
        self.assertTrue(hasattr(APIHandler, 'serve_image'))
        self.assertTrue(hasattr(APIHandler, 'serve_float'))
        self.assertTrue(hasattr(APIHandler, 'serve_map'))
        self.assertTrue(hasattr(APIHandler, 'serve_status'))


class TestFileStructure(unittest.TestCase):
    """Test file structure and documentation"""
    
    def test_readme_exists(self):
        """Test that README exists"""
        readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
        self.assertTrue(os.path.exists(readme_path))
    
    def test_requirements_exists(self):
        """Test that requirements.txt exists"""
        req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
        self.assertTrue(os.path.exists(req_path))
    
    def test_all_scripts_exist(self):
        """Test that all expected scripts exist"""
        base_dir = os.path.dirname(__file__)
        expected_files = [
            'api_server.py',
            'websocket_server.py',
            'webrtc_server.py',
            'run_servers.py',
            'test_servers.py',
            'demo.py',
            'launch.sh',
            'README.md',
            'requirements.txt',
            '__init__.py'
        ]
        
        for filename in expected_files:
            filepath = os.path.join(base_dir, filename)
            self.assertTrue(
                os.path.exists(filepath),
                f"Expected file {filename} does not exist"
            )
    
    def test_scripts_are_executable(self):
        """Test that Python scripts are executable"""
        base_dir = os.path.dirname(__file__)
        scripts = [
            'api_server.py',
            'websocket_server.py',
            'webrtc_server.py',
            'run_servers.py',
            'test_servers.py',
            'demo.py'
        ]
        
        for script in scripts:
            filepath = os.path.join(base_dir, script)
            # Check if file has execute permission
            self.assertTrue(
                os.access(filepath, os.X_OK),
                f"Script {script} is not executable"
            )


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Running Unit Tests (No Server Startup Required)")
    print("=" * 60 + "\n")
    
    # Run tests
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print("=" * 60 + "\n")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
