import unittest
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app
from app.routers.ingestion import parse_rss_feed, extract_article_content, ingest_rss_feeds


class TestIngestion(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Use the same default RSS source as in the application
        self.default_rss_source = "https://finance.yahoo.com/news/rssindex"
        # Override environment variable to use our test source if needed
        os.environ["RSS_SOURCES"] = self.default_rss_source

    def test_health_endpoint(self):
        """Test that the health endpoint returns the expected response."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_get_rss_sources(self):
        """Test that the RSS sources endpoint returns the expected sources."""
        response = self.client.get("/ingestion/sources")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [self.default_rss_source])

    @patch('app.routers.ingestion.feedparser.parse')
    def test_parse_rss_feed(self, mock_parse):
        """Test the RSS feed parsing function."""
        # Mock the feedparser response
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [
            {"title": "Test Article", "link": "https://example.com/article"}
        ]
        mock_parse.return_value = mock_feed

        # Call the function
        result = parse_rss_feed(self.default_rss_source)

        # Check the result
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Test Article")
        mock_parse.assert_called_once_with(self.default_rss_source)

    @patch('app.routers.ingestion.NewsArticle')
    def test_extract_article_content(self, mock_news_article):
        """Test the article content extraction function."""
        # Mock the newspaper article
        mock_article = MagicMock()
        mock_article.text = "This is the article content."
        mock_news_article.return_value = mock_article

        # Call the function
        result = extract_article_content("https://example.com/article")

        # Check the result
        self.assertEqual(result, "This is the article content.")
        mock_news_article.assert_called_once_with("https://example.com/article")
        mock_article.download.assert_called_once()
        mock_article.parse.assert_called_once()

    @patch('app.routers.ingestion.parse_rss_feed')
    def test_ingest_rss_feeds_simplified(self, mock_parse):
        """
        Test that ingest_rss_feeds calls parse_rss_feed for each RSS source.
        This is a simplified test that avoids mocking the whole chain of dependencies.
        """
        # Configure mock to return empty list to avoid further processing
        mock_parse.return_value = []
        
        # Call the function
        ingest_rss_feeds()
        
        # Verify parse_rss_feed was called with the expected source
        mock_parse.assert_called_once_with(self.default_rss_source)


if __name__ == "__main__":
    unittest.main()
