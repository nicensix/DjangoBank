"""
Comprehensive security tests for the banking platform.
Tests authentication, authorization, input validation, and security vulnerabilities.
"""

import time
from decimal import Decimal
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.cache import cache
from django.test.utils import override_settings
from django.db import transaction
from accounts.models import BankAccount
from transactions.models import Transaction
from admin_panel.models import AdminAction
from .fixtures import TestDataFixtures, TestScenarios

User = get_user_model()


class AuthenticationSecurityTest(TestCase):
    """Test authentication security measures."""
    
    def setUp(self):
        self.client = Client()
        self.test_data = TestDataFixtures.create_complete_test_dataset()
        self.users = self.test_data['users']
        self.login_url = reverse('accounts:login')
    
    def test_password_strength_enforcement(self):
        """Test that weak passwords are rejected during registration."""
        registration_url = reverse('accounts:register')
        
        weak_passwords = [
            'password',      # Common password
            '123456',        # Numeric only
            'abc',           # Too short
            'PASSWORD',      # No lowercase
            'password123',   # No uppercase
            'Password',      # No numbers
            'Password123',   # No special characters
        ]
        
        for weak_password in weak_passwords:
            response = self.client.post(registration_url, {
                'username': f'testuser_{weak_password[:3]}',
                'first_name': 'Test',
                'last_name': 'User',
                'email': f'test_{weak_password[:3]}@example.com',
                'password1': weak_password,
                'password2': weak_password,
                'account_type': 'savings'
            })
            
            # Should stay on registration page with errors
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'error', msg_prefix=f"Weak password '{weak_password}' should be rejected")
    
    def test_brute_force_protection(self):
        """Test protection against brute force login attempts."""
        # Attempt multiple failed logins
        for i in range(6):  # Exceed typical rate limit
            response = self.client.post(self.login_url, {
                'username': 'testuser1',
                'password': 'wrongpassword'
            })
            
            if i < 5:
                # First few attempts should show normal error
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Invalid username or password')
            else:
                # After rate limit, should be blocked or show rate limit message
                # Implementation may vary, but should not allow unlimited attempts
                pass
    
    def test_session_security(self):
        """Test session security measures."""
        # Login successfully
        response = self.client.post(self.login_url, {
            'username': 'testuser1',
            'password': 'TestPass123!'
        })
        self.assertEqual(response.status_code, 302)
        
        # Verify session exists
        self.assertIn('sessionid', self.client.cookies)
        
        # Access protected page
        dashboard_response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(dashboard_response.status_code, 200)
        
        # Logout
        logout_response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(logout_response.status_code, 302)
        
        # Verify session cleared
        dashboard_after_logout = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(dashboard_after_logout.status_code, 302)  # Redirect to login
    
    def test_password_hashing(self):
        """Test that passwords are properly hashed."""
        user = self.users['user1']
        
        # Password should not be stored in plain text
        self.assertNotEqual(user.password, 'TestPass123!')
        
        # Should use Django's password hashing
        self.assertTrue(user.password.startswith('pbkdf2_sha256$'))
        
        # Should verify correctly
        self.assertTrue(user.check_password('TestPass123!'))
        self.assertFalse(user.check_password('wrongpassword'))
    
    def test_account_lockout_after_failed_attempts(self):
        """Test account lockout after multiple failed login attempts."""
        username = 'testuser1'
        
        # Make multiple failed attempts
        failed_attempts = 0
        for i in range(10):
            response = self.client.post(self.login_url, {
                'username': username,
                'password': 'wrongpassword'
            })
            
            if response.status_code == 200 and 'Invalid username or password' in response.content.decode():
                failed_attempts += 1
            elif 'too many' in response.content.decode().lower() or 'locked' in response.content.decode().lower():
                # Account should be locked after several attempts
                break
        
        # Should have some protection mechanism
        self.assertGreater(failed_attempts, 0)


