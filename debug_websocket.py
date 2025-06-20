#!/usr/bin/env python3
"""
Debug script to test WebSocket functionality manually.
"""

import asyncio
import json
import logging
import time
import websockets
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_connection():
    """Test WebSocket connection and message reception."""
    uri = "ws://127.0.0.1:8000/ws/sentiment"
    
    try:
        logger.info(f"Connecting to {uri}...")
        websocket = await websockets.connect(uri)
        logger.info("✅ Connected to WebSocket!")
        
        # Listen for initial connection message
        logger.info("Waiting for connection message...")
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)
            logger.info(f"📨 Received: {data}")
        except asyncio.TimeoutError:
            logger.warning("No initial message received")
        
        # Trigger test broadcast
        logger.info("Triggering test broadcast...")
        response = requests.post("http://127.0.0.1:8000/api/websocket/test-broadcast")
        logger.info(f"Broadcast response: {response.json()}")
        
        # Listen for broadcast messages
        logger.info("Listening for broadcast messages...")
        messages_received = 0
        timeout = 10.0
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                data = json.loads(message)
                messages_received += 1
                logger.info(f"📨 Message #{messages_received}: {data.get('type', 'unknown')} - {data.get('message', '')}")
                
                if messages_received >= 3:  # Expecting 3 broadcasts
                    break
                    
            except asyncio.TimeoutError:
                logger.info("Timeout waiting for more messages")
                break
        
        logger.info(f"Total messages received: {messages_received}")
        
        await websocket.close()
        logger.info("WebSocket connection closed")
        
    except Exception as e:
        logger.error(f"WebSocket test failed: {e}")
        
async def test_multiple_connections():
    """Test multiple WebSocket connections."""
    uri = "ws://127.0.0.1:8000/ws/sentiment"
    num_clients = 3
    clients = []
    
    try:
        # Connect multiple clients
        logger.info(f"Connecting {num_clients} clients...")
        for i in range(num_clients):
            websocket = await websockets.connect(uri)
            clients.append(websocket)
            logger.info(f"Client {i+1} connected")
            
            # Wait for connection message
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                data = json.loads(message)
                logger.info(f"Client {i+1} received: {data.get('type')} - active_connections: {data.get('active_connections')}")
            except asyncio.TimeoutError:
                logger.warning(f"Client {i+1} didn't receive connection message")
        
        # Trigger test broadcast
        logger.info("Triggering test broadcast with multiple clients...")
        response = requests.post("http://127.0.0.1:8000/api/websocket/test-broadcast")
        logger.info(f"Broadcast response: {response.json()}")
        
        # Listen for broadcasts on all clients
        await asyncio.sleep(2)  # Wait for broadcasts
        
        for i, websocket in enumerate(clients):
            messages_received = 0
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    messages_received += 1
                    logger.info(f"Client {i+1} received message #{messages_received}: {data.get('type')}")
            except asyncio.TimeoutError:
                logger.info(f"Client {i+1} received {messages_received} broadcast messages")
        
        # Close all connections
        for i, websocket in enumerate(clients):
            await websocket.close()
            logger.info(f"Client {i+1} disconnected")
            
    except Exception as e:
        logger.error(f"Multiple connections test failed: {e}")

async def main():
    """Main test function."""
    logger.info("🚀 Starting WebSocket debug tests...")
    
    # Check server health
    try:
        response = requests.get("http://127.0.0.1:8000/health")
        logger.info(f"Server health: {response.json()}")
    except Exception as e:
        logger.error(f"Server not responding: {e}")
        return
    
    # Test single connection
    logger.info("\n=== Test 1: Single WebSocket Connection ===")
    await test_websocket_connection()
    
    # Test multiple connections
    logger.info("\n=== Test 2: Multiple WebSocket Connections ===")
    await test_multiple_connections()
    
    logger.info("\n✨ Debug tests completed!")

if __name__ == "__main__":
    asyncio.run(main()) 