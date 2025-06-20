#!/usr/bin/env python3
"""
WebSocket Integration Test Runner for TradeEasy Week 5.

This script runs all WebSocket integration tests and provides a comprehensive
report of the results, including performance metrics and test coverage.
"""

import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'websocket_tests_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    return logging.getLogger(__name__)


def check_server_running():
    """Check if the TradeEasy server is running."""
    try:
        import requests
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def run_test_module(module_name: str, logger: logging.Logger):
    """Run a specific test module and return the results."""
    logger.info(f"Running {module_name}...")
    
    start_time = time.time()
    
    try:
        # Run the test module using unittest
        result = subprocess.run(
            [sys.executable, "-m", "unittest", f"tests.{module_name}", "-v"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per test module
        )
        
        duration = time.time() - start_time
        
        # Parse results
        output_lines = result.stdout.split('\n')
        error_lines = result.stderr.split('\n')
        
        # Count tests
        test_count = len([line for line in output_lines if 'test_' in line and '...' in line])
        passed_count = len([line for line in output_lines if line.strip().endswith('ok')])
        failed_count = len([line for line in output_lines if 'FAIL' in line or 'ERROR' in line])
        
        success = result.returncode == 0
        
        logger.info(f"Completed {module_name}: {passed_count} passed, {failed_count} failed in {duration:.2f}s")
        
        return {
            "module": module_name,
            "success": success,
            "duration": duration,
            "test_count": test_count,
            "passed": passed_count,
            "failed": failed_count,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
        
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        logger.error(f"Test module {module_name} timed out after {duration:.2f}s")
        return {
            "module": module_name,
            "success": False,
            "duration": duration,
            "test_count": 0,
            "passed": 0,
            "failed": 1,
            "stdout": "",
            "stderr": "Test timed out",
            "return_code": -1
        }
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Error running {module_name}: {e}")
        return {
            "module": module_name,
            "success": False,
            "duration": duration,
            "test_count": 0,
            "passed": 0,
            "failed": 1,
            "stdout": "",
            "stderr": str(e),
            "return_code": -1
        }


def generate_test_report(results: list, logger: logging.Logger):
    """Generate a comprehensive test report."""
    logger.info("=" * 80)
    logger.info("WEBSOCKET INTEGRATION TEST REPORT")
    logger.info("=" * 80)
    
    total_tests = sum(r["test_count"] for r in results)
    total_passed = sum(r["passed"] for r in results)
    total_failed = sum(r["failed"] for r in results)
    total_duration = sum(r["duration"] for r in results)
    successful_modules = len([r for r in results if r["success"]])
    
    logger.info(f"Test Modules: {len(results)}")
    logger.info(f"Successful Modules: {successful_modules}/{len(results)}")
    logger.info(f"Total Tests: {total_tests}")
    logger.info(f"Passed: {total_passed}")
    logger.info(f"Failed: {total_failed}")
    logger.info(f"Success Rate: {(total_passed/total_tests*100):.1f}%" if total_tests > 0 else "N/A")
    logger.info(f"Total Duration: {total_duration:.2f}s")
    logger.info("")
    
    # Module-by-module breakdown
    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        logger.info(f"{status} {result['module']}: {result['passed']}/{result['test_count']} tests in {result['duration']:.2f}s")
    
    logger.info("")
    
    # Detailed failure information
    failed_modules = [r for r in results if not r["success"]]
    if failed_modules:
        logger.info("FAILURE DETAILS:")
        logger.info("-" * 40)
        for result in failed_modules:
            logger.info(f"Module: {result['module']}")
            logger.info(f"Return Code: {result['return_code']}")
            if result["stderr"]:
                logger.info("STDERR:")
                logger.info(result["stderr"])
            logger.info("")
    
    return {
        "total_modules": len(results),
        "successful_modules": successful_modules,
        "total_tests": total_tests,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "success_rate": (total_passed/total_tests*100) if total_tests > 0 else 0,
        "total_duration": total_duration,
        "overall_success": total_failed == 0 and successful_modules == len(results)
    }


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run TradeEasy WebSocket Integration Tests")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only (skip load tests)")
    parser.add_argument("--load-only", action="store_true", help="Run load tests only")
    parser.add_argument("--module", type=str, help="Run specific test module only")
    parser.add_argument("--no-server-check", action="store_true", help="Skip server availability check")
    
    args = parser.parse_args()
    
    logger = setup_logging()
    
    logger.info("Starting TradeEasy WebSocket Integration Tests")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Working Directory: {Path.cwd()}")
    logger.info("")
    
    # Check if server is running
    if not args.no_server_check:
        logger.info("Checking server availability...")
        if not check_server_running():
            logger.error("❌ TradeEasy server is not running on http://127.0.0.1:8000")
            logger.error("Please start the server with: uvicorn app.main:app --host 127.0.0.1 --port 8000")
            sys.exit(1)
        else:
            logger.info("✅ Server is running")
    
    # Define test modules
    test_modules = []
    
    if args.module:
        test_modules = [args.module]
    elif args.load_only:
        test_modules = ["test_websocket_load"]
    elif args.quick:
        test_modules = [
            "test_websocket_integration",
            "test_websocket_rss_integration"
        ]
    else:
        test_modules = [
            "test_websocket_integration",
            "test_websocket_rss_integration", 
            "test_websocket_load"
        ]
    
    logger.info(f"Running test modules: {', '.join(test_modules)}")
    logger.info("")
    
    # Run tests
    results = []
    start_time = time.time()
    
    for module in test_modules:
        result = run_test_module(module, logger)
        results.append(result)
        
        # Short break between modules
        time.sleep(1)
    
    total_time = time.time() - start_time
    
    # Generate report
    logger.info("")
    summary = generate_test_report(results, logger)
    
    logger.info(f"Total execution time: {total_time:.2f}s")
    logger.info("")
    
    # Exit with appropriate code
    if summary["overall_success"]:
        logger.info("🎉 All WebSocket integration tests PASSED!")
        sys.exit(0)
    else:
        logger.error("💥 Some WebSocket integration tests FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main() 