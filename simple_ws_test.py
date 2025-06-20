#!/usr/bin/env python3
"""
Simple WebSocket test to debug connection tracking issues.
"""

import asyncio
import json
import websockets
import requests
import time

async def test_connection_tracking():
    """Test if WebSocket connections are being tracked properly."""
    
    # Check initial stats
    response = requests.get("http://127.0.0.1:8001/api/websocket/stats")
    initial_stats = response.json()
    print(f"Initial stats: {initial_stats}")
    
    # Connect to WebSocket
    uri = "ws://127.0.0.1:8001/ws/sentiment"
    print(f"Connecting to {uri}...")
    
    websocket = await websockets.connect(uri)
    print("✅ Connected!")
    
    # Wait for connection message
    message = await websocket.recv()
    data = json.loads(message)
    print(f"📨 Connection message: {data}")
    
    # Check stats after connection
    response = requests.get("http://127.0.0.1:8001/api/websocket/stats")
    connected_stats = response.json()
    print(f"After connection stats: {connected_stats}")
    
    # Trigger test broadcast
    print("🚀 Triggering test broadcast...")
    response = requests.post("http://127.0.0.1:8001/api/websocket/test-broadcast")
    print(f"Broadcast response: {response.json()}")
    
    # Listen for broadcast messages
    broadcast_count = 0
    timeout = 10.0
    start_time = time.time()
    
    print("📡 Listening for broadcast messages...")
    while time.time() - start_time < timeout:
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            data = json.loads(message)
            broadcast_count += 1
            print(f"📨 Broadcast #{broadcast_count}: {data.get('type', 'unknown')}")
            
            if broadcast_count >= 3:  # Expecting 3 broadcasts
                break
                
        except asyncio.TimeoutError:
            print("⏰ Timeout waiting for more broadcasts")
            break
    
    print(f"✅ Received {broadcast_count} broadcast messages")
    
    # Close connection
    await websocket.close()
    
    # Check final stats
    response = requests.get("http://127.0.0.1:8001/api/websocket/stats")
    final_stats = response.json()
    print(f"Final stats: {final_stats}")
    
    print("🎉 Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_connection_tracking()) 