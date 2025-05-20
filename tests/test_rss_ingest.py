"""
Test module for RSS ingestion functionality.
"""
import datetime
import hashlib
import unittest
from unittest.mock import MagicMock, call, patch

import feedparser

from app import rss_ingest
from app.rss_feeds import ALL_FEEDS


class TestRssIngest(unittest.TestCase):
    """Test cases for the RSS ingestion module."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_url = "https://example.com/feed.xml"

        # Create a mock feed entry that has both 'title' and 'link' attributes
        # for compatibility with validate_feed function
        mock_entry = MagicMock()
        mock_entry.title = "Test Article"
        mock_entry.link = "https://example.com/article"
        mock_entry.summary = "This is a test article."
        mock_entry.published_parsed = (2023, 7, 15, 12, 30, 0, 5, 196, 0)

        # Create a mock feedparser result
        self.mock_feed = MagicMock()
        self.mock_feed.bozo = False
        self.mock_feed.entries = [mock_entry]

        # Create a datetime for testing
        self.test_datetime = datetime.datetime(2023, 7, 15, 12, 30, 0)

    @patch("app.rss_ingest.feedparser.parse")
    def test_validate_feed_valid(self, mock_parse):
        """Test that validate_feed returns True for a valid feed."""
        # Configure mock with proper attributes
        mock_entry = MagicMock()
        mock_entry.title = "Test Article"
        mock_entry.link = "https://example.com/article"

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [mock_entry]

        mock_parse.return_value = mock_feed

        # Call the function
        is_valid, message = rss_ingest.validate_feed(self.test_url)

        # Check the result
        self.assertTrue(is_valid)
        self.assertEqual(message, "Feed is valid")
        mock_parse.assert_called_once_with(self.test_url)

    @patch("app.rss_ingest.feedparser.parse")
    def test_validate_feed_invalid_xml(self, mock_parse):
        """Test that validate_feed returns False for invalid XML."""
        # Configure mock with bozo exception
        mock_feed = MagicMock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = "XML parsing error"
        mock_parse.return_value = mock_feed

        # Call the function
        is_valid, message = rss_ingest.validate_feed(self.test_url)

        # Check the result
        self.assertFalse(is_valid)
        self.assertTrue("invalid XML" in message)
        mock_parse.assert_called_once_with(self.test_url)

    @patch("app.rss_ingest.feedparser.parse")
    def test_validate_feed_no_entries(self, mock_parse):
        """Test that validate_feed returns False for feeds with no entries."""
        # Configure mock with no entries
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = []
        mock_parse.return_value = mock_feed

        # Call the function
        is_valid, message = rss_ingest.validate_feed(self.test_url)

        # Check the result
        self.assertFalse(is_valid)
        self.assertEqual(message, "Feed has no entries")
        mock_parse.assert_called_once_with(self.test_url)

    @patch("app.rss_ingest.feedparser.parse")
    def test_validate_feed_missing_fields(self, mock_parse):
        """Test that validate_feed returns False for feeds with missing fields."""

        # Create an entry that only has a title but no link
        class EntryMissingLink:
            def __init__(self):
                self.title = "Test Article"
                # No 'link' attribute

        # Configure mock with entry missing link
        mock_entry = EntryMissingLink()

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [mock_entry]
        mock_parse.return_value = mock_feed

        # Call the function
        is_valid, message = rss_ingest.validate_feed(self.test_url)

        # Check the result
        self.assertFalse(is_valid)
        self.assertTrue("missing required fields" in message)
        self.assertTrue("link" in message)
        mock_parse.assert_called_once_with(self.test_url)

    @patch("app.rss_ingest.feedparser.parse")
    def test_parse_rss_feed(self, mock_parse):
        """Test the RSS feed parsing function."""
        # Configure mock with properly structured entry that will be converted to a dict
        mock_entry = MagicMock()
        mock_entry.title = "Test Article"
        mock_entry.link = "https://example.com/article"
        mock_entry.summary = "This is a test article."

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [mock_entry]

        mock_parse.return_value = mock_feed

        # Call the function
        result = rss_ingest.parse_rss_feed(self.test_url)

        # Check the result
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Test Article")
        self.assertEqual(result[0]["link"], "https://example.com/article")
        mock_parse.assert_called_once_with(self.test_url)

    @patch("app.rss_ingest.feedparser.parse")
    def test_parse_rss_feed_with_error(self, mock_parse):
        """Test error handling in parse_rss_feed."""
        # Configure mock with bozo exception
        mock_feed = MagicMock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = "XML parsing error"
        mock_parse.return_value = mock_feed

        # Call the function
        result = rss_ingest.parse_rss_feed(self.test_url)

        # Check the result
        self.assertEqual(result, [])
        mock_parse.assert_called_once_with(self.test_url)

    @patch("app.rss_ingest.download_article")
    def test_extract_article_content(self, mock_download_article):
        """Test the article content extraction function."""
        # Mock the newspaper article
        mock_article = MagicMock()
        mock_article.text = "This is the article content."
        mock_article.authors = ["Author 1", "Author 2"]
        mock_article.publish_date = self.test_datetime
        mock_article.top_image = "https://example.com/image.jpg"
        mock_article.keywords = ["keyword1", "keyword2"]
        mock_article.summary = "This is a summary of the article."

        # Configure the mock to return our mocked article
        mock_download_article.return_value = mock_article

        # Call the function - pass an empty rss_summary
        result = rss_ingest.extract_article_content("https://example.com/article", "")

        # Check the result
        self.assertEqual(result["text"], "This is the article content.")
        self.assertEqual(result["authors"], ["Author 1", "Author 2"])
        self.assertEqual(result["publish_date"], self.test_datetime)
        self.assertEqual(result["top_image"], "https://example.com/image.jpg")

        # Either the article's NLP summary or its text will be used, depending on
        # whether NLP processing succeeded
        self.assertTrue(
            result["summary"] == "This is a summary of the article."
            or result["summary"] == "This is the article content."
        )

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

    def test_calculate_content_hash(self):
        """Test the content hash calculation function."""
        # Test data
        content = "This is test content."
        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Call the function
        result = rss_ingest.calculate_content_hash(content)

        # Check the result
        self.assertEqual(result, expected_hash)

    @patch("app.rss_ingest.parse_rss_feed")
    @patch("app.rss_ingest.extract_article_content")
    @patch("app.crud.get_article_by_url")
    @patch("app.crud.create_article")
    def test_ingest_feed(
        self,
        mock_create_article,
        mock_get_article,
        mock_extract_content,
        mock_parse_feed,
    ):
        """Test the feed ingestion function."""
        # Mock database session
        mock_db = MagicMock()

        # Configure mocks
        mock_parse_feed.return_value = [
            {
                "title": "Test Article",
                "link": "https://example.com/article",
                "published_at": self.test_datetime,
                "source": self.test_url,
                "summary": "This is a test article.",
            }
        ]
        mock_get_article.return_value = None  # Article doesn't exist yet

        # Mock article extraction results
        mock_extract_content.return_value = {
            "text": "This is the article content.",
            "authors": ["Author 1", "Author 2"],
            "publish_date": self.test_datetime,
            "top_image": "https://example.com/image.jpg",
            "keywords": ["keyword1", "keyword2"],
            "summary": "This is a summary of the article.",
            "error": None,
        }

        mock_article = MagicMock()
        mock_article.title = "Test Article"
        mock_create_article.return_value = mock_article

        # Call the function
        entries, articles, errors = rss_ingest.ingest_feed(mock_db, self.test_url)

        # Check the result
        self.assertEqual(entries, 1)
        self.assertEqual(articles, 1)
        self.assertEqual(errors, 0)
        mock_parse_feed.assert_called_once_with(self.test_url)
        mock_get_article.assert_called_once_with(mock_db, "https://example.com/article")
        mock_extract_content.assert_called_once_with(
            "https://example.com/article", "This is a test article."
        )
        mock_create_article.assert_called_once()

    @patch("app.rss_ingest.parse_rss_feed")
    @patch("app.rss_ingest.extract_article_content")
    @patch("app.crud.get_article_by_url")
    @patch("app.crud.create_article")
    def test_ingest_feed_extraction_error(
        self,
        mock_create_article,
        mock_get_article,
        mock_extract_content,
        mock_parse_feed,
    ):
        """Test that ingest_feed handles article extraction errors."""
        # Mock database session
        mock_db = MagicMock()

        # Configure mocks
        mock_parse_feed.return_value = [
            {
                "title": "Test Article",
                "link": "https://example.com/article",
                "published_at": self.test_datetime,
                "source": self.test_url,
                "summary": "This is a test article.",
            }
        ]
        mock_get_article.return_value = None  # Article doesn't exist yet

        # Mock extraction error
        mock_extract_content.return_value = {
            "text": "",
            "authors": [],
            "publish_date": None,
            "top_image": "",
            "keywords": [],
            "summary": "",
            "error": "Download error",
        }

        # Call the function
        entries, articles, errors = rss_ingest.ingest_feed(mock_db, self.test_url)

        # Check the result
        self.assertEqual(entries, 1)
        self.assertEqual(articles, 0)  # No articles created
        self.assertEqual(errors, 1)  # One error recorded
        mock_parse_feed.assert_called_once_with(self.test_url)
        mock_get_article.assert_called_once_with(mock_db, "https://example.com/article")
        mock_extract_content.assert_called_once_with(
            "https://example.com/article", "This is a test article."
        )
        mock_create_article.assert_not_called()

    @patch("app.rss_ingest.parse_rss_feed")
    @patch("app.rss_ingest.extract_article_content")
    @patch("app.crud.get_article_by_url")
    @patch("app.crud.create_article")
    def test_ingest_feed_existing_article(
        self,
        mock_create_article,
        mock_get_article,
        mock_extract_content,
        mock_parse_feed,
    ):
        """Test that ingest_feed skips existing articles."""
        # Mock database session
        mock_db = MagicMock()

        # Configure mocks
        mock_parse_feed.return_value = [
            {
                "title": "Test Article",
                "link": "https://example.com/article",
                "published_at": self.test_datetime,
                "source": self.test_url,
                "summary": "This is a test article.",
            }
        ]
        # Article already exists
        mock_get_article.return_value = MagicMock()

        # Call the function
        entries, articles, errors = rss_ingest.ingest_feed(mock_db, self.test_url)

        # Check the result
        self.assertEqual(entries, 1)
        self.assertEqual(articles, 0)  # No articles created
        self.assertEqual(errors, 0)
        mock_parse_feed.assert_called_once_with(self.test_url)
        mock_get_article.assert_called_once_with(mock_db, "https://example.com/article")
        mock_extract_content.assert_not_called()
        mock_create_article.assert_not_called()

    @patch("app.rss_ingest.validate_feed")
    @patch("app.rss_ingest.ingest_feed")
    def test_ingest_all_feeds(self, mock_ingest_feed, mock_validate_feed):
        """Test the all feeds ingestion function."""
        # Mock database session
        mock_db = MagicMock()

        # Configure mocks
        mock_validate_feed.return_value = (True, "Feed is valid")
        mock_ingest_feed.return_value = (5, 3, 0)  # 5 entries, 3 created, 0 errors

        # Call the function
        result = rss_ingest.ingest_all_feeds(mock_db)

        # Check the result
        self.assertEqual(result["total_feeds_processed"], len(ALL_FEEDS))
        self.assertEqual(result["feeds_with_errors"], 0)
        self.assertEqual(result["total_entries_processed"], 5 * len(ALL_FEEDS))
        self.assertEqual(result["articles_created"], 3 * len(ALL_FEEDS))
        self.assertEqual(result["errors"], 0)
        self.assertTrue("processing_time_seconds" in result)

        # Check each feed was validated and ingested
        self.assertEqual(mock_validate_feed.call_count, len(ALL_FEEDS))
        self.assertEqual(mock_ingest_feed.call_count, len(ALL_FEEDS))

        # Check the first call used the first feed URL
        first_feed = ALL_FEEDS[0]
        mock_validate_feed.assert_has_calls([call(first_feed)], any_order=True)
        mock_ingest_feed.assert_has_calls([call(mock_db, first_feed)], any_order=True)


if __name__ == "__main__":
    unittest.main()
