from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


# Article schemas
class ArticleBase(BaseModel):
    source: str
    title: str
    content: str
    url: str
    authors: Optional[str] = None
    image_url: Optional[str] = None
    summary: Optional[str] = None


class ArticleCreate(ArticleBase):
    published_at: Optional[datetime] = None


class Article(ArticleBase):
    id: UUID
    published_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Sentiment schemas
class SentimentBase(BaseModel):
    lexicon_score: Optional[float] = None
    finbert_score: Optional[float] = None


class SentimentCreate(SentimentBase):
    article_id: UUID


class Sentiment(SentimentBase):
    id: UUID
    article_id: UUID

    model_config = ConfigDict(from_attributes=True)


# SentimentAggregate schemas
class SentimentAggregateBase(BaseModel):
    asset: str
    avg_score: float


class SentimentAggregateCreate(SentimentAggregateBase):
    timestamp: Optional[datetime] = None


class SentimentAggregate(SentimentAggregateBase):
    id: UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# Watchlist schemas
class WatchlistBase(BaseModel):
    asset: str


class WatchlistCreate(WatchlistBase):
    user_id: UUID


class Watchlist(WatchlistBase):
    id: UUID
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)


# Alert schemas
class AlertBase(BaseModel):
    asset: str
    threshold: float
    direction: str = Field(..., description="Either 'above' or 'below'")


class AlertCreate(AlertBase):
    user_id: UUID


class Alert(AlertBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    triggered_at: Optional[datetime] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# Sentiment Analysis Request/Response
class SentimentAnalysisRequest(BaseModel):
    text: str


class SentimentAnalysisResponse(BaseModel):
    lexicon_score: float
    finbert_score: float


# Health Check Response
class HealthCheck(BaseModel):
    status: str = "ok"
