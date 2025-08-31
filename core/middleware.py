"""
Custom middleware for security and logging.
"""

import logging
import time
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import resolve
from .security import check_suspicious_activity, log_authentication_attempt

User = get_user_model()
logger = logging.getLogger(__name__)


class SecurityMiddleware:
    """
    Middleware for enhanced security monitoring and protection.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Sensitive endpoints that need extra protection
        self.sensitive_endpoints = [
            'accounts:login',
            'accounts:register',
            'transactions:deposit',
            'transactions:withdrawal',
            'transactions:transfer',
            'admin_panel:dashboard',
        ]
        
        # Rate limits for different endpoint types
        self.rate_limits = {
            'auth': {'limit': 5, 'window': 300},      # 5 attempts per 5 minutes
            'transaction': {'limit': 10, 'window': 60}, # 10 transactions per minute
            'general': {'limit': 100, 'window': 300},   # 100 requests per 5 minutes
            'admin': {'limit': 20, 'window': 300},      # 20 admin requests per 5 minutes
        }
    
    def __call__(self, request):
        # Pre-process request
        start_time = time.time()
        
        # Get client IP
        ip = self.get_client_ip(request)
        
        # Check for suspicious activity
        suspicious_indicators = check_suspicious_activity(request, request.user if hasattr(request, 'user') else None)
        
        # Log suspicious activity
        if any(suspicious_indicators.values()):
            logger.warning(f"Suspicious activity detected from IP {ip}: {suspicious_indicators}")
        
        # Apply rate limiting
        if self.should_rate_limit(request):
            logger.warning(f"Rate limit exceeded for IP {ip} on {request.path}")
            return self.rate_limit_response(request)
        
        # Process request
        response = self.get_response(request)
        
        # Post-process response
        processing_time = time.time() - start_time
        
        # Log slow requests
        if processing_time > 2.0:  # Log requests taking more than 2 seconds
            logger.warning(f"Slow request: {request.path} took {processing_time:.2f}s from IP {ip}")
        
        # Add security headers
        response = self.add_security_headers(response)
        
        return response
    
    def get_client_ip(self, request):
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip
    
    def should_rate_limit(self, request):
        """Check if the request should be rate limited."""
        ip = self.get_client_ip(request)
        
        # Determine rate limit type based on URL
        try:
            url_name = resolve(request.path_info).url_name
            namespace = resolve(request.path_info).namespace
            full_name = f"{namespace}:{url_name}" if namespace else url_name
        except:
            full_name = request.path_info
        
        # Determine rate limit category
        if any(endpoint in full_name for endpoint in ['login', 'register']):
            limit_type = 'auth'
        elif any(endpoint in full_name for endpoint in ['deposit', 'withdrawal', 'transfer']):
            limit_type = 'transaction'
        elif 'admin' in full_name:
            limit_type = 'admin'
        else:
            limit_type = 'general'
        
        # Get rate limit settings
        rate_config = self.rate_limits.get(limit_type, self.rate_limits['general'])
        limit = rate_config['limit']
        window = rate_config['window']
        
        # Create cache key
        cache_key = f"rate_limit:{limit_type}:{ip}"
        
        # Get current attempts
        attempts = cache.get(cache_key, 0)
        
        if attempts >= limit:
            return True
        
        # Increment attempts
        cache.set(cache_key, attempts + 1, window)
        return False
    
    def rate_limit_response(self, request):
        """Return rate limit exceeded response."""
        if request.content_type == 'application/json':
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.'
            }, status=429)
        else:
            response = HttpResponse(
                "Too many requests. Please try again later.",
                status=429
            )
            return response
    
    def add_security_headers(self, response):
        """Add security headers to the response."""
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Content Security Policy (basic)
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self';"
        )
        
        return response


class RequestLoggingMiddleware:
    """
    Middleware for comprehensive request logging.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Sensitive data that should not be logged
        self.sensitive_fields = [
            'password', 'password1', 'password2', 'csrfmiddlewaretoken',
            'old_password', 'new_password1', 'new_password2'
        ]
    
    def __call__(self, request):
        # Log request details
        self.log_request(request)
        
        # Process request
        response = self.get_response(request)
        
        # Log response details
        self.log_response(request, response)
        
        return response
    
    def log_request(self, request):
        """Log incoming request details."""
        ip = self.get_client_ip(request)
        user = request.user if hasattr(request, 'user') and request.user.is_authenticated else 'Anonymous'
        
        # Sanitize POST data for logging
        post_data = {}
        if request.method == 'POST':
            for key, value in request.POST.items():
                if key.lower() not in self.sensitive_fields:
                    post_data[key] = str(value)[:100]  # Truncate long values
                else:
                    post_data[key] = '[REDACTED]'
        
        log_data = {
            'method': request.method,
            'path': request.path,
            'ip': ip,
            'user': str(user),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
            'post_data': post_data if post_data else None,
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f"Request: {log_data}")
    
    def log_response(self, request, response):
        """Log response details."""
        ip = self.get_client_ip(request)
        
        log_data = {
            'path': request.path,
            'ip': ip,
            'status_code': response.status_code,
            'timestamp': timezone.now().isoformat()
        }
        
        # Log different levels based on status code
        if response.status_code >= 500:
            logger.error(f"Server Error Response: {log_data}")
        elif response.status_code >= 400:
            logger.warning(f"Client Error Response: {log_data}")
        else:
            logger.info(f"Response: {log_data}")
    
    def get_client_ip(self, request):
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip


