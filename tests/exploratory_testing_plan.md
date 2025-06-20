# TradeEasy Backend - Exploratory Testing Plan
## Week 7 QA - Edge Cases & Boundary Testing

### Overview
This document outlines exploratory testing scenarios focusing on edge cases, boundary conditions, and error scenarios that may not be covered by standard functional testing. The goal is to identify potential system vulnerabilities and ensure robust error handling.

---

## 1. RSS Feed Edge Cases

### ETC-RSS-001: Empty RSS Feeds
**Scenario**: RSS feeds return empty or minimal content
**Priority**: High

**Test Cases**:
1. **Completely Empty Feed**
   - Mock RSS endpoint returning empty XML: `<?xml version="1.0"?><rss></rss>`
   - Expected: Graceful handling, no system crash, appropriate logging

2. **Feed with No Items**
   - RSS with valid structure but zero `<item>` elements
   - Expected: No articles added, ingestion completes successfully

3. **Feed with Empty Items**
   - Items with empty `<title>`, `<description>`, or `<link>` fields
   - Expected: Skip invalid items, process valid ones, log warnings

**Test Commands**:
```bash
# Create mock empty RSS feed
curl -X POST http://localhost:8000/api/ingestion/test-feed \
  -H "Content-Type: application/xml" \
  -d '<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>'
```

---

### ETC-RSS-002: Malformed RSS Feeds
**Scenario**: RSS feeds with invalid XML structure or content
**Priority**: High

**Test Cases**:
1. **Invalid XML Structure**
   - Unclosed tags: `<rss><channel><item><title>Test</item></channel></rss>`
   - Malformed encoding: Invalid UTF-8 characters
   - Missing required elements

2. **Corrupted Content**
   - Binary data in XML fields
   - Extremely long content (>1MB per item)
   - Special characters and encoding issues

3. **Invalid Date Formats**
   - Non-standard date formats in `<pubDate>`
   - Future dates (year 2099)
   - Invalid timezone specifications

**Test Data Examples**:
```xml
<!-- Malformed XML -->
<rss version="2.0">
  <channel>
    <item>
      <title>Unclosed title
      <description>Valid description</description>
    </item>
  </channel>
</rss>

<!-- Invalid characters -->
<rss version="2.0">
  <channel>
    <item>
      <title>Test with \x00\x01 invalid chars</title>
      <description>Content with 🚀💰📈 emojis</description>
    </item>
  </channel>
</rss>
```

---

### ETC-RSS-003: Network and Connectivity Edge Cases
**Scenario**: Network issues during RSS ingestion
**Priority**: Medium

**Test Cases**:
1. **Timeout Scenarios**
   - RSS feeds that respond very slowly (>30 seconds)
   - Partial responses that hang mid-transfer
   - DNS resolution failures

2. **HTTP Error Responses**
   - 404 Not Found for RSS URLs
   - 500 Internal Server Error from RSS source
   - 403 Forbidden (authentication required)
   - Redirect loops

3. **Content-Type Issues**
   - RSS served with wrong Content-Type (text/html instead of application/xml)
   - Compressed responses (gzip) not properly handled
   - Character encoding mismatches

**Test Commands**:
```bash
# Test timeout handling
curl -X POST http://localhost:8000/api/ingestion/test-timeout \
  --max-time 5

# Test 404 handling
curl -X POST http://localhost:8000/api/ingestion/test-404
```

---

## 2. Sentiment Analysis Edge Cases

### ETC-SENT-001: Extreme Content Scenarios
**Scenario**: Unusual article content that might break sentiment analysis
**Priority**: High

**Test Cases**:
1. **Empty or Minimal Content**
   - Empty string: `""`
   - Single character: `"a"`
   - Only whitespace: `"   \n\t   "`
   - Only punctuation: `"!@#$%^&*()"`

2. **Extremely Long Content**
   - Articles with 100,000+ characters
   - Repeated text patterns
   - Memory exhaustion scenarios

3. **Special Characters and Encoding**
   - Unicode characters: `"📈💰🚀 Apple stock rises"`
   - HTML entities: `"Apple &amp; Microsoft &lt;earnings&gt;"`
   - Mixed languages: `"Apple 株価上昇 акции растут"`

