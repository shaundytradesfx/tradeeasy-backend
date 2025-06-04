from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from . import models, schemas


# Article CRUD operations
def get_article(db: Session, article_id: UUID):
    return db.query(models.Article).filter(models.Article.id == article_id).first()


def get_article_by_url(db: Session, url: str):
    return db.query(models.Article).filter(models.Article.url == url).first()


def get_articles(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(models.Article)
        .order_by(models.Article.published_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_article(db: Session, article: schemas.ArticleCreate):
    db_article = models.Article(
        source=article.source,
        title=article.title,
        content=article.content,
        url=article.url,
        published_at=article.published_at or datetime.utcnow(),
        authors=article.authors,
        image_url=article.image_url,
        summary=article.summary,
    )
    db.add(db_article)
    db.commit()
    db.refresh(db_article)
    return db_article


def upsert_article(db: Session, article: schemas.ArticleCreate) -> Tuple[models.Article, bool]:
    """
    Upsert an article - create if it doesn't exist, update if it does.
    Uses URL for deduplication.
    
    Args:
        db: Database session
        article: Article data to create or update
        
    Returns:
        Tuple of (article object, was_created boolean)
    """
    # Check if article with the same URL already exists
    existing_article = get_article_by_url(db, article.url)
    
    created = False
    
    if existing_article:
        # Update existing article
        existing_article.title = article.title
        existing_article.content = article.content
        existing_article.source = article.source
        
        # Only update published_at if the new date is provided and is earlier
        if article.published_at and (
            not existing_article.published_at or 
            article.published_at < existing_article.published_at
        ):
            existing_article.published_at = article.published_at
            
        # Update optional fields if provided
        if article.authors:
            existing_article.authors = article.authors
        if article.image_url:
            existing_article.image_url = article.image_url
        if article.summary:
            existing_article.summary = article.summary
            
        db.commit()
        db.refresh(existing_article)
        return existing_article, created
    else:
        # Create new article
        created = True
        return create_article(db, article), created


def get_articles_by_date_range(db: Session, start_date: datetime, end_date: datetime, 
                              skip: int = 0, limit: int = 100):
    """
    Get articles published within a specific date range.
    
    Args:
        db: Database session
        start_date: Start date for the range
        end_date: End date for the range
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of articles within the date range
    """
    return (
        db.query(models.Article)
        .filter(models.Article.published_at >= start_date)
        .filter(models.Article.published_at <= end_date)
        .order_by(models.Article.published_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


# Sentiment CRUD operations
def get_sentiment(db: Session, sentiment_id: UUID):
    return (
        db.query(models.Sentiment).filter(models.Sentiment.id == sentiment_id).first()
    )


def get_sentiments_by_article(db: Session, article_id: UUID):
    return (
        db.query(models.Sentiment)
        .filter(models.Sentiment.article_id == article_id)
        .all()
    )


def create_sentiment(db: Session, sentiment: schemas.SentimentCreate):
    db_sentiment = models.Sentiment(**sentiment.model_dump())
    db.add(db_sentiment)
    db.commit()
    db.refresh(db_sentiment)
    return db_sentiment


# SentimentAggregate CRUD operations
def get_sentiment_aggregate(db: Session, aggregate_id: UUID):
    return (
        db.query(models.SentimentAggregate)
        .filter(models.SentimentAggregate.id == aggregate_id)
        .first()
    )


def get_sentiment_history_by_asset_id(db: Session, asset_id: UUID, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    """
    Get sentiment history for a specific asset by asset_id with optional date range.
    
    Args:
        db: Database session
        asset_id: UUID of the asset
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        
    Returns:
        List of SentimentAggregate objects ordered by timestamp
    """
    query = db.query(models.SentimentAggregate).filter(
        models.SentimentAggregate.asset_id == asset_id
    )

    if start_date:
        query = query.filter(models.SentimentAggregate.timestamp >= start_date)
    
    if end_date:
        query = query.filter(models.SentimentAggregate.timestamp <= end_date)

    return query.order_by(models.SentimentAggregate.timestamp.asc()).all()


def get_sentiment_history_by_symbol(db: Session, symbol: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    """
    Get sentiment history for a specific asset by symbol with optional date range.
    
    Args:
        db: Database session
        symbol: Asset symbol (e.g., 'BTC', 'AAPL')
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        
    Returns:
        List of SentimentAggregate objects ordered by timestamp
    """
    query = (
        db.query(models.SentimentAggregate)
        .join(models.Asset)
        .filter(models.Asset.symbol == symbol)
    )

    if start_date:
        query = query.filter(models.SentimentAggregate.timestamp >= start_date)
    
    if end_date:
        query = query.filter(models.SentimentAggregate.timestamp <= end_date)

    return query.order_by(models.SentimentAggregate.timestamp.asc()).all()


def get_sentiment_history(db: Session, asset: str, time_range: Optional[int] = None):
    """
    Get sentiment history for a specific asset over the last time_range hours.
    If time_range is None, return all history.
    
    DEPRECATED: Use get_sentiment_history_by_symbol instead.
    """
    return get_sentiment_history_by_symbol(
        db, 
        asset, 
        start_date=datetime.utcnow() - timedelta(hours=time_range) if time_range else None
    )


def create_sentiment_aggregate(db: Session, aggregate: schemas.SentimentAggregateCreate):
    """
    Create a new sentiment aggregate record.
    
    Args:
        db: Database session
        aggregate: SentimentAggregateCreate schema with asset_id and avg_score
        
    Returns:
        Created SentimentAggregate object
    """
    db_aggregate = models.SentimentAggregate(
        asset_id=aggregate.asset_id,
        avg_score=aggregate.avg_score,
        timestamp=aggregate.timestamp or datetime.utcnow(),
    )
    db.add(db_aggregate)
    db.commit()
    db.refresh(db_aggregate)
    return db_aggregate


def compute_hourly_sentiment_averages(db: Session, target_hour: Optional[datetime] = None):
    """
    Compute hourly sentiment averages for all assets and store them in SentimentAggregate table.
    
    Args:
        db: Database session
        target_hour: Specific hour to compute averages for (defaults to previous hour)
        
    Returns:
        List of created SentimentAggregate objects
    """
    from sqlalchemy import func, and_
    
    if target_hour is None:
        # Default to the previous complete hour
        now = datetime.utcnow()
        target_hour = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    
    # Calculate the hour range
    hour_start = target_hour
    hour_end = hour_start + timedelta(hours=1)
    
    # Query to get average sentiment scores per asset for the target hour
    # This joins articles -> sentiments and groups by asset mentions in articles
    # For now, we'll use a simplified approach based on article content analysis
    
    # Get all articles published in the target hour
    articles_in_hour = (
        db.query(models.Article)
        .filter(
            and_(
                models.Article.published_at >= hour_start,
                models.Article.published_at < hour_end
            )
        )
        .all()
    )
    
    if not articles_in_hour:
        return []
    
    # Get all sentiments for these articles
    article_ids = [article.id for article in articles_in_hour]
    sentiments = (
        db.query(models.Sentiment)
        .filter(models.Sentiment.article_id.in_(article_ids))
        .all()
    )
    
    if not sentiments:
        return []
    
    # For now, create a general market sentiment aggregate
    # In a real implementation, you'd analyze article content to determine which assets they mention
    avg_lexicon = sum(s.lexicon_score for s in sentiments if s.lexicon_score is not None) / len([s for s in sentiments if s.lexicon_score is not None]) if any(s.lexicon_score is not None for s in sentiments) else 0.0
    avg_finbert = sum(s.finbert_score for s in sentiments if s.finbert_score is not None) / len([s for s in sentiments if s.finbert_score is not None]) if any(s.finbert_score is not None for s in sentiments) else 0.0
    
    # Use the average of both scores
    combined_avg = (avg_lexicon + avg_finbert) / 2 if (avg_lexicon != 0.0 or avg_finbert != 0.0) else 0.0
    
    # Get or create default assets
    default_assets = ['BTC', 'ETH', 'AAPL', 'TSLA', 'EUR/USD']
    created_aggregates = []
    
    for symbol in default_assets:
        # Get or create asset
        asset = db.query(models.Asset).filter(models.Asset.symbol == symbol).first()
        if not asset:
            asset = models.Asset(
                symbol=symbol,
                name=f"{symbol} Asset",
                type="crypto" if symbol in ['BTC', 'ETH'] else "stock" if symbol in ['AAPL', 'TSLA'] else "forex"
            )
            db.add(asset)
            db.commit()
            db.refresh(asset)
        
        # Check if aggregate already exists for this hour
        existing = (
            db.query(models.SentimentAggregate)
            .filter(
                and_(
                    models.SentimentAggregate.asset_id == asset.id,
                    models.SentimentAggregate.timestamp >= hour_start,
                    models.SentimentAggregate.timestamp < hour_end
                )
            )
            .first()
        )
        
        if not existing:
            # Create new aggregate
            aggregate = models.SentimentAggregate(
                asset_id=asset.id,
                avg_score=combined_avg,
                timestamp=hour_start
            )
            db.add(aggregate)
            created_aggregates.append(aggregate)
    
    if created_aggregates:
        db.commit()
        for agg in created_aggregates:
            db.refresh(agg)
    
    return created_aggregates


def get_latest_sentiment_by_asset_symbol(db: Session, symbol: str):
    """
    Get the latest sentiment aggregate for a specific asset symbol.
    
    Args:
        db: Database session
        symbol: Asset symbol (e.g., 'BTC', 'AAPL')
        
    Returns:
        Latest SentimentAggregate object or None
    """
    return (
        db.query(models.SentimentAggregate)
        .join(models.Asset)
        .filter(models.Asset.symbol == symbol)
        .order_by(models.SentimentAggregate.timestamp.desc())
        .first()
    )


def get_assets(db: Session, skip: int = 0, limit: int = 100):
    """
    Get all assets with pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of Asset objects
    """
    return db.query(models.Asset).offset(skip).limit(limit).all()


def get_asset_by_symbol(db: Session, symbol: str):
    """
    Get an asset by its symbol.
    
    Args:
        db: Database session
        symbol: Asset symbol (e.g., 'BTC', 'AAPL')
        
    Returns:
        Asset object or None
    """
    return db.query(models.Asset).filter(models.Asset.symbol == symbol).first()


def create_asset(db: Session, symbol: str, name: str, asset_type: str, description: Optional[str] = None):
    """
    Create a new asset.
    
    Args:
        db: Database session
        symbol: Asset symbol (e.g., 'BTC', 'AAPL')
        name: Asset name
        asset_type: Type of asset (stock, crypto, forex, commodity)
        description: Optional description
        
    Returns:
        Created Asset object
    """
    db_asset = models.Asset(
        symbol=symbol,
        name=name,
        type=asset_type,
        description=description
    )
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset


# Watchlist CRUD operations
def get_watchlist(db: Session, watchlist_id: UUID):
    return (
        db.query(models.Watchlist).filter(models.Watchlist.id == watchlist_id).first()
    )


def get_watchlists_by_user(db: Session, user_id: UUID):
    return db.query(models.Watchlist).filter(models.Watchlist.user_id == user_id).all()


def create_watchlist(db: Session, watchlist: schemas.WatchlistCreate):
    db_watchlist = models.Watchlist(**watchlist.model_dump())
    db.add(db_watchlist)
    db.commit()
    db.refresh(db_watchlist)
    return db_watchlist


def delete_watchlist(db: Session, watchlist_id: UUID):
    db_watchlist = (
        db.query(models.Watchlist).filter(models.Watchlist.id == watchlist_id).first()
    )
    if db_watchlist:
        db.delete(db_watchlist)
        db.commit()
    return db_watchlist


# Alert CRUD operations
def get_alert(db: Session, alert_id: UUID):
    return db.query(models.Alert).filter(models.Alert.id == alert_id).first()


def get_alerts_by_user(db: Session, user_id: UUID, active_only: bool = False):
    query = db.query(models.Alert).filter(models.Alert.user_id == user_id)
    if active_only:
        query = query.filter(models.Alert.is_active == True)
    return query.all()


def create_alert(db: Session, alert: schemas.AlertCreate):
    db_alert = models.Alert(
        user_id=alert.user_id,
        asset_id=alert.asset_id,
        threshold=alert.threshold,
        direction=alert.direction,
        created_at=datetime.utcnow(),
        is_active=True,
    )
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert


def update_alert_triggered(db: Session, alert_id: UUID):
    db_alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if db_alert:
        db_alert.triggered_at = datetime.utcnow()
        db_alert.is_active = False
        db.commit()
        db.refresh(db_alert)
    return db_alert


def delete_alert(db: Session, alert_id: UUID):
    db_alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if db_alert:
        db.delete(db_alert)
        db.commit()
    return db_alert


# Search CRUD operations
def search_articles_postgresql(db: Session, query: str, skip: int = 0, limit: int = 100):
    """
    Search articles using PostgreSQL Full-Text Search.
    
    Args:
        db: Database session
        query: Search query string
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of articles matching the search query with relevance ranking
    """
    from sqlalchemy import text, func
    
    # Use PostgreSQL FTS with to_tsvector and plainto_tsquery
    # This provides better relevance ranking and search capabilities
    search_stmt = text("""
        SELECT articles.*, 
               ts_rank(to_tsvector('english', articles.content || ' ' || articles.title), 
                      plainto_tsquery('english', :query)) as rank
        FROM articles 
        WHERE to_tsvector('english', articles.content || ' ' || articles.title) 
              @@ plainto_tsquery('english', :query)
        ORDER BY rank DESC, articles.published_at DESC
        OFFSET :skip LIMIT :limit
    """)
    
    result = db.execute(search_stmt, {"query": query, "skip": skip, "limit": limit})
    
    # Convert to Article model instances
    articles = []
    for row in result.fetchall():
        article = models.Article(
            id=row.id,
            source=row.source,
            title=row.title,
            content=row.content,
            published_at=row.published_at,
            url=row.url,
            authors=row.authors,
            image_url=row.image_url,
            summary=row.summary
        )
        articles.append(article)
    
    return articles


def search_articles_sqlite(db: Session, query: str, skip: int = 0, limit: int = 100):
    """
    Search articles using SQLite LIKE queries as fallback.
    
    Args:
        db: Database session
        query: Search query string
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of articles matching the search query
    """
    # Split query into words for better matching
    query_words = query.strip().split()
    query_conditions = []
    
    # Create LIKE conditions for each word
    for word in query_words:
        like_pattern = f"%{word}%"
        query_conditions.append(
            (models.Article.content.ilike(like_pattern)) |
            (models.Article.title.ilike(like_pattern))
        )
    
    # Combine all conditions with AND logic
    if query_conditions:
        combined_condition = query_conditions[0]
        for condition in query_conditions[1:]:
            combined_condition = combined_condition & condition
        
        return (
            db.query(models.Article)
            .filter(combined_condition)
            .order_by(models.Article.published_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    else:
        return []


def search_articles(db: Session, query: str, skip: int = 0, limit: int = 100):
    """
    Search articles using the best available method based on database type.
    
    Args:
        db: Database session
        query: Search query string
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of articles matching the search query
    """
    if not query or not query.strip():
        return []
    
    # Detect database dialect
    dialect_name = db.bind.dialect.name
    
    try:
        if dialect_name == "postgresql":
            return search_articles_postgresql(db, query, skip, limit)
        else:
            return search_articles_sqlite(db, query, skip, limit)
    except Exception as e:
        # Fallback to SQLite search if PostgreSQL FTS fails
        print(f"Search failed with {dialect_name}, falling back to SQLite search: {e}")
        return search_articles_sqlite(db, query, skip, limit)


def search_articles_with_sentiment(db: Session, query: str, skip: int = 0, limit: int = 100):
    """
    Search articles and include their sentiment analysis data.
    
    Args:
        db: Database session
        query: Search query string
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of tuples containing (article, sentiment_list)
    """
    articles = search_articles(db, query, skip, limit)
    
    results = []
    for article in articles:
        # Get sentiment data for this article
        sentiments = get_sentiments_by_article(db, article.id)
        results.append((article, sentiments))
    
    return results


def count_search_results(db: Session, query: str):
    """
    Count total number of articles matching a search query.
    
    Args:
        db: Database session
        query: Search query string
        
    Returns:
        Total count of matching articles
    """
    if not query or not query.strip():
        return 0
    
    dialect_name = db.bind.dialect.name
    
    try:
        if dialect_name == "postgresql":
            # Use PostgreSQL FTS for counting
            from sqlalchemy import text
            count_stmt = text("""
                SELECT COUNT(*) 
                FROM articles 
                WHERE to_tsvector('english', articles.content || ' ' || articles.title) 
                      @@ plainto_tsquery('english', :query)
            """)
            result = db.execute(count_stmt, {"query": query})
            return result.scalar()
        else:
            # Use SQLite LIKE for counting
            query_words = query.strip().split()
            query_conditions = []
            
            for word in query_words:
                like_pattern = f"%{word}%"
                query_conditions.append(
                    (models.Article.content.ilike(like_pattern)) |
                    (models.Article.title.ilike(like_pattern))
                )
            
            if query_conditions:
                combined_condition = query_conditions[0]
                for condition in query_conditions[1:]:
                    combined_condition = combined_condition & condition
                
                return db.query(models.Article).filter(combined_condition).count()
            else:
                return 0
    except Exception as e:
        print(f"Count search failed: {e}")
        return 0


def create_postgresql_fts_index(db: Session):
    """
    Create PostgreSQL Full-Text Search index for better performance.
    Only works with PostgreSQL databases.
    
    Args:
        db: Database session
        
    Returns:
        True if index was created successfully, False otherwise
    """
    if db.bind.dialect.name != "postgresql":
        print("FTS index creation skipped - not using PostgreSQL")
        return False
    
    try:
        from sqlalchemy import text
        
        # Create GIN index for FTS
        index_stmt = text("""
            CREATE INDEX IF NOT EXISTS idx_articles_fts 
            ON articles USING gin(to_tsvector('english', content || ' ' || title))
        """)
        
        db.execute(index_stmt)
        db.commit()
        print("PostgreSQL FTS index created successfully")
        return True
        
    except Exception as e:
        print(f"Failed to create PostgreSQL FTS index: {e}")
        db.rollback()
        return False


# User CRUD operations
def get_user(db: Session, user_id: UUID):
    """Get user by ID."""
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str):
    """Get user by username."""
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str):
    """Get user by email."""
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate):
    """Create a new user."""
    import hashlib
    
    # Hash password (simple hash for demo - use proper hashing in production)
    password_hash = hashlib.sha256(user.password.encode()).hexdigest()
    
    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=password_hash,
        created_at=datetime.utcnow()
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_users(db: Session, skip: int = 0, limit: int = 100):
    """Get all users with pagination."""
    return db.query(models.User).offset(skip).limit(limit).all()


# Enhanced asset CRUD operations
def create_asset(db: Session, asset: schemas.AssetCreate):
    """Create a new asset from schema."""
    db_asset = models.Asset(
        symbol=asset.symbol,
        name=asset.name,
        type=asset.type,
        description=asset.description
    )
    
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset


def get_asset_by_id(db: Session, asset_id: UUID):
    """Get asset by ID."""
    return db.query(models.Asset).filter(models.Asset.id == asset_id).first()


# Alert checking functions for ingestion
def check_and_trigger_alerts(db: Session, asset_symbol: str, sentiment_score: float):
    """
    Check if sentiment score crosses any alert thresholds and trigger alerts.
    
    Args:
        db: Database session
        asset_symbol: Symbol of the asset (e.g., 'AAPL', 'BTC')
        sentiment_score: Current sentiment score
        
    Returns:
        List of triggered alert IDs
    """
    # Get asset by symbol
    asset = get_asset_by_symbol(db, asset_symbol)
    if not asset:
        return []
    
    # Get all active alerts for this asset
    active_alerts = (
        db.query(models.Alert)
        .filter(
            models.Alert.asset_id == asset.id,
            models.Alert.is_active == True,
            models.Alert.triggered_at == None
        )
        .all()
    )
    
    triggered_alerts = []
    
    for alert in active_alerts:
        should_trigger = False
        
        if alert.direction == "above" and sentiment_score >= alert.threshold:
            should_trigger = True
        elif alert.direction == "below" and sentiment_score <= alert.threshold:
            should_trigger = True
        
        if should_trigger:
            # Update alert as triggered
            alert.triggered_at = datetime.utcnow()
            db.commit()
            triggered_alerts.append(alert.id)
    
    return triggered_alerts


def get_triggered_alerts(db: Session, user_id: UUID = None, limit: int = 50):
    """Get recently triggered alerts."""
    query = db.query(models.Alert).filter(models.Alert.triggered_at != None)
    
    if user_id:
        query = query.filter(models.Alert.user_id == user_id)
    
    return (
        query
        .order_by(models.Alert.triggered_at.desc())
        .limit(limit)
        .all()
    )


def reset_alert(db: Session, alert_id: UUID):
    """Reset an alert to active state (clear triggered_at)."""
    alert = get_alert(db, alert_id)
    if alert:
        alert.triggered_at = None
        alert.is_active = True
        db.commit()
        return alert
    return None
