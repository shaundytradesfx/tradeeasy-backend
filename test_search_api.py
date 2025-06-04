"""
Test script for Search API functionality.
Tests both basic search functionality and performance with sample data.
"""

import time
import requests
import json
from datetime import datetime, timedelta
from uuid import uuid4


def test_search_api():
    """Test the search API endpoints with sample data."""
    
    base_url = "http://localhost:8000/api"
    
    print("🔍 Testing TradeEasy Search API")
    print("=" * 50)
    
    # Test 1: Check API health and search stats
    print("\n1. Testing search stats endpoint...")
    try:
        response = requests.get(f"{base_url}/search/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"   ✅ Search stats: {stats}")
        else:
            print(f"   ❌ Failed to get search stats: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting search stats: {e}")
    
    # Test 2: Create sample articles for testing
    print("\n2. Creating sample financial articles...")
    sample_articles = [
        {
            "title": "Federal Reserve Raises Interest Rates to Combat Inflation",
            "content": "The Federal Reserve announced today that it is raising the federal funds rate by 0.75 percentage points to help combat rising inflation. Fed Chairman Jerome Powell stated that the central bank is committed to bringing inflation back to its 2% target. The decision comes as inflation continues to remain elevated above the Fed's target, with consumer prices rising at their fastest pace in decades. This rate hike is the latest in a series of aggressive moves by the Fed to cool down the overheated economy.",
            "source": "Financial News Today",
            "url": f"https://example.com/fed-rate-decision-{uuid4()}",
            "published_at": datetime.utcnow().isoformat()
        },
        {
            "title": "Bitcoin Price Surges Following Major Institutional Adoption",
            "content": "Bitcoin reached new highs today following announcements from several major financial institutions about their plans to integrate cryptocurrency into their services. The digital currency climbed above $50,000 as investors showed renewed confidence in the crypto market. Major players including JPMorgan and Goldman Sachs have announced new crypto trading desks, while Tesla confirmed it will continue accepting Bitcoin payments for its vehicles. Market analysts believe this institutional adoption could drive further price appreciation in the coming months.",
            "source": "Crypto Daily",
            "url": f"https://example.com/bitcoin-surge-{uuid4()}",
            "published_at": (datetime.utcnow() - timedelta(hours=2)).isoformat()
        },
        {
            "title": "Apple Reports Strong Q4 Earnings Despite Supply Chain Challenges",
            "content": "Apple Inc. reported better-than-expected fourth quarter earnings, with revenue of $83.4 billion despite ongoing supply chain disruptions. The tech giant's iPhone sales remained robust, while its services division continued to show strong growth. CEO Tim Cook praised the company's ability to navigate supply chain challenges and expressed optimism about future prospects. The company also announced increased investment in its manufacturing capabilities to reduce dependence on overseas suppliers.",
            "source": "Tech Business Weekly",
            "url": f"https://example.com/apple-earnings-{uuid4()}",
            "published_at": (datetime.utcnow() - timedelta(hours=6)).isoformat()
        },
        {
            "title": "Oil Prices Drop as Global Economic Concerns Mount",
            "content": "Crude oil prices fell sharply today as concerns about global economic growth weighed on energy markets. West Texas Intermediate crude dropped below $80 per barrel amid fears that rising interest rates and inflation could lead to reduced demand. The International Energy Agency warned that a global recession could significantly impact oil consumption. OPEC+ is scheduled to meet next week to discuss potential production adjustments in response to market conditions.",
            "source": "Energy Market Report",
            "url": f"https://example.com/oil-prices-drop-{uuid4()}",
            "published_at": (datetime.utcnow() - timedelta(hours=4)).isoformat()
        },
        {
            "title": "Gold Reaches Multi-Year High as Investors Seek Safe Haven",
            "content": "Gold prices surged to their highest level in over two years as investors fled to safe-haven assets amid economic uncertainty. The precious metal topped $2,000 per ounce as concerns about inflation and geopolitical tensions drove demand. Central bank purchases of gold have also increased significantly this year, with many countries diversifying their reserves away from traditional currencies. Market experts predict gold could reach even higher levels if economic conditions continue to deteriorate.",
            "source": "Precious Metals Weekly",
            "url": f"https://example.com/gold-high-{uuid4()}",
            "published_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()
        }
    ]
    
    created_articles = 0
    for article in sample_articles:
        try:
            # First create the article
            response = requests.post(f"{base_url}/ingestion/articles", json=article)
            if response.status_code == 200:
                article_data = response.json()
                created_articles += 1
                
                # Analyze sentiment for the article
                sentiment_request = {"text": article["content"]}
                sentiment_response = requests.post(f"{base_url}/sentiment/article", json=sentiment_request)
                
                if sentiment_response.status_code == 200:
                    sentiment_data = sentiment_response.json()
                    print(f"   ✅ Created article: '{article['title'][:50]}...' with sentiment scores")
                else:
                    print(f"   ⚠️  Created article but failed sentiment analysis: {sentiment_response.status_code}")
            else:
                print(f"   ❌ Failed to create article: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error creating article: {e}")
    
    print(f"   📊 Created {created_articles} sample articles")
    
    # Give database a moment to process
    time.sleep(1)
    
    # Test 3: Basic search functionality
    print("\n3. Testing basic search functionality...")
    search_queries = [
        "Federal Reserve rate",
        "Bitcoin price",
        "Apple earnings",
        "oil prices",
        "gold safe haven"
    ]
    
    for query in search_queries:
        try:
            response = requests.get(f"{base_url}/search/?q={query}&limit=5")
            if response.status_code == 200:
                results = response.json()
                print(f"   ✅ Query '{query}': Found {results['total_count']} results")
                if results['results']:
                    first_result = results['results'][0]
                    article_title = first_result['article']['title'][:60]
                    sentiment_count = len(first_result['sentiments'])
                    print(f"      📝 Top result: '{article_title}...' ({sentiment_count} sentiment scores)")
            else:
                print(f"   ❌ Query '{query}' failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error searching for '{query}': {e}")
    
    # Test 4: Test articles-only endpoint
    print("\n4. Testing articles-only search endpoint...")
    try:
        response = requests.get(f"{base_url}/search/articles?q=inflation&limit=3")
        if response.status_code == 200:
            articles = response.json()
            print(f"   ✅ Articles-only search: Found {len(articles)} articles")
            for article in articles:
                print(f"      📄 '{article['title'][:50]}...'")
        else:
            print(f"   ❌ Articles-only search failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error in articles-only search: {e}")
    
    # Test 5: Performance testing
    print("\n5. Performance testing...")
    performance_queries = [
        "Fed rate decision",
        "Bitcoin cryptocurrency", 
        "Apple technology earnings",
        "oil energy market",
        "inflation economic policy"
    ]
    
    total_time = 0
    successful_searches = 0
    
    for query in performance_queries:
        try:
            start_time = time.time()
            response = requests.get(f"{base_url}/search/?q={query}&limit=10")
            end_time = time.time()
            
            search_time = end_time - start_time
            total_time += search_time
            
            if response.status_code == 200:
                results = response.json()
                successful_searches += 1
                print(f"   ⏱️  Query '{query}': {search_time:.3f}s ({results['total_count']} results)")
            else:
                print(f"   ❌ Query '{query}' failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error testing '{query}': {e}")
    
    if successful_searches > 0:
        avg_time = total_time / successful_searches
        print(f"   📊 Average search time: {avg_time:.3f}s over {successful_searches} searches")
        
        # Performance evaluation
        if avg_time < 0.200:
            print(f"   🚀 Excellent performance: < 200ms")
        elif avg_time < 0.500:
            print(f"   ✅ Good performance: < 500ms")
        elif avg_time < 1.000:
            print(f"   ⚠️  Acceptable performance: < 1s")
        else:
            print(f"   ❌ Poor performance: > 1s")
    
    # Test 6: Create search index (if using PostgreSQL)
    print("\n6. Testing search index creation...")
    try:
        response = requests.post(f"{base_url}/search/index")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Index creation: {result['status']} - {result['message']}")
        else:
            print(f"   ❌ Index creation failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error creating index: {e}")
    
    # Test 7: Error handling
    print("\n7. Testing error handling...")
    error_tests = [
        ("", "Empty query"),
        ("   ", "Whitespace only query"),
        ("a" * 10000, "Very long query")
    ]
    
    for query, description in error_tests:
        try:
            response = requests.get(f"{base_url}/search/?q={query}")
            if response.status_code == 400:
                print(f"   ✅ {description}: Correctly returned 400 error")
            elif response.status_code == 200:
                results = response.json()
                print(f"   ⚠️  {description}: Unexpectedly succeeded ({results['total_count']} results)")
            else:
                print(f"   ❌ {description}: Unexpected status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error testing {description}: {e}")
    
    # Test 8: Pagination
    print("\n8. Testing pagination...")
    try:
        response = requests.get(f"{base_url}/search/?q=the&limit=2&skip=0")
        if response.status_code == 200:
            results = response.json()
            print(f"   ✅ Pagination: Page 1 - {len(results['results'])} results, has_more: {results['has_more']}")
            
            if results['has_more']:
                response2 = requests.get(f"{base_url}/search/?q=the&limit=2&skip=2")
                if response2.status_code == 200:
                    results2 = response2.json()
                    print(f"   ✅ Pagination: Page 2 - {len(results2['results'])} results")
        else:
            print(f"   ❌ Pagination test failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error testing pagination: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Search API testing completed!")
    print("\nTo manually test the API:")
    print(f"• Basic search: GET {base_url}/search/?q=Fed+rate+decision")
    print(f"• Articles only: GET {base_url}/search/articles?q=Bitcoin")
    print(f"• Search stats: GET {base_url}/search/stats")
    print(f"• Create index: POST {base_url}/search/index")


if __name__ == "__main__":
    test_search_api() 