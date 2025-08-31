"""
Test fixtures for consistent testing across the banking platform.
Provides reusable test data and setup utilities.
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from accounts.models import BankAccount
from transactions.models import Transaction
from admin_panel.models import AdminAction

User = get_user_model()


class TestDataFixtures:
    """Centralized test data fixtures for consistent testing."""
    
    @staticmethod
    def create_test_users():
        """Create a set of test users with different roles."""
        users = {}
        
        # Regular users
        users['user1'] = User.objects.create_user(
            username='testuser1',
            email='user1@example.com',
            password='TestPass123!',
            first_name='Alice',
            last_name='Johnson'
        )
        
        users['user2'] = User.objects.create_user(
            username='testuser2',
            email='user2@example.com',
            password='TestPass123!',
            first_name='Bob',
            last_name='Smith'
        )
        
        users['user3'] = User.objects.create_user(
            username='testuser3',
            email='user3@example.com',
            password='TestPass123!',
            first_name='Charlie',
            last_name='Brown'
        )
        
        # Inactive user
        users['inactive_user'] = User.objects.create_user(
            username='inactiveuser',
            email='inactive@example.com',
            password='TestPass123!',
            first_name='Inactive',
            last_name='User',
            is_active=False
        )
        
        # Staff user
        users['staff'] = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='StaffPass123!',
            first_name='Staff',
            last_name='Member',
            is_staff=True
        )
        
        # Admin user
        users['admin'] = User.objects.create_superuser(
            username='adminuser',
            email='admin@example.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User'
        )
        
        return users
    
    @staticmethod
    def create_test_bank_accounts(users):
        """Create test bank accounts for the provided users."""
        accounts = {}
        
        # Active accounts with different balances
        accounts['user1_savings'] = BankAccount.objects.create(
            user=users['user1'],
            account_type='savings',
            balance=Decimal('1000.00'),
            status='active'
        )
        
        accounts['user1_current'] = BankAccount.objects.create(
            user=users['user1'],
            account_type='current',
            balance=Decimal('500.00'),
            status='active'
        )
        
        accounts['user2_savings'] = BankAccount.objects.create(
            user=users['user2'],
            account_type='savings',
            balance=Decimal('750.00'),
            status='active'
        )
        
        accounts['user3_current'] = BankAccount.objects.create(
            user=users['user3'],
            account_type='current',
            balance=Decimal('250.00'),
            status='active'
        )
        
        # Pending account
        accounts['user2_pending'] = BankAccount.objects.create(
            user=users['user2'],
            account_type='savings',
            balance=Decimal('0.00'),
            status='pending'
        )
        
        # Frozen account
        accounts['user3_frozen'] = BankAccount.objects.create(
            user=users['user3'],
            account_type='savings',
            balance=Decimal('300.00'),
            status='frozen'
        )
        
        # Closed account
        accounts['user1_closed'] = BankAccount.objects.create(
            user=users['user1'],
            account_type='current',
            balance=Decimal('0.00'),
            status='closed'
        )
        
        # High balance account for testing limits
        accounts['high_balance'] = BankAccount.objects.create(
            user=users['user1'],
            account_type='savings',
            balance=Decimal('50000.00'),
            status='active'
        )
        
        # Low balance account for insufficient funds testing
        accounts['low_balance'] = BankAccount.objects.create(
            user=users['user2'],
            account_type='current',
            balance=Decimal('10.00'),
            status='active'
        )
        
        return accounts
    
    @staticmethod
    def create_test_transactions(accounts):
        """Create test transactions for the provided accounts."""
        transactions = []
        
        # Deposit transactions
        transactions.append(Transaction.objects.create(
            transaction_type='deposit',
            amount=Decimal('500.00'),
            receiver_account=accounts['user1_savings'],
            description='Initial deposit',
            receiver_balance_after=Decimal('1500.00')
        ))
        
        transactions.append(Transaction.objects.create(
            transaction_type='deposit',
            amount=Decimal('250.00'),
            receiver_account=accounts['user2_savings'],
            description='Salary deposit',
            receiver_balance_after=Decimal('1000.00')
        ))
        
        # Withdrawal transactions
        transactions.append(Transaction.objects.create(
            transaction_type='withdrawal',
            amount=Decimal('100.00'),
            sender_account=accounts['user1_savings'],
            description='ATM withdrawal',
            sender_balance_after=Decimal('1400.00')
        ))
        
        transactions.append(Transaction.objects.create(
            transaction_type='withdrawal',
            amount=Decimal('50.00'),
            sender_account=accounts['user2_savings'],
            description='Cash withdrawal',
            sender_balance_after=Decimal('950.00')
        ))
        
        # Transfer transactions
        transactions.append(Transaction.objects.create(
            transaction_type='transfer',
            amount=Decimal('200.00'),
            sender_account=accounts['user1_savings'],
            receiver_account=accounts['user2_savings'],
            description='Monthly payment',
            sender_balance_after=Decimal('1200.00'),
            receiver_balance_after=Decimal('1150.00')
        ))
        
        transactions.append(Transaction.objects.create(
            transaction_type='transfer',
            amount=Decimal('75.00'),
            sender_account=accounts['user2_savings'],
            receiver_account=accounts['user3_current'],
            description='Shared expense',
            sender_balance_after=Decimal('1075.00'),
            receiver_balance_after=Decimal('325.00')
        ))
        
        # High-value transaction for monitoring
        transactions.append(Transaction.objects.create(
            transaction_type='transfer',
            amount=Decimal('15000.00'),
            sender_account=accounts['high_balance'],
            receiver_account=accounts['user1_savings'],
            description='Large transfer',
            sender_balance_after=Decimal('35000.00'),
            receiver_balance_after=Decimal('16200.00')
        ))
        
        return transactions
    
    @staticmethod
    def create_test_admin_actions(users, accounts):
        """Create test admin actions for the provided users and accounts."""
        admin_actions = []
        
        # Account approval
        admin_actions.append(AdminAction.objects.create(
            action_type='account_approve',
            admin_user=users['admin'],
            target_user=users['user1'],
            target_account=accounts['user1_savings'],
            description='Account verification completed'
        ))
        
        # Account freeze
        admin_actions.append(AdminAction.objects.create(
            action_type='account_freeze',
            admin_user=users['staff'],
            target_user=users['user3'],
            target_account=accounts['user3_frozen'],
            description='Suspicious activity detected'
        ))
        
        # Account unfreeze
        admin_actions.append(AdminAction.objects.create(
            action_type='account_unfreeze',
            admin_user=users['admin'],
            target_user=users['user3'],
            target_account=accounts['user3_frozen'],
            description='Investigation completed, account cleared'
        ))
        
        # Account closure
        admin_actions.append(AdminAction.objects.create(
            action_type='account_close',
            admin_user=users['staff'],
            target_user=users['user1'],
            target_account=accounts['user1_closed'],
            description='Account closure requested by customer'
        ))
        
        # User deactivation
        admin_actions.append(AdminAction.objects.create(
            action_type='user_deactivate',
            admin_user=users['admin'],
            target_user=users['inactive_user'],
            description='Account suspended due to policy violation'
        ))
        
        # Transaction flag
        admin_actions.append(AdminAction.objects.create(
            action_type='transaction_flag',
            admin_user=users['staff'],
            target_user=users['user1'],
            description='Large transaction flagged for review'
        ))
        
        return admin_actions
    
    @staticmethod
    def create_complete_test_dataset():
        """Create a complete test dataset with all related objects."""
        # Create users
        users = TestDataFixtures.create_test_users()
        
        # Create accounts
        accounts = TestDataFixtures.create_test_bank_accounts(users)
        
        # Create transactions
        transactions = TestDataFixtures.create_test_transactions(accounts)
        
        # Create admin actions
        admin_actions = TestDataFixtures.create_test_admin_actions(users, accounts)
        
        return {
            'users': users,
            'accounts': accounts,
            'transactions': transactions,
            'admin_actions': admin_actions
        }
    
    @staticmethod
    def get_test_form_data():
        """Get test form data for various forms."""
        return {
            'registration': {
                'valid': {
                    'username': 'newuser123',
                    'first_name': 'New',
                    'last_name': 'User',
                    'email': 'newuser@example.com',
                    'password1': 'SecurePass123!',
                    'password2': 'SecurePass123!',
                    'account_type': 'savings'
                },
                'invalid_password': {
                    'username': 'newuser123',
                    'first_name': 'New',
                    'last_name': 'User',
                    'email': 'newuser@example.com',
                    'password1': 'weak',
                    'password2': 'weak',
                    'account_type': 'savings'
                },
                'password_mismatch': {
                    'username': 'newuser123',
                    'first_name': 'New',
                    'last_name': 'User',
                    'email': 'newuser@example.com',
                    'password1': 'SecurePass123!',
                    'password2': 'DifferentPass123!',
                    'account_type': 'savings'
                }
            },
            'login': {
                'valid': {
                    'username': 'testuser1',
                    'password': 'TestPass123!'
                },
                'invalid': {
                    'username': 'testuser1',
                    'password': 'WrongPassword'
                }
            },
            'deposit': {
                'valid': {
                    'amount': '100.50',
                    'description': 'Test deposit'
                },
                'invalid_amount': {
                    'amount': '-50.00',
                    'description': 'Invalid deposit'
                },
                'large_amount': {
                    'amount': '200000.00',
                    'description': 'Large deposit'
                }
            },
            'withdrawal': {
                'valid': {
                    'amount': '75.25',
                    'description': 'ATM withdrawal'
                },
                'insufficient_funds': {
                    'amount': '2000.00',
                    'description': 'Large withdrawal'
                },
                'invalid_amount': {
                    'amount': '0.00',
                    'description': 'Zero withdrawal'
                }
            },
            'transfer': {
                'valid': {
                    'amount': '150.00',
                    'description': 'Monthly payment'
                },
                'insufficient_funds': {
                    'amount': '5000.00',
                    'description': 'Large transfer'
                },
                'invalid_recipient': {
                    'recipient_account_number': '999999999999',
                    'amount': '100.00',
                    'description': 'Invalid transfer'
                }
            }
        }
    
    @staticmethod
    def get_test_credentials():
        """Get test user credentials."""
        return {
            'user1': {'username': 'testuser1', 'password': 'TestPass123!'},
            'user2': {'username': 'testuser2', 'password': 'TestPass123!'},
            'user3': {'username': 'testuser3', 'password': 'TestPass123!'},
            'inactive_user': {'username': 'inactiveuser', 'password': 'TestPass123!'},
            'staff': {'username': 'staffuser', 'password': 'StaffPass123!'},
            'admin': {'username': 'adminuser', 'password': 'AdminPass123!'}
        }
    
    @staticmethod
    def cleanup_test_data():
        """Clean up all test data."""
        # Delete in reverse order of dependencies
        AdminAction.objects.all().delete()
        Transaction.objects.all().delete()
        BankAccount.objects.all().delete()
        User.objects.all().delete()


class TestScenarios:
    """Pre-defined test scenarios for common testing patterns."""
    
    @staticmethod
    def successful_transaction_scenario():
        """Scenario for testing successful transactions."""
        users = TestDataFixtures.create_test_users()
        accounts = TestDataFixtures.create_test_bank_accounts(users)
        
        return {
            'sender': users['user1'],
            'sender_account': accounts['user1_savings'],
            'recipient': users['user2'],
            'recipient_account': accounts['user2_savings'],
            'amount': Decimal('100.00'),
            'description': 'Test transaction'
        }
    
    @staticmethod
    def insufficient_funds_scenario():
        """Scenario for testing insufficient funds handling."""
        users = TestDataFixtures.create_test_users()
        accounts = TestDataFixtures.create_test_bank_accounts(users)
        
        return {
            'user': users['user2'],
            'account': accounts['low_balance'],  # Only $10.00 balance
            'attempted_amount': Decimal('50.00'),
            'description': 'Insufficient funds test'
        }
    
    @staticmethod
    def admin_approval_scenario():
        """Scenario for testing admin approval workflow."""
        users = TestDataFixtures.create_test_users()
        accounts = TestDataFixtures.create_test_bank_accounts(users)
        
        return {
            'admin': users['admin'],
            'user': users['user2'],
            'pending_account': accounts['user2_pending'],
            'approval_reason': 'Account verification completed'
        }
    
    @staticmethod
    def security_violation_scenario():
        """Scenario for testing security violation handling."""
        users = TestDataFixtures.create_test_users()
        accounts = TestDataFixtures.create_test_bank_accounts(users)
        
        return {
            'admin': users['staff'],
            'user': users['user3'],
            'account': accounts['user3_current'],
            'violation_reason': 'Suspicious activity detected'
        }
    
    @staticmethod
    def concurrent_transaction_scenario():
        """Scenario for testing concurrent transactions."""
        users = TestDataFixtures.create_test_users()
        accounts = TestDataFixtures.create_test_bank_accounts(users)
        
        return {
            'users': [users['user1'], users['user2'], users['user3']],
            'accounts': [
                accounts['user1_savings'],
                accounts['user2_savings'],
                accounts['user3_current']
            ],
            'transaction_amounts': [
                Decimal('50.00'),
                Decimal('75.00'),
                Decimal('100.00')
            ]
        }


class TestAssertions:
    """Custom assertion helpers for banking platform tests."""
    
    @staticmethod
    def assert_balance_equals(test_case, account, expected_balance):
        """Assert that account balance equals expected value."""
        account.refresh_from_db()
        test_case.assertEqual(
            account.balance,
            expected_balance,
            f"Account {account.account_number} balance {account.balance} != {expected_balance}"
        )
    
    @staticmethod
    def assert_transaction_exists(test_case, transaction_type, amount, sender=None, receiver=None):
        """Assert that a transaction with specified parameters exists."""
        filters = {
            'transaction_type': transaction_type,
            'amount': amount
        }
        
        if sender:
            filters['sender_account'] = sender
        if receiver:
            filters['receiver_account'] = receiver
        
        test_case.assertTrue(
            Transaction.objects.filter(**filters).exists(),
            f"Transaction {transaction_type} of {amount} not found"
        )
    
    @staticmethod
    def assert_admin_action_logged(test_case, action_type, admin_user, target_account=None, target_user=None):
        """Assert that an admin action was logged."""
        filters = {
            'action_type': action_type,
            'admin_user': admin_user
        }
        
        if target_account:
            filters['target_account'] = target_account
        if target_user:
            filters['target_user'] = target_user
        
        test_case.assertTrue(
            AdminAction.objects.filter(**filters).exists(),
            f"Admin action {action_type} by {admin_user.username} not found"
        )
    
    @staticmethod
    def assert_account_status(test_case, account, expected_status):
        """Assert that account has expected status."""
        account.refresh_from_db()
        test_case.assertEqual(
            account.status,
            expected_status,
            f"Account {account.account_number} status {account.status} != {expected_status}"
        )
    
    @staticmethod
    def assert_user_can_login(test_case, client, username, password):
        """Assert that user can successfully login."""
        response = client.post(reverse('accounts:login'), {
            'username': username,
            'password': password
        })
        test_case.assertEqual(response.status_code, 302)
        test_case.assertRedirects(response, reverse('accounts:dashboard'))
    
    @staticmethod
    def assert_user_cannot_access(test_case, client, url):
        """Assert that user cannot access a protected URL."""
        response = client.get(url)
        test_case.assertEqual(response.status_code, 302)
        test_case.assertIn('login', response.url)
    
    @staticmethod
    def assert_message_contains(test_case, response, message_text):
        """Assert that response contains a message with specified text."""
        messages = list(get_messages(response.wsgi_request))
        message_found = any(message_text.lower() in str(m).lower() for m in messages)
        test_case.assertTrue(
            message_found,
            f"Message containing '{message_text}' not found in {[str(m) for m in messages]}"
        )


# Import reverse for use in assertions
from django.urls import reverse
from django.contrib.messages import get_messages