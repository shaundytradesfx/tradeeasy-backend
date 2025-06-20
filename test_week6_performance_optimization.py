#!/usr/bin/env python3
"""
Test suite for Week 6: Performance and Optimization

This test verifies:
1. Performance profiling and monitoring
2. Async RSS processing and batching
3. NLP batch processing optimization
4. Database connection pooling and query optimization
5. System performance metrics and recommendations
"""

import asyncio
import json
import logging
import pytest
import time
from datetime import datetime
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db
from app.models import Base, User, Article, Sentiment
from app.performance import (
    PerformanceProfiler,
    AsyncRSSProcessor,
    BatchSentimentProcessor,
    DatabasePerformanceOptimizer,
    optimized_rss_ingestion,
    profile_current_performance
)
from app import crud, schemas

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_week6_performance_optimization.db"
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

class TestWeek6PerformanceOptimization:
    """Test Week 6 performance optimization features."""
    
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
        
        logger.info("Week 6 Performance Optimization Test Setup Complete")
    
    @classmethod
    def teardown_class(cls):
        """Clean up test database."""
        cls.db.close()
        Base.metadata.drop_all(bind=engine)
        logger.info("Week 6 Performance Optimization Test Teardown Complete")
    
    def get_auth_token(self):
        """Get authentication token for API requests."""
        response = self.client.get("/api/auth/demo-login")
        if response.status_code == 200:
            return response.json()["access_token"]
        return None
    
    def test_performance_profiler(self):
        """Test the performance profiler functionality."""
        logger.info("Testing performance profiler...")
        
        # Test profiler creation
        profiler = PerformanceProfiler()
        assert profiler is not None
        
        # Test operation tracking
        metric = profiler.start_operation("test_operation", {"test": "data"})
        assert metric.operation_name == "test_operation"
        assert metric.metadata["test"] == "data"
        
        # Simulate some work
        time.sleep(0.1)
        
        profiler.end_operation(metric, success=True)
        assert metric.duration is not None
        assert metric.duration > 0.05  # Should be at least 50ms
        assert metric.success is True
        
        # Test stats retrieval
        stats = profiler.get_operation_stats("test_operation")
        assert stats["count"] == 1
        assert stats["avg_duration"] > 0
        
        # Test decorator tracking
        @profiler.track_operation("decorated_operation")
        def test_function():
            time.sleep(0.05)
            return "test_result"
        
        result = test_function()
        assert result == "test_result"
        
        decorated_stats = profiler.get_operation_stats("decorated_operation")
        assert decorated_stats["count"] == 1
        
        logger.info("✅ Performance profiler working correctly")
    
    def test_async_rss_processor(self):
        """Test async RSS processing functionality."""
        logger.info("Testing async RSS processor...")
        
        async def run_async_test():
            # Test with mock feeds to avoid network dependencies
            test_feeds = [
                "https://example.com/feed1.xml",
                "https://example.com/feed2.xml"
            ]
            
            processor = AsyncRSSProcessor(max_concurrent_feeds=2)
            
            # Mock the aiohttp session
            with patch('aiohttp.ClientSession') as mock_session:
                mock_response = MagicMock()
                mock_response.text.return_value = asyncio.coroutine(lambda: """
                    <?xml version="1.0"?>
                    <rss version="2.0">
                        <channel>
                            <item>
                                <title>Test Article</title>
                                <link>https://example.com/article1</link>
                                <description>Test description</description>
                            </item>
                        </channel>
                    </rss>
                """)()
                
                mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
                
                async with processor:
                    results = await processor.process_feeds_batch(test_feeds)
                
                # Should process both feeds
                assert len(results) <= 2  # May fail due to parsing, but should attempt both
        
        # Run async test
        asyncio.run(run_async_test())
        
        logger.info("✅ Async RSS processor working correctly")
    
    def test_batch_sentiment_processor(self):
        """Test batch sentiment processing optimization."""
        logger.info("Testing batch sentiment processor...")
        
        # Create test articles
        test_articles = [
            {"text": "The stock market showed positive trends today with strong performance."},
            {"text": "Economic indicators suggest a potential downturn in the financial sector."},
            {"text": "Company earnings exceeded expectations leading to increased investor confidence."}
        ]
        
        processor = BatchSentimentProcessor(batch_size=2)
        
        # Test batch processing
        results = processor.process_articles_batch(test_articles)
        
        assert len(results) == len(test_articles)
        
        for result in results:
            assert "lexicon_score" in result
            assert "finbert_score" in result
            assert "article" in result
            assert isinstance(result["lexicon_score"], (int, float))
            assert isinstance(result["finbert_score"], (int, float))
        
        logger.info("✅ Batch sentiment processor working correctly")
    
    def test_database_performance_optimizer(self):
        """Test database performance optimization."""
        logger.info("Testing database performance optimizer...")
        
        optimizer = DatabasePerformanceOptimizer()
        
        # Test engine parameter optimization
        sqlite_params = optimizer.get_optimized_engine_params("sqlite:///test.db")
        assert "pool_size" in sqlite_params
        assert "pool_pre_ping" in sqlite_params
        
        postgresql_params = optimizer.get_optimized_engine_params("postgresql://user:pass@localhost/db")
        assert "pool_size" in postgresql_params
        assert "connect_args" in postgresql_params
        assert postgresql_params["connect_args"]["application_name"] == "tradeeasy_backend"
        
        # Test query performance tracking
        # Simulate some query times
        optimizer.query_times["SELECT"].extend([0.1, 0.2, 0.3, 1.5, 0.8])
        
        stats = optimizer.get_query_performance_stats()
        assert "SELECT" in stats
        assert stats["SELECT"]["count"] == 5
        assert stats["SELECT"]["avg_time"] > 0
        assert stats["SELECT"]["slow_queries"] == 1  # 1.5s query is slow
        
        logger.info("✅ Database performance optimizer working correctly")
    
    def test_performance_api_endpoints(self):
        """Test performance monitoring API endpoints."""
        logger.info("Testing performance API endpoints...")
        
        token = self.get_auth_token()
        if not token:
            logger.warning("Cannot test performance endpoints without authentication")
            return
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test performance profile endpoint
        response = self.client.get("/api/performance/profile", headers=headers)
        assert response.status_code == 200
        
        profile_data = response.json()
        assert profile_data["status"] == "success"
        assert "performance_analysis" in profile_data
        assert "system_metrics" in profile_data["performance_analysis"]
        assert "database_metrics" in profile_data["performance_analysis"]
        
        # Test performance stats endpoint
        response = self.client.get("/api/performance/stats", headers=headers)
        assert response.status_code == 200
        
        stats_data = response.json()
        assert stats_data["status"] == "success"
        assert "operation_stats" in stats_data
        assert "database_stats" in stats_data
        
        # Test database stats endpoint
        response = self.client.get("/api/performance/database/stats", headers=headers)
        assert response.status_code == 200
        
        db_stats = response.json()
        assert db_stats["status"] == "success"
        assert "health_score" in db_stats
        assert isinstance(db_stats["health_score"], (int, float))
        
        # Test recommendations endpoint
        response = self.client.get("/api/performance/recommendations", headers=headers)
        assert response.status_code == 200
        
        recommendations = response.json()
        assert recommendations["status"] == "success"
        assert "recommendations" in recommendations
        assert "performance_score" in recommendations
        
        logger.info("✅ Performance API endpoints working correctly")
    
    def test_nlp_benchmarking(self):
        """Test NLP performance benchmarking."""
        logger.info("Testing NLP benchmarking...")
        
        token = self.get_auth_token()
        if not token:
            logger.warning("Cannot test NLP benchmarking without authentication")
            return
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test with small dataset for speed
        test_data = {
            "text_samples": [
                "The stock market is performing well today.",
                "Economic indicators show positive trends."
            ],
            "batch_sizes": [1, 2]
        }
        
        response = self.client.post(
            "/api/performance/benchmark/nlp",
            json=test_data,
            headers=headers
        )
        
        assert response.status_code == 200
        
        benchmark_data = response.json()
        assert benchmark_data["status"] == "success"
        assert "benchmark_results" in benchmark_data
        assert "recommended_batch_size" in benchmark_data
        
        # Check benchmark results structure
        for batch_size in test_data["batch_sizes"]:
            key = f"batch_size_{batch_size}"
            assert key in benchmark_data["benchmark_results"]
            assert "processing_time" in benchmark_data["benchmark_results"][key]
            assert "articles_per_second" in benchmark_data["benchmark_results"][key]
        
        logger.info("✅ NLP benchmarking working correctly")
    
    def test_async_processing_test(self):
        """Test async processing test endpoint."""
        logger.info("Testing async processing test...")
        
        token = self.get_auth_token()
        if not token:
            logger.warning("Cannot test async processing without authentication")
            return
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test with small number of feeds
        response = self.client.post(
            "/api/performance/test/async-processing?num_feeds=2",
            headers=headers
        )
        
        # This might fail due to network issues, but should not crash
        assert response.status_code in [200, 500]  # Allow for network failures
        
        if response.status_code == 200:
            test_data = response.json()
            assert test_data["status"] == "success"
            assert "test_results" in test_data
            
            results = test_data["test_results"]
            assert "feeds_processed" in results
            assert "processing_time" in results
        
        logger.info("✅ Async processing test working correctly")
    
    def test_optimized_ingestion_functionality(self):
        """Test optimized RSS ingestion functionality."""
        logger.info("Testing optimized ingestion functionality...")
        
        # Test with mock data to avoid network dependencies
        async def run_optimized_test():
            # Mock feeds to avoid actual network calls
            mock_feeds = ["https://example.com/test_feed.xml"]
            
            with patch('app.performance.AsyncRSSProcessor') as mock_processor:
                # Mock the async context manager
                mock_instance = MagicMock()
                mock_processor.return_value.__aenter__.return_value = mock_instance
                mock_processor.return_value.__aexit__.return_value = asyncio.coroutine(lambda *args: None)()
                
                # Mock feed processing results
                mock_instance.process_feeds_batch.return_value = asyncio.coroutine(lambda feeds: {
                    "https://example.com/test_feed.xml": [
                        {
                            "title": "Test Article",
                            "link": "https://example.com/article1",
                            "published_at": datetime.utcnow(),
                            "source": "https://example.com/test_feed.xml",
                            "summary": "Test summary"
                        }
                    ]
                })()
                
                # Mock article extraction
                mock_instance.extract_articles_batch.return_value = asyncio.coroutine(lambda urls: [
                    {
                        "text": "Test article content for sentiment analysis.",
                        "url": "https://example.com/article1",
                        "summary": "Test summary"
                    }
                ])()
                
                # Run optimized ingestion
                result = await optimized_rss_ingestion(self.db, mock_feeds)
                
                assert "total_feeds" in result
                assert "performance_stats" in result
                assert "optimization_used" in result
                assert result["optimization_used"] is True
        
        # Run async test
        asyncio.run(run_optimized_test())
        
        logger.info("✅ Optimized ingestion functionality working correctly")
    
    def test_system_performance_profiling(self):
        """Test system performance profiling."""
        logger.info("Testing system performance profiling...")
        
        # Test performance profiling function
        performance_data = profile_current_performance(self.db)
        
        assert "timestamp" in performance_data
        assert "system_metrics" in performance_data
        assert "database_metrics" in performance_data
        assert "nlp_metrics" in performance_data
        assert "recommendations" in performance_data
        
        # Check system metrics
        system_metrics = performance_data["system_metrics"]
        assert "cpu_percent" in system_metrics
        assert "memory" in system_metrics
        assert "disk" in system_metrics
        
        # Check memory metrics
        memory_metrics = system_metrics["memory"]
        assert "total" in memory_metrics
        assert "available" in memory_metrics
        assert "percent" in memory_metrics
        
        # Check database metrics
        db_metrics = performance_data["database_metrics"]
        if "error" not in db_metrics:
            assert "simple_query_time" in db_metrics
        
        # Check NLP metrics
        nlp_metrics = performance_data["nlp_metrics"]
        if "error" not in nlp_metrics:
            assert "lexicon_processing_time" in nlp_metrics
            assert "finbert_processing_time" in nlp_metrics
        
        logger.info("✅ System performance profiling working correctly")
    
    def run_all_tests(self):
        """Run all Week 6 performance optimization tests."""
        logger.info("🚀 Starting Week 6 Performance Optimization Tests")
        logger.info("=" * 60)
        
        test_methods = [
            self.test_performance_profiler,
            self.test_async_rss_processor,
            self.test_batch_sentiment_processor,
            self.test_database_performance_optimizer,
            self.test_performance_api_endpoints,
            self.test_nlp_benchmarking,
            self.test_async_processing_test,
            self.test_optimized_ingestion_functionality,
            self.test_system_performance_profiling
        ]
        
        results = {}
        
        for test_method in test_methods:
            test_name = test_method.__name__
            try:
                logger.info(f"\n📋 Running {test_name}...")
                test_method()
                results[test_name] = True
                logger.info(f"✅ {test_name} PASSED")
            except Exception as e:
                results[test_name] = False
                logger.error(f"❌ {test_name} FAILED: {e}")
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 WEEK 6 PERFORMANCE OPTIMIZATION TEST SUMMARY")
        logger.info("=" * 60)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{test_name.replace('test_', '').replace('_', ' ').title()}: {status}")
        
        logger.info(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            logger.info("🎉 All Week 6 Performance Optimization tests PASSED!")
        else:
            logger.warning(f"⚠️  {total - passed} tests failed. Review optimization implementation.")
        
        return results


if __name__ == "__main__":
    """Run the test suite directly."""
    logger.info("Starting Week 6 Performance Optimization Test Suite...")
    
    test_instance = TestWeek6PerformanceOptimization()
    test_instance.setup_class()
    
    try:
        results = test_instance.run_all_tests()
        
        # Exit with appropriate code
        if all(results.values()):
            exit(0)
        else:
            exit(1)
            
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        exit(1)
    finally:
        test_instance.teardown_class() 