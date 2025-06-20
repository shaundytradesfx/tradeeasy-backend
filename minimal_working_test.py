#!/usr/bin/env python3

"""
Minimal FastAPI server for testing basic functionality.
This helps isolate whether the issue is with FastAPI itself or our application code.
"""

from fastapi import FastAPI
import uvicorn

# Create a minimal FastAPI app
app = FastAPI(title="Minimal Test Server")

@app.get("/")
async def root():
    return {"status": "working", "message": "Minimal server is responding"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/test")
async def test():
    return {"test": "passed", "server": "responding"}

if __name__ == "__main__":
    print("Starting minimal test server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info") 