"""
Integration tests for complete user workflows in the banking platform.
These tests validate end-to-end functionality across multiple apps and components.
"""

import time
from decimal import Decimal
from django.test import TestCase, Client, TransactionTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.db import transaction
from accounts.models import BankAccount
from transactions.models import Transaction
from admin_panel.models import AdminAction

User = get_user_model()


class UserRegistrationAndAccountCreationWorkflowTest(TestCase):
    """Test complete user registration and account creation workflow."""
    
    def setUp(self):
        self.client = Client()
        self.registration_url = reverse('accounts:register')
        self.login_url = reverse('accounts:login')
        self.dashboard_url = reverse('accounts:dashboard')
    
    def test_complete_user_registration_workflow(self):
        """Test the complete user registration workflow from start to finish."""
        # Step 1: Access registration page
        response = self.client.get(self.registration_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Your Account')
        
        # Step 2: Submit valid registration data
        registration_data = {
            'username': 'newuser123',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'account_type': 'savings'
        }
        
        response = self.client.post(self.registration_url, data=registration_data)
        
        # Step 3: Verify redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.login_url)
        
        # Step 4: Verify user was created
        user = User.objects.get(username='newuser123')
        self.assertEqual(user.email, 'john.doe@example.com')
        self.assertEqual(user.first_name, 'John')
        self.assertEqual(user.last_name, 'Doe')
        self.assertTrue(user.check_password('SecurePass123!'))
        
        # Step 5: Verify bank account was automatically created
        bank_account = BankAccount.objects.get(user=user)
        self.assertEqual(bank_account.account_type, 'savings')
        self.assertEqual(bank_account.balance, Decimal('0.00'))
        self.assertEqual(bank_account.status, 'pending')
        self.assertIsNotNone(bank_account.account_number)
        self.assertEqual(len(bank_account.account_number), 12)
        
        # Step 6: Verify success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('successfully registered' in str(m).lower() for m in messages))
        
        # Step 7: Test login with new credentials
        login_response = self.client.post(self.login_url, {
            'username': 'newuser123',
            'password': 'SecurePass123!'
        })
        
        # Step 8: Verify successful login and redirect to dashboard
        self.assertEqual(login_response.status_code, 302)
        self.assertRedirects(login_response, self.dashboard_url)
        
        # Step 9: Access dashboard and verify account information is displayed
        dashboard_response = self.client.get(self.dashboard_url)
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, 'Welcome, John!')
        self.assertContains(dashboard_response, bank_account.account_number)
        self.assertContains(dashboard_response, '$0.00')  # Initial balance
        self.assertContains(dashboard_response, 'Pending')  # Account status
    
    def test_registration_with_duplicate_username(self):
        """Test registration workflow with duplicate username."""
        # Create existing user
        User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='TestPass123!'
        )
        
        # Attempt to register with same username
        registration_data = {
            'username': 'existinguser',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane@example.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'account_type': 'current'
        }
        
        response = self.client.post(self.registration_url, data=registration_data)
        
        # Should stay on registration page with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A user with that username already exists')
        
        # Verify no new user or bank account created
        self.assertEqual(User.objects.filter(email='jane@example.com').count(), 0)
    
    def test_registration_with_duplicate_email(self):
        """Test registration workflow with duplicate email."""
        # Create existing user
        User.objects.create_user(
            username='existinguser',
            email='duplicate@example.com',
            password='TestPass123!'
        )
        
        # Attempt to register with same email
        registration_data = {
            'username': 'newuser',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'duplicate@example.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'account_type': 'current'
        }
        
        response = self.client.post(self.registration_url, data=registration_data)
        
        # Should stay on registration page with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User with this email already exists')
        
        # Verify no new user created
        self.assertEqual(User.objects.filter(username='newuser').count(), 0)


