#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dummy WebSocket Server for testing
Serves floats via WebSocket
"""

import asyncio
import json
import time
import random

try:
    import websockets
except ImportError:
    print("websockets library not found. Install it with: pip install websockets")
    websockets = None


class DummyWebSocketServer:
    """Dummy WebSocket Server for testing that continuously streams float data via WebSocket connections."""
    
    def __init__(self, host='localhost', port=8765, interval=1.0):
        self.host = host
        self.port = port
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
                'message': 'Connected to dummy WebSocket server. Data type: float',
                'interval': self.interval
            }))
            
            # Continuously send data
            while True:
                await self.send_float(websocket)
                await asyncio.sleep(self.interval)
                
        except websockets.exceptions.ConnectionClosed:
            print(f"[WebSocket Server] Client disconnected: {client_address}")
        finally:
            self.clients.remove(websocket)
    
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
        print(f"[WebSocket Server] Data type: float")
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
    parser.add_argument('--interval', type=float, default=1.0,
                        help='Interval between messages in seconds')
    args = parser.parse_args()
    
    server = DummyWebSocketServer(
        host=args.host,
        port=args.port,
        interval=args.interval
    )
    server.run()
