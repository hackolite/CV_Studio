#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dummy WebRTC Server for testing
Serves images and floats via WebRTC data channels
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
    from aiohttp import web
    import aiortc
    from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
    from av import VideoFrame
except ImportError:
    print("Required libraries not found. Install with: pip install aiohttp aiortc")
    web = None
    aiortc = None
    
    # Define dummy classes to allow module import when libraries are not available
    class VideoStreamTrack:
        """Dummy VideoStreamTrack class for when aiortc is not installed"""
        pass
    
    class VideoFrame:
        """Dummy VideoFrame class for when av is not installed"""
        pass
    
    class RTCPeerConnection:
        """Dummy RTCPeerConnection class for when aiortc is not installed"""
        pass
    
    class RTCSessionDescription:
        """Dummy RTCSessionDescription class for when aiortc is not installed"""
        pass


class RandomVideoStreamTrack(VideoStreamTrack):
    """Video stream track that generates random images"""
    
    def __init__(self, width=640, height=480, fps=30):
        super().__init__()
        self.width = width
        self.height = height
        self.fps = fps
        self.counter = 0
    
    async def recv(self):
        """Generate and return a random video frame"""
        pts, time_base = await self.next_timestamp()
        
        # Generate random image
        img_array = np.random.randint(0, 255, (self.height, self.width, 3), dtype=np.uint8)
        
        # Create video frame
        frame = VideoFrame.from_ndarray(img_array, format='rgb24')
        frame.pts = pts
        frame.time_base = time_base
        
        self.counter += 1
        return frame


class DummyWebRTCServer:
    """Dummy WebRTC Server"""
    
    def __init__(self, host='0.0.0.0', port=8080, data_type='image'):
        self.host = host
        self.port = port
        self.data_type = data_type
        self.pcs = set()
        self.app = None
    
    async def offer(self, request):
        """Handle WebRTC offer"""
        params = await request.json()
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        
        pc = RTCPeerConnection()
        self.pcs.add(pc)
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print(f"[WebRTC Server] Connection state: {pc.connectionState}")
            if pc.connectionState == "failed" or pc.connectionState == "closed":
                await pc.close()
                self.pcs.discard(pc)
        
        # Add video track if data type is image
        if self.data_type == 'image':
            video_track = RandomVideoStreamTrack()
            pc.addTrack(video_track)
            print("[WebRTC Server] Added video track")
        
        # Create data channel for floats
        if self.data_type == 'float':
            channel = pc.createDataChannel("data")
            
            @channel.on("open")
            def on_open():
                asyncio.ensure_future(self.send_float_data(channel))
            
            print("[WebRTC Server] Created data channel")
        
        # Handle offer
        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        return web.Response(
            content_type="application/json",
            text=json.dumps({
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type
            })
        )
    
    async def send_float_data(self, channel):
        """Send float data through data channel"""
        while channel.readyState == "open":
            value = random.uniform(0.0, 100.0)
            data = {
                'type': 'float',
                'value': value,
                'timestamp': time.time()
            }
            channel.send(json.dumps(data))
            print(f"[WebRTC Server] Sent float: {value:.2f}")
            await asyncio.sleep(1.0)
    
    async def on_shutdown(self, app):
        """Cleanup on shutdown"""
        coros = [pc.close() for pc in self.pcs]
        await asyncio.gather(*coros)
        self.pcs.clear()
    
    def create_app(self):
        """Create aiohttp application"""
        self.app = web.Application()
        self.app.router.add_post("/offer", self.offer)
        self.app.router.add_get("/", self.index)
        self.app.on_shutdown.append(self.on_shutdown)
        return self.app
    
    async def index(self, request):
        """Serve a simple index page"""
        html = """
        <html>
            <head><title>Dummy WebRTC Server</title></head>
            <body>
                <h1>Dummy WebRTC Server</h1>
                <p>Data type: {data_type}</p>
                <p>POST to /offer to establish WebRTC connection</p>
            </body>
        </html>
        """.format(data_type=self.data_type)
        return web.Response(text=html, content_type='text/html')
    
    def run(self):
        """Run the WebRTC server"""
        if web is None or aiortc is None:
            print("[WebRTC Server] ERROR: Required libraries not installed")
            print("Install with: pip install aiohttp aiortc")
            return
        
        print(f"[WebRTC Server] Starting on http://{self.host}:{self.port}")
        print(f"[WebRTC Server] Data type: {self.data_type}")
        
        app = self.create_app()
        web.run_app(app, host=self.host, port=self.port)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Dummy WebRTC Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--type', choices=['image', 'float'], default='image',
                        help='Type of data to serve (image or float)')
    args = parser.parse_args()
    
    server = DummyWebRTCServer(host=args.host, port=args.port, data_type=args.type)
    server.run()
