"""
Tests for ingestion metrics system.

This module tests the metrics collection, Prometheus integration,
and enhanced error handling for the RSS ingestion system.
"""

import unittest
from unittest.mock import patch, MagicMock
import time
from datetime import datetime

from app.metrics import IngestionMetrics, metrics, get_metrics_summary
from app.rss_ingest import ingest_all_feeds, ingest_feed, validate_feed
from app.database import get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base


class TestIngestionMetrics(unittest.TestCase):
    """Test cases for ingestion metrics tracking."""

    def setUp(self):
        """Set up test metrics instance."""
        self.test_metrics = IngestionMetrics()

    def test_metrics_initialization(self):
        """Test that metrics are properly initialized."""
        self.assertIsNone(self.test_metrics.current_run_start)
        self.assertEqual(self.test_metrics.current_run_stats['feeds_processed'], 0)
        self.assertEqual(self.test_metrics.current_run_stats['total_errors'], 0)

    def test_start_ingestion_run(self):
        """Test starting an ingestion run."""
        self.test_metrics.start_ingestion_run()
        
        self.assertIsNotNone(self.test_metrics.current_run_start)
        self.assertEqual(self.test_metrics.current_run_stats['feeds_processed'], 0)
        self.assertEqual(self.test_metrics.current_run_stats['feeds_with_errors'], 0)

    def test_record_feed_processed(self):
        """Test recording feed processing."""
        self.test_metrics.start_ingestion_run()
        
        # Record successful feed
        self.test_metrics.record_feed_processed('success', 'equities')
        self.assertEqual(self.test_metrics.current_run_stats['feeds_processed'], 1)
        self.assertEqual(self.test_metrics.current_run_stats['feeds_with_errors'], 0)
        
        # Record failed feed
        self.test_metrics.record_feed_processed('error', 'crypto')
        self.assertEqual(self.test_metrics.current_run_stats['feeds_processed'], 2)
        self.assertEqual(self.test_metrics.current_run_stats['feeds_with_errors'], 1)

    def test_record_entries_and_articles(self):
        """Test recording entries and articles."""
        self.test_metrics.start_ingestion_run()
        
        self.test_metrics.record_entries_processed(10, 'forex')
        self.test_metrics.record_articles_created(8, 'forex')
        
        self.assertEqual(self.test_metrics.current_run_stats['total_entries'], 10)
        self.assertEqual(self.test_metrics.current_run_stats['total_articles'], 8)

    def test_record_errors(self):
        """Test error recording and breakdown."""
        self.test_metrics.start_ingestion_run()
        
        self.test_metrics.record_error('parse_error', 'equities')
        self.test_metrics.record_error('timeout', 'crypto')
        self.test_metrics.record_error('parse_error', 'equities')
        
        self.assertEqual(self.test_metrics.current_run_stats['total_errors'], 3)
        self.assertEqual(self.test_metrics.current_run_stats['error_breakdown']['parse_error_equities'], 2)
        self.assertEqual(self.test_metrics.current_run_stats['error_breakdown']['timeout_crypto'], 1)

    def test_record_article_extraction(self):
        """Test article extraction metrics."""
        # This should not raise any exceptions
        self.test_metrics.record_article_extraction(1.5, 2048, 2)

    def test_record_database_operation(self):
        """Test database operation metrics."""
        # This should not raise any exceptions
        self.test_metrics.record_database_operation('create_article', 0.05, 'success')
        self.test_metrics.record_database_operation('check_duplicate', 0.02, 'success')

    def test_finish_ingestion_run(self):
        """Test finishing an ingestion run."""
        self.test_metrics.start_ingestion_run()
        
        # Add some test data
        self.test_metrics.record_feed_processed('success', 'equities')
        self.test_metrics.record_entries_processed(5, 'equities')
        self.test_metrics.record_articles_created(4, 'equities')
        
        # Small delay to ensure duration > 0
        time.sleep(0.1)
        
        stats = self.test_metrics.finish_ingestion_run(10)
        
        self.assertIsNotNone(stats)
        self.assertEqual(stats['feeds_processed'], 1)
        self.assertEqual(stats['total_entries'], 5)
        self.assertEqual(stats['total_articles'], 4)
        self.assertGreater(stats['duration'], 0)

    def test_get_current_stats(self):
        """Test getting current statistics."""
        self.test_metrics.start_ingestion_run()
        
        stats = self.test_metrics.get_current_stats()
        
        self.assertIn('feeds_processed', stats)
        self.assertIn('total_errors', stats)
        self.assertIn('duration', stats)

    def test_finish_without_start(self):
        """Test finishing without starting should log warning."""
        with patch('app.metrics.logger') as mock_logger:
            result = self.test_metrics.finish_ingestion_run(5)
            mock_logger.warning.assert_called_once()
            self.assertIsNone(result)


