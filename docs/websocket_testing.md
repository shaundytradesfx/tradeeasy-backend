# WebSocket Integration Tests for TradeEasy - Week 5

This document describes the comprehensive WebSocket integration testing suite for the TradeEasy real-time sentiment broadcasting system.

## Overview

The WebSocket integration tests validate the complete real-time functionality of the TradeEasy system, including:

- Multi-client WebSocket connections
- Real-time sentiment broadcasting during RSS ingestion
- Alert triggering and notification broadcasting
- Connection lifecycle management
- Performance under load
- Data integrity and message validation

## Test Structure

### Test Files

1. **`tests/test_websocket_integration.py`**
   - Core WebSocket functionality tests
   - Connection management and lifecycle
   - Message validation and broadcasting
   - Error handling scenarios

2. **`tests/test_websocket_load.py`**
   - Performance and load testing
   - Concurrent connection handling
   - Memory usage monitoring
   - Stress testing scenarios

3. **`tests/test_websocket_rss_integration.py`**
   - RSS ingestion and WebSocket integration
   - Real-time sentiment broadcasting
   - Alert triggering during ingestion
   - Multi-client broadcasting validation

4. **`run_websocket_tests.py`**
   - Test runner script
   - Comprehensive reporting
   - Configurable test execution

## Running the Tests

### Prerequisites

1. **Start the TradeEasy Server**
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

2. **Install Test Dependencies**
   ```bash
   pip install websockets aiohttp psutil
   ```

### Test Execution Options

#### 1. Run All Tests
```bash
python run_websocket_tests.py
```

#### 2. Quick Tests Only (Skip Load Tests)
```bash
python run_websocket_tests.py --quick
```

#### 3. Load Tests Only
```bash
python run_websocket_tests.py --load-only
```

#### 4. Specific Test Module
```bash
python run_websocket_tests.py --module test_websocket_integration
```

#### 5. Individual Test Classes
```bash
# Core integration tests
python -m unittest tests.test_websocket_integration -v

# Load tests
python -m unittest tests.test_websocket_load -v

# RSS integration tests
python -m unittest tests.test_websocket_rss_integration -v
```

#### 6. Single Test Method
```bash
python -m unittest tests.test_websocket_integration.TestWebSocketIntegration.test_single_websocket_connection -v
```

## Test Coverage

### Core WebSocket Functionality

- **Connection Management**
  - Single and multiple client connections
  - Connection lifecycle (connect, disconnect, reconnect)
  - Connection statistics and metadata tracking
  - Error handling and recovery

- **Message Broadcasting**
  - Sentiment updates (`sentiment_update`)
  - Aggregate updates (`aggregate_update`)
  - Alert triggers (`alert_triggered`)
  - Connection establishment messages
  - Echo functionality

- **Data Validation**
  - Message structure verification
  - Data integrity checks
  - Timestamp validation
  - Content accuracy

### Integration with Backend Systems

- **RSS Ingestion Integration**
  - Real-time broadcasting during article processing
  - Sentiment analysis triggering broadcasts
  - Multiple feed processing validation

- **Alert System Integration**
  - Alert threshold crossing detection
  - Real-time alert broadcasting
  - User-specific alert handling

- **Database Integration**
  - Hourly aggregate computation broadcasting
  - Sentiment data persistence validation
  - Asset and user data consistency

### Performance and Load Testing

- **Light Load (10 clients)**
  - >95% success rate
  - <1 second connection time
  - <5% error rate

- **Medium Load (50 clients)**
  - >90% success rate
  - <2 seconds connection time
  - <10% error rate

- **Heavy Load (100 clients)**
  - >80% success rate
  - <5 seconds connection time
  - <20% error rate

- **Burst Connections**
  - Simultaneous connection handling
  - <10 seconds maximum connection time
  - <25% error rate

- **Memory Usage**
  - Memory leak detection
  - Resource cleanup validation
  - Performance under sustained load

## Test Results Interpretation

### Success Metrics