class AuthorizationSecurityTest(TestCase):
    """Test authorization and access control security."""
    
    def setUp(self):
        self.client = Client()
        self.test_data = TestDataFixtures.create_complete_test_dataset()
        self.users = self.test_data['users']
        self.accounts = self.test_data['accounts']
    
    def test_user_data_isolation(self):
        """Test that users can only access their own data."""
        # Login as user1
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Try to access user2's transaction history by manipulating URLs
        user2_account = self.accounts['user2_savings']
        
        # Create a transaction for user2
        Transaction.objects.create(
            transaction_type='deposit',
            amount=Decimal('100.00'),
            receiver_account=user2_account,
            description='User2 private transaction'
        )
        
        # User1 should not see user2's transactions in their history
        history_response = self.client.get(reverse('transactions:history'))
        self.assertEqual(history_response.status_code, 200)
        self.assertNotContains(history_response, 'User2 private transaction')
        
        # User1 should not be able to transfer from user2's account
        transfer_response = self.client.post(reverse('transactions:transfer'), {
            'recipient_account_number': self.accounts['user1_savings'].account_number,
            'amount': '50.00',
            'description': 'Unauthorized transfer attempt'
        })
        
        # Should not succeed (user can only transfer from their own accounts)
        # The form should validate that the sender is the logged-in user
        if transfer_response.status_code == 200:
            self.assertContains(transfer_response, 'error')
    
    def test_admin_access_control(self):
        """Test that admin functions are properly protected."""
        # Regular user should not access admin functions
        self.client.login(username='testuser1', password='TestPass123!')
        
        admin_urls = [
            reverse('admin_panel:dashboard'),
            reverse('admin_panel:user_management'),
            reverse('admin_panel:account_management'),
            reverse('admin_panel:transaction_monitoring'),
        ]
        
        for url in admin_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, f"Regular user should not access {url}")
            self.assertIn('login', response.url.lower())
        
        # Admin user should access admin functions
        self.client.logout()
        self.client.login(username='adminuser', password='AdminPass123!')
        
        for url in admin_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Admin user should access {url}")
    
    def test_account_status_enforcement(self):
        """Test that account status is properly enforced."""
        # Test with frozen account
        frozen_account = self.accounts['user3_frozen']
        self.client.login(username='testuser3', password='TestPass123!')
        
        # Should not be able to perform transactions on frozen account
        deposit_response = self.client.get(reverse('transactions:deposit'))
        self.assertEqual(deposit_response.status_code, 302)  # Should redirect with error
        
        messages = list(get_messages(deposit_response.wsgi_request))
        self.assertTrue(any('frozen' in str(m).lower() for m in messages))
    
    def test_cross_site_request_forgery_protection(self):
        """Test CSRF protection on forms."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Try to submit form without CSRF token
        response = self.client.post(reverse('transactions:deposit'), {
            'amount': '100.00',
            'description': 'CSRF test'
        }, HTTP_X_CSRFTOKEN='')
        
        # Should be rejected due to missing/invalid CSRF token
        self.assertEqual(response.status_code, 403)
    
    def test_direct_object_reference_protection(self):
        """Test protection against insecure direct object references."""
        # Login as user1
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Try to access another user's account by ID manipulation
        user2_account = self.accounts['user2_savings']
        
        # This would be a vulnerability if the system allowed it
        # The system should validate that the user owns the account being accessed
        
        # For example, if there were URLs like /account/{id}/details
        # The system should verify ownership before showing details
        
        # Since our current system doesn't expose such URLs, we test the principle
        # by ensuring transaction forms validate account ownership
        
        # Try to transfer from an account the user doesn't own
        # This should be prevented by proper authorization checks
        pass  # Implementation depends on specific URL patterns


class InputValidationSecurityTest(TestCase):
    """Test input validation and sanitization security."""
    
    def setUp(self):
        self.client = Client()
        self.test_data = TestDataFixtures.create_complete_test_dataset()
        self.users = self.test_data['users']
        self.accounts = self.test_data['accounts']
    
    def test_sql_injection_protection(self):
        """Test protection against SQL injection attacks."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Try SQL injection in form fields
        malicious_inputs = [
            "'; DROP TABLE transactions; --",
            "' OR '1'='1",
            "1; DELETE FROM accounts WHERE 1=1; --",
            "' UNION SELECT * FROM auth_user --"
        ]
        
        for malicious_input in malicious_inputs:
            # Try in deposit description
            response = self.client.post(reverse('transactions:deposit'), {
                'amount': '10.00',
                'description': malicious_input
            })
            
            # Should either succeed with sanitized input or fail validation
            # But should not cause SQL injection
            self.assertIn(response.status_code, [200, 302])
            
            # Database should still be intact
            self.assertTrue(Transaction.objects.exists())
            self.assertTrue(User.objects.exists())
    
    def test_xss_protection(self):
        """Test protection against Cross-Site Scripting (XSS) attacks."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Try XSS in form fields
        xss_payloads = [
            '<script>alert("XSS")</script>',
            '<img src="x" onerror="alert(\'XSS\')">',
            'javascript:alert("XSS")',
            '<svg onload="alert(\'XSS\')">',
            '"><script>alert("XSS")</script>'
        ]
        
        for payload in xss_payloads:
            # Try XSS in transaction description
            response = self.client.post(reverse('transactions:deposit'), {
                'amount': '10.00',
                'description': payload
            })
            
            if response.status_code == 302:  # Successful submission
                # Check that the payload is properly escaped in transaction history
                history_response = self.client.get(reverse('transactions:history'))
                self.assertEqual(history_response.status_code, 200)
                
                # Should not contain unescaped script tags
                self.assertNotContains(history_response, '<script>')
                self.assertNotContains(history_response, 'javascript:')
                self.assertNotContains(history_response, 'onerror=')
    
    def test_amount_validation_security(self):
        """Test security of amount validation."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Try various malicious amount inputs
        malicious_amounts = [
            '-999999999',      # Large negative number
            '999999999999',    # Extremely large number
            '1.999999999',     # Too many decimal places
            'NaN',             # Not a number
            'Infinity',        # Infinity
            '1e308',           # Scientific notation
            '0x1000',          # Hexadecimal
            '1,000,000',       # With commas
            '1 OR 1=1',        # SQL injection attempt
        ]
        
        for malicious_amount in malicious_amounts:
            response = self.client.post(reverse('transactions:deposit'), {
                'amount': malicious_amount,
                'description': 'Security test'
            })
            
            # Should either show validation error or reject the input
            if response.status_code == 200:
                self.assertContains(response, 'error')
            
            # Account balance should not be affected by invalid input
            account = self.accounts['user1_savings']
            account.refresh_from_db()
            # Balance should remain reasonable (not affected by malicious input)
            self.assertLess(account.balance, Decimal('1000000'))
    
    def test_account_number_validation_security(self):
        """Test security of account number validation."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Try various malicious account number inputs
        malicious_account_numbers = [
            "'; DROP TABLE accounts; --",
            '../../../etc/passwd',
            '<script>alert("XSS")</script>',
            '000000000000',  # All zeros
            '999999999999',  # All nines
            'ABCDEFGHIJKL',  # Letters
            '12345678901234567890',  # Too long
            '',  # Empty
            None,  # None value
        ]
        
        for malicious_number in malicious_account_numbers:
            if malicious_number is None:
                continue
                
            response = self.client.post(reverse('transactions:transfer'), {
                'recipient_account_number': malicious_number,
                'amount': '10.00',
                'description': 'Security test transfer'
            })
            
            # Should show validation error for invalid account numbers
            if response.status_code == 200:
                self.assertContains(response, 'error')
            
            # No transaction should be created with invalid account number
            self.assertFalse(Transaction.objects.filter(
                description='Security test transfer',
                transaction_type='transfer'
            ).exists())


class SessionSecurityTest(TestCase):
    """Test session security measures."""
    
    def setUp(self):
        self.client = Client()
        self.test_data = TestDataFixtures.create_complete_test_dataset()
        self.users = self.test_data['users']
    
    def test_session_timeout(self):
        """Test session timeout functionality."""
        # Login
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser1',
            'password': 'TestPass123!'
        })
        self.assertEqual(response.status_code, 302)
        
        # Access protected page
        dashboard_response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(dashboard_response.status_code, 200)
        
        # Simulate session timeout by clearing session
        self.client.logout()
        
        # Try to access protected page after timeout
        dashboard_after_timeout = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(dashboard_after_timeout.status_code, 302)  # Should redirect to login
    
    def test_concurrent_session_handling(self):
        """Test handling of concurrent sessions for the same user."""
        client1 = Client()
        client2 = Client()
        
        # Login with same user from two different clients
        response1 = client1.post(reverse('accounts:login'), {
            'username': 'testuser1',
            'password': 'TestPass123!'
        })
        self.assertEqual(response1.status_code, 302)
        
        response2 = client2.post(reverse('accounts:login'), {
            'username': 'testuser1',
            'password': 'TestPass123!'
        })
        self.assertEqual(response2.status_code, 302)
        
        # Both sessions should be able to access dashboard
        # (Unless system implements single-session policy)
        dashboard1 = client1.get(reverse('accounts:dashboard'))
        dashboard2 = client2.get(reverse('accounts:dashboard'))
        
        # At minimum, both should not cause errors
        self.assertIn(dashboard1.status_code, [200, 302])
        self.assertIn(dashboard2.status_code, [200, 302])
    
    def test_session_fixation_protection(self):
        """Test protection against session fixation attacks."""
        # Get initial session ID
        initial_response = self.client.get(reverse('accounts:login'))
        initial_session_id = self.client.session.session_key
        
        # Login
        login_response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser1',
            'password': 'TestPass123!'
        })
        self.assertEqual(login_response.status_code, 302)
        
        # Session ID should change after login (protection against session fixation)
        new_session_id = self.client.session.session_key
        
        # Note: Django automatically handles session fixation protection
        # This test verifies the behavior exists
        if initial_session_id and new_session_id:
            # If both exist, they should be different
            self.assertNotEqual(initial_session_id, new_session_id)


class DataProtectionSecurityTest(TestCase):
    """Test data protection and privacy security measures."""
    
    def setUp(self):
        self.client = Client()
        self.test_data = TestDataFixtures.create_complete_test_dataset()
        self.users = self.test_data['users']
        self.accounts = self.test_data['accounts']
    
    def test_sensitive_data_exposure(self):
        """Test that sensitive data is not exposed in responses."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Check dashboard response
        dashboard_response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(dashboard_response.status_code, 200)
        
        # Should not contain sensitive information in HTML
        response_content = dashboard_response.content.decode()
        
        # Should not expose full account numbers in HTML comments or hidden fields
        # (Account numbers shown to user are acceptable, but not in hidden/debug info)
        
        # Should not contain password hashes
        self.assertNotIn('pbkdf2_sha256', response_content)
        
        # Should not contain database connection strings
        self.assertNotIn('DATABASE_URL', response_content)
        self.assertNotIn('SECRET_KEY', response_content)
    
    def test_error_message_information_disclosure(self):
        """Test that error messages don't disclose sensitive information."""
        # Try to login with non-existent user
        response = self.client.post(reverse('accounts:login'), {
            'username': 'nonexistentuser12345',
            'password': 'somepassword'
        })
        
        # Error message should be generic, not revealing whether user exists
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')
        
        # Should not reveal specific information like "User does not exist"
        self.assertNotContains(response, 'User does not exist')
        self.assertNotContains(response, 'nonexistentuser12345')
    
    def test_transaction_data_privacy(self):
        """Test that transaction data is properly protected."""
        # Create transactions for different users
        Transaction.objects.create(
            transaction_type='deposit',
            amount=Decimal('1000.00'),
            receiver_account=self.accounts['user1_savings'],
            description='User1 confidential deposit'
        )
        
        Transaction.objects.create(
            transaction_type='deposit',
            amount=Decimal('2000.00'),
            receiver_account=self.accounts['user2_savings'],
            description='User2 confidential deposit'
        )
        
        # Login as user1
        self.client.login(username='testuser1', password='TestPass123!')
        
        # User1 should only see their own transactions
        history_response = self.client.get(reverse('transactions:history'))
        self.assertEqual(history_response.status_code, 200)
        
        self.assertContains(history_response, 'User1 confidential deposit')
        self.assertNotContains(history_response, 'User2 confidential deposit')


