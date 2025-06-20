"""
Security utilities and middleware for TradeEasy backend.

This module provides comprehensive security features including:
- Input validation and sanitization
- XSS prevention
- Rate limiting
- CSRF protection
- SQL injection prevention (additional layer)
"""

import re
import html
import logging
import hashlib
import secrets
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import bleach

# Set up logging
logger = logging.getLogger(__name__)

# Rate limiting storage (in-memory for simplicity, use Redis in production)
rate_limit_storage: Dict[str, Dict[str, Any]] = defaultdict(dict)
rate_limit_lock = Lock()

# CSRF token storage (in-memory for simplicity, use Redis in production)
csrf_tokens: Dict[str, datetime] = {}
csrf_lock = Lock()

# Security configuration
SECURITY_CONFIG = {
    "max_text_length": 10000,  # Maximum text input length
    "max_query_length": 500,   # Maximum search query length
    "csrf_token_expiry": 3600,  # CSRF token expiry in seconds
    "rate_limits": {
        # Format: endpoint_pattern: (requests_per_minute, requests_per_hour)
        "auth": (10, 100),          # Authentication endpoints
        "sentiment": (60, 1000),    # Sentiment analysis
        "search": (30, 500),        # Search endpoints
        "ingestion": (5, 50),       # Ingestion endpoints
        "default": (100, 2000),     # Default for other endpoints
    }
}

# XSS prevention - allowed HTML tags and attributes
ALLOWED_TAGS = []  # No HTML tags allowed in user input
ALLOWED_ATTRIBUTES = {}


class SecurityError(Exception):
    """Custom exception for security-related errors."""
    pass


def sanitize_text_input(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize text input to prevent XSS and other injection attacks.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length (defaults to config value)
        
    Returns:
        Sanitized text
        
    Raises:
        SecurityError: If input is invalid or potentially malicious
    """
    if not isinstance(text, str):
        raise SecurityError("Input must be a string")
    
    # Check length
    max_len = max_length or SECURITY_CONFIG["max_text_length"]
    if len(text) > max_len:
        raise SecurityError(f"Input text too long (max {max_len} characters)")
    
    # Remove null bytes and control characters
    text = text.replace('\x00', '').replace('\r', '').replace('\n', ' ')
    
    # HTML escape to prevent XSS
    text = html.escape(text, quote=True)
    
    # Use bleach for additional sanitization
    text = bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)
    
    # Remove potentially dangerous patterns
    dangerous_patterns = [
        r'javascript:',
        r'vbscript:',
        r'data:',
        r'<script',
        r'</script>',
        r'<iframe',
        r'<object',
        r'<embed',
        r'onload=',
        r'onerror=',
        r'onclick=',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"Potentially dangerous pattern detected: {pattern}")
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text.strip()


def sanitize_search_query(query: str) -> str:
    """
    Sanitize search query input with additional SQL injection prevention.
    
    Args:
        query: Search query to sanitize
        
    Returns:
        Sanitized query
        
    Raises:
        SecurityError: If query is invalid or potentially malicious
    """
    if not isinstance(query, str):
        raise SecurityError("Query must be a string")
    
    # Check length
    if len(query) > SECURITY_CONFIG["max_query_length"]:
        raise SecurityError(f"Search query too long (max {SECURITY_CONFIG['max_query_length']} characters)")
    
    # Basic sanitization
    query = sanitize_text_input(query, SECURITY_CONFIG["max_query_length"])
    
    # Additional SQL injection prevention patterns
    sql_patterns = [
        r';\s*drop\s+table',
        r';\s*delete\s+from',
        r';\s*update\s+',
        r';\s*insert\s+into',
        r'union\s+select',
        r'or\s+1\s*=\s*1',
        r'and\s+1\s*=\s*1',
        r'--\s*',
        r'/\*.*?\*/',
        r'xp_cmdshell',
        r'sp_executesql',
    ]
    
    for pattern in sql_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            logger.warning(f"Potential SQL injection pattern detected: {pattern}")
            raise SecurityError("Invalid characters in search query")
    
    return query


def validate_asset_symbol(symbol: str) -> str:
    """
    Validate and sanitize asset symbol input.
    
    Args:
        symbol: Asset symbol to validate
        
    Returns:
        Validated symbol
        
    Raises:
        SecurityError: If symbol is invalid
    """
    if not isinstance(symbol, str):
        raise SecurityError("Asset symbol must be a string")
    
    # Asset symbols should be alphanumeric with limited special characters
    if not re.match(r'^[A-Za-z0-9._-]{1,20}$', symbol):
        raise SecurityError("Invalid asset symbol format")
    
    return symbol.upper().strip()


def generate_csrf_token() -> str:
    """
    Generate a secure CSRF token.
    
    Returns:
        CSRF token string
    """
    token = secrets.token_urlsafe(32)
    
    with csrf_lock:
        csrf_tokens[token] = datetime.utcnow() + timedelta(seconds=SECURITY_CONFIG["csrf_token_expiry"])
    
    return token


def validate_csrf_token(token: str) -> bool:
    """
    Validate a CSRF token.
    
    Args:
        token: CSRF token to validate
        
    Returns:
        True if token is valid, False otherwise
    """
    if not token:
        return False
    
    with csrf_lock:
        if token not in csrf_tokens:
            return False
        
        # Check if token has expired
        if datetime.utcnow() > csrf_tokens[token]:
            del csrf_tokens[token]
            return False
        
        # Token is valid, remove it (one-time use)
        del csrf_tokens[token]
        return True


def cleanup_expired_csrf_tokens():
    """Clean up expired CSRF tokens."""
    now = datetime.utcnow()
    with csrf_lock:
        expired_tokens = [token for token, expiry in csrf_tokens.items() if now > expiry]
        for token in expired_tokens:
            del csrf_tokens[token]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.
    
    Implements per-IP rate limiting with different limits for different endpoint types.
    """
    
    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
    
    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Determine endpoint type and rate limit
        endpoint_type = self._get_endpoint_type(request.url.path)
        rate_limit = SECURITY_CONFIG["rate_limits"].get(endpoint_type, SECURITY_CONFIG["rate_limits"]["default"])
        
        # Check rate limit
        if self._is_rate_limited(client_ip, endpoint_type, rate_limit):
            logger.warning(f"Rate limit exceeded for IP {client_ip} on endpoint type {endpoint_type}")
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": "60"}
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self._get_remaining_requests(client_ip, endpoint_type, rate_limit)
        response.headers["X-RateLimit-Limit"] = str(rate_limit[0])  # Per minute limit
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int((datetime.utcnow() + timedelta(minutes=1)).timestamp()))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded headers (for reverse proxy setups)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _get_endpoint_type(self, path: str) -> str:
        """Determine endpoint type based on path."""
        if "/auth/" in path:
            return "auth"
        elif "/sentiment/" in path:
            return "sentiment"
        elif "/search/" in path:
            return "search"
        elif "/ingestion/" in path:
            return "ingestion"
        else:
            return "default"
    
    def _is_rate_limited(self, client_ip: str, endpoint_type: str, rate_limit: tuple) -> bool:
        """Check if client has exceeded rate limit."""
        now = datetime.utcnow()
        minute_limit, hour_limit = rate_limit
        
        with rate_limit_lock:
            if client_ip not in rate_limit_storage:
                rate_limit_storage[client_ip] = {}
            
            client_data = rate_limit_storage[client_ip]
            
            if endpoint_type not in client_data:
                client_data[endpoint_type] = {
                    "minute_requests": [],
                    "hour_requests": []
                }
            
            endpoint_data = client_data[endpoint_type]
            
            # Clean up old requests
            minute_ago = now - timedelta(minutes=1)
            hour_ago = now - timedelta(hours=1)
            
            endpoint_data["minute_requests"] = [
                req_time for req_time in endpoint_data["minute_requests"] 
                if req_time > minute_ago
            ]
            endpoint_data["hour_requests"] = [
                req_time for req_time in endpoint_data["hour_requests"] 
                if req_time > hour_ago
            ]
            
            # Check limits
            if len(endpoint_data["minute_requests"]) >= minute_limit:
                return True
            if len(endpoint_data["hour_requests"]) >= hour_limit:
                return True
            
            # Record this request
            endpoint_data["minute_requests"].append(now)
            endpoint_data["hour_requests"].append(now)
            
            return False
    
    def _get_remaining_requests(self, client_ip: str, endpoint_type: str, rate_limit: tuple) -> int:
        """Get remaining requests for the current minute."""
        minute_limit = rate_limit[0]
        
        with rate_limit_lock:
            if client_ip not in rate_limit_storage:
                return minute_limit
            
            client_data = rate_limit_storage[client_ip]
            if endpoint_type not in client_data:
                return minute_limit
            
            return max(0, minute_limit - len(client_data[endpoint_type]["minute_requests"]))


