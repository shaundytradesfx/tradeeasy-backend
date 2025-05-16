import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import sqlalchemy.types as types

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
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(types.String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value


class Article(Base):
    """Model for storing news articles."""
    __tablename__ = "articles"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    source = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    published_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    url = Column(String(512), nullable=False, unique=True)
    
    # Define relationship with Sentiment
    sentiments = relationship("Sentiment", back_populates="article", cascade="all, delete-orphan")


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
    asset = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    avg_score = Column(Float, nullable=False)
    
    # SQLite doesn't support partitioning, only use this for PostgreSQL
    __table_args__ = ()


class Watchlist(Base):
    """Model for user watchlists."""
    __tablename__ = "watchlists"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), nullable=False)
    asset = Column(String(50), nullable=False)
    
    # Ensure a user can't add the same asset twice
    __table_args__ = (
        UniqueConstraint('user_id', 'asset', name='uq_watchlist_user_asset'),
    )


class Alert(Base):
    """Model for user alerts."""
    __tablename__ = "alerts"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), nullable=False)
    asset = Column(String(50), nullable=False)
    threshold = Column(Float, nullable=False)
    direction = Column(String(10), nullable=False)  # 'above' or 'below'
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    triggered_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
