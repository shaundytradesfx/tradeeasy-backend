"""SQLAlchemy models for the TradeEasy backend application.

This module defines the database models for users, assets, articles, sentiments,
sentiment aggregates, watchlists, and alerts.
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
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
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
    symbol = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # stock, forex, crypto, commodity
    description = Column(Text, nullable=True)

    # Define relationships
    sentiment_aggregates = relationship(
        "SentimentAggregate", back_populates="asset", cascade="all, delete-orphan"
    )
    watchlists = relationship(
        "Watchlist", back_populates="asset", cascade="all, delete-orphan"
    )
    alerts = relationship("Alert", back_populates="asset", cascade="all, delete-orphan")


class Article(Base):
    """Model for storing news articles."""

    __tablename__ = "articles"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    source = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    published_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    url = Column(String(512), nullable=False, unique=True)
    authors = Column(String(512), nullable=True)  # Comma-separated list of authors
    image_url = Column(String(1024), nullable=True)  # URL to the top image
    summary = Column(Text, nullable=True)  # Auto-generated summary of the article

    # Define relationship with Sentiment
    sentiments = relationship(
        "Sentiment", back_populates="article", cascade="all, delete-orphan"
    )


class Sentiment(Base):
    """Model for storing sentiment analysis results for articles."""

    __tablename__ = "sentiments"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    article_id = Column(GUID(), ForeignKey("articles.id"), nullable=False)
    lexicon_score = Column(Float)
    finbert_score = Column(Float)

    # Define relationship with Article
    article = relationship("Article", back_populates="sentiments")


class SentimentAggregate(Base):
    """Model for storing aggregated sentiment scores by asset and time."""

    __tablename__ = "sentiment_aggregates"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    asset_id = Column(GUID(), ForeignKey("assets.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    avg_score = Column(Float, nullable=False)

    # Define relationship with Asset
    asset = relationship("Asset", back_populates="sentiment_aggregates")

    # SQLite doesn't support partitioning, only use this for PostgreSQL
    __table_args__ = ()


class Watchlist(Base):
    """Model for user watchlists."""

    __tablename__ = "watchlists"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    asset_id = Column(GUID(), ForeignKey("assets.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Define relationships
    user = relationship("User", back_populates="watchlists")
    asset = relationship("Asset", back_populates="watchlists")

    # Ensure a user can't add the same asset twice
    __table_args__ = (
        UniqueConstraint("user_id", "asset_id", name="uq_watchlist_user_asset"),
    )


class Alert(Base):
    """Model for user alerts."""

    __tablename__ = "alerts"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    asset_id = Column(GUID(), ForeignKey("assets.id"), nullable=False)
    threshold = Column(Float, nullable=False)
    direction = Column(String(10), nullable=False)  # 'above' or 'below'
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    triggered_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Define relationships
    user = relationship("User", back_populates="alerts")
    asset = relationship("Asset", back_populates="alerts")
