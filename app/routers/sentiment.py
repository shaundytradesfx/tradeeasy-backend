"""
Sentiment analysis API endpoints.

This module provides endpoints for analyzing sentiment of text and retrieving
latest sentiment data for assets.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta

from ..database import get_db
from ..schemas import SentimentAnalysisRequest, SentimentAnalysisResponse, SentimentAggregateWithAsset, Asset
from ..models import Asset as ModelAsset
from ..nlp import (
    analyze_article_sentiment,
    analyze_finbert_sentiment,
    calculate_lexicon_score
)
from .. import crud
from ..nlp.finbert import analyze_finbert_sentiment
from ..nlp.lexicon import get_lexicon
from ..nlp.preprocess import preprocess_text

router = APIRouter(
    tags=["sentiment"],
    responses={404: {"description": "Not found"}},
)


@router.post("/article", response_model=SentimentAnalysisResponse)
async def analyze_article_sentiment_endpoint(
    request: SentimentAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze sentiment of input text using both Loughran-McDonald lexicon and FinBERT.
    
    This endpoint takes raw text input and returns sentiment scores from both
    the Loughran-McDonald financial lexicon and the FinBERT transformer model.
    
    Args:
        request: SentimentAnalysisRequest containing the text to analyze
        db: Database session dependency
        
    Returns:
        SentimentAnalysisResponse: Contains lexicon_score and finbert_score
        
    Raises:
        HTTPException: 400 if text is empty or analysis fails
        HTTPException: 500 if there's an internal server error
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text input cannot be empty")
    
    try:
        # Analyze sentiment using lexicon approach
        lexicon = get_lexicon()
        # Simple tokenization - split by whitespace and clean
        tokens = request.text.lower().split()
        lexicon_score = lexicon.calculate_sentiment_score(tokens)
        
        # Analyze sentiment using FinBERT
        finbert_result = analyze_finbert_sentiment(request.text)
        finbert_score = finbert_result.get("composite_score", 0.0)
        
        return SentimentAnalysisResponse(
            lexicon_score=lexicon_score,
            finbert_score=finbert_score
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error analyzing sentiment: {str(e)}"
        )


@router.get("/latest", response_model=Optional[SentimentAggregateWithAsset])
async def get_latest_sentiment(
    asset: str = Query(..., description="Asset symbol (e.g., BTC, AAPL)"),
    db: Session = Depends(get_db)
):
    """
    Get the latest sentiment aggregate for a specific asset.
    
    Args:
        asset: Asset symbol to get sentiment for
        db: Database session
        
    Returns:
        Latest sentiment aggregate with asset details or None if not found
    """
    try:
        sentiment_aggregate = crud.get_latest_sentiment_by_asset_symbol(db, asset)
        
        if not sentiment_aggregate:
            raise HTTPException(
                status_code=404, 
                detail=f"No sentiment data found for asset: {asset}"
            )
        
        # Load the asset relationship
        asset_obj = crud.get_asset_by_symbol(db, asset)
        if not asset_obj:
            raise HTTPException(
                status_code=404, 
                detail=f"Asset not found: {asset}"
            )
        
        # Create response with asset details
        return SentimentAggregateWithAsset(
            id=sentiment_aggregate.id,
            avg_score=sentiment_aggregate.avg_score,
            timestamp=sentiment_aggregate.timestamp,
            asset=Asset(
                id=asset_obj.id,
                symbol=asset_obj.symbol,
                name=asset_obj.name,
                type=asset_obj.type,
                description=asset_obj.description
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sentiment: {str(e)}")


@router.get("/history", response_model=List[SentimentAggregateWithAsset])
async def get_sentiment_history(
    asset: str = Query(..., description="Asset symbol (e.g., BTC, AAPL)"),
    range: Optional[str] = Query(None, description="Time range: 1h, 24h, 7d, 30d, or custom"),
    start: Optional[datetime] = Query(None, description="Custom start date (ISO format)"),
    end: Optional[datetime] = Query(None, description="Custom end date (ISO format)"),
    db: Session = Depends(get_db)
):
    """
    Get sentiment history for a specific asset over a given time range.
    
    Args:
        asset: Asset symbol to get history for
        range: Predefined time range (1h, 24h, 7d, 30d) or None for custom dates
        start: Custom start date (used if range is None)
        end: Custom end date (used if range is None)
        db: Database session
        
    Returns:
        List of sentiment aggregates with asset details ordered by timestamp
    """
    try:
        # Validate asset exists
        asset_obj = crud.get_asset_by_symbol(db, asset)
        if not asset_obj:
            raise HTTPException(
                status_code=404, 
                detail=f"Asset not found: {asset}"
            )
        
        # Determine date range
        start_date = None
        end_date = None
        
        if range:
            now = datetime.utcnow()
            if range == "1h":
                start_date = now - timedelta(hours=1)
            elif range == "24h":
                start_date = now - timedelta(hours=24)
            elif range == "7d":
                start_date = now - timedelta(days=7)
            elif range == "30d":
                start_date = now - timedelta(days=30)
            else:
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid range. Use: 1h, 24h, 7d, 30d, or provide custom start/end dates"
                )
            end_date = now
        else:
            # Use custom dates
            start_date = start
            end_date = end
        
        # Get sentiment history
        sentiment_history = crud.get_sentiment_history_by_symbol(
            db, asset, start_date, end_date
        )
        
        # Convert to response format with asset details
        response = []
        for sentiment_aggregate in sentiment_history:
            response.append(SentimentAggregateWithAsset(
                id=sentiment_aggregate.id,
                avg_score=sentiment_aggregate.avg_score,
                timestamp=sentiment_aggregate.timestamp,
                asset=Asset(
                    id=asset_obj.id,
                    symbol=asset_obj.symbol,
                    name=asset_obj.name,
                    type=asset_obj.type,
                    description=asset_obj.description
                )
            ))
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sentiment history: {str(e)}")


@router.post("/compute-hourly", response_model=List[SentimentAggregateWithAsset])
async def compute_hourly_aggregates(
    target_hour: Optional[datetime] = Query(None, description="Specific hour to compute (defaults to previous hour)"),
    db: Session = Depends(get_db)
):
    """
    Manually trigger computation of hourly sentiment aggregates.
    
    Args:
        target_hour: Specific hour to compute aggregates for (defaults to previous hour)
        db: Database session
        
    Returns:
        List of created sentiment aggregates with asset details
    """
    try:
        # Compute hourly aggregates
        created_aggregates = crud.compute_hourly_sentiment_averages(db, target_hour)
        
        if not created_aggregates:
            return []
        
        # Convert to response format with asset details
        response = []
        for aggregate in created_aggregates:
            # Get asset details
            asset_obj = db.query(crud.models.Asset).filter(
                crud.models.Asset.id == aggregate.asset_id
            ).first()
            
            if asset_obj:
                response.append(SentimentAggregateWithAsset(
                    id=aggregate.id,
                    avg_score=aggregate.avg_score,
                    timestamp=aggregate.timestamp,
                    asset=Asset(
                        id=asset_obj.id,
                        symbol=asset_obj.symbol,
                        name=asset_obj.name,
                        type=asset_obj.type,
                        description=asset_obj.description
                    )
                ))
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing hourly aggregates: {str(e)}")


@router.get("/assets", response_model=List[Asset])
async def get_assets(
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Get all available assets.
    
    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List of available assets
    """
    try:
        assets = crud.get_assets(db, skip=skip, limit=limit)
        return [Asset(
            id=asset.id,
            symbol=asset.symbol,
            name=asset.name,
            type=asset.type,
            description=asset.description
        ) for asset in assets]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving assets: {str(e)}") 