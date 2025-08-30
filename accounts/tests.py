from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from .models import BankAccount

User = get_user_model()


class UserModelTest(TestCase):
    """Test cases for the custom User model."""
    
    def setUp(self):
        """Set up test data."""
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'testpass123'
        }
    
    def test_create_user(self):
        """Test creating a user with valid data."""
        user = User.objects.create_user(**self.user_data)
        
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertTrue(user.check_password('testpass123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_create_superuser(self):
        """Test creating a superuser."""
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.assertEqual(superuser.username, 'admin')
        self.assertTrue(superuser.is_active)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
    
    def test_user_string_representation(self):
        """Test the string representation of the user."""
        user = User.objects.create_user(**self.user_data)
        expected_str = "testuser (Test User)"
        self.assertEqual(str(user), expected_str)
    
    def test_user_string_representation_without_names(self):
        """Test string representation when first_name and last_name are empty."""
        user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        expected_str = "testuser2 ( )"
        self.assertEqual(str(user), expected_str)
    
    def test_username_uniqueness(self):
        """Test that usernames must be unique."""
        User.objects.create_user(**self.user_data)
        
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username='testuser',  # Same username
                email='different@example.com',
                password='testpass123'
            )
    
    def test_email_field(self):
        """Test email field functionality."""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.email, 'test@example.com')
        
        # Test that email can be blank
        user_no_email = User.objects.create_user(
            username='testuser2',
            password='testpass123'
        )
        self.assertEqual(user_no_email.email, '')
    
    def test_user_permissions(self):
        """Test user permissions functionality."""
        user = User.objects.create_user(**self.user_data)
        
        # Test default permissions
        self.assertFalse(user.has_perm('some_permission'))
        self.assertFalse(user.has_module_perms('some_app'))
        
        # Test superuser permissions
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.assertTrue(superuser.has_perm('any_permission'))
        self.assertTrue(superuser.has_module_perms('any_app'))
    
    def test_user_authentication(self):
        """Test user authentication functionality."""
        user = User.objects.create_user(**self.user_data)
        
        # Test correct password
        self.assertTrue(user.check_password('testpass123'))
        
        # Test incorrect password
        self.assertFalse(user.check_password('wrongpassword'))
    
    def test_user_active_status(self):
        """Test user active status functionality."""
        user = User.objects.create_user(**self.user_data)
        
        # User should be active by default
        self.assertTrue(user.is_active)
        
        # Test deactivating user
        user.is_active = False
        user.save()
        self.assertFalse(user.is_active)
    
    def test_user_model_meta(self):
        """Test User model meta options."""
        self.assertEqual(User._meta.db_table, 'auth_user')
        self.assertEqual(User._meta.verbose_name, 'User')
        self.assertEqual(User._meta.verbose_name_plural, 'Users')


