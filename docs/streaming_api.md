# Sentiment Streaming API Documentation

## Overview

The Sentiment Streaming API provides a REST endpoint for polling sentiment data updates, serving as an alternative to WebSocket connections for clients that cannot use WebSocket protocols.

## Endpoint

### GET `/api/sentiment/stream`

Get sentiment updates since a given timestamp for polling clients.

#### Description

This endpoint provides a REST alternative to WebSocket connections for clients that cannot use WebSocket. It returns sentiment data that has been updated since the specified timestamp, including:

- Sentiment aggregates for assets
- Recent articles with sentiment analysis
- Triggered alerts

The response format matches WebSocket broadcast messages for consistency between polling and real-time clients.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `since` | datetime (ISO format) | No | Timestamp to get updates since. If not provided, returns data from the last hour. |

#### Request Examples

```bash
# Get all updates from the last hour (default)
GET /api/sentiment/stream

# Get updates since a specific timestamp
GET /api/sentiment/stream?since=2024-01-01T12:00:00Z

# Get updates since 2 hours ago
GET /api/sentiment/stream?since=2024-01-01T10:00:00Z
```

#### Response Format

The response follows the same structure as WebSocket messages for consistency:

```json
{
  "updates": [
    {
      "type": "sentiment_update",
      "timestamp": "2024-01-01T12:30:00Z",
      "article": {
        "id": "uuid-string",
        "title": "Article Title",
        "source": "Source Name",
        "url": "https://example.com/article",
        "published_at": "2024-01-01T12:00:00Z",
        "asset_class": "general"
      },
      "sentiment": {
        "lexicon_score": 0.15,
        "finbert_score": 0.23,
        "overall_sentiment": "positive"
      },
      "metadata": {}
    }
  ],
  "aggregates": [
    {
      "type": "aggregate_update",
      "timestamp": "2024-01-01T12:00:00Z",
      "asset": {
        "symbol": "BTC",
        "avg_sentiment": 0.18,
        "article_count": 5,
        "time_period": "1h"
      },
      "sentiment_category": "positive",
      "metadata": {}
    }
  ],
  "alerts": [
    {
      "type": "alert_triggered",
      "timestamp": "2024-01-01T12:15:00Z",
      "alert": {
        "id": "uuid-string",
        "asset_symbol": "AAPL",
        "threshold": 0.3,
        "direction": "above",
        "current_value": 0.35,
        "user_id": "uuid-string"
      },
      "metadata": {}
    }
  ],
  "metadata": {
    "since": "2024-01-01T11:00:00Z",
    "total_updates": 1,
    "total_aggregates": 1,
    "total_alerts": 1,
    "generated_at": "2024-01-01T12:30:00Z"
  }
}
```

#### Response Fields

##### Updates Array
Contains individual article sentiment analysis results:

- `type`: Always "sentiment_update"
- `timestamp`: When the article was published
- `article`: Article metadata including ID, title, source, URL, and classification
- `sentiment`: Sentiment scores from different analysis methods
- `metadata`: Additional contextual information

##### Aggregates Array
Contains computed sentiment aggregates for assets:

- `type`: Always "aggregate_update"
- `timestamp`: When the aggregate was computed
- `asset`: Asset information including symbol, average sentiment, and article count
- `sentiment_category`: Human-readable sentiment classification
- `metadata`: Additional contextual information

##### Alerts Array
Contains triggered alert notifications:

- `type`: Always "alert_triggered"
- `timestamp`: When the alert was triggered
- `alert`: Alert details including thresholds and current values
- `metadata`: Additional contextual information

##### Metadata Object
Contains response-level information:

- `since`: The timestamp used for filtering (null if not provided)
- `total_*`: Counts of each type of update
- `generated_at`: When this response was generated

#### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success - Returns sentiment updates |
| 400 | Bad Request - Invalid timestamp format |
| 500 | Internal Server Error - Server processing error |

#### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

## Usage Patterns

### Polling Client Implementation

```python
import requests
from datetime import datetime, timedelta
import time

class SentimentPoller:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.last_check = None
    
    def poll_updates(self):
        """Poll for new sentiment updates."""
        url = f"{self.base_url}/api/sentiment/stream"
        
        # Use last check time or default to 1 hour ago
        if self.last_check:
            params = {"since": self.last_check.isoformat()}
        else:
            params = {}
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            self.last_check = datetime.utcnow()
            
            return data
        except requests.exceptions.RequestException as e:
            print(f"Polling error: {e}")
            return None
    
    def start_polling(self, interval=30):
        """Start polling every interval seconds."""
        while True:
            updates = self.poll_updates()
            if updates:
                self.process_updates(updates)
            time.sleep(interval)
    
    def process_updates(self, data):
        """Process received updates."""
        print(f"Received {data['metadata']['total_updates']} updates")
        print(f"Received {data['metadata']['total_aggregates']} aggregates")
        print(f"Received {data['metadata']['total_alerts']} alerts")

# Usage
poller = SentimentPoller()
poller.start_polling(interval=30)  # Poll every 30 seconds
```

### JavaScript/TypeScript Client