def get_security_headers() -> Dict[str, str]:
    """
    Get security headers to add to responses.
    
    Returns:
        Dictionary of security headers
    """
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
    }


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        for header, value in get_security_headers().items():
            response.headers[header] = value
        
        return response


# Input validation decorators
def validate_text_input(max_length: Optional[int] = None):
    """Decorator to validate text input in request bodies."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This would need to be implemented based on specific endpoint needs
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_csrf_token():
    """Decorator to require CSRF token for state-changing operations."""
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            # Check for CSRF token in headers
            csrf_token = request.headers.get("X-CSRF-Token")
            if not csrf_token or not validate_csrf_token(csrf_token):
                raise HTTPException(
                    status_code=403,
                    detail="Invalid or missing CSRF token"
                )
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


# Security audit functions
def audit_endpoint_security(endpoint_path: str, method: str, has_auth: bool, has_rate_limit: bool) -> Dict[str, Any]:
    """
    Audit security configuration of an endpoint.
    
    Args:
        endpoint_path: Path of the endpoint
        method: HTTP method
        has_auth: Whether endpoint requires authentication
        has_rate_limit: Whether endpoint has rate limiting
        
    Returns:
        Security audit results
    """
    issues = []
    recommendations = []
    
    # Check for authentication on sensitive endpoints
    if method in ["POST", "PUT", "DELETE", "PATCH"] and not has_auth:
        if "auth" not in endpoint_path:  # Auth endpoints don't need auth
            issues.append("State-changing endpoint without authentication")
            recommendations.append("Add authentication requirement")
    
    # Check for rate limiting
    if not has_rate_limit:
        issues.append("Endpoint without rate limiting")
        recommendations.append("Add rate limiting")
    
    # Check for CSRF protection on state-changing endpoints
    if method in ["POST", "PUT", "DELETE", "PATCH"]:
        recommendations.append("Consider CSRF protection for state-changing operations")
    
    return {
        "endpoint": f"{method} {endpoint_path}",
        "security_level": "high" if not issues else "medium" if len(issues) == 1 else "low",
        "issues": issues,
        "recommendations": recommendations
    }


def log_security_event(event_type: str, details: Dict[str, Any], client_ip: str = None):
    """
    Log security-related events for monitoring and analysis.
    
    Args:
        event_type: Type of security event
        details: Event details
        client_ip: Client IP address if available
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "client_ip": client_ip,
        "details": details
    }
    
    logger.warning(f"Security Event: {log_entry}") 