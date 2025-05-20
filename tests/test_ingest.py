import os
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app import rss_ingest
from app.main import app
from app.rss_feeds import ALL_FEEDS


class TestIngestion(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Use the first feed from ALL_FEEDS as the default test source
        self.default_rss_source = (
            ALL_FEEDS[0] if ALL_FEEDS else "https://finance.yahoo.com/news/rssindex"
        )

    def test_health_endpoint(self):
        """Test that the health endpoint returns the expected response."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_get_rss_sources(self):
        """Test that the RSS sources endpoint returns the expected sources."""
        response = self.client.get("/ingestion/sources")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.json()) > 0)
        # Check that the first item has a url field that matches our first feed
        self.assertEqual(response.json()[0]["url"], ALL_FEEDS[0])

    @patch("app.rss_ingest.feedparser.parse")
    def test_parse_rss_feed(self, mock_parse):
        """Test the RSS feed parsing function."""
        # Mock the feedparser response
        mock_entry = MagicMock()
        mock_entry.title = "Test Article"
        mock_entry.link = "https://example.com/article"

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [mock_entry]
        mock_parse.return_value = mock_feed

        # Call the function
        result = rss_ingest.parse_rss_feed(self.default_rss_source)

        # Check the result
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Test Article")
        mock_parse.assert_called_once_with(self.default_rss_source)

    @patch("app.rss_ingest.download_article")
    def test_extract_article_content(self, mock_download_article):
        """Test the article content extraction function."""
        # Mock the newspaper article
        mock_article = MagicMock()
        mock_article.text = "This is the article content."
        mock_article.authors = ["Author 1", "Author 2"]
        mock_article.publish_date = datetime(2023, 1, 1, 12, 0, 0)
        mock_article.top_image = "https://example.com/image.jpg"
        mock_article.keywords = ["keyword1", "keyword2"]
        mock_article.summary = "This is a summary of the article."
        mock_download_article.return_value = mock_article

        # Call the function
        result = rss_ingest.extract_article_content("https://example.com/article", "")

        # Check the result
        self.assertEqual(result["text"], "This is the article content.")
        self.assertEqual(result["authors"], ["Author 1", "Author 2"])
        self.assertEqual(result["publish_date"], datetime(2023, 1, 1, 12, 0, 0))
        self.assertEqual(result["top_image"], "https://example.com/image.jpg")

        # Either the article's NLP summary or its text will be used as summary
        self.assertTrue(
            result["summary"] == "This is a summary of the article."
            or result["summary"] == "This is the article content."
        )
        self.assertIsNone(result["error"])
        mock_download_article.assert_called_once_with("https://example.com/article")
        mock_article.parse.assert_called_once()
        # We no longer consistently call nlp() since we conditionally call it based on text length

    @patch("app.rss_ingest.download_article")
    def test_extract_article_content_with_error(self, mock_download_article):
        """Test error handling in extract_article_content."""
        # Configure mock to raise exception
        mock_download_article.side_effect = Exception("Download error")

        # Call the function
        result = rss_ingest.extract_article_content("https://example.com/article")

        # Check the result
        self.assertEqual(result["text"], "")
        self.assertEqual(result["authors"], [])
        self.assertIsNone(result["publish_date"])
        self.assertIsNotNone(result["error"])
        mock_download_article.assert_called_once_with("https://example.com/article")

    @patch("app.rss_ingest.validate_feed")
    @patch("app.rss_ingest.ingest_feed")
    def test_ingest_all_feeds_simplified(self, mock_ingest_feed, mock_validate_feed):
        """
        Test that ingest_all_feeds validates and ingests each feed.
        This is a simplified test that avoids mocking the whole chain of dependencies.
        """
        # Configure mocks
        mock_validate_feed.return_value = (True, "Feed is valid")
        mock_ingest_feed.return_value = (5, 3, 0)  # 5 entries, 3 created, 0 errors

        # Mock database session
        mock_db = MagicMock()

        # Call the function
        result = rss_ingest.ingest_all_feeds(mock_db)

        # Verify validate_feed and ingest_feed were called for the first feed
        mock_validate_feed.assert_any_call(self.default_rss_source)
        mock_ingest_feed.assert_any_call(mock_db, self.default_rss_source)

        # Check that we got stats back
        self.assertTrue("total_feeds_processed" in result)
        self.assertTrue("articles_created" in result)


if __name__ == "__main__":
    unittest.main()