```typescript
interface SentimentStreamResponse {
  updates: SentimentUpdate[];
  aggregates: AggregateUpdate[];
  alerts: AlertUpdate[];
  metadata: {
    since: string | null;
    total_updates: number;
    total_aggregates: number;
    total_alerts: number;
    generated_at: string;
  };
}

class SentimentPoller {
  private baseUrl: string;
  private lastCheck: Date | null = null;
  
  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }
  
  async pollUpdates(): Promise<SentimentStreamResponse | null> {
    const url = new URL('/api/sentiment/stream', this.baseUrl);
    
    if (this.lastCheck) {
      url.searchParams.set('since', this.lastCheck.toISOString());
    }
    
    try {
      const response = await fetch(url.toString());
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data: SentimentStreamResponse = await response.json();
      this.lastCheck = new Date();
      
      return data;
    } catch (error) {
      console.error('Polling error:', error);
      return null;
    }
  }
  
  startPolling(intervalMs: number = 30000): void {
    const poll = async () => {
      const updates = await this.pollUpdates();
      if (updates) {
        this.processUpdates(updates);
      }
    };
    
    // Initial poll
    poll();
    
    // Set up interval
    setInterval(poll, intervalMs);
  }
  
  private processUpdates(data: SentimentStreamResponse): void {
    console.log(`Received ${data.metadata.total_updates} updates`);
    console.log(`Received ${data.metadata.total_aggregates} aggregates`);
    console.log(`Received ${data.metadata.total_alerts} alerts`);
    
    // Process updates, aggregates, and alerts as needed
  }
}

// Usage
const poller = new SentimentPoller();
poller.startPolling(30000); // Poll every 30 seconds
```

## Integration with WebSocket

The streaming endpoint is designed to complement the existing WebSocket implementation:

### WebSocket vs Polling Decision Matrix

| Use Case | Recommendation | Reason |
|----------|----------------|---------|
| Real-time dashboard | WebSocket | Immediate updates, lower latency |
| Mobile app (iOS/Android) | Polling | Better battery life, simpler connection management |
| Serverless functions | Polling | No persistent connections needed |
| Corporate firewall | Polling | HTTP typically allowed, WebSocket may be blocked |
| Batch processing | Polling | Can process updates in batches |
| High-frequency trading | WebSocket | Lowest possible latency |

### Hybrid Implementation

```python
class HybridSentimentClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.websocket_client = None
        self.poller = SentimentPoller(base_url)
        self.use_websocket = True
    
    async def connect(self):
        """Try WebSocket first, fall back to polling."""
        try:
            # Attempt WebSocket connection
            self.websocket_client = await self.connect_websocket()
            self.use_websocket = True
            print("Connected via WebSocket")
        except Exception as e:
            print(f"WebSocket failed: {e}, falling back to polling")
            self.use_websocket = False
            self.poller.start_polling()
    
    async def connect_websocket(self):
        # WebSocket connection logic here
        pass
```

## Rate Limiting and Best Practices

### Recommended Polling Intervals

- **Real-time applications**: 10-30 seconds
- **Dashboard updates**: 1-2 minutes
- **Background sync**: 5-15 minutes
- **Batch processing**: 1+ hours

### Performance Considerations

1. **Timestamp Management**: Always use the `since` parameter to avoid duplicate data
2. **Error Handling**: Implement exponential backoff for failed requests
3. **Data Processing**: Process updates asynchronously to avoid blocking the polling loop
4. **Connection Pooling**: Reuse HTTP connections for better performance

### Monitoring and Debugging

The endpoint includes metadata to help with monitoring:

```python
def monitor_polling_performance(data):
    """Monitor polling performance metrics."""
    metadata = data['metadata']
    
    # Check data freshness
    generated_at = datetime.fromisoformat(metadata['generated_at'].replace('Z', '+00:00'))
    latency = datetime.now(timezone.utc) - generated_at
    
    print(f"Response latency: {latency.total_seconds():.2f} seconds")
    print(f"Data age: {latency.total_seconds():.2f} seconds")
    
    # Check update volume
    total_items = (
        metadata['total_updates'] + 
        metadata['total_aggregates'] + 
        metadata['total_alerts']
    )
    
    if total_items == 0:
        print("No new updates available")
    elif total_items > 100:
        print(f"Warning: Large update batch ({total_items} items)")
```

## Testing

Use the provided test script to verify the endpoint:

```bash
python test_streaming_endpoint.py
```

This will test:
1. Basic endpoint functionality
2. Timestamp parameter handling
3. API documentation availability

## Security Considerations

- The endpoint currently doesn't require authentication
- Consider implementing rate limiting for production use
- Monitor for potential DoS attacks via timestamp parameter manipulation
- Validate and sanitize timestamp inputs

## Future Enhancements

Potential improvements for future versions:

1. **Asset Filtering**: Add parameters to filter by specific assets
2. **Pagination**: Implement pagination for large result sets
3. **Compression**: Add gzip compression for large responses
4. **Caching**: Implement response caching for frequently requested time ranges
5. **Authentication**: Add user-specific filtering and rate limits 