**Test Data**:
```json
{
  "text": "",
  "asset": "AAPL"
}

{
  "text": "A".repeat(100000),
  "asset": "STRESS_TEST"
}

{
  "text": "🚀💰📈💎🌙 AAPL TO THE MOON 🌙💎📈💰🚀",
  "asset": "AAPL"
}
```

---

### ETC-SENT-002: FinBERT Model Edge Cases
**Scenario**: Test FinBERT model with unusual inputs
**Priority**: Medium

**Test Cases**:
1. **Non-Financial Content**
   - Weather reports
   - Sports news
   - Personal diary entries
   - Technical documentation

2. **Ambiguous Sentiment**
   - Sarcastic content: `"Great, another market crash"`
   - Mixed sentiment: `"Apple profits up but layoffs announced"`
   - Neutral technical content

3. **Model Resource Limits**
   - Concurrent sentiment analysis requests (>100 simultaneous)
   - Memory usage during batch processing
   - Model loading failures

---

## 3. Database Edge Cases

### ETC-DB-001: Data Integrity and Constraints
**Scenario**: Test database constraints and edge cases
**Priority**: High

**Test Cases**:
1. **Constraint Violations**
   - Duplicate article URLs
   - NULL values in required fields
   - Foreign key constraint violations
   - Data type mismatches

2. **Large Dataset Scenarios**
   - Tables with millions of records
   - Complex queries with large result sets
   - Index performance under load
   - Database connection pool exhaustion

3. **Concurrent Access**
   - Multiple users accessing same watchlist
   - Simultaneous alert creation/deletion
   - Race conditions in sentiment aggregation

**Test SQL**:
```sql
-- Test constraint violations
INSERT INTO articles (id, source, title, content, published_at) 
VALUES (NULL, NULL, NULL, NULL, NULL);

-- Test large dataset queries
SELECT * FROM sentiment_aggregates 
WHERE asset = 'AAPL' 
ORDER BY timestamp DESC 
LIMIT 1000000;
```

---

### ETC-DB-002: Transaction and Rollback Scenarios
**Scenario**: Test transaction handling and error recovery
**Priority**: Medium

**Test Cases**:
1. **Failed Transactions**
   - Simulate database deadlocks
   - Transaction timeout scenarios
   - Partial transaction failures

2. **Data Consistency**
   - Verify rollback behavior
   - Check referential integrity after failures
   - Concurrent transaction conflicts

---

## 4. Authentication and Security Edge Cases

### ETC-AUTH-001: JWT Token Edge Cases
**Scenario**: Test JWT token handling edge cases
**Priority**: High

**Test Cases**:
1. **Malformed Tokens**
   - Invalid JWT structure
   - Corrupted signatures
   - Missing required claims
   - Expired tokens with future dates

2. **Token Manipulation**
   - Modified payload data
   - Algorithm confusion attacks
   - Token replay attacks
   - Extremely long tokens (>8KB)

**Test Examples**:
```bash
# Test with malformed JWT
curl -H "Authorization: Bearer invalid.jwt.token" \
  http://localhost:8000/api/watchlist

# Test with empty token
curl -H "Authorization: Bearer " \
  http://localhost:8000/api/watchlist

# Test with extremely long token
curl -H "Authorization: Bearer $(python -c 'print("a"*10000)')" \
  http://localhost:8000/api/watchlist
```

---

### ETC-AUTH-002: Rate Limiting Edge Cases
**Scenario**: Test rate limiting under extreme conditions
**Priority**: Medium

**Test Cases**:
1. **Burst Traffic**
   - 1000 requests in 1 second
   - Sustained high-rate requests
   - Multiple IP addresses

2. **Edge Case Scenarios**
   - Requests exactly at rate limit boundary
   - Clock synchronization issues
   - Rate limit reset timing

---

## 5. WebSocket Edge Cases

### ETC-WS-001: Connection Edge Cases
**Scenario**: Test WebSocket connection handling
**Priority**: High

**Test Cases**:
1. **Connection Failures**
   - Abrupt client disconnections
   - Server restart during active connections
   - Network interruptions

2. **Message Handling**
   - Extremely large messages (>1MB)
   - Malformed JSON messages
   - Binary data in text messages
   - Rapid message bursts