class BankAccountModelTest(TestCase):
    """Test cases for the BankAccount model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.account_data = {
            'user': self.user,
            'account_type': 'savings',
            'balance': 1000.00,
            'status': 'active'
        }
    
    def test_create_bank_account(self):
        """Test creating a bank account with valid data."""
        account = BankAccount.objects.create(**self.account_data)
        
        self.assertEqual(account.user, self.user)
        self.assertEqual(account.account_type, 'savings')
        self.assertEqual(account.balance, 1000.00)
        self.assertEqual(account.status, 'active')
        self.assertIsNotNone(account.account_number)
        self.assertEqual(len(account.account_number), 12)
        self.assertTrue(account.account_number.isdigit())
    
    def test_account_number_generation(self):
        """Test automatic account number generation."""
        account = BankAccount.objects.create(**self.account_data)
        
        # Account number should be generated automatically
        self.assertIsNotNone(account.account_number)
        self.assertEqual(len(account.account_number), 12)
        self.assertTrue(account.account_number.isdigit())
        self.assertFalse(account.account_number.startswith('0'))
    
    def test_account_number_uniqueness(self):
        """Test that account numbers are unique."""
        account1 = BankAccount.objects.create(**self.account_data)
        account2 = BankAccount.objects.create(**self.account_data)
        
        self.assertNotEqual(account1.account_number, account2.account_number)
    
    def test_custom_account_number(self):
        """Test creating account with custom account number."""
        custom_account_data = self.account_data.copy()
        custom_account_data['account_number'] = '123456789012'
        
        account = BankAccount.objects.create(**custom_account_data)
        self.assertEqual(account.account_number, '123456789012')
    
    def test_account_number_validation(self):
        """Test account number validation."""
        # Test valid account numbers
        self.assertTrue(BankAccount.is_valid_account_number('123456789012'))
        self.assertTrue(BankAccount.is_valid_account_number('987654321098'))
        
        # Test invalid account numbers
        self.assertFalse(BankAccount.is_valid_account_number('012345678901'))  # Starts with 0
        self.assertFalse(BankAccount.is_valid_account_number('12345678901'))   # Too short
        self.assertFalse(BankAccount.is_valid_account_number('1234567890123')) # Too long
        self.assertFalse(BankAccount.is_valid_account_number('12345678901a'))  # Contains letter
        self.assertFalse(BankAccount.is_valid_account_number(123456789012))    # Not string
    
    def test_negative_balance_validation(self):
        """Test that negative balance raises validation error."""
        account_data = self.account_data.copy()
        account_data['balance'] = -100.00
        
        account = BankAccount(**account_data)
        with self.assertRaises(ValidationError) as context:
            account.full_clean()
        
        self.assertIn('balance', context.exception.message_dict)
        self.assertIn('cannot be negative', str(context.exception.message_dict['balance']))
    
    def test_invalid_account_number_validation(self):
        """Test that invalid account number raises validation error."""
        account_data = self.account_data.copy()
        account_data['account_number'] = '12345'  # Too short
        
        account = BankAccount(**account_data)
        with self.assertRaises(ValidationError) as context:
            account.full_clean()
        
        self.assertIn('account_number', context.exception.message_dict)
    
    def test_account_status_methods(self):
        """Test account status checking methods."""
        account = BankAccount.objects.create(**self.account_data)
        
        # Test active account
        account.status = 'active'
        self.assertTrue(account.is_active())
        self.assertFalse(account.is_frozen())
        self.assertTrue(account.can_transact())
        
        # Test frozen account
        account.status = 'frozen'
        self.assertFalse(account.is_active())
        self.assertTrue(account.is_frozen())
        self.assertFalse(account.can_transact())
        
        # Test closed account
        account.status = 'closed'
        self.assertFalse(account.is_active())
        self.assertFalse(account.is_frozen())
        self.assertFalse(account.can_transact())
    
    def test_account_status_change_methods(self):
        """Test methods for changing account status."""
        account = BankAccount.objects.create(**self.account_data)
        
        # Test freezing account
        account.freeze_account()
        account.refresh_from_db()
        self.assertEqual(account.status, 'frozen')
        
        # Test unfreezing account
        account.unfreeze_account()
        account.refresh_from_db()
        self.assertEqual(account.status, 'active')
        
        # Test closing account
        account.close_account()
        account.refresh_from_db()
        self.assertEqual(account.status, 'closed')
        
        # Test approving pending account
        account.status = 'pending'
        account.save()
        account.approve_account()
        account.refresh_from_db()
        self.assertEqual(account.status, 'active')
    
    def test_account_string_representation(self):
        """Test the string representation of the account."""
        account = BankAccount.objects.create(**self.account_data)
        expected_str = f"{account.account_number} - testuser (Savings)"
        self.assertEqual(str(account), expected_str)
    
    def test_account_type_choices(self):
        """Test account type choices."""
        # Test savings account
        savings_account = BankAccount.objects.create(**self.account_data)
        self.assertEqual(savings_account.account_type, 'savings')
        self.assertEqual(savings_account.get_account_type_display(), 'Savings')
        
        # Test current account
        current_account_data = self.account_data.copy()
        current_account_data['account_type'] = 'current'
        current_account = BankAccount.objects.create(**current_account_data)
        self.assertEqual(current_account.account_type, 'current')
        self.assertEqual(current_account.get_account_type_display(), 'Current')
    
    def test_default_values(self):
        """Test default values for model fields."""
        minimal_data = {'user': self.user}
        account = BankAccount.objects.create(**minimal_data)
        
        self.assertEqual(account.account_type, 'savings')
        self.assertEqual(account.balance, 0.00)
        self.assertEqual(account.status, 'pending')
        self.assertIsNotNone(account.created_at)
        self.assertIsNotNone(account.updated_at)
    
    def test_user_relationship(self):
        """Test the relationship between User and BankAccount."""
        account1 = BankAccount.objects.create(**self.account_data)
        account2 = BankAccount.objects.create(**self.account_data)
        
        # Test forward relationship
        self.assertEqual(account1.user, self.user)
        self.assertEqual(account2.user, self.user)
        
        # Test reverse relationship
        user_accounts = self.user.bank_accounts.all()
        self.assertIn(account1, user_accounts)
        self.assertIn(account2, user_accounts)
        self.assertEqual(user_accounts.count(), 2)
    
    def test_model_meta_options(self):
        """Test model meta options."""
        self.assertEqual(BankAccount._meta.db_table, 'bank_accounts')
        self.assertEqual(BankAccount._meta.verbose_name, 'Bank Account')
        self.assertEqual(BankAccount._meta.verbose_name_plural, 'Bank Accounts')
        self.assertEqual(BankAccount._meta.ordering, ['-created_at'])

# Import additional modules for view and form tests
from django.test import Client
from django.urls import reverse
from .forms import UserRegistrationForm, UserLoginForm


class UserRegistrationFormTest(TestCase):
    """Test cases for UserRegistrationForm."""
    
    def test_valid_registration_form(self):
        """Test form with valid data."""
        form_data = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'account_type': 'savings'
        }
        form = UserRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_duplicate_username(self):
        """Test form with duplicate username."""
        User.objects.create_user(username='testuser', email='existing@example.com')
        
        form_data = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'account_type': 'savings'
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
    
    def test_duplicate_email(self):
        """Test form with duplicate email."""
        User.objects.create_user(username='existing', email='test@example.com')
        
        form_data = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'account_type': 'savings'
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_password_mismatch(self):
        """Test form with mismatched passwords."""
        form_data = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'differentpass',
            'account_type': 'savings'
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
    
    def test_form_save_creates_bank_account(self):
        """Test that saving form creates user and bank account."""
        form_data = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'account_type': 'current'
        }
        form = UserRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        user = form.save()
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        
        # Check bank account was created
        bank_account = BankAccount.objects.get(user=user)
        self.assertEqual(bank_account.account_type, 'current')
        self.assertEqual(bank_account.status, 'pending')
        self.assertEqual(bank_account.balance, 0.00)


class UserLoginFormTest(TestCase):
    """Test cases for UserLoginForm."""
    
    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
    
    def test_valid_login_form(self):
        """Test form with valid credentials."""
        form_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        form = UserLoginForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_invalid_credentials(self):
        """Test form with invalid credentials."""
        form_data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        form = UserLoginForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Invalid username or password', str(form.errors))
    
    def test_inactive_user(self):
        """Test form with inactive user."""
        self.user.is_active = False
        self.user.save()
        
        form_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        form = UserLoginForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('This account is inactive', str(form.errors))


class RegistrationViewTest(TestCase):
    """Test cases for registration view."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
        self.register_url = reverse('accounts:register')
    
    def test_registration_view_get(self):
        """Test GET request to registration view."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Your Account')
        self.assertIsInstance(response.context['form'], UserRegistrationForm)
    
    def test_registration_view_post_valid(self):
        """Test POST request with valid data."""
        form_data = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'account_type': 'savings'
        }
        response = self.client.post(self.register_url, data=form_data)
        
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:login'))
        
        # Check user was created
        user = User.objects.get(username='testuser')
        self.assertEqual(user.email, 'test@example.com')
        
        # Check bank account was created
        bank_account = BankAccount.objects.get(user=user)
        self.assertEqual(bank_account.account_type, 'savings')
        self.assertEqual(bank_account.status, 'pending')
    
    def test_registration_view_post_invalid(self):
        """Test POST request with invalid data."""
        form_data = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'invalid-email',
            'password1': 'testpass123',
            'password2': 'differentpass',
            'account_type': 'savings'
        }
        response = self.client.post(self.register_url, data=form_data)
        
        # Should stay on registration page
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please correct the errors below')
        
        # Check user was not created
        self.assertFalse(User.objects.filter(username='testuser').exists())
    
    def test_authenticated_user_redirect(self):
        """Test that authenticated users are redirected from registration."""
        user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:dashboard'))


class LoginViewTest(TestCase):
    """Test cases for login view."""
    
    def setUp(self):
        """Set up test client and user."""
        self.client = Client()
        self.login_url = reverse('accounts:login')
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            first_name='Test'
        )
    
    def test_login_view_get(self):
        """Test GET request to login view."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome Back')
        self.assertIsInstance(response.context['form'], UserLoginForm)
    
    def test_login_view_post_valid(self):
        """Test POST request with valid credentials."""
        form_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data=form_data)
        
        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:dashboard'))
    
    def test_login_view_post_invalid(self):
        """Test POST request with invalid credentials."""
        form_data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, data=form_data)
        
        # Should stay on login page
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')
    
    def test_authenticated_user_redirect(self):
        """Test that authenticated users are redirected from login."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:dashboard'))


class LogoutViewTest(TestCase):
    """Test cases for logout view."""
    
    def setUp(self):
        """Set up test client and user."""
        self.client = Client()
        self.logout_url = reverse('accounts:logout')
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            first_name='Test'
        )
    
    def test_logout_view(self):
        """Test logout functionality."""
        # Login first
        self.client.login(username='testuser', password='testpass123')
        
        # Then logout
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:login'))
        
        # Check user is logged out
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 302)  # Should redirect to login


class DashboardViewTest(TestCase):
    """Test cases for dashboard view."""
    
    def setUp(self):
        """Set up test client and user with bank account."""
        self.client = Client()
        self.dashboard_url = reverse('accounts:dashboard')
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            first_name='Test'
        )
        self.bank_account = BankAccount.objects.create(
            user=self.user,
            account_type='savings',
            balance=1000.00,
            status='active'
        )
    
    def test_dashboard_view_authenticated(self):
        """Test dashboard view for authenticated user."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome, Test!')
        self.assertContains(response, self.bank_account.account_number)
        self.assertContains(response, '$1000.00')
    
    def test_dashboard_view_unauthenticated(self):
        """Test dashboard view for unauthenticated user."""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)
        # Should redirect to login with next parameter
        expected_url = f"{reverse('accounts:login')}?next={self.dashboard_url}"
        self.assertRedirects(response, expected_url)
    
    def test_dashboard_view_no_bank_account(self):
        """Test dashboard view for user without bank account."""
        user_no_account = User.objects.create_user(
            username='noaccountuser',
            password='testpass123',
            first_name='NoAccount'
        )
        self.client.login(username='noaccountuser', password='testpass123')
        
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No bank account found')