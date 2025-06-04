"""
Search API endpoints.

This module provides endpoints for searching articles with full-text search
capabilities and sentiment analysis integration.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import SearchResponse, ArticleWithSentiment, Article, Sentiment
from .. import crud

router = APIRouter(
    prefix="/search",
    tags=["search"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=SearchResponse)
async def search_articles(
    q: str = Query(..., description="Search query string", min_length=1),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Search articles using full-text search with sentiment analysis data.
    
    This endpoint supports both PostgreSQL Full-Text Search (when available) 
    and SQLite LIKE queries as fallback. Results include article content 
    and associated sentiment scores.
    
    Args:
        q: Search query string (e.g., "Fed rate decision", "Bitcoin price")
        skip: Number of records to skip for pagination  
        limit: Maximum number of records to return (1-1000)
        db: Database session dependency
        
    Returns:
        SearchResponse: Contains matching articles with sentiment data and pagination info
        
    Raises:
        HTTPException: 400 if query is empty or invalid
        HTTPException: 500 if there's an internal server error
    """
    try:
        # Validate query
        if not q or not q.strip():
            raise HTTPException(status_code=400, detail="Search query cannot be empty")
        
        # Get search results with sentiment data
        search_results = crud.search_articles_with_sentiment(db, q.strip(), skip, limit)
        
        # Get total count for pagination
        total_count = crud.count_search_results(db, q.strip())
        
        # Convert to response format
        results = []
        for article, sentiments in search_results:
            # Convert SQLAlchemy objects to Pydantic models
            article_dict = {
                'id': article.id,
                'source': article.source,
                'title': article.title,
                'content': article.content,
                'url': article.url,
                'published_at': article.published_at,
                'authors': article.authors,
                'image_url': article.image_url,
                'summary': article.summary
            }
            
            sentiment_dicts = []
            for sentiment in sentiments:
                sentiment_dict = {
                    'id': sentiment.id,
                    'article_id': sentiment.article_id,
                    'lexicon_score': sentiment.lexicon_score,
                    'finbert_score': sentiment.finbert_score
                }
                sentiment_dicts.append(Sentiment(**sentiment_dict))
            
            results.append(ArticleWithSentiment(
                article=Article(**article_dict),
                sentiments=sentiment_dicts
            ))
        
        # Check if there are more results
        has_more = (skip + limit) < total_count
        
        return SearchResponse(
            results=results,
            total_count=total_count,
            query=q.strip(),
            skip=skip,
            limit=limit,
            has_more=has_more
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error performing search: {str(e)}"
        )


@router.get("/articles", response_model=List[Article])
async def search_articles_only(
    q: str = Query(..., description="Search query string", min_length=1),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Search articles without sentiment data for faster responses.
    
    This endpoint provides a lightweight search that returns only article data
    without sentiment analysis scores, useful for quick searches or when 
    sentiment data is not needed.
    
    Args:
        q: Search query string
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return (1-1000)
        db: Database session dependency
        
    Returns:
        List[Article]: Matching articles without sentiment data
        
    Raises:
        HTTPException: 400 if query is empty or invalid
        HTTPException: 500 if there's an internal server error
    """
    try:
        # Validate query
        if not q or not q.strip():
            raise HTTPException(status_code=400, detail="Search query cannot be empty")
        
        # Get search results
        articles = crud.search_articles(db, q.strip(), skip, limit)
        
        # Convert to response format
        results = []
        for article in articles:
            article_dict = {
                'id': article.id,
                'source': article.source,
                'title': article.title,
                'content': article.content,
                'url': article.url,
                'published_at': article.published_at,
                'authors': article.authors,
                'image_url': article.image_url,
                'summary': article.summary
            }
            results.append(Article(**article_dict))
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error performing search: {str(e)}"
        )


@router.post("/index")
async def create_search_index(
    db: Session = Depends(get_db)
):
    """
    Create or update the full-text search index for better performance.
    
    This endpoint creates a PostgreSQL GIN index for full-text search
    when using PostgreSQL. For SQLite, this operation is a no-op.
    
    Args:
        db: Database session dependency
        
    Returns:
        dict: Status of index creation
        
    Raises:
        HTTPException: 500 if index creation fails
    """
    try:
        success = crud.create_postgresql_fts_index(db)
        
        if success:
            return {
                "status": "success",
                "message": "PostgreSQL FTS index created successfully",
                "database": "postgresql"
            }
        else:
            return {
                "status": "skipped", 
                "message": "Index creation skipped - not using PostgreSQL",
                "database": db.bind.dialect.name
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating search index: {str(e)}"
        )


@router.get("/stats")
async def get_search_stats(
    db: Session = Depends(get_db)
):
    """
    Get search-related statistics and information.
    
    This endpoint provides information about the search capabilities,
    database type, and article counts for monitoring and debugging.
    
    Args:
        db: Database session dependency
        
    Returns:
        dict: Search statistics and configuration info
    """
    try:
        total_articles = crud.get_articles(db, skip=0, limit=1)
        total_count = db.query(crud.models.Article).count()
        
        dialect_name = db.bind.dialect.name
        search_type = "PostgreSQL Full-Text Search" if dialect_name == "postgresql" else "SQLite LIKE Search"
        
        return {
            "database_type": dialect_name,
            "search_type": search_type,
            "total_articles": total_count,
            "supports_fts": dialect_name == "postgresql",
            "status": "active"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving search stats: {str(e)}"
        ) 