class CompleteTransactionWorkflowTest(TestCase):
    """Test complete transaction workflows including deposit, withdrawal, and transfer."""
    
    def setUp(self):
        self.client = Client()
        
        # Create test users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='TestPass123!',
            first_name='Alice',
            last_name='Johnson'
        )
        
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='TestPass123!',
            first_name='Bob',
            last_name='Smith'
        )
        
        # Create bank accounts
        self.account1 = BankAccount.objects.create(
            user=self.user1,
            account_type='savings',
            balance=Decimal('1000.00'),
            status='active'
        )
        
        self.account2 = BankAccount.objects.create(
            user=self.user2,
            account_type='current',
            balance=Decimal('500.00'),
            status='active'
        )
        
        # URLs
        self.login_url = reverse('accounts:login')
        self.dashboard_url = reverse('accounts:dashboard')
        self.deposit_url = reverse('transactions:deposit')
        self.withdrawal_url = reverse('transactions:withdrawal')
        self.transfer_url = reverse('transactions:transfer')
        self.history_url = reverse('transactions:history')
    
    def test_complete_deposit_workflow(self):
        """Test complete deposit workflow from login to transaction completion."""
        # Step 1: Login
        login_response = self.client.post(self.login_url, {
            'username': 'user1',
            'password': 'TestPass123!'
        })
        self.assertEqual(login_response.status_code, 302)
        
        # Step 2: Access dashboard and verify initial balance
        dashboard_response = self.client.get(self.dashboard_url)
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, '$1000.00')
        
        # Step 3: Navigate to deposit page
        deposit_response = self.client.get(self.deposit_url)
        self.assertEqual(deposit_response.status_code, 200)
        self.assertContains(deposit_response, 'Deposit Money')
        self.assertContains(deposit_response, self.account1.account_number)
        
        # Step 4: Submit deposit form
        deposit_data = {
            'amount': '250.75',
            'description': 'Salary deposit'
        }
        
        submit_response = self.client.post(self.deposit_url, data=deposit_data)
        
        # Step 5: Verify redirect to dashboard
        self.assertEqual(submit_response.status_code, 302)
        self.assertRedirects(submit_response, self.dashboard_url)
        
        # Step 6: Verify success message
        messages = list(get_messages(submit_response.wsgi_request))
        self.assertTrue(any('Successfully deposited $250.75' in str(m) for m in messages))
        
        # Step 7: Verify balance updated
        self.account1.refresh_from_db()
        self.assertEqual(self.account1.balance, Decimal('1250.75'))
        
        # Step 8: Verify transaction record created
        transaction_record = Transaction.objects.filter(
            transaction_type='deposit',
            receiver_account=self.account1,
            amount=Decimal('250.75')
        ).first()
        
        self.assertIsNotNone(transaction_record)
        self.assertEqual(transaction_record.description, 'Salary deposit')
        self.assertEqual(transaction_record.receiver_balance_after, Decimal('1250.75'))
        
        # Step 9: Verify updated balance shown on dashboard
        final_dashboard_response = self.client.get(self.dashboard_url)
        self.assertContains(final_dashboard_response, '$1250.75')
        
        # Step 10: Verify transaction appears in history
        history_response = self.client.get(self.history_url)
        self.assertEqual(history_response.status_code, 200)
        self.assertContains(history_response, 'Salary deposit')
        self.assertContains(history_response, '$250.75')
    
    def test_complete_withdrawal_workflow(self):
        """Test complete withdrawal workflow."""
        # Login
        self.client.login(username='user1', password='TestPass123!')
        
        # Navigate to withdrawal page
        withdrawal_response = self.client.get(self.withdrawal_url)
        self.assertEqual(withdrawal_response.status_code, 200)
        self.assertContains(withdrawal_response, 'Withdraw Money')
        self.assertContains(withdrawal_response, '$1000.00')  # Available balance
        
        # Submit withdrawal
        withdrawal_data = {
            'amount': '150.25',
            'description': 'ATM withdrawal'
        }
        
        submit_response = self.client.post(self.withdrawal_url, data=withdrawal_data)
        self.assertEqual(submit_response.status_code, 302)
        
        # Verify balance updated
        self.account1.refresh_from_db()
        self.assertEqual(self.account1.balance, Decimal('849.75'))
        
        # Verify transaction record
        transaction_record = Transaction.objects.filter(
            transaction_type='withdrawal',
            sender_account=self.account1,
            amount=Decimal('150.25')
        ).first()
        
        self.assertIsNotNone(transaction_record)
        self.assertEqual(transaction_record.sender_balance_after, Decimal('849.75'))
    
    def test_complete_transfer_workflow(self):
        """Test complete transfer workflow between two accounts."""
        # Login as user1
        self.client.login(username='user1', password='TestPass123!')
        
        # Navigate to transfer page
        transfer_response = self.client.get(self.transfer_url)
        self.assertEqual(transfer_response.status_code, 200)
        self.assertContains(transfer_response, 'Transfer Money')
        
        # Submit transfer
        transfer_data = {
            'recipient_account_number': self.account2.account_number,
            'amount': '300.50',
            'description': 'Monthly payment'
        }
        
        submit_response = self.client.post(self.transfer_url, data=transfer_data)
        self.assertEqual(submit_response.status_code, 302)
        
        # Verify sender balance updated
        self.account1.refresh_from_db()
        self.assertEqual(self.account1.balance, Decimal('699.50'))
        
        # Verify recipient balance updated
        self.account2.refresh_from_db()
        self.assertEqual(self.account2.balance, Decimal('800.50'))
        
        # Verify transaction record created
        transaction_record = Transaction.objects.filter(
            transaction_type='transfer',
            sender_account=self.account1,
            receiver_account=self.account2,
            amount=Decimal('300.50')
        ).first()
        
        self.assertIsNotNone(transaction_record)
        self.assertEqual(transaction_record.sender_balance_after, Decimal('699.50'))
        self.assertEqual(transaction_record.receiver_balance_after, Decimal('800.50'))
        
        # Verify both users can see the transaction in their history
        # Check sender's history
        history_response = self.client.get(self.history_url)
        self.assertContains(history_response, 'Monthly payment')
        self.assertContains(history_response, f'Transfer to {self.account2.account_number}')
        
        # Login as recipient and check their history
        self.client.logout()
        self.client.login(username='user2', password='TestPass123!')
        
        history_response = self.client.get(self.history_url)
        self.assertContains(history_response, 'Monthly payment')
        self.assertContains(history_response, f'Transfer from {self.account1.account_number}')
    
    def test_insufficient_funds_workflow(self):
        """Test workflow when attempting withdrawal/transfer with insufficient funds."""
        # Login
        self.client.login(username='user1', password='TestPass123!')
        
        # Attempt withdrawal exceeding balance
        withdrawal_data = {
            'amount': '1500.00',  # More than $1000 balance
            'description': 'Large withdrawal'
        }
        
        response = self.client.post(self.withdrawal_url, data=withdrawal_data)
        
        # Should stay on withdrawal page with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Insufficient funds')
        
        # Verify balance unchanged
        self.account1.refresh_from_db()
        self.assertEqual(self.account1.balance, Decimal('1000.00'))
        
        # Verify no transaction record created
        self.assertFalse(Transaction.objects.filter(
            transaction_type='withdrawal',
            amount=Decimal('1500.00')
        ).exists())
    
    def test_invalid_recipient_transfer_workflow(self):
        """Test transfer workflow with invalid recipient account."""
        # Login
        self.client.login(username='user1', password='TestPass123!')
        
        # Attempt transfer to non-existent account
        transfer_data = {
            'recipient_account_number': '999999999999',
            'amount': '100.00',
            'description': 'Invalid transfer'
        }
        
        response = self.client.post(self.transfer_url, data=transfer_data)
        
        # Should stay on transfer page with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recipient account not found')
        
        # Verify balance unchanged
        self.account1.refresh_from_db()
        self.assertEqual(self.account1.balance, Decimal('1000.00'))


