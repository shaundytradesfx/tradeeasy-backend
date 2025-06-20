# TradeEasy Partner API Guide

**Version:** 1.0.0  
**Base URL:** `http://localhost:8000` (Development) | `https://api.tradeeasy.com` (Production)  
**Interactive Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

## Quick Start

### 1. Authentication
```bash
# Get demo token
curl -X GET "http://localhost:8000/api/auth/demo-login"

# Or login with credentials
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "demo123"}'
```

### 2. Analyze Sentiment
```bash
curl -X POST "http://localhost:8000/api/sentiment/article" \
  -H "Content-Type: application/json" \
  -d '{"text": "Apple stock surged after strong earnings report"}'
```

### 3. Get Real-time Updates
```bash
# REST polling
curl "http://localhost:8000/api/sentiment/stream"

# WebSocket (JavaScript)
const ws = new WebSocket('ws://localhost:8000/ws/sentiment');
```

## Core Features

### Sentiment Analysis
- **FinBERT Model**: Advanced transformer for financial text
- **Loughran-McDonald Lexicon**: Financial sentiment dictionary
- **Real-time Processing**: Sub-second analysis
- **Multi-asset Support**: Equities, crypto, FX, commodities

### Search & Discovery
- **Full-text Search**: PostgreSQL/SQLite powered
- **Sentiment Filtering**: Find positive/negative articles
- **Asset Classification**: Automatic categorization
- **Pagination**: Handle large result sets

### Watchlists & Alerts
- **Personal Watchlists**: Track favorite assets
- **Real-time Alerts**: Sentiment threshold notifications
- **WebSocket Delivery**: Instant alert delivery
- **Historical Tracking**: Alert trigger history

## Authentication

All protected endpoints require JWT authentication:

```bash
# Include in Authorization header
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/watchlists/"
```

**Token Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "demo"
}
```

## Key Endpoints

### Sentiment Analysis

#### POST /api/sentiment/article
Analyze text sentiment using both models.

**Request:**
```json
{
  "text": "Federal Reserve signals potential rate cuts amid economic uncertainty"
}
```

**Response:**
```json
{
  "lexicon_score": -0.125,
  "finbert_score": -0.234
}
```

#### GET /api/sentiment/latest?asset=BTC
Get latest sentiment aggregate for an asset.

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:00:00Z",
  "avg_score": 0.234,
  "asset": {
    "symbol": "BTC",
    "name": "Bitcoin",
    "type": "crypto"
  }
}
```

#### GET /api/sentiment/history?asset=AAPL&range=24h
Get historical sentiment data.

**Response:**
```json
[
  {
    "timestamp": "2024-01-15T14:00:00Z",
    "avg_score": 0.234,
    "asset": {"symbol": "AAPL", "name": "Apple Inc."}
  }
]
```

### Search

#### GET /api/search/?q=earnings&limit=10
Search articles with sentiment data.

**Response:**
```json
{
  "results": [
    {
      "article": {
        "title": "Apple Reports Strong Q4 Earnings",
        "source": "Reuters",
        "published_at": "2024-01-15T10:30:00Z"
      },
      "sentiments": [
        {
          "lexicon_score": 0.125,
          "finbert_score": 0.742
        }
      ]
    }
  ],
  "total_count": 156,
  "has_more": true
}
```

### Watchlists

#### GET /api/watchlists/
Get user's watchlists (requires auth).

#### POST /api/watchlists/?asset_symbol=BTC
Add asset to watchlist (requires auth).

### Alerts

#### POST /api/alerts/?asset_symbol=BTC&threshold=0.5&direction=above
Create sentiment alert (requires auth).

#### GET /api/alerts/triggered
Get recently triggered alerts (requires auth).

## Real-time Updates

### WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/sentiment');

