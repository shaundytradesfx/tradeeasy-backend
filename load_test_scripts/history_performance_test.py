#!/usr/bin/env python3
"""
Specialized load testing script for /api/sentiment/history endpoint performance.

This script focuses specifically on the sentiment history functionality with:
1. Various time range scenarios (1h, 24h, 7d, 30d)
2. Different asset types (crypto, stocks, forex, commodities)
3. Custom date range testing
4. Performance benchmarking and reporting
"""

import asyncio
import aiohttp
import time
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HistoryPerformanceTester:
    """Comprehensive sentiment history endpoint performance tester."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.history_url = f"{base_url}/api/sentiment/history"
        self.latest_url = f"{base_url}/api/sentiment/latest"
        
        # Test assets by category
        self.test_assets = {
            "cryptocurrencies": ["BTC", "ETH", "ADA", "DOT", "SOL", "AVAX"],
            "stocks": ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "META"],
            "forex": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"],
            "commodities": ["GOLD", "SILVER", "OIL", "COPPER", "WHEAT"],
            "popular_assets": ["BTC", "AAPL", "EUR/USD", "GOLD"]  # Most commonly queried
        }
        
        # Time range scenarios
        self.time_ranges = ["1h", "24h", "7d", "30d"]
        
        self.results = {
            "response_times": [],
            "success_count": 0,
            "failure_count": 0,
            "error_details": [],
            "asset_performance": {}
        }
    
    async def test_single_history_request(self, session: aiohttp.ClientSession, 
                                        asset: str, time_range: str = None,
                                        start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Test a single history request and return performance metrics."""
        start_time = time.time()
        
        try:
            params = {"asset": asset}
            if time_range:
                params["range"] = time_range
            if start_date:
                params["start"] = start_date
            if end_date:
                params["end"] = end_date
            
            async with session.get(self.history_url, params=params) as response:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "response_time": response_time,
                        "status_code": response.status,
                        "data_points": len(data) if isinstance(data, list) else 0,
                        "asset": asset,
                        "time_range": time_range,
                        "start_date": start_date,
                        "end_date": end_date
                    }
                elif response.status == 404:
                    # 404 is acceptable if no data exists
                    return {
                        "success": True,
                        "response_time": response_time,
                        "status_code": response.status,
                        "data_points": 0,
                        "asset": asset,
                        "time_range": time_range,
                        "no_data": True
                    }
                else:
                    return {
                        "success": False,
                        "response_time": response_time,
                        "status_code": response.status,
                        "error": f"HTTP {response.status}",
                        "asset": asset,
                        "time_range": time_range
                    }
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            return {
                "success": False,
                "response_time": response_time,
                "error": str(e),
                "asset": asset,
                "time_range": time_range
            }
    
    async def test_time_range_performance(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test performance across different time ranges."""
        logger.info("Testing time range performance...")
        
        time_range_results = {
            "test_name": "time_range_performance",
            "ranges": {}
        }
        
        # Test each time range with popular assets
        for time_range in self.time_ranges:
            range_data = {
                "time_range": time_range,
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "response_times": [],
                "avg_data_points": 0,
                "total_data_points": 0
            }
            
            tasks = []
            for asset in self.test_assets["popular_assets"]:
                tasks.append(self.test_single_history_request(session, asset, time_range))
            
            results = await asyncio.gather(*tasks)
            
            for result in results:
                range_data["total_requests"] += 1
                if result["success"]:
                    range_data["successful_requests"] += 1
                    range_data["response_times"].append(result["response_time"])
                    range_data["total_data_points"] += result.get("data_points", 0)
                else:
                    range_data["failed_requests"] += 1
            
            if range_data["response_times"]:
                range_data["avg_response_time"] = statistics.mean(range_data["response_times"])
                range_data["max_response_time"] = max(range_data["response_times"])
                range_data["min_response_time"] = min(range_data["response_times"])
            
            if range_data["successful_requests"] > 0:
                range_data["avg_data_points"] = range_data["total_data_points"] / range_data["successful_requests"]
            
            time_range_results["ranges"][time_range] = range_data
        
        return time_range_results
    
    async def test_asset_category_performance(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test performance across different asset categories."""
        logger.info("Testing asset category performance...")
        
        category_results = {
            "test_name": "asset_category_performance",
            "categories": {}
        }
        
        for category, assets in self.test_assets.items():
            if category == "popular_assets":  # Skip this meta-category
                continue
                
            category_data = {
                "category": category,
                "assets_tested": len(assets),
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "response_times": [],
                "assets_with_data": 0,
                "assets_without_data": 0
            }
            
            tasks = []
            for asset in assets:
                # Test with 7d range as a standard
                tasks.append(self.test_single_history_request(session, asset, "7d"))
            
            results = await asyncio.gather(*tasks)
            
            for result in results:
                category_data["total_requests"] += 1
                if result["success"]:
                    category_data["successful_requests"] += 1
                    category_data["response_times"].append(result["response_time"])
                    
                    if result.get("data_points", 0) > 0:
                        category_data["assets_with_data"] += 1
                    else:
                        category_data["assets_without_data"] += 1
                else:
                    category_data["failed_requests"] += 1
            
            if category_data["response_times"]:
                category_data["avg_response_time"] = statistics.mean(category_data["response_times"])
                category_data["max_response_time"] = max(category_data["response_times"])
                category_data["data_availability_rate"] = category_data["assets_with_data"] / len(assets) * 100
            
            category_results["categories"][category] = category_data
        
        return category_results
    
    async def test_custom_date_ranges(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test performance with custom date ranges."""
        logger.info("Testing custom date ranges...")
        
        custom_date_test = {
            "test_name": "custom_date_ranges",
            "scenarios": []
        }
        
        now = datetime.utcnow()
        
        # Define custom date scenarios
        date_scenarios = [
            {
                "name": "last_3_days",
                "start": (now - timedelta(days=3)).isoformat(),
                "end": now.isoformat()
            },
            {
                "name": "last_week_specific",
                "start": (now - timedelta(days=7)).isoformat(),
                "end": (now - timedelta(days=1)).isoformat()
            },
            {
                "name": "last_month",
                "start": (now - timedelta(days=30)).isoformat(),
                "end": now.isoformat()
            },
            {
                "name": "specific_week",
                "start": (now - timedelta(days=14)).isoformat(),
                "end": (now - timedelta(days=7)).isoformat()
            }
        ]
        
        test_asset = "BTC"  # Use consistent asset for testing
        
        for scenario in date_scenarios:
            result = await self.test_single_history_request(
                session, test_asset, 
                start_date=scenario["start"], 
                end_date=scenario["end"]
            )
            
            scenario_result = {
                "scenario_name": scenario["name"],
                "start_date": scenario["start"],
                "end_date": scenario["end"],
                "response_time": result["response_time"],
                "success": result["success"],
                "data_points": result.get("data_points", 0)
            }
            custom_date_test["scenarios"].append(scenario_result)
        
        return custom_date_test
    
    async def test_concurrent_history_load(self, session: aiohttp.ClientSession, 
                                         concurrent_users: int = 15, 
                                         requests_per_user: int = 8) -> Dict[str, Any]:
        """Test concurrent load on history endpoint."""
        logger.info(f"Testing concurrent history load: {concurrent_users} users, {requests_per_user} requests each...")
        
        async def user_session():
            """Simulate a single user making multiple history requests."""
            user_results = []
            for _ in range(requests_per_user):
                # Vary requests across different assets and time ranges
                asset = "BTC"  # Could randomize: random.choice(self.test_assets["popular_assets"])
                time_range = "7d"  # Could randomize: random.choice(self.time_ranges)
                
                result = await self.test_single_history_request(session, asset, time_range)
                user_results.append(result)
                await asyncio.sleep(0.2)  # Small delay between requests
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
            "test_name": "concurrent_history_load",
            "concurrent_users": concurrent_users,
            "requests_per_user": requests_per_user,
            "total_requests": len(all_results),
            "successful_requests": len(successful_results),
            "failed_requests": len(failed_results),
            "success_rate": len(successful_results) / len(all_results) * 100 if all_results else 0,
            "avg_response_time": statistics.mean([r["response_time"] for r in successful_results]) if successful_results else 0,
            "max_response_time": max([r["response_time"] for r in successful_results]) if successful_results else 0,
            "total_data_points": sum([r.get("data_points", 0) for r in successful_results])
        }
        
        return concurrent_test
    
    async def test_latest_sentiment_performance(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test performance of the latest sentiment endpoint (related to history)."""
        logger.info("Testing latest sentiment endpoint performance...")
        
        latest_test = {
            "test_name": "latest_sentiment_performance",
            "total_assets_tested": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "assets_with_data": 0,
            "assets_without_data": 0
        }
        
        tasks = []
        all_assets = []
        for category, assets in self.test_assets.items():
            if category != "popular_assets":
                all_assets.extend(assets)
        
        # Remove duplicates
        unique_assets = list(set(all_assets))
        
        for asset in unique_assets:
            tasks.append(self.test_latest_sentiment(session, asset))
        
        results = await asyncio.gather(*tasks)
        
        for result in results:
            latest_test["total_assets_tested"] += 1
            if result["success"]:
                latest_test["successful_requests"] += 1
                latest_test["response_times"].append(result["response_time"])
                
                if result.get("has_data", False):
                    latest_test["assets_with_data"] += 1
                else:
                    latest_test["assets_without_data"] += 1
            else:
                latest_test["failed_requests"] += 1
        
        if latest_test["response_times"]:
            latest_test["avg_response_time"] = statistics.mean(latest_test["response_times"])
            latest_test["max_response_time"] = max(latest_test["response_times"])
            latest_test["min_response_time"] = min(latest_test["response_times"])
        
        return latest_test
    
    async def test_latest_sentiment(self, session: aiohttp.ClientSession, asset: str) -> Dict[str, Any]:
        """Test a single latest sentiment request."""
        start_time = time.time()
        
        try:
            params = {"asset": asset}
            async with session.get(self.latest_url, params=params) as response:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "response_time": response_time,
                        "status_code": response.status,
                        "has_data": True,
                        "asset": asset
                    }
                elif response.status == 404:
                    return {
                        "success": True,
                        "response_time": response_time,
                        "status_code": response.status,
                        "has_data": False,
                        "asset": asset
                    }
                else:
                    return {
                        "success": False,
                        "response_time": response_time,
                        "status_code": response.status,
                        "error": f"HTTP {response.status}",
                        "asset": asset
                    }
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            return {
                "success": False,
                "response_time": response_time,
                "error": str(e),
                "asset": asset
            }
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive history endpoint performance testing."""
        logger.info("🚀 Starting comprehensive history performance testing...")
        
        start_time = datetime.now()
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100)
        ) as session:
            
            # Test 1: Time range performance
            time_range_results = await self.test_time_range_performance(session)
            
            # Test 2: Asset category performance
            category_results = await self.test_asset_category_performance(session)
            
            # Test 3: Custom date range testing
            custom_date_results = await self.test_custom_date_ranges(session)
            
            # Test 4: Concurrent load testing
            concurrent_results = await self.test_concurrent_history_load(session, 
                                                                        concurrent_users=20, 
                                                                        requests_per_user=10)
            
            # Test 5: Latest sentiment performance (related endpoint)
            latest_results = await self.test_latest_sentiment_performance(session)
        
        end_time = datetime.now()
        
        # Compile comprehensive report
        comprehensive_report = {
            "test_summary": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_duration": str(end_time - start_time),
                "test_target": self.base_url
            },
            "time_range_performance": time_range_results,
            "asset_category_performance": category_results,
            "custom_date_ranges": custom_date_results,
            "concurrent_load_test": concurrent_results,
            "latest_sentiment_performance": latest_results,
            "performance_summary": self.generate_performance_summary(
                time_range_results, category_results, concurrent_results, latest_results
            )
        }
        
        return comprehensive_report
    
    def generate_performance_summary(self, time_range_results: Dict, 
                                   category_results: Dict, 
                                   concurrent_results: Dict,
                                   latest_results: Dict) -> Dict[str, Any]:
        """Generate overall performance summary."""
        all_response_times = []
        total_successful = 0
        total_failed = 0
        
        # Aggregate from time range tests
        for range_data in time_range_results["ranges"].values():
            all_response_times.extend(range_data.get("response_times", []))
            total_successful += range_data["successful_requests"]
            total_failed += range_data["failed_requests"]
        
        # Aggregate from category tests
        for cat_data in category_results["categories"].values():
            all_response_times.extend(cat_data.get("response_times", []))
            total_successful += cat_data["successful_requests"]
            total_failed += cat_data["failed_requests"]
        
        # Add concurrent test results
        total_successful += concurrent_results["successful_requests"]
        total_failed += concurrent_results["failed_requests"]
        
        # Add latest sentiment results
        all_response_times.extend(latest_results.get("response_times", []))
        total_successful += latest_results["successful_requests"]
        total_failed += latest_results["failed_requests"]
        
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
        if summary.get("avg_response_time", 0) > 800:
            recommendations.append("Average response time > 800ms - consider data aggregation optimization")
        if summary.get("percentile_95", 0) > 1500:
            recommendations.append("95th percentile > 1.5s - investigate database query performance")
        if summary["overall_success_rate"] < 95:
            recommendations.append("Success rate < 95% - review error handling and data availability")
        
        # Check data availability
        total_assets_tested = sum([len(assets) for category, assets in self.test_assets.items() if category != "popular_assets"])
        data_availability_issues = []
        for cat_name, cat_data in category_results["categories"].items():
            if cat_data.get("data_availability_rate", 0) < 50:
                data_availability_issues.append(f"Low data availability for {cat_name} ({cat_data.get('data_availability_rate', 0):.1f}%)")
        
        if data_availability_issues:
            recommendations.extend(data_availability_issues)
        
        summary["recommendations"] = recommendations
        
        return summary
    
    def print_report(self, report: Dict[str, Any]):
        """Print formatted performance report."""
        logger.info("\n" + "=" * 80)
        logger.info("📊 HISTORY ENDPOINT PERFORMANCE REPORT")
        logger.info("=" * 80)
        
        summary = report["performance_summary"]
        logger.info(f"\n🎯 OVERALL PERFORMANCE:")
        logger.info(f"   Success Rate: {summary['overall_success_rate']:.1f}%")
        logger.info(f"   Total Requests: {summary['total_requests']}")
        logger.info(f"   Average Response Time: {summary.get('avg_response_time', 0):.2f}ms")
        logger.info(f"   95th Percentile: {summary.get('percentile_95', 0):.2f}ms")
        
        logger.info(f"\n⏱️  TIME RANGE PERFORMANCE:")
        for range_name, data in report["time_range_performance"]["ranges"].items():
            logger.info(f"   {range_name.upper()}:")
            logger.info(f"     Success Rate: {(data['successful_requests']/(data['successful_requests']+data['failed_requests'])*100):.1f}%")
            logger.info(f"     Avg Response: {data.get('avg_response_time', 0):.2f}ms")
            logger.info(f"     Avg Data Points: {data.get('avg_data_points', 0):.1f}")
        
        logger.info(f"\n📈 ASSET CATEGORY PERFORMANCE:")
        for cat_name, data in report["asset_category_performance"]["categories"].items():
            logger.info(f"   {cat_name.replace('_', ' ').title()}:")
            logger.info(f"     Data Availability: {data.get('data_availability_rate', 0):.1f}%")
            logger.info(f"     Avg Response: {data.get('avg_response_time', 0):.2f}ms")
            logger.info(f"     Assets with Data: {data['assets_with_data']}/{data['assets_tested']}")
        
        concurrent = report["concurrent_load_test"]
        logger.info(f"\n🚀 CONCURRENT LOAD TEST:")
        logger.info(f"   Users: {concurrent['concurrent_users']}")
        logger.info(f"   Success Rate: {concurrent['success_rate']:.1f}%")
        logger.info(f"   Avg Response: {concurrent['avg_response_time']:.2f}ms")
        logger.info(f"   Total Data Points: {concurrent['total_data_points']}")
        
        if summary["recommendations"]:
            logger.info(f"\n💡 RECOMMENDATIONS:")
            for rec in summary["recommendations"]:
                logger.info(f"   • {rec}")
        
        logger.info("=" * 80)

async def main():
    """Main function to run history performance testing."""
    tester = HistoryPerformanceTester()
    
    try:
        report = await tester.run_comprehensive_test()
        tester.print_report(report)
        
        # Save detailed report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"history_performance_report_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"\n📄 Detailed report saved to: {filename}")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 