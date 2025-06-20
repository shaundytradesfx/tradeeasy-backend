# TradeEasy Backend - Manual Test Cases
## Week 7 QA & Testing Documentation

### Overview
This document defines comprehensive manual test cases for all TradeEasy backend feature flows. Each test case includes preconditions, test steps, expected results, and acceptance criteria.

---

## 1. Authentication Flow Test Cases

### TC-AUTH-001: Demo User Login
**Objective**: Verify demo user authentication works correctly
**Priority**: High
**Preconditions**: Server is running, database is accessible

**Test Steps**:
1. Send POST request to `/api/auth/login/demo`
2. Verify response contains JWT token
3. Use token in Authorization header for protected endpoints
4. Verify token expiration handling

**Expected Results**:
- Status: 200 OK
- Response contains valid JWT token
- Token allows access to protected endpoints
- Token expires after configured time

**Acceptance Criteria**:
- ✅ Demo login successful
- ✅ JWT token format valid
- ✅ Protected endpoints accessible with token
- ✅ Token expiration handled gracefully

---

### TC-AUTH-002: Standard User Login
**Objective**: Verify standard user authentication
**Priority**: High
**Preconditions**: User exists in database

**Test Steps**:
1. Send POST request to `/api/auth/login` with valid credentials
2. Verify JWT token generation
3. Test token with various protected endpoints
4. Test token refresh mechanism

**Expected Results**:
- Successful authentication with valid credentials
- JWT token contains user information
- Token works across all protected endpoints

---

### TC-AUTH-003: Invalid Authentication
**Objective**: Verify proper handling of invalid credentials
**Priority**: Medium
**Preconditions**: Server running

**Test Steps**:
1. Send login request with invalid username
2. Send login request with invalid password
3. Send login request with malformed data
4. Verify error responses

**Expected Results**:
- Status: 401 Unauthorized for invalid credentials
- Proper error messages returned
- No sensitive information leaked

---

## 2. Sentiment Analysis Flow Test Cases

### TC-SENT-001: Article Sentiment Analysis
**Objective**: Verify sentiment analysis for individual articles
**Priority**: High
**Preconditions**: Authentication token available

**Test Steps**:
1. Send POST request to `/api/sentiment/analyze` with article text
2. Verify both lexicon and FinBERT scores returned
3. Test with various article lengths
4. Test with different sentiment polarities

**Expected Results**:
- Status: 200 OK
- Response contains lexicon_score and finbert_score
- Scores are within expected range (-1.0 to 1.0)
- Processing time < 200ms per requirement

**Test Data**:
```json
{
  "text": "Apple Inc. reported strong quarterly earnings, beating analyst expectations significantly.",
  "asset": "AAPL"
}
```

**Acceptance Criteria**:
- ✅ Sentiment scores calculated correctly
- ✅ Response time within SLA
- ✅ Both scoring methods return values
- ✅ Asset tagging works properly

---

### TC-SENT-002: Latest Sentiment Retrieval
**Objective**: Verify latest sentiment data retrieval
**Priority**: High
**Preconditions**: Articles exist in database

**Test Steps**:
1. Send GET request to `/api/sentiment/latest?asset=AAPL`
2. Verify response contains recent sentiment data
3. Test with different assets
4. Test with non-existent assets

**Expected Results**:
- Returns most recent sentiment data for asset
- Proper handling of non-existent assets
- Response includes timestamp and scores

---

### TC-SENT-003: Sentiment History
**Objective**: Verify historical sentiment data retrieval
**Priority**: High
**Preconditions**: Historical data exists

**Test Steps**:
1. Send GET request to `/api/sentiment/history?asset=AAPL&range=24h`
2. Test different time ranges (1h, 24h, 7d, 30d)
3. Verify data aggregation
4. Test pagination

**Expected Results**:
- Returns time-series sentiment data
- Proper aggregation by time period
- Pagination works correctly
- Data sorted chronologically

---

### TC-SENT-004: Sentiment Streaming
**Objective**: Verify real-time sentiment streaming
**Priority**: High
**Preconditions**: Authentication token, recent data

**Test Steps**:
1. Send GET request to `/api/sentiment/stream?since=<timestamp>`
2. Verify incremental data retrieval
3. Test with various timestamp formats
4. Test edge cases (future timestamps, invalid formats)

**Expected Results**:
- Returns only new data since timestamp
- Proper timestamp handling
- Efficient data transfer

---

## 3. Search Functionality Test Cases

### TC-SEARCH-001: Basic Article Search
**Objective**: Verify article search functionality
**Priority**: High
**Preconditions**: Articles indexed in database

