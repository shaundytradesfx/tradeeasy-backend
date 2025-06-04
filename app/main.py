"""Main FastAPI application with RSS ingestion, sentiment analysis, and metrics."""
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from prometheus_client import start_http_server

from .database import engine, SessionLocal
from .models import Base
from .routers import ingestion, sentiment, search, watchlist, alerts, auth
from .rss_ingest import ingest_all_feeds, ingest_with_alert_checking
from .metrics import metrics
from .websocket_manager import websocket_manager
from . import crud

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


async def scheduled_rss_ingestion():
    """Scheduled task to run RSS ingestion with alert checking."""
    logger.info("Starting scheduled RSS ingestion with alert checking...")
    try:
        db = SessionLocal()
        try:
            # Use the enhanced ingestion function that includes alert checking
            result = ingest_with_alert_checking(db)
            
            # Log both ingestion and alert results
            ingestion_summary = {
                "articles_created": result.get("articles_created", 0),
                "total_feeds_processed": result.get("total_feeds_processed", 0),
                "total_errors": result.get("total_errors", 0)
            }
            
            alert_summary = result.get("alert_checking", {})
            
            logger.info(f"Scheduled RSS ingestion completed: {ingestion_summary}")
            if alert_summary.get("alerts_triggered", 0) > 0:
                logger.info(f"Alert checking: {alert_summary['alerts_triggered']} alerts triggered")
            
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in scheduled RSS ingestion: {e}")


async def scheduled_hourly_aggregates():
    """Scheduled task to compute hourly sentiment aggregates."""
    logger.info("Starting scheduled hourly sentiment aggregation...")
    try:
        db = SessionLocal()
        try:
            created_aggregates = crud.compute_hourly_sentiment_averages(db)
            logger.info(f"Created {len(created_aggregates)} hourly sentiment aggregates")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in scheduled hourly aggregation: {e}")


