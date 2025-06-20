#!/usr/bin/env python3
"""
Test script for the new sentiment streaming endpoint.
"""

import requests
import json
from datetime import datetime, timedelta


def test_streaming_endpoint():
    """Test the /api/sentiment/stream endpoint."""
    base_url = "http://localhost:8000"
    
    print("Testing sentiment streaming endpoint...")
    
    # Test 1: Basic endpoint without parameters
    print("\n1. Testing basic endpoint (no parameters):")
    try:
        response = requests.get(f"{base_url}/api/sentiment/stream")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response keys: {list(data.keys())}")
            print(f"Updates count: {len(data.get('updates', []))}")
            print(f"Aggregates count: {len(data.get('aggregates', []))}")
            print(f"Alerts count: {len(data.get('alerts', []))}")
            print(f"Metadata: {data.get('metadata', {})}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: With timestamp parameter
    print("\n2. Testing with timestamp parameter:")
    try:
        # Get data from 2 hours ago
        since_time = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        response = requests.get(f"{base_url}/api/sentiment/stream?since={since_time}")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Updates count: {len(data.get('updates', []))}")
            print(f"Aggregates count: {len(data.get('aggregates', []))}")
            print(f"Since timestamp: {data.get('metadata', {}).get('since')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Check API documentation
    print("\n3. Testing API documentation availability:")
    try:
        response = requests.get(f"{base_url}/openapi.json")
        print(f"OpenAPI Schema Status: {response.status_code}")
        
        if response.status_code == 200:
            openapi_data = response.json()
            paths = openapi_data.get("paths", {})
            streaming_path = "/api/sentiment/stream"
            
            if streaming_path in paths:
                print(f"✓ Streaming endpoint documented in OpenAPI schema")
                endpoint_info = paths[streaming_path]
                print(f"  Methods: {list(endpoint_info.keys())}")
                
                if "get" in endpoint_info:
                    get_info = endpoint_info["get"]
                    print(f"  Summary: {get_info.get('summary', 'N/A')}")
                    print(f"  Parameters: {len(get_info.get('parameters', []))}")
            else:
                print(f"✗ Streaming endpoint not found in OpenAPI schema")
        else:
            print(f"Failed to get OpenAPI schema: {response.text}")
    except Exception as e:
        print(f"Error checking API docs: {e}")


if __name__ == "__main__":
    test_streaming_endpoint() 