**Test Steps**:
1. Send GET request to `/api/search?q=Apple`
2. Verify search results relevance
3. Test different query types
4. Verify sentiment tags in results

**Expected Results**:
- Relevant articles returned
- Results include sentiment information
- Search performance acceptable
- Proper ranking of results

**Test Queries**:
- Single word: "Apple"
- Multiple words: "Apple earnings report"
- Quoted phrase: "quarterly earnings"
- Special characters: "Apple & Microsoft"

---

### TC-SEARCH-002: Search Pagination
**Objective**: Verify search result pagination
**Priority**: Medium
**Preconditions**: Large dataset available

**Test Steps**:
1. Send search request with limit parameter
2. Test offset/pagination parameters
3. Verify total count accuracy
4. Test edge cases (limit=0, negative values)

**Expected Results**:
- Pagination works correctly
- Total count matches actual results
- Performance remains acceptable with large datasets

---

### TC-SEARCH-003: Advanced Search Filters
**Objective**: Verify advanced search filtering
**Priority**: Medium
**Preconditions**: Diverse article dataset

**Test Steps**:
1. Test asset-specific search
2. Test date range filtering
3. Test sentiment score filtering
4. Test source filtering

**Expected Results**:
- Filters work independently and in combination
- Results match filter criteria
- Performance acceptable with multiple filters

---

## 4. Watchlist Management Test Cases

### TC-WATCH-001: Create Watchlist
**Objective**: Verify watchlist creation
**Priority**: High
**Preconditions**: Authenticated user

**Test Steps**:
1. Send POST request to `/api/watchlist` with asset
2. Verify watchlist entry created
3. Test duplicate asset handling
4. Test invalid asset symbols

**Expected Results**:
- Watchlist entry created successfully
- Duplicates handled gracefully
- Invalid symbols rejected with proper error

---

### TC-WATCH-002: Retrieve Watchlist
**Objective**: Verify watchlist retrieval
**Priority**: High
**Preconditions**: User has watchlist entries

**Test Steps**:
1. Send GET request to `/api/watchlist`
2. Verify all user's watchlist items returned
3. Verify sentiment data included
4. Test empty watchlist scenario

**Expected Results**:
- All watchlist items returned
- Current sentiment data included
- Empty watchlist handled properly

---

### TC-WATCH-003: Delete Watchlist Item
**Objective**: Verify watchlist item deletion
**Priority**: Medium
**Preconditions**: Watchlist items exist

**Test Steps**:
1. Send DELETE request to `/api/watchlist/{asset}`
2. Verify item removed from watchlist
3. Test deletion of non-existent items
4. Verify other items unaffected

**Expected Results**:
- Item successfully removed
- Non-existent items handled gracefully
- Other watchlist items remain intact

---

## 5. Alert System Test Cases

### TC-ALERT-001: Create Alert
**Objective**: Verify alert creation functionality
**Priority**: High
**Preconditions**: Authenticated user

**Test Steps**:
1. Send POST request to `/api/alerts` with alert configuration
2. Verify alert stored in database
3. Test various threshold types
4. Test invalid configurations

**Test Data**:
```json
{
  "asset": "AAPL",
  "threshold": 0.5,
  "direction": "above",
  "notification_type": "email"
}
```

**Expected Results**:
- Alert created successfully
- Configuration validated
- Invalid configurations rejected

---

### TC-ALERT-002: Alert Triggering
**Objective**: Verify alert triggering mechanism
**Priority**: High
**Preconditions**: Active alerts configured

**Test Steps**:
1. Create alert with specific threshold
2. Generate sentiment data that crosses threshold
3. Verify alert triggered
4. Check alert notification sent

**Expected Results**:
- Alert triggers when threshold crossed
- Notification sent promptly
- Alert status updated correctly

---

### TC-ALERT-003: Alert Management
**Objective**: Verify alert CRUD operations
**Priority**: Medium
**Preconditions**: Alerts exist

**Test Steps**:
1. List all user alerts (GET `/api/alerts`)
2. Update alert configuration (PUT `/api/alerts/{id}`)
3. Delete alert (DELETE `/api/alerts/{id}`)
4. Test bulk operations

**Expected Results**:
- All CRUD operations work correctly
- Data integrity maintained
- Proper error handling

---

## 6. Real-Time Updates Test Cases

### TC-REALTIME-001: WebSocket Connection
**Objective**: Verify WebSocket connectivity and data flow
**Priority**: High
**Preconditions**: Server running, authentication available

