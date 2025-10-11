#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dummy WebSocket Server for testing
Serves images and floats via WebSocket
"""

import asyncio
import json
import time
import random
import base64
import io
import numpy as np
from PIL import Image

try:
    import websockets
except ImportError:
    print("websockets library not found. Install it with: pip install websockets")
    websockets = None


class DummyWebSocketServer:
    """Dummy WebSocket Server that streams images and floats"""
    
    def __init__(self, host='localhost', port=8765, data_type='image', interval=1.0):
        self.host = host
        self.port = port
        self.data_type = data_type  # 'image' or 'float'
        self.interval = interval
        self.clients = set()
    
    async def handler(self, websocket):
        """Handle WebSocket connections"""
        self.clients.add(websocket)
        client_address = websocket.remote_address
        print(f"[WebSocket Server] Client connected: {client_address}")
        
        try:
            # Send welcome message
            await websocket.send(json.dumps({
                'type': 'welcome',
                'message': f'Connected to dummy WebSocket server. Data type: {self.data_type}',
                'interval': self.interval
            }))
            
            # Continuously send data
            while True:
                if self.data_type == 'image':
                    await self.send_image(websocket)
                elif self.data_type == 'float':
                    await self.send_float(websocket)
                
                await asyncio.sleep(self.interval)
                
        except websockets.exceptions.ConnectionClosed:
            print(f"[WebSocket Server] Client disconnected: {client_address}")
        finally:
            self.clients.remove(websocket)
    
    async def send_image(self, websocket):
        """Send a random generated image"""
        # Generate a smaller random color image (320x240)
        width, height = 320, 240
        img_array = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        
        # Convert to PIL Image
        img = Image.fromarray(img_array)
        
        # Convert to base64
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
        
        # Send as JSON
        data = {
            'type': 'image',
            'data': img_base64,
            'format': 'png',
            'width': width,
            'height': height,
            'timestamp': time.time()
        }
        
        await websocket.send(json.dumps(data))
        print(f"[WebSocket Server] Sent image ({width}x{height})")
    
    async def send_float(self, websocket):
        """Send a random float value"""
        value = random.uniform(0.0, 100.0)
        data = {
            'type': 'float',
            'value': value,
            'timestamp': time.time()
        }
        
        await websocket.send(json.dumps(data))
        print(f"[WebSocket Server] Sent float: {value:.2f}")
    
    async def start(self):
        """Start the WebSocket server"""
        if websockets is None:
            print("[WebSocket Server] ERROR: websockets library not installed")
            return
        
        print(f"[WebSocket Server] Starting on ws://{self.host}:{self.port}")
        print(f"[WebSocket Server] Data type: {self.data_type}")
        print(f"[WebSocket Server] Interval: {self.interval}s")
        
        async with websockets.serve(self.handler, self.host, self.port):
            print(f"[WebSocket Server] Server is running...")
            await asyncio.Future()  # Run forever
    
    def run(self):
        """Run the WebSocket server"""
        asyncio.run(self.start())


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Dummy WebSocket Server')
    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8765, help='Port to bind to')
    parser.add_argument('--type', choices=['image', 'float'], default='image',
                        help='Type of data to serve (image or float)')
    parser.add_argument('--interval', type=float, default=1.0,
                        help='Interval between messages in seconds')
    args = parser.parse_args()
    
    server = DummyWebSocketServer(
        host=args.host,
        port=args.port,
        data_type=args.type,
        interval=args.interval
    )
    server.run()
