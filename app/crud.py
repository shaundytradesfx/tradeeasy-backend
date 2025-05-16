from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timedelta
from typing import List, Optional

from . import models, schemas


# Article CRUD operations
def get_article(db: Session, article_id: UUID):
    return db.query(models.Article).filter(models.Article.id == article_id).first()


def get_article_by_url(db: Session, url: str):
    return db.query(models.Article).filter(models.Article.url == url).first()


def get_articles(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Article).order_by(models.Article.published_at.desc()).offset(skip).limit(limit).all()


def create_article(db: Session, article: schemas.ArticleCreate):
    db_article = models.Article(
        source=article.source,
        title=article.title,
        content=article.content,
        url=article.url,
        published_at=article.published_at or datetime.utcnow()
    )
    db.add(db_article)
    db.commit()
    db.refresh(db_article)
    return db_article


# Sentiment CRUD operations
def get_sentiment(db: Session, sentiment_id: UUID):
    return db.query(models.Sentiment).filter(models.Sentiment.id == sentiment_id).first()


def get_sentiments_by_article(db: Session, article_id: UUID):
    return db.query(models.Sentiment).filter(models.Sentiment.article_id == article_id).all()


def create_sentiment(db: Session, sentiment: schemas.SentimentCreate):
    db_sentiment = models.Sentiment(**sentiment.dict())
    db.add(db_sentiment)
    db.commit()
    db.refresh(db_sentiment)
    return db_sentiment


# SentimentAggregate CRUD operations
def get_sentiment_aggregate(db: Session, aggregate_id: UUID):
    return db.query(models.SentimentAggregate).filter(models.SentimentAggregate.id == aggregate_id).first()


def get_sentiment_history(db: Session, asset: str, time_range: Optional[int] = None):
    """
    Get sentiment history for a specific asset over the last time_range hours.
    If time_range is None, return all history.
    """
    query = db.query(models.SentimentAggregate).filter(models.SentimentAggregate.asset == asset)
    
    if time_range:
        cutoff_time = datetime.utcnow() - timedelta(hours=time_range)
        query = query.filter(models.SentimentAggregate.timestamp >= cutoff_time)
    
    return query.order_by(models.SentimentAggregate.timestamp.asc()).all()


def create_sentiment_aggregate(db: Session, aggregate: schemas.SentimentAggregateCreate):
    db_aggregate = models.SentimentAggregate(
        asset=aggregate.asset,
        avg_score=aggregate.avg_score,
        timestamp=aggregate.timestamp or datetime.utcnow()
    )
    db.add(db_aggregate)
    db.commit()
    db.refresh(db_aggregate)
    return db_aggregate


# Watchlist CRUD operations
def get_watchlist(db: Session, watchlist_id: UUID):
    return db.query(models.Watchlist).filter(models.Watchlist.id == watchlist_id).first()


def get_watchlists_by_user(db: Session, user_id: UUID):
    return db.query(models.Watchlist).filter(models.Watchlist.user_id == user_id).all()


def create_watchlist(db: Session, watchlist: schemas.WatchlistCreate):
    db_watchlist = models.Watchlist(**watchlist.dict())
    db.add(db_watchlist)
    db.commit()
    db.refresh(db_watchlist)
    return db_watchlist


def delete_watchlist(db: Session, watchlist_id: UUID):
    db_watchlist = db.query(models.Watchlist).filter(models.Watchlist.id == watchlist_id).first()
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
        asset=alert.asset,
        threshold=alert.threshold,
        direction=alert.direction,
        created_at=datetime.utcnow(),
        is_active=True
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
