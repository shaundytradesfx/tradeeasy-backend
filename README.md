# TradeEasy Backend

Real-time sentiment analytics platform for equities, FX, crypto, and commodities.

## Project Overview

TradeEasy is a platform that ingests financial news from various RSS feeds, analyzes sentiment using lexicon-based approaches and FinBERT, and provides real-time analytics through a web dashboard.

## Technologies

- **Framework**: FastAPI (Python 3.11)
- **Database**: PostgreSQL
- **Libraries**: SQLAlchemy, Uvicorn, feedparser, newspaper3k, python-dotenv, transformers (FinBERT)
- **Deployment**: Docker (uvicorn entrypoint)

## Directory Structure

```
tradeeasy-backend/
├── app/
│   ├── main.py            # FastAPI application entry point
│   ├── models.py          # SQLAlchemy models
│   ├── schemas.py         # Pydantic schemas
│   ├── database.py        # Database configuration
│   ├── crud.py            # Database operations
│   └── routers/
│       └── ingestion.py   # RSS ingestion logic
├── tests/
│   └── test_ingest.py     # Tests for ingestion
├── requirements.txt       # Project dependencies
└── Dockerfile             # Docker configuration
```

## Setup

### Environment Variables

Create a `.env` file in the project root with the following variables:

```
# Database configuration
DATABASE_URL=postgresql://postgres:password@localhost/tradeeasy

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

3. Set up the PostgreSQL database:

```bash
# Create a PostgreSQL database named 'tradeeasy'
# Update the DATABASE_URL in your .env file if needed
```

4. Run the application:

```bash
uvicorn app.main:app --reload
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

- **Health Check**: `GET /health`
- **RSS Ingestion**: `POST /ingestion/rss`
- **RSS Sources**: `GET /ingestion/sources`

## Testing

Run the tests with pytest:

```bash
pytest
```

## License

[MIT License](LICENSE) 