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
import logging

from ..database import get_db
from ..schemas import SentimentAnalysisRequest, SentimentAnalysisResponse, SentimentAggregateWithAsset, Asset, SentimentStreamResponse, SentimentUpdate, SentimentUpdateData, SentimentScores, AggregateUpdate, AggregateAssetData, AlertUpdate, AlertTriggerData
from ..models import Asset as ModelAsset
from ..security import sanitize_text_input, validate_asset_symbol, SecurityError, log_security_event
# Removed heavy imports that load spaCy/PyTorch:
# from ..nlp.lexicon import get_lexicon
# from ..nlp.preprocess import preprocess_text
from .. import crud
# Removed heavy FinBERT import: from ..nlp.finbert import analyze_finbert_sentiment

router = APIRouter(
    tags=["sentiment"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)


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
    
    # Validate and sanitize text input
    try:
        sanitized_text = sanitize_text_input(request.text)
    except SecurityError as e:
        log_security_event("invalid_text_input", {"text_length": len(request.text), "error": str(e)})
        raise HTTPException(status_code=400, detail=f"Invalid text input: {str(e)}")
    
    try:
        # Simple lexicon-based sentiment analysis with lazy loading
        lexicon_score = 0.0
        try:
            # Only import lexicon when actually needed
            from ..nlp.lexicon import get_lexicon
            lexicon = get_lexicon()
            # Simple tokenization - split by whitespace and clean
            tokens = request.text.lower().split()
            lexicon_score = lexicon.calculate_sentiment_score(tokens)
        except Exception as lexicon_error:
            # If lexicon fails, provide a simple fallback
            logger.warning(f"Lexicon analysis failed, using simple fallback: {lexicon_error}")
            # Simple fallback: count positive/negative words
            positive_words = {"good", "great", "excellent", "positive", "up", "gain", "profit", "success", "growth", "strong"}
            negative_words = {"bad", "terrible", "negative", "down", "loss", "fail", "decline", "weak", "poor", "drop"}
            words = sanitized_text.lower().split()
            pos_count = sum(1 for word in words if word in positive_words)
            neg_count = sum(1 for word in words if word in negative_words)
            total_words = len(words)
            lexicon_score = (pos_count - neg_count) / total_words if total_words > 0 else 0.0
        
        # Lazy load FinBERT only when needed to prevent startup blocking
        finbert_score = 0.0
        try:
            # Only import FinBERT when actually needed
            from ..nlp.finbert import analyze_finbert_sentiment
            finbert_result = analyze_finbert_sentiment(sanitized_text)
            finbert_score = finbert_result.get("composite_score", 0.0)
        except Exception as finbert_error:
            # If FinBERT fails, log warning but continue with lexicon score
            logger.warning(f"FinBERT analysis failed, using lexicon only: {finbert_error}")
            finbert_score = 0.0
        
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
        # Validate and sanitize asset symbol
        try:
            validated_asset = validate_asset_symbol(asset)
        except SecurityError as e:
            log_security_event("invalid_asset_symbol", {"asset": asset, "error": str(e)})
            raise HTTPException(status_code=400, detail=f"Invalid asset symbol: {str(e)}")
        
        sentiment_aggregate = crud.get_latest_sentiment_by_asset_symbol(db, validated_asset)
        
        if not sentiment_aggregate:
            raise HTTPException(
                status_code=404, 
                detail=f"No sentiment data found for asset: {validated_asset}"
            )
        
        # Load the asset relationship
        asset_obj = crud.get_asset_by_symbol(db, validated_asset)
        if not asset_obj:
            raise HTTPException(
                status_code=404, 
                detail=f"Asset not found: {validated_asset}"
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
        # Validate and sanitize asset symbol
        try:
            validated_asset = validate_asset_symbol(asset)
        except SecurityError as e:
            log_security_event("invalid_asset_symbol", {"asset": asset, "error": str(e)})
            raise HTTPException(status_code=400, detail=f"Invalid asset symbol: {str(e)}")
        
        # Validate asset exists
        asset_obj = crud.get_asset_by_symbol(db, validated_asset)
        if not asset_obj:
            raise HTTPException(
                status_code=404, 
                detail=f"Asset not found: {validated_asset}"
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


@router.get("/stream", response_model=SentimentStreamResponse)
async def get_sentiment_stream(
    since: Optional[datetime] = Query(None, description="Timestamp to get updates since (ISO format). If not provided, returns data from the last hour."),
    db: Session = Depends(get_db)
):
    """
    Get sentiment updates since a given timestamp for polling clients.
    
    This endpoint provides a REST alternative to WebSocket connections for clients
    that cannot use WebSocket. It returns sentiment data that has been updated
    since the specified timestamp, including real-time triggered alerts.
    
    Args:
        since: Optional timestamp to filter updates from. If None, returns data from last hour.
        db: Database session
        
    Returns:
        SentimentStreamResponse: Contains sentiment updates, aggregates, and triggered alerts
        
    Example:
        GET /api/sentiment/stream?since=2024-01-01T12:00:00Z
        
    Response format matches WebSocket broadcast messages for consistency.
    """
    try:
        # Default to last hour if no timestamp provided
        if since is None:
            since = datetime.utcnow() - timedelta(hours=1)
        
        # Get sentiment aggregates and articles since timestamp
        sentiment_aggregates, articles_with_sentiment = crud.get_sentiment_updates_since(db, since)
        
        # Get triggered alerts since timestamp
        triggered_alerts = crud.get_triggered_alerts_since(db, since)
        
        # Convert sentiment aggregates to response format
        aggregates = []
        for aggregate in sentiment_aggregates:
            asset = crud.get_asset_by_id(db, aggregate.asset_id)
            if asset:
                aggregates.append(AggregateUpdate(
                    type="aggregate_update",
                    asset=AggregateAssetData(
                        symbol=asset.symbol,
                        avg_sentiment=aggregate.avg_score,
                        article_count=0,  # This would need to be computed from articles
                        time_period="1h"
                    ),
                    sentiment_category="positive" if aggregate.avg_score > 0.1 else "negative" if aggregate.avg_score < -0.1 else "neutral",
                    timestamp=aggregate.timestamp.isoformat(),
                    metadata={
                        "aggregate_id": str(aggregate.id),
                        "asset_id": str(asset.id),
                        "computed_at": aggregate.timestamp.isoformat()
                    }
                ))
        
        # Convert articles to sentiment updates
        updates = []
        for article, sentiment in articles_with_sentiment:
            updates.append(SentimentUpdate(
                type="sentiment_update",
                article=SentimentUpdateData(
                    id=str(article.id),
                    title=article.title,
                    source=article.source,
                    url=article.url or "",
                    published_at=article.published_at.isoformat() if article.published_at else datetime.utcnow().isoformat(),
                    asset_class="unknown"
                ),
                sentiment=SentimentScores(
                    lexicon_score=sentiment.lexicon_score or 0.0,
                    finbert_score=sentiment.finbert_score or 0.0,
                    overall_sentiment="positive" if (sentiment.finbert_score or 0.0) > 0.1 else "negative" if (sentiment.finbert_score or 0.0) < -0.1 else "neutral"
                ),
                timestamp=article.published_at.isoformat() if article.published_at else datetime.utcnow().isoformat(),
                metadata={
                    "article_id": str(article.id),
                    "sentiment_id": str(sentiment.id),
                    "processed_at": datetime.utcnow().isoformat()
                }
            ))
        
        # Convert triggered alerts to response format
        alerts = []
        for alert in triggered_alerts:
            asset = crud.get_asset_by_id(db, alert.asset_id)
            # Get the current sentiment value that triggered the alert
            current_sentiment = 0.0
            if asset:
                latest_sentiment = crud.get_latest_sentiment_by_asset_symbol(db, asset.symbol)
                if latest_sentiment:
                    current_sentiment = latest_sentiment.avg_score
            
            alerts.append(AlertUpdate(
                type="alert_triggered",
                alert=AlertTriggerData(
                    id=str(alert.id),
                    asset_symbol=asset.symbol if asset else "unknown",
                    threshold=alert.threshold,
                    direction=alert.direction,
                    current_value=current_sentiment,
                    user_id=str(alert.user_id)
                ),
                timestamp=alert.triggered_at.isoformat() if alert.triggered_at else datetime.utcnow().isoformat(),
                metadata={
                    "alert_id": str(alert.id),
                    "asset_id": str(alert.asset_id),
                    "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None
                }
            ))
        
        return SentimentStreamResponse(
            updates=updates,
            aggregates=aggregates,
            alerts=alerts,
            metadata={
                "since": since.isoformat(),
                "total_updates": len(updates),
                "total_aggregates": len(aggregates),
                "total_alerts": len(alerts),
                "generated_at": datetime.utcnow().isoformat(),
                "status": "success"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in sentiment stream endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving sentiment stream: {str(e)}") 