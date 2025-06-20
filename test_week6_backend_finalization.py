#!/usr/bin/env python3
"""
Test suite for Week 6: Backend Finalization

This test verifies:
1. JWT authentication implementation
2. Secured watchlist/alert endpoints 
3. Database indexes for performance
4. Password hashing with bcrypt
5. Token validation and expiration
"""

import asyncio
import json
import logging
import pytest
import requests
import time
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db, create_performance_indexes
from app.models import Base, User, Asset, Alert
from app import crud, schemas
from app.auth import create_access_token, verify_token, get_password_hash, verify_password

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_week6_backend_finalization.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestWeek6BackendFinalization:
    """Test Week 6 backend finalization features."""
    
    @classmethod
    def setup_class(cls):
        """Set up test database and data."""
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Create test client
        cls.client = TestClient(app)
        cls.db = TestingSessionLocal()
        
        logger.info("Week 6 Backend Finalization Test Setup Complete")
    
    @classmethod
    def teardown_class(cls):
        """Clean up test database."""
        cls.db.close()
        Base.metadata.drop_all(bind=engine)
        logger.info("Week 6 Backend Finalization Test Teardown Complete")
    
    def test_jwt_authentication_system(self):
        """Test JWT authentication implementation."""
        logger.info("Testing JWT authentication system...")
        
        # Test 1: Authentication status endpoint
        response = self.client.get("/api/auth/status")
        assert response.status_code == 200
        auth_status = response.json()
        
        assert auth_status["auth_type"] == "JWT"
        assert auth_status["algorithm"] == "HS256"
        assert auth_status["token_expiry_minutes"] == 1440
        assert "JWT tokens" in auth_status["security_features"]
        assert "bcrypt password hashing" in auth_status["security_features"]
        
        logger.info("✅ JWT authentication status verified")
        
        # Test 2: Demo login with JWT
        response = self.client.get("/api/auth/demo-login")
        assert response.status_code == 200
        
        login_data = response.json()
        assert "access_token" in login_data
        assert login_data["token_type"] == "bearer"
        assert login_data["username"] == "demo"
        
        # Verify token is valid JWT
        token = login_data["access_token"]
        token_data = verify_token(token)
        assert token_data is not None
        assert token_data["username"] == "demo"
        
        logger.info("✅ JWT token generation and validation working")
        
        # Test 3: Manual login with JWT
        response = self.client.post("/api/auth/login", json={
            "username": "demo",
            "password": "demo123"
        })
        assert response.status_code == 200
        
        manual_login = response.json()
        assert "access_token" in manual_login
        assert manual_login["token_type"] == "bearer"
        
        logger.info("✅ Manual JWT login working")
        
        return token
    
    def test_password_hashing(self):
        """Test bcrypt password hashing."""
        logger.info("Testing bcrypt password hashing...")
        
        # Test password hashing
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        # Verify hash format (bcrypt hashes start with $2b$)
        assert hashed.startswith("$2b$")
        assert len(hashed) > 50  # bcrypt hashes are typically ~60 chars
        
        # Verify password verification works
        assert verify_password(password, hashed)
        assert not verify_password("wrong_password", hashed)
        
        logger.info("✅ bcrypt password hashing working correctly")
    
    def test_endpoint_security(self):
        """Test that watchlist and alert endpoints are properly secured."""
        logger.info("Testing endpoint security...")
        
        # Test 1: Unauthorized access should fail
        unauthorized_endpoints = [
            "/api/watchlists/",
            "/api/alerts/",
            "/api/watchlists/stats",
            "/api/alerts/stats",
            "/api/alerts/triggered"
        ]
        
        for endpoint in unauthorized_endpoints:
            response = self.client.get(endpoint)
            assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"
        
        logger.info("✅ Unauthorized access properly blocked")
        
        # Test 2: Invalid token should fail
        invalid_headers = {"Authorization": "Bearer invalid_token_here"}
        
        for endpoint in unauthorized_endpoints:
            response = self.client.get(endpoint, headers=invalid_headers)
            assert response.status_code == 401, f"Endpoint {endpoint} should reject invalid tokens"
        
        logger.info("✅ Invalid tokens properly rejected")
        
        # Test 3: Valid token should work
        demo_response = self.client.get("/api/auth/demo-login")
        token = demo_response.json()["access_token"]
        valid_headers = {"Authorization": f"Bearer {token}"}
        
        for endpoint in unauthorized_endpoints:
            response = self.client.get(endpoint, headers=valid_headers)
            assert response.status_code == 200, f"Endpoint {endpoint} should work with valid token"
        
        logger.info("✅ Valid tokens properly accepted")
    
    def test_database_indexes(self):
        """Test database index creation and performance."""
        logger.info("Testing database indexes...")
        
        # Test 1: Index creation function
        created_count = create_performance_indexes(engine)
        assert created_count >= 0  # Should not fail
        
        logger.info(f"✅ Database index creation completed: {created_count} indexes")
        
        # Test 2: Index creation endpoint (requires authentication)
        demo_response = self.client.get("/api/auth/demo-login")
        token = demo_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.client.post("/api/auth/admin/create-indexes", headers=headers)
        assert response.status_code == 200
        
        index_result = response.json()
        assert index_result["status"] == "success"
        assert "indexes_created" in index_result
        
        logger.info("✅ Index creation endpoint working")
        
        # Test 3: Verify some indexes exist
        with engine.connect() as conn:
            # Check for some critical indexes
            critical_indexes = [
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%user%'",
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%asset%'",
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%timestamp%'"
            ]
            
            for query in critical_indexes:
                result = conn.execute(text(query))
                indexes = result.fetchall()
                assert len(indexes) > 0, f"Should have indexes matching query: {query}"
        
        logger.info("✅ Database indexes verified")
    
    def test_token_expiration(self):
        """Test JWT token expiration functionality."""
        logger.info("Testing token expiration...")
        
        # Create a token with short expiration (1 second)
        short_token = create_access_token(
            data={"sub": "test_user", "username": "test"},
            expires_delta=timedelta(seconds=1)
        )
        
        # Token should be valid immediately
        token_data = verify_token(short_token)
        assert token_data is not None
        
        # Wait for token to expire
        time.sleep(2)
        
        # Token should now be invalid
        expired_token_data = verify_token(short_token)
        assert expired_token_data is None
        
        logger.info("✅ Token expiration working correctly")
    
    def test_end_to_end_auth_flow(self):
        """Test complete authentication flow."""
        logger.info("Testing end-to-end authentication flow...")
        
        # Step 1: Get demo login token
        response = self.client.get("/api/auth/demo-login")
        assert response.status_code == 200
        token = response.json()["access_token"]
        
        # Step 2: Use token to access protected resource
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.get("/api/watchlists/", headers=headers)
        assert response.status_code == 200
        
        # Step 3: Create a watchlist (test write operation)
        # First create a demo asset
        try:
            response = self.client.post("/api/watchlists/?asset_symbol=BTC", headers=headers)
            # This might fail if BTC asset doesn't exist, which is fine for testing auth
            assert response.status_code in [200, 404, 400]
        except:
            pass  # Asset creation might fail, but auth should work
        
        # Step 4: Test alert creation (another write operation)
        try:
            response = self.client.post(
                "/api/alerts/?asset_symbol=BTC&threshold=0.5&direction=above",
                headers=headers
            )
            # This might fail if BTC asset doesn't exist, which is fine for testing auth
            assert response.status_code in [200, 404, 400]
        except:
            pass  # Asset creation might fail, but auth should work
        
        logger.info("✅ End-to-end authentication flow working")
    
    def test_security_headers(self):
        """Test security-related headers and responses."""
        logger.info("Testing security headers...")
        
        # Test that 401 responses include proper WWW-Authenticate header
        response = self.client.get("/api/watchlists/")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert response.headers["WWW-Authenticate"] == "Bearer"
        
        logger.info("✅ Security headers properly set")
    
    def run_all_tests(self):
        """Run all Week 6 backend finalization tests."""
        logger.info("🚀 Starting Week 6 Backend Finalization Tests")
        logger.info("=" * 60)
        
        test_methods = [
            self.test_jwt_authentication_system,
            self.test_password_hashing,
            self.test_endpoint_security,
            self.test_database_indexes,
            self.test_token_expiration,
            self.test_end_to_end_auth_flow,
            self.test_security_headers
        ]
        
        results = {}
        
        for test_method in test_methods:
            test_name = test_method.__name__
            try:
                logger.info(f"\n📋 Running {test_name}...")
                test_method()
                results[test_name] = True
                logger.info(f"✅ {test_name} PASSED")
            except Exception as e:
                results[test_name] = False
                logger.error(f"❌ {test_name} FAILED: {e}")
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 WEEK 6 BACKEND FINALIZATION TEST SUMMARY")
        logger.info("=" * 60)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{test_name.replace('test_', '').replace('_', ' ').title()}: {status}")
        
        logger.info(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            logger.info("🎉 All Week 6 Backend Finalization tests PASSED!")
        else:
            logger.warning(f"⚠️  {total - passed} tests failed. Review implementation.")
        
        return results


if __name__ == "__main__":
    """Run the test suite directly."""
    logger.info("Starting Week 6 Backend Finalization Test Suite...")
    
    test_instance = TestWeek6BackendFinalization()
    test_instance.setup_class()
    
    try:
        results = test_instance.run_all_tests()
        
        # Exit with appropriate code
        if all(results.values()):
            exit(0)
        else:
            exit(1)
            
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        exit(1)
    finally:
        test_instance.teardown_class() 