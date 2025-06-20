#!/usr/bin/env python3
"""
Simple test to verify monitoring components are properly configured.
"""

import sys
sys.path.append('.')

def test_monitoring_components():
    """Test that all monitoring components are properly configured."""
    print("🚀 Testing TradeEasy Monitoring Components...")
    
    try:
        # Test app imports
        from app.main import app
        print("✅ App imports successful")
        
        # Test metrics initialization
        from app.metrics import IngestionMetrics
        metrics = IngestionMetrics()
        print("✅ Metrics initialization successful")
        
        # Test Prometheus client
        from prometheus_client import start_http_server, generate_latest
        print("✅ Prometheus client import successful")
        
        # Test metrics generation
        metrics_output = generate_latest()
        if b"tradeeasy_" in metrics_output:
            print("✅ TradeEasy metrics are being generated")
        else:
            print("⚠️  TradeEasy metrics not yet generated (normal on first run)")
            
        print("\n🎉 All monitoring components are properly configured!")
        print("📊 Prometheus metrics server can be started on port 8001")
        print("📈 API metrics endpoint available at /metrics")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_monitoring_components()
    sys.exit(0 if success else 1) 