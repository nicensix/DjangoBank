"""
Security-focused unit tests for the banking platform.
"""

import unittest
from decimal import Decimal
from django.test import TestCase, RequestFactory, Client
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.contrib.messages import get_messages
from accounts.models import BankAccount
from accounts.forms import UserRegistrationForm, UserLoginForm
from transactions.forms import DepositForm, WithdrawalForm, TransferForm
from core.security import (
    SecurityValidator, sanitize_input, validate_account_number_format,
    validate_amount_format, generate_secure_token, hash_sensitive_data,
    check_suspicious_activity, RateLimitMixin
)

User = get_user_model()


class SecurityValidatorTest(TestCase):
    """Test the SecurityValidator class."""
    
    def test_password_strength_validation(self):
        """Test password strength validation."""
        # Valid password
        is_valid, errors = SecurityValidator.validate_password_strength('StrongPass123!')
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Too short
        is_valid, errors = SecurityValidator.validate_password_strength('Short1!')
        self.assertFalse(is_valid)
        self.assertIn('at least 8 characters', ' '.join(errors))
        
        # No uppercase
        is_valid, errors = SecurityValidator.validate_password_strength('lowercase123!')
        self.assertFalse(is_valid)
        self.assertIn('uppercase letter', ' '.join(errors))
        
        # No lowercase
        is_valid, errors = SecurityValidator.validate_password_strength('UPPERCASE123!')
        self.assertFalse(is_valid)
        self.assertIn('lowercase letter', ' '.join(errors))
        
        # No digit
        is_valid, errors = SecurityValidator.validate_password_strength('NoDigits!')
        self.assertFalse(is_valid)
        self.assertIn('digit', ' '.join(errors))
        
        # No special character
        is_valid, errors = SecurityValidator.validate_password_strength('NoSpecial123')
        self.assertFalse(is_valid)
        self.assertIn('special character', ' '.join(errors))
        
        # Repeated characters
        is_valid, errors = SecurityValidator.validate_password_strength('Passsss123!')
        self.assertFalse(is_valid)
        self.assertIn('repeated characters', ' '.join(errors))
    
    def test_username_security_validation(self):
        """Test username security validation."""
        # Valid username
        is_valid, errors = SecurityValidator.validate_username_security('validuser123')
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Too short
        is_valid, errors = SecurityValidator.validate_username_security('ab')
        self.assertFalse(is_valid)
        self.assertIn('at least 3 characters', ' '.join(errors))
        
        # Too long
        is_valid, errors = SecurityValidator.validate_username_security('a' * 31)
        self.assertFalse(is_valid)
        self.assertIn('longer than 30 characters', ' '.join(errors))
        
        # Invalid characters
        is_valid, errors = SecurityValidator.validate_username_security('user@domain.com')
        self.assertFalse(is_valid)
        self.assertIn('letters, numbers, dots, hyphens, and underscores', ' '.join(errors))
        
        # Reserved username
        is_valid, errors = SecurityValidator.validate_username_security('admin')
        self.assertFalse(is_valid)
        self.assertIn('reserved', ' '.join(errors))
    
    def test_transaction_amount_validation(self):
        """Test transaction amount validation."""
        # Valid amount
        is_valid, errors = SecurityValidator.validate_transaction_amount(Decimal('100.50'), 'deposit')
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Zero amount
        is_valid, errors = SecurityValidator.validate_transaction_amount(Decimal('0'), 'deposit')
        self.assertFalse(is_valid)
        self.assertIn('greater than zero', ' '.join(errors))
        
        # Negative amount
        is_valid, errors = SecurityValidator.validate_transaction_amount(Decimal('-100'), 'deposit')
        self.assertFalse(is_valid)
        self.assertIn('greater than zero', ' '.join(errors))
        
        # Too many decimal places
        is_valid, errors = SecurityValidator.validate_transaction_amount(Decimal('100.123'), 'deposit')
        self.assertFalse(is_valid)
        self.assertIn('2 decimal places', ' '.join(errors))
        
        # Exceeds deposit limit
        is_valid, errors = SecurityValidator.validate_transaction_amount(Decimal('200000'), 'deposit')
        self.assertFalse(is_valid)
        self.assertIn('exceeds maximum limit', ' '.join(errors))
        
        # Exceeds withdrawal limit
        is_valid, errors = SecurityValidator.validate_transaction_amount(Decimal('20000'), 'withdrawal')
        self.assertFalse(is_valid)
        self.assertIn('exceeds maximum limit', ' '.join(errors))
        
        # Invalid format
        is_valid, errors = SecurityValidator.validate_transaction_amount('invalid', 'deposit')
        self.assertFalse(is_valid)
        self.assertIn('Invalid amount format', ' '.join(errors))


