"""
Metrics collection and Prometheus exporter for TradeEasy ingestion system.

This module provides comprehensive metrics tracking for RSS feed ingestion,
including counters, gauges, and histograms for monitoring system performance.
"""

import time
from typing import Dict, Any
from prometheus_client import Counter, Gauge, Histogram, Info, start_http_server
import logging

logger = logging.getLogger(__name__)

# Ingestion Metrics
ingestion_feeds_total = Counter(
    'tradeeasy_ingestion_feeds_total',
    'Total number of RSS feeds processed',
    ['status']  # success, error, invalid
)

ingestion_entries_total = Counter(
    'tradeeasy_ingestion_entries_total', 
    'Total number of RSS entries processed',
    ['feed_category']  # equities, forex, crypto, commodities
)

ingestion_articles_created_total = Counter(
    'tradeeasy_ingestion_articles_created_total',
    'Total number of articles successfully created',
    ['feed_category']
)

ingestion_errors_total = Counter(
    'tradeeasy_ingestion_errors_total',
    'Total number of ingestion errors',
    ['error_type', 'feed_category']  # parse_error, download_error, db_error, etc.
)

ingestion_duration_seconds = Histogram(
    'tradeeasy_ingestion_duration_seconds',
    'Time spent processing RSS feeds',
    ['operation'],  # full_ingestion, single_feed, article_extraction
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

ingestion_last_success_timestamp = Gauge(
    'tradeeasy_ingestion_last_success_timestamp',
    'Timestamp of last successful ingestion run'
)

ingestion_feeds_with_errors = Gauge(
    'tradeeasy_ingestion_feeds_with_errors',
    'Number of feeds that had errors in last run'
)

ingestion_active_feeds = Gauge(
    'tradeeasy_ingestion_active_feeds',
    'Number of active RSS feeds being monitored'
)

# Article processing metrics
article_extraction_duration_seconds = Histogram(
    'tradeeasy_article_extraction_duration_seconds',
    'Time spent extracting article content',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0]
)

article_extraction_retries_total = Counter(
    'tradeeasy_article_extraction_retries_total',
    'Total number of article extraction retries',
    ['retry_reason']  # timeout, connection_error, http_error
)

article_content_length_bytes = Histogram(
    'tradeeasy_article_content_length_bytes',
    'Length of extracted article content in bytes',
    buckets=[100, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000]
)

# System info
system_info = Info(
    'tradeeasy_system_info',
    'System information'
)

# Database metrics
database_operations_total = Counter(
    'tradeeasy_database_operations_total',
    'Total database operations',
    ['operation', 'status']  # create_article, check_duplicate, etc.
)

database_operation_duration_seconds = Histogram(
    'tradeeasy_database_operation_duration_seconds',
    'Database operation duration',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)


