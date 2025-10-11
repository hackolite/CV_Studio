#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example/Demo script showing how to use the dummy servers
This script demonstrates:
1. Starting servers programmatically
2. Connecting to each server type
3. Receiving and processing data
"""

import os
import sys
import time
import json
import asyncio
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def demo_api_server():
    """Demonstrate API server usage"""
    print("\n" + "=" * 60)
    print("DEMO: API Server")
    print("=" * 60)
    
    base_url = "http://localhost:8080"
    
    # Test status endpoint
    print("\n1. Fetching server status...")
    response = urllib.request.urlopen(f"{base_url}/status")
    data = json.loads(response.read().decode())
    print(f"   Status: {data['status']}")
    print(f"   Available endpoints: {', '.join(data['endpoints'])}")
    
    # Test float endpoint multiple times
    print("\n2. Fetching random float values (5 times)...")
    float_values = []
    for i in range(5):
        response = urllib.request.urlopen(f"{base_url}/float")
        data = json.loads(response.read().decode())
        float_values.append(data['value'])
        print(f"   Sample {i+1}: {data['value']:.4f}")
    
    print(f"   Average: {sum(float_values)/len(float_values):.4f}")
    print(f"   Min: {min(float_values):.4f}, Max: {max(float_values):.4f}")
    
    # Test image endpoint
    print("\n3. Fetching random image...")
    response = urllib.request.urlopen(f"{base_url}/image")
    image_data = response.read()
    print(f"   Image size: {len(image_data)} bytes")
    print(f"   Image format: PNG")
    
    # Save image
    output_path = "/tmp/demo_api_image.png"
    with open(output_path, 'wb') as f:
        f.write(image_data)
    print(f"   Saved to: {output_path}")
    
    print("\n✓ API Server demo completed!")


async def demo_websocket_server_float():
    """Demonstrate WebSocket server with float data"""
    print("\n" + "=" * 60)
    print("DEMO: WebSocket Server (Float)")
    print("=" * 60)
    
    try:
        import websockets
    except ImportError:
        print("✗ websockets library not installed. Install with: pip install websockets")
        return
    
    uri = "ws://localhost:8766"
    
    print(f"\n1. Connecting to {uri}...")
    async with websockets.connect(uri) as websocket:
        print("   ✓ Connected!")
        
        # Receive welcome message
        print("\n2. Receiving welcome message...")
        message = await websocket.recv()
        data = json.loads(message)
        print(f"   Type: {data['type']}")
        print(f"   Message: {data['message']}")
        print(f"   Interval: {data['interval']}s")
        
        # Receive and display 10 float values
        print("\n3. Receiving float stream (10 values)...")
        float_values = []
        for i in range(10):
            message = await websocket.recv()
            data = json.loads(message)
            float_values.append(data['value'])
            print(f"   Value {i+1:2d}: {data['value']:8.4f} (timestamp: {data['timestamp']})")
        
        print(f"\n   Statistics:")
        print(f"   - Average: {sum(float_values)/len(float_values):.4f}")
        print(f"   - Min: {min(float_values):.4f}")
        print(f"   - Max: {max(float_values):.4f}")
    
    print("\n✓ WebSocket Float demo completed!")


async def demo_websocket_server_image():
    """Demonstrate WebSocket server with image data"""
    print("\n" + "=" * 60)
    print("DEMO: WebSocket Server (Image)")
    print("=" * 60)
    
    try:
        import websockets
        import base64
        from PIL import Image
        import io
    except ImportError as e:
        print(f"✗ Required library not installed: {e}")
        return
    
    uri = "ws://localhost:8765"
    
    print(f"\n1. Connecting to {uri}...")
    async with websockets.connect(uri, max_size=2**21) as websocket:  # 2MB limit
        print("   ✓ Connected!")
        
        # Receive welcome message
        message = await websocket.recv()
        data = json.loads(message)
        print(f"\n2. Welcome: {data['message']}")
        
        # Receive and process 3 images
        print("\n3. Receiving image stream (3 images)...")
        for i in range(3):
            message = await websocket.recv()
            data = json.loads(message)
            
            # Decode base64 image
            image_data = base64.b64decode(data['data'])
            image = Image.open(io.BytesIO(image_data))
            
            print(f"   Image {i+1}:")
            print(f"     - Format: {data['format']}")
            print(f"     - Size: {data['width']}x{data['height']}")
            print(f"     - Data size: {len(image_data)} bytes")
            print(f"     - PIL size: {image.size}")
            
            # Optionally save the first image
            if i == 0:
                output_path = "/tmp/demo_ws_image.png"
                image.save(output_path)
                print(f"     - Saved to: {output_path}")
    
    print("\n✓ WebSocket Image demo completed!")


def start_servers():
    """Start all required servers"""
    print("\n" + "=" * 60)
    print("Starting Dummy Servers")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    processes = []
    
    # Start API server
    api_script = os.path.join(base_dir, 'api_server.py')
    api_proc = subprocess.Popen(
        [sys.executable, api_script, '--port', '8080'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    processes.append(('API (port 8080)', api_proc))
    print("✓ Started API server on port 8080")
    
    # Start WebSocket server for images
    ws_script = os.path.join(base_dir, 'websocket_server.py')
    ws_image_proc = subprocess.Popen(
        [sys.executable, ws_script, '--port', '8765', '--type', 'image', '--interval', '1.0'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    processes.append(('WebSocket Image (port 8765)', ws_image_proc))
    print("✓ Started WebSocket server (images) on port 8765")
    
    # Start WebSocket server for floats
    ws_float_proc = subprocess.Popen(
        [sys.executable, ws_script, '--port', '8766', '--type', 'float', '--interval', '0.5'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    processes.append(('WebSocket Float (port 8766)', ws_float_proc))
    print("✓ Started WebSocket server (floats) on port 8766")
    
    print("\nWaiting for servers to initialize...")
    time.sleep(3)
    print("=" * 60)
    
    return processes


def stop_servers(processes):
    """Stop all servers"""
    print("\n" + "=" * 60)
    print("Stopping Servers")
    print("=" * 60)
    
    for name, proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
            print(f"✓ Stopped {name}")
        except subprocess.TimeoutExpired:
            proc.kill()
            print(f"✓ Killed {name}")
        except Exception as e:
            print(f"✗ Error stopping {name}: {e}")
    
    print("=" * 60)


async def run_all_demos():
    """Run all demonstration functions"""
    # Demo API server
    demo_api_server()
    
    # Demo WebSocket servers
    await demo_websocket_server_float()
    await demo_websocket_server_image()


def main():
    """Main demo function"""
    print("\n" + "=" * 60)
    print("DUMMY SERVERS DEMONSTRATION")
    print("=" * 60)
    print("\nThis demo will:")
    print("1. Start API, WebSocket (image), and WebSocket (float) servers")
    print("2. Connect to each server and retrieve data")
    print("3. Display the received data")
    print("4. Stop all servers")
    print("\nPress Ctrl+C to abort at any time.")
    print("=" * 60)
    
    # Start servers
    processes = start_servers()
    
    try:
        # Run demonstrations
        asyncio.run(run_all_demos())
        
        # Summary
        print("\n" + "=" * 60)
        print("DEMO SUMMARY")
        print("=" * 60)
        print("\n✓ All demonstrations completed successfully!")
        print("\nServers demonstrated:")
        print("  - API Server: HTTP REST endpoints for images and floats")
        print("  - WebSocket (Image): Streaming random images")
        print("  - WebSocket (Float): Streaming random float values")
        print("\nYou can use these servers to test the CV_Studio nodes:")
        print("  - API Node: http://localhost:8080/image or /float")
        print("  - WebSocket Node: ws://localhost:8765 or ws://localhost:8766")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n✗ Demo interrupted by user")
    except Exception as e:
        print(f"\n✗ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Stop all servers
        stop_servers(processes)


if __name__ == '__main__':
    main()