- **Connection Success Rate**: Percentage of successful WebSocket connections
- **Message Delivery Rate**: Percentage of messages successfully delivered
- **Error Rate**: Percentage of failed operations
- **Response Time**: Average time for connections and message delivery
- **Memory Usage**: Resource consumption during testing

### Expected Performance Benchmarks

| Test Type | Connections | Success Rate | Avg Connection Time | Error Rate |
|-----------|-------------|--------------|-------------------|------------|
| Light     | 10          | ≥95%         | <1s               | <5%        |
| Medium    | 50          | ≥90%         | <2s               | <10%       |
| Heavy     | 100         | ≥80%         | <5s               | <20%       |

### Common Issues and Troubleshooting

1. **Server Not Running**
   ```
   Error: TradeEasy server is not running on http://127.0.0.1:8000
   Solution: Start the server with uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

2. **Connection Timeouts**
   ```
   Possible causes: High server load, network issues, resource exhaustion
   Solution: Reduce concurrent connections, check server resources
   ```

3. **Import Errors**
   ```
   Error: No module named 'websockets'
   Solution: pip install websockets aiohttp psutil
   ```

4. **Database Lock Errors**
   ```
   Error: Database is locked
   Solution: Ensure no other tests are running, restart the server
   ```

## Test Architecture

### WebSocket Test Clients

- **`WebSocketTestClient`**: Basic WebSocket client for functional testing
- **`LoadTestWebSocketClient`**: Performance-focused client with metrics collection
- **`RSSWebSocketTestClient`**: Specialized client for RSS integration testing

### Metrics Collection

- **`LoadTestMetrics`**: Comprehensive performance metrics collection
- Connection time tracking
- Message delivery monitoring
- Error rate calculation
- Memory usage analysis

### Async Test Execution

- **`AsyncTestRunner`**: Helper class for running async tests in unittest
- Event loop management
- Timeout handling
- Exception propagation

## Continuous Integration

### GitHub Actions Integration

```yaml
name: WebSocket Integration Tests
on: [push, pull_request]
jobs:
  websocket-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install websockets aiohttp psutil
      - name: Start server
        run: uvicorn app.main:app --host 127.0.0.1 --port 8000 &
      - name: Wait for server
        run: sleep 10
      - name: Run WebSocket tests
        run: python run_websocket_tests.py --quick
```

### Local Development Workflow

1. **Pre-commit Testing**
   ```bash
   python run_websocket_tests.py --quick
   ```

2. **Full Testing Before Release**
   ```bash
   python run_websocket_tests.py
   ```

3. **Performance Regression Testing**
   ```bash
   python run_websocket_tests.py --load-only
   ```

## Week 5 Implementation Validation

The WebSocket integration tests specifically validate the Week 5 requirements:

### ✅ Real-time WebSocket Endpoint
- `/ws/sentiment` endpoint functional
- Connection management working
- Message broadcasting operational

### ✅ RSS Ingestion Integration
- Sentiment updates broadcast during ingestion
- Alert checking and broadcasting
- Hourly aggregate broadcasting

### ✅ Multi-client Support
- Concurrent connection handling
- Broadcast delivery to all clients
- Connection isolation and cleanup

### ✅ Performance Requirements
- Production-ready performance metrics
- Load testing validation
- Memory usage optimization

### ✅ Data Integrity
- Message structure validation
- Content accuracy verification
- Timestamp consistency

## Future Enhancements

### Authentication Testing
- JWT token validation
- User-specific broadcasting
- Permission-based access control

### Scalability Testing
- Database connection pooling
- Redis broadcasting (if implemented)
- Horizontal scaling validation

### Advanced Monitoring
- Real-time performance dashboards
- Alert fatigue prevention
- Client connection analytics

## Conclusion

The WebSocket integration test suite provides comprehensive validation of the TradeEasy real-time sentiment broadcasting system. It ensures that the Week 5 implementation meets all functional and performance requirements while providing tools for ongoing quality assurance and performance monitoring.

For questions or issues with the WebSocket testing suite, please refer to the test logs or create an issue in the project repository. 