# CI/CD Status
# TradeEasy Backend

Real-time sentiment analytics platform for equities, FX, crypto, and commodities.

## Project Overview

TradeEasy is a platform that ingests financial news from various RSS feeds, analyzes sentiment using lexicon-based approaches and FinBERT, and provides real-time analytics through a web dashboard with watchlists, alerts, and real-time streaming capabilities.

## Technologies

- **Framework**: FastAPI (Python 3.11)
- **Database**: SQLite (development) / PostgreSQL (production)
- **Libraries**: SQLAlchemy, Uvicorn, feedparser, newspaper3k, python-dotenv, transformers (FinBERT), spaCy
- **Deployment**: Docker (uvicorn entrypoint)
- **Real-time**: WebSocket + REST polling fallback
- **Scheduling**: APScheduler for automated RSS ingestion

## Directory Structure

```
tradeeasy-backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── database.py          # Database configuration
│   ├── crud.py              # Database operations
│   ├── metrics.py           # Prometheus metrics
│   ├── websocket_manager.py # WebSocket connection management
│   ├── nlp/                 # NLP processing modules
│   │   ├── sentiment.py     # Sentiment analysis orchestration
│   │   ├── lexicon.py       # Loughran-McDonald lexicon
│   │   ├── finbert.py       # FinBERT transformer model
│   │   └── preprocess.py    # Text preprocessing
│   └── routers/
│       ├── ingestion.py     # RSS ingestion endpoints
│       ├── sentiment.py     # Sentiment analysis endpoints
│       ├── search.py        # Article search endpoints
│       ├── watchlist.py     # User watchlist management
│       ├── alerts.py        # Alert system endpoints
│       └── auth.py          # Authentication endpoints
├── tests/                   # Comprehensive test suite
├── requirements.txt         # Project dependencies
└── Dockerfile              # Docker configuration
```

## Setup

### Environment Variables

Create a `.env` file in the project root with the following variables:

```
# Database configuration
DATABASE_URL=postgresql://postgres:password@localhost/tradeeasy
# For development, SQLite is used by default: sqlite:///./tradeeasy.db

# RSS feed sources (comma-separated)
RSS_SOURCES=https://finance.yahoo.com/news/rssindex,https://www.investing.com/rss/news.rss,https://www.cnbc.com/id/100003114/device/rss/rss.html

# Application settings
DEBUG=True
```

### Local Development

1. Create and activate a Python virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up the database:

```bash
# For development, SQLite is used automatically
# For PostgreSQL, create a database named 'tradeeasy' and update DATABASE_URL
```

4. Run the application:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000, and the interactive API documentation at http://localhost:8000/docs.

### Docker

To build and run the application using Docker:

```bash
# Build the Docker image
docker build -t tradeeasy-backend .

# Run the container
docker run -p 8000:8000 --env-file .env tradeeasy-backend
```

## API Endpoints

### Core Endpoints
- **Health Check**: `GET /health`
- **API Status**: `GET /api/status` - Comprehensive system status

### Authentication
- **Login**: `POST /api/auth/login`
- **Demo Login**: `GET /api/auth/demo-login`
- **Logout**: `POST /api/auth/logout`

### RSS Ingestion
- **Trigger Ingestion**: `POST /ingestion/ingestion/rss`
- **Get Sources**: `GET /ingestion/ingestion/sources`
- **Ingestion Status**: `GET /ingestion/ingestion/status`
- **Validate Feed**: `GET /ingestion/ingestion/validate/{feed_index}`

### Sentiment Analysis
- **Analyze Text**: `POST /api/sentiment/article`
- **Latest Sentiment**: `GET /api/sentiment/latest?asset={symbol}`
- **Sentiment History**: `GET /api/sentiment/history?asset={symbol}&range={timespan}`
- **Compute Hourly**: `POST /api/sentiment/compute-hourly`
- **Available Assets**: `GET /api/sentiment/assets`

### **Week 5: Real-Time Streaming (Polling Feedback)**
- **Stream Updates**: `GET /api/sentiment/stream?since={timestamp}`
  - REST alternative to WebSocket connections
  - Returns sentiment updates, aggregates, and alerts since specified timestamp
  - Example: `GET /api/sentiment/stream?since=2024-01-01T12:00:00Z`
  - Response format matches WebSocket broadcast messages for consistency

