#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration tests for dummy servers
Tests API, WebSocket, and WebRTC servers
"""

import os
import sys
import time
import unittest
import subprocess
import json
import urllib.request
import signal

# Add dummy_servers directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestDummyServers(unittest.TestCase):
    """Integration tests for dummy servers"""
    
    @classmethod
    def setUpClass(cls):
        """Start all servers before tests"""
        print("\n" + "=" * 60)
        print("Setting up test servers...")
        print("=" * 60)
        
        cls.base_dir = os.path.dirname(os.path.abspath(__file__))
        cls.processes = []
        
        # Start API server
        api_script = os.path.join(cls.base_dir, 'api_server.py')
        cls.api_process = subprocess.Popen(
            [sys.executable, api_script, '--port', '8080'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        cls.processes.append(cls.api_process)
        print("✓ Started API server on port 8080")
        
        # Start WebSocket server (float)
        ws_script = os.path.join(cls.base_dir, 'websocket_server.py')
        cls.ws_float_process = subprocess.Popen(
            [sys.executable, ws_script, '--port', '8765'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        cls.processes.append(cls.ws_float_process)
        print("✓ Started WebSocket server (float) on port 8765")
        
        # Wait for servers to start
        print("\nWaiting for servers to initialize...")
        time.sleep(3)
        print("=" * 60)
    
    @classmethod
    def tearDownClass(cls):
        """Stop all servers after tests"""
        print("\n" + "=" * 60)
        print("Stopping test servers...")
        print("=" * 60)
        
        for process in cls.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        
        print("✓ All servers stopped")
        print("=" * 60)
    
    def test_api_status_endpoint(self):
        """Test API server status endpoint"""
        response = urllib.request.urlopen('http://localhost:8080/status')
        data = json.loads(response.read().decode())
        
        self.assertEqual(data['status'], 'running')
        self.assertIn('endpoints', data)
        self.assertIn('timestamp', data)
        print("✓ API status endpoint test passed")
    
    def test_api_float_endpoint(self):
        """Test API server float endpoint"""
        response = urllib.request.urlopen('http://localhost:8080/float')
        data = json.loads(response.read().decode())
        
        self.assertIn('value', data)
        self.assertIn('timestamp', data)
        self.assertIsInstance(data['value'], (int, float))
        self.assertGreaterEqual(data['value'], 0.0)
        self.assertLessEqual(data['value'], 100.0)
        print(f"✓ API float endpoint test passed (value: {data['value']:.2f})")
    
    def test_api_image_endpoint(self):
        """Test API server image endpoint"""
        response = urllib.request.urlopen('http://localhost:8080/image')
        image_data = response.read()
        
        self.assertGreater(len(image_data), 0)
        # Check PNG header
        self.assertTrue(image_data.startswith(b'\x89PNG'))
        print(f"✓ API image endpoint test passed (size: {len(image_data)} bytes)")
    
    def test_websocket_float_server(self):
        """Test WebSocket server with float data"""
        try:
            import websockets
            import asyncio
            
            async def test():
                uri = "ws://localhost:8765"
                async with websockets.connect(uri) as websocket:
                    # Receive welcome message
                    welcome = await websocket.recv()
                    welcome_data = json.loads(welcome)
                    self.assertEqual(welcome_data['type'], 'welcome')
                    
                    # Receive float data
                    message = await websocket.recv()
                    data = json.loads(message)
                    self.assertEqual(data['type'], 'float')
                    self.assertIn('value', data)
                    self.assertIsInstance(data['value'], (int, float))
                    print(f"✓ WebSocket float test passed (value: {data['value']:.2f})")
            
            asyncio.run(test())
            
        except ImportError:
            self.skipTest("websockets library not installed")
    
    def test_multiple_api_requests(self):
        """Test multiple concurrent API requests"""
        results = []
        for i in range(5):
            response = urllib.request.urlopen('http://localhost:8080/float')
            data = json.loads(response.read().decode())
            results.append(data['value'])
        
        self.assertEqual(len(results), 5)
        # Verify all values are different (random)
        self.assertGreater(len(set(results)), 1)
        print(f"✓ Multiple API requests test passed (values: {[f'{v:.2f}' for v in results]})")


class TestServerScripts(unittest.TestCase):
    """Test server scripts can be imported and initialized"""
    
    def test_api_server_import(self):
        """Test API server can be imported"""
        from api_server import DummyAPIServer
        server = DummyAPIServer(host='localhost', port=9999)
        self.assertIsNotNone(server)
        print("✓ API server import test passed")
    
    def test_websocket_server_import(self):
        """Test WebSocket server can be imported"""
        try:
            from websocket_server import DummyWebSocketServer
            server = DummyWebSocketServer(host='localhost', port=9999)
            self.assertIsNotNone(server)
            print("✓ WebSocket server import test passed")
        except ImportError:
            self.skipTest("websockets library not installed")
    
    def test_webrtc_server_import(self):
        """Test WebRTC server can be imported"""
        try:
            from webrtc_server import DummyWebRTCServer
            server = DummyWebRTCServer(host='localhost', port=9999)
            self.assertIsNotNone(server)
            print("✓ WebRTC server import test passed")
        except ImportError:
            self.skipTest("WebRTC libraries not installed")


def run_quick_test():
    """Run a quick manual test without unittest framework"""
    print("\n" + "=" * 60)
    print("Quick Manual Test")
    print("=" * 60)
    
    # Start API server only for quick test
    base_dir = os.path.dirname(os.path.abspath(__file__))
    api_script = os.path.join(base_dir, 'api_server.py')
    
    print("\nStarting API server...")
    process = subprocess.Popen(
        [sys.executable, api_script, '--port', '8080'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    try:
        print("Waiting for server to start...")
        time.sleep(4)
        
        # Test status
        print("\n1. Testing status endpoint...")
        response = urllib.request.urlopen('http://localhost:8080/status')
        data = json.loads(response.read().decode())
        print(f"   Status: {data['status']}")
        print(f"   Endpoints: {data['endpoints']}")
        
        # Test float
        print("\n2. Testing float endpoint...")
        response = urllib.request.urlopen('http://localhost:8080/float')
        data = json.loads(response.read().decode())
        print(f"   Value: {data['value']:.4f}")
        
        # Test image
        print("\n3. Testing image endpoint...")
        response = urllib.request.urlopen('http://localhost:8080/image')
        image_data = response.read()
        print(f"   Image size: {len(image_data)} bytes")
        
        print("\n" + "=" * 60)
        print("✓ Quick test completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
    
    finally:
        print("\nStopping server...")
        process.terminate()
        process.wait(timeout=5)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test dummy servers')
    parser.add_argument('--quick', action='store_true', 
                        help='Run quick test without full test suite')
    args = parser.parse_args()
    
    if args.quick:
        run_quick_test()
    else:
        unittest.main(argv=[''], verbosity=2)