class IngestionMetrics:
    """Class to track and manage ingestion metrics."""
    
    def __init__(self):
        """Initialize metrics tracking."""
        self.current_run_start = None
        self.current_run_stats = {
            'feeds_processed': 0,
            'feeds_with_errors': 0,
            'total_entries': 0,
            'total_articles': 0,
            'total_errors': 0,
            'error_breakdown': {}
        }
        
        # Set system info
        system_info.info({
            'version': '0.1.0',
            'component': 'tradeeasy-backend',
            'module': 'rss-ingestion'
        })
    
    def start_ingestion_run(self):
        """Mark the start of an ingestion run."""
        self.current_run_start = time.time()
        self.current_run_stats = {
            'feeds_processed': 0,
            'feeds_with_errors': 0,
            'total_entries': 0,
            'total_articles': 0,
            'total_errors': 0,
            'error_breakdown': {}
        }
        logger.info("Started ingestion metrics tracking")
    
    def record_feed_processed(self, status: str, category: str = 'unknown'):
        """Record that a feed was processed."""
        ingestion_feeds_total.labels(status=status).inc()
        self.current_run_stats['feeds_processed'] += 1
        
        if status == 'error':
            self.current_run_stats['feeds_with_errors'] += 1
    
    def record_entries_processed(self, count: int, category: str = 'unknown'):
        """Record the number of entries processed."""
        ingestion_entries_total.labels(feed_category=category).inc(count)
        self.current_run_stats['total_entries'] += count
    
    def record_articles_created(self, count: int, category: str = 'unknown'):
        """Record the number of articles created."""
        ingestion_articles_created_total.labels(feed_category=category).inc(count)
        self.current_run_stats['total_articles'] += count
    
    def record_error(self, error_type: str, category: str = 'unknown'):
        """Record an error during ingestion."""
        ingestion_errors_total.labels(error_type=error_type, feed_category=category).inc()
        self.current_run_stats['total_errors'] += 1
        
        # Track error breakdown
        key = f"{error_type}_{category}"
        self.current_run_stats['error_breakdown'][key] = \
            self.current_run_stats['error_breakdown'].get(key, 0) + 1
    
    def record_article_extraction(self, duration: float, content_length: int, retries: int = 0):
        """Record article extraction metrics."""
        article_extraction_duration_seconds.observe(duration)
        article_content_length_bytes.observe(content_length)
        
        if retries > 0:
            article_extraction_retries_total.labels(retry_reason='general').inc(retries)
    
    def record_database_operation(self, operation: str, duration: float, status: str = 'success'):
        """Record database operation metrics."""
        database_operations_total.labels(operation=operation, status=status).inc()
        database_operation_duration_seconds.labels(operation=operation).observe(duration)
    
    def finish_ingestion_run(self, active_feeds_count: int):
        """Mark the end of an ingestion run and update gauges."""
        if self.current_run_start is None:
            logger.warning("finish_ingestion_run called without start_ingestion_run")
            return
        
        duration = time.time() - self.current_run_start
        ingestion_duration_seconds.labels(operation='full_ingestion').observe(duration)
        
        # Update gauges
        ingestion_last_success_timestamp.set_to_current_time()
        ingestion_feeds_with_errors.set(self.current_run_stats['feeds_with_errors'])
        ingestion_active_feeds.set(active_feeds_count)
        
        # Add duration to stats
        self.current_run_stats['duration'] = duration
        
        # Log comprehensive stats
        logger.info(
            f"Ingestion run completed in {duration:.2f}s. "
            f"Stats: {self.current_run_stats}"
        )
        
        return self.current_run_stats
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current run statistics."""
        stats = self.current_run_stats.copy()
        if self.current_run_start:
            stats['duration'] = time.time() - self.current_run_start
        return stats


# Global metrics instance
metrics = IngestionMetrics()


def start_metrics_server(port: int = 8001):
    """Start Prometheus metrics server on specified port."""
    try:
        start_http_server(port)
        logger.info(f"Prometheus metrics server started on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")


def get_metrics_summary() -> Dict[str, Any]:
    """Get a summary of current metrics for logging/debugging."""
    try:
        # Access Prometheus metrics properly
        feeds_total = 0
        articles_total = 0
        errors_total = 0
        
        # Sum up counter values across all labels
        for sample in ingestion_feeds_total.collect()[0].samples:
            feeds_total += sample.value
            
        for sample in ingestion_articles_created_total.collect()[0].samples:
            articles_total += sample.value
            
        for sample in ingestion_errors_total.collect()[0].samples:
            errors_total += sample.value
        
        return {
            'feeds_processed_total': feeds_total,
            'articles_created_total': articles_total,
            'errors_total': errors_total,
            'last_success_timestamp': ingestion_last_success_timestamp._value._value,
            'active_feeds': ingestion_active_feeds._value._value,
            'feeds_with_errors': ingestion_feeds_with_errors._value._value
        }
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        return {
            'feeds_processed_total': 0,
            'articles_created_total': 0,
            'errors_total': 0,
            'last_success_timestamp': 0,
            'active_feeds': 0,
            'feeds_with_errors': 0
        } 