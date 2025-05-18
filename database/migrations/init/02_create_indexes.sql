-- TradeEasy Database Indexes
-- Creates all indexes for optimal query performance

-- Article indexes
CREATE INDEX IF NOT EXISTS articles_published_at_idx ON articles(published_at);
CREATE INDEX IF NOT EXISTS articles_source_idx ON articles(source);

-- Sentiment indexes
CREATE INDEX IF NOT EXISTS sentiments_article_id_idx ON sentiments(article_id);

-- SentimentAggregate indexes
CREATE INDEX IF NOT EXISTS sentiment_aggregates_asset_timestamp_idx
ON sentiment_aggregates(asset_id, timestamp);

-- Watchlist indexes
CREATE INDEX IF NOT EXISTS watchlist_user_id_idx ON watchlists(user_id);
CREATE INDEX IF NOT EXISTS watchlist_asset_id_idx ON watchlists(asset_id);

-- Alert indexes
CREATE INDEX IF NOT EXISTS alert_user_id_idx ON alerts(user_id);
CREATE INDEX IF NOT EXISTS alert_asset_is_active_idx ON alerts(asset_id, is_active);

-- Asset indexes
CREATE INDEX IF NOT EXISTS asset_type_idx ON assets(type);

-- Full-text search indexes for article content (PostgreSQL specific)
CREATE INDEX IF NOT EXISTS articles_content_gin_idx ON articles
USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS articles_title_gin_idx ON articles
USING gin(to_tsvector('english', title));