class TestMetricsIntegration(unittest.TestCase):
    """Test integration of metrics with ingestion system."""

    def setUp(self):
        """Set up test database."""
        # Create in-memory SQLite database for testing
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = TestingSessionLocal()

    def tearDown(self):
        """Clean up test database."""
        self.db.close()

    @patch('app.rss_ingest.ALL_FEEDS', ['http://test-feed.com/rss'])
    @patch('app.rss_ingest.FEED_CATEGORIES', {'http://test-feed.com/rss': 'test'})
    @patch('app.rss_ingest.parse_rss_feed')
    @patch('app.rss_ingest.validate_feed')
    def test_ingest_all_feeds_with_metrics(self, mock_validate, mock_parse):
        """Test that ingest_all_feeds properly records metrics."""
        # Mock successful validation and parsing
        mock_validate.return_value = (True, "Valid feed")
        mock_parse.return_value = [
            {
                'title': 'Test Article',
                'link': 'http://test.com/article1',
                'published_at': datetime.utcnow(),
                'source': 'http://test-feed.com/rss',
                'summary': 'Test summary',
                'asset_class': 'test'
            }
        ]
        
        # Mock article extraction to avoid network calls
        with patch('app.rss_ingest.extract_article_content') as mock_extract:
            mock_extract.return_value = {
                'text': 'Test article content',
                'authors': ['Test Author'],
                'publish_date': datetime.utcnow(),
                'top_image': None,
                'keywords': [],
                'summary': 'Test summary',
                'error': None
            }
            
            # Run ingestion
            stats = ingest_all_feeds(self.db)
            
            # Verify stats structure
            self.assertIn('total_feeds_processed', stats)
            self.assertIn('articles_created', stats)
            self.assertIn('processing_time_seconds', stats)
            self.assertIn('success_rate', stats)
            self.assertIn('feed_results', stats)
            self.assertIn('timestamp', stats)
            
            # Verify at least one feed was processed
            self.assertGreater(stats['total_feeds_processed'], 0)

    def test_validate_feed_metrics(self):
        """Test that feed validation records appropriate metrics."""
        # Test with invalid URL
        with patch('app.rss_ingest.feedparser.parse') as mock_parse:
            mock_feed = MagicMock()
            mock_feed.bozo = True
            mock_feed.bozo_exception = "Invalid XML"
            mock_parse.return_value = mock_feed
            
            is_valid, message = validate_feed('http://invalid-feed.com')
            
            self.assertFalse(is_valid)
            self.assertIn("Invalid XML", message)

    @patch('app.rss_ingest.ALL_FEEDS', ['http://test-feed.com/rss'])
    @patch('app.rss_ingest.FEED_CATEGORIES', {'http://test-feed.com/rss': 'test'})
    def test_ingest_feed_with_errors(self):
        """Test that feed ingestion with errors records metrics properly."""
        with patch('app.rss_ingest.parse_rss_feed') as mock_parse:
            # Mock parsing to return entries but extraction fails
            mock_parse.return_value = [
                {
                    'title': 'Test Article',
                    'link': 'http://test.com/article1',
                    'published_at': datetime.utcnow(),
                    'source': 'http://test-feed.com/rss',
                    'summary': 'Test summary',
                    'asset_class': 'test'
                }
            ]
            
            with patch('app.rss_ingest.extract_article_content') as mock_extract:
                # Mock extraction failure
                mock_extract.return_value = {
                    'text': '',  # Empty text indicates failure
                    'authors': [],
                    'publish_date': None,
                    'top_image': None,
                    'keywords': [],
                    'summary': '',
                    'error': 'Extraction failed'
                }
                
                entries, articles, errors = ingest_feed(self.db, 'http://test-feed.com/rss')
                
                # Should have processed entries but created no articles due to extraction failure
                self.assertGreater(entries, 0)
                self.assertEqual(articles, 0)
                self.assertGreater(errors, 0)


class TestPrometheusMetrics(unittest.TestCase):
    """Test Prometheus metrics functionality."""

    def test_get_metrics_summary(self):
        """Test getting metrics summary."""
        summary = get_metrics_summary()
        
        # Should return a dictionary with expected keys
        self.assertIsInstance(summary, dict)
        expected_keys = [
            'feeds_processed_total',
            'articles_created_total', 
            'errors_total',
            'last_success_timestamp',
            'active_feeds',
            'feeds_with_errors'
        ]
        
        for key in expected_keys:
            self.assertIn(key, summary)

    @patch('app.metrics.start_http_server')
    def test_start_metrics_server(self, mock_start_server):
        """Test starting Prometheus metrics server."""
        from app.metrics import start_metrics_server
        
        start_metrics_server(8001)
        mock_start_server.assert_called_once_with(8001)

    @patch('app.metrics.start_http_server')
    def test_start_metrics_server_error(self, mock_start_server):
        """Test handling errors when starting metrics server."""
        mock_start_server.side_effect = Exception("Port already in use")
        
        from app.metrics import start_metrics_server
        
        # Should not raise exception, just log error
        start_metrics_server(8001)
        mock_start_server.assert_called_once_with(8001)


if __name__ == '__main__':
    unittest.main() 