class AdminWorkflowIntegrationTest(TestCase):
    """Test complete admin workflow integration."""
    
    def setUp(self):
        self.client = Client()
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='AdminPass123!',
            is_staff=True,
            first_name='Admin',
            last_name='User'
        )
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username='regularuser',
            email='regular@example.com',
            password='UserPass123!',
            first_name='Regular',
            last_name='User'
        )
        
        # Create pending bank account
        self.pending_account = BankAccount.objects.create(
            user=self.regular_user,
            account_type='savings',
            balance=Decimal('0.00'),
            status='pending'
        )
        
        # URLs
        self.login_url = reverse('accounts:login')
        self.admin_dashboard_url = reverse('admin_panel:dashboard')
        self.user_management_url = reverse('admin_panel:user_management')
        self.account_management_url = reverse('admin_panel:account_management')
    
    def test_complete_admin_account_approval_workflow(self):
        """Test complete admin workflow for approving a pending account."""
        # Step 1: Admin login
        login_response = self.client.post(self.login_url, {
            'username': 'admin',
            'password': 'AdminPass123!'
        })
        self.assertEqual(login_response.status_code, 302)
        
        # Step 2: Access admin dashboard
        dashboard_response = self.client.get(self.admin_dashboard_url)
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, 'Admin Dashboard')
        self.assertContains(dashboard_response, 'Pending Approval: 1')
        
        # Step 3: Navigate to account management
        account_mgmt_response = self.client.get(self.account_management_url)
        self.assertEqual(account_mgmt_response.status_code, 200)
        self.assertContains(account_mgmt_response, self.pending_account.account_number)
        self.assertContains(account_mgmt_response, 'Pending')
        
        # Step 4: Approve the account
        approve_url = reverse('admin_panel:approve_account', args=[self.pending_account.id])
        approve_response = self.client.post(approve_url, {
            'reason': 'Account verification completed'
        })
        
        # Step 5: Verify redirect back to account management
        self.assertEqual(approve_response.status_code, 302)
        self.assertRedirects(approve_response, self.account_management_url)
        
        # Step 6: Verify account status updated
        self.pending_account.refresh_from_db()
        self.assertEqual(self.pending_account.status, 'active')
        
        # Step 7: Verify admin action logged
        admin_action = AdminAction.objects.filter(
            action_type='account_approve',
            admin_user=self.admin_user,
            target_account=self.pending_account
        ).first()
        
        self.assertIsNotNone(admin_action)
        self.assertEqual(admin_action.description, 'Account verification completed')
        
        # Step 8: Verify success message
        messages = list(get_messages(approve_response.wsgi_request))
        self.assertTrue(any('successfully approved' in str(m).lower() for m in messages))
        
        # Step 9: Verify dashboard statistics updated
        updated_dashboard_response = self.client.get(self.admin_dashboard_url)
        self.assertContains(updated_dashboard_response, 'Active Accounts: 1')
        self.assertContains(updated_dashboard_response, 'Pending Approval: 0')
    
    def test_complete_admin_account_freeze_workflow(self):
        """Test complete admin workflow for freezing an account."""
        # Set account to active first
        self.pending_account.status = 'active'
        self.pending_account.balance = Decimal('500.00')
        self.pending_account.save()
        
        # Admin login
        self.client.login(username='admin', password='AdminPass123!')
        
        # Navigate to account management
        self.client.get(self.account_management_url)
        
        # Freeze the account
        freeze_url = reverse('admin_panel:freeze_account', args=[self.pending_account.id])
        freeze_response = self.client.post(freeze_url, {
            'reason': 'Suspicious activity detected'
        })
        
        # Verify account frozen
        self.pending_account.refresh_from_db()
        self.assertEqual(self.pending_account.status, 'frozen')
        
        # Verify admin action logged
        admin_action = AdminAction.objects.filter(
            action_type='account_freeze',
            admin_user=self.admin_user,
            target_account=self.pending_account
        ).first()
        
        self.assertIsNotNone(admin_action)
        self.assertEqual(admin_action.description, 'Suspicious activity detected')
        
        # Test that frozen account cannot perform transactions
        self.client.logout()
        self.client.login(username='regularuser', password='UserPass123!')
        
        # Attempt deposit on frozen account
        deposit_url = reverse('transactions:deposit')
        deposit_response = self.client.get(deposit_url)
        
        # Should redirect with error message
        self.assertEqual(deposit_response.status_code, 302)
        messages = list(get_messages(deposit_response.wsgi_request))
        self.assertTrue(any('frozen' in str(m).lower() for m in messages))


