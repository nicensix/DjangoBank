"""
Security utilities and functions for the banking platform.
"""

import re
import logging
import hashlib
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.html import escape
from django.utils.safestring import mark_safe

User = get_user_model()
logger = logging.getLogger(__name__)


class RateLimitMixin:
    """
    Mixin to add rate limiting functionality to views.
    """
    
    def get_client_ip(self, request):
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_rate_limited(self, request, action='default', limit=5, window=300):
        """
        Check if the request should be rate limited.
        
        Args:
            request: Django request object
            action: Action identifier for different rate limits
            limit: Maximum number of attempts allowed
            window: Time window in seconds
            
        Returns:
            bool: True if rate limited, False otherwise
        """
        ip = self.get_client_ip(request)
        cache_key = f"rate_limit:{action}:{ip}"
        
        # Get current attempts
        attempts = cache.get(cache_key, 0)
        
        if attempts >= limit:
            logger.warning(f"Rate limit exceeded for IP {ip} on action {action}")
            return True
        
        # Increment attempts
        cache.set(cache_key, attempts + 1, window)
        return False
    
    def log_security_event(self, request, event_type, details=None):
        """Log security-related events."""
        ip = self.get_client_ip(request)
        user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
        
        log_data = {
            'event_type': event_type,
            'ip_address': ip,
            'user': str(user) if user else 'Anonymous',
            'timestamp': timezone.now().isoformat(),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'details': details or {}
        }
        
        logger.warning(f"Security Event: {event_type} - {log_data}")


def sanitize_input(value, allow_html=False):
    """
    Sanitize user input to prevent XSS attacks.
    
    Args:
        value: Input value to sanitize
        allow_html: Whether to allow basic HTML tags
        
    Returns:
        str: Sanitized input
    """
    if not isinstance(value, str):
        return value
    
    # Remove null bytes and control characters
    value = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', value)
    
    if not allow_html:
        # Escape HTML entities
        value = escape(value)
    else:
        # Allow only basic HTML tags (for descriptions, etc.)
        allowed_tags = ['b', 'i', 'u', 'em', 'strong']
        # This is a basic implementation - in production, use a library like bleach
        for tag in allowed_tags:
            value = re.sub(f'<(?!/?{tag}\b)[^>]*>', '', value)
    
    return value.strip()


def validate_account_number_format(account_number):
    """
    Validate account number format for security.
    
    Args:
        account_number: Account number to validate
        
    Returns:
        bool: True if valid format, False otherwise
    """
    if not isinstance(account_number, str):
        return False
    
    # Account number should be exactly 12 digits
    pattern = r'^\d{12}$'
    return bool(re.match(pattern, account_number))


def validate_amount_format(amount):
    """
    Validate monetary amount format for security.
    
    Args:
        amount: Amount to validate
        
    Returns:
        bool: True if valid format, False otherwise
    """
    try:
        from decimal import Decimal, InvalidOperation
        
        # Convert to string first to handle various input types
        amount_str = str(amount).strip()
        
        # Check for valid decimal format
        decimal_amount = Decimal(amount_str)
        
        # Check for reasonable precision (max 2 decimal places)
        if decimal_amount.as_tuple().exponent < -2:
            return False
        
        # Check for reasonable range (not negative, not too large)
        if decimal_amount < 0 or decimal_amount > Decimal('999999999.99'):
            return False
        
        return True
        
    except (InvalidOperation, ValueError, TypeError):
        return False


