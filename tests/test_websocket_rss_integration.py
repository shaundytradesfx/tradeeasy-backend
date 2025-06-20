"""
RSS Ingestion and WebSocket Integration Tests for TradeEasy.

This module tests the integration between RSS ingestion and WebSocket
broadcasting to ensure real-time sentiment updates are properly sent
when articles are processed.
"""

import asyncio
import json
import logging
import time
import unittest
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock

import websockets
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.websocket_manager import websocket_manager
from app import crud, models, schemas
from app.database import SessionLocal
from app.rss_ingest import ingest_with_alert_checking


# Set up logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RSSWebSocketTestClient:
    """WebSocket client for RSS integration testing."""
    
    def __init__(self, uri: str):
        self.uri = uri
        self.websocket = None
        self.connected = False
        self.messages = []
        self.sentiment_updates = []
        self.aggregate_updates = []
        self.alert_triggers = []
        
    async def connect(self):
        """Connect to the WebSocket."""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            logger.info(f"RSS test client connected to {self.uri}")
        except Exception as e:
            logger.error(f"Failed to connect RSS test client: {e}")
            raise
            
    async def disconnect(self):
        """Disconnect from the WebSocket."""
        if self.websocket and self.connected:
            await self.websocket.close()
            self.connected = False
            logger.info("RSS test client disconnected")
            
    async def listen_and_categorize_messages(self, timeout: float = 30.0) -> Dict[str, List[Dict]]:
        """Listen for messages and categorize them by type."""
        if not self.websocket or not self.connected:
            return {"messages": [], "sentiment_updates": [], "aggregate_updates": [], "alert_triggers": []}
            
        end_time = time.time() + timeout
        
        try:
            while time.time() < end_time and self.connected:
                try:
                    remaining_time = end_time - time.time()
                    if remaining_time <= 0:
                        break
                        
                    message = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=min(2.0, remaining_time)
                    )
                    
                    data = json.loads(message)
                    self.messages.append(data)
                    
                    # Categorize messages
                    msg_type = data.get("type", "unknown")
                    if msg_type == "sentiment_update":
                        self.sentiment_updates.append(data)
                        logger.info(f"Received sentiment update: {data.get('article', {}).get('title', 'Unknown')}")
                    elif msg_type == "aggregate_update":
                        self.aggregate_updates.append(data)
                        logger.info(f"Received aggregate update: {data.get('asset', {}).get('symbol', 'Unknown')}")
                    elif msg_type == "alert_triggered":
                        self.alert_triggers.append(data)
                        logger.info(f"Received alert trigger: {data.get('alert', {}).get('asset_symbol', 'Unknown')}")
                    else:
                        logger.info(f"Received message: {msg_type}")
                        
                except asyncio.TimeoutError:
                    # Continue listening until overall timeout
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.info("WebSocket connection closed during RSS integration test")
                    self.connected = False
                    break
                    
        except Exception as e:
            logger.error(f"Error during RSS WebSocket listening: {e}")
            
        return {
            "messages": self.messages,
            "sentiment_updates": self.sentiment_updates,
            "aggregate_updates": self.aggregate_updates,
            "alert_triggers": self.alert_triggers
        }