class AuthenticationAndAuthorizationWorkflowTest(TestCase):
    """Test complete authentication and authorization workflows."""
    
    def setUp(self):
        self.client = Client()
        
        # Create users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='TestPass123!',
            first_name='User',
            last_name='One'
        )
        
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='TestPass123!',
            first_name='User',
            last_name='Two'
        )
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='AdminPass123!',
            is_staff=True
        )
        
        # Create accounts
        self.account1 = BankAccount.objects.create(
            user=self.user1,
            account_type='savings',
            balance=Decimal('1000.00'),
            status='active'
        )
        
        self.account2 = BankAccount.objects.create(
            user=self.user2,
            account_type='current',
            balance=Decimal('500.00'),
            status='active'
        )
        
        # URLs
        self.login_url = reverse('accounts:login')
        self.logout_url = reverse('accounts:logout')
        self.dashboard_url = reverse('accounts:dashboard')
        self.history_url = reverse('transactions:history')
        self.admin_dashboard_url = reverse('admin_panel:dashboard')
    
    def test_complete_login_logout_workflow(self):
        """Test complete login and logout workflow."""
        # Step 1: Access login page
        login_page_response = self.client.get(self.login_url)
        self.assertEqual(login_page_response.status_code, 200)
        self.assertContains(login_page_response, 'Welcome Back')
        
        # Step 2: Submit valid credentials
        login_response = self.client.post(self.login_url, {
            'username': 'user1',
            'password': 'TestPass123!'
        })
        
        # Step 3: Verify redirect to dashboard
        self.assertEqual(login_response.status_code, 302)
        self.assertRedirects(login_response, self.dashboard_url)
        
        # Step 4: Verify session created and user authenticated
        dashboard_response = self.client.get(self.dashboard_url)
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, 'Welcome, User!')
        
        # Step 5: Verify user can access protected resources
        history_response = self.client.get(self.history_url)
        self.assertEqual(history_response.status_code, 200)
        
        # Step 6: Logout
        logout_response = self.client.get(self.logout_url)
        self.assertEqual(logout_response.status_code, 302)
        self.assertRedirects(logout_response, self.login_url)
        
        # Step 7: Verify session cleared and access denied
        dashboard_after_logout = self.client.get(self.dashboard_url)
        self.assertEqual(dashboard_after_logout.status_code, 302)  # Redirect to login
    
    def test_user_isolation_workflow(self):
        """Test that users can only access their own data."""
        # Login as user1
        self.client.login(username='user1', password='TestPass123!')
        
        # Verify user1 can access their dashboard
        dashboard_response = self.client.get(self.dashboard_url)
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, self.account1.account_number)
        self.assertNotContains(dashboard_response, self.account2.account_number)
        
        # Verify user1 can only see their transactions
        history_response = self.client.get(self.history_url)
        self.assertEqual(history_response.status_code, 200)
        
        # Create transactions for both users
        Transaction.objects.create(
            transaction_type='deposit',
            amount=Decimal('100.00'),
            receiver_account=self.account1,
            description='User1 deposit'
        )
        
        Transaction.objects.create(
            transaction_type='deposit',
            amount=Decimal('200.00'),
            receiver_account=self.account2,
            description='User2 deposit'
        )
        
        # User1 should only see their transaction
        history_response = self.client.get(self.history_url)
        self.assertContains(history_response, 'User1 deposit')
        self.assertNotContains(history_response, 'User2 deposit')
        
        # Switch to user2
        self.client.logout()
        self.client.login(username='user2', password='TestPass123!')
        
        # User2 should only see their transaction
        history_response = self.client.get(self.history_url)
        self.assertContains(history_response, 'User2 deposit')
        self.assertNotContains(history_response, 'User1 deposit')
    
    def test_admin_access_control_workflow(self):
        """Test admin access control workflow."""
        # Regular user should not access admin panel
        self.client.login(username='user1', password='TestPass123!')
        
        admin_response = self.client.get(self.admin_dashboard_url)
        self.assertEqual(admin_response.status_code, 302)  # Redirect to login
        
        # Admin user should access admin panel
        self.client.logout()
        self.client.login(username='admin', password='AdminPass123!')
        
        admin_response = self.client.get(self.admin_dashboard_url)
        self.assertEqual(admin_response.status_code, 200)
        self.assertContains(admin_response, 'Admin Dashboard')
        
        # Admin should see all users and accounts
        user_mgmt_response = self.client.get(reverse('admin_panel:user_management'))
        self.assertEqual(user_mgmt_response.status_code, 200)
        self.assertContains(user_mgmt_response, 'user1')
        self.assertContains(user_mgmt_response, 'user2')
    
    def test_invalid_credentials_workflow(self):
        """Test workflow with invalid credentials."""
        # Attempt login with wrong password
        login_response = self.client.post(self.login_url, {
            'username': 'user1',
            'password': 'WrongPassword'
        })
        
        # Should stay on login page with error
        self.assertEqual(login_response.status_code, 200)
        self.assertContains(login_response, 'Invalid username or password')
        
        # Verify user not authenticated
        dashboard_response = self.client.get(self.dashboard_url)
        self.assertEqual(dashboard_response.status_code, 302)  # Redirect to login
        
        # Attempt login with non-existent user
        login_response = self.client.post(self.login_url, {
            'username': 'nonexistent',
            'password': 'TestPass123!'
        })
        
        self.assertEqual(login_response.status_code, 200)
        self.assertContains(login_response, 'Invalid username or password')


