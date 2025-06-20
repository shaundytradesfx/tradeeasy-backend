"""
Performance monitoring and optimization API endpoints.

Provides endpoints for profiling ingestion & NLP latency,
monitoring system performance, and running optimized operations.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from .. import models
from ..auth import get_current_user
from ..database import get_db
from ..performance import (
    profiler,
    profile_current_performance,
    optimized_rss_ingestion,
    AsyncRSSProcessor,
    BatchSentimentProcessor,
    db_optimizer
)

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/performance",
    tags=["performance"],
    responses={404: {"description": "Not found"}},
)


@router.get("/profile")
async def get_performance_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get comprehensive performance profile of the system.
    
    Analyzes current system performance, database metrics, and NLP processing
    to identify bottlenecks and provide optimization recommendations.
    """
    try:
        logger.info(f"User {current_user.username} requested performance profile")
        
        # Get comprehensive performance analysis
        performance_data = profile_current_performance(db)
        
        return {
            "status": "success",
            "performance_analysis": performance_data,
            "user": current_user.username,
            "message": "Performance profile generated successfully"
        }
        
    except Exception as e:
        logger.error(f"Performance profiling failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Performance profiling failed: {str(e)}"
        )


@router.get("/stats")
async def get_performance_stats(
    current_user: models.User = Depends(get_current_user)
):
    """
    Get real-time performance statistics.
    
    Returns current operation statistics, database performance metrics,
    and system resource usage.
    """
    try:
        # Get performance statistics
        operation_stats = profiler.get_all_stats()
        database_stats = db_optimizer.get_query_performance_stats()
        
        return {
            "status": "success",
            "operation_stats": operation_stats,
            "database_stats": database_stats,
            "user": current_user.username,
            "total_operations": sum(stats.get("count", 0) for stats in operation_stats.values() if isinstance(stats, dict))
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance stats: {str(e)}"
        )


