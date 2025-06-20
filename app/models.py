"""SQLAlchemy models for the TradeEasy backend application.

This module defines the database models for users, assets, articles, sentiments,
sentiment aggregates, watchlists, and alerts with optimized indexes.
"""
import uuid
from datetime import datetime

import sqlalchemy.types as types
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


# Custom UUID type for SQLite compatibility
class GUID(types.TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, otherwise uses
    BLOB or CHAR(36), depending on the dialect.
    """

    impl = types.String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Select the best implementation for the given dialect."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(types.String(36))

    def process_bind_param(self, value, dialect):
        """Process the value before binding it to the statement."""
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        """Process the value when loading from database."""
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value


class User(Base):
    """Model for user accounts."""

    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=True)

    # Define relationships
    watchlists = relationship(
        "Watchlist", back_populates="user", cascade="all, delete-orphan"
    )
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")


class Asset(Base):
    """Model for financial assets that can be tracked."""

    __tablename__ = "assets"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False, index=True)  # stock, forex, crypto, commodity
    description = Column(Text, nullable=True)

    # Define relationships
    sentiment_aggregates = relationship(
        "SentimentAggregate", back_populates="asset", cascade="all, delete-orphan"
    )
    watchlists = relationship(
        "Watchlist", back_populates="asset", cascade="all, delete-orphan"
    )
    alerts = relationship("Alert", back_populates="asset", cascade="all, delete-orphan")

    # Additional indexes for performance
    __table_args__ = (
        Index("idx_asset_symbol_type", "symbol", "type"),
    )


class Article(Base):
    """Model for storing news articles."""

    __tablename__ = "articles"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    source = Column(String(255), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    published_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    url = Column(String(512), nullable=False, unique=True)
    authors = Column(String(512), nullable=True)  # Comma-separated list of authors
    image_url = Column(String(1024), nullable=True)  # URL to the top image
    summary = Column(Text, nullable=True)  # Auto-generated summary of the article

    # Define relationship with Sentiment
    sentiments = relationship(
        "Sentiment", back_populates="article", cascade="all, delete-orphan"
    )

    # Additional indexes for performance
    __table_args__ = (
        Index("idx_article_published_source", "published_at", "source"),
        Index("idx_article_url_hash", "url"),  # For fast deduplication
    )


class Sentiment(Base):
    """Model for storing sentiment analysis results for articles."""

    __tablename__ = "sentiments"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    article_id = Column(GUID(), ForeignKey("articles.id"), nullable=False, index=True)
    lexicon_score = Column(Float)
    finbert_score = Column(Float)

    # Define relationship with Article
    article = relationship("Article", back_populates="sentiments")

    # Additional indexes for performance
    __table_args__ = (
        Index("idx_sentiment_article_scores", "article_id", "lexicon_score", "finbert_score"),
    )


class SentimentAggregate(Base):
    """Model for storing aggregated sentiment scores by asset and time."""

    __tablename__ = "sentiment_aggregates"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    asset_id = Column(GUID(), ForeignKey("assets.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    avg_score = Column(Float, nullable=False)

    # Define relationship with Asset
    asset = relationship("Asset", back_populates="sentiment_aggregates")

    # Performance indexes for frequent queries
    __table_args__ = (
        Index("idx_sentiment_agg_asset_timestamp", "asset_id", "timestamp"),
        Index("idx_sentiment_agg_timestamp_score", "timestamp", "avg_score"),
        Index("idx_sentiment_agg_asset_timestamp_desc", "asset_id", "timestamp"),
    )


class Watchlist(Base):
    """Model for user watchlists."""

    __tablename__ = "watchlists"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    asset_id = Column(GUID(), ForeignKey("assets.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Define relationships
    user = relationship("User", back_populates="watchlists")
    asset = relationship("Asset", back_populates="watchlists")

    # Ensure a user can't add the same asset twice + performance indexes
    __table_args__ = (
        UniqueConstraint("user_id", "asset_id", name="uq_watchlist_user_asset"),
        Index("idx_watchlist_user_created", "user_id", "created_at"),
    )


class Alert(Base):
    """Model for user alerts."""

    __tablename__ = "alerts"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    asset_id = Column(GUID(), ForeignKey("assets.id"), nullable=False, index=True)
    threshold = Column(Float, nullable=False)
    direction = Column(String(10), nullable=False, index=True)  # 'above' or 'below'
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    triggered_at = Column(DateTime, nullable=True, index=True)
    is_active = Column(Boolean, default=True, index=True)

    # Define relationships
    user = relationship("User", back_populates="alerts")
    asset = relationship("Asset", back_populates="alerts")

    # Performance indexes for alert processing
    __table_args__ = (
        Index("idx_alert_user_active", "user_id", "is_active"),
        Index("idx_alert_asset_active", "asset_id", "is_active"),
        Index("idx_alert_triggered", "triggered_at"),
        Index("idx_alert_asset_active_threshold", "asset_id", "is_active", "threshold"),
    )