async def scheduled_alert_maintenance():
    """Scheduled task for alert system maintenance (optional)."""
    logger.info("Starting scheduled alert maintenance...")
    try:
        db = SessionLocal()
        try:
            # Clean up old triggered alerts (older than 30 days)
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            # This is a placeholder for alert maintenance logic
            # In a real system, you might want to:
            # - Clean up old triggered alerts
            # - Send digest emails
            # - Update alert statistics
            
            logger.info("Alert maintenance completed")
            
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in scheduled alert maintenance: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    global scheduler
    
    # Startup
    logger.info("Starting TradeEasy backend...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    # Start Prometheus metrics server
    try:
        start_http_server(8001)
        logger.info("Prometheus metrics server started on port 8001")
    except Exception as e:
        logger.warning(f"Failed to start Prometheus server: {e}")
    
    # Initialize and start scheduler
    scheduler = AsyncIOScheduler()
    
    # Schedule RSS ingestion with alert checking every hour
    scheduler.add_job(
        scheduled_rss_ingestion,
        trigger=IntervalTrigger(hours=1),
        id="rss_ingestion_with_alerts",
        name="RSS Feed Ingestion with Alert Checking",
        replace_existing=True
    )
    
    # Schedule hourly sentiment aggregation (offset by 5 minutes after the hour)
    scheduler.add_job(
        scheduled_hourly_aggregates,
        trigger=IntervalTrigger(hours=1, start_date="2024-01-01 00:05:00"),
        id="hourly_aggregates",
        name="Hourly Sentiment Aggregation",
        replace_existing=True
    )
    
    # Schedule alert maintenance daily at 2 AM
    scheduler.add_job(
        scheduled_alert_maintenance,
        trigger=IntervalTrigger(hours=24, start_date="2024-01-01 02:00:00"),
        id="alert_maintenance",
        name="Daily Alert Maintenance",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started with RSS ingestion, hourly aggregation, and alert maintenance jobs")
    
    # Start metrics tracking
    metrics.start_ingestion_run()
    
    yield
    
    # Shutdown
    logger.info("Shutting down TradeEasy backend...")
    if scheduler:
        scheduler.shutdown()
        logger.info("Scheduler shut down")


# Create FastAPI app with lifespan management
app = FastAPI(
    title="TradeEasy Backend",
    description="Real-time sentiment analytics platform for financial markets with watchlists and alerts",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers - organized by functionality
app.include_router(auth.router)  # Authentication endpoints
app.include_router(watchlist.router)  # Watchlist endpoints  
app.include_router(alerts.router)  # Alert endpoints
app.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
app.include_router(sentiment.router, prefix="/api/sentiment", tags=["sentiment"])
app.include_router(search.router, prefix="/api/search", tags=["search"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/status")
async def api_status():
    """Get comprehensive API status including watchlist and alert features."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "features": {
            "rss_ingestion": True,
            "sentiment_analysis": True,
            "search": True,
            "watchlists": True,
            "alerts": True,
            "authentication": "demo",
            "background_alert_checking": True,
            "websocket_streaming": True
        },
        "endpoints": {
            "auth": "/api/auth/*",
            "watchlists": "/api/watchlists/*", 
            "alerts": "/api/alerts/*",
            "sentiment": "/api/sentiment/*",
            "search": "/api/search/*",
            "ingestion": "/ingestion/*",
            "websocket": "/ws/sentiment"
        },
        "scheduler_jobs": ["rss_ingestion_with_alerts", "hourly_aggregates", "alert_maintenance"]
    }


@app.websocket("/ws/sentiment")
async def websocket_sentiment_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time sentiment updates.
    
    Clients can connect to this endpoint to receive real-time broadcasts of:
    - New sentiment analysis results
    - Aggregate sentiment updates  
    - Alert notifications
    """
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive and handle any client messages
            data = await websocket.receive_text()
            
            # Echo back any received message for testing
            if data:
                await websocket_manager.send_personal_message({
                    "type": "echo",
                    "message": f"Received: {data}",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)


@app.get("/api/websocket/stats")
async def get_websocket_stats():
    """Get statistics about active WebSocket connections."""
    return await websocket_manager.get_connection_stats()


@app.post("/api/websocket/test-broadcast")
async def test_websocket_broadcast():
    """Test endpoint to manually trigger WebSocket broadcasts."""
    try:
        # Test sentiment update broadcast
        test_article_data = {
            "id": "test-123",
            "title": "Test Article for WebSocket Broadcasting",
            "source": "test-source",
            "url": "https://example.com/test",
            "published_at": datetime.utcnow().isoformat(),
            "asset_class": "test"
        }
        
        test_sentiment_data = {
            "lexicon_score": 0.5,
            "finbert_score": 0.3,
            "processing_time": 0.1
        }
        
        await websocket_manager.broadcast_sentiment_update(test_article_data, test_sentiment_data)
        
        # Test aggregate update broadcast
        test_aggregate_data = {
            "avg_score": 0.4,
            "article_count": 5,
            "time_period": "1h"
        }
        
        await websocket_manager.broadcast_aggregate_update("TEST", test_aggregate_data)
        
        # Test alert triggered broadcast
        test_alert_data = {
            "alert_id": "test-alert-123",
            "asset_symbol": "TEST",
            "threshold": 0.5,
            "direction": "above",
            "current_sentiment": 0.6,
            "user_id": "test-user-123"
        }
        
        await websocket_manager.broadcast_alert_triggered(test_alert_data)
        
        return {
            "status": "success",
            "message": "Test broadcasts sent",
            "broadcasts_sent": 3,
            "active_connections": len(websocket_manager.active_connections)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to send test broadcasts: {str(e)}",
            "active_connections": len(websocket_manager.active_connections)
        }


@app.get("/metrics")
async def get_metrics():
    """Get Prometheus metrics."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi import Response
    
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Run the application using Uvicorn if executing this file directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
