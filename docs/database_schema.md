# TradeEasy Database Schema

This document describes the database schema for the TradeEasy backend application, including the Entity Relationship Diagram (ERD) and detailed table definitions.

## Entity Relationship Diagram (ERD)

```
+----------------+       +----------------+       +-------------------+
|     User       |       |     Asset      |       |      Article      |
+----------------+       +----------------+       +-------------------+
| id (PK)        |       | id (PK)        |       | id (PK)           |
| username       |       | symbol         |       | source            |
| email          |       | name           |       | title             |
| password_hash  |       | type           |       | content           |
| created_at     |       | description    |       | published_at      |
| updated_at     |       |                |       | url               |
+----------------+       +----------------+       +-------------------+
       |                        |                        |
       |                        |                        |
       v                        v                        v
+----------------+       +----------------+       +------------------+
|   Watchlist    |       |     Alert      |       |    Sentiment     |
+----------------+       +----------------+       +------------------+
| id (PK)        |       | id (PK)        |       | id (PK)          |
| user_id (FK)   |       | user_id (FK)   |       | article_id (FK)  |
| asset_id (FK)  |       | asset_id (FK)  |       | lexicon_score    |
| created_at     |       | threshold      |       | finbert_score    |
|                |       | direction      |       |                  |
|                |       | created_at     |       |                  |
|                |       | triggered_at   |       |                  |
|                |       | is_active      |       |                  |
+----------------+       +----------------+       +------------------+
                                                          |
                                                          |
                                                          v
                                               +----------------------+
                                               | SentimentAggregate   |
                                               +----------------------+
                                               | id (PK)              |
                                               | asset_id (FK)        |
                                               | timestamp            |
                                               | avg_score            |
                                               |                      |
                                               +----------------------+
```

## Table Definitions

### User Table

Stores user account information.

| Column         | Type      | Constraints         | Description                        |
|----------------|-----------|---------------------|------------------------------------|
| id             | UUID      | PK, NOT NULL        | Unique identifier for the user     |
| username       | VARCHAR   | UNIQUE, NOT NULL    | User's login name                  |
| email          | VARCHAR   | UNIQUE, NOT NULL    | User's email address               |
| password_hash  | VARCHAR   | NOT NULL            | Hashed password                    |
| created_at     | TIMESTAMP | NOT NULL, DEFAULT   | When the user account was created  |
| updated_at     | TIMESTAMP |                     | When the user account was last updated |

### Asset Table

Defines financial assets that can be tracked.

| Column      | Type      | Constraints         | Description                           |
|-------------|-----------|---------------------|---------------------------------------|
| id          | UUID      | PK, NOT NULL        | Unique identifier for the asset       |
| symbol      | VARCHAR   | UNIQUE, NOT NULL    | Trading symbol (e.g., AAPL, BTC-USD) |
| name        | VARCHAR   | NOT NULL            | Full name of the asset                |
| type        | VARCHAR   | NOT NULL            | Type: stock, forex, crypto, commodity |
| description | TEXT      |                     | Brief description of the asset        |

### Article Table

Stores news articles fetched from RSS feeds.

| Column       | Type      | Constraints           | Description                    |
|--------------|-----------|------------------------|--------------------------------|
| id           | UUID      | PK, NOT NULL          | Unique identifier              |
| source       | VARCHAR   | NOT NULL              | Source of the article          |
| title        | VARCHAR   | NOT NULL              | Article title                  |
| content      | TEXT      | NOT NULL              | Full article content           |
| published_at | TIMESTAMP | NOT NULL, DEFAULT     | When the article was published |
| url          | VARCHAR   | UNIQUE, NOT NULL      | URL of the original article    |

### Sentiment Table

Stores sentiment analysis results for articles.

| Column        | Type      | Constraints           | Description                       |
|---------------|-----------|------------------------|-----------------------------------|
| id            | UUID      | PK, NOT NULL          | Unique identifier                 |
| article_id    | UUID      | FK, NOT NULL          | Reference to the article          |
| lexicon_score | FLOAT     |                       | Sentiment score from lexicon-based analysis |
| finbert_score | FLOAT     |                       | Sentiment score from FinBERT model |

### SentimentAggregate Table

Stores aggregated sentiment scores for assets over time.

| Column     | Type      | Constraints           | Description                           |
|------------|-----------|------------------------|---------------------------------------|
| id         | UUID      | PK, NOT NULL          | Unique identifier                     |
| asset_id   | UUID      | FK, NOT NULL          | Reference to the asset                |
| timestamp  | TIMESTAMP | NOT NULL, DEFAULT     | Time period for the aggregation       |
| avg_score  | FLOAT     | NOT NULL              | Average sentiment score for the period |

### Watchlist Table

Tracks which assets users are following.

| Column     | Type      | Constraints           | Description                     |
|------------|-----------|------------------------|---------------------------------|
| id         | UUID      | PK, NOT NULL          | Unique identifier               |
| user_id    | UUID      | FK, NOT NULL          | Reference to the user           |
| asset_id   | UUID      | FK, NOT NULL          | Reference to the asset          |
| created_at | TIMESTAMP | NOT NULL, DEFAULT     | When the entry was created      |

Unique constraint on (user_id, asset_id) to prevent duplicates

### Alert Table

Configures alerts for when sentiment scores cross thresholds.

| Column       | Type      | Constraints           | Description                         |
|--------------|-----------|------------------------|-------------------------------------|
| id           | UUID      | PK, NOT NULL          | Unique identifier                   |
| user_id      | UUID      | FK, NOT NULL          | Reference to the user               |
| asset_id     | UUID      | FK, NOT NULL          | Reference to the asset              |
| threshold    | FLOAT     | NOT NULL              | Sentiment threshold for the alert   |
| direction    | VARCHAR   | NOT NULL              | 'above' or 'below'                  |
| created_at   | TIMESTAMP | NOT NULL, DEFAULT     | When the alert was created          |
| triggered_at | TIMESTAMP |                       | When the alert was last triggered   |
| is_active    | BOOLEAN   | NOT NULL, DEFAULT     | Whether the alert is active         |

## Indexes

For optimal query performance, the following indexes should be created:

1. `articles_published_at_idx` on `articles(published_at)`
2. `sentiment_aggregates_asset_timestamp_idx` on `sentiment_aggregates(asset_id, timestamp)`
3. `articles_source_idx` on `articles(source)`
4. `watchlist_user_id_idx` on `watchlists(user_id)`
5. `alert_user_id_idx` on `alerts(user_id)`
6. `alert_asset_is_active_idx` on `alerts(asset_id, is_active)`

## Database Migrations

Migrations should be managed using Alembic to track schema changes over time.
