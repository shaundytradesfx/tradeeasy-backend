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
    avg_score: float


class SentimentAggregateCreate(SentimentAggregateBase):
    asset_id: UUID
    timestamp: Optional[datetime] = None


class SentimentAggregate(SentimentAggregateBase):
    id: UUID
    asset_id: UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# Asset schemas
class AssetBase(BaseModel):
    symbol: str
    name: str
    type: str
    description: Optional[str] = None


class AssetCreate(AssetBase):
    pass


class Asset(AssetBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


# Enhanced SentimentAggregate with Asset details for API responses
class SentimentAggregateWithAsset(SentimentAggregateBase):
    id: UUID
    timestamp: datetime
    asset: Asset

    model_config = ConfigDict(from_attributes=True)


# User schemas
class UserBase(BaseModel):
    username: str
    email: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Watchlist schemas (updated)
class WatchlistBase(BaseModel):
    asset_id: UUID


class WatchlistCreate(WatchlistBase):
    user_id: UUID


class Watchlist(WatchlistBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Enhanced Watchlist with Asset details
class WatchlistWithAsset(BaseModel):
    id: UUID
    user_id: UUID
    created_at: datetime
    asset: Asset

    model_config = ConfigDict(from_attributes=True)


# Alert schemas (updated)
class AlertBase(BaseModel):
    asset_id: UUID
    threshold: float
    direction: str  # 'above' or 'below'


class AlertCreate(AlertBase):
    user_id: UUID


class Alert(AlertBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    triggered_at: Optional[datetime] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class AlertWithAsset(BaseModel):
    id: UUID
    user_id: UUID
    asset_id: UUID
    threshold: float
    direction: str
    created_at: datetime
    triggered_at: Optional[datetime] = None
    is_active: bool = True
    asset: Asset

    model_config = ConfigDict(from_attributes=True)


# Authentication schemas
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    username: str


# Sentiment Analysis Request/Response
class SentimentAnalysisRequest(BaseModel):
    text: str


class SentimentAnalysisResponse(BaseModel):
    lexicon_score: float
    finbert_score: float


# Health Check Response
class HealthCheck(BaseModel):
    status: str = "ok"


# Search schemas
class SearchRequest(BaseModel):
    q: str = Field(..., description="Search query string")
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of records to return")


class ArticleWithSentiment(BaseModel):
    """Article with its associated sentiment data."""
    article: Article
    sentiments: List[Sentiment]

    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel):
    """Search results with pagination info."""
    results: List[ArticleWithSentiment]
    total_count: int
    query: str
    skip: int
    limit: int
    has_more: bool

    model_config = ConfigDict(from_attributes=True)


class SearchSuggestion(BaseModel):
    """Search suggestion for autocomplete."""
    term: str
    frequency: int
    category: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