class TransactionSecurityMiddleware:
    """
    Middleware specifically for transaction security monitoring.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Transaction endpoints that need monitoring
        self.transaction_endpoints = [
            '/transactions/deposit/',
            '/transactions/withdrawal/',
            '/transactions/transfer/',
        ]
    
    def __call__(self, request):
        # Check if this is a transaction request
        is_transaction = any(endpoint in request.path for endpoint in self.transaction_endpoints)
        
        if is_transaction and request.method == 'POST':
            # Log transaction attempt
            self.log_transaction_attempt(request)
            
            # Check for suspicious transaction patterns
            if self.is_suspicious_transaction(request):
                logger.warning(f"Suspicious transaction attempt from IP {self.get_client_ip(request)}")
        
        response = self.get_response(request)
        
        return response
    
    def log_transaction_attempt(self, request):
        """Log transaction attempts for security monitoring."""
        ip = self.get_client_ip(request)
        user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
        
        # Extract transaction details (sanitized)
        amount = request.POST.get('amount', 'unknown')
        transaction_type = self.get_transaction_type(request.path)
        
        log_data = {
            'transaction_type': transaction_type,
            'amount': amount if amount != 'unknown' else 'unknown',
            'user': str(user) if user else 'Anonymous',
            'ip': ip,
            'timestamp': timezone.now().isoformat(),
            'path': request.path
        }
        
        logger.info(f"Transaction Attempt: {log_data}")
    
    def is_suspicious_transaction(self, request):
        """Check for suspicious transaction patterns."""
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return True  # Unauthenticated transaction attempts are suspicious
        
        # Check for rapid transaction attempts
        user_id = request.user.id
        ip = self.get_client_ip(request)
        cache_key = f"transaction_attempts:{user_id}:{ip}"
        
        attempts = cache.get(cache_key, 0)
        if attempts > 5:  # More than 5 transaction attempts in the cache window
            return True
        
        cache.set(cache_key, attempts + 1, 300)  # 5-minute window
        
        # Check for unusual amounts
        try:
            amount = float(request.POST.get('amount', 0))
            if amount > 50000:  # Transactions over $50,000 are flagged
                return True
        except (ValueError, TypeError):
            pass
        
        return False
    
    def get_transaction_type(self, path):
        """Determine transaction type from path."""
        if 'deposit' in path:
            return 'deposit'
        elif 'withdrawal' in path:
            return 'withdrawal'
        elif 'transfer' in path:
            return 'transfer'
        return 'unknown'
    
    def get_client_ip(self, request):
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip