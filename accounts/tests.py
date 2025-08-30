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
