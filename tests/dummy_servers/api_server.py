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
        elif self.path == '/map':
            self.serve_map()
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
    
    def serve_map(self):
        """Serve map data with latitude/longitude coordinates"""
        # Generate sample location data around various world cities
        # This simulates GPS tracking, sensor networks, or IoT devices
        
        cities = [
            {"name": "Paris", "lat": 48.8566, "lon": 2.3522},
            {"name": "London", "lat": 51.5074, "lon": -0.1278},
            {"name": "New York", "lat": 40.7128, "lon": -74.0060},
            {"name": "Tokyo", "lat": 35.6762, "lon": 139.6503},
            {"name": "Sydney", "lat": -33.8688, "lon": 151.2093},
            {"name": "San Francisco", "lat": 37.7749, "lon": -122.4194},
            {"name": "Berlin", "lat": 52.5200, "lon": 13.4050},
            {"name": "Singapore", "lat": 1.3521, "lon": 103.8198},
        ]
        
        # Randomly select 3-5 cities
        num_points = random.randint(3, 5)
        selected_cities = random.sample(cities, num_points)
        
        # Add random offset to simulate movement/variation
        points = []
        for city in selected_cities:
            lat_offset = random.uniform(-0.05, 0.05)
            lon_offset = random.uniform(-0.05, 0.05)
            points.append({
                "name": city["name"],
                "latitude": city["lat"] + lat_offset,
                "longitude": city["lon"] + lon_offset,
                "timestamp": time.time()
            })
        
        # Create response in a format compatible with the Map node
        data = {
            "points": points,
            "timestamp": time.time(),
            "count": len(points)
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
            'endpoints': ['/image', '/float', '/map', '/status'],
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
        print(f"  - http://{self.host}:{self.port}/map (GET) - Returns map data with lat/lon")
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