3. **Authentication Edge Cases**
   - Token expiration during connection
   - Invalid token after connection established
   - Multiple authentication attempts

**Test Script**:
```python
import asyncio
import websockets
import json

async def test_websocket_edge_cases():
    # Test malformed message
    async with websockets.connect("ws://localhost:8000/ws/sentiment") as ws:
        await ws.send("invalid json")
        response = await ws.recv()
        print(f"Response to invalid JSON: {response}")
    
    # Test extremely large message
    large_message = json.dumps({"data": "x" * 1000000})
    async with websockets.connect("ws://localhost:8000/ws/sentiment") as ws:
        await ws.send(large_message)
```

---

## 6. API Input Validation Edge Cases

### ETC-API-001: Parameter Validation
**Scenario**: Test API parameter validation with edge cases
**Priority**: High

**Test Cases**:
1. **Boundary Values**
   - Negative numbers where positive expected
   - Zero values for required parameters
   - Maximum integer values (2^31-1)
   - Floating point edge cases (NaN, Infinity)

2. **String Validation**
   - Extremely long strings (>10MB)
   - Empty strings where content required
   - SQL injection attempts
   - XSS payload attempts

3. **Date/Time Edge Cases**
   - Invalid date formats
   - Dates before Unix epoch (1970)
   - Future dates (year 3000)
   - Timezone edge cases

**Test Examples**:
```bash
# Test negative values
curl "http://localhost:8000/api/sentiment/history?asset=AAPL&range=-1h"

# Test extremely long asset name
curl "http://localhost:8000/api/sentiment/latest?asset=$(python -c 'print("A"*10000)')"

# Test SQL injection
curl "http://localhost:8000/api/search?q='; DROP TABLE articles; --"

# Test XSS
curl "http://localhost:8000/api/search?q=<script>alert('xss')</script>"
```

---

## 7. Performance Edge Cases

### ETC-PERF-001: Resource Exhaustion
**Scenario**: Test system behavior under resource constraints
**Priority**: Medium

**Test Cases**:
1. **Memory Exhaustion**
   - Large sentiment analysis batches
   - Memory leaks in long-running processes
   - Garbage collection pressure

2. **CPU Intensive Operations**
   - Complex search queries
   - Concurrent FinBERT processing
   - Regex-heavy text processing

3. **Disk Space Issues**
   - Database growth beyond available space
   - Log file accumulation
   - Temporary file cleanup

---

## 8. Monitoring and Metrics Edge Cases

### ETC-MON-001: Metrics Collection Edge Cases
**Scenario**: Test metrics collection under unusual conditions
**Priority**: Low

**Test Cases**:
1. **Metrics Overflow**
   - Counter values exceeding limits
   - Histogram bucket edge cases
   - Gauge value extremes

2. **Collection Failures**
   - Prometheus server unavailable
   - Metrics endpoint timeout
   - Malformed metrics data

---

## Exploratory Testing Execution Plan

### Phase 1: Critical Edge Cases (Day 1)
- RSS feed malformation and empty feeds
- Sentiment analysis with extreme content
- Database constraint violations
- Authentication token edge cases

### Phase 2: System Limits (Day 2)
- Performance under load
- Resource exhaustion scenarios
- WebSocket connection limits
- API parameter boundaries

### Phase 3: Integration Edge Cases (Day 3)
- Cross-component failure scenarios
- Data consistency under stress
- Monitoring system edge cases
- Recovery and resilience testing

### Test Environment Setup
```bash
# Create test database with edge case data
python create_edge_case_test_data.py

# Start monitoring
docker-compose -f docker-compose.monitoring.yml up -d

# Run edge case test suite
python run_exploratory_tests.py --phase all
```

### Success Criteria
- System remains stable under all edge conditions
- Appropriate error messages for invalid inputs
- No data corruption or loss
- Graceful degradation when limits exceeded
- Security vulnerabilities identified and documented

### Risk Assessment
- **High Risk**: RSS malformation causing system crashes
- **Medium Risk**: Memory exhaustion during sentiment analysis
- **Low Risk**: Metrics collection edge cases

### Reporting
- Document all edge cases that cause system failures
- Provide recommendations for input validation improvements
- Report performance bottlenecks discovered
- Create bug reports for any security vulnerabilities found 