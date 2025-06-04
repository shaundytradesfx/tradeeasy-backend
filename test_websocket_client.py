#!/usr/bin/env python3
"""
WebSocket Test Client for TradeEasy Week 5 Implementation.

This script tests the real-time WebSocket functionality by connecting to
the /ws/sentiment endpoint and listening for broadcasts.
"""

import asyncio
import json
import sys
import websockets
from datetime import datetime


async def test_websocket_connection():
    """Test WebSocket connection and listen for messages."""
    uri = "ws://127.0.0.1:8000/ws/sentiment"
    
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket!")
            
            # Send a test message
            test_message = {
                "type": "test",
                "message": "Hello from test client",
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send(json.dumps(test_message))
            print(f"📤 Sent test message: {test_message}")
            
            # Listen for messages
            print("🎧 Listening for messages... (Press Ctrl+C to stop)")
            message_count = 0
            
            async for message in websocket:
                message_count += 1
                try:
                    data = json.loads(message)
                    msg_type = data.get("type", "unknown")
                    timestamp = data.get("timestamp", "")
                    
                    print(f"\n📨 Message #{message_count} [{msg_type}] at {timestamp}")
                    
                    if msg_type == "connection_established":
                        print(f"  🎉 Connection established: {data.get('message')}")
                        print(f"  👥 Active connections: {data.get('active_connections')}")
                        
                    elif msg_type == "echo":
                        print(f"  🔄 Echo response: {data.get('message')}")
                        
                    elif msg_type == "sentiment_update":
                        article = data.get("article", {})
                        sentiment = data.get("sentiment", {})
                        print(f"  📰 New article: {article.get('title', 'Unknown')}")
                        print(f"  💭 FinBERT score: {sentiment.get('finbert_score', 'N/A')}")
                        print(f"  📊 Lexicon score: {sentiment.get('lexicon_score', 'N/A')}")
                        print(f"  🏷️  Asset class: {article.get('asset_class', 'Unknown')}")
                        
                    elif msg_type == "aggregate_update":
                        asset = data.get("asset", {})
                        print(f"  📈 Aggregate update for {asset.get('symbol', 'Unknown')}")
                        print(f"  📊 Average sentiment: {asset.get('avg_sentiment', 'N/A')}")
                        print(f"  📝 Article count: {asset.get('article_count', 'N/A')}")
                        
                    elif msg_type == "alert_triggered":
                        alert = data.get("alert", {})
                        print(f"  🚨 Alert triggered for {alert.get('asset_symbol', 'Unknown')}")
                        print(f"  🎯 Threshold: {alert.get('threshold', 'N/A')} ({alert.get('direction', 'N/A')})")
                        print(f"  📊 Current sentiment: {alert.get('current_sentiment', 'N/A')}")
                        
                    else:
                        print(f"  🔮 Unknown message type: {data}")
                        
                except json.JSONDecodeError:
                    print(f"  ⚠️  Invalid JSON message: {message}")
                except Exception as e:
                    print(f"  ❌ Error processing message: {e}")
                    
    except websockets.exceptions.ConnectionClosed:
        print("❌ WebSocket connection closed")
    except websockets.exceptions.InvalidURI:
        print("❌ Invalid WebSocket URI")
    except Exception as e:
        print(f"❌ Error connecting to WebSocket: {e}")


async def test_websocket_stats():
    """Test the WebSocket stats endpoint."""
    import aiohttp
    
    print("\n🔍 Testing WebSocket stats endpoint...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://127.0.0.1:8000/api/websocket/stats") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ WebSocket stats: {json.dumps(data, indent=2)}")
                else:
                    print(f"❌ Failed to get stats: {response.status}")
    except Exception as e:
        print(f"❌ Error getting WebSocket stats: {e}")


async def main():
    """Main test function."""
    print("🚀 TradeEasy WebSocket Test Client - Week 5")
    print("=" * 50)
    
    # Test stats endpoint first
    await test_websocket_stats()
    
    # Test WebSocket connection
    try:
        await test_websocket_connection()
    except KeyboardInterrupt:
        print("\n👋 Test client stopped by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0) 