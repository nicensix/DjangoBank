from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .utils import generate_account_number, format_currency, validate_positive_amount


class CoreViewsTestCase(TestCase):
    """Test cases for core app views."""
    
    def setUp(self):
        self.client = Client()
    
    def test_home_view(self):
        """Test that the home page loads correctly."""
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome to Banking Platform')
        self.assertContains(response, 'Secure Banking')


class CoreUtilsTestCase(TestCase):
    """Test cases for core utility functions."""
    
    def test_generate_account_number(self):
        """Test account number generation."""
        account_number = generate_account_number()
        self.assertEqual(len(account_number), 10)
        self.assertTrue(account_number.isdigit())
        
        # Test uniqueness by generating multiple numbers
        numbers = [generate_account_number() for _ in range(100)]
        self.assertEqual(len(numbers), len(set(numbers)))  # All should be unique
    
    def test_format_currency(self):
        """Test currency formatting."""
        self.assertEqual(format_currency(100), '$100.00')
        self.assertEqual(format_currency(1234.56), '$1,234.56')
        self.assertEqual(format_currency(0), '$0.00')
    
    def test_validate_positive_amount(self):
        """Test amount validation."""
        self.assertTrue(validate_positive_amount(100))
        self.assertTrue(validate_positive_amount(0.01))
        self.assertFalse(validate_positive_amount(0))
        self.assertFalse(validate_positive_amount(-100))
        self.assertFalse(validate_positive_amount('invalid'))