#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dummy API Server for testing
Serves images and floats via HTTP endpoints
"""

import io
import json
import time
import random
import numpy as np
from http.server import HTTPServer, BaseHTTPRequestHandler
from PIL import Image


class APIHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler that serves images and floats"""
    
    def log_message(self, format, *args):
        """Override to add custom logging"""
        print(f"[API Server] {self.address_string()} - {format % args}")
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/image':
            self.serve_image()
        elif self.path == '/float':
            self.serve_float()
        elif self.path == '/status':
            self.serve_status()
        else:
            self.send_error(404, "Endpoint not found")
    
    def serve_image(self):
        """Serve a random generated image"""
        # Generate a random color image (640x480)
        width, height = 640, 480
        
        # Create random image with some patterns
        img_array = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        
        # Add timestamp text
        img = Image.fromarray(img_array)
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        # Send response
        self.send_response(200)
        self.send_header('Content-Type', 'image/png')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(img_byte_arr.getvalue())
    
    def serve_float(self):
        """Serve a random float value"""
        value = random.uniform(0.0, 100.0)
        data = {
            'value': value,
            'timestamp': time.time()
        }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def serve_status(self):
        """Serve server status"""
        status = {
            'status': 'running',
            'endpoints': ['/image', '/float', '/status'],
            'timestamp': time.time()
        }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(status).encode())


class DummyAPIServer:
    """Dummy API Server wrapper"""
    
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
        self.server = None
    
    def start(self):
        """Start the API server"""
        self.server = HTTPServer((self.host, self.port), APIHandler)
        print(f"[API Server] Starting on {self.host}:{self.port}")
        print(f"[API Server] Available endpoints:")
        print(f"  - http://{self.host}:{self.port}/image (GET) - Returns random image")
        print(f"  - http://{self.host}:{self.port}/float (GET) - Returns random float")
        print(f"  - http://{self.host}:{self.port}/status (GET) - Returns server status")
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("\n[API Server] Shutting down...")
            self.server.shutdown()
    
    def stop(self):
        """Stop the API server"""
        if self.server:
            self.server.shutdown()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Dummy API Server')
    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    args = parser.parse_args()
    
    server = DummyAPIServer(host=args.host, port=args.port)
    server.start()
