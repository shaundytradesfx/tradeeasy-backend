"""
Performance profiling and optimization module for TradeEasy backend.

This module provides tools for profiling ingestion & NLP latency, 
optimizing heavy text operations with batching and async processing,
and monitoring database performance.
"""

import time
import asyncio
import aiohttp
import logging
import psutil
import threading
import concurrent.futures
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Any, Optional, Tuple

import feedparser
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import event, text

from .database import get_db

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Dataclass for tracking performance metrics."""
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceProfiler:
    """
    Performance profiler for monitoring and optimizing operations.
    
    Tracks latency, throughput, and resource usage for various operations.
    """
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.operation_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.database_operations: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.lock = threading.Lock()
        
    def start_operation(self, operation_name: str, metadata: Dict[str, Any] = None) -> PerformanceMetrics:
        """Start tracking a performance operation."""
        metric = PerformanceMetrics(
            operation_name=operation_name,
            start_time=time.time(),
            metadata=metadata or {}
        )
        return metric
    
    def end_operation(self, metric: PerformanceMetrics, success: bool = True, error_message: str = None):
        """End tracking a performance operation."""
        metric.end_time = time.time()
        metric.duration = metric.end_time - metric.start_time
        metric.success = success
        metric.error_message = error_message
        
        with self.lock:
            self.metrics.append(metric)
            self.operation_times[metric.operation_name].append(metric.duration)
    
    @asynccontextmanager
    async def track_async_operation(self, operation_name: str, metadata: Dict[str, Any] = None):
        """Context manager for tracking async operations."""
        metric = self.start_operation(operation_name, metadata)
        try:
            yield metric
            self.end_operation(metric, success=True)
        except Exception as e:
            self.end_operation(metric, success=False, error_message=str(e))
            raise
    
    def track_operation(self, operation_name: str, metadata: Dict[str, Any] = None):
        """Decorator for tracking function performance."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                metric = self.start_operation(operation_name, metadata)
                try:
                    result = func(*args, **kwargs)
                    self.end_operation(metric, success=True)
                    return result
                except Exception as e:
                    self.end_operation(metric, success=False, error_message=str(e))
                    raise
            return wrapper
        return decorator
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get statistics for a specific operation."""
        times = list(self.operation_times[operation_name])
        if not times:
            return {"operation": operation_name, "count": 0}
        
        return {
            "operation": operation_name,
            "count": len(times),
            "avg_duration": sum(times) / len(times),
            "min_duration": min(times),
            "max_duration": max(times),
            "total_duration": sum(times),
            "recent_operations": len([t for t in times if t > 0])
        }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        stats = {}
        for operation_name in self.operation_times.keys():
            stats[operation_name] = self.get_operation_stats(operation_name)
        
        # Add system metrics
        stats["system"] = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return stats


# Global profiler instance
profiler = PerformanceProfiler()


class AsyncRSSProcessor:
    """
    Async RSS processor for optimized feed ingestion.
    
    Implements batching, concurrent processing, and async I/O for improved performance.
    """
    
    def __init__(self, max_concurrent_feeds: int = 10, max_concurrent_articles: int = 20, batch_size: int = 50):
        self.max_concurrent_feeds = max_concurrent_feeds
        self.max_concurrent_articles = max_concurrent_articles
        self.batch_size = batch_size
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def fetch_feed_async(self, url: str) -> Tuple[str, List[Dict]]:
        """Asynchronously fetch and parse an RSS feed."""
        async with profiler.track_async_operation("async_feed_fetch", {"url": url}):
            try:
                async with self.session.get(url) as response:
                    content = await response.text()
                    
                # Parse feed in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    feed = await loop.run_in_executor(executor, feedparser.parse, content)
                
                if feed.bozo:
                    logger.warning(f"RSS feed parsing error for {url}: {feed.bozo_exception}")
                    return url, []
                
                entries = []
                for entry in feed.entries:
                    if hasattr(entry, "link") and hasattr(entry, "title"):
                        std_entry = {
                            "title": entry.title,
                            "link": entry.link,
                            "published_at": None,
                            "source": url,
                            "summary": getattr(entry, "summary", ""),
                        }
                        
                        # Parse publish date
                        if hasattr(entry, "published_parsed") and entry.published_parsed:
                            try:
                                published_time = time.mktime(entry.published_parsed)
                                std_entry["published_at"] = datetime.fromtimestamp(published_time)
                            except (TypeError, ValueError):
                                pass
                        
                        entries.append(std_entry)
                
                logger.info(f"Async fetched {len(entries)} entries from {url}")
                return url, entries
                
            except Exception as e:
                logger.error(f"Error fetching RSS feed {url}: {e}")
                return url, []
    
    async def process_feeds_batch(self, feed_urls: List[str]) -> Dict[str, List[Dict]]:
        """Process multiple feeds concurrently."""
        async with profiler.track_async_operation("batch_feed_processing", {"feed_count": len(feed_urls)}):
            # Create semaphore to limit concurrent requests
            semaphore = asyncio.Semaphore(self.max_concurrent_feeds)
            
            async def fetch_with_semaphore(url):
                async with semaphore:
                    return await self.fetch_feed_async(url)
            
            # Execute all feed fetches concurrently
            results = await asyncio.gather(
                *[fetch_with_semaphore(url) for url in feed_urls],
                return_exceptions=True
            )
            
            # Process results
            feed_results = {}
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Feed processing exception: {result}")
                    continue
                
                url, entries = result
                feed_results[url] = entries
            
            return feed_results
    
    async def extract_articles_batch(self, article_urls: List[str]) -> List[Dict]:
        """Extract content from multiple articles concurrently."""
        async with profiler.track_async_operation("batch_article_extraction", {"article_count": len(article_urls)}):
            from .rss_ingest import extract_article_content
            
            # Create semaphore to limit concurrent article extractions
            semaphore = asyncio.Semaphore(self.max_concurrent_articles)
            
            async def extract_with_semaphore(url):
                async with semaphore:
                    loop = asyncio.get_event_loop()
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        return await loop.run_in_executor(
                            executor, extract_article_content, url, ""
                        )
            
            # Execute all extractions concurrently
            results = await asyncio.gather(
                *[extract_with_semaphore(url) for url in article_urls],
                return_exceptions=True
            )
            
            # Filter successful extractions
            extracted_articles = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Article extraction exception for {article_urls[i]}: {result}")
                    continue
                
                if result and result.get("text"):
                    extracted_articles.append(result)
            
            return extracted_articles


class BatchSentimentProcessor:
    """
    Optimized batch sentiment processor for improved NLP performance.
    
    Implements batching, caching, and parallel processing for sentiment analysis.
    """
    
    def __init__(self, batch_size: int = 32, max_workers: int = 4):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self._finbert_analyzer = None
    
    @property
    def finbert_analyzer(self):
        """Lazy load FinBERT analyzer."""
        if self._finbert_analyzer is None:
            try:
                from .nlp.finbert import get_finbert_analyzer
                self._finbert_analyzer = get_finbert_analyzer()
            except Exception as e:
                logger.warning(f"Failed to load FinBERT analyzer: {e}")
                self._finbert_analyzer = None
        return self._finbert_analyzer
    
    @profiler.track_operation("batch_sentiment_analysis")
    def process_articles_batch(self, articles: List[Dict]) -> List[Dict]:
        """Process sentiment analysis for a batch of articles."""
        if not articles:
            return []
        
        logger.info(f"Processing sentiment for {len(articles)} articles in batch")
        
        # Extract texts for batch processing
        texts = [article.get("text", "") for article in articles]
        
        # Process with FinBERT if available
        if self.finbert_analyzer:
            try:
                # Use FinBERT batch processing
                finbert_results = self.finbert_analyzer.analyze_batch(texts, use_cache=True)
            except Exception as e:
                logger.error(f"FinBERT batch processing failed: {e}")
                finbert_results = [{"composite_score": 0.0}] * len(texts)
        else:
            finbert_results = [{"composite_score": 0.0}] * len(texts)
        
        # Process with lexicon in parallel
        lexicon_results = self._process_lexicon_batch(texts)
        
        # Combine results
        results = []
        for i, article in enumerate(articles):
            result = {
                "article": article,
                "lexicon_score": lexicon_results[i],
                "finbert_score": finbert_results[i].get("composite_score", 0.0),
                "finbert_details": finbert_results[i]
            }
            results.append(result)
        
        return results
    
    def _process_lexicon_batch(self, texts: List[str]) -> List[float]:
        """Process lexicon sentiment for a batch of texts."""
        try:
            from .nlp.lexicon import get_lexicon
            lexicon = get_lexicon()
            
            scores = []
            for text in texts:
                # Simple tokenization for batch processing
                tokens = text.lower().split()
                score = lexicon.calculate_sentiment_score(tokens)
                scores.append(score)
            
            return scores
        except Exception as e:
            logger.error(f"Lexicon batch processing failed: {e}")
            return [0.0] * len(texts)
    
    async def process_articles_async(self, articles: List[Dict]) -> List[Dict]:
        """Asynchronously process sentiment analysis with batching."""
        if not articles:
            return []
        
        async with profiler.track_async_operation("async_batch_sentiment", {"article_count": len(articles)}):
            # Split into batches
            batches = [
                articles[i:i + self.batch_size]
                for i in range(0, len(articles), self.batch_size)
            ]
            
            # Process batches concurrently
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                batch_futures = [
                    loop.run_in_executor(executor, self.process_articles_batch, batch)
                    for batch in batches
                ]
                
                batch_results = await asyncio.gather(*batch_futures)
            
            # Flatten results
            all_results = []
            for batch_result in batch_results:
                all_results.extend(batch_result)
            
            return all_results


class DatabasePerformanceOptimizer:
    """
    Database performance optimizer with connection pooling and query monitoring.
    """
    
    def __init__(self):
        self.query_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.slow_query_threshold = 1.0  # seconds
    
    def optimize_engine_config(self, engine):
        """Configure engine for optimal performance."""
        # Add query timing event listener
        @event.listens_for(engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
        
        @event.listens_for(engine, "after_cursor_execute") 
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total_time = time.time() - context._query_start_time
            
            # Log slow queries
            if total_time > self.slow_query_threshold:
                logger.warning(f"Slow query detected ({total_time:.3f}s): {statement[:100]}...")
            
            # Track query performance
            query_type = statement.split()[0].upper() if statement else "UNKNOWN"
            self.query_times[query_type].append(total_time)
    
    def get_optimized_engine_params(self, database_url: str) -> Dict[str, Any]:
        """Get optimized engine parameters based on database type."""
        if "postgresql" in database_url:
            return {
                "pool_size": 20,
                "max_overflow": 0,
                "pool_pre_ping": True,
                "pool_recycle": 3600,
                "echo": False,
                "connect_args": {
                    "options": "-c timezone=utc",
                    "application_name": "tradeeasy_backend",
                    "connect_timeout": 10,
                }
            }
        elif "sqlite" in database_url:
            return {
                "pool_size": 5,
                "max_overflow": 10,
                "pool_pre_ping": True,
                "connect_args": {
                    "check_same_thread": False,
                    "timeout": 20,
                    "isolation_level": None,
                }
            }
        else:
            return {}
    
    def get_query_performance_stats(self) -> Dict[str, Any]:
        """Get query performance statistics."""
        stats = {}
        for query_type, times in self.query_times.items():
            if times:
                times_list = list(times)
                stats[query_type] = {
                    "count": len(times_list),
                    "avg_time": sum(times_list) / len(times_list),
                    "min_time": min(times_list),
                    "max_time": max(times_list),
                    "slow_queries": len([t for t in times_list if t > self.slow_query_threshold])
                }
        return stats


# Global database optimizer
db_optimizer = DatabasePerformanceOptimizer()


async def optimized_rss_ingestion(db: Session, feed_urls: List[str] = None) -> Dict[str, Any]:
    """
    Optimized RSS ingestion with async processing and batching.
    
    Args:
        db: Database session
        feed_urls: Optional list of feed URLs to process
        
    Returns:
        Ingestion statistics and performance metrics
    """
    # Local imports to avoid circular import issues
    from . import crud, schemas, models
    
    if not feed_urls:
        from .rss_feeds import ALL_FEEDS
        feed_urls = ALL_FEEDS
    
    start_time = time.time()
    logger.info(f"Starting optimized RSS ingestion for {len(feed_urls)} feeds")
    
    total_articles_created = 0
    total_entries_processed = 0
    total_errors = 0
    performance_stats = {}
    feed_results = {}  # Initialize to prevent reference errors
    
    try:
        # Step 1: Async feed processing
        async with AsyncRSSProcessor() as processor:
            feed_results = await processor.process_feeds_batch(feed_urls)
        
        # Step 2: Collect all article URLs for batch processing
        all_entries = []
        for url, entries in feed_results.items():
            total_entries_processed += len(entries)
            all_entries.extend(entries)
        
        # Step 3: Filter out existing articles (batch query)
        entry_urls = [entry["link"] for entry in all_entries]
        existing_urls = set()
        
        if entry_urls:
            # Batch query for existing articles
            with profiler.track_operation("batch_duplicate_check"):
                existing_articles = db.query(models.Article.url).filter(
                    models.Article.url.in_(entry_urls)
                ).all()
                existing_urls = {article.url for article in existing_articles}
        
        # Filter new entries
        new_entries = [entry for entry in all_entries if entry["link"] not in existing_urls]
        logger.info(f"Found {len(new_entries)} new articles out of {len(all_entries)} total entries")
        
        if not new_entries:
            logger.info("No new articles to process")
            return {
                "total_feeds": len(feed_urls),
                "total_entries": total_entries_processed,
                "articles_created": 0,
                "errors": 0,
                "duration": time.time() - start_time,
                "performance_stats": profiler.get_all_stats()
            }
        
        # Step 4: Async article content extraction
        async with AsyncRSSProcessor() as processor:
            extracted_articles = await processor.extract_articles_batch(
                [entry["link"] for entry in new_entries]
            )
        
        # Step 5: Batch sentiment processing
        sentiment_processor = BatchSentimentProcessor()
        sentiment_results = await sentiment_processor.process_articles_async(extracted_articles)
        
        # Step 6: Batch database insertion
        with profiler.track_operation("batch_db_insertion"):
            for result in sentiment_results:
                try:
                    article_data = result["article"]
                    
                    if not article_data.get("text"):
                        continue
                    
                    # Find corresponding entry for metadata
                    entry = next((e for e in new_entries if e["link"] == article_data.get("url")), {})
                    
                    # Create article
                    article_create = schemas.ArticleCreate(
                        source=entry.get("source", "unknown"),
                        title=entry.get("title", "Unknown Title"),
                        content=article_data["text"],
                        url=article_data.get("url", entry.get("link", "")),
                        published_at=entry.get("published_at") or article_data.get("publish_date"),
                        authors=", ".join(article_data.get("authors", [])) if article_data.get("authors") else None,
                        image_url=article_data.get("top_image"),
                        summary=article_data.get("summary")
                    )
                    
                    article = crud.create_article(db, article_create)
                    
                    # Create sentiment
                    sentiment_create = schemas.SentimentCreate(
                        article_id=article.id,
                        lexicon_score=result.get("lexicon_score"),
                        finbert_score=result.get("finbert_score")
                    )
                    
                    crud.create_sentiment(db, sentiment_create)
                    total_articles_created += 1
                    
                except Exception as e:
                    logger.error(f"Error creating article: {e}")
                    total_errors += 1
        
        duration = time.time() - start_time
        performance_stats = profiler.get_all_stats()
        
        logger.info(
            f"Optimized ingestion completed: {total_articles_created} articles created "
            f"from {total_entries_processed} entries in {duration:.2f}s"
        )
        
        return {
            "total_feeds": len(feed_urls),
            "total_entries": total_entries_processed,
            "articles_created": total_articles_created,
            "errors": total_errors,
            "duration": duration,
            "performance_stats": performance_stats,
            "optimization_used": True
        }
        
    except Exception as e:
        logger.error(f"Optimized ingestion failed: {e}")
        return {
            "total_feeds": len(feed_urls),
            "total_entries": total_entries_processed,
            "articles_created": total_articles_created,
            "errors": total_errors + 1,
            "duration": time.time() - start_time,
            "error": str(e),
            "performance_stats": profiler.get_all_stats()
        }


def profile_current_performance(db: Session) -> Dict[str, Any]:
    """
    Profile current system performance and identify bottlenecks.
    
    Args:
        db: Database session
        
    Returns:
        Comprehensive performance analysis
    """
    # Local imports to avoid circular import issues
    from . import models
    
    logger.info("Starting performance profiling...")
    
    performance_analysis = {
        "timestamp": datetime.utcnow().isoformat(),
        "system_metrics": {},
        "database_metrics": {},
        "nlp_metrics": {},
        "recommendations": []
    }
    
    # System metrics
    performance_analysis["system_metrics"] = {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "percent": psutil.virtual_memory().percent
        },
        "disk": {
            "total": psutil.disk_usage('/').total,
            "free": psutil.disk_usage('/').free,
            "percent": psutil.disk_usage('/').percent
        }
    }
    
    # Database metrics
    try:
        # Test query performance
        query_start = time.time()
        article_count = db.query(models.Article).count()
        query_duration = time.time() - query_start
        
        performance_analysis["database_metrics"] = {
            "article_count": article_count,
            "simple_query_time": query_duration,
            "query_stats": db_optimizer.get_query_performance_stats()
        }
        
        # Recommendations based on query time
        if query_duration > 0.5:
            performance_analysis["recommendations"].append(
                "Database queries are slow - consider optimizing indexes or connection pooling"
            )
    except Exception as e:
        performance_analysis["database_metrics"] = {"error": str(e)}
    
    # NLP performance test
    try:
        test_text = "The stock market showed positive trends today with strong performance."
        
        # Test lexicon processing
        lexicon_start = time.time()
        from .nlp.sentiment import analyze_article_sentiment
        lexicon_result = analyze_article_sentiment(test_text)
        lexicon_duration = time.time() - lexicon_start
        
        # Test FinBERT processing if available
        finbert_duration = 0
        try:
            finbert_start = time.time()
            from .nlp.finbert import analyze_finbert_sentiment
            finbert_result = analyze_finbert_sentiment(test_text)
            finbert_duration = time.time() - finbert_start
        except Exception:
            finbert_result = None
        
        performance_analysis["nlp_metrics"] = {
            "lexicon_processing_time": lexicon_duration,
            "finbert_processing_time": finbert_duration,
            "finbert_available": finbert_result is not None
        }
        
        # Recommendations based on NLP performance
        if finbert_duration > 2.0:
            performance_analysis["recommendations"].append(
                "FinBERT processing is slow - consider batch processing or GPU acceleration"
            )
    except Exception as e:
        performance_analysis["nlp_metrics"] = {"error": str(e)}
    
    # System-based recommendations
    if performance_analysis["system_metrics"]["memory"]["percent"] > 80:
        performance_analysis["recommendations"].append(
            "High memory usage detected - consider increasing system memory or optimizing memory usage"
        )
    
    if performance_analysis["system_metrics"]["cpu_percent"] > 80:
        performance_analysis["recommendations"].append(
            "High CPU usage detected - consider optimizing CPU-intensive operations"
        )
    
    return performance_analysis 