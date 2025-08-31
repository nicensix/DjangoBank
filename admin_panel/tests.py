from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from accounts.models import BankAccount
from transactions.models import Transaction
from .models import AdminAction

User = get_user_model()


class AdminDashboardViewTests(TestCase):
    """Test cases for admin dashboard view and access control."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username='regular_user',
            email='regular@example.com',
            password='testpass123'
        )
        
        # Create staff user
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )
        
        # Create superuser
        self.superuser = User.objects.create_superuser(
            username='admin_user',
            email='admin@example.com',
            password='testpass123'
        )
        
        # Create some test accounts
        self.account1 = BankAccount.objects.create(
            user=self.regular_user,
            account_type='savings',
            balance=1000.00,
            status='active'
        )
        
        self.account2 = BankAccount.objects.create(
            user=self.regular_user,
            account_type='current',
            balance=500.00,
            status='pending'
        )
        
        # Create test transaction
        self.transaction = Transaction.objects.create(
            transaction_type='deposit',
            amount=100.00,
            receiver_account=self.account1,
            description='Test deposit'
        )
        
        self.dashboard_url = reverse('admin_panel:dashboard')
    
    def test_admin_dashboard_requires_login(self):
        """Test that admin dashboard requires user to be logged in."""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_regular_user_cannot_access_admin_dashboard(self):
        """Test that regular users cannot access admin dashboard."""
        self.client.login(username='regular_user', password='testpass123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_staff_user_can_access_admin_dashboard(self):
        """Test that staff users can access admin dashboard."""
        self.client.login(username='staff_user', password='testpass123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Dashboard')
    
    def test_superuser_can_access_admin_dashboard(self):
        """Test that superusers can access admin dashboard."""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Dashboard')
    
    def test_admin_dashboard_displays_user_statistics(self):
        """Test that admin dashboard displays correct user statistics."""
        self.client.login(username='staff_user', password='testpass123')
        response = self.client.get(self.dashboard_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Total Users')
        
        # Check context data
        self.assertEqual(response.context['total_users'], 3)  # 3 users created
        self.assertEqual(response.context['active_users'], 3)  # All users are active
    
    def test_admin_dashboard_displays_account_statistics(self):
        """Test that admin dashboard displays correct account statistics."""
        self.client.login(username='staff_user', password='testpass123')
        response = self.client.get(self.dashboard_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bank Accounts')
        
        # Check context data
        self.assertEqual(response.context['total_accounts'], 2)
        self.assertEqual(response.context['active_accounts'], 1)
        self.assertEqual(response.context['pending_accounts'], 1)
        self.assertEqual(response.context['frozen_accounts'], 0)
        self.assertEqual(response.context['closed_accounts'], 0)
    
    def test_admin_dashboard_displays_transaction_statistics(self):
        """Test that admin dashboard displays correct transaction statistics."""
        self.client.login(username='staff_user', password='testpass123')
        response = self.client.get(self.dashboard_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Transactions')
        
        # Check context data
        self.assertEqual(response.context['total_transactions'], 1)
    
    def test_admin_dashboard_displays_total_balance(self):
        """Test that admin dashboard calculates and displays total system balance."""
        self.client.login(username='staff_user', password='testpass123')
        response = self.client.get(self.dashboard_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Total Balance')
        
        # Total balance should only include active and frozen accounts
        # account1 is active (1000.00), account2 is pending (not included)
        expected_balance = 1000.00  # Only active accounts are included
        self.assertEqual(float(response.context['total_balance']), expected_balance)
    
    def test_admin_dashboard_shows_pending_accounts(self):
        """Test that admin dashboard shows accounts pending approval."""
        self.client.login(username='staff_user', password='testpass123')
        response = self.client.get(self.dashboard_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that pending accounts are in context
        pending_accounts = response.context['pending_approval_accounts']
        self.assertEqual(len(pending_accounts), 1)
        self.assertEqual(pending_accounts[0], self.account2)
    
    def test_admin_dashboard_shows_recent_activities(self):
        """Test that admin dashboard shows recent activities."""
        # Create an admin action
        AdminAction.objects.create(
            action_type='account_approve',
            admin_user=self.staff_user,
            target_account=self.account1,
            target_user=self.regular_user,
            description='Account approved for testing'
        )
        
        self.client.login(username='staff_user', password='testpass123')
        response = self.client.get(self.dashboard_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check recent admin actions
        recent_actions = response.context['recent_admin_actions']
        self.assertEqual(len(recent_actions), 1)
        self.assertEqual(recent_actions[0].action_type, 'account_approve')
        
        # Check recent transactions
        recent_transactions = response.context['recent_transactions']
        self.assertEqual(len(recent_transactions), 1)
        self.assertEqual(recent_transactions[0], self.transaction)
    
    def test_admin_dashboard_template_rendering(self):
        """Test that admin dashboard template renders correctly."""
        self.client.login(username='staff_user', password='testpass123')
        response = self.client.get(self.dashboard_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin_panel/dashboard.html')
        
        # Check for key elements in the template
        self.assertContains(response, 'Admin Dashboard')
        self.assertContains(response, 'User Management')
        self.assertContains(response, 'Transaction Monitor')
        self.assertContains(response, 'Recent Activity')
    
    def test_is_admin_user_function(self):
        """Test the is_admin_user helper function."""
        from admin_panel.views import is_admin_user
        
        # Test with regular user
        self.assertFalse(is_admin_user(self.regular_user))
        
        # Test with staff user
        self.assertTrue(is_admin_user(self.staff_user))
        
        # Test with superuser
        self.assertTrue(is_admin_user(self.superuser))
        
        # Test with anonymous user
        from django.contrib.auth.models import AnonymousUser
        anonymous_user = AnonymousUser()
        self.assertFalse(is_admin_user(anonymous_user))


class AdminNavigationTests(TestCase):
    """Test cases for admin navigation in base template."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username='regular_user',
            email='regular@example.com',
            password='testpass123'
        )
        
        # Create staff user
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )
        
        # Use home page to test navigation
        self.home_url = reverse('core:home')
    
    def test_admin_navigation_not_shown_to_regular_users(self):
        """Test that admin navigation is not shown to regular users."""
        self.client.login(username='regular_user', password='testpass123')
        response = self.client.get(self.home_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Admin Panel')
    
    def test_admin_navigation_shown_to_staff_users(self):
        """Test that admin navigation is shown to staff users."""
        self.client.login(username='staff_user', password='testpass123')
        response = self.client.get(self.home_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Panel')
    
    def test_admin_navigation_not_shown_to_anonymous_users(self):
        """Test that admin navigation is not shown to anonymous users."""
        response = self.client.get(self.home_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Admin Panel')


class UserManagementViewTests(TestCase):
    """Test cases for user management view and operations."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create staff user
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )
        
        # Create regular users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123',
            is_active=False
        )
        
        self.superuser = User.objects.create_superuser(
            username='superuser',
            email='super@example.com',
            password='testpass123'
        )
        
        self.user_management_url = reverse('admin_panel:user_management')
    
    def test_user_management_requires_admin_access(self):
        """Test that user management requires admin access."""
        # Test without login
        response = self.client.get(self.user_management_url)
        self.assertEqual(response.status_code, 302)
        
        # Test with regular user
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.user_management_url)
        self.assertEqual(response.status_code, 302)
    
    def test_user_management_displays_users(self):
        """Test that user management displays users correctly."""
        self.client.login(username='staff_user', password='testpass123')
        response = self.client.get(self.user_management_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Management')
        self.assertContains(response, 'user1')
        self.assertContains(response, 'user2')
        self.assertContains(response, 'John Doe')
    
    def test_user_search_functionality(self):
        """Test user search functionality."""
        self.client.login(username='staff_user', password='testpass123')
        
        # Search by username
        response = self.client.get(self.user_management_url, {'search': 'user1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'user1')
        self.assertNotContains(response, 'user2')
        
        # Search by name
        response = self.client.get(self.user_management_url, {'search': 'John'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'user1')
        self.assertNotContains(response, 'user2')
    
    def test_user_status_filter(self):
        """Test user status filtering."""
        self.client.login(username='staff_user', password='testpass123')
        
        # Filter active users
        response = self.client.get(self.user_management_url, {'status': 'active'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'user1')
        self.assertNotContains(response, 'user2')
        
        # Filter inactive users
        response = self.client.get(self.user_management_url, {'status': 'inactive'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'user1')
        self.assertContains(response, 'user2')
    
    def test_toggle_user_status(self):
        """Test toggling user active status."""
        self.client.login(username='staff_user', password='testpass123')
        
        # Deactivate active user
        response = self.client.post(
            reverse('admin_panel:toggle_user_status', args=[self.user1.id]),
            {'reason': 'Test deactivation'}
        )
        self.assertEqual(response.status_code, 302)
        
        self.user1.refresh_from_db()
        self.assertFalse(self.user1.is_active)
        
        # Check admin action was logged
        action = AdminAction.objects.filter(
            action_type='user_deactivate',
            target_user=self.user1
        ).first()
        self.assertIsNotNone(action)
        self.assertEqual(action.admin_user, self.staff_user)
        
        # Activate inactive user
        response = self.client.post(
            reverse('admin_panel:toggle_user_status', args=[self.user2.id]),
            {'reason': 'Test activation'}
        )
        self.assertEqual(response.status_code, 302)
        
        self.user2.refresh_from_db()
        self.assertTrue(self.user2.is_active)
    
    def test_cannot_deactivate_superuser(self):
        """Test that superusers cannot be deactivated."""
        self.client.login(username='staff_user', password='testpass123')
        
        response = self.client.post(
            reverse('admin_panel:toggle_user_status', args=[self.superuser.id])
        )
        self.assertEqual(response.status_code, 302)
        
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_active)


class AccountManagementViewTests(TestCase):
    """Test cases for account management view and operations."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create staff user
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username='regular_user',
            email='regular@example.com',
            password='testpass123'
        )
        
        # Create test accounts
        self.active_account = BankAccount.objects.create(
            user=self.regular_user,
            account_type='savings',
            balance=1000.00,
            status='active'
        )
        
        self.pending_account = BankAccount.objects.create(
            user=self.regular_user,
            account_type='current',
            balance=0.00,
            status='pending'
        )
        
        self.frozen_account = BankAccount.objects.create(
            user=self.regular_user,
            account_type='savings',
            balance=500.00,
            status='frozen'
        )
        
        self.account_management_url = reverse('admin_panel:account_management')
    
    def test_account_management_requires_admin_access(self):
        """Test that account management requires admin access."""
        # Test without login
        response = self.client.get(self.account_management_url)
        self.assertEqual(response.status_code, 302)
        
        # Test with regular user
        self.client.login(username='regular_user', password='testpass123')
        response = self.client.get(self.account_management_url)
        self.assertEqual(response.status_code, 302)
    
    def test_account_management_displays_accounts(self):
        """Test that account management displays accounts correctly."""
        self.client.login(username='staff_user', password='testpass123')
        response = self.client.get(self.account_management_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Account Management')
        self.assertContains(response, self.active_account.account_number)
        self.assertContains(response, self.pending_account.account_number)
        self.assertContains(response, self.frozen_account.account_number)
    
    def test_approve_account(self):
        """Test approving a pending account."""
        self.client.login(username='staff_user', password='testpass123')
        
        response = self.client.post(
            reverse('admin_panel:approve_account', args=[self.pending_account.id]),
            {'reason': 'Test approval'}
        )
        self.assertEqual(response.status_code, 302)
        
        self.pending_account.refresh_from_db()
        self.assertEqual(self.pending_account.status, 'active')
        
        # Check admin action was logged
        action = AdminAction.objects.filter(
            action_type='account_approve',
            target_account=self.pending_account
        ).first()
        self.assertIsNotNone(action)
        self.assertEqual(action.admin_user, self.staff_user)
    
    def test_freeze_account(self):
        """Test freezing an active account."""
        self.client.login(username='staff_user', password='testpass123')
        
        response = self.client.post(
            reverse('admin_panel:freeze_account', args=[self.active_account.id]),
            {'reason': 'Test freeze'}
        )
        self.assertEqual(response.status_code, 302)
        
        self.active_account.refresh_from_db()
        self.assertEqual(self.active_account.status, 'frozen')
        
        # Check admin action was logged
        action = AdminAction.objects.filter(
            action_type='account_freeze',
            target_account=self.active_account
        ).first()
        self.assertIsNotNone(action)
    
    def test_unfreeze_account(self):
        """Test unfreezing a frozen account."""
        self.client.login(username='staff_user', password='testpass123')
        
        response = self.client.post(
            reverse('admin_panel:unfreeze_account', args=[self.frozen_account.id]),
            {'reason': 'Test unfreeze'}
        )
        self.assertEqual(response.status_code, 302)
        
        self.frozen_account.refresh_from_db()
        self.assertEqual(self.frozen_account.status, 'active')
        
        # Check admin action was logged
        action = AdminAction.objects.filter(
            action_type='account_unfreeze',
            target_account=self.frozen_account
        ).first()
        self.assertIsNotNone(action)
    
    def test_close_account_with_zero_balance(self):
        """Test closing an account with zero balance."""
        # Create account with zero balance
        zero_balance_account = BankAccount.objects.create(
            user=self.regular_user,
            account_type='savings',
            balance=0.00,
            status='active'
        )
        
        self.client.login(username='staff_user', password='testpass123')
        
        response = self.client.post(
            reverse('admin_panel:close_account', args=[zero_balance_account.id]),
            {'reason': 'Test closure'}
        )
        self.assertEqual(response.status_code, 302)
        
        zero_balance_account.refresh_from_db()
        self.assertEqual(zero_balance_account.status, 'closed')
        
        # Check admin action was logged
        action = AdminAction.objects.filter(
            action_type='account_close',
            target_account=zero_balance_account
        ).first()
        self.assertIsNotNone(action)
    
    def test_cannot_close_account_with_positive_balance(self):
        """Test that accounts with positive balance cannot be closed."""
        self.client.login(username='staff_user', password='testpass123')
        
        response = self.client.post(
            reverse('admin_panel:close_account', args=[self.active_account.id]),
            {'reason': 'Test closure'}
        )
        self.assertEqual(response.status_code, 302)
        
        self.active_account.refresh_from_db()
        self.assertNotEqual(self.active_account.status, 'closed')
    
    def test_account_search_functionality(self):
        """Test account search functionality."""
        self.client.login(username='staff_user', password='testpass123')
        
        # Search by account number
        response = self.client.get(
            self.account_management_url, 
            {'search': self.active_account.account_number}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.active_account.account_number)
        
        # Search by username
        response = self.client.get(
            self.account_management_url, 
            {'search': 'regular_user'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.active_account.account_number)
    
    def test_account_status_filter(self):
        """Test account status filtering."""
        self.client.login(username='staff_user', password='testpass123')
        
        # Filter active accounts
        response = self.client.get(self.account_management_url, {'status': 'active'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.active_account.account_number)
        self.assertNotContains(response, self.pending_account.account_number)
        
        # Filter pending accounts
        response = self.client.get(self.account_management_url, {'status': 'pending'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.active_account.account_number)
        self.assertContains(response, self.pending_account.account_number)


class TransactionMonitoringViewTests(TestCase):
    """Test cases for transaction monitoring view and operations."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create staff user
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )
        
        # Create regular users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        
        # Create test accounts
        self.account1 = BankAccount.objects.create(
            user=self.user1,
            account_type='savings',
            balance=5000.00,
            status='active'
        )
        
        self.account2 = BankAccount.objects.create(
            user=self.user2,
            account_type='current',
            balance=3000.00,
            status='active'
        )
        
        # Create test transactions
        self.deposit_transaction = Transaction.objects.create(
            transaction_type='deposit',
            amount=1000.00,
            receiver_account=self.account1,
            description='Test deposit'
        )
        
        self.transfer_transaction = Transaction.objects.create(
            transaction_type='transfer',
            amount=500.00,
            sender_account=self.account1,
            receiver_account=self.account2,
            description='Test transfer'
        )
        
        self.high_value_transaction = Transaction.objects.create(
            transaction_type='transfer',
            amount=15000.00,
            sender_account=self.account1,
            receiver_account=self.account2,
            description='High value transfer'
        )
        
        self.transaction_monitoring_url = reverse('admin_panel:transaction_monitoring')
    
    def test_transaction_monitoring_requires_admin_access(self):
        """Test that transaction monitoring requires admin access."""
        # Test without login
        response = self.client.get(self.transaction_monitoring_url)
        self.assertEqual(response.status_code, 302)
        
        # Test with regular user
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.transaction_monitoring_url)
        self.assertEqual(response.status_code, 302)
    
    def test_transaction_monitoring_displays_transactions(self):
        """Test that transaction monitoring displays transactions correctly."""
        self.client.login(username='staff_user', password='testpass123')
        response = self.client.get(self.transaction_monitoring_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Transaction Monitoring')
        self.assertContains(response, self.deposit_transaction.reference_number)
        self.assertContains(response, self.transfer_transaction.reference_number)
        self.assertContains(response, self.high_value_transaction.reference_number)
    
    def test_transaction_search_functionality(self):
        """Test transaction search functionality."""
        self.client.login(username='staff_user', password='testpass123')
        
        # Search by reference number
        response = self.client.get(
            self.transaction_monitoring_url, 
            {'search': self.deposit_transaction.reference_number}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.deposit_transaction.reference_number)
        self.assertNotContains(response, self.transfer_transaction.reference_number)
        
        # Search by account number
        response = self.client.get(
            self.transaction_monitoring_url, 
            {'search': self.account1.account_number}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.deposit_transaction.reference_number)
        self.assertContains(response, self.transfer_transaction.reference_number)
    
    def test_transaction_type_filter(self):
        """Test transaction type filtering."""
        self.client.login(username='staff_user', password='testpass123')
        
        # Filter deposit transactions
        response = self.client.get(
            self.transaction_monitoring_url, 
            {'transaction_type': 'deposit'}
        )
        self.assertEqual(response.status_code, 200)
        # Check that only deposit transactions are in the main transaction list
        transactions = response.context['transactions']
        transaction_refs = [t.reference_number for t in transactions]
        self.assertIn(self.deposit_transaction.reference_number, transaction_refs)
        self.assertNotIn(self.transfer_transaction.reference_number, transaction_refs)
        
        # Filter transfer transactions
        response = self.client.get(
            self.transaction_monitoring_url, 
            {'transaction_type': 'transfer'}
        )
        self.assertEqual(response.status_code, 200)
        # Check that only transfer transactions are in the main transaction list
        transactions = response.context['transactions']
        transaction_refs = [t.reference_number for t in transactions]
        self.assertNotIn(self.deposit_transaction.reference_number, transaction_refs)
        self.assertIn(self.transfer_transaction.reference_number, transaction_refs)
    
    def test_amount_filter(self):
        """Test amount filtering."""
        self.client.login(username='staff_user', password='testpass123')
        
        # Filter by minimum amount
        response = self.client.get(
            self.transaction_monitoring_url, 
            {'amount_min': '10000'}
        )
        self.assertEqual(response.status_code, 200)
        # Check that only high value transaction is in the main transaction list
        transactions = response.context['transactions']
        transaction_refs = [t.reference_number for t in transactions]
        self.assertNotIn(self.deposit_transaction.reference_number, transaction_refs)
        self.assertNotIn(self.transfer_transaction.reference_number, transaction_refs)
        self.assertIn(self.high_value_transaction.reference_number, transaction_refs)
        
        # Filter by maximum amount
        response = self.client.get(
            self.transaction_monitoring_url, 
            {'amount_max': '1000'}
        )
        self.assertEqual(response.status_code, 200)
        # Check that only smaller transactions are in the main transaction list
        transactions = response.context['transactions']
        transaction_refs = [t.reference_number for t in transactions]
        self.assertIn(self.deposit_transaction.reference_number, transaction_refs)
        self.assertIn(self.transfer_transaction.reference_number, transaction_refs)
        self.assertNotIn(self.high_value_transaction.reference_number, transaction_refs)
    
    def test_flag_transaction(self):
        """Test flagging a transaction as suspicious."""
        self.client.login(username='staff_user', password='testpass123')
        
        response = self.client.post(
            reverse('admin_panel:flag_transaction', args=[self.high_value_transaction.id]),
            {
                'reason': 'Unusually large amount for this account',
                'freeze_accounts': 'true'
            }
        )
        self.assertEqual(response.status_code, 302)
        
        # Check that admin action was logged
        action = AdminAction.objects.filter(
            admin_user=self.staff_user,
            additional_data__transaction_id=self.high_value_transaction.id
        ).first()
        self.assertIsNotNone(action)
        
        # Check that accounts were frozen
        self.account1.refresh_from_db()
        self.account2.refresh_from_db()
        self.assertEqual(self.account1.status, 'frozen')
        self.assertEqual(self.account2.status, 'frozen')
    
    def test_flag_transaction_without_freezing(self):
        """Test flagging a transaction without freezing accounts."""
        self.client.login(username='staff_user', password='testpass123')
        
        response = self.client.post(
            reverse('admin_panel:flag_transaction', args=[self.transfer_transaction.id]),
            {'reason': 'Suspicious pattern detected'}
        )
        self.assertEqual(response.status_code, 302)
        
        # Check that admin action was logged
        action = AdminAction.objects.filter(
            admin_user=self.staff_user,
            additional_data__transaction_id=self.transfer_transaction.id
        ).first()
        self.assertIsNotNone(action)
        
        # Check that accounts were not frozen
        self.account1.refresh_from_db()
        self.account2.refresh_from_db()
        self.assertEqual(self.account1.status, 'active')
        self.assertEqual(self.account2.status, 'active')
    
    def test_transaction_detail_view(self):
        """Test transaction detail view."""
        self.client.login(username='staff_user', password='testpass123')
        
        response = self.client.get(
            reverse('admin_panel:transaction_detail', args=[self.transfer_transaction.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Transaction Detail')
        self.assertContains(response, self.transfer_transaction.reference_number)
        self.assertContains(response, self.account1.account_number)
        self.assertContains(response, self.account2.account_number)
    
    def test_transaction_detail_nonexistent(self):
        """Test transaction detail view with nonexistent transaction."""
        self.client.login(username='staff_user', password='testpass123')
        
        response = self.client.get(
            reverse('admin_panel:transaction_detail', args=[99999])
        )
        self.assertEqual(response.status_code, 302)
    
    def test_high_value_transaction_detection(self):
        """Test that high value transactions are properly detected."""
        self.client.login(username='staff_user', password='testpass123')
        response = self.client.get(self.transaction_monitoring_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that statistics include high value transactions
        self.assertGreater(response.context['high_value_transactions'], 0)
    
    def test_suspicious_transaction_detection(self):
        """Test suspicious transaction detection algorithms."""
        # Create multiple large transactions from same account
        for i in range(4):
            Transaction.objects.create(
                transaction_type='transfer',
                amount=6000.00,
                sender_account=self.account1,
                receiver_account=self.account2,
                description=f'Large transfer {i}'
            )
        
        self.client.login(username='staff_user', password='testpass123')
        response = self.client.get(self.transaction_monitoring_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that suspicious transactions are detected
        suspicious_transactions = response.context['suspicious_transactions']
        self.assertGreater(len(suspicious_transactions), 0)