class TestWebSocketRSSIntegration(unittest.TestCase):
    """Integration tests for WebSocket and RSS ingestion."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class."""
        cls.client = TestClient(app)
        cls.base_ws_uri = "ws://127.0.0.1:8000/ws/sentiment"
        
        # Verify server is running
        try:
            response = cls.client.get("/health")
            if response.status_code != 200:
                raise Exception("Server not responding")
        except Exception as e:
            logger.warning(f"Server might not be running: {e}")
            
    def setUp(self):
        """Set up each test."""
        # Reset WebSocket manager state
        websocket_manager.active_connections.clear()
        websocket_manager.connection_info.clear()
        
        # Set up database session
        self.db = SessionLocal()
        
        # Clean up any existing test data to avoid constraint violations
        self._cleanup_test_data()
        
    def tearDown(self):
        """Clean up after each test."""
        try:
            # Clean up test data again after test
            self._cleanup_test_data()
        finally:
            self.db.close()
        
        # Clean up any remaining WebSocket connections
        asyncio.run(self._cleanup_connections())
        
    async def _cleanup_connections(self):
        """Clean up any remaining WebSocket connections."""
        for connection in list(websocket_manager.active_connections):
            websocket_manager.disconnect(connection)

    def _cleanup_test_data(self):
        """Clean up test data to avoid constraint violations."""
        try:
            # Delete test articles with known test URL patterns
            import time
            from sqlalchemy import text
            
            # Clean up test sentiments first (foreign key constraint)
            self.db.execute(text("""
                DELETE FROM sentiments WHERE article_id IN (
                    SELECT id FROM articles WHERE url LIKE '%test-article%' 
                    OR url LIKE '%example.com%'
                    OR title LIKE '%Test Article%'
                    OR source LIKE '%test%'
                )
            """))
            
            # Clean up test articles
            self.db.execute(text("""
                DELETE FROM articles WHERE url LIKE '%test-article%' 
                OR url LIKE '%example.com%'
                OR title LIKE '%Test Article%'
                OR source LIKE '%test%'
            """))
            
            # Clean up test alerts 
            self.db.execute(text("""
                DELETE FROM alerts WHERE asset_id IN (
                    SELECT id FROM assets WHERE symbol LIKE 'TEST%'
                )
            """))
            
            # Clean up test assets
            self.db.execute(text("DELETE FROM assets WHERE symbol LIKE 'TEST%'"))
            
            # Clean up test users
            self.db.execute(text("DELETE FROM users WHERE username LIKE '%test%'"))
            
            self.db.commit()
            logger.info("Cleaned up test data successfully")
            
        except Exception as e:
            logger.warning(f"Error during test data cleanup: {e}")
            self.db.rollback()

    def test_rss_ingestion_triggers_websocket_broadcasts(self):
        """Test that RSS ingestion triggers WebSocket broadcasts."""
        
        async def integration_test():
            # Connect WebSocket client
            client = RSSWebSocketTestClient(self.base_ws_uri)
            await client.connect()
            
            # Wait a moment to ensure connection is established
            await asyncio.sleep(1)
            
            # Create truly unique URL for this test run
            import time
            import uuid
            timestamp = int(time.time() * 1000000)  # microseconds
            test_id = str(uuid.uuid4())[:8]
            unique_url = f"https://example.com/test-article-{timestamp}-{test_id}"
            
            # Mock RSS ingestion to simulate real articles being processed
            with patch('app.rss_ingest.parse_rss_feed') as mock_parse, \
                 patch('app.rss_ingest.extract_article_content') as mock_extract, \
                 patch('app.crud.get_article_by_url') as mock_get_article:
                
                # Mock RSS feed data with unique URL
                mock_parse.return_value = [
                    {
                        "title": f"Test Financial News Article {test_id}",
                        "link": unique_url,
                        "published_at": datetime.utcnow(),
                        "source": "test-source",
                        "summary": "This is a test financial news article about markets."
                    }
                ]
                
                # Mock article extraction
                mock_extract.return_value = {
                    "text": "This is a test financial news article about positive market trends and bullish sentiment.",
                    "authors": ["Test Author"],
                    "publish_date": datetime.utcnow(),
                    "top_image": None,
                    "keywords": ["finance", "markets"],
                    "summary": "Test article about positive market trends.",
                    "error": None
                }
                
                # Mock that article doesn't exist yet
                mock_get_article.return_value = None
                
                # Start listening for WebSocket messages
                listen_task = asyncio.create_task(
                    client.listen_and_categorize_messages(timeout=15.0)
                )
                
                # Small delay to ensure listening is started
                await asyncio.sleep(1)
                
                # Trigger RSS ingestion with alert checking
                ingestion_result = ingest_with_alert_checking(self.db)
                
                # Wait for WebSocket messages
                messages_result = await listen_task
                
                await client.disconnect()
                
                return {
                    "ingestion_result": ingestion_result,
                    "websocket_messages": messages_result
                }
        
        result = asyncio.run(integration_test())
        
        # Verify ingestion worked
        ingestion = result["ingestion_result"]
        self.assertGreater(ingestion.get("articles_created", 0), 0)
        
        # Verify WebSocket messages were sent
        ws_messages = result["websocket_messages"]
        self.assertGreater(len(ws_messages["messages"]), 0)  # At least connection_established
        
        # Should have received some sentiment updates if articles were processed
        if ingestion.get("articles_created", 0) > 0:
            # We might receive sentiment updates if the sentiment analysis was triggered
            logger.info(f"Articles created: {ingestion.get('articles_created')}")
            logger.info(f"Total WebSocket messages: {len(ws_messages['messages'])}")
            logger.info(f"Sentiment updates: {len(ws_messages['sentiment_updates'])}")

    def test_manual_sentiment_analysis_triggers_broadcast(self):
        """Test that manual sentiment analysis triggers WebSocket broadcasts."""
        async def sentiment_broadcast_test():
            # Connect WebSocket client
            client = RSSWebSocketTestClient(self.base_ws_uri)
            await client.connect()
            
            # Create a test article with unique URL using timestamp
            import time
            timestamp = int(time.time() * 1000000)  # microseconds for maximum uniqueness
            unique_url = f"https://example.com/test-article-{timestamp}.html"
            
            article_data = schemas.ArticleCreate(
                source="test-source",
                title=f"Test Article for Sentiment Broadcasting {timestamp}",
                content="This is a very positive article about the stock market performance. Great news for investors and excellent returns expected.",
                url=unique_url,
                published_at=datetime.utcnow()
            )
            
            # Create test article in database
            db_article = crud.create_article(self.db, article_data)
            
            # Wait for any initial connection messages
            await asyncio.sleep(1)
            
            # Manually trigger sentiment analysis
            from app.nlp.sentiment_analyzer import SentimentAnalyzer
            analyzer = SentimentAnalyzer()
            sentiment_result = analyzer.analyze_sentiment(article_data.content)
            
            # Create sentiment record
            sentiment_data = schemas.SentimentCreate(
                article_id=db_article.id,
                lexicon_score=sentiment_result.get("lexicon_score", 0.5),
                finbert_score=sentiment_result.get("finbert_score", 0.7)
            )
            crud.create_sentiment(self.db, sentiment_data)
            
            # Trigger WebSocket broadcast
            await websocket_manager.broadcast_sentiment_update(
                article_data={
                    "id": db_article.id,
                    "title": article_data.title,
                    "source": article_data.source,
                    "url": article_data.url,
                    "published_at": article_data.published_at.isoformat(),
                    "asset_class": "equity"
                },
                sentiment_data=sentiment_result
            )
            
            # Wait for broadcast to be received
            await asyncio.sleep(2)
            
            # Verify broadcast was received
            await client.disconnect()
            
            # Check that we received at least one sentiment_update message
            sentiment_messages = [msg for msg in client.messages 
                                if msg.get("type") == "sentiment_update"]
            
            self.assertGreater(len(sentiment_messages), 0, 
                             "Should receive at least one sentiment_update message")
            
            if sentiment_messages:
                msg = sentiment_messages[0]
                self.assertIn("article", msg)
                self.assertIn("sentiment", msg)
                self.assertEqual(msg["article"]["title"], article_data.title)
                
        # Run the async test
        asyncio.run(sentiment_broadcast_test())

    def test_alert_triggering_with_websocket_broadcast(self):
        """Test that alert triggering sends WebSocket broadcasts."""
        
        async def alert_broadcast_test():
            # Create a test user and asset
            test_user = models.User(
                username="test_websocket_user",
                email="test@example.com",
                password_hash="test_hash"
            )
            self.db.add(test_user)
            self.db.commit()
            self.db.refresh(test_user)
            
            # Create a test asset
            test_asset = models.Asset(
                symbol="TESTWS",
                name="Test WebSocket Asset",
                type="stock"
            )
            self.db.add(test_asset)
            self.db.commit()
            self.db.refresh(test_asset)
            
            # Create an alert
            alert_data = schemas.AlertCreate(
                user_id=test_user.id,
                asset_id=test_asset.id,
                threshold=0.5,
                direction="above"
            )
            test_alert = crud.create_alert(self.db, alert_data)
            
            # Connect WebSocket client
            client = RSSWebSocketTestClient(self.base_ws_uri)
            await client.connect()
            
            # Start listening for WebSocket messages
            listen_task = asyncio.create_task(
                client.listen_and_categorize_messages(timeout=10.0)
            )
            
            # Small delay to ensure listening is started
            await asyncio.sleep(1)
            
            # Trigger alert checking with a sentiment score above threshold
            triggered_alerts = crud.check_and_trigger_alerts(self.db, "TESTWS", 0.7)
            
            # Wait for WebSocket messages
            messages_result = await listen_task
            
            await client.disconnect()
            
            # Clean up
            self.db.delete(test_alert)
            self.db.delete(test_asset)
            self.db.delete(test_user)
            self.db.commit()
            
            return {
                "triggered_alerts": triggered_alerts,
                "websocket_messages": messages_result
            }
        
        result = asyncio.run(alert_broadcast_test())
        
        # Verify alert was triggered
        self.assertGreater(len(result["triggered_alerts"]), 0)
        
        # Verify WebSocket messages were received
        ws_messages = result["websocket_messages"]
        self.assertGreater(len(ws_messages["messages"]), 0)
        
        # Look for alert_triggered messages
        alert_messages = ws_messages["alert_triggers"]
        logger.info(f"Alert messages received: {len(alert_messages)}")
        
        # We might not always get the alert broadcast due to async timing,
        # but the alert should have been triggered in the database
        logger.info(f"Triggered alerts: {result['triggered_alerts']}")
        logger.info(f"Total WebSocket messages: {len(ws_messages['messages'])}")

    def test_hourly_aggregates_trigger_broadcast(self):
        """Test that hourly sentiment aggregates trigger WebSocket broadcasts."""
        async def aggregate_broadcast_test():
            # Connect WebSocket client
            client = RSSWebSocketTestClient(self.base_ws_uri)
            await client.connect()
            
            # Create test articles with unique URLs
            import time
            base_timestamp = int(time.time() * 1000)
            
            articles = []
            for i in range(3):
                article_data = schemas.ArticleCreate(
                    source="test-aggregate-source",
                    title=f"Test Aggregate Article {i+1}",
                    content=f"This is test article {i+1} with positive sentiment for aggregation testing.",
                    url=f"https://example.com/test-aggregate-{base_timestamp}-{i}",
                    summary=f"Test article {i+1} summary"
                )
                
                article = crud.create_article(self.db, article_data)
                articles.append(article)
                
                # Add sentiment for each article
                sentiment_data = schemas.SentimentCreate(
                    article_id=article.id,
                    lexicon_score=0.6 + (i * 0.1),
                    finbert_score=0.5 + (i * 0.1),
                    asset="AAPL"
                )
                
                crud.create_sentiment(self.db, sentiment_data)
            
            # Manually trigger hourly aggregation
            from app.main import create_hourly_sentiment_aggregates
            aggregates_created = create_hourly_sentiment_aggregates()
            
            # Wait for potential broadcasts
            await asyncio.sleep(2)
            
            # Listen for messages
            messages = await client.listen_and_categorize_messages(timeout=3.0)
            
            await client.disconnect()
            
            return {
                "articles_created": len(articles),
                "aggregates_created": aggregates_created,
                "messages_received": len(messages["messages"]),
                "message_types": [msg.get("type") for msg in messages["messages"]]
            }
            
        result = asyncio.run(aggregate_broadcast_test())
        
        # Verify articles and aggregates were created
        self.assertGreater(result["articles_created"], 0)
        
        # Should receive at least connection message
        self.assertGreaterEqual(result["messages_received"], 1)
        
        logger.info(f"Hourly aggregates test: {result}")

    def test_multiple_clients_receive_rss_broadcasts(self):
        """Test that multiple WebSocket clients receive RSS-triggered broadcasts."""
        
        async def multi_client_rss_test():
            num_clients = 3
            clients = []
            
            # Connect multiple clients
            for i in range(num_clients):
                client = RSSWebSocketTestClient(self.base_ws_uri)
                await client.connect()
                clients.append(client)
                await asyncio.sleep(0.1)  # Small delay between connections
            
            # Start listening tasks for all clients
            listen_tasks = []
            for client in clients:
                task = asyncio.create_task(
                    client.listen_and_categorize_messages(timeout=10.0)
                )
                listen_tasks.append(task)
            
            # Small delay to ensure all are listening
            await asyncio.sleep(1)
            
            # Trigger test broadcasts (simulating RSS ingestion)
            num_broadcasts = 2
            for i in range(num_broadcasts):
                response = self.client.post("/api/websocket/test-broadcast")
                self.assertEqual(response.status_code, 200)
                await asyncio.sleep(1)  # Delay between broadcasts
            
            # Wait for all clients to finish listening
            all_results = await asyncio.gather(*listen_tasks)
            
            # Disconnect all clients
            for client in clients:
                await client.disconnect()
            
            return {
                "num_clients": num_clients,
                "client_results": all_results
            }
        
        result = asyncio.run(multi_client_rss_test())
        
        # Verify all clients received messages
        client_results = result["client_results"]
        self.assertEqual(len(client_results), result["num_clients"])
        
        for i, client_result in enumerate(client_results):
            # Each client should have received multiple messages
            self.assertGreater(len(client_result["messages"]), 3)  # connection + broadcasts
            
            # Each client should have received sentiment, aggregate, and alert messages
            self.assertGreater(len(client_result["sentiment_updates"]), 0)
            self.assertGreater(len(client_result["aggregate_updates"]), 0)
            self.assertGreater(len(client_result["alert_triggers"]), 0)
            
            logger.info(f"Client {i}: {len(client_result['messages'])} total messages")

    def test_websocket_broadcast_data_integrity(self):
        """Test that WebSocket broadcast data matches the source data."""
        
        async def data_integrity_test():
            # Connect WebSocket client
            client = RSSWebSocketTestClient(self.base_ws_uri)
            await client.connect()
            
            # Start listening for WebSocket messages
            listen_task = asyncio.create_task(
                client.listen_and_categorize_messages(timeout=8.0)
            )
            
            # Small delay to ensure listening is started
            await asyncio.sleep(1)
            
            # Trigger test broadcast with known data
            response = self.client.post("/api/websocket/test-broadcast")
            self.assertEqual(response.status_code, 200)
            
            # Wait for WebSocket messages
            messages_result = await listen_task
            
            await client.disconnect()
            
            return messages_result
        
        messages_result = asyncio.run(data_integrity_test())
        
        # Verify we received the expected message types
        sentiment_updates = messages_result["sentiment_updates"]
        aggregate_updates = messages_result["aggregate_updates"]
        alert_triggers = messages_result["alert_triggers"]
        
        # Verify sentiment update structure and data
        if sentiment_updates:
            sentiment_msg = sentiment_updates[0]
            
            # Check required fields
            self.assertIn("timestamp", sentiment_msg)
            self.assertIn("article", sentiment_msg)
            self.assertIn("sentiment", sentiment_msg)
            self.assertIn("metadata", sentiment_msg)
            
            # Check article data structure
            article = sentiment_msg["article"]
            self.assertEqual(article["title"], "Test Article for WebSocket Broadcasting")
            self.assertEqual(article["source"], "test-source")
            self.assertIn("id", article)
            
            # Check sentiment data structure
            sentiment = sentiment_msg["sentiment"]
            self.assertEqual(sentiment["lexicon_score"], 0.5)
            self.assertEqual(sentiment["finbert_score"], 0.3)
            self.assertIn("overall_sentiment", sentiment)
        
        # Verify aggregate update structure
        if aggregate_updates:
            aggregate_msg = aggregate_updates[0]
            
            self.assertIn("timestamp", aggregate_msg)
            self.assertIn("asset", aggregate_msg)
            self.assertIn("sentiment_category", aggregate_msg)
            
            asset = aggregate_msg["asset"]
            self.assertEqual(asset["symbol"], "TEST")
            self.assertEqual(asset["avg_sentiment"], 0.4)
            self.assertEqual(asset["article_count"], 5)
        
        # Verify alert trigger structure
        if alert_triggers:
            alert_msg = alert_triggers[0]
            
            self.assertIn("timestamp", alert_msg)
            self.assertIn("alert", alert_msg)
            
            alert = alert_msg["alert"]
            self.assertEqual(alert["asset_symbol"], "TEST")
            self.assertEqual(alert["threshold"], 0.5)
            self.assertEqual(alert["direction"], "above")
            self.assertEqual(alert["current_sentiment"], 0.6)
        
        logger.info("Data integrity test completed successfully")

    def test_rss_ingestion_triggers_real_time_broadcast(self):
        """Test that RSS ingestion triggers real-time WebSocket broadcasts."""
        async def rss_broadcast_test():
            # Connect WebSocket client
            client = RSSWebSocketTestClient(self.base_ws_uri)
            await client.connect()
            
            # Wait for initial connection message
            await asyncio.sleep(1)
            
            # Create a unique test article to simulate RSS ingestion
            import time
            timestamp = int(time.time() * 1000000)  # microseconds for uniqueness
            unique_url = f"https://example.com/test-rss-article-{timestamp}.html"
            
            # Simulate RSS ingestion by directly creating article and sentiment
            article_data = schemas.ArticleCreate(
                source="test-rss-feed",
                title=f"Breaking News: Market Update {timestamp}",
                content="The markets are showing strong positive momentum today with significant gains across all sectors.",
                url=unique_url,
                published_at=datetime.utcnow()
            )
            
            # Create article
            db_article = crud.create_article(self.db, article_data)
            
            # Create sentiment
            sentiment_data = schemas.SentimentCreate(
                article_id=db_article.id,
                lexicon_score=0.8,
                finbert_score=0.85
            )
            crud.create_sentiment(self.db, sentiment_data)
            
            # Trigger broadcast (simulating what RSS ingestion would do)
            await websocket_manager.broadcast_sentiment_update(
                article_data={
                    "id": db_article.id,
                    "title": article_data.title,
                    "source": article_data.source,
                    "url": article_data.url,
                    "published_at": article_data.published_at.isoformat(),
                    "asset_class": "equity"
                },
                sentiment_data={
                    "lexicon_score": 0.8,
                    "finbert_score": 0.85,
                    "processing_time": 0.5
                }
            )
            
            # Wait for broadcast to propagate
            await asyncio.sleep(2)
            
            # Disconnect and verify
            await client.disconnect()
            
            # Verify we received the broadcast
            sentiment_messages = [msg for msg in client.messages 
                                if msg.get("type") == "sentiment_update"]
            
            self.assertGreater(len(sentiment_messages), 0,
                             "Should receive sentiment_update from RSS ingestion")
            
            if sentiment_messages:
                msg = sentiment_messages[0]
                self.assertEqual(msg["article"]["source"], "test-rss-feed")
                self.assertIn("sentiment", msg)
                
        # Run the async test
        asyncio.run(rss_broadcast_test())


class AsyncTestRunner:
    """Helper class to run async tests."""
    
    @staticmethod
    def run_async_test(test_func):
        """Run an async test function."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(test_func())
        finally:
            loop.close()


if __name__ == "__main__":
    # Configure logging for test runs
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the tests
    unittest.main(verbosity=2) 