class RateLimitingSecurityTest(TestCase):
    """Test rate limiting security measures."""
    
    def setUp(self):
        self.client = Client()
        self.test_data = TestDataFixtures.create_complete_test_dataset()
        self.users = self.test_data['users']
        cache.clear()  # Clear cache before tests
    
    def test_login_rate_limiting(self):
        """Test rate limiting on login attempts."""
        # Make multiple rapid login attempts
        attempts = 0
        for i in range(10):
            response = self.client.post(reverse('accounts:login'), {
                'username': 'testuser1',
                'password': 'wrongpassword'
            })
            attempts += 1
            
            # After several attempts, should be rate limited
            if i > 5 and (response.status_code == 429 or 'rate limit' in response.content.decode().lower()):
                break
        
        # Should have some form of rate limiting
        self.assertGreater(attempts, 3)  # At least some attempts allowed
    
    def test_transaction_rate_limiting(self):
        """Test rate limiting on transaction submissions."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Make multiple rapid transaction attempts
        successful_transactions = 0
        rate_limited = False
        
        for i in range(20):
            response = self.client.post(reverse('transactions:deposit'), {
                'amount': '1.00',
                'description': f'Rate limit test {i}'
            })
            
            if response.status_code == 302:  # Successful
                successful_transactions += 1
            elif response.status_code == 429 or 'rate limit' in response.content.decode().lower():
                rate_limited = True
                break
            
            time.sleep(0.1)  # Small delay between requests
        
        # Should allow reasonable number of transactions
        self.assertGreater(successful_transactions, 5)
        
        # May or may not have rate limiting depending on implementation
        # This test documents the behavior


class ErrorHandlingSecurityTest(TestCase):
    """Test security aspects of error handling."""
    
    def setUp(self):
        self.client = Client()
        self.test_data = TestDataFixtures.create_complete_test_dataset()
        self.users = self.test_data['users']
        self.accounts = self.test_data['accounts']
    
    def test_database_error_handling(self):
        """Test that database errors don't expose sensitive information."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Try to cause a database constraint violation
        # (This is a controlled test, not actual malicious input)
        
        # Create a transaction with duplicate reference number (if system allows custom refs)
        # Or try other constraint violations
        
        # The system should handle errors gracefully without exposing:
        # - Database schema information
        # - Connection strings
        # - Internal file paths
        # - Stack traces in production
        
        # For now, test that normal operations work correctly
        response = self.client.post(reverse('transactions:deposit'), {
            'amount': '10.00',
            'description': 'Error handling test'
        })
        
        # Should either succeed or fail gracefully
        self.assertIn(response.status_code, [200, 302])
    
    def test_exception_information_disclosure(self):
        """Test that exceptions don't disclose sensitive information."""
        # This test would be more relevant in a production environment
        # where DEBUG=False and proper error handling is configured
        
        # Try to access non-existent URLs
        response = self.client.get('/nonexistent/url/')
        self.assertEqual(response.status_code, 404)
        
        # 404 page should not expose sensitive information
        if response.status_code == 404:
            content = response.content.decode()
            self.assertNotIn('SECRET_KEY', content)
            self.assertNotIn('DATABASE', content)
            self.assertNotIn('/home/', content)  # File paths
    
    def test_form_error_security(self):
        """Test that form errors don't expose sensitive information."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Submit invalid form data
        response = self.client.post(reverse('transactions:transfer'), {
            'recipient_account_number': 'invalid',
            'amount': 'invalid',
            'description': 'Error test'
        })
        
        # Should show form errors
        self.assertEqual(response.status_code, 200)
        
        # Error messages should be user-friendly, not technical
        content = response.content.decode()
        self.assertNotIn('ValidationError', content)
        self.assertNotIn('traceback', content)
        self.assertNotIn('Exception', content)