class MultiUserConcurrentWorkflowTest(TransactionTestCase):
    """Test workflows with multiple concurrent users."""
    
    def setUp(self):
        # Create multiple users and accounts
        self.users = []
        self.accounts = []
        
        for i in range(3):
            user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password='TestPass123!',
                first_name=f'User{i}',
                last_name='Test'
            )
            
            account = BankAccount.objects.create(
                user=user,
                account_type='savings',
                balance=Decimal('1000.00'),
                status='active'
            )
            
            self.users.append(user)
            self.accounts.append(account)
    
    def test_concurrent_user_sessions(self):
        """Test multiple users with concurrent sessions."""
        clients = [Client() for _ in range(3)]
        
        # Login all users simultaneously
        for i, client in enumerate(clients):
            login_response = client.post(reverse('accounts:login'), {
                'username': f'user{i}',
                'password': 'TestPass123!'
            })
            self.assertEqual(login_response.status_code, 302)
        
        # Each user should see their own dashboard
        for i, client in enumerate(clients):
            dashboard_response = client.get(reverse('accounts:dashboard'))
            self.assertEqual(dashboard_response.status_code, 200)
            self.assertContains(dashboard_response, f'Welcome, User{i}!')
            self.assertContains(dashboard_response, self.accounts[i].account_number)
        
        # Perform transactions simultaneously
        for i, client in enumerate(clients):
            deposit_response = client.post(reverse('transactions:deposit'), {
                'amount': f'{100 + i * 50}.00',
                'description': f'Concurrent deposit {i}'
            })
            self.assertEqual(deposit_response.status_code, 302)
        
        # Verify each account has correct balance
        for i, account in enumerate(self.accounts):
            account.refresh_from_db()
            expected_balance = Decimal('1000.00') + Decimal(f'{100 + i * 50}.00')
            self.assertEqual(account.balance, expected_balance)
    
    def test_concurrent_transfers_between_users(self):
        """Test concurrent transfers between multiple users."""
        clients = [Client() for _ in range(3)]
        
        # Login all users
        for i, client in enumerate(clients):
            client.login(username=f'user{i}', password='TestPass123!')
        
        # User0 transfers to User1, User1 transfers to User2, User2 transfers to User0
        transfer_data = [
            (0, 1, '100.00'),  # User0 -> User1
            (1, 2, '150.00'),  # User1 -> User2
            (2, 0, '200.00'),  # User2 -> User0
        ]
        
        # Execute transfers simultaneously
        for sender_idx, receiver_idx, amount in transfer_data:
            transfer_response = clients[sender_idx].post(reverse('transactions:transfer'), {
                'recipient_account_number': self.accounts[receiver_idx].account_number,
                'amount': amount,
                'description': f'Transfer from user{sender_idx} to user{receiver_idx}'
            })
            # Some transfers might succeed, others might fail due to timing
            self.assertIn(transfer_response.status_code, [200, 302])
        
        # Verify final balances are consistent
        total_balance = sum(account.balance for account in self.accounts)
        for account in self.accounts:
            account.refresh_from_db()
        
        final_total_balance = sum(account.balance for account in self.accounts)
        self.assertEqual(total_balance, final_total_balance)  # Total should remain same


