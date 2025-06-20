#!/usr/bin/env python3
"""
Week 7 Monitoring Integration Test

This script tests the complete Prometheus/Grafana monitoring integration
for TradeEasy backend, verifying:
1. Prometheus metrics server functionality
2. Metrics collection and exposure
3. Grafana configuration and dashboards
4. Alerting rules validation
5. Complete monitoring stack integration

Usage:
    python test_week7_monitoring_integration.py
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, List, Any

import httpx
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Week7MonitoringTester:
    """Comprehensive tester for Week 7 monitoring integration."""
    
    def __init__(self):
        """Initialize the monitoring tester."""
        self.results = {
            "prometheus_server": {},
            "metrics_collection": {},
            "grafana_config": {},
            "alerting_rules": {},
            "integration_tests": {},
            "summary": {}
        }
        self.base_url = "http://localhost:8000"
        self.prometheus_url = "http://localhost:9090"
        self.prometheus_metrics_url = "http://localhost:8001"
        self.grafana_url = "http://localhost:3001"
        
    def print_section(self, title: str):
        """Print a formatted section header."""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
        
    def record_result(self, test_name: str, success: bool, details: str = ""):
        """Record a test result."""
        result = {
            "success": success,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Determine which category this test belongs to
        if "prometheus" in test_name.lower():
            self.results["prometheus_server"][test_name] = result
        elif "metrics" in test_name.lower():
            self.results["metrics_collection"][test_name] = result
        elif "grafana" in test_name.lower():
            self.results["grafana_config"][test_name] = result
        elif "alert" in test_name.lower():
            self.results["alerting_rules"][test_name] = result
        else:
            self.results["integration_tests"][test_name] = result
            
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {test_name}: {details}")
        
    async def test_prometheus_server_enabled(self):
        """Test that Prometheus server is enabled in main.py."""
        self.print_section("1. Prometheus Server Configuration")
        
        try:
            with open("app/main.py", "r") as f:
                content = f.read()
                
            # Check if Prometheus server is enabled (not commented out)
            if "start_http_server(8001)" in content and not content.count("# start_http_server(8001)"):
                self.record_result("Prometheus Server Enabled", True, "start_http_server(8001) is active")
            else:
                self.record_result("Prometheus Server Enabled", False, "start_http_server(8001) is commented out")
                
            # Check for metrics import
            if "from prometheus_client import start_http_server" in content:
                self.record_result("Prometheus Import", True, "prometheus_client imported correctly")
            else:
                self.record_result("Prometheus Import", False, "prometheus_client import missing")
                
        except Exception as e:
            self.record_result("Prometheus Configuration Check", False, f"Error reading main.py: {e}")
            
    async def test_prometheus_metrics_endpoint(self):
        """Test Prometheus metrics endpoint availability."""
        self.print_section("2. Prometheus Metrics Collection")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test dedicated metrics server (port 8001)
                try:
                    response = await client.get(self.prometheus_metrics_url)
                    if response.status_code == 200:
                        content = response.text
                        if "tradeeasy_" in content:
                            self.record_result("Metrics Server (8001)", True, f"TradeEasy metrics available")
                        else:
                            self.record_result("Metrics Server (8001)", True, "Server responding but no TradeEasy metrics yet")
                    else:
                        self.record_result("Metrics Server (8001)", False, f"HTTP {response.status_code}")
                except Exception as e:
                    self.record_result("Metrics Server (8001)", False, f"Connection failed: {e}")
                
                # Test API metrics endpoint (port 8000/metrics)
                try:
                    response = await client.get(f"{self.base_url}/metrics")
                    if response.status_code == 200:
                        content = response.text
                        if "tradeeasy_" in content or "prometheus" in content.lower():
                            self.record_result("API Metrics Endpoint", True, "Metrics endpoint responding")
                        else:
                            self.record_result("API Metrics Endpoint", True, "Endpoint responding, metrics may be empty")
                    else:
                        self.record_result("API Metrics Endpoint", False, f"HTTP {response.status_code}")
                except Exception as e:
                    self.record_result("API Metrics Endpoint", False, f"Connection failed: {e}")
                    
        except Exception as e:
            self.record_result("Metrics Endpoint Test", False, f"Test failed: {e}")
            
    def test_prometheus_configuration(self):
        """Test Prometheus configuration files."""
        self.print_section("3. Prometheus Configuration Files")
        
        # Test prometheus.yml
        try:
            with open("prometheus.yml", "r") as f:
                config = yaml.safe_load(f)
                
            # Check scrape configs
            scrape_configs = config.get("scrape_configs", [])
            tradeeasy_jobs = [job for job in scrape_configs if "tradeeasy" in job.get("job_name", "")]
            
            if len(tradeeasy_jobs) >= 2:
                self.record_result("Prometheus Config", True, f"Found {len(tradeeasy_jobs)} TradeEasy scrape jobs")
            else:
                self.record_result("Prometheus Config", False, f"Only {len(tradeeasy_jobs)} TradeEasy jobs found")
                
            # Check rule files
            rule_files = config.get("rule_files", [])
            if "tradeeasy_rules.yml" in rule_files:
                self.record_result("Rule Files Config", True, "tradeeasy_rules.yml configured")
            else:
                self.record_result("Rule Files Config", False, "tradeeasy_rules.yml not in rule_files")
                
        except FileNotFoundError:
            self.record_result("Prometheus Config", False, "prometheus.yml not found")
        except Exception as e:
            self.record_result("Prometheus Config", False, f"Error reading config: {e}")
            
        # Test alerting rules
        try:
            with open("tradeeasy_rules.yml", "r") as f:
                rules = yaml.safe_load(f)
                
            groups = rules.get("groups", [])
            total_rules = sum(len(group.get("rules", [])) for group in groups)
            
            if total_rules >= 5:
                self.record_result("Alerting Rules", True, f"{total_rules} alerting rules configured")
            else:
                self.record_result("Alerting Rules", False, f"Only {total_rules} rules found")
                
        except FileNotFoundError:
            self.record_result("Alerting Rules", False, "tradeeasy_rules.yml not found")
        except Exception as e:
            self.record_result("Alerting Rules", False, f"Error reading rules: {e}")
            
    def test_grafana_configuration(self):
        """Test Grafana configuration and dashboards."""
        self.print_section("4. Grafana Configuration")
        
        # Test Docker Compose configuration
        try:
            with open("docker-compose.monitoring.yml", "r") as f:
                compose = yaml.safe_load(f)
                
            services = compose.get("services", {})
            if "grafana" in services and "prometheus" in services:
                self.record_result("Docker Compose", True, "Grafana and Prometheus services configured")
            else:
                self.record_result("Docker Compose", False, "Missing Grafana or Prometheus services")
                
        except FileNotFoundError:
            self.record_result("Docker Compose", False, "docker-compose.monitoring.yml not found")
        except Exception as e:
            self.record_result("Docker Compose", False, f"Error reading compose file: {e}")
            
        # Test Grafana provisioning
        provisioning_files = [
            "grafana/provisioning/datasources/prometheus.yml",
            "grafana/provisioning/dashboards/dashboard.yml"
        ]
        
        for file_path in provisioning_files:
            try:
                with open(file_path, "r") as f:
                    config = yaml.safe_load(f)
                    
                file_name = os.path.basename(file_path)
                self.record_result(f"Grafana {file_name}", True, "Configuration file exists and valid")
                
            except FileNotFoundError:
                self.record_result(f"Grafana {file_name}", False, "File not found")
            except Exception as e:
                self.record_result(f"Grafana {file_name}", False, f"Error reading file: {e}")
                
        # Test dashboard JSON
        try:
            with open("grafana/dashboards/tradeeasy-overview.json", "r") as f:
                dashboard = json.load(f)
                
            panels = dashboard.get("panels", [])
            if len(panels) >= 4:
                self.record_result("Grafana Dashboard", True, f"Dashboard with {len(panels)} panels configured")
            else:
                self.record_result("Grafana Dashboard", False, f"Only {len(panels)} panels found")
                
        except FileNotFoundError:
            self.record_result("Grafana Dashboard", False, "tradeeasy-overview.json not found")
        except Exception as e:
            self.record_result("Grafana Dashboard", False, f"Error reading dashboard: {e}")
            
    def test_alertmanager_configuration(self):
        """Test Alertmanager configuration."""
        self.print_section("5. Alertmanager Configuration")
        
        try:
            with open("alertmanager.yml", "r") as f:
                config = yaml.safe_load(f)
                
            # Check receivers
            receivers = config.get("receivers", [])
            if len(receivers) >= 3:
                self.record_result("Alertmanager Receivers", True, f"{len(receivers)} receivers configured")
            else:
                self.record_result("Alertmanager Receivers", False, f"Only {len(receivers)} receivers found")
                
            # Check routes
            route = config.get("route", {})
            routes = route.get("routes", [])
            if len(routes) >= 2:
                self.record_result("Alertmanager Routes", True, f"{len(routes)} routes configured")
            else:
                self.record_result("Alertmanager Routes", False, f"Only {len(routes)} routes found")
                
        except FileNotFoundError:
            self.record_result("Alertmanager Config", False, "alertmanager.yml not found")
        except Exception as e:
            self.record_result("Alertmanager Config", False, f"Error reading config: {e}")
            
    async def test_backend_health(self):
        """Test that the backend is healthy and ready for monitoring."""
        self.print_section("6. Backend Health Check")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test health endpoint
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    self.record_result("Backend Health", True, "Backend is healthy")
                else:
                    self.record_result("Backend Health", False, f"HTTP {response.status_code}")
                    
                # Test status endpoint
                response = await client.get(f"{self.base_url}/api/status")
                if response.status_code == 200:
                    status = response.json()
                    features = status.get("features", {})
                    if features.get("rss_ingestion") and features.get("sentiment_analysis"):
                        self.record_result("Backend Features", True, "Core features available")
                    else:
                        self.record_result("Backend Features", False, "Some features missing")
                else:
                    self.record_result("Backend Status", False, f"HTTP {response.status_code}")
                    
        except Exception as e:
            self.record_result("Backend Health Check", False, f"Connection failed: {e}")
            
    def test_monitoring_stack_integration(self):
        """Test the complete monitoring stack integration."""
        self.print_section("7. Monitoring Stack Integration")
        
        # Check if all required files exist
        required_files = [
            "prometheus.yml",
            "tradeeasy_rules.yml", 
            "docker-compose.monitoring.yml",
            "alertmanager.yml",
            "grafana/provisioning/datasources/prometheus.yml",
            "grafana/provisioning/dashboards/dashboard.yml",
            "grafana/dashboards/tradeeasy-overview.json"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
                
        if not missing_files:
            self.record_result("Configuration Files", True, "All monitoring configuration files present")
        else:
            self.record_result("Configuration Files", False, f"Missing files: {missing_files}")
            
        # Test Docker Compose validation
        try:
            result = subprocess.run(
                ["docker-compose", "-f", "docker-compose.monitoring.yml", "config"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.record_result("Docker Compose Validation", True, "Configuration is valid")
            else:
                self.record_result("Docker Compose Validation", False, f"Validation failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.record_result("Docker Compose Validation", False, "Validation timed out")
        except Exception as e:
            self.record_result("Docker Compose Validation", False, f"Error: {e}")
            
    def generate_summary(self):
        """Generate a comprehensive test summary."""
        self.print_section("Week 7 Monitoring Integration Summary")
        
        total_tests = 0
        passed_tests = 0
        
        for category, tests in self.results.items():
            if category == "summary":
                continue
                
            category_passed = 0
            category_total = len(tests)
            
            for test_name, result in tests.items():
                total_tests += 1
                if result["success"]:
                    passed_tests += 1
                    category_passed += 1
                    
            if category_total > 0:
                category_percentage = (category_passed / category_total) * 100
                print(f"\n{category.replace('_', ' ').title()}: {category_passed}/{category_total} ({category_percentage:.1f}%)")
                
        overall_percentage = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"OVERALL RESULTS: {passed_tests}/{total_tests} tests passed ({overall_percentage:.1f}%)")
        print(f"{'='*60}")
        
        # Store summary
        self.results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": overall_percentage,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Determine overall status
        if overall_percentage >= 90:
            print("🎉 EXCELLENT: Week 7 monitoring integration is ready for production!")
        elif overall_percentage >= 75:
            print("✅ GOOD: Week 7 monitoring integration is mostly complete with minor issues.")
        elif overall_percentage >= 50:
            print("⚠️  PARTIAL: Week 7 monitoring integration needs significant work.")
        else:
            print("❌ INCOMPLETE: Week 7 monitoring integration requires major fixes.")
            
        return overall_percentage >= 75
        
    def save_results(self):
        """Save test results to a JSON file."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"week7_monitoring_test_results_{timestamp}.json"
        
        try:
            with open(filename, "w") as f:
                json.dump(self.results, f, indent=2)
            print(f"\n📄 Test results saved to: {filename}")
        except Exception as e:
            print(f"\n❌ Failed to save results: {e}")
            
    async def run_all_tests(self):
        """Run all monitoring integration tests."""
        print("🚀 Starting Week 7 Monitoring Integration Tests...")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        
        # Run all test categories
        await self.test_prometheus_server_enabled()
        await self.test_prometheus_metrics_endpoint()
        self.test_prometheus_configuration()
        self.test_grafana_configuration()
        self.test_alertmanager_configuration()
        await self.test_backend_health()
        self.test_monitoring_stack_integration()
        
        # Generate summary and save results
        success = self.generate_summary()
        self.save_results()
        
        return success


async def main():
    """Main test execution function."""
    tester = Week7MonitoringTester()
    
    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 