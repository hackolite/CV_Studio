#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
General test script to launch and test dummy servers
"""

import os
import sys
import time
import argparse
import subprocess
import signal
from multiprocessing import Process

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ServerLauncher:
    """Launch and manage dummy servers"""
    
    def __init__(self):
        self.processes = []
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
    
    def start_api_server(self, host='localhost', port=8080):
        """Start API server"""
        script = os.path.join(self.base_dir, 'api_server.py')
        process = subprocess.Popen(
            [sys.executable, script, '--host', host, '--port', str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.processes.append(('API', process))
        print(f"✓ Started API Server on {host}:{port}")
        return process
    
    def start_websocket_server(self, host='localhost', port=8765, data_type='image', interval=1.0):
        """Start WebSocket server"""
        script = os.path.join(self.base_dir, 'websocket_server.py')
        process = subprocess.Popen(
            [sys.executable, script, '--host', host, '--port', str(port), 
             '--type', data_type, '--interval', str(interval)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.processes.append(('WebSocket', process))
        print(f"✓ Started WebSocket Server on {host}:{port} (type: {data_type})")
        return process
    
    def start_webrtc_server(self, host='0.0.0.0', port=8081, data_type='image'):
        """Start WebRTC server"""
        script = os.path.join(self.base_dir, 'webrtc_server.py')
        process = subprocess.Popen(
            [sys.executable, script, '--host', host, '--port', str(port), '--type', data_type],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.processes.append(('WebRTC', process))
        print(f"✓ Started WebRTC Server on {host}:{port} (type: {data_type})")
        return process
    
    def start_all(self, config=None):
        """Start all servers with configuration"""
        if config is None:
            config = {
                'api': {'host': 'localhost', 'port': 8080},
                'websocket_image': {'host': 'localhost', 'port': 8765, 'type': 'image'},
                'websocket_float': {'host': 'localhost', 'port': 8766, 'type': 'float'},
                'webrtc': {'host': '0.0.0.0', 'port': 8081, 'type': 'image'},
            }
        
        print("=" * 60)
        print("Starting Dummy Servers for Testing")
        print("=" * 60)
        
        # Start API server
        if 'api' in config:
            self.start_api_server(**config['api'])
        
        # Start WebSocket servers
        if 'websocket_image' in config:
            self.start_websocket_server(
                host=config['websocket_image']['host'],
                port=config['websocket_image']['port'],
                data_type='image'
            )
        
        if 'websocket_float' in config:
            self.start_websocket_server(
                host=config['websocket_float']['host'],
                port=config['websocket_float']['port'],
                data_type='float'
            )
        
        # Start WebRTC server
        if 'webrtc' in config:
            self.start_webrtc_server(**config['webrtc'])
        
        print("=" * 60)
        print("\nAll servers started!")
        print("\nEndpoints:")
        print("  API Server:")
        print(f"    - http://localhost:8080/image (GET image)")
        print(f"    - http://localhost:8080/float (GET float)")
        print(f"    - http://localhost:8080/status (GET status)")
        print("  WebSocket Servers:")
        print(f"    - ws://localhost:8765 (streaming images)")
        print(f"    - ws://localhost:8766 (streaming floats)")
        print("  WebRTC Server:")
        print(f"    - http://localhost:8081 (WebRTC signaling)")
        print("\nPress Ctrl+C to stop all servers")
        print("=" * 60)
    
    def stop_all(self):
        """Stop all running servers"""
        print("\n\nStopping all servers...")
        for name, process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✓ Stopped {name} Server")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"✓ Killed {name} Server")
            except Exception as e:
                print(f"✗ Error stopping {name} Server: {e}")
        
        self.processes.clear()
        print("All servers stopped.")
    
    def monitor(self):
        """Monitor running servers and display output"""
        try:
            while True:
                for name, process in self.processes:
                    # Check if process is still running
                    if process.poll() is not None:
                        print(f"✗ {name} Server stopped unexpectedly")
                        # Try to get error output
                        stdout, stderr = process.communicate()
                        if stderr:
                            print(f"Error: {stderr}")
                
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nReceived interrupt signal...")


def run_tests():
    """Run basic tests on the servers"""
    import urllib.request
    import json
    
    print("\n" + "=" * 60)
    print("Running Basic Tests")
    print("=" * 60)
    
    # Wait for servers to start
    print("\nWaiting for servers to start...")
    time.sleep(2)
    
    # Test API server
    print("\n1. Testing API Server...")
    try:
        # Test status endpoint
        response = urllib.request.urlopen('http://localhost:8080/status')
        data = json.loads(response.read().decode())
        print(f"   ✓ Status endpoint: {data['status']}")
        
        # Test float endpoint
        response = urllib.request.urlopen('http://localhost:8080/float')
        data = json.loads(response.read().decode())
        print(f"   ✓ Float endpoint: {data['value']:.2f}")
        
        # Test image endpoint
        response = urllib.request.urlopen('http://localhost:8080/image')
        print(f"   ✓ Image endpoint: {len(response.read())} bytes")
        
    except Exception as e:
        print(f"   ✗ API Server test failed: {e}")
    
    # Test WebSocket (basic connection test)
    print("\n2. Testing WebSocket Server...")
    try:
        import websockets
        
        async def test_websocket():
            uri = "ws://localhost:8765"
            async with websockets.connect(uri) as websocket:
                # Receive welcome message
                message = await websocket.recv()
                data = json.loads(message)
                print(f"   ✓ WebSocket connected: {data.get('message', 'OK')}")
                
                # Receive one data message
                message = await websocket.recv()
                data = json.loads(message)
                print(f"   ✓ Received data type: {data.get('type')}")
        
        import asyncio
        asyncio.run(test_websocket())
        
    except ImportError:
        print("   ⚠ websockets library not installed, skipping WebSocket test")
    except Exception as e:
        print(f"   ✗ WebSocket test failed: {e}")
    
    print("\n3. Testing WebRTC Server...")
    try:
        response = urllib.request.urlopen('http://localhost:8081/')
        html = response.read().decode()
        if 'WebRTC' in html:
            print("   ✓ WebRTC server is responding")
        else:
            print("   ✗ WebRTC server response unexpected")
    except Exception as e:
        print(f"   ✗ WebRTC test failed: {e}")
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Launch dummy servers for testing')
    parser.add_argument('--api-only', action='store_true', help='Start only API server')
    parser.add_argument('--websocket-only', action='store_true', help='Start only WebSocket servers')
    parser.add_argument('--webrtc-only', action='store_true', help='Start only WebRTC server')
    parser.add_argument('--test', action='store_true', help='Run tests after starting servers')
    parser.add_argument('--api-port', type=int, default=8080, help='API server port')
    parser.add_argument('--ws-image-port', type=int, default=8765, help='WebSocket image server port')
    parser.add_argument('--ws-float-port', type=int, default=8766, help='WebSocket float server port')
    parser.add_argument('--webrtc-port', type=int, default=8081, help='WebRTC server port')
    
    args = parser.parse_args()
    
    launcher = ServerLauncher()
    
    # Setup signal handler
    def signal_handler(sig, frame):
        launcher.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Determine which servers to start
    config = {}
    
    if args.api_only:
        config['api'] = {'host': 'localhost', 'port': args.api_port}
    elif args.websocket_only:
        config['websocket_image'] = {'host': 'localhost', 'port': args.ws_image_port, 'type': 'image'}
        config['websocket_float'] = {'host': 'localhost', 'port': args.ws_float_port, 'type': 'float'}
    elif args.webrtc_only:
        config['webrtc'] = {'host': '0.0.0.0', 'port': args.webrtc_port, 'type': 'image'}
    else:
        # Start all servers
        config = {
            'api': {'host': 'localhost', 'port': args.api_port},
            'websocket_image': {'host': 'localhost', 'port': args.ws_image_port, 'type': 'image'},
            'websocket_float': {'host': 'localhost', 'port': args.ws_float_port, 'type': 'float'},
            'webrtc': {'host': '0.0.0.0', 'port': args.webrtc_port, 'type': 'image'},
        }
    
    # Start servers
    launcher.start_all(config)
    
    # Run tests if requested
    if args.test:
        run_tests()
    
    # Monitor servers
    try:
        launcher.monitor()
    finally:
        launcher.stop_all()


if __name__ == '__main__':
    main()
