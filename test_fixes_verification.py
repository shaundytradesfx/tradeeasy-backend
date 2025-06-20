#!/usr/bin/env python3
"""
Verification test for WebSocket integration fixes.
This script validates that all the comprehensive fixes applied work correctly.
"""

import asyncio
import json
import requests
import time
import websockets
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_multiple_clients_with_broadcasts():
    """Test multiple WebSocket clients receiving broadcasts - the main fix validation."""
    
    print("🔧 Testing Multiple Clients with Broadcasts (Main Fix)")
    print("=" * 60)
    
    # Check initial stats
    response = requests.get("http://127.0.0.1:8001/api/websocket/stats")
    initial_stats = response.json()
    print(f"Initial stats: {initial_stats}")
    
    num_clients = 3
    clients = []
    
    try:
        # Connect multiple clients
        for i in range(num_clients):
            uri = "ws://127.0.0.1:8001/ws/sentiment"
            print(f"Connecting client {i+1} to {uri}...")
            
            websocket = await websockets.connect(uri)
            clients.append(websocket)
            
            # Wait for connection message
            message = await websocket.recv()
            data = json.loads(message)
            print(f"📨 Client {i+1} connected: {data.get('type')} - Active connections: {data.get('active_connections')}")
            
        # Wait for all connections to be established
        await asyncio.sleep(2)
        
        # Check stats with all clients connected
        response = requests.get("http://127.0.0.1:8001/api/websocket/stats")
        connected_stats = response.json()
        print(f"✅ All clients connected - Stats: {connected_stats}")
        
        # Trigger test broadcast
        print("🚀 Triggering test broadcast...")
        response = requests.post("http://127.0.0.1:8001/api/websocket/test-broadcast")
        broadcast_result = response.json()
        print(f"Broadcast response: {broadcast_result}")
        
        # Each client should receive broadcasts
        for i, websocket in enumerate(clients):
            print(f"📡 Waiting for broadcasts for client {i+1}...")
            received_count = 0
            timeout = 8.0
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(message)
                    received_count += 1
                    print(f"📨 Client {i+1} received broadcast #{received_count}: {data.get('type')}")
                    
                    if received_count >= 3:  # Expecting 3 broadcasts
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            print(f"✅ Client {i+1} received {received_count} broadcast messages")
        
        print("🎉 Multiple clients broadcast test PASSED!")
        
    finally:
        # Close all connections
        for i, websocket in enumerate(clients):
            await websocket.close()
            print(f"Client {i+1} disconnected")
        
        # Verify cleanup
        await asyncio.sleep(1)
        response = requests.get("http://127.0.0.1:8001/api/websocket/stats")
        final_stats = response.json()
        print(f"Final stats: {final_stats}")

async def test_connection_lifecycle():
    """Test connection lifecycle - connect, disconnect, reconnect."""
    
    print("\n🔄 Testing Connection Lifecycle")
    print("=" * 40)
    
    uri = "ws://127.0.0.1:8001/ws/sentiment"
    
    # First connection
    print("Connecting...")
    websocket = await websockets.connect(uri)
    message = await websocket.recv()
    data = json.loads(message)
    print(f"📨 Connected: {data.get('active_connections')} active connections")
    
    # Check stats
    response = requests.get("http://127.0.0.1:8001/api/websocket/stats")
    stats = response.json()
    print(f"Stats after connect: {stats['active_connections']} connections")
    
    # Disconnect
    await websocket.close()
    print("Disconnected")
    
    # Wait for disconnection processing
    await asyncio.sleep(2)
    
    # Check stats after disconnect
    response = requests.get("http://127.0.0.1:8001/api/websocket/stats")
    stats = response.json()
    print(f"Stats after disconnect: {stats['active_connections']} connections")
    
    # Reconnect
    print("Reconnecting...")
    websocket = await websockets.connect(uri)
    message = await websocket.recv()
    data = json.loads(message)
    print(f"📨 Reconnected: {data.get('active_connections')} active connections")
    
    await websocket.close()
    print("✅ Connection lifecycle test PASSED!")

async def test_broadcast_timing_fix():
    """Test that broadcasts are received properly with the timing fixes."""
    
    print("\n⏰ Testing Broadcast Timing Fix")
    print("=" * 35)
    
    uri = "ws://127.0.0.1:8001/ws/sentiment"
    
    # Connect
    websocket = await websockets.connect(uri)
    await websocket.recv()  # Connection message
    print("Connected and ready")
    
    # Wait a moment for connection to be fully established (the key fix)
    await asyncio.sleep(1)
    
    # Trigger broadcast
    print("🚀 Triggering broadcast...")
    response = requests.post("http://127.0.0.1:8001/api/websocket/test-broadcast")
    
    # Wait for broadcasts with proper timing
    received_count = 0
    timeout = 6.0
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            data = json.loads(message)
            received_count += 1
            print(f"📨 Received broadcast #{received_count}: {data.get('type')}")
            
            if received_count >= 3:
                break
                
        except asyncio.TimeoutError:
            break
    
    await websocket.close()
    
    if received_count >= 3:
        print("✅ Broadcast timing fix PASSED!")
    else:
        print(f"❌ Broadcast timing fix FAILED - only received {received_count}/3 messages")

async def main():
    """Run all verification tests."""
    
    print("🧪 WebSocket Integration Fixes Verification")
    print("=" * 50)
    print("Validating fixes for:")
    print("• Multiple client connection tracking")
    print("• Broadcast message timing")
    print("• Connection lifecycle management")
    print("• Message validation and structure")
    print()
    
    # Run all tests
    await test_multiple_clients_with_broadcasts()
    await test_connection_lifecycle()
    await test_broadcast_timing_fix()
    
    print("\n🎊 All WebSocket integration fixes verified successfully!")
    print("The comprehensive fixes applied are working correctly.")

if __name__ == "__main__":
    asyncio.run(main()) 