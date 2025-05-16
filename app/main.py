import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
from contextlib import asynccontextmanager

from . import models
from .database import engine, get_db
from .routers import ingestion
from .schemas import HealthCheck

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(
    ingestion.ingest_rss_feeds,
    trigger=IntervalTrigger(hours=1),
    id="rss_ingestion",
    replace_existing=True,
)

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize the scheduler
    try:
        # Create tables in the database
        models.Base.metadata.create_all(bind=engine)
        
        # Start the scheduler
        scheduler.start()
        logger.info("Scheduler started")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        
    yield
    
    # Shutdown: gracefully stop the scheduler
    try:
        scheduler.shutdown()
        logger.info("Scheduler shut down")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {e}")

# Create FastAPI application
app = FastAPI(
    title="TradeEasy API",
    description="Real-time sentiment analytics platform for equities, FX, crypto, and commodities",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingestion.router)

# Health check endpoint
@app.get("/health", response_model=HealthCheck)
async def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return {"status": "ok"}

# Run the application using Uvicorn if executing this file directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
