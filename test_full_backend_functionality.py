#!/usr/bin/env python3
"""
TradeEasy Backend - Comprehensive Full Functionality Test Suite

This script tests all backend functionality end-to-end to verify the complete system
is working correctly after Shaun's implementation is complete.

Author: Claude Assistant
Date: December 2024
Version: 1.0
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import httpx
import websockets
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradeEasyBackendTester:
    """Comprehensive backend functionality tester."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.auth_token = None
        self.test_results = {}
        self.start_time = datetime.now()
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all comprehensive backend tests."""
        logger.info("🚀 Starting TradeEasy Backend Full Functionality Tests")
        logger.info("=" * 80)
        
        test_categories = [
            ("Basic Health & Status", self.test_health_status),
            ("Authentication System", self.test_authentication),
            ("Sentiment Analysis", self.test_sentiment_analysis),
            ("Search Functionality", self.test_search),
            ("History & Analytics", self.test_history),
            ("Watchlist & Alerts", self.test_watchlist_alerts),
            ("WebSocket & Real-time", self.test_websocket),
            ("Performance & Monitoring", self.test_performance),
            ("Edge Cases", self.test_edge_cases),
        ]
        
        for category_name, test_function in test_categories:
            logger.info(f"\n📋 {category_name}")
            logger.info("-" * 60)
            
            try:
                results = await test_function()
                self.test_results[category_name] = results
                success_count = sum(1 for r in results.values() if r.get('status') == 'PASS')
                total_count = len(results)
                success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
                
                logger.info(f"✅ {category_name}: {success_count}/{total_count} tests passed ({success_rate:.1f}%)")
                
            except Exception as e:
                logger.error(f"❌ {category_name} failed: {e}")
                self.test_results[category_name] = {"error": str(e), "status": "FAIL"}
        
        return await self.generate_final_report()
    
    async def test_health_status(self) -> Dict[str, Any]:
        """Test basic health and status endpoints."""
        results = {}
        
        async with httpx.AsyncClient() as client:
            # Health endpoint
            try:
                response = await client.get(f"{self.base_url}/health")
                results["health_endpoint"] = {
                    "status": "PASS" if response.status_code == 200 else "FAIL",
                    "response_time": response.elapsed.total_seconds(),
                    "data": response.json() if response.status_code == 200 else None
                }
                logger.info(f"✅ Health endpoint: {response.status_code}")
            except Exception as e:
                results["health_endpoint"] = {"status": "FAIL", "error": str(e)}
                logger.error(f"❌ Health endpoint failed: {e}")
            
            # Status endpoint
            try:
                response = await client.get(f"{self.base_url}/api/status")
                results["status_endpoint"] = {
                    "status": "PASS" if response.status_code == 200 else "FAIL",
                    "response_time": response.elapsed.total_seconds()
                }
                logger.info(f"✅ Status endpoint: {response.status_code}")
            except Exception as e:
                results["status_endpoint"] = {"status": "FAIL", "error": str(e)}
                logger.error(f"❌ Status endpoint failed: {e}")
            
            # API docs
            try:
                response = await client.get(f"{self.base_url}/docs")
                results["api_docs"] = {
                    "status": "PASS" if response.status_code == 200 else "FAIL"
                }
                logger.info(f"✅ API docs: {response.status_code}")
            except Exception as e:
                results["api_docs"] = {"status": "FAIL", "error": str(e)}
                logger.error(f"❌ API docs failed: {e}")
        
        return results
    
    async def test_authentication(self) -> Dict[str, Any]:
        """Test authentication system."""
        results = {}
        
        async with httpx.AsyncClient() as client:
            # Demo login
            try:
                response = await client.get(f"{self.base_url}/api/auth/demo-login")
                if response.status_code == 200:
                    auth_data = response.json()
                    self.auth_token = auth_data.get("access_token")
                    results["demo_login"] = {
                        "status": "PASS",
                        "token_received": bool(self.auth_token)
                    }
                    logger.info(f"✅ Demo login successful")
                else:
                    results["demo_login"] = {"status": "FAIL", "status_code": response.status_code}
                    logger.error(f"❌ Demo login failed: {response.status_code}")
            except Exception as e:
                results["demo_login"] = {"status": "FAIL", "error": str(e)}
                logger.error(f"❌ Demo login failed: {e}")
            
            # Protected endpoint access
            if self.auth_token:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                try:
                    response = await client.get(f"{self.base_url}/api/watchlists/", headers=headers)
                    results["protected_access"] = {
                        "status": "PASS" if response.status_code == 200 else "FAIL",
                        "status_code": response.status_code
                    }
                    logger.info(f"✅ Protected endpoint access: {response.status_code}")
                except Exception as e:
                    results["protected_access"] = {"status": "FAIL", "error": str(e)}
                    logger.error(f"❌ Protected endpoint failed: {e}")
        
        return results
    
    async def test_sentiment_analysis(self) -> Dict[str, Any]:
        """Test sentiment analysis engine."""
        results = {}
        
        test_texts = [
            "Apple stock soars on strong earnings",
            "Market fears spread amid uncertainty",
            "Bitcoin rallies strongly"
        ]
        
        async with httpx.AsyncClient() as client:
            for i, text in enumerate(test_texts, 1):
                try:
                    payload = {"text": text}
                    response = await client.post(f"{self.base_url}/api/sentiment/article", json=payload)
                    
                    if response.status_code == 200:
                        sentiment_data = response.json()
                        results[f"sentiment_test_{i}"] = {
                            "status": "PASS",
                            "lexicon_score": sentiment_data.get("lexicon_score"),
                            "finbert_score": sentiment_data.get("finbert_score"),
                        }
                        logger.info(f"✅ Sentiment {i}: L={sentiment_data.get('lexicon_score'):.3f}, F={sentiment_data.get('finbert_score'):.3f}")
                    else:
                        results[f"sentiment_test_{i}"] = {"status": "FAIL", "status_code": response.status_code}
                        logger.error(f"❌ Sentiment {i} failed: {response.status_code}")
                        
                except Exception as e:
                    results[f"sentiment_test_{i}"] = {"status": "FAIL", "error": str(e)}
                    logger.error(f"❌ Sentiment {i} failed: {e}")
        
        return results
    
    async def test_search(self) -> Dict[str, Any]:
        """Test search functionality."""
        results = {}
        
        search_queries = ["Bitcoin", "Apple", "market"]
        
        async with httpx.AsyncClient() as client:
            for i, query in enumerate(search_queries, 1):
                try:
                    response = await client.get(f"{self.base_url}/api/search/?q={query}&limit=5")
                    if response.status_code == 200:
                        search_data = response.json()
                        results[f"search_{i}"] = {
                            "status": "PASS",
                            "query": query,
                            "results_count": len(search_data.get("articles", []))
                        }
                        logger.info(f"✅ Search '{query}': {len(search_data.get('articles', []))} results")
                    else:
                        results[f"search_{i}"] = {"status": "FAIL", "status_code": response.status_code}
                        logger.error(f"❌ Search '{query}' failed: {response.status_code}")
                except Exception as e:
                    results[f"search_{i}"] = {"status": "FAIL", "error": str(e)}
                    logger.error(f"❌ Search '{query}' failed: {e}")
        
        return results
    
    async def test_history(self) -> Dict[str, Any]:
        """Test history endpoints."""
        results = {}
        
        async with httpx.AsyncClient() as client:
            assets = ["BTC", "AAPL"]
            for asset in assets:
                try:
                    response = await client.get(f"{self.base_url}/api/sentiment/history?asset={asset}&range=24h")
                    results[f"history_{asset}"] = {
                        "status": "PASS" if response.status_code in [200, 404] else "FAIL",
                        "status_code": response.status_code
                    }
                    logger.info(f"✅ History {asset}: {response.status_code}")
                except Exception as e:
                    results[f"history_{asset}"] = {"status": "FAIL", "error": str(e)}
                    logger.error(f"❌ History {asset} failed: {e}")
        
        return results
    
    async def test_watchlist_alerts(self) -> Dict[str, Any]:
        """Test watchlist and alerts."""
        results = {}
        
        if not self.auth_token:
            results["auth_required"] = {"status": "FAIL", "error": "No auth token"}
            return results
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with httpx.AsyncClient() as client:
            # Watchlists
            try:
                response = await client.get(f"{self.base_url}/api/watchlists/", headers=headers)
                results["get_watchlists"] = {
                    "status": "PASS" if response.status_code == 200 else "FAIL",
                    "status_code": response.status_code
                }
                logger.info(f"✅ Get watchlists: {response.status_code}")
            except Exception as e:
                results["get_watchlists"] = {"status": "FAIL", "error": str(e)}
                logger.error(f"❌ Get watchlists failed: {e}")
            
            # Alerts
            try:
                response = await client.get(f"{self.base_url}/api/alerts/", headers=headers)
                results["get_alerts"] = {
                    "status": "PASS" if response.status_code == 200 else "FAIL",
                    "status_code": response.status_code
                }
                logger.info(f"✅ Get alerts: {response.status_code}")
            except Exception as e:
                results["get_alerts"] = {"status": "FAIL", "error": str(e)}
                logger.error(f"❌ Get alerts failed: {e}")
        
        return results
    
    async def test_websocket(self) -> Dict[str, Any]:
        """Test WebSocket functionality."""
        results = {}
        
        async with httpx.AsyncClient() as client:
            # WebSocket stats
            try:
                response = await client.get(f"{self.base_url}/api/websocket/stats")
                results["websocket_stats"] = {
                    "status": "PASS" if response.status_code == 200 else "FAIL",
                    "status_code": response.status_code
                }
                logger.info(f"✅ WebSocket stats: {response.status_code}")
            except Exception as e:
                results["websocket_stats"] = {"status": "FAIL", "error": str(e)}
                logger.error(f"❌ WebSocket stats failed: {e}")
            
            # Test broadcast
            try:
                response = await client.post(f"{self.base_url}/api/websocket/test-broadcast")
                results["websocket_broadcast"] = {
                    "status": "PASS" if response.status_code == 200 else "FAIL",
                    "status_code": response.status_code
                }
                logger.info(f"✅ WebSocket broadcast: {response.status_code}")
            except Exception as e:
                results["websocket_broadcast"] = {"status": "FAIL", "error": str(e)}
                logger.error(f"❌ WebSocket broadcast failed: {e}")
        
        return results
    
    async def test_performance(self) -> Dict[str, Any]:
        """Test performance and monitoring."""
        results = {}
        
        async with httpx.AsyncClient() as client:
            # Metrics endpoint
            try:
                response = await client.get(f"{self.base_url}/metrics")
                results["metrics_endpoint"] = {
                    "status": "PASS" if response.status_code == 200 else "FAIL",
                    "has_tradeeasy_metrics": "tradeeasy_" in response.text if response.status_code == 200 else False
                }
                logger.info(f"✅ Metrics endpoint: {response.status_code}")
            except Exception as e:
                results["metrics_endpoint"] = {"status": "FAIL", "error": str(e)}
                logger.error(f"❌ Metrics endpoint failed: {e}")
            
            # Prometheus server (port 8001)
            try:
                response = await client.get("http://localhost:8001")
                results["prometheus_server"] = {
                    "status": "PASS" if response.status_code == 200 else "FAIL"
                }
                logger.info(f"✅ Prometheus server: {response.status_code}")
            except Exception as e:
                results["prometheus_server"] = {"status": "FAIL", "error": str(e)}
                logger.error(f"❌ Prometheus server failed: {e}")
        
        return results
    
    async def test_edge_cases(self) -> Dict[str, Any]:
        """Test edge cases and error handling."""
        results = {}
        
        async with httpx.AsyncClient() as client:
            # Invalid endpoint
            try:
                response = await client.get(f"{self.base_url}/api/nonexistent")
                results["invalid_endpoint"] = {
                    "status": "PASS" if response.status_code == 404 else "FAIL",
                    "status_code": response.status_code
                }
                logger.info(f"✅ Invalid endpoint handled: {response.status_code}")
            except Exception as e:
                results["invalid_endpoint"] = {"status": "FAIL", "error": str(e)}
                logger.error(f"❌ Invalid endpoint test failed: {e}")
            
            # Malformed request
            try:
                response = await client.post(f"{self.base_url}/api/sentiment/article", json={"invalid": "data"})
                results["malformed_request"] = {
                    "status": "PASS" if response.status_code in [400, 422] else "FAIL",
                    "status_code": response.status_code
                }
                logger.info(f"✅ Malformed request rejected: {response.status_code}")
            except Exception as e:
                results["malformed_request"] = {"status": "FAIL", "error": str(e)}
                logger.error(f"❌ Malformed request test failed: {e}")
        
        return results
    
    async def generate_final_report(self) -> Dict[str, Any]:
        """Generate final test report."""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        # Calculate statistics
        total_tests = 0
        passed_tests = 0
        
        for category, results in self.test_results.items():
            if isinstance(results, dict) and "error" not in results:
                for test_name, test_result in results.items():
                    total_tests += 1
                    if test_result.get("status") == "PASS":
                        passed_tests += 1
            elif "error" in results:
                total_tests += 1
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        logger.info("\n" + "=" * 80)
        logger.info("🎯 TRADEEASY BACKEND - COMPREHENSIVE TEST REPORT")
        logger.info("=" * 80)
        logger.info(f"📊 Test Duration: {total_duration:.2f} seconds")
        logger.info(f"📈 Total Tests: {total_tests}")
        logger.info(f"✅ Passed: {passed_tests}")
        logger.info(f"❌ Failed: {total_tests - passed_tests}")
        logger.info(f"🎯 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 95:
            logger.info("🎉 EXCELLENT! TradeEasy backend is fully functional and production-ready!")
        elif success_rate >= 85:
            logger.info("✅ GOOD! TradeEasy backend is working well with minor issues.")
        else:
            logger.info("⚠️ ATTENTION NEEDED! Some functionality may need fixes.")
        
        logger.info("=" * 80)
        
        # Save report
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "success_rate": success_rate,
                "duration": total_duration
            },
            "results": self.test_results
        }
        
        report_file = f"backend_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📄 Report saved to: {report_file}")
        
        return report

async def main():
    """Run comprehensive backend tests."""
    tester = TradeEasyBackendTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 