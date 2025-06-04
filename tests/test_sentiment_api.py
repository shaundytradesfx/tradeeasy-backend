"""
Tests for sentiment analysis API endpoints.

This module tests the sentiment analysis endpoints including:
- POST /api/sentiment/article
- GET /api/sentiment/latest
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db, Base
from app.models import Asset, SentimentAggregate


class TestSentimentAPI(unittest.TestCase):
    """Test cases for sentiment analysis API endpoints."""

    def setUp(self):
        """Set up test client and database."""
        self.client = TestClient(app)
        
        # Create in-memory SQLite database for testing
        self.engine = create_engine(
            "sqlite:///./test_sentiment.db", 
            connect_args={"check_same_thread": False}
        )
        TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
        
        # Override the get_db dependency
        def override_get_db():
            try:
                db = TestingSessionLocal()
                yield db
            finally:
                db.close()
        
        app.dependency_overrides[get_db] = override_get_db
        
        # Create test data
        self.setup_test_data()

    def tearDown(self):
        """Clean up after tests."""
        # Remove dependency override
        app.dependency_overrides.clear()
        
        # Drop all tables
        Base.metadata.drop_all(bind=self.engine)

    def setup_test_data(self):
        """Create test assets and sentiment data."""
        # Use the overridden database session
        db = next(app.dependency_overrides[get_db]())
        
        # Create test assets
        self.btc_asset = Asset(
            id=uuid.uuid4(),
            symbol="BTC",
            name="Bitcoin",
            type="crypto",
            description="Bitcoin cryptocurrency"
        )
        
        self.aapl_asset = Asset(
            id=uuid.uuid4(),
            symbol="AAPL",
            name="Apple Inc.",
            type="stock",
            description="Apple Inc. stock"
        )
        
        db.add(self.btc_asset)
        db.add(self.aapl_asset)
        db.commit()
        
        # Store the IDs for later use
        self.btc_asset_id = self.btc_asset.id
        self.aapl_asset_id = self.aapl_asset.id
        
        # Create test sentiment aggregates
        self.btc_sentiment = SentimentAggregate(
            id=uuid.uuid4(),
            asset_id=self.btc_asset_id,
            timestamp=datetime(2024, 1, 15, 12, 0, 0),
            avg_score=0.25
        )
        
        self.aapl_sentiment = SentimentAggregate(
            id=uuid.uuid4(),
            asset_id=self.aapl_asset_id,
            timestamp=datetime(2024, 1, 15, 10, 0, 0),
            avg_score=-0.15
        )
        
        db.add(self.btc_sentiment)
        db.add(self.aapl_sentiment)
        db.commit()
        db.close()

    @patch('app.routers.sentiment.analyze_finbert_sentiment')
    @patch('app.routers.sentiment.calculate_lexicon_score')
    def test_analyze_article_sentiment_success(self, mock_lexicon, mock_finbert):
        """Test successful sentiment analysis of article text."""
        # Mock the sentiment analysis functions
        mock_lexicon.return_value = 0.15
        mock_finbert.return_value = {"score": 0.22}
        
        # Test data
        test_text = "Apple Inc. reported strong quarterly earnings with revenue growth."
        
        # Make request
        response = self.client.post(
            "/api/sentiment/article",
            json={"text": test_text}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("lexicon_score", data)
        self.assertIn("finbert_score", data)
        self.assertEqual(data["lexicon_score"], 0.15)
        self.assertEqual(data["finbert_score"], 0.22)
        
        # Verify mocks were called
        mock_lexicon.assert_called_once_with(test_text)
        mock_finbert.assert_called_once_with(test_text)

    def test_analyze_article_sentiment_empty_text(self):
        """Test sentiment analysis with empty text input."""
        # Test with empty string
        response = self.client.post(
            "/api/sentiment/article",
            json={"text": ""}
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("Text input cannot be empty", response.json()["detail"])
        
        # Test with whitespace only
        response = self.client.post(
            "/api/sentiment/article",
            json={"text": "   "}
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("Text input cannot be empty", response.json()["detail"])

    def test_analyze_article_sentiment_invalid_json(self):
        """Test sentiment analysis with invalid JSON."""
        response = self.client.post(
            "/api/sentiment/article",
            json={"wrong_field": "some text"}
        )
        
        self.assertEqual(response.status_code, 422)  # Validation error

    @patch('app.routers.sentiment.calculate_lexicon_score')
    def test_analyze_article_sentiment_lexicon_error(self, mock_lexicon):
        """Test sentiment analysis when lexicon analysis fails."""
        # Mock lexicon to raise exception
        mock_lexicon.side_effect = Exception("Lexicon analysis failed")
        
        response = self.client.post(
            "/api/sentiment/article",
            json={"text": "Test text"}
        )
        
        self.assertEqual(response.status_code, 500)
        self.assertIn("Error analyzing sentiment", response.json()["detail"])

    @patch('app.routers.sentiment.analyze_finbert_sentiment')
    @patch('app.routers.sentiment.calculate_lexicon_score')
    def test_analyze_article_sentiment_finbert_error(self, mock_lexicon, mock_finbert):
        """Test sentiment analysis when FinBERT analysis fails."""
        # Mock successful lexicon but failed FinBERT
        mock_lexicon.return_value = 0.1
        mock_finbert.side_effect = Exception("FinBERT analysis failed")
        
        response = self.client.post(
            "/api/sentiment/article",
            json={"text": "Test text"}
        )
        
        self.assertEqual(response.status_code, 500)
        self.assertIn("Error analyzing sentiment", response.json()["detail"])

    def test_get_latest_sentiment_success(self):
        """Test successful retrieval of latest sentiment for an asset."""
        response = self.client.get("/api/sentiment/latest?asset=BTC")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check response structure
        self.assertIn("asset_symbol", data)
        self.assertIn("asset_name", data)
        self.assertIn("asset_type", data)
        self.assertIn("latest_sentiment", data)
        
        # Check values
        self.assertEqual(data["asset_symbol"], "BTC")
        self.assertEqual(data["asset_name"], "Bitcoin")
        self.assertEqual(data["asset_type"], "crypto")
        
        sentiment = data["latest_sentiment"]
        self.assertIn("id", sentiment)
        self.assertIn("avg_score", sentiment)
        self.assertIn("timestamp", sentiment)
        self.assertEqual(sentiment["avg_score"], 0.25)

    def test_get_latest_sentiment_case_insensitive(self):
        """Test that asset symbol lookup is case insensitive."""
        # Test lowercase
        response = self.client.get("/api/sentiment/latest?asset=btc")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["asset_symbol"], "BTC")
        
        # Test mixed case
        response = self.client.get("/api/sentiment/latest?asset=aapl")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["asset_symbol"], "AAPL")

    def test_get_latest_sentiment_asset_not_found(self):
        """Test retrieval of sentiment for non-existent asset."""
        response = self.client.get("/api/sentiment/latest?asset=NONEXISTENT")
        
        self.assertEqual(response.status_code, 404)
        self.assertIn("Asset with symbol 'NONEXISTENT' not found", response.json()["detail"])

    def test_get_latest_sentiment_no_data(self):
        """Test retrieval of sentiment for asset with no sentiment data."""
        # Create asset without sentiment data
        db = next(app.dependency_overrides[get_db]())
        
        no_sentiment_asset = Asset(
            id=uuid.uuid4(),
            symbol="NODATA",
            name="No Data Asset",
            type="stock",
            description="Asset with no sentiment data"
        )
        
        db.add(no_sentiment_asset)
        db.commit()
        db.close()
        
        response = self.client.get("/api/sentiment/latest?asset=NODATA")
        
        self.assertEqual(response.status_code, 404)
        self.assertIn("No sentiment data available for asset 'NODATA'", response.json()["detail"])

    def test_get_latest_sentiment_missing_asset_param(self):
        """Test retrieval of sentiment without asset parameter."""
        response = self.client.get("/api/sentiment/latest")
        
        self.assertEqual(response.status_code, 422)  # Validation error

    def test_get_latest_sentiment_multiple_records(self):
        """Test that the latest sentiment record is returned when multiple exist."""
        db = next(app.dependency_overrides[get_db]())
        
        # Add an older sentiment record for BTC
        older_sentiment = SentimentAggregate(
            id=uuid.uuid4(),
            asset_id=self.btc_asset_id,  # Use the stored ID
            timestamp=datetime(2024, 1, 14, 12, 0, 0),  # Earlier date
            avg_score=0.10
        )
        
        # Add a newer sentiment record for BTC
        newer_sentiment = SentimentAggregate(
            id=uuid.uuid4(),
            asset_id=self.btc_asset_id,  # Use the stored ID
            timestamp=datetime(2024, 1, 16, 12, 0, 0),  # Later date
            avg_score=0.35
        )
        
        db.add(older_sentiment)
        db.add(newer_sentiment)
        db.commit()
        db.close()
        
        response = self.client.get("/api/sentiment/latest?asset=BTC")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should return the newest sentiment (0.35, not 0.25 or 0.10)
        self.assertEqual(data["latest_sentiment"]["avg_score"], 0.35)

    @patch('app.routers.sentiment.analyze_finbert_sentiment')
    @patch('app.routers.sentiment.calculate_lexicon_score')
    def test_analyze_article_sentiment_with_special_characters(self, mock_lexicon, mock_finbert):
        """Test sentiment analysis with text containing special characters."""
        mock_lexicon.return_value = 0.05
        mock_finbert.return_value = {"score": -0.12}
        
        # Text with special characters, HTML, and emojis
        test_text = "Apple's Q4 earnings 📈 exceeded expectations! Revenue ↗️ $89.5B vs $88.9B expected. <strong>Strong</strong> performance in iPhone sales."
        
        response = self.client.post(
            "/api/sentiment/article",
            json={"text": test_text}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["lexicon_score"], 0.05)
        self.assertEqual(data["finbert_score"], -0.12)

    def test_api_documentation_endpoints_exist(self):
        """Test that API documentation endpoints are accessible."""
        # Test OpenAPI schema
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        
        openapi_data = response.json()
        
        # Check that our sentiment endpoints are documented
        self.assertIn("/api/sentiment/article", openapi_data["paths"])
        self.assertIn("/api/sentiment/latest", openapi_data["paths"])
        
        # Check that POST method exists for /api/sentiment/article
        self.assertIn("post", openapi_data["paths"]["/api/sentiment/article"])
        
        # Check that GET method exists for /api/sentiment/latest
        self.assertIn("get", openapi_data["paths"]["/api/sentiment/latest"])


if __name__ == "__main__":
    unittest.main() 