def generate_secure_token(length=32):
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Length of the token
        
    Returns:
        str: Secure random token
    """
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_sensitive_data(data):
    """
    Hash sensitive data for logging purposes.
    
    Args:
        data: Sensitive data to hash
        
    Returns:
        str: Hashed data
    """
    if not data:
        return 'empty'
    
    # Use SHA-256 for hashing
    return hashlib.sha256(str(data).encode()).hexdigest()[:16]


class SecurityValidator:
    """
    Centralized security validation for forms and inputs.
    """
    
    @staticmethod
    def validate_password_strength(password):
        """
        Validate password strength beyond Django's default validators.
        
        Args:
            password: Password to validate
            
        Returns:
            tuple: (is_valid, error_messages)
        """
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long.")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter.")
        
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter.")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one digit.")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character.")
        
        # Check for common patterns
        if re.search(r'(.)\1{2,}', password):
            errors.append("Password cannot contain repeated characters.")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_username_security(username):
        """
        Validate username for security concerns.
        
        Args:
            username: Username to validate
            
        Returns:
            tuple: (is_valid, error_messages)
        """
        errors = []
        
        # Check length
        if len(username) < 3:
            errors.append("Username must be at least 3 characters long.")
        
        if len(username) > 30:
            errors.append("Username cannot be longer than 30 characters.")
        
        # Check for valid characters only
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            errors.append("Username can only contain letters, numbers, dots, hyphens, and underscores.")
        
        # Check for reserved usernames
        reserved_usernames = [
            'admin', 'administrator', 'root', 'system', 'test', 'user',
            'support', 'help', 'api', 'www', 'mail', 'email', 'bank',
            'banking', 'finance', 'money', 'cash', 'account', 'accounts'
        ]
        
        if username.lower() in reserved_usernames:
            errors.append("This username is reserved and cannot be used.")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_transaction_amount(amount, transaction_type='general'):
        """
        Validate transaction amounts with security checks.
        
        Args:
            amount: Amount to validate
            transaction_type: Type of transaction for specific limits
            
        Returns:
            tuple: (is_valid, error_messages)
        """
        errors = []
        
        try:
            from decimal import Decimal, InvalidOperation
            
            # Convert to Decimal for precise validation
            if isinstance(amount, str):
                amount = amount.strip()
            
            decimal_amount = Decimal(str(amount))
            
            # Basic validations
            if decimal_amount <= 0:
                errors.append("Amount must be greater than zero.")
            
            # Check decimal places
            if decimal_amount.as_tuple().exponent < -2:
                errors.append("Amount cannot have more than 2 decimal places.")
            
            # Transaction-specific limits
            limits = {
                'deposit': Decimal('100000.00'),    # $100,000
                'withdrawal': Decimal('10000.00'),   # $10,000
                'transfer': Decimal('50000.00'),     # $50,000
                'general': Decimal('100000.00')      # Default limit
            }
            
            max_amount = limits.get(transaction_type, limits['general'])
            
            if decimal_amount > max_amount:
                errors.append(f"Amount exceeds maximum limit of ${max_amount:,.2f} for {transaction_type} transactions.")
            
        except (InvalidOperation, ValueError, TypeError):
            errors.append("Invalid amount format.")
        
        return len(errors) == 0, errors


def log_authentication_attempt(request, username, success=False, failure_reason=None):
    """
    Log authentication attempts for security monitoring.
    
    Args:
        request: Django request object
        username: Username attempted
        success: Whether authentication was successful
        failure_reason: Reason for failure if applicable
    """
    ip = request.META.get('REMOTE_ADDR', 'unknown')
    user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
    
    log_data = {
        'timestamp': timezone.now().isoformat(),
        'ip_address': ip,
        'username': hash_sensitive_data(username),  # Hash username for privacy
        'success': success,
        'failure_reason': failure_reason,
        'user_agent': user_agent[:200]  # Truncate user agent
    }
    
    if success:
        logger.info(f"Successful login: {log_data}")
    else:
        logger.warning(f"Failed login attempt: {log_data}")


def check_suspicious_activity(request, user=None):
    """
    Check for suspicious activity patterns.
    
    Args:
        request: Django request object
        user: User object if authenticated
        
    Returns:
        dict: Suspicious activity indicators
    """
    indicators = {
        'suspicious_ip': False,
        'unusual_user_agent': False,
        'rapid_requests': False,
        'details': []
    }
    
    ip = request.META.get('REMOTE_ADDR', '')
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Check for suspicious IP patterns
    if ip:
        # Check for known bad IP ranges (this is a simplified example)
        # Note: 127.0.0.1 is localhost and should not be flagged in tests
        suspicious_patterns = ['0.0.0.0', '192.168.1.1']  # Add real patterns in production
        if any(pattern in ip for pattern in suspicious_patterns):
            indicators['suspicious_ip'] = True
            indicators['details'].append(f"Suspicious IP pattern: {ip}")
    
    # Check for unusual user agents
    if user_agent:
        suspicious_agents = ['bot', 'crawler', 'spider', 'scraper']
        if any(agent in user_agent.lower() for agent in suspicious_agents):
            indicators['unusual_user_agent'] = True
            indicators['details'].append("Suspicious user agent detected")
    
    # Check for rapid requests (basic implementation)
    if user:
        cache_key = f"request_count:{user.id}:{ip}"
        request_count = cache.get(cache_key, 0)
        if request_count > 100:  # More than 100 requests in the cache window
            indicators['rapid_requests'] = True
            indicators['details'].append("Rapid request pattern detected")
        
        cache.set(cache_key, request_count + 1, 300)  # 5-minute window
    
    return indicators