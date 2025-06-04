#!/usr/bin/env python3
"""Final verification test for Week 4 watchlist and alerts implementation."""

import sys
import time
import requests
import json

BASE_URL = "http://localhost:8000"

def test_endpoint(method, url, **kwargs):
    """Test an endpoint and return response data."""
    try:
        if method.upper() == "GET":
            response = requests.get(url, **kwargs)
        elif method.upper() == "POST":
            response = requests.post(url, **kwargs)
        elif method.upper() == "DELETE":
            response = requests.delete(url, **kwargs)
        else:
            return False, f"Unsupported method: {method}"
        
        print(f"{method.upper()} {url} -> {response.status_code}")
        
        if response.status_code >= 400:
            print(f"  Error: {response.text}")
            return False, response.text
        
        try:
            data = response.json()
            print(f"  Response: {json.dumps(data, indent=2, default=str)[:200]}...")
            return True, data
        except:
            return True, response.text
            
    except Exception as e:
        print(f"  Exception: {e}")
        return False, str(e)


def main():
    """Run comprehensive tests for Week 4 implementation."""
    print("=" * 60)
    print("WEEK 4 FINAL VERIFICATION TEST")
    print("=" * 60)
    
    # Wait for server to start
    print("\n1. Waiting for server to start...")
    time.sleep(3)
    
    # Test 1: Server health
    print("\n2. Testing server health...")
    success, data = test_endpoint("GET", f"{BASE_URL}/health")
    if not success:
        print("❌ Server health check failed")
        return False
    print("✅ Server health check passed")
    
    # Test 2: API status
    print("\n3. Testing API status...")
    success, data = test_endpoint("GET", f"{BASE_URL}/api/status")
    if not success:
        print("❌ API status check failed")
        return False
    print("✅ API status check passed")
    
    # Test 3: Authentication
    print("\n4. Testing authentication...")
    success, auth_data = test_endpoint("GET", f"{BASE_URL}/api/auth/demo-login")
    if not success:
        print("❌ Authentication failed")
        return False
    
    # Extract token
    token = auth_data.get("access_token")
    if not token:
        print("❌ No access token received")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Authentication passed")
    
    # Test 4: Watchlist endpoints
    print("\n5. Testing watchlist endpoints...")
    
    # Get watchlists
    success, data = test_endpoint("GET", f"{BASE_URL}/api/watchlists/", headers=headers)
    if not success:
        print("❌ Get watchlists failed")
        return False
    print("✅ Get watchlists passed")
    
    # Get watchlist stats
    success, data = test_endpoint("GET", f"{BASE_URL}/api/watchlists/stats", headers=headers)
    if not success:
        print("❌ Get watchlist stats failed")
        return False
    print("✅ Get watchlist stats passed")
    
    # Test 5: Alert endpoints
    print("\n6. Testing alert endpoints...")
    
    # Get alerts
    success, data = test_endpoint("GET", f"{BASE_URL}/api/alerts/", headers=headers)
    if not success:
        print("❌ Get alerts failed")
        return False
    print("✅ Get alerts passed")
    
    # Get alert stats
    success, data = test_endpoint("GET", f"{BASE_URL}/api/alerts/stats", headers=headers)
    if not success:
        print("❌ Get alert stats failed")
        return False
    print("✅ Get alert stats passed")
    
    # Test 6: Alert creation
    print("\n7. Testing alert creation...")
    success, data = test_endpoint(
        "POST", 
        f"{BASE_URL}/api/alerts/?asset_symbol=AAPL&threshold=0.5&direction=above",
        headers=headers
    )
    if not success:
        print("❌ Alert creation failed")
        return False
    print("✅ Alert creation passed")
    
    # Test alerts again to confirm it shows up
    success, data = test_endpoint("GET", f"{BASE_URL}/api/alerts/", headers=headers)
    if not success:
        print("❌ Get alerts after creation failed")
        return False
    
    if len(data) == 0:
        print("❌ No alerts found after creation")
        return False
    print("✅ Alert retrieval after creation passed")
    
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED! Week 4 implementation is complete!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 