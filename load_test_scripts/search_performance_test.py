#!/usr/bin/env python3
"""
Specialized load testing script for /api/search endpoint performance.

This script focuses specifically on the search functionality with:
1. Various query patterns (short, long, complex)
2. Different pagination scenarios
3. Performance benchmarking and reporting
4. Search-specific edge cases
"""

import asyncio
import aiohttp
import time
import statistics
from datetime import datetime
from typing import List, Dict, Any
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SearchPerformanceTester:
    """Comprehensive search endpoint performance tester."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.search_url = f"{base_url}/api/search/"
        self.articles_url = f"{base_url}/api/search/articles"
        self.stats_url = f"{base_url}/api/search/stats"
        
        # Test query patterns
        self.test_queries = {
            "short_queries": [
                "BTC", "USD", "Fed", "oil", "gold", "rate", "tax", "GDP"
            ],
            "medium_queries": [
                "Federal Reserve", "interest rate", "Bitcoin price", 
                "market analysis", "economic growth", "inflation data"
            ],
            "long_queries": [
                "Federal Reserve interest rate decision impact on market",
                "cryptocurrency market volatility analysis and predictions",
                "quarterly earnings report revenue growth expectations"
            ],
            "financial_terms": [
                "earnings", "revenue", "profit", "loss", "dividend", "stock",
                "bond", "commodity", "forex", "cryptocurrency", "inflation"
            ],
            "complex_queries": [
                "earnings AND revenue", "Bitcoin OR cryptocurrency", 
                "Federal Reserve rate hike", "market volatility analysis"
            ]
        }
        
        self.results = {
            "response_times": [],
            "success_count": 0,
            "failure_count": 0,
            "error_details": [],
            "query_performance": {}
        }
    
    async def test_single_search(self, session: aiohttp.ClientSession, query: str, 
                                limit: int = 10, skip: int = 0) -> Dict[str, Any]:
        """Test a single search request and return performance metrics."""
        start_time = time.time()
        
        try:
            params = {"q": query, "limit": limit, "skip": skip}
            async with session.get(self.search_url, params=params) as response:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "response_time": response_time,
                        "status_code": response.status,
                        "result_count": data.get("total_count", 0),
                        "returned_results": len(data.get("results", [])),
                        "query": query,
                        "limit": limit,
                        "skip": skip
                    }
                else:
                    return {
                        "success": False,
                        "response_time": response_time,
                        "status_code": response.status,
                        "error": f"HTTP {response.status}",
                        "query": query
                    }
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            return {
                "success": False,
                "response_time": response_time,
                "error": str(e),
                "query": query
            }
    
    async def test_query_pattern(self, session: aiohttp.ClientSession, 
                                pattern_name: str, queries: List[str]) -> Dict[str, Any]:
        """Test a specific pattern of queries."""
        logger.info(f"Testing {pattern_name} queries...")
        
        pattern_results = {
            "pattern_name": pattern_name,
            "total_queries": len(queries),
            "successful_queries": 0,
            "failed_queries": 0,
            "response_times": [],
            "avg_response_time": 0,
            "min_response_time": 0,
            "max_response_time": 0,
            "percentile_95": 0,
            "total_results_found": 0
        }
        
        tasks = []
        for query in queries:
            # Test with different pagination parameters
            for limit in [5, 10, 20]:
                for skip in [0, 5, 10]:
                    tasks.append(self.test_single_search(session, query, limit, skip))
        
        results = await asyncio.gather(*tasks)
        
        for result in results:
            if result["success"]:
                pattern_results["successful_queries"] += 1
                pattern_results["response_times"].append(result["response_time"])
                pattern_results["total_results_found"] += result.get("result_count", 0)
            else:
                pattern_results["failed_queries"] += 1
                self.results["error_details"].append(result)
        
        if pattern_results["response_times"]:
            times = pattern_results["response_times"]
            pattern_results["avg_response_time"] = statistics.mean(times)
            pattern_results["min_response_time"] = min(times)
            pattern_results["max_response_time"] = max(times)
            pattern_results["percentile_95"] = statistics.quantiles(times, n=20)[18]  # 95th percentile
        
        return pattern_results
    
    async def test_pagination_performance(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test pagination performance with different skip/limit combinations."""
        logger.info("Testing pagination performance...")
        
        pagination_test = {
            "test_name": "pagination_performance",
            "scenarios": []
        }
        
        test_query = "market analysis"  # Fixed query for consistent testing
        
        # Test different pagination scenarios
        scenarios = [
            {"limit": 5, "skip": 0},
            {"limit": 10, "skip": 0},
            {"limit": 20, "skip": 0},
            {"limit": 50, "skip": 0},
            {"limit": 10, "skip": 50},
            {"limit": 10, "skip": 100},
            {"limit": 10, "skip": 500},
            {"limit": 100, "skip": 0},  # Large limit
            {"limit": 5, "skip": 1000}   # Deep pagination
        ]
        
        for scenario in scenarios:
            result = await self.test_single_search(
                session, test_query, scenario["limit"], scenario["skip"]
            )
            scenario_result = {
                "limit": scenario["limit"],
                "skip": scenario["skip"],
                "response_time": result["response_time"],
                "success": result["success"],
                "returned_results": result.get("returned_results", 0)
            }
            pagination_test["scenarios"].append(scenario_result)
        
        return pagination_test
    
    async def test_concurrent_load(self, session: aiohttp.ClientSession, 
                                  concurrent_users: int = 10, 
                                  requests_per_user: int = 5) -> Dict[str, Any]:
        """Test concurrent load on search endpoint."""
        logger.info(f"Testing concurrent load: {concurrent_users} users, {requests_per_user} requests each...")
        
        async def user_session():
            """Simulate a single user making multiple requests."""
            user_results = []
            for _ in range(requests_per_user):
                query = "Bitcoin market analysis"  # Fixed query
                result = await self.test_single_search(session, query)
                user_results.append(result)
                await asyncio.sleep(0.1)  # Small delay between requests
            return user_results
        
        # Create concurrent user sessions
        user_tasks = [user_session() for _ in range(concurrent_users)]
        all_user_results = await asyncio.gather(*user_tasks)
        
        # Aggregate results
        all_results = []
        for user_results in all_user_results:
            all_results.extend(user_results)
        
        successful_results = [r for r in all_results if r["success"]]
        failed_results = [r for r in all_results if not r["success"]]
        
        concurrent_test = {
            "test_name": "concurrent_load",
            "concurrent_users": concurrent_users,
            "requests_per_user": requests_per_user,
            "total_requests": len(all_results),
            "successful_requests": len(successful_results),
            "failed_requests": len(failed_results),
            "success_rate": len(successful_results) / len(all_results) * 100,
            "avg_response_time": statistics.mean([r["response_time"] for r in successful_results]) if successful_results else 0,
            "max_response_time": max([r["response_time"] for r in successful_results]) if successful_results else 0
        }
        
        return concurrent_test
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive search performance testing."""
        logger.info("🚀 Starting comprehensive search performance testing...")
        
        start_time = datetime.now()
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100)
        ) as session:
            
            # Test 1: Query pattern performance
            pattern_results = {}
            for pattern_name, queries in self.test_queries.items():
                pattern_result = await self.test_query_pattern(session, pattern_name, queries)
                pattern_results[pattern_name] = pattern_result
            
            # Test 2: Pagination performance
            pagination_result = await self.test_pagination_performance(session)
            
            # Test 3: Concurrent load testing
            concurrent_result = await self.test_concurrent_load(session, 
                                                               concurrent_users=20, 
                                                               requests_per_user=10)
            
            # Test 4: Search stats endpoint performance
            stats_start = time.time()
            try:
                async with session.get(self.stats_url) as response:
                    stats_response_time = (time.time() - stats_start) * 1000
                    if response.status == 200:
                        stats_data = await response.json()
                        stats_test = {
                            "success": True,
                            "response_time": stats_response_time,
                            "total_articles": stats_data.get("total_articles", 0),
                            "database_type": stats_data.get("database_type", "unknown")
                        }
                    else:
                        stats_test = {"success": False, "status_code": response.status}
            except Exception as e:
                stats_test = {"success": False, "error": str(e)}
        
        end_time = datetime.now()
        
        # Compile comprehensive report
        comprehensive_report = {
            "test_summary": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_duration": str(end_time - start_time),
                "test_target": self.base_url
            },
            "query_pattern_results": pattern_results,
            "pagination_performance": pagination_result,
            "concurrent_load_test": concurrent_result,
            "search_stats_test": stats_test,
            "performance_summary": self.generate_performance_summary(pattern_results, pagination_result, concurrent_result)
        }
        
        return comprehensive_report
    
    def generate_performance_summary(self, pattern_results: Dict, 
                                   pagination_result: Dict, 
                                   concurrent_result: Dict) -> Dict[str, Any]:
        """Generate overall performance summary."""
        all_response_times = []
        total_successful = 0
        total_failed = 0
        
        # Aggregate all response times and success/failure counts
        for pattern_data in pattern_results.values():
            all_response_times.extend(pattern_data["response_times"])
            total_successful += pattern_data["successful_queries"]
            total_failed += pattern_data["failed_queries"]
        
        summary = {
            "overall_success_rate": total_successful / (total_successful + total_failed) * 100 if (total_successful + total_failed) > 0 else 0,
            "total_requests": total_successful + total_failed,
            "successful_requests": total_successful,
            "failed_requests": total_failed
        }
        
        if all_response_times:
            summary.update({
                "avg_response_time": statistics.mean(all_response_times),
                "min_response_time": min(all_response_times),
                "max_response_time": max(all_response_times),
                "percentile_50": statistics.median(all_response_times),
                "percentile_95": statistics.quantiles(all_response_times, n=20)[18] if len(all_response_times) >= 20 else max(all_response_times),
                "percentile_99": statistics.quantiles(all_response_times, n=100)[98] if len(all_response_times) >= 100 else max(all_response_times)
            })
        
        # Performance recommendations
        recommendations = []
        if summary.get("avg_response_time", 0) > 1000:
            recommendations.append("Average response time > 1s - consider database optimization")
        if summary.get("percentile_95", 0) > 2000:
            recommendations.append("95th percentile > 2s - investigate slow queries")
        if summary["overall_success_rate"] < 95:
            recommendations.append("Success rate < 95% - review error handling")
        
        summary["recommendations"] = recommendations
        
        return summary
    
    def print_report(self, report: Dict[str, Any]):
        """Print formatted performance report."""
        logger.info("\n" + "=" * 80)
        logger.info("📊 SEARCH ENDPOINT PERFORMANCE REPORT")
        logger.info("=" * 80)
        
        summary = report["performance_summary"]
        logger.info(f"\n🎯 OVERALL PERFORMANCE:")
        logger.info(f"   Success Rate: {summary['overall_success_rate']:.1f}%")
        logger.info(f"   Total Requests: {summary['total_requests']}")
        logger.info(f"   Average Response Time: {summary.get('avg_response_time', 0):.2f}ms")
        logger.info(f"   95th Percentile: {summary.get('percentile_95', 0):.2f}ms")
        
        logger.info(f"\n📋 QUERY PATTERN PERFORMANCE:")
        for pattern_name, data in report["query_pattern_results"].items():
            logger.info(f"   {pattern_name.replace('_', ' ').title()}:")
            logger.info(f"     Success Rate: {(data['successful_queries']/(data['successful_queries']+data['failed_queries'])*100):.1f}%")
            logger.info(f"     Avg Response: {data['avg_response_time']:.2f}ms")
            logger.info(f"     Max Response: {data['max_response_time']:.2f}ms")
        
        concurrent = report["concurrent_load_test"]
        logger.info(f"\n🚀 CONCURRENT LOAD TEST:")
        logger.info(f"   Users: {concurrent['concurrent_users']}")
        logger.info(f"   Success Rate: {concurrent['success_rate']:.1f}%")
        logger.info(f"   Avg Response: {concurrent['avg_response_time']:.2f}ms")
        logger.info(f"   Max Response: {concurrent['max_response_time']:.2f}ms")
        
        if summary["recommendations"]:
            logger.info(f"\n💡 RECOMMENDATIONS:")
            for rec in summary["recommendations"]:
                logger.info(f"   • {rec}")
        
        logger.info("=" * 80)

async def main():
    """Main function to run search performance testing."""
    tester = SearchPerformanceTester()
    
    try:
        report = await tester.run_comprehensive_test()
        tester.print_report(report)
        
        # Save detailed report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"search_performance_report_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"\n📄 Detailed report saved to: {filename}")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 