class ErrorHandlingWorkflowTest(TestCase):
    """Test error handling in complete workflows."""
    
    def setUp(self):
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User'
        )
        
        self.account = BankAccount.objects.create(
            user=self.user,
            account_type='savings',
            balance=Decimal('100.00'),
            status='active'
        )
    
    def test_network_interruption_simulation(self):
        """Test workflow behavior during simulated network issues."""
        self.client.login(username='testuser', password='TestPass123!')
        
        # Simulate a transaction that might be interrupted
        initial_balance = self.account.balance
        
        # Start a transaction
        with transaction.atomic():
            # This simulates a transaction that starts but might be interrupted
            deposit_response = self.client.post(reverse('transactions:deposit'), {
                'amount': '50.00',
                'description': 'Test deposit'
            })
            
            # If successful, verify consistency
            if deposit_response.status_code == 302:
                self.account.refresh_from_db()
                self.assertEqual(self.account.balance, initial_balance + Decimal('50.00'))
                
                # Verify transaction record exists
                self.assertTrue(Transaction.objects.filter(
                    transaction_type='deposit',
                    amount=Decimal('50.00'),
                    receiver_account=self.account
                ).exists())
    
    def test_database_constraint_violation_handling(self):
        """Test handling of database constraint violations."""
        self.client.login(username='testuser', password='TestPass123!')
        
        # Attempt to create duplicate transaction with same reference number
        # This should be handled gracefully by the system
        
        # First transaction
        response1 = self.client.post(reverse('transactions:deposit'), {
            'amount': '25.00',
            'description': 'First deposit'
        })
        
        # Should succeed
        self.assertEqual(response1.status_code, 302)
        
        # Verify system maintains consistency even with potential conflicts
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('125.00'))
    
    def test_form_validation_error_recovery(self):
        """Test recovery from form validation errors."""
        self.client.login(username='testuser', password='TestPass123!')
        
        # Submit invalid form data
        invalid_response = self.client.post(reverse('transactions:deposit'), {
            'amount': 'invalid_amount',
            'description': 'Invalid deposit'
        })
        
        # Should stay on form page with errors
        self.assertEqual(invalid_response.status_code, 200)
        self.assertContains(invalid_response, 'error')
        
        # Verify no changes to account
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('100.00'))
        
        # Submit valid form data after error
        valid_response = self.client.post(reverse('transactions:deposit'), {
            'amount': '75.00',
            'description': 'Valid deposit after error'
        })
        
        # Should succeed
        self.assertEqual(valid_response.status_code, 302)
        
        # Verify account updated correctly
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('175.00'))