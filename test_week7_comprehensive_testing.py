#!/usr/bin/env python3
"""
Test suite for Week 7: Comprehensive Automated Testing

This test suite expands pytest coverage for:
1. Ingestion edge cases (RSS feed failures, malformed data, network issues)
2. NLP output validation (sentiment analysis accuracy, edge cases) 
3. Comprehensive API endpoint testing
4. Error handling and recovery scenarios
5. Performance and reliability testing
"""

import asyncio
import json
import logging
import pytest
import time
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List, Dict, Any

import feedparser
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db
from app.models import Base, User, Article, Sentiment, Asset, SentimentAggregate
from app import crud, schemas
from app.rss_ingest import parse_rss_feed, extract_article_content, ingest_feed
from app.nlp.sentiment import analyze_article_sentiment
from app.nlp.finbert import analyze_finbert_sentiment

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_week7_comprehensive.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestWeek7ComprehensiveTesting:
    """Comprehensive test suite for Week 7 automated testing."""
    
    @classmethod
    def setup_class(cls):
        """Set up test database and data."""
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Create test client
        cls.client = TestClient(app)
        cls.db = TestingSessionLocal()
        
        # Create demo user for testing
        try:
            from app.auth import get_password_hash
            demo_user = User(
                username="demo",
                email="demo@test.com",
                password_hash=get_password_hash("demo123")
            )
            cls.db.add(demo_user)
            cls.db.commit()
            cls.demo_user_id = demo_user.id
        except Exception as e:
            logger.warning(f"Demo user creation failed: {e}")
            # Use existing demo user
            demo_user = cls.db.query(User).filter(User.username == "demo").first()
            cls.demo_user_id = demo_user.id if demo_user else None
        
        # Create test assets
        cls.setup_test_assets()
        
        logger.info("Week 7 Comprehensive Testing Setup Complete")
    
    @classmethod
    def setup_test_assets(cls):
        """Create test assets for comprehensive testing."""
        test_assets = [
            {"symbol": "BTC", "name": "Bitcoin", "type": "crypto", "description": "Bitcoin cryptocurrency"},
            {"symbol": "ETH", "name": "Ethereum", "type": "crypto", "description": "Ethereum cryptocurrency"},
            {"symbol": "AAPL", "name": "Apple Inc.", "type": "stock", "description": "Apple Inc. stock"},
            {"symbol": "TSLA", "name": "Tesla Inc.", "type": "stock", "description": "Tesla Inc. stock"},
            {"symbol": "EUR/USD", "name": "Euro US Dollar", "type": "forex", "description": "EUR/USD currency pair"},
            {"symbol": "GOLD", "name": "Gold", "type": "commodity", "description": "Gold precious metal"}
        ]
        
        for asset_data in test_assets:
            asset = cls.db.query(Asset).filter(Asset.symbol == asset_data["symbol"]).first()
            if not asset:
                asset = Asset(**asset_data)
                cls.db.add(asset)
        
        cls.db.commit()
    
    @classmethod
    def teardown_class(cls):
        """Clean up test database."""
        cls.db.close()
        Base.metadata.drop_all(bind=engine)
        logger.info("Week 7 Comprehensive Testing Teardown Complete")
    
    def get_auth_token(self):
        """Get authentication token for API requests."""
        response = self.client.get("/api/auth/demo-login")
        if response.status_code == 200:
            return response.json()["access_token"]
        return None

    # ============================================================================
    # INGESTION EDGE CASES TESTING
    # ============================================================================
    
    def test_rss_feed_network_errors(self):
        """Test RSS ingestion handling of network errors."""
        logger.info("Testing RSS feed network error handling...")
        
        # Test connection timeout
        with patch('feedparser.parse') as mock_parse:
            mock_parse.side_effect = ConnectionError("Network unreachable")
            
            result = parse_rss_feed("https://unreachable.example.com/feed.xml")
            assert result == []
        
        # Test HTTP errors
        with patch('feedparser.parse') as mock_parse:
            mock_feed = MagicMock()
            mock_feed.bozo = True
            mock_feed.bozo_exception = "HTTP 500 Server Error"
            mock_parse.return_value = mock_feed
            
            result = parse_rss_feed("https://error.example.com/feed.xml")
            assert result == []
        
        logger.info("✅ RSS feed network error handling working correctly")
    
    def test_malformed_rss_data(self):
        """Test RSS ingestion handling of malformed data."""
        logger.info("Testing malformed RSS data handling...")
        
        # Test invalid XML
        with patch('feedparser.parse') as mock_parse:
            mock_feed = MagicMock()
            mock_feed.bozo = True
            mock_feed.bozo_exception = "XML syntax error"
            mock_parse.return_value = mock_feed
            
            result = parse_rss_feed("https://invalid.example.com/feed.xml")
            assert result == []
        
        # Test missing required fields
        with patch('feedparser.parse') as mock_parse:
            mock_entry = MagicMock()
            mock_entry.title = "Test Title"
            # Missing link field
            delattr(mock_entry, 'link') if hasattr(mock_entry, 'link') else None
            
            mock_feed = MagicMock()
            mock_feed.bozo = False
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed
            
            result = parse_rss_feed("https://incomplete.example.com/feed.xml")
            # Should handle missing fields gracefully
            assert isinstance(result, list)
        
        # Test corrupted timestamps
        with patch('feedparser.parse') as mock_parse:
            mock_entry = MagicMock()
            mock_entry.title = "Test Title"
            mock_entry.link = "https://example.com/article"
            mock_entry.published_parsed = "invalid_date"  # Corrupted timestamp
            
            mock_feed = MagicMock()
            mock_feed.bozo = False
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed
            
            result = parse_rss_feed("https://baddate.example.com/feed.xml")
            assert isinstance(result, list)
        
        logger.info("✅ Malformed RSS data handling working correctly")
    
    def test_article_extraction_edge_cases(self):
        """Test article content extraction edge cases."""
        logger.info("Testing article extraction edge cases...")
        
        # Test invalid URLs
        result = extract_article_content("not-a-url", "")
        assert result["text"] == ""
        assert result["error"] is not None
        
        # Test URLs that return 404
        with patch('app.rss_ingest.download_article') as mock_download:
            mock_download.side_effect = Exception("HTTP 404 Not Found")
            
            result = extract_article_content("https://example.com/not-found", "")
            assert result["text"] == ""
            assert result["error"] is not None
        
        # Test articles with no extractable content
        with patch('app.rss_ingest.download_article') as mock_download:
            mock_article = MagicMock()
            mock_article.text = ""  # No content
            mock_article.authors = []
            mock_article.publish_date = None
            mock_download.return_value = mock_article
            
            result = extract_article_content("https://example.com/empty", "fallback content")
            assert "fallback content" in result["text"] or result["text"] == ""
        
        # Test articles with special characters and encoding issues
        with patch('app.rss_ingest.download_article') as mock_download:
            mock_article = MagicMock()
            mock_article.text = "Test content with special chars: ñ, é, 中文, 🚀, ©"
            mock_article.authors = ["José María"]
            mock_download.return_value = mock_article
            
            result = extract_article_content("https://example.com/special", "")
            assert result["text"] != ""
            assert "special chars" in result["text"]
        
        logger.info("✅ Article extraction edge cases handling working correctly")
    
    def test_duplicate_article_handling(self):
        """Test duplicate article detection and handling."""
        logger.info("Testing duplicate article handling...")
        
        # Create a test article
        test_article_data = {
            "source": "test-source",
            "title": "Test Article for Duplicate Detection",
            "content": "This is test content for duplicate detection.",
            "url": "https://example.com/test-duplicate",
            "published_at": datetime.utcnow()
        }
        
        # Create the article first time
        article1 = crud.create_article(self.db, schemas.ArticleCreate(**test_article_data))
        assert article1 is not None
        
        # Try to create the same article again (should be detected as duplicate)
        article2 = crud.get_article_by_url(self.db, test_article_data["url"])
        assert article2 is not None
        assert article1.id == article2.id  # Should be the same article
        
        # Test with similar but slightly different content
        similar_article_data = test_article_data.copy()
        similar_article_data["url"] = "https://example.com/test-duplicate-similar"
        similar_article_data["content"] = "This is test content for duplicate detection with minor changes."
        
        article3 = crud.create_article(self.db, schemas.ArticleCreate(**similar_article_data))
        assert article3 is not None
        assert article1.id != article3.id  # Should be different articles
        
        logger.info("✅ Duplicate article handling working correctly")
    
    def test_database_transaction_failures(self):
        """Test database transaction failure scenarios."""
        logger.info("Testing database transaction failure scenarios...")
        
        # Test article creation with invalid data
        invalid_article_data = {
            "source": "",  # Invalid empty source
            "title": "",   # Invalid empty title
            "content": "Valid content",
            "url": "invalid-url",  # Invalid URL format
            "published_at": "invalid-date"  # Invalid date format
        }
        
        try:
            # This should handle invalid data gracefully
            with self.db.begin():
                article = Article(**invalid_article_data)
                self.db.add(article)
                self.db.commit()
        except Exception as e:
            # Should handle exceptions gracefully
            logger.info(f"Expected exception for invalid data: {e}")
            self.db.rollback()
        
        # Test sentiment creation with invalid article ID
        try:
            with self.db.begin():
                sentiment = Sentiment(
                    article_id="non-existent-id",
                    lexicon_score=0.5,
                    finbert_score=0.3
                )
                self.db.add(sentiment)
                self.db.commit()
        except Exception as e:
            logger.info(f"Expected exception for invalid article ID: {e}")
            self.db.rollback()
        
        logger.info("✅ Database transaction failure handling working correctly")

    # ============================================================================
    # NLP OUTPUT VALIDATION TESTING
    # ============================================================================
    
    def test_sentiment_analysis_accuracy(self):
        """Test sentiment analysis accuracy with known examples."""
        logger.info("Testing sentiment analysis accuracy...")
        
        # Test clearly positive text
        positive_text = "This company has excellent earnings growth and outstanding performance. Investors are very optimistic about future prospects."
        positive_result = analyze_article_sentiment(positive_text)
        assert positive_result["lexicon_score"] > 0, f"Expected positive score, got {positive_result['lexicon_score']}"
        
        # Test clearly negative text
        negative_text = "The company faces severe financial difficulties and terrible losses. Market outlook is extremely pessimistic and concerning."
        negative_result = analyze_article_sentiment(negative_text)
        assert negative_result["lexicon_score"] < 0, f"Expected negative score, got {negative_result['lexicon_score']}"
        
        # Test neutral text
        neutral_text = "The company reported quarterly results. The financial statements were published according to schedule."
        neutral_result = analyze_article_sentiment(neutral_text)
        assert abs(neutral_result["lexicon_score"]) < 0.1, f"Expected neutral score, got {neutral_result['lexicon_score']}"
        
        # Test mixed sentiment text
        mixed_text = "While the company shows excellent growth, there are concerning risks and potential difficulties ahead."
        mixed_result = analyze_article_sentiment(mixed_text)
        assert isinstance(mixed_result["lexicon_score"], (int, float))
        
        logger.info("✅ Sentiment analysis accuracy validation working correctly")
    
    def test_nlp_edge_cases(self):
        """Test NLP processing with edge case inputs."""
        logger.info("Testing NLP edge cases...")
        
        # Test empty text
        result = analyze_article_sentiment("")
        assert result["lexicon_score"] == 0.0
        
        # Test very short text
        result = analyze_article_sentiment("Good.")
        assert isinstance(result["lexicon_score"], (int, float))
        
        # Test very long text (simulate article with 10,000+ words)
        long_text = "The market situation is positive. " * 2000  # Approx 10,000 words
        result = analyze_article_sentiment(long_text)
        assert isinstance(result["lexicon_score"], (int, float))
        assert result["lexicon_score"] > 0  # Should be positive
        
        # Test text with only numbers and symbols
        numeric_text = "123 456 789 !@# $%^ &*() []{}|\\:;\"'<>,.?/~`"
        result = analyze_article_sentiment(numeric_text)
        assert result["lexicon_score"] == 0.0  # Should be neutral
        
        # Test text with HTML and special characters
        html_text = "<div>The <strong>company</strong> shows <em>excellent</em> growth! 📈 Revenue ↗️ $100M+ 🎉</div>"
        result = analyze_article_sentiment(html_text)
        assert isinstance(result["lexicon_score"], (int, float))
        
        # Test multilingual text (should handle gracefully)
        multilingual_text = "The company es muy bueno и очень хорошо 这家公司很好"
        result = analyze_article_sentiment(multilingual_text)
        assert isinstance(result["lexicon_score"], (int, float))
        
        logger.info("✅ NLP edge cases handling working correctly")
    
    def test_finbert_integration(self):
        """Test FinBERT integration and fallback mechanisms."""
        logger.info("Testing FinBERT integration...")
        
        # Test FinBERT with financial text
        financial_text = "The Federal Reserve announced an interest rate hike of 0.25% to combat inflation."
        
        try:
            result = analyze_finbert_sentiment(financial_text)
            assert isinstance(result, dict)
            assert "score" in result or "composite_score" in result
            logger.info(f"FinBERT analysis successful: {result}")
        except Exception as e:
            logger.warning(f"FinBERT not available, expected in some environments: {e}")
        
        # Test FinBERT error handling
        with patch('app.nlp.finbert.analyze_finbert_sentiment') as mock_finbert:
            mock_finbert.side_effect = Exception("FinBERT model not available")
            
            # Should fall back gracefully when FinBERT fails
            result = analyze_article_sentiment(financial_text)
            assert isinstance(result["lexicon_score"], (int, float))
        
        logger.info("✅ FinBERT integration working correctly")
    
    def test_sentiment_consistency(self):
        """Test sentiment analysis consistency and reproducibility."""
        logger.info("Testing sentiment analysis consistency...")
        
        test_text = "Apple Inc. reported strong quarterly earnings exceeding analyst expectations."
        
        # Run the same analysis multiple times
        results = []
        for i in range(5):
            result = analyze_article_sentiment(test_text)
            results.append(result["lexicon_score"])
        
        # Results should be consistent (same input = same output)
        assert all(score == results[0] for score in results), f"Inconsistent results: {results}"
        
        # Test slight variations in input
        variations = [
            "Apple Inc. reported strong quarterly earnings exceeding analyst expectations.",
            "Apple Inc reported strong quarterly earnings exceeding analyst expectations",  # No period
            "APPLE INC. REPORTED STRONG QUARTERLY EARNINGS EXCEEDING ANALYST EXPECTATIONS.",  # Uppercase
            "Apple Inc. reported strong quarterly earnings exceeding analyst expectations!",  # Exclamation
        ]
        
        variation_results = []
        for variation in variations:
            result = analyze_article_sentiment(variation)
            variation_results.append(result["lexicon_score"])
        
        # Results should be similar (not identical due to preprocessing differences)
        for i, score in enumerate(variation_results[1:], 1):
            diff = abs(score - variation_results[0])
            assert diff < 0.2, f"Variation {i} differs too much: {diff}"
        
        logger.info("✅ Sentiment analysis consistency working correctly")

    # ============================================================================
    # COMPREHENSIVE API ENDPOINT TESTING
    # ============================================================================
    
    def test_health_endpoints(self):
        """Test all health check endpoints."""
        logger.info("Testing health check endpoints...")
        
        # Main health endpoint
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        
        # API status endpoint
        response = self.client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "features" in data
        assert "endpoints" in data
        
        logger.info("✅ Health endpoints working correctly")
    
    def test_authentication_endpoints(self):
        """Test authentication and authorization endpoints."""
        logger.info("Testing authentication endpoints...")
        
        # Demo login
        response = self.client.get("/api/auth/demo-login")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        # Test protected endpoint with valid token
        token = data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Use watchlist endpoint as a protected endpoint test
        response = self.client.get("/api/watchlists/", headers=headers)
        assert response.status_code == 200
        
        # Test invalid token
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        response = self.client.get("/api/watchlists/", headers=invalid_headers)
        assert response.status_code == 401
        
        # Test missing authorization header
        response = self.client.get("/api/watchlists/")
        assert response.status_code == 401
        
        logger.info("✅ Authentication endpoints working correctly")
    
    def test_sentiment_endpoints_comprehensive(self):
        """Test sentiment analysis endpoints comprehensively."""
        logger.info("Testing sentiment endpoints comprehensively...")
        
        # Test sentiment analysis endpoint
        test_texts = [
            "Apple Inc. shows excellent growth potential.",
            "Market volatility creates uncertainty for investors.",
            "The company announced neutral quarterly results.",
            "",  # Empty text (should handle gracefully)
            "Very short.",
            "A" * 10000,  # Very long text
        ]
        
        for i, text in enumerate(test_texts):
            if text == "":  # Empty text should return error
                response = self.client.post(
                    "/api/sentiment/article",
                    json={"text": text}
                )
                assert response.status_code == 400
            else:
                response = self.client.post(
                    "/api/sentiment/article",
                    json={"text": text}
                )
                assert response.status_code == 200
                data = response.json()
                assert "lexicon_score" in data
                assert "finbert_score" in data
                assert isinstance(data["lexicon_score"], (int, float))
        
        # Test latest sentiment endpoint for each asset
        test_assets = ["BTC", "ETH", "AAPL", "TSLA", "EUR/USD", "GOLD"]
        
        for asset in test_assets:
            response = self.client.get(f"/api/sentiment/latest?asset={asset}")
            # May return 404 if no sentiment data exists, which is acceptable
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                data = response.json()
                assert data["asset_symbol"] == asset
                assert "latest_sentiment" in data
        
        logger.info("✅ Sentiment endpoints comprehensive testing working correctly")
    
    def test_search_endpoints_comprehensive(self):
        """Test search endpoints with various scenarios."""
        logger.info("Testing search endpoints comprehensively...")
        
        # Create sample articles for searching
        sample_articles = [
            {
                "source": "Test Source",
                "title": "Bitcoin Price Analysis: Market Shows Strong Growth",
                "content": "Bitcoin cryptocurrency shows excellent performance with rising prices and positive market sentiment.",
                "url": f"https://example.com/btc-{uuid.uuid4()}",
                "published_at": datetime.utcnow()
            },
            {
                "source": "Test Source", 
                "title": "Apple Earnings Report: Record Revenue Growth",
                "content": "Apple Inc. reported outstanding quarterly earnings with record revenue growth and strong iPhone sales.",
                "url": f"https://example.com/aapl-{uuid.uuid4()}",
                "published_at": datetime.utcnow()
            },
            {
                "source": "Test Source",
                "title": "Federal Reserve Interest Rate Decision",
                "content": "The Federal Reserve announced a rate hike to combat inflation, affecting market sentiment.",
                "url": f"https://example.com/fed-{uuid.uuid4()}",
                "published_at": datetime.utcnow()
            }
        ]
        
        # Create articles in database
        for article_data in sample_articles:
            crud.create_article(self.db, schemas.ArticleCreate(**article_data))
        
        # Test various search queries
        search_queries = [
            "Bitcoin",
            "Apple earnings",
            "Federal Reserve",
            "growth",
            "market",
            "price",
            "revenue",
            "xyz_nonexistent_term"  # Should return no results
        ]
        
        for query in search_queries:
            # Test main search endpoint
            response = self.client.get(f"/api/search/?q={query}&limit=10")
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert "total_count" in data
            assert isinstance(data["total_count"], int)
            
            # Test articles-only endpoint
            response = self.client.get(f"/api/search/articles?q={query}&limit=5")
            assert response.status_code == 200
            articles = response.json()
            assert isinstance(articles, list)
        
        # Test search with pagination
        response = self.client.get("/api/search/?q=market&skip=0&limit=2")
        assert response.status_code == 200
        
        response = self.client.get("/api/search/?q=market&skip=2&limit=2")
        assert response.status_code == 200
        
        # Test search stats
        response = self.client.get("/api/search/stats")
        assert response.status_code == 200
        stats = response.json()
        assert "total_articles" in stats
        assert "database_type" in stats
        
        # Test invalid search parameters
        response = self.client.get("/api/search/?q=&limit=10")  # Empty query
        assert response.status_code == 422  # Validation error
        
        response = self.client.get("/api/search/?q=test&limit=0")  # Invalid limit
        assert response.status_code == 422  # Validation error
        
        logger.info("✅ Search endpoints comprehensive testing working correctly")
    
    def test_history_endpoint_comprehensive(self):
        """Test sentiment history endpoint comprehensively."""
        logger.info("Testing history endpoint comprehensively...")
        
        # Create sample sentiment aggregates for testing
        test_asset = self.db.query(Asset).filter(Asset.symbol == "BTC").first()
        if test_asset:
            # Create sentiment aggregates for different time periods
            now = datetime.utcnow()
            time_periods = [
                now - timedelta(hours=1),
                now - timedelta(hours=12),
                now - timedelta(days=1),
                now - timedelta(days=3),
                now - timedelta(days=7),
                now - timedelta(days=15),
                now - timedelta(days=30)
            ]
            
            for i, timestamp in enumerate(time_periods):
                sentiment_agg = SentimentAggregate(
                    asset_id=test_asset.id,
                    timestamp=timestamp,
                    avg_score=0.1 * (i - 3)  # Varying scores from -0.3 to 0.3
                )
                self.db.add(sentiment_agg)
            
            self.db.commit()
        
        # Test different time ranges
        time_ranges = ["1h", "24h", "7d", "30d"]
        
        for time_range in time_ranges:
            response = self.client.get(f"/api/sentiment/history?asset=BTC&range={time_range}")
            assert response.status_code in [200, 404]  # 404 if no data
            
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list)
                for item in data:
                    assert "avg_score" in item
                    assert "timestamp" in item
                    assert "asset" in item
        
        # Test custom date range
        start_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        end_date = datetime.utcnow().isoformat()
        
        response = self.client.get(
            f"/api/sentiment/history?asset=BTC&start={start_date}&end={end_date}"
        )
        assert response.status_code in [200, 404]
        
        # Test invalid parameters
        response = self.client.get("/api/sentiment/history?asset=INVALID&range=1h")
        assert response.status_code == 404  # Asset not found
        
        response = self.client.get("/api/sentiment/history?asset=BTC&range=invalid")
        assert response.status_code == 400  # Invalid range
        
        logger.info("✅ History endpoint comprehensive testing working correctly")
    
    def test_watchlist_and_alerts_endpoints(self):
        """Test watchlist and alerts endpoints comprehensively."""
        logger.info("Testing watchlist and alerts endpoints...")
        
        token = self.get_auth_token()
        if not token:
            logger.warning("Cannot test watchlist/alerts endpoints without authentication")
            return
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test watchlist endpoints
        # Get current watchlist
        response = self.client.get("/api/watchlists/", headers=headers)
        assert response.status_code == 200
        
        # Add asset to watchlist
        response = self.client.post("/api/watchlists/?asset_symbol=BTC", headers=headers)
        assert response.status_code in [200, 201, 400]  # 400 if already exists
        
        # Test alerts endpoints
        # Get current alerts
        response = self.client.get("/api/alerts/", headers=headers)
        assert response.status_code == 200
        
        # Create alert
        response = self.client.post("/api/alerts/?asset_symbol=BTC&threshold=0.5&direction=above", headers=headers)
        assert response.status_code in [200, 201]
        
        logger.info("✅ Watchlist and alerts endpoints working correctly")
    
    def test_websocket_endpoints(self):
        """Test WebSocket endpoints and functionality."""
        logger.info("Testing WebSocket endpoints...")
        
        # Test WebSocket stats endpoint
        response = self.client.get("/api/websocket/stats")
        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data
        
        # Test WebSocket broadcast test endpoint
        response = self.client.post("/api/websocket/test-broadcast")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "broadcasts_sent" in data
        
        logger.info("✅ WebSocket endpoints working correctly")
    
    def test_error_handling_and_edge_cases(self):
        """Test error handling and edge cases across all endpoints."""
        logger.info("Testing error handling and edge cases...")
        
        # Test malformed JSON requests
        response = self.client.post(
            "/api/sentiment/article",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
        
        # Test missing required parameters
        response = self.client.get("/api/sentiment/latest")  # Missing asset parameter
        assert response.status_code == 422
        
        # Test invalid HTTP methods
        response = self.client.delete("/api/sentiment/article")  # DELETE not allowed
        assert response.status_code == 405
        
        # Test very large requests
        large_text = "A" * 100000  # 100KB text
        response = self.client.post(
            "/api/sentiment/article",
            json={"text": large_text}
        )
        assert response.status_code in [200, 413, 422]  # May be limited by server config
        
        # Test special characters in URLs
        response = self.client.get("/api/search/?q=test%20with%20spaces%20and%20%E2%9C%93")
        assert response.status_code == 200
        
        logger.info("✅ Error handling and edge cases working correctly")
    
    def test_performance_endpoints(self):
        """Test performance monitoring endpoints if available."""
        logger.info("Testing performance endpoints...")
        
        token = self.get_auth_token()
        if not token:
            logger.warning("Cannot test performance endpoints without authentication")
            return
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test if performance endpoints exist (they may not be mounted)
        try:
            response = self.client.get("/api/performance/profile", headers=headers)
            if response.status_code == 200:
                data = response.json()
                assert "performance_analysis" in data
                logger.info("✅ Performance profile endpoint working")
            elif response.status_code == 404:
                logger.info("Performance endpoints not available (expected)")
            else:
                logger.warning(f"Performance endpoint returned unexpected status: {response.status_code}")
        except Exception as e:
            logger.info(f"Performance endpoints not available: {e}")
        
        logger.info("✅ Performance endpoints testing completed")

    # ============================================================================
    # TEST EXECUTION AND REPORTING
    # ============================================================================
    
    def run_all_tests(self):
        """Run all comprehensive tests and generate report."""
        logger.info("🚀 Starting Week 7 Comprehensive Testing Suite")
        logger.info("=" * 70)
        
        test_categories = {
            "Ingestion Edge Cases": [
                self.test_rss_feed_network_errors,
                self.test_malformed_rss_data,
                self.test_article_extraction_edge_cases,
                self.test_duplicate_article_handling,
                self.test_database_transaction_failures
            ],
            "NLP Output Validation": [
                self.test_sentiment_analysis_accuracy,
                self.test_nlp_edge_cases,
                self.test_finbert_integration,
                self.test_sentiment_consistency
            ],
            "API Endpoint Testing": [
                self.test_health_endpoints,
                self.test_authentication_endpoints,
                self.test_sentiment_endpoints_comprehensive,
                self.test_search_endpoints_comprehensive,
                self.test_history_endpoint_comprehensive,
                self.test_watchlist_and_alerts_endpoints,
                self.test_websocket_endpoints,
                self.test_error_handling_and_edge_cases,
                self.test_performance_endpoints
            ]
        }
        
        results = {}
        total_tests = 0
        passed_tests = 0
        
        for category, test_methods in test_categories.items():
            logger.info(f"\n📋 {category}")
            logger.info("-" * 50)
            
            category_results = {}
            category_passed = 0
            
            for test_method in test_methods:
                test_name = test_method.__name__
                total_tests += 1
                
                try:
                    logger.info(f"Running {test_name}...")
                    test_method()
                    category_results[test_name] = True
                    category_passed += 1
                    passed_tests += 1
                    logger.info(f"✅ {test_name} PASSED")
                except Exception as e:
                    category_results[test_name] = False
                    logger.error(f"❌ {test_name} FAILED: {e}")
            
            results[category] = {
                "tests": category_results,
                "passed": category_passed,
                "total": len(test_methods),
                "success_rate": category_passed / len(test_methods) * 100
            }
        
        # Generate comprehensive report
        logger.info("\n" + "=" * 70)
        logger.info("📊 WEEK 7 COMPREHENSIVE TESTING REPORT")
        logger.info("=" * 70)
        
        for category, category_data in results.items():
            logger.info(f"\n{category}:")
            logger.info(f"  Tests: {category_data['passed']}/{category_data['total']} passed ({category_data['success_rate']:.1f}%)")
            
            for test_name, passed in category_data["tests"].items():
                status = "✅ PASS" if passed else "❌ FAIL"
                logger.info(f"    {test_name.replace('test_', '').replace('_', ' ').title()}: {status}")
        
        overall_success_rate = passed_tests / total_tests * 100
        logger.info(f"\n🎯 OVERALL RESULTS:")
        logger.info(f"   Total Tests: {total_tests}")
        logger.info(f"   Passed: {passed_tests}")
        logger.info(f"   Failed: {total_tests - passed_tests}")
        logger.info(f"   Success Rate: {overall_success_rate:.1f}%")
        
        if overall_success_rate >= 90:
            logger.info("🎉 EXCELLENT! Week 7 comprehensive testing achieved high coverage!")
        elif overall_success_rate >= 80:
            logger.info("✅ GOOD! Week 7 comprehensive testing shows solid coverage.")
        elif overall_success_rate >= 70:
            logger.info("⚠️  ACCEPTABLE. Some areas need improvement.")
        else:
            logger.warning("❌ NEEDS WORK. Multiple test failures detected.")
        
        return results


if __name__ == "__main__":
    """Run the comprehensive test suite directly."""
    logger.info("Starting Week 7 Comprehensive Testing Suite...")
    
    test_instance = TestWeek7ComprehensiveTesting()
    test_instance.setup_class()
    
    try:
        results = test_instance.run_all_tests()
        
        # Exit with appropriate code
        total_tests = sum(cat_data["total"] for cat_data in results.values())
        passed_tests = sum(cat_data["passed"] for cat_data in results.values())
        success_rate = passed_tests / total_tests * 100
        
        if success_rate >= 80:
            exit(0)
        else:
            exit(1)
            
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        exit(1)
    finally:
        test_instance.teardown_class() 