### Search
- **Search Articles**: `GET /api/search/search/?q={query}`
- **Search Articles Only**: `GET /api/search/search/articles?q={query}`
- **Create Search Index**: `POST /api/search/search/index`

### Watchlists
- **Get Watchlists**: `GET /api/watchlists/`
- **Add to Watchlist**: `POST /api/watchlists/?asset_symbol={symbol}`
- **Remove from Watchlist**: `DELETE /api/watchlists/{watchlist_id}`
- **Watchlist Stats**: `GET /api/watchlists/stats`

### Alerts
- **Get Alerts**: `GET /api/alerts/`
- **Create Alert**: `POST /api/alerts/?asset_symbol={symbol}&threshold={value}&direction={above|below}`
- **Delete Alert**: `DELETE /api/alerts/{alert_id}`
- **Reset Alert**: `POST /api/alerts/{alert_id}/reset`
- **Triggered Alerts**: `GET /api/alerts/triggered`
- **Test Alert Trigger**: `POST /api/alerts/test-trigger`

### Real-Time WebSocket
- **WebSocket Endpoint**: `ws://localhost:8000/ws/sentiment`
  - Real-time sentiment updates
  - Alert notifications
  - Aggregate updates

### Metrics & Monitoring
- **Prometheus Metrics**: `GET /metrics`
- **WebSocket Stats**: `GET /api/websocket/stats`

## Features

### ✅ Week 1-2: Core Infrastructure
- [x] FastAPI application with SQLAlchemy models
- [x] RSS feed ingestion with newspaper3k
- [x] Article storage and deduplication

### ✅ Week 3: NLP Pipeline
- [x] Loughran-McDonald lexicon sentiment scoring
- [x] FinBERT transformer-based sentiment analysis
- [x] Text preprocessing with spaCy

### ✅ Week 4: Advanced Features
- [x] Scheduled hourly ingestion with APScheduler
- [x] Hourly sentiment aggregates computation
- [x] User watchlists and alert system
- [x] Background alert checking and triggering

### ✅ Week 5: Real-Time Integration
- [x] WebSocket endpoint for real-time updates (`/ws/sentiment`)
- [x] **REST polling fallback endpoint** (`/api/sentiment/stream?since=timestamp`)
- [x] Real-time alert broadcasting
- [x] Live sentiment aggregate updates

### Additional Features
- [x] Comprehensive search with full-text capabilities
- [x] Authentication system (demo implementation)
- [x] Prometheus metrics integration
- [x] Comprehensive API documentation
- [x] Error handling and retry mechanisms
- [x] Performance optimizations with lazy loading

## Testing

Run the tests with pytest:

```bash
pytest
```

Run specific test suites:

```bash
# Test WebSocket functionality
pytest tests/test_websocket_load.py

# Test RSS ingestion
pytest tests/test_ingest.py

# Test search functionality
pytest test_search_api.py
```

## Architecture

### Data Flow
1. **RSS Ingestion**: Scheduled hourly fetching from financial news sources
2. **Content Extraction**: Full article text extraction with newspaper3k
3. **Sentiment Analysis**: Dual scoring with lexicon + FinBERT
4. **Aggregation**: Hourly sentiment averages by asset
5. **Alert Processing**: Background checking for user-defined thresholds
6. **Real-Time Distribution**: WebSocket broadcasts + REST polling

### Real-Time Architecture
- **WebSocket**: Primary real-time channel for live updates
- **REST Polling**: Fallback for clients that cannot use WebSocket
- **Consistent Format**: Both channels use identical message formats
- **Alert Integration**: Real-time alert notifications across both channels

## Performance

- **Import Optimization**: Lazy loading of heavy ML libraries (spaCy, PyTorch)
- **Startup Time**: < 2 seconds with optimized imports
- **Response Time**: < 200ms for sentiment analysis endpoints
- **Concurrent Connections**: Supports multiple WebSocket clients
- **Background Processing**: Non-blocking scheduled tasks

## Production Considerations

- Configure `DATABASE_URL` for PostgreSQL in production
- Set up proper environment variables
- Enable Prometheus metrics collection
- Configure log levels appropriately
- Set up SSL/TLS for WebSocket connections
- Implement proper authentication/authorization

## License

[MIT License](LICENSE) 