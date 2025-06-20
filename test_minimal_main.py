"""Minimal FastAPI application for testing."""
import logging
from fastapi import FastAPI

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create minimal FastAPI app
app = FastAPI(
    title="Minimal TradeEasy Backend",
    description="Minimal version for testing",
    version="1.0.0"
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "Minimal server is working"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Minimal TradeEasy backend is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 