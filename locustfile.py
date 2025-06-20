#!/usr/bin/env python3
"""
Locust load testing file for Week 7: TradeEasy API Load Testing

This file defines load tests for critical API endpoints:
1. /api/search - Full-text search functionality
2. /api/history - Sentiment history queries
3. Additional endpoints for comprehensive testing

Usage:
    locust -f locustfile.py --host=http://localhost:8000
    
Web UI will be available at: http://localhost:8089
"""

import random
import time
from datetime import datetime, timedelta
from locust import HttpUser, task, between, events
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradeEasyAPIUser(HttpUser):
    """
    Simulates a user interacting with the TradeEasy API.
    
    This user performs various API operations including searching,
    retrieving sentiment history, and other common operations.
    """
    
    # Wait between 1-5 seconds between tasks (simulating real user behavior)
    wait_time = between(1, 5)
    
    def on_start(self):
        """Initialize user session with authentication."""
        self.auth_token = None
        self.available_assets = [
            "BTC", "ETH", "AAPL", "TSLA", "GOOGL", "MSFT", 
            "EUR/USD", "USD/JPY", "GBP/USD", "GOLD", "SILVER", "OIL"
        ]
        self.search_queries = [
            "Bitcoin", "Federal Reserve", "inflation", "earnings",
            "market", "price", "stock", "cryptocurrency", "economy",
            "growth", "revenue", "profit", "analysis", "forecast"
        ]
        
        # Authenticate user
        self.authenticate()
    
    def authenticate(self):
        """Authenticate user and get access token."""
        try:
            response = self.client.get("/api/auth/demo-login")
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                logger.info("Authentication successful")
            else:
                logger.warning(f"Authentication failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Authentication error: {e}")
    
    @property
    def auth_headers(self):
        """Get authentication headers."""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}
    
    @task(30)
    def search_articles(self):
        """
        Test the /api/search endpoint (HIGH PRIORITY - 30% of requests).
        
        This is the primary endpoint being load tested as specified.
        """
        query = random.choice(self.search_queries)
        limit = random.choice([5, 10, 20, 50])
        skip = random.choice([0, 5, 10, 20])
        
        with self.client.get(
            f"/api/search/?q={query}&limit={limit}&skip={skip}",
            catch_response=True,
            name="/api/search (main endpoint)"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "results" in data and "total_count" in data:
                        response.success()
                        # Log performance metrics
                        response_time = response.elapsed.total_seconds()
                        if response_time > 2.0:
                            logger.warning(f"Slow search response: {response_time:.2f}s for query '{query}'")
                    else:
                        response.failure("Invalid response format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(25)
    def get_sentiment_history(self):
        """
        Test the /api/sentiment/history endpoint (HIGH PRIORITY - 25% of requests).
        
        This is the second primary endpoint being load tested as specified.
        """
        asset = random.choice(self.available_assets)
        time_range = random.choice(["1h", "24h", "7d", "30d"])
        
        with self.client.get(
            f"/api/sentiment/history?asset={asset}&range={time_range}",
            catch_response=True,
            name="/api/sentiment/history (main endpoint)"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        response.success()
                        # Log performance metrics
                        response_time = response.elapsed.total_seconds()
                        if response_time > 1.5:
                            logger.warning(f"Slow history response: {response_time:.2f}s for {asset} ({time_range})")
                    else:
                        response.failure("Invalid response format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 404:
                # 404 is acceptable if no data exists for the asset
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(15)
    def search_articles_only(self):
        """Test the /api/search/articles endpoint (MEDIUM PRIORITY - 15% of requests)."""
        query = random.choice(self.search_queries)
        limit = random.choice([3, 5, 10])
        
        with self.client.get(
            f"/api/search/articles?q={query}&limit={limit}",
            catch_response=True,
            name="/api/search/articles"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(10)
    def analyze_sentiment(self):
        """Test the /api/sentiment/article endpoint (MEDIUM PRIORITY - 10% of requests)."""
        test_texts = [
            "Apple Inc. reported strong quarterly earnings exceeding analyst expectations.",
            "The Federal Reserve announced an interest rate decision affecting market sentiment.",
            "Bitcoin price shows volatility as investors evaluate market conditions.",
            "Company stocks rise on positive economic indicators and growth forecasts.",
            "Market uncertainty continues as analysts review financial performance metrics."
        ]
        
        text = random.choice(test_texts)
        
        with self.client.post(
            "/api/sentiment/article",
            json={"text": text},
            catch_response=True,
            name="/api/sentiment/article"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "lexicon_score" in data and "finbert_score" in data:
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(8)
    def get_latest_sentiment(self):
        """Test the /api/sentiment/latest endpoint (MEDIUM PRIORITY - 8% of requests)."""
        asset = random.choice(self.available_assets)
        
        with self.client.get(
            f"/api/sentiment/latest?asset={asset}",
            catch_response=True,
            name="/api/sentiment/latest"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "asset_symbol" in data and "latest_sentiment" in data:
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 404:
                # 404 is acceptable if no sentiment data exists
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(5)
    def get_search_stats(self):
        """Test the /api/search/stats endpoint (LOW PRIORITY - 5% of requests)."""
        with self.client.get(
            "/api/search/stats",
            catch_response=True,
            name="/api/search/stats"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "total_articles" in data and "database_type" in data:
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(3)
    def health_check(self):
        """Test health endpoints (LOW PRIORITY - 3% of requests)."""
        with self.client.get("/health", name="/health") as response:
            if response.status_code != 200:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(2)
    def api_status(self):
        """Test API status endpoint (LOW PRIORITY - 2% of requests)."""
        with self.client.get("/api/status", name="/api/status") as response:
            if response.status_code != 200:
                response.failure(f"API status failed: {response.status_code}")
    
    @task(2)
    def test_authenticated_endpoints(self):
        """Test authenticated endpoints if auth is available (LOW PRIORITY - 2% of requests)."""
        if not self.auth_token:
            return
        
        # Test watchlists endpoint
        with self.client.get(
            "/api/watchlists/",
            headers=self.auth_headers,
            catch_response=True,
            name="/api/watchlists (authenticated)"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                # Re-authenticate if token expired
                self.authenticate()
            else:
                response.failure(f"HTTP {response.status_code}")


class HighLoadUser(TradeEasyAPIUser):
    """
    High-load user for stress testing.
    
    This user type focuses heavily on the primary endpoints 
    (/api/search and /api/history) with minimal wait times.
    """
    
    # Reduced wait time for stress testing
    wait_time = between(0.1, 1.0)
    
    @task(50)
    def search_stress_test(self):
        """Stress test the search endpoint."""
        query = random.choice(self.search_queries)
        # Use more aggressive parameters for stress testing
        limit = random.choice([20, 50, 100])
        
        with self.client.get(
            f"/api/search/?q={query}&limit={limit}",
            catch_response=True,
            name="/api/search (stress test)"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(50)
    def history_stress_test(self):
        """Stress test the history endpoint."""
        asset = random.choice(self.available_assets)
        time_range = random.choice(["7d", "30d"])  # Use longer ranges for stress
        
        with self.client.get(
            f"/api/sentiment/history?asset={asset}&range={time_range}",
            catch_response=True,
            name="/api/sentiment/history (stress test)"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


# Locust event handlers for custom reporting
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Custom request handler for detailed logging."""
    if exception:
        logger.error(f"Request failed: {name} - {exception}")
    elif response_time > 2000:  # Log slow requests (>2 seconds)
        logger.warning(f"Slow request: {name} took {response_time}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test start information."""
    logger.info("🚀 Starting TradeEasy API Load Testing")
    logger.info(f"Target host: {environment.host}")
    logger.info("Primary endpoints under test:")
    logger.info("  - /api/search (Full-text search)")
    logger.info("  - /api/sentiment/history (Sentiment history)")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log test completion information."""
    logger.info("📊 TradeEasy API Load Testing Complete")
    if environment.stats.total:
        logger.info(f"Total requests: {environment.stats.total.num_requests}")
        logger.info(f"Failed requests: {environment.stats.total.num_failures}")
        logger.info(f"Average response time: {environment.stats.total.avg_response_time:.2f}ms")
        logger.info(f"Max response time: {environment.stats.total.max_response_time:.2f}ms")


# Custom user classes for different testing scenarios
class SearchFocusedUser(TradeEasyAPIUser):
    """User that focuses primarily on search functionality."""
    
    @task(80)
    def focused_search(self):
        """Heavily focus on search operations."""
        self.search_articles()
    
    @task(20)
    def search_supporting_ops(self):
        """Supporting operations for search testing."""
        choice = random.choice([
            self.search_articles_only,
            self.get_search_stats,
            self.health_check
        ])
        choice()


class HistoryFocusedUser(TradeEasyAPIUser):
    """User that focuses primarily on history functionality."""
    
    @task(80)
    def focused_history(self):
        """Heavily focus on history operations."""
        self.get_sentiment_history()
    
    @task(20)
    def history_supporting_ops(self):
        """Supporting operations for history testing."""
        choice = random.choice([
            self.get_latest_sentiment,
            self.analyze_sentiment,
            self.health_check
        ])
        choice()


# Example usage:
# 
# Basic load testing:
#   locust -f locustfile.py --host=http://localhost:8000
#
# High-load stress testing:
#   locust -f locustfile.py --host=http://localhost:8000 -u 100 -r 10 --run-time 300s
#
# Search-focused testing:
#   locust -f locustfile.py SearchFocusedUser --host=http://localhost:8000
#
# History-focused testing:
#   locust -f locustfile.py HistoryFocusedUser --host=http://localhost:8000
#
# Headless testing (no web UI):
#   locust -f locustfile.py --host=http://localhost:8000 --headless -u 50 -r 5 --run-time 120s 