class SecurityUtilsTest(TestCase):
    """Test security utility functions."""
    
    def test_sanitize_input(self):
        """Test input sanitization."""
        # Basic HTML escaping
        result = sanitize_input('<script>alert("xss")</script>')
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;script&gt;', result)
        
        # Null byte removal
        result = sanitize_input('test\x00string')
        self.assertEqual(result, 'teststring')
        
        # Control character removal
        result = sanitize_input('test\x01\x02string')
        self.assertEqual(result, 'teststring')
        
        # Whitespace trimming
        result = sanitize_input('  test string  ')
        self.assertEqual(result, 'test string')
    
    def test_validate_account_number_format(self):
        """Test account number format validation."""
        # Valid account number
        self.assertTrue(validate_account_number_format('123456789012'))
        
        # Too short
        self.assertFalse(validate_account_number_format('12345'))
        
        # Too long
        self.assertFalse(validate_account_number_format('1234567890123'))
        
        # Contains letters
        self.assertFalse(validate_account_number_format('12345678901a'))
        
        # Not a string
        self.assertFalse(validate_account_number_format(123456789012))
    
    def test_validate_amount_format(self):
        """Test amount format validation."""
        # Valid amounts
        self.assertTrue(validate_amount_format('100.50'))
        self.assertTrue(validate_amount_format(100.50))
        self.assertTrue(validate_amount_format(Decimal('100.50')))
        
        # Invalid amounts
        self.assertFalse(validate_amount_format('invalid'))
        self.assertFalse(validate_amount_format(-100))
        self.assertFalse(validate_amount_format('100.123'))  # Too many decimal places
        self.assertFalse(validate_amount_format('1000000000'))  # Too large
    
    def test_generate_secure_token(self):
        """Test secure token generation."""
        token1 = generate_secure_token()
        token2 = generate_secure_token()
        
        # Tokens should be different
        self.assertNotEqual(token1, token2)
        
        # Default length should be 32
        self.assertEqual(len(token1), 32)
        
        # Custom length
        token3 = generate_secure_token(16)
        self.assertEqual(len(token3), 16)
    
    def test_hash_sensitive_data(self):
        """Test sensitive data hashing."""
        # Hash should be consistent
        hash1 = hash_sensitive_data('sensitive_data')
        hash2 = hash_sensitive_data('sensitive_data')
        self.assertEqual(hash1, hash2)
        
        # Different data should produce different hashes
        hash3 = hash_sensitive_data('different_data')
        self.assertNotEqual(hash1, hash3)
        
        # Empty data
        hash4 = hash_sensitive_data('')
        self.assertEqual(hash4, 'empty')
        
        # None data
        hash5 = hash_sensitive_data(None)
        self.assertEqual(hash5, 'empty')


class RateLimitTest(TestCase):
    """Test rate limiting functionality."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.rate_limiter = RateLimitMixin()
        cache.clear()  # Clear cache before each test
    
    def test_rate_limiting(self):
        """Test basic rate limiting."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        # First few requests should not be rate limited
        for i in range(3):
            self.assertFalse(self.rate_limiter.is_rate_limited(request, 'test', limit=5, window=300))
        
        # Exceed the limit
        for i in range(3):
            self.rate_limiter.is_rate_limited(request, 'test', limit=5, window=300)
        
        # Should now be rate limited
        self.assertTrue(self.rate_limiter.is_rate_limited(request, 'test', limit=5, window=300))
    
    def test_different_ips_separate_limits(self):
        """Test that different IPs have separate rate limits."""
        request1 = self.factory.get('/')
        request1.META['REMOTE_ADDR'] = '127.0.0.1'
        
        request2 = self.factory.get('/')
        request2.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Exhaust limit for first IP
        for i in range(5):
            self.rate_limiter.is_rate_limited(request1, 'test', limit=5, window=300)
        
        # First IP should be rate limited
        self.assertTrue(self.rate_limiter.is_rate_limited(request1, 'test', limit=5, window=300))
        
        # Second IP should not be rate limited
        self.assertFalse(self.rate_limiter.is_rate_limited(request2, 'test', limit=5, window=300))