@router.post("/optimize/ingestion")
async def run_optimized_ingestion(
    background_tasks: BackgroundTasks,
    feed_urls: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Run optimized RSS ingestion with async processing and batching.
    
    Processes RSS feeds using optimized algorithms including:
    - Async feed fetching
    - Batch article extraction
    - Concurrent sentiment processing
    - Optimized database operations
    """
    try:
        logger.info(f"User {current_user.username} started optimized ingestion")
        
        # Run optimized ingestion
        result = await optimized_rss_ingestion(db, feed_urls)
        
        logger.info(f"Optimized ingestion completed for user {current_user.username}")
        
        return {
            "status": "success",
            "ingestion_result": result,
            "user": current_user.username,
            "message": "Optimized ingestion completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Optimized ingestion failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Optimized ingestion failed: {str(e)}"
        )


@router.post("/benchmark/nlp")
async def benchmark_nlp_performance(
    text_samples: Optional[List[str]] = None,
    batch_sizes: Optional[List[int]] = None,
    current_user: models.User = Depends(get_current_user)
):
    """
    Benchmark NLP processing performance with different configurations.
    
    Tests sentiment analysis performance with various batch sizes
    and processing configurations to identify optimal settings.
    """
    try:
        logger.info(f"User {current_user.username} started NLP benchmarking")
        
        # Default test samples
        if not text_samples:
            text_samples = [
                "The stock market showed positive trends today with strong performance.",
                "Economic indicators suggest a potential downturn in the financial sector.",
                "Company earnings exceeded expectations leading to increased investor confidence.",
                "Market volatility continues to impact trading decisions across all sectors.",
                "New regulations may affect the cryptocurrency market in the coming months."
            ] * 10  # 50 samples for testing
        
        # Default batch sizes to test
        if not batch_sizes:
            batch_sizes = [1, 5, 10, 20, 32]
        
        benchmark_results = {}
        
        for batch_size in batch_sizes:
            logger.info(f"Testing batch size: {batch_size}")
            
            # Create articles for testing
            test_articles = [{"text": text} for text in text_samples]
            
            # Benchmark batch processing
            processor = BatchSentimentProcessor(batch_size=batch_size)
            
            import time
            start_time = time.time()
            results = await processor.process_articles_async(test_articles)
            duration = time.time() - start_time
            
            benchmark_results[f"batch_size_{batch_size}"] = {
                "batch_size": batch_size,
                "total_articles": len(test_articles),
                "processing_time": duration,
                "articles_per_second": len(test_articles) / duration,
                "avg_time_per_article": duration / len(test_articles),
                "successful_processing": len([r for r in results if r.get("lexicon_score") is not None])
            }
        
        # Find optimal batch size
        best_batch_size = max(
            benchmark_results.keys(),
            key=lambda k: benchmark_results[k]["articles_per_second"]
        )
        
        return {
            "status": "success",
            "benchmark_results": benchmark_results,
            "recommended_batch_size": benchmark_results[best_batch_size]["batch_size"],
            "best_performance": benchmark_results[best_batch_size],
            "user": current_user.username,
            "message": "NLP benchmarking completed successfully"
        }
        
    except Exception as e:
        logger.error(f"NLP benchmarking failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"NLP benchmarking failed: {str(e)}"
        )


@router.get("/database/stats")
async def get_database_performance_stats(
    current_user: models.User = Depends(get_current_user)
):
    """
    Get detailed database performance statistics.
    
    Returns query performance metrics, connection pool status,
    and optimization recommendations.
    """
    try:
        # Get database performance stats
        db_stats = db_optimizer.get_query_performance_stats()
        
        # Calculate overall database health score
        health_score = 100
        recommendations = []
        
        for query_type, stats in db_stats.items():
            avg_time = stats.get("avg_time", 0)
            slow_queries = stats.get("slow_queries", 0)
            total_queries = stats.get("count", 0)
            
            if avg_time > 1.0:
                health_score -= 20
                recommendations.append(f"{query_type} queries are slow (avg: {avg_time:.3f}s)")
            
            if slow_queries > 0 and total_queries > 0:
                slow_ratio = slow_queries / total_queries
                if slow_ratio > 0.1:  # More than 10% slow queries
                    health_score -= 15
                    recommendations.append(f"{query_type} has {slow_ratio:.1%} slow queries")
        
        return {
            "status": "success",
            "database_stats": db_stats,
            "health_score": max(0, health_score),
            "recommendations": recommendations,
            "user": current_user.username,
            "total_query_types": len(db_stats)
        }
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get database stats: {str(e)}"
        )


@router.post("/test/async-processing")
async def test_async_processing(
    num_feeds: int = 5,
    current_user: models.User = Depends(get_current_user)
):
    """
    Test async processing performance with a limited number of feeds.
    
    Useful for testing and benchmarking the async RSS processing
    capabilities without running a full ingestion.
    """
    try:
        logger.info(f"User {current_user.username} started async processing test")
        
        # Get sample feeds for testing
        from ..rss_feeds import ALL_FEEDS
        test_feeds = ALL_FEEDS[:num_feeds]
        
        results = {}
        
        # Test async feed processing
        async with AsyncRSSProcessor() as processor:
            import time
            start_time = time.time()
            
            feed_results = await processor.process_feeds_batch(test_feeds)
            
            processing_time = time.time() - start_time
            
            total_entries = sum(len(entries) for entries in feed_results.values())
            
            results = {
                "feeds_processed": len(feed_results),
                "total_entries": total_entries,
                "processing_time": processing_time,
                "feeds_per_second": len(test_feeds) / processing_time,
                "entries_per_second": total_entries / processing_time if processing_time > 0 else 0,
                "successful_feeds": len([url for url, entries in feed_results.items() if entries]),
                "failed_feeds": len([url for url, entries in feed_results.items() if not entries])
            }
        
        return {
            "status": "success",
            "test_results": results,
            "user": current_user.username,
            "message": "Async processing test completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Async processing test failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Async processing test failed: {str(e)}"
        )


@router.get("/recommendations")
async def get_performance_recommendations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get personalized performance optimization recommendations.
    
    Analyzes current system state and usage patterns to provide
    specific recommendations for improving performance.
    """
    try:
        # Get performance profile
        performance_data = profile_current_performance(db)
        
        # Get operation statistics
        operation_stats = profiler.get_all_stats()
        
        # Generate recommendations
        recommendations = []
        priority_scores = {}
        
        # System resource recommendations
        system_metrics = performance_data.get("system_metrics", {})
        memory_percent = system_metrics.get("memory", {}).get("percent", 0)
        cpu_percent = system_metrics.get("cpu_percent", 0)
        
        if memory_percent > 80:
            recommendations.append({
                "category": "system",
                "priority": "high",
                "issue": "High memory usage",
                "recommendation": "Consider increasing system RAM or optimizing memory-intensive operations",
                "current_value": f"{memory_percent:.1f}%",
                "target_value": "<70%"
            })
            priority_scores["memory"] = 90
        
        if cpu_percent > 70:
            recommendations.append({
                "category": "system", 
                "priority": "medium",
                "issue": "High CPU usage",
                "recommendation": "Consider optimizing CPU-intensive operations or using async processing",
                "current_value": f"{cpu_percent:.1f}%",
                "target_value": "<60%"
            })
            priority_scores["cpu"] = 70
        
        # Database performance recommendations
        db_metrics = performance_data.get("database_metrics", {})
        query_time = db_metrics.get("simple_query_time", 0)
        
        if query_time > 0.5:
            recommendations.append({
                "category": "database",
                "priority": "high",
                "issue": "Slow database queries",
                "recommendation": "Enable database connection pooling and optimize query indexes",
                "current_value": f"{query_time:.3f}s",
                "target_value": "<0.1s"
            })
            priority_scores["database"] = 85
        
        # NLP performance recommendations
        nlp_metrics = performance_data.get("nlp_metrics", {})
        finbert_time = nlp_metrics.get("finbert_processing_time", 0)
        
        if finbert_time > 2.0:
            recommendations.append({
                "category": "nlp",
                "priority": "medium",
                "issue": "Slow FinBERT processing",
                "recommendation": "Enable batch processing for sentiment analysis or consider GPU acceleration",
                "current_value": f"{finbert_time:.3f}s",
                "target_value": "<1.0s"
            })
            priority_scores["nlp"] = 60
        
        # Operation frequency recommendations
        for operation, stats in operation_stats.items():
            if isinstance(stats, dict) and stats.get("count", 0) > 0:
                avg_duration = stats.get("avg_duration", 0)
                
                if operation == "rss_ingestion" and avg_duration > 30:
                    recommendations.append({
                        "category": "ingestion",
                        "priority": "medium",
                        "issue": "Slow RSS ingestion",
                        "recommendation": "Use optimized async ingestion with batch processing",
                        "current_value": f"{avg_duration:.1f}s",
                        "target_value": "<15s"
                    })
        
        # Sort recommendations by priority
        priority_order = {"high": 3, "medium": 2, "low": 1}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 0), reverse=True)
        
        return {
            "status": "success",
            "recommendations": recommendations,
            "total_recommendations": len(recommendations),
            "high_priority_count": len([r for r in recommendations if r["priority"] == "high"]),
            "performance_score": max(0, 100 - sum(priority_scores.values()) // len(priority_scores) if priority_scores else 100),
            "user": current_user.username
        }
        
    except Exception as e:
        logger.error(f"Failed to generate recommendations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        ) 