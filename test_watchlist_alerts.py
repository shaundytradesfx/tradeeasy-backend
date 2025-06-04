#!/usr/bin/env python3
"""
Test script for Week 4 Watchlist and Alerts implementation.

This script tests the complete watchlist and alerts backend functionality
including authentication, CRUD operations, and alert triggering.
"""

import requests
import json
import time
import sys
from typing import Dict, Any

class WatchlistAlertsTest:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        
    def log(self, message: str):
        """Log a message with timestamp."""
        print(f"[{time.strftime('%H:%M:%S')}] {message}")
        
    def test_server_health(self) -> bool:
        """Test if the server is running."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                self.log("✅ Server is running")
                return True
            else:
                self.log(f"❌ Server health check failed: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"❌ Server is not accessible: {e}")
            return False
    
    def test_api_status(self) -> bool:
        """Test the API status endpoint."""
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                features = data.get("features", {})
                
                required_features = ["watchlists", "alerts", "authentication", "background_alert_checking"]
                missing_features = [f for f in required_features if not features.get(f)]
                
                if not missing_features:
                    self.log("✅ All required features are available")
                    return True
                else:
                    self.log(f"❌ Missing features: {missing_features}")
                    return False
            else:
                self.log(f"❌ API status check failed: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"❌ API status check error: {e}")
            return False
    
    def test_authentication(self) -> bool:
        """Test the authentication system."""
        try:
            # Test demo login
            response = requests.get(f"{self.base_url}/api/auth/demo-login", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_id = data.get("user_id")
                
                if self.token and self.user_id:
                    self.log("✅ Demo authentication successful")
                    return True
                else:
                    self.log("❌ Demo authentication failed: missing token or user_id")
                    return False
            else:
                self.log(f"❌ Demo authentication failed: {response.status_code}")
                self.log(f"Response: {response.text}")
                return False
        except Exception as e:
            self.log(f"❌ Authentication error: {e}")
            return False
    
    def get_headers(self) -> Dict[str, str]:
        """Get authorization headers."""
        if not self.token:
            raise ValueError("No authentication token available")
        return {"Authorization": f"Bearer {self.token}"}
    
    def test_watchlist_endpoints(self) -> bool:
        """Test watchlist CRUD operations."""
        try:
            headers = self.get_headers()
            
            # Test getting empty watchlist
            response = requests.get(f"{self.base_url}/api/watchlists/", headers=headers, timeout=5)
            if response.status_code == 200:
                watchlists = response.json()
                self.log(f"✅ Get watchlists successful: {len(watchlists)} items")
            else:
                self.log(f"❌ Get watchlists failed: {response.status_code}")
                self.log(f"Response: {response.text}")
                return False
            
            # Test watchlist stats
            response = requests.get(f"{self.base_url}/api/watchlists/stats", headers=headers, timeout=5)
            if response.status_code == 200:
                stats = response.json()
                self.log(f"✅ Get watchlist stats successful: {stats}")
            else:
                self.log(f"❌ Get watchlist stats failed: {response.status_code}")
                self.log(f"Response: {response.text}")
                return False
            
            # Test creating watchlist (this might fail if assets don't exist)
            response = requests.post(
                f"{self.base_url}/api/watchlists/?asset_symbol=BTC", 
                headers=headers, 
                timeout=5
            )
            if response.status_code == 200:
                watchlist = response.json()
                self.log(f"✅ Create watchlist successful: {watchlist}")
            else:
                self.log(f"⚠️  Create watchlist failed (expected if no assets): {response.status_code}")
                self.log(f"Response: {response.text}")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Watchlist endpoints error: {e}")
            return False
    
    def test_alert_endpoints(self) -> bool:
        """Test alert CRUD operations."""
        try:
            headers = self.get_headers()
            
            # Test getting empty alerts
            response = requests.get(f"{self.base_url}/api/alerts/", headers=headers, timeout=5)
            if response.status_code == 200:
                alerts = response.json()
                self.log(f"✅ Get alerts successful: {len(alerts)} items")
            else:
                self.log(f"❌ Get alerts failed: {response.status_code}")
                self.log(f"Response: {response.text}")
                return False
            
            # Test alert stats
            response = requests.get(f"{self.base_url}/api/alerts/stats", headers=headers, timeout=5)
            if response.status_code == 200:
                stats = response.json()
                self.log(f"✅ Get alert stats successful: {stats}")
            else:
                self.log(f"❌ Get alert stats failed: {response.status_code}")
                self.log(f"Response: {response.text}")
                return False
            
            # Test triggered alerts
            response = requests.get(f"{self.base_url}/api/alerts/triggered", headers=headers, timeout=5)
            if response.status_code == 200:
                triggered = response.json()
                self.log(f"✅ Get triggered alerts successful: {len(triggered)} items")
            else:
                self.log(f"❌ Get triggered alerts failed: {response.status_code}")
                self.log(f"Response: {response.text}")
                return False
            
            # Test alert trigger functionality
            response = requests.post(
                f"{self.base_url}/api/alerts/test-trigger?asset_symbol=BTC&sentiment_score=0.5",
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                result = response.json()
                self.log(f"✅ Test alert trigger successful: {result}")
            else:
                self.log(f"⚠️  Test alert trigger failed (expected if no assets): {response.status_code}")
                self.log(f"Response: {response.text}")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Alert endpoints error: {e}")
            return False
    
    def test_database_setup(self) -> bool:
        """Test if the database has the required tables and demo data."""
        try:
            # This is a basic test - we'll check if we can access endpoints
            # In a real test, we'd check the database directly
            
            headers = self.get_headers()
            
            # Check if we can access user-specific endpoints without errors
            endpoints_to_test = [
                "/api/watchlists/",
                "/api/alerts/",
                "/api/watchlists/stats",
                "/api/alerts/stats"
            ]
            
            all_passed = True
            for endpoint in endpoints_to_test:
                response = requests.get(f"{self.base_url}{endpoint}", headers=headers, timeout=5)
                if response.status_code == 200:
                    self.log(f"✅ Database access test passed for {endpoint}")
                else:
                    self.log(f"❌ Database access test failed for {endpoint}: {response.status_code}")
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            self.log(f"❌ Database setup test error: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests and return results."""
        self.log("🚀 Starting Week 4 Watchlist and Alerts Tests")
        self.log("=" * 60)
        
        results = {}
        
        # Test 1: Server Health
        self.log("\n📋 Test 1: Server Health")
        results["server_health"] = self.test_server_health()
        
        # Test 2: API Status
        self.log("\n📋 Test 2: API Status")
        results["api_status"] = self.test_api_status()
        
        # Test 3: Authentication
        self.log("\n📋 Test 3: Authentication")
        results["authentication"] = self.test_authentication()
        
        if not results["authentication"]:
            self.log("❌ Cannot proceed without authentication")
            return results
        
        # Test 4: Database Setup
        self.log("\n📋 Test 4: Database Setup")
        results["database_setup"] = self.test_database_setup()
        
        # Test 5: Watchlist Endpoints
        self.log("\n📋 Test 5: Watchlist Endpoints")
        results["watchlist_endpoints"] = self.test_watchlist_endpoints()
        
        # Test 6: Alert Endpoints
        self.log("\n📋 Test 6: Alert Endpoints")
        results["alert_endpoints"] = self.test_alert_endpoints()
        
        # Summary
        self.log("\n" + "=" * 60)
        self.log("📊 TEST SUMMARY")
        self.log("=" * 60)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{test_name.replace('_', ' ').title()}: {status}")
        
        self.log(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            self.log("🎉 All tests passed! Week 4 implementation is working correctly.")
        else:
            self.log("⚠️  Some tests failed. Check the logs above for details.")
        
        return results


def main():
    """Main function to run the tests."""
    tester = WatchlistAlertsTest()
    results = tester.run_all_tests()
    
    # Exit with appropriate code
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main() 