ws.onopen = () => console.log('Connected');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleUpdate(data);
};
```

### REST Polling Alternative
```bash
# Get updates since timestamp
curl "http://localhost:8000/api/sentiment/stream?since=2024-01-15T14:00:00Z"
```

**Response includes:**
- `updates`: New sentiment analyses
- `aggregates`: Hourly sentiment aggregates  
- `alerts`: Triggered alerts
- `metadata`: Query statistics

## Message Types

### Sentiment Update
```json
{
  "type": "sentiment_update",
  "timestamp": "2024-01-15T14:30:00Z",
  "article": {
    "title": "Market Analysis",
    "source": "Bloomberg"
  },
  "sentiment": {
    "lexicon_score": 0.15,
    "finbert_score": 0.68,
    "overall_sentiment": "positive"
  }
}
```

### Alert Trigger
```json
{
  "type": "alert_triggered",
  "timestamp": "2024-01-15T14:15:00Z",
  "alert": {
    "asset_symbol": "BTC",
    "threshold": 0.5,
    "current_value": 0.67,
    "direction": "above"
  }
}
```

## Error Handling

### HTTP Status Codes
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing/invalid token)
- `404` - Not Found
- `422` - Validation Error
- `429` - Rate Limit Exceeded

### Error Response
```json
{
  "detail": [
    {
      "loc": ["body", "text"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Rate Limits

- **Standard**: 1,000 requests/hour
- **Premium**: 10,000 requests/hour
- **Enterprise**: Custom limits

**Headers:**
- `X-RateLimit-Limit`: Request limit
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset time

## Data Models

### Sentiment Scores
- **Range**: -1.0 (very negative) to +1.0 (very positive)
- **Neutral**: -0.1 to +0.1
- **Positive**: +0.1 to +1.0
- **Negative**: -1.0 to -0.1

### Asset Types
- `equity` - Stocks (AAPL, MSFT, etc.)
- `crypto` - Cryptocurrencies (BTC, ETH, etc.)
- `fx` - Foreign Exchange (EUR/USD, GBP/JPY, etc.)
- `commodity` - Commodities (Gold, Oil, etc.)

## Best Practices

### 1. Authentication
- Store JWT tokens securely
- Implement token refresh logic
- Use HTTPS in production

### 2. Rate Limiting
- Implement exponential backoff
- Cache responses when appropriate
- Use WebSocket for real-time data

### 3. Error Handling
- Check HTTP status codes
- Parse error messages for debugging
- Implement retry logic for transient errors

### 4. Performance
- Use pagination for large datasets
- Implement client-side caching
- Limit query parameters appropriately

## SDKs & Examples

### Python
```python
import requests

# Authenticate
response = requests.get('http://localhost:8000/api/auth/demo-login')
token = response.json()['access_token']

# Analyze sentiment
headers = {'Authorization': f'Bearer {token}'}
data = {'text': 'Apple stock is performing well'}
response = requests.post(
    'http://localhost:8000/api/sentiment/article',
    json=data,
    headers=headers
)
print(response.json())
```

### JavaScript
```javascript
// Authenticate
const authResponse = await fetch('http://localhost:8000/api/auth/demo-login');
const { access_token } = await authResponse.json();

// Analyze sentiment
const response = await fetch('http://localhost:8000/api/sentiment/article', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access_token}`
  },
  body: JSON.stringify({
    text: 'Apple stock is performing well'
  })
});
const result = await response.json();
console.log(result);
```

## Support & Resources

### Documentation
- **Interactive API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **OpenAPI Specification**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
- **WebSocket Testing**: Use browser dev tools or Postman

### Contact
- **Technical Support**: api-support@tradeeasy.com
- **Sales Inquiries**: sales@tradeeasy.com
- **Status Updates**: [status.tradeeasy.com](https://status.tradeeasy.com)

### Community
- **GitHub**: [github.com/tradeeasy/api-examples](https://github.com/tradeeasy/api-examples)
- **Discord**: [discord.gg/tradeeasy](https://discord.gg/tradeeasy)
- **Stack Overflow**: Tag questions with `tradeeasy-api`

---

**API Version**: 1.0.0  
**Last Updated**: January 2024  
**Next Update**: February 2024 (v1.1.0 with enhanced analytics) 