**Test Steps**:
1. Establish WebSocket connection to `/ws/sentiment`
2. Verify connection established
3. Generate sentiment updates
4. Verify real-time data received

**Expected Results**:
- WebSocket connection successful
- Real-time updates received
- Data format correct
- Connection stable

---

### TC-REALTIME-002: WebSocket Authentication
**Objective**: Verify WebSocket authentication
**Priority**: High
**Preconditions**: JWT token available

**Test Steps**:
1. Connect to WebSocket with valid token
2. Connect with invalid token
3. Connect without token
4. Test token expiration during connection

**Expected Results**:
- Valid tokens allow connection
- Invalid tokens rejected
- Proper error messages
- Graceful handling of token expiration

---

### TC-REALTIME-003: Multiple Client Handling
**Objective**: Verify multiple WebSocket clients
**Priority**: Medium
**Preconditions**: Server capacity available

**Test Steps**:
1. Establish multiple WebSocket connections
2. Generate sentiment updates
3. Verify all clients receive updates
4. Test client disconnection scenarios

**Expected Results**:
- Multiple clients supported
- All clients receive updates
- Disconnections handled gracefully
- No memory leaks

---

## 7. RSS Ingestion Test Cases

### TC-RSS-001: Scheduled Ingestion
**Objective**: Verify scheduled RSS feed ingestion
**Priority**: High
**Preconditions**: RSS sources configured

**Test Steps**:
1. Verify scheduler is running
2. Monitor ingestion job execution
3. Check articles added to database
4. Verify deduplication works

**Expected Results**:
- Ingestion runs on schedule
- Articles successfully parsed and stored
- Duplicates properly handled
- Error logging functional

---

### TC-RSS-002: Manual Ingestion Trigger
**Objective**: Verify manual ingestion trigger
**Priority**: Medium
**Preconditions**: Admin access

**Test Steps**:
1. Send POST request to `/api/ingestion/trigger`
2. Monitor ingestion process
3. Verify articles processed
4. Check ingestion metrics

**Expected Results**:
- Manual trigger works
- Ingestion completes successfully
- Metrics updated correctly

---

## 8. Performance & Monitoring Test Cases

### TC-PERF-001: Health Check
**Objective**: Verify system health monitoring
**Priority**: High
**Preconditions**: Server running

**Test Steps**:
1. Send GET request to `/health`
2. Verify response time
3. Check system status information
4. Test under load conditions

**Expected Results**:
- Health check responds quickly (<100ms)
- Accurate system status reported
- Performance acceptable under load

---

### TC-PERF-002: Metrics Collection
**Objective**: Verify metrics collection and reporting
**Priority**: Medium
**Preconditions**: Prometheus configured

**Test Steps**:
1. Access metrics endpoint `/metrics`
2. Verify metrics format
3. Check key performance indicators
4. Verify metrics accuracy

**Expected Results**:
- Metrics endpoint accessible
- Prometheus format correct
- Key metrics present and accurate

---

## 9. Error Handling Test Cases

### TC-ERROR-001: Database Connection Failure
**Objective**: Verify graceful handling of database issues
**Priority**: High
**Preconditions**: Ability to simulate DB failure

**Test Steps**:
1. Simulate database connection failure
2. Send various API requests
3. Verify error responses
4. Check system recovery

**Expected Results**:
- Proper error responses (503 Service Unavailable)
- No system crashes
- Graceful recovery when DB restored

---

### TC-ERROR-002: External Service Failures
**Objective**: Verify handling of external service failures
**Priority**: Medium
**Preconditions**: External dependencies identified

**Test Steps**:
1. Simulate RSS feed unavailability
2. Simulate FinBERT service failure
3. Test API responses during failures
4. Verify fallback mechanisms

**Expected Results**:
- Graceful degradation of service
- Appropriate error messages
- System remains stable

---

## Test Execution Guidelines

### Pre-Test Setup
1. Ensure server is running on localhost:8000
2. Database is accessible and populated with test data
3. Authentication tokens are available
4. Monitoring systems are active

### Test Environment
- **Base URL**: http://localhost:8000
- **Database**: PostgreSQL with test data
- **Authentication**: JWT tokens
- **Monitoring**: Prometheus metrics enabled

### Test Data Requirements
- Sample articles across different assets
- Historical sentiment data
- User accounts for authentication testing
- RSS feed test data

### Success Criteria
- All high-priority test cases pass
- Performance requirements met
- Error handling works correctly
- Real-time features functional
- Data integrity maintained

### Reporting
- Document all test results
- Report any failures with detailed steps to reproduce
- Include performance metrics
- Provide recommendations for improvements 