class FormSecurityTest(TestCase):
    """Test form security enhancements."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User'
        )
        self.bank_account = BankAccount.objects.create(
            user=self.user,
            account_type='savings',
            balance=Decimal('1000.00'),
            status='active'
        )
    
    def test_registration_form_security(self):
        """Test registration form security validation."""
        # Valid data
        form_data = {
            'username': 'newuser123',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'account_type': 'savings'
        }
        form = UserRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Weak password
        form_data['password1'] = 'weak'
        form_data['password2'] = 'weak'
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)
        
        # Invalid username
        form_data['username'] = 'admin'  # Reserved username
        form_data['password1'] = 'SecurePass123!'
        form_data['password2'] = 'SecurePass123!'
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        
        # XSS attempt in name
        form_data['username'] = 'validuser'
        form_data['first_name'] = '<script>alert("xss")</script>'
        form = UserRegistrationForm(data=form_data)
        if form.is_valid():
            # Should be sanitized
            self.assertNotIn('<script>', form.cleaned_data['first_name'])
    
    def test_login_form_security(self):
        """Test login form security validation."""
        request = self.factory.post('/login/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        # Valid login
        form_data = {
            'username': 'testuser',
            'password': 'TestPass123!'
        }
        form = UserLoginForm(data=form_data, request=request)
        self.assertTrue(form.is_valid())
        
        # Invalid credentials
        form_data['password'] = 'wrongpassword'
        form = UserLoginForm(data=form_data, request=request)
        self.assertFalse(form.is_valid())
        
        # XSS attempt in username
        form_data['username'] = '<script>alert("xss")</script>'
        form = UserLoginForm(data=form_data, request=request)
        if not form.is_valid() and 'username' in form.cleaned_data:
            # Should be sanitized
            self.assertNotIn('<script>', form.cleaned_data['username'])
    
    def test_transaction_form_security(self):
        """Test transaction form security validation."""
        request = self.factory.post('/deposit/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.user = self.user
        
        # Valid deposit
        form_data = {
            'amount': '100.50',
            'description': 'Test deposit'
        }
        form = DepositForm(data=form_data, request=request)
        self.assertTrue(form.is_valid())
        
        # Invalid amount
        form_data['amount'] = '-100'
        form = DepositForm(data=form_data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
        
        # XSS attempt in description
        form_data['amount'] = '100.50'
        form_data['description'] = '<script>alert("xss")</script>'
        form = DepositForm(data=form_data, request=request)
        if form.is_valid():
            # Should be sanitized
            self.assertNotIn('<script>', form.cleaned_data['description'])
        
        # Suspicious description
        form_data['description'] = 'money laundering operation'
        form = DepositForm(data=form_data, request=request)
        # Form should still be valid but logged as suspicious
        self.assertTrue(form.is_valid())


class ViewSecurityTest(TestCase):
    """Test view-level security."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User'
        )
        self.bank_account = BankAccount.objects.create(
            user=self.user,
            account_type='savings',
            balance=Decimal('1000.00'),
            status='active'
        )
    
    def test_csrf_protection(self):
        """Test CSRF protection on forms."""
        # Login first
        self.client.login(username='testuser', password='TestPass123!')
        
        # Try to submit form without CSRF token
        response = self.client.post('/transactions/deposit/', {
            'amount': '100.00',
            'description': 'Test deposit'
        })
        
        # Should be rejected due to missing CSRF token
        self.assertEqual(response.status_code, 403)
    
    def test_authentication_required(self):
        """Test that authentication is required for protected views."""
        # Try to access dashboard without login
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Try to access transaction views without login
        response = self.client.get('/transactions/deposit/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_session_security(self):
        """Test session security features."""
        # Login
        response = self.client.post('/accounts/login/', {
            'username': 'testuser',
            'password': 'TestPass123!'
        })
        
        # Check that session cookies have security flags
        # Note: This would need to be tested in a production environment
        # with HTTPS enabled for secure cookies
        
        # Verify session is created
        self.assertIn('sessionid', self.client.cookies)
    
    def test_input_validation_in_views(self):
        """Test that views properly validate input."""
        self.client.login(username='testuser', password='TestPass123!')
        
        # Test with invalid amount
        response = self.client.post('/transactions/deposit/', {
            'amount': 'invalid_amount',
            'description': 'Test'
        })
        
        # Should show form errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error')  # Should contain error message


class SuspiciousActivityTest(TestCase):
    """Test suspicious activity detection."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
    
    def test_suspicious_activity_detection(self):
        """Test detection of suspicious activity patterns."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.META['HTTP_USER_AGENT'] = 'Normal Browser'
        request.user = self.user
        
        # Normal request should not be suspicious
        indicators = check_suspicious_activity(request, self.user)
        self.assertFalse(any(indicators.values()))
        
        # Suspicious user agent
        request.META['HTTP_USER_AGENT'] = 'Bot/1.0'
        indicators = check_suspicious_activity(request, self.user)
        self.assertTrue(indicators['unusual_user_agent'])
    
    def test_rapid_request_detection(self):
        """Test detection of rapid requests."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.META['HTTP_USER_AGENT'] = 'Normal Browser'
        request.user = self.user
        
        # Simulate rapid requests by manipulating cache
        cache_key = f"request_count:{self.user.id}:127.0.0.1"
        cache.set(cache_key, 150, 300)  # Set high request count
        
        indicators = check_suspicious_activity(request, self.user)
        self.assertTrue(indicators['rapid_requests'])


if __name__ == '__main__':
    unittest.main()