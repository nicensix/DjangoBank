from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from accounts.models import BankAccount
from .models import Transaction

User = get_user_model()


class TransactionModelTest(TestCase):
    """Test cases for the Transaction model."""
    
    def setUp(self):
        """Set up test data."""
        # Create test users
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
        
        # Create test bank accounts
        self.account1 = BankAccount.objects.create(
            user=self.user1,
            account_type='savings',
            balance=1000.00,
            status='active'
        )
        self.account2 = BankAccount.objects.create(
            user=self.user2,
            account_type='current',
            balance=500.00,
            status='active'
        )
    
    def test_create_deposit_transaction(self):
        """Test creating a deposit transaction."""
        transaction = Transaction.objects.create(
            transaction_type='deposit',
            amount=100.00,
            receiver_account=self.account1,
            description='Test deposit'
        )
        
        self.assertEqual(transaction.transaction_type, 'deposit')
        self.assertEqual(transaction.amount, Decimal('100.00'))
        self.assertEqual(transaction.receiver_account, self.account1)
        self.assertIsNone(transaction.sender_account)
        self.assertEqual(transaction.description, 'Test deposit')
        self.assertIsNotNone(transaction.reference_number)
        self.assertTrue(transaction.reference_number.startswith('TXN'))
    
    def test_create_withdrawal_transaction(self):
        """Test creating a withdrawal transaction."""
        transaction = Transaction.objects.create(
            transaction_type='withdrawal',
            amount=50.00,
            sender_account=self.account1,
            description='Test withdrawal'
        )
        
        self.assertEqual(transaction.transaction_type, 'withdrawal')
        self.assertEqual(transaction.amount, Decimal('50.00'))
        self.assertEqual(transaction.sender_account, self.account1)
        self.assertIsNone(transaction.receiver_account)
        self.assertEqual(transaction.description, 'Test withdrawal')
    
    def test_create_transfer_transaction(self):
        """Test creating a transfer transaction."""
        transaction = Transaction.objects.create(
            transaction_type='transfer',
            amount=200.00,
            sender_account=self.account1,
            receiver_account=self.account2,
            description='Test transfer'
        )
        
        self.assertEqual(transaction.transaction_type, 'transfer')
        self.assertEqual(transaction.amount, Decimal('200.00'))
        self.assertEqual(transaction.sender_account, self.account1)
        self.assertEqual(transaction.receiver_account, self.account2)
        self.assertEqual(transaction.description, 'Test transfer')
    
    def test_reference_number_generation(self):
        """Test automatic reference number generation."""
        transaction = Transaction.objects.create(
            transaction_type='deposit',
            amount=100.00,
            receiver_account=self.account1
        )
        
        self.assertIsNotNone(transaction.reference_number)
        self.assertTrue(transaction.reference_number.startswith('TXN'))
        self.assertEqual(len(transaction.reference_number), 21)  # TXN + 14 digits + 4 chars
    
    def test_reference_number_uniqueness(self):
        """Test that reference numbers are unique."""
        transaction1 = Transaction.objects.create(
            transaction_type='deposit',
            amount=100.00,
            receiver_account=self.account1
        )
        transaction2 = Transaction.objects.create(
            transaction_type='deposit',
            amount=200.00,
            receiver_account=self.account2
        )
        
        self.assertNotEqual(transaction1.reference_number, transaction2.reference_number)
    
    def test_custom_reference_number(self):
        """Test creating transaction with custom reference number."""
        custom_ref = 'CUSTOM123456789'
        transaction = Transaction.objects.create(
            transaction_type='deposit',
            amount=100.00,
            receiver_account=self.account1,
            reference_number=custom_ref
        )
        
        self.assertEqual(transaction.reference_number, custom_ref)
    
    def test_negative_amount_validation(self):
        """Test that negative amount raises validation error."""
        transaction = Transaction(
            transaction_type='deposit',
            amount=-100.00,
            receiver_account=self.account1
        )
        
        with self.assertRaises(ValidationError) as context:
            transaction.full_clean()
        
        self.assertIn('amount', context.exception.message_dict)
        self.assertIn('must be positive', str(context.exception.message_dict['amount']))
    
    def test_zero_amount_validation(self):
        """Test that zero amount raises validation error."""
        transaction = Transaction(
            transaction_type='deposit',
            amount=0.00,
            receiver_account=self.account1
        )
        
        with self.assertRaises(ValidationError) as context:
            transaction.full_clean()
        
        self.assertIn('amount', context.exception.message_dict)
    
    def test_deposit_validation(self):
        """Test deposit transaction validation."""
        # Valid deposit
        transaction = Transaction(
            transaction_type='deposit',
            amount=100.00,
            receiver_account=self.account1,
            reference_number='TEST123456789'
        )
        transaction.full_clean()  # Should not raise
        
        # Invalid deposit - no receiver account
        transaction = Transaction(
            transaction_type='deposit',
            amount=100.00
        )
        with self.assertRaises(ValidationError) as context:
            transaction.full_clean()
        self.assertIn('receiver_account', context.exception.message_dict)
        
        # Invalid deposit - has sender account
        transaction = Transaction(
            transaction_type='deposit',
            amount=100.00,
            receiver_account=self.account1,
            sender_account=self.account2
        )
        with self.assertRaises(ValidationError) as context:
            transaction.full_clean()
        self.assertIn('sender_account', context.exception.message_dict)
    
    def test_withdrawal_validation(self):
        """Test withdrawal transaction validation."""
        # Valid withdrawal
        transaction = Transaction(
            transaction_type='withdrawal',
            amount=100.00,
            sender_account=self.account1,
            reference_number='TEST123456789'
        )
        transaction.full_clean()  # Should not raise
        
        # Invalid withdrawal - no sender account
        transaction = Transaction(
            transaction_type='withdrawal',
            amount=100.00
        )
        with self.assertRaises(ValidationError) as context:
            transaction.full_clean()
        self.assertIn('sender_account', context.exception.message_dict)
        
        # Invalid withdrawal - has receiver account
        transaction = Transaction(
            transaction_type='withdrawal',
            amount=100.00,
            sender_account=self.account1,
            receiver_account=self.account2
        )
        with self.assertRaises(ValidationError) as context:
            transaction.full_clean()
        self.assertIn('receiver_account', context.exception.message_dict)
    
    def test_transfer_validation(self):
        """Test transfer transaction validation."""
        # Valid transfer
        transaction = Transaction(
            transaction_type='transfer',
            amount=100.00,
            sender_account=self.account1,
            receiver_account=self.account2,
            reference_number='TEST123456789'
        )
        transaction.full_clean()  # Should not raise
        
        # Invalid transfer - no sender account
        transaction = Transaction(
            transaction_type='transfer',
            amount=100.00,
            receiver_account=self.account2
        )
        with self.assertRaises(ValidationError) as context:
            transaction.full_clean()
        self.assertIn('sender_account', context.exception.message_dict)
        
        # Invalid transfer - no receiver account
        transaction = Transaction(
            transaction_type='transfer',
            amount=100.00,
            sender_account=self.account1
        )
        with self.assertRaises(ValidationError) as context:
            transaction.full_clean()
        self.assertIn('receiver_account', context.exception.message_dict)
        
        # Invalid transfer - same account
        transaction = Transaction(
            transaction_type='transfer',
            amount=100.00,
            sender_account=self.account1,
            receiver_account=self.account1
        )
        with self.assertRaises(ValidationError) as context:
            transaction.full_clean()
        self.assertIn('receiver_account', context.exception.message_dict)
    
    def test_transaction_type_methods(self):
        """Test transaction type checking methods."""
        deposit = Transaction.objects.create(
            transaction_type='deposit',
            amount=100.00,
            receiver_account=self.account1
        )
        withdrawal = Transaction.objects.create(
            transaction_type='withdrawal',
            amount=50.00,
            sender_account=self.account1
        )
        transfer = Transaction.objects.create(
            transaction_type='transfer',
            amount=200.00,
            sender_account=self.account1,
            receiver_account=self.account2
        )
        
        # Test deposit
        self.assertTrue(deposit.is_deposit())
        self.assertFalse(deposit.is_withdrawal())
        self.assertFalse(deposit.is_transfer())
        
        # Test withdrawal
        self.assertFalse(withdrawal.is_deposit())
        self.assertTrue(withdrawal.is_withdrawal())
        self.assertFalse(withdrawal.is_transfer())
        
        # Test transfer
        self.assertFalse(transfer.is_deposit())
        self.assertFalse(transfer.is_withdrawal())
        self.assertTrue(transfer.is_transfer())
    
    def test_get_account_methods(self):
        """Test get_account and get_other_account methods."""
        deposit = Transaction.objects.create(
            transaction_type='deposit',
            amount=100.00,
            receiver_account=self.account1
        )
        withdrawal = Transaction.objects.create(
            transaction_type='withdrawal',
            amount=50.00,
            sender_account=self.account1
        )
        transfer = Transaction.objects.create(
            transaction_type='transfer',
            amount=200.00,
            sender_account=self.account1,
            receiver_account=self.account2
        )
        
        # Test deposit
        self.assertEqual(deposit.get_account(), self.account1)
        self.assertIsNone(deposit.get_other_account())
        
        # Test withdrawal
        self.assertEqual(withdrawal.get_account(), self.account1)
        self.assertIsNone(withdrawal.get_other_account())
        
        # Test transfer
        self.assertEqual(transfer.get_account(), self.account1)
        self.assertEqual(transfer.get_other_account(), self.account2)
    
    def test_get_display_amount_for_account(self):
        """Test get_display_amount_for_account method."""
        deposit = Transaction.objects.create(
            transaction_type='deposit',
            amount=100.00,
            receiver_account=self.account1
        )
        withdrawal = Transaction.objects.create(
            transaction_type='withdrawal',
            amount=50.00,
            sender_account=self.account1
        )
        transfer = Transaction.objects.create(
            transaction_type='transfer',
            amount=200.00,
            sender_account=self.account1,
            receiver_account=self.account2
        )
        
        # Test deposit
        self.assertEqual(deposit.get_display_amount_for_account(self.account1), Decimal('100.00'))
        self.assertEqual(deposit.get_display_amount_for_account(self.account2), Decimal('0.00'))
        
        # Test withdrawal
        self.assertEqual(withdrawal.get_display_amount_for_account(self.account1), Decimal('-50.00'))
        self.assertEqual(withdrawal.get_display_amount_for_account(self.account2), Decimal('0.00'))
        
        # Test transfer
        self.assertEqual(transfer.get_display_amount_for_account(self.account1), Decimal('-200.00'))
        self.assertEqual(transfer.get_display_amount_for_account(self.account2), Decimal('200.00'))
    
    def test_get_description_for_account(self):
        """Test get_description_for_account method."""
        deposit = Transaction.objects.create(
            transaction_type='deposit',
            amount=100.00,
            receiver_account=self.account1,
            description='Salary deposit'
        )
        withdrawal = Transaction.objects.create(
            transaction_type='withdrawal',
            amount=50.00,
            sender_account=self.account1,
            description='ATM withdrawal'
        )
        transfer = Transaction.objects.create(
            transaction_type='transfer',
            amount=200.00,
            sender_account=self.account1,
            receiver_account=self.account2,
            description='Monthly transfer'
        )
        
        # Test deposit
        desc = deposit.get_description_for_account(self.account1)
        self.assertIn('Deposit', desc)
        self.assertIn('Salary deposit', desc)
        
        # Test withdrawal
        desc = withdrawal.get_description_for_account(self.account1)
        self.assertIn('Withdrawal', desc)
        self.assertIn('ATM withdrawal', desc)
        
        # Test transfer
        desc_sender = transfer.get_description_for_account(self.account1)
        desc_receiver = transfer.get_description_for_account(self.account2)
        self.assertIn('Transfer to', desc_sender)
        self.assertIn('Transfer from', desc_receiver)
        self.assertIn('Monthly transfer', desc_sender)
        self.assertIn('Monthly transfer', desc_receiver)
    
    def test_string_representation(self):
        """Test the string representation of transactions."""
        deposit = Transaction.objects.create(
            transaction_type='deposit',
            amount=100.00,
            receiver_account=self.account1
        )
        withdrawal = Transaction.objects.create(
            transaction_type='withdrawal',
            amount=50.00,
            sender_account=self.account1
        )
        transfer = Transaction.objects.create(
            transaction_type='transfer',
            amount=200.00,
            sender_account=self.account1,
            receiver_account=self.account2
        )
        
        # Test string representations
        self.assertIn('Deposit of $100', str(deposit))
        self.assertIn(self.account1.account_number, str(deposit))
        
        self.assertIn('Withdrawal of $50', str(withdrawal))
        self.assertIn(self.account1.account_number, str(withdrawal))
        
        self.assertIn('Transfer of $200', str(transfer))
        self.assertIn(self.account1.account_number, str(transfer))
        self.assertIn(self.account2.account_number, str(transfer))
    
    def test_account_relationships(self):
        """Test relationships between Transaction and BankAccount models."""
        # Create transactions
        deposit = Transaction.objects.create(
            transaction_type='deposit',
            amount=100.00,
            receiver_account=self.account1
        )
        withdrawal = Transaction.objects.create(
            transaction_type='withdrawal',
            amount=50.00,
            sender_account=self.account1
        )
        transfer = Transaction.objects.create(
            transaction_type='transfer',
            amount=200.00,
            sender_account=self.account1,
            receiver_account=self.account2
        )
        
        # Test sent_transactions relationship
        sent_transactions = self.account1.sent_transactions.all()
        self.assertIn(withdrawal, sent_transactions)
        self.assertIn(transfer, sent_transactions)
        self.assertNotIn(deposit, sent_transactions)
        
        # Test received_transactions relationship
        received_transactions = self.account1.received_transactions.all()
        self.assertIn(deposit, received_transactions)
        self.assertNotIn(withdrawal, received_transactions)
        self.assertNotIn(transfer, received_transactions)
        
        received_transactions_2 = self.account2.received_transactions.all()
        self.assertIn(transfer, received_transactions_2)
    
    def test_model_meta_options(self):
        """Test model meta options."""
        self.assertEqual(Transaction._meta.db_table, 'transactions')
        self.assertEqual(Transaction._meta.verbose_name, 'Transaction')
        self.assertEqual(Transaction._meta.verbose_name_plural, 'Transactions')
        self.assertEqual(Transaction._meta.ordering, ['-timestamp'])


class DepositFunctionalityTestCase(TestCase):
    """Test cases for deposit functionality."""
    
    def setUp(self):
        """Set up test data."""
        from django.test import Client
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Create bank account
        self.bank_account = BankAccount.objects.create(
            user=self.user,
            account_type='savings',
            balance=Decimal('1000.00'),
            status='active'
        )
        
        from django.urls import reverse
        self.deposit_url = reverse('transactions:deposit')
    
    def test_deposit_form_valid_data(self):
        """Test deposit form with valid data."""
        from .forms import DepositForm
        
        form_data = {
            'amount': '100.50',
            'description': 'Test deposit'
        }
        form = DepositForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['amount'], Decimal('100.50'))
        self.assertEqual(form.cleaned_data['description'], 'Test deposit')
    
    def test_deposit_form_invalid_amount(self):
        """Test deposit form with invalid amounts."""
        from .forms import DepositForm
        
        # Negative amount
        form = DepositForm(data={'amount': '-50.00'})
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
        
        # Zero amount
        form = DepositForm(data={'amount': '0.00'})
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
        
        # Amount too large
        form = DepositForm(data={'amount': '200000.00'})
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
    
    def test_deposit_form_default_description(self):
        """Test deposit form sets default description when empty."""
        from .forms import DepositForm
        
        form_data = {
            'amount': '100.00',
            'description': ''
        }
        form = DepositForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['description'], 'Cash deposit')
    
    def test_deposit_view_get_authenticated(self):
        """Test deposit view GET request for authenticated user."""
        from .forms import DepositForm
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.deposit_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Deposit Money')
        self.assertContains(response, self.bank_account.account_number)
        self.assertContains(response, '$1000.00')  # Current balance
        self.assertIsInstance(response.context['form'], DepositForm)
    
    def test_deposit_view_get_unauthenticated(self):
        """Test deposit view GET request for unauthenticated user."""
        response = self.client.get(self.deposit_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_deposit_view_no_bank_account(self):
        """Test deposit view when user has no bank account."""
        from django.contrib.messages import get_messages
        
        # Create user without bank account
        user_no_account = User.objects.create_user(
            username='noaccountuser',
            password='testpass123'
        )
        
        self.client.login(username='noaccountuser', password='testpass123')
        response = self.client.get(self.deposit_url)
        
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('No bank account found' in str(m) for m in messages))
    
    def test_deposit_view_inactive_account(self):
        """Test deposit view with inactive account."""
        from django.contrib.messages import get_messages
        
        self.bank_account.status = 'frozen'
        self.bank_account.save()
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.deposit_url)
        
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('frozen and cannot perform transactions' in str(m) for m in messages))
    
    def test_deposit_view_post_valid(self):
        """Test successful deposit transaction."""
        from django.contrib.messages import get_messages
        from django.urls import reverse
        
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'amount': '250.75',
            'description': 'Salary deposit'
        }
        
        initial_balance = self.bank_account.balance
        response = self.client.post(self.deposit_url, data=form_data)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:dashboard'))
        
        # Check balance updated
        self.bank_account.refresh_from_db()
        expected_balance = initial_balance + Decimal('250.75')
        self.assertEqual(self.bank_account.balance, expected_balance)
        
        # Check transaction created
        transaction = Transaction.objects.filter(
            transaction_type='deposit',
            receiver_account=self.bank_account
        ).first()
        
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, Decimal('250.75'))
        self.assertEqual(transaction.description, 'Salary deposit')
        self.assertEqual(transaction.receiver_balance_after, expected_balance)
        self.assertIsNone(transaction.sender_account)
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Successfully deposited $250.75' in str(m) for m in messages))
    
    def test_deposit_view_post_invalid(self):
        """Test deposit view with invalid form data."""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'amount': '-100.00',  # Invalid negative amount
            'description': 'Invalid deposit'
        }
        
        initial_balance = self.bank_account.balance
        response = self.client.post(self.deposit_url, data=form_data)
        
        # Check form redisplayed with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ensure this value is greater than or equal to 0.01')
        
        # Check balance unchanged
        self.bank_account.refresh_from_db()
        self.assertEqual(self.bank_account.balance, initial_balance)
        
        # Check no transaction created
        self.assertFalse(Transaction.objects.filter(
            transaction_type='deposit',
            receiver_account=self.bank_account,
            amount=Decimal('100.00')
        ).exists())
    
    def test_deposit_edge_cases(self):
        """Test deposit edge cases."""
        from django.urls import reverse
        
        self.client.login(username='testuser', password='testpass123')
        
        # Test minimum deposit amount
        form_data = {
            'amount': '0.01',
            'description': 'Minimum deposit'
        }
        response = self.client.post(self.deposit_url, data=form_data)
        self.assertEqual(response.status_code, 302)  # Should succeed
        
        # Check transaction created
        transaction = Transaction.objects.filter(
            amount=Decimal('0.01'),
            transaction_type='deposit'
        ).first()
        self.assertIsNotNone(transaction)
        
        # Test maximum allowed deposit amount
        form_data = {
            'amount': '100000.00',
            'description': 'Maximum deposit'
        }
        response = self.client.post(self.deposit_url, data=form_data)
        self.assertEqual(response.status_code, 302)  # Should succeed
    
    def test_deposit_with_special_characters_in_description(self):
        """Test deposit with special characters in description."""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'amount': '100.00',
            'description': 'Deposit with special chars: @#$%^&*()'
        }
        
        response = self.client.post(self.deposit_url, data=form_data)
        self.assertEqual(response.status_code, 302)
        
        # Check transaction created with special characters
        transaction = Transaction.objects.filter(
            transaction_type='deposit',
            description='Deposit with special chars: @#$%^&*()'
        ).first()
        self.assertIsNotNone(transaction)


class WithdrawalFunctionalityTestCase(TestCase):
    """Test cases for withdrawal functionality."""
    
    def setUp(self):
        """Set up test data."""
        from django.test import Client
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Create bank account with sufficient balance
        self.bank_account = BankAccount.objects.create(
            user=self.user,
            account_type='savings',
            balance=Decimal('1000.00'),
            status='active'
        )
        
        from django.urls import reverse
        self.withdrawal_url = reverse('transactions:withdrawal')
    
    def test_withdrawal_form_valid_data(self):
        """Test withdrawal form with valid data."""
        from .forms import WithdrawalForm
        
        form_data = {
            'amount': '100.50',
            'description': 'ATM withdrawal'
        }
        form = WithdrawalForm(data=form_data, account=self.bank_account)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['amount'], Decimal('100.50'))
        self.assertEqual(form.cleaned_data['description'], 'ATM withdrawal')
    
    def test_withdrawal_form_insufficient_funds(self):
        """Test withdrawal form with insufficient funds."""
        from .forms import WithdrawalForm
        
        form_data = {
            'amount': '1500.00',  # More than available balance
            'description': 'Large withdrawal'
        }
        form = WithdrawalForm(data=form_data, account=self.bank_account)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
        self.assertIn('Insufficient funds', str(form.errors['amount']))
    
    def test_withdrawal_form_invalid_amount(self):
        """Test withdrawal form with invalid amounts."""
        from .forms import WithdrawalForm
        
        # Negative amount
        form = WithdrawalForm(data={'amount': '-50.00'}, account=self.bank_account)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
        
        # Zero amount
        form = WithdrawalForm(data={'amount': '0.00'}, account=self.bank_account)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
        
        # Amount too large (over limit)
        form = WithdrawalForm(data={'amount': '15000.00'}, account=self.bank_account)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
    
    def test_withdrawal_form_default_description(self):
        """Test withdrawal form sets default description when empty."""
        from .forms import WithdrawalForm
        
        form_data = {
            'amount': '100.00',
            'description': ''
        }
        form = WithdrawalForm(data=form_data, account=self.bank_account)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['description'], 'Cash withdrawal')
    
    def test_withdrawal_view_get_authenticated(self):
        """Test withdrawal view GET request for authenticated user."""
        from .forms import WithdrawalForm
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.withdrawal_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Withdraw Money')
        self.assertContains(response, self.bank_account.account_number)
        self.assertContains(response, '$1000.00')  # Available balance
        self.assertIsInstance(response.context['form'], WithdrawalForm)
    
    def test_withdrawal_view_get_unauthenticated(self):
        """Test withdrawal view GET request for unauthenticated user."""
        response = self.client.get(self.withdrawal_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_withdrawal_view_no_bank_account(self):
        """Test withdrawal view when user has no bank account."""
        from django.contrib.messages import get_messages
        
        # Create user without bank account
        user_no_account = User.objects.create_user(
            username='noaccountuser',
            password='testpass123'
        )
        
        self.client.login(username='noaccountuser', password='testpass123')
        response = self.client.get(self.withdrawal_url)
        
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('No bank account found' in str(m) for m in messages))
    
    def test_withdrawal_view_inactive_account(self):
        """Test withdrawal view with inactive account."""
        from django.contrib.messages import get_messages
        
        self.bank_account.status = 'frozen'
        self.bank_account.save()
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.withdrawal_url)
        
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('frozen and cannot perform transactions' in str(m) for m in messages))
    
    def test_withdrawal_view_post_valid(self):
        """Test successful withdrawal transaction."""
        from django.contrib.messages import get_messages
        from django.urls import reverse
        
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'amount': '250.75',
            'description': 'ATM withdrawal'
        }
        
        initial_balance = self.bank_account.balance
        response = self.client.post(self.withdrawal_url, data=form_data)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:dashboard'))
        
        # Check balance updated
        self.bank_account.refresh_from_db()
        expected_balance = initial_balance - Decimal('250.75')
        self.assertEqual(self.bank_account.balance, expected_balance)
        
        # Check transaction created
        transaction = Transaction.objects.filter(
            transaction_type='withdrawal',
            sender_account=self.bank_account
        ).first()
        
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, Decimal('250.75'))
        self.assertEqual(transaction.description, 'ATM withdrawal')
        self.assertEqual(transaction.sender_balance_after, expected_balance)
        self.assertIsNone(transaction.receiver_account)
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Successfully withdrew $250.75' in str(m) for m in messages))
    
    def test_withdrawal_view_post_insufficient_funds(self):
        """Test withdrawal view with insufficient funds."""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'amount': '1500.00',  # More than available balance
            'description': 'Large withdrawal'
        }
        
        initial_balance = self.bank_account.balance
        response = self.client.post(self.withdrawal_url, data=form_data)
        
        # Check form redisplayed with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Insufficient funds')
        
        # Check balance unchanged
        self.bank_account.refresh_from_db()
        self.assertEqual(self.bank_account.balance, initial_balance)
        
        # Check no transaction created
        self.assertFalse(Transaction.objects.filter(
            transaction_type='withdrawal',
            sender_account=self.bank_account,
            amount=Decimal('1500.00')
        ).exists())
    
    def test_withdrawal_view_post_invalid(self):
        """Test withdrawal view with invalid form data."""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'amount': '-100.00',  # Invalid negative amount
            'description': 'Invalid withdrawal'
        }
        
        initial_balance = self.bank_account.balance
        response = self.client.post(self.withdrawal_url, data=form_data)
        
        # Check form redisplayed with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ensure this value is greater than or equal to 0.01')
        
        # Check balance unchanged
        self.bank_account.refresh_from_db()
        self.assertEqual(self.bank_account.balance, initial_balance)
        
        # Check no transaction created
        self.assertFalse(Transaction.objects.filter(
            transaction_type='withdrawal',
            sender_account=self.bank_account,
            amount=Decimal('100.00')
        ).exists())
    
    def test_withdrawal_edge_cases(self):
        """Test withdrawal edge cases."""
        self.client.login(username='testuser', password='testpass123')
        
        # Test minimum withdrawal amount
        form_data = {
            'amount': '0.01',
            'description': 'Minimum withdrawal'
        }
        response = self.client.post(self.withdrawal_url, data=form_data)
        self.assertEqual(response.status_code, 302)  # Should succeed
        
        # Check transaction created
        transaction = Transaction.objects.filter(
            amount=Decimal('0.01'),
            transaction_type='withdrawal'
        ).first()
        self.assertIsNotNone(transaction)
        
        # Test withdrawal of entire remaining balance
        self.bank_account.refresh_from_db()
        remaining_balance = self.bank_account.balance
        
        form_data = {
            'amount': str(remaining_balance),
            'description': 'Full withdrawal'
        }
        response = self.client.post(self.withdrawal_url, data=form_data)
        self.assertEqual(response.status_code, 302)  # Should succeed
        
        # Check balance is now zero
        self.bank_account.refresh_from_db()
        self.assertEqual(self.bank_account.balance, Decimal('0.00'))
    
    def test_withdrawal_with_zero_balance_account(self):
        """Test withdrawal view with zero balance account."""
        # Set account balance to zero
        self.bank_account.balance = Decimal('0.00')
        self.bank_account.save()
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.withdrawal_url)
        
        # Should still show the page but with warnings
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Insufficient Funds')
        self.assertContains(response, 'Your account balance is $0.00')
    
    def test_withdrawal_maximum_limit(self):
        """Test withdrawal maximum limit validation."""
        from .forms import WithdrawalForm
        
        # Set high balance
        self.bank_account.balance = Decimal('50000.00')
        self.bank_account.save()
        
        # Test maximum allowed withdrawal amount
        form_data = {
            'amount': '10000.00',
            'description': 'Maximum withdrawal'
        }
        form = WithdrawalForm(data=form_data, account=self.bank_account)
        self.assertTrue(form.is_valid())
        
        # Test over maximum limit
        form_data = {
            'amount': '15000.00',
            'description': 'Over limit withdrawal'
        }
        form = WithdrawalForm(data=form_data, account=self.bank_account)
        self.assertFalse(form.is_valid())
        self.assertIn('Maximum withdrawal amount', str(form.errors['amount']))


class TransferFunctionalityTestCase(TestCase):
    """Test cases for transfer functionality."""
    
    def setUp(self):
        """Set up test data."""
        from django.test import Client
        self.client = Client()
        
        # Create test users
        self.user1 = User.objects.create_user(
            username='sender',
            email='sender@example.com',
            password='testpass123',
            first_name='Sender',
            last_name='User'
        )
        
        self.user2 = User.objects.create_user(
            username='receiver',
            email='receiver@example.com',
            password='testpass123',
            first_name='Receiver',
            last_name='User'
        )
        
        # Create bank accounts
        self.sender_account = BankAccount.objects.create(
            user=self.user1,
            account_type='savings',
            balance=Decimal('1000.00'),
            status='active'
        )
        
        self.receiver_account = BankAccount.objects.create(
            user=self.user2,
            account_type='current',
            balance=Decimal('500.00'),
            status='active'
        )
        
        from django.urls import reverse
        self.transfer_url = reverse('transactions:transfer')
    
    def test_transfer_form_valid_data(self):
        """Test transfer form with valid data."""
        from .forms import TransferForm
        
        form_data = {
            'recipient_account_number': self.receiver_account.account_number,
            'amount': '100.50',
            'description': 'Payment for services'
        }
        form = TransferForm(data=form_data, sender_account=self.sender_account)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['amount'], Decimal('100.50'))
        self.assertEqual(form.cleaned_data['description'], 'Payment for services')
        self.assertEqual(form.get_recipient_account(), self.receiver_account)
    
    def test_transfer_form_invalid_recipient_account(self):
        """Test transfer form with invalid recipient account."""
        from .forms import TransferForm
        
        # Non-existent account
        form_data = {
            'recipient_account_number': '999999999999',
            'amount': '100.00',
            'description': 'Test transfer'
        }
        form = TransferForm(data=form_data, sender_account=self.sender_account)
        self.assertFalse(form.is_valid())
        self.assertIn('recipient_account_number', form.errors)
        self.assertIn('Recipient account not found', str(form.errors['recipient_account_number']))
        
        # Invalid format
        form_data = {
            'recipient_account_number': '12345',  # Too short
            'amount': '100.00',
            'description': 'Test transfer'
        }
        form = TransferForm(data=form_data, sender_account=self.sender_account)
        self.assertFalse(form.is_valid())
        self.assertIn('recipient_account_number', form.errors)
        
        # Same account
        form_data = {
            'recipient_account_number': self.sender_account.account_number,
            'amount': '100.00',
            'description': 'Test transfer'
        }
        form = TransferForm(data=form_data, sender_account=self.sender_account)
        self.assertFalse(form.is_valid())
        self.assertIn('recipient_account_number', form.errors)
        self.assertIn('Cannot transfer money to your own account', str(form.errors['recipient_account_number']))
    
    def test_transfer_form_insufficient_funds(self):
        """Test transfer form with insufficient funds."""
        from .forms import TransferForm
        
        form_data = {
            'recipient_account_number': self.receiver_account.account_number,
            'amount': '1500.00',  # More than available balance
            'description': 'Large transfer'
        }
        form = TransferForm(data=form_data, sender_account=self.sender_account)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
        self.assertIn('Insufficient funds', str(form.errors['amount']))
    
    def test_transfer_form_inactive_recipient(self):
        """Test transfer form with inactive recipient account."""
        from .forms import TransferForm
        
        # Set recipient account to frozen
        self.receiver_account.status = 'frozen'
        self.receiver_account.save()
        
        form_data = {
            'recipient_account_number': self.receiver_account.account_number,
            'amount': '100.00',
            'description': 'Test transfer'
        }
        form = TransferForm(data=form_data, sender_account=self.sender_account)
        self.assertFalse(form.is_valid())
        self.assertIn('recipient_account_number', form.errors)
        self.assertIn('not active and cannot receive transfers', str(form.errors['recipient_account_number']))
    
    def test_transfer_form_default_description(self):
        """Test transfer form sets default description when empty."""
        from .forms import TransferForm
        
        form_data = {
            'recipient_account_number': self.receiver_account.account_number,
            'amount': '100.00',
            'description': ''
        }
        form = TransferForm(data=form_data, sender_account=self.sender_account)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['description'], 'Money transfer')
    
    def test_transfer_view_get_authenticated(self):
        """Test transfer view GET request for authenticated user."""
        from .forms import TransferForm
        
        self.client.login(username='sender', password='testpass123')
        response = self.client.get(self.transfer_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Transfer Money')
        self.assertContains(response, self.sender_account.account_number)
        self.assertContains(response, '$1000.00')  # Available balance
        self.assertIsInstance(response.context['form'], TransferForm)
    
    def test_transfer_view_get_unauthenticated(self):
        """Test transfer view GET request for unauthenticated user."""
        response = self.client.get(self.transfer_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_transfer_view_no_bank_account(self):
        """Test transfer view when user has no bank account."""
        from django.contrib.messages import get_messages
        
        # Create user without bank account
        user_no_account = User.objects.create_user(
            username='noaccountuser',
            password='testpass123'
        )
        
        self.client.login(username='noaccountuser', password='testpass123')
        response = self.client.get(self.transfer_url)
        
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('No bank account found' in str(m) for m in messages))
    
    def test_transfer_view_inactive_account(self):
        """Test transfer view with inactive sender account."""
        from django.contrib.messages import get_messages
        
        self.sender_account.status = 'frozen'
        self.sender_account.save()
        
        self.client.login(username='sender', password='testpass123')
        response = self.client.get(self.transfer_url)
        
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('frozen and cannot perform transactions' in str(m) for m in messages))
    
    def test_transfer_view_post_valid(self):
        """Test successful transfer transaction."""
        from django.contrib.messages import get_messages
        from django.urls import reverse
        
        self.client.login(username='sender', password='testpass123')
        
        form_data = {
            'recipient_account_number': self.receiver_account.account_number,
            'amount': '250.75',
            'description': 'Payment for services'
        }
        
        initial_sender_balance = self.sender_account.balance
        initial_receiver_balance = self.receiver_account.balance
        
        response = self.client.post(self.transfer_url, data=form_data)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:dashboard'))
        
        # Check balances updated
        self.sender_account.refresh_from_db()
        self.receiver_account.refresh_from_db()
        
        expected_sender_balance = initial_sender_balance - Decimal('250.75')
        expected_receiver_balance = initial_receiver_balance + Decimal('250.75')
        
        self.assertEqual(self.sender_account.balance, expected_sender_balance)
        self.assertEqual(self.receiver_account.balance, expected_receiver_balance)
        
        # Check transaction created
        transaction = Transaction.objects.filter(
            transaction_type='transfer',
            sender_account=self.sender_account,
            receiver_account=self.receiver_account
        ).first()
        
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, Decimal('250.75'))
        self.assertEqual(transaction.description, 'Payment for services')
        self.assertEqual(transaction.sender_balance_after, expected_sender_balance)
        self.assertEqual(transaction.receiver_balance_after, expected_receiver_balance)
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Successfully transferred $250.75' in str(m) for m in messages))
    
    def test_transfer_view_post_insufficient_funds(self):
        """Test transfer view with insufficient funds."""
        self.client.login(username='sender', password='testpass123')
        
        form_data = {
            'recipient_account_number': self.receiver_account.account_number,
            'amount': '1500.00',  # More than available balance
            'description': 'Large transfer'
        }
        
        initial_sender_balance = self.sender_account.balance
        initial_receiver_balance = self.receiver_account.balance
        
        response = self.client.post(self.transfer_url, data=form_data)
        
        # Check form redisplayed with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Insufficient funds')
        
        # Check balances unchanged
        self.sender_account.refresh_from_db()
        self.receiver_account.refresh_from_db()
        
        self.assertEqual(self.sender_account.balance, initial_sender_balance)
        self.assertEqual(self.receiver_account.balance, initial_receiver_balance)
        
        # Check no transaction created
        self.assertFalse(Transaction.objects.filter(
            transaction_type='transfer',
            sender_account=self.sender_account,
            receiver_account=self.receiver_account,
            amount=Decimal('1500.00')
        ).exists())
    
    def test_transfer_view_post_invalid_recipient(self):
        """Test transfer view with invalid recipient account."""
        self.client.login(username='sender', password='testpass123')
        
        form_data = {
            'recipient_account_number': '999999999999',  # Non-existent account
            'amount': '100.00',
            'description': 'Test transfer'
        }
        
        initial_sender_balance = self.sender_account.balance
        response = self.client.post(self.transfer_url, data=form_data)
        
        # Check form redisplayed with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recipient account not found')
        
        # Check balance unchanged
        self.sender_account.refresh_from_db()
        self.assertEqual(self.sender_account.balance, initial_sender_balance)
        
        # Check no transaction created
        self.assertFalse(Transaction.objects.filter(
            transaction_type='transfer',
            sender_account=self.sender_account,
            amount=Decimal('100.00')
        ).exists())
    
    def test_transfer_atomicity(self):
        """Test that transfer transactions are atomic."""
        self.client.login(username='sender', password='testpass123')
        
        # Mock a database error during transaction creation
        original_create = Transaction.objects.create
        
        def mock_create(*args, **kwargs):
            if kwargs.get('transaction_type') == 'transfer':
                raise Exception("Database error")
            return original_create(*args, **kwargs)
        
        Transaction.objects.create = mock_create
        
        try:
            form_data = {
                'recipient_account_number': self.receiver_account.account_number,
                'amount': '100.00',
                'description': 'Test transfer'
            }
            
            initial_sender_balance = self.sender_account.balance
            initial_receiver_balance = self.receiver_account.balance
            
            response = self.client.post(self.transfer_url, data=form_data)
            
            # Check balances unchanged due to rollback
            self.sender_account.refresh_from_db()
            self.receiver_account.refresh_from_db()
            
            self.assertEqual(self.sender_account.balance, initial_sender_balance)
            self.assertEqual(self.receiver_account.balance, initial_receiver_balance)
            
            # Check error message displayed
            from django.contrib.messages import get_messages
            messages = list(get_messages(response.wsgi_request))
            self.assertTrue(any('error occurred while processing' in str(m) for m in messages))
            
        finally:
            # Restore original method
            Transaction.objects.create = original_create
    
    def test_transfer_edge_cases(self):
        """Test transfer edge cases."""
        self.client.login(username='sender', password='testpass123')
        
        # Test minimum transfer amount
        form_data = {
            'recipient_account_number': self.receiver_account.account_number,
            'amount': '0.01',
            'description': 'Minimum transfer'
        }
        response = self.client.post(self.transfer_url, data=form_data)
        self.assertEqual(response.status_code, 302)  # Should succeed
        
        # Check transaction created
        transaction = Transaction.objects.filter(
            amount=Decimal('0.01'),
            transaction_type='transfer'
        ).first()
        self.assertIsNotNone(transaction)
        
        # Test transfer of entire remaining balance
        self.sender_account.refresh_from_db()
        remaining_balance = self.sender_account.balance
        
        form_data = {
            'recipient_account_number': self.receiver_account.account_number,
            'amount': str(remaining_balance),
            'description': 'Full transfer'
        }
        response = self.client.post(self.transfer_url, data=form_data)
        self.assertEqual(response.status_code, 302)  # Should succeed
        
        # Check sender balance is now zero
        self.sender_account.refresh_from_db()
        self.assertEqual(self.sender_account.balance, Decimal('0.00'))
    
    def test_transfer_maximum_limit(self):
        """Test transfer maximum limit validation."""
        from .forms import TransferForm
        
        # Set high balance
        self.sender_account.balance = Decimal('100000.00')
        self.sender_account.save()
        
        # Test maximum allowed transfer amount
        form_data = {
            'recipient_account_number': self.receiver_account.account_number,
            'amount': '50000.00',
            'description': 'Maximum transfer'
        }
        form = TransferForm(data=form_data, sender_account=self.sender_account)
        self.assertTrue(form.is_valid())
        
        # Test over maximum limit
        form_data = {
            'recipient_account_number': self.receiver_account.account_number,
            'amount': '75000.00',
            'description': 'Over limit transfer'
        }
        form = TransferForm(data=form_data, sender_account=self.sender_account)
        self.assertFalse(form.is_valid())
        self.assertIn('Maximum transfer amount', str(form.errors['amount']))
    
    def test_transfer_with_special_characters_in_description(self):
        """Test transfer with special characters in description."""
        self.client.login(username='sender', password='testpass123')
        
        form_data = {
            'recipient_account_number': self.receiver_account.account_number,
            'amount': '100.00',
            'description': 'Transfer with special chars: @#$%^&*()'
        }
        
        response = self.client.post(self.transfer_url, data=form_data)
        self.assertEqual(response.status_code, 302)
        
        # Check transaction created with special characters
        transaction = Transaction.objects.filter(
            transaction_type='transfer',
            description='Transfer with special chars: @#$%^&*()'
        ).first()
        self.assertIsNotNone(transaction)


class TransactionHistoryViewTestCase(TestCase):
    """Test cases for transaction history view functionality."""
    
    def setUp(self):
        """Set up test data."""
        from django.test import Client
        from django.urls import reverse
        
        self.client = Client()
        
        # Create test users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123',
            first_name='User',
            last_name='One'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123',
            first_name='User',
            last_name='Two'
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
        
        self.history_url = reverse('transactions:history')
        
        # Create test transactions
        self.create_test_transactions()
    
    def create_test_transactions(self):
        """Create test transactions for testing."""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        
        # Create large withdrawal (35 days ago) - for date filtering tests
        self.old_withdrawal = Transaction.objects.create(
            transaction_type='withdrawal',
            amount=Decimal('500.00'),
            sender_account=self.account1,
            sender_balance_after=Decimal('500.00'),
            description='Old withdrawal'
        )
        # Manually set timestamp after creation to avoid auto_now_add
        Transaction.objects.filter(id=self.old_withdrawal.id).update(
            timestamp=now - timedelta(days=35)
        )
        self.old_withdrawal.refresh_from_db()
        
        # Create deposit transaction (7 days ago)
        self.deposit_txn = Transaction.objects.create(
            transaction_type='deposit',
            amount=Decimal('200.00'),
            receiver_account=self.account1,
            receiver_balance_after=Decimal('1200.00'),
            description='Salary deposit'
        )
        Transaction.objects.filter(id=self.deposit_txn.id).update(
            timestamp=now - timedelta(days=7)
        )
        self.deposit_txn.refresh_from_db()
        
        # Create withdrawal transaction (5 days ago)
        self.withdrawal_txn = Transaction.objects.create(
            transaction_type='withdrawal',
            amount=Decimal('50.00'),
            sender_account=self.account1,
            sender_balance_after=Decimal('1150.00'),
            description='ATM withdrawal'
        )
        Transaction.objects.filter(id=self.withdrawal_txn.id).update(
            timestamp=now - timedelta(days=5)
        )
        self.withdrawal_txn.refresh_from_db()
        
        # Create transfer transaction (3 days ago)
        self.transfer_txn = Transaction.objects.create(
            transaction_type='transfer',
            amount=Decimal('100.00'),
            sender_account=self.account1,
            receiver_account=self.account2,
            sender_balance_after=Decimal('1050.00'),
            receiver_balance_after=Decimal('600.00'),
            description='Monthly transfer'
        )
        Transaction.objects.filter(id=self.transfer_txn.id).update(
            timestamp=now - timedelta(days=3)
        )
        self.transfer_txn.refresh_from_db()
        
        # Create recent deposit (1 day ago)
        self.recent_deposit = Transaction.objects.create(
            transaction_type='deposit',
            amount=Decimal('300.00'),
            receiver_account=self.account1,
            receiver_balance_after=Decimal('1350.00'),
            description='Bonus payment'
        )
        Transaction.objects.filter(id=self.recent_deposit.id).update(
            timestamp=now - timedelta(days=1)
        )
        self.recent_deposit.refresh_from_db()
    
    def test_history_view_authenticated_user(self):
        """Test transaction history view for authenticated user."""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.history_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Transaction History')
        self.assertContains(response, self.account1.account_number)
        self.assertContains(response, '$1000.00')  # Current balance
        
        # Check that transactions are displayed
        self.assertContains(response, 'Salary deposit')
        self.assertContains(response, 'ATM withdrawal')
        self.assertContains(response, 'Monthly transfer')
        self.assertContains(response, 'Bonus payment')
        
        # Check transaction count
        self.assertEqual(response.context['total_transactions'], 5)  # All transactions for account1
    
    def test_history_view_unauthenticated_user(self):
        """Test transaction history view for unauthenticated user."""
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_history_view_no_bank_account(self):
        """Test transaction history view when user has no bank account."""
        from django.contrib.messages import get_messages
        
        # Create user without bank account
        user_no_account = User.objects.create_user(
            username='noaccountuser',
            password='testpass123'
        )
        
        self.client.login(username='noaccountuser', password='testpass123')
        response = self.client.get(self.history_url)
        
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('No bank account found' in str(m) for m in messages))
    
    def test_history_view_transaction_ordering(self):
        """Test that transactions are ordered by timestamp (newest first)."""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.history_url)
        
        transaction_data = response.context['transaction_data']
        
        # Check that transactions are in descending order by timestamp
        timestamps = [item['transaction'].timestamp for item in transaction_data]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
        
        # Check that the most recent transaction is first
        self.assertEqual(transaction_data[0]['transaction'], self.recent_deposit)
    
    def test_history_view_pagination(self):
        """Test pagination functionality."""
        # Create many transactions to test pagination
        for i in range(25):
            Transaction.objects.create(
                transaction_type='deposit',
                amount=Decimal('10.00'),
                receiver_account=self.account1,
                receiver_balance_after=Decimal('1000.00'),
                description=f'Test deposit {i}'
            )
        
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.history_url)
        
        # Check pagination context
        self.assertTrue(response.context['page_obj'].has_other_pages)
        self.assertEqual(len(response.context['transaction_data']), 20)  # 20 per page
        
        # Test second page
        response = self.client.get(self.history_url + '?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context['transaction_data']) > 0)
    
    def test_history_view_transaction_type_filter(self):
        """Test filtering by transaction type."""
        self.client.login(username='user1', password='testpass123')
        
        # Filter by deposits
        response = self.client.get(self.history_url + '?type=deposit')
        transaction_data = response.context['transaction_data']
        
        # Should only show deposit transactions
        for item in transaction_data:
            self.assertEqual(item['transaction'].transaction_type, 'deposit')
        
        # Should show 2 deposits for account1
        self.assertEqual(len(transaction_data), 2)
        
        # Filter by withdrawals
        response = self.client.get(self.history_url + '?type=withdrawal')
        transaction_data = response.context['transaction_data']
        
        # Should only show withdrawal transactions
        for item in transaction_data:
            self.assertEqual(item['transaction'].transaction_type, 'withdrawal')
        
        # Should show 2 withdrawals for account1
        self.assertEqual(len(transaction_data), 2)
        
        # Filter by transfers
        response = self.client.get(self.history_url + '?type=transfer')
        transaction_data = response.context['transaction_data']
        
        # Should only show transfer transactions
        for item in transaction_data:
            self.assertEqual(item['transaction'].transaction_type, 'transfer')
        
        # Should show 1 transfer for account1
        self.assertEqual(len(transaction_data), 1)
    
    def test_history_view_date_filter(self):
        """Test filtering by date ranges."""
        self.client.login(username='user1', password='testpass123')
        
        # Filter by last 7 days
        response = self.client.get(self.history_url + '?date_filter=7days')
        transaction_data = response.context['transaction_data']
        
        # Should show transactions from last 7 days (3 transactions)
        self.assertEqual(len(transaction_data), 3)
        
        # Filter by last 30 days
        response = self.client.get(self.history_url + '?date_filter=30days')
        transaction_data = response.context['transaction_data']
        
        # Should show transactions from last 30 days (4 transactions)
        self.assertEqual(len(transaction_data), 4)
        
        # Filter by last 90 days
        response = self.client.get(self.history_url + '?date_filter=90days')
        transaction_data = response.context['transaction_data']
        
        # Should show all transactions (5 transactions)
        self.assertEqual(len(transaction_data), 5)
    
    def test_history_view_custom_date_range_filter(self):
        """Test filtering by custom date range."""
        from django.utils import timezone
        from datetime import timedelta
        
        self.client.login(username='user1', password='testpass123')
        
        now = timezone.now()
        start_date = (now - timedelta(days=6)).strftime('%Y-%m-%d')
        end_date = (now - timedelta(days=2)).strftime('%Y-%m-%d')
        
        response = self.client.get(
            self.history_url + f'?start_date={start_date}&end_date={end_date}'
        )
        transaction_data = response.context['transaction_data']
        
        # Should show transactions within the date range
        self.assertEqual(len(transaction_data), 2)  # withdrawal and transfer
    
    def test_history_view_amount_filter(self):
        """Test filtering by amount range."""
        self.client.login(username='user1', password='testpass123')
        
        # Filter by minimum amount
        response = self.client.get(self.history_url + '?min_amount=100')
        transaction_data = response.context['transaction_data']
        
        # Should show transactions >= $100
        for item in transaction_data:
            self.assertGreaterEqual(item['transaction'].amount, Decimal('100.00'))
        
        # Filter by maximum amount
        response = self.client.get(self.history_url + '?max_amount=100')
        transaction_data = response.context['transaction_data']
        
        # Should show transactions <= $100
        for item in transaction_data:
            self.assertLessEqual(item['transaction'].amount, Decimal('100.00'))
        
        # Filter by amount range
        response = self.client.get(self.history_url + '?min_amount=50&max_amount=200')
        transaction_data = response.context['transaction_data']
        
        # Should show transactions between $50 and $200
        for item in transaction_data:
            self.assertGreaterEqual(item['transaction'].amount, Decimal('50.00'))
            self.assertLessEqual(item['transaction'].amount, Decimal('200.00'))
    
    def test_history_view_invalid_filters(self):
        """Test handling of invalid filter values."""
        from django.contrib.messages import get_messages
        
        self.client.login(username='user1', password='testpass123')
        
        # Invalid date format
        response = self.client.get(self.history_url + '?start_date=invalid-date')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Invalid start date format' in str(m) for m in messages))
        
        # Invalid amount format
        response = self.client.get(self.history_url + '?min_amount=invalid-amount')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Invalid minimum amount format' in str(m) for m in messages))
    
    def test_history_view_transaction_display_amounts(self):
        """Test that transaction amounts are displayed correctly for the account."""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.history_url)
        
        transaction_data = response.context['transaction_data']
        
        # Find specific transactions and check display amounts
        for item in transaction_data:
            txn = item['transaction']
            if txn == self.deposit_txn:
                self.assertEqual(item['display_amount'], Decimal('200.00'))
                self.assertTrue(item['is_credit'])
                self.assertFalse(item['is_debit'])
            elif txn == self.withdrawal_txn:
                self.assertEqual(item['display_amount'], Decimal('-50.00'))
                self.assertFalse(item['is_credit'])
                self.assertTrue(item['is_debit'])
            elif txn == self.transfer_txn:
                self.assertEqual(item['display_amount'], Decimal('-100.00'))  # Sent from account1
                self.assertFalse(item['is_credit'])
                self.assertTrue(item['is_debit'])
    
    def test_history_view_transaction_descriptions(self):
        """Test that transaction descriptions are formatted correctly."""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.history_url)
        
        transaction_data = response.context['transaction_data']
        
        # Check that descriptions are properly formatted
        descriptions = [item['description'] for item in transaction_data]
        
        self.assertTrue(any('Deposit - Salary deposit' in desc for desc in descriptions))
        self.assertTrue(any('Withdrawal - ATM withdrawal' in desc for desc in descriptions))
        self.assertTrue(any(f'Transfer to {self.account2.account_number}' in desc for desc in descriptions))
    
    def test_history_view_statistics(self):
        """Test transaction statistics in the view context."""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.history_url)
        
        # Check statistics
        self.assertEqual(response.context['total_deposits'], 2)
        self.assertEqual(response.context['total_withdrawals'], 2)
        self.assertEqual(response.context['total_transfers_sent'], 1)
        self.assertEqual(response.context['total_transfers_received'], 0)
    
    def test_history_view_no_transactions(self):
        """Test history view when user has no transactions."""
        # Create user with account but no transactions
        user_no_txn = User.objects.create_user(
            username='notxnuser',
            password='testpass123'
        )
        account_no_txn = BankAccount.objects.create(
            user=user_no_txn,
            account_type='savings',
            balance=Decimal('0.00'),
            status='active'
        )
        
        self.client.login(username='notxnuser', password='testpass123')
        response = self.client.get(self.history_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No Transactions Found')
        self.assertEqual(len(response.context['transaction_data']), 0)
        self.assertEqual(response.context['total_transactions'], 0)
    
    def test_history_view_filter_persistence(self):
        """Test that filter values are persisted in the template."""
        self.client.login(username='user1', password='testpass123')
        
        filter_params = '?type=deposit&date_filter=30days&min_amount=50&max_amount=500'
        response = self.client.get(self.history_url + filter_params)
        
        # Check that filter values are in context
        self.assertEqual(response.context['current_type'], 'deposit')
        self.assertEqual(response.context['current_date_filter'], '30days')
        self.assertEqual(response.context['current_min_amount'], '50')
        self.assertEqual(response.context['current_max_amount'], '500')
    
    def test_history_view_combined_filters(self):
        """Test combining multiple filters."""
        self.client.login(username='user1', password='testpass123')
        
        # Combine type and amount filters
        response = self.client.get(
            self.history_url + '?type=deposit&min_amount=250'
        )
        transaction_data = response.context['transaction_data']
        
        # Should show only deposits >= $250
        self.assertEqual(len(transaction_data), 1)  # Only the $300 bonus payment
        self.assertEqual(transaction_data[0]['transaction'], self.recent_deposit)
    
    def test_history_view_balance_after_display(self):
        """Test that balance after transaction is displayed correctly."""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.history_url)
        
        transaction_data = response.context['transaction_data']
        
        # Check that balance_after values are correct
        for item in transaction_data:
            txn = item['transaction']
            if txn == self.deposit_txn:
                self.assertEqual(item['balance_after'], Decimal('1200.00'))
            elif txn == self.withdrawal_txn:
                self.assertEqual(item['balance_after'], Decimal('1150.00'))
            elif txn == self.transfer_txn:
                self.assertEqual(item['balance_after'], Decimal('1050.00'))  # Sender balance
    
    def test_history_view_transfer_from_receiver_perspective(self):
        """Test transfer transaction from receiver's perspective."""
        self.client.login(username='user2', password='testpass123')
        response = self.client.get(self.history_url)
        
        transaction_data = response.context['transaction_data']
        
        # Should show the transfer as received
        transfer_item = next(
            item for item in transaction_data 
            if item['transaction'] == self.transfer_txn
        )
        
        self.assertEqual(transfer_item['display_amount'], Decimal('100.00'))  # Positive for receiver
        self.assertTrue(transfer_item['is_credit'])
        self.assertFalse(transfer_item['is_debit'])
        self.assertIn(f'Transfer from {self.account1.account_number}', transfer_item['description'])
        self.assertEqual(transfer_item['balance_after'], Decimal('600.00'))  # Receiver balance


class StatementDownloadTestCase(TestCase):
    """Test cases for statement download functionality."""
    
    def setUp(self):
        """Set up test data."""
        from django.test import Client
        from django.urls import reverse
        
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='statementuser',
            email='statement@example.com',
            password='testpass123',
            first_name='Statement',
            last_name='User'
        )
        
        # Create bank account
        self.account = BankAccount.objects.create(
            user=self.user,
            account_type='savings',
            balance=Decimal('1000.00'),
            status='active'
        )
        
        self.csv_url = reverse('transactions:download_csv_statement')
        self.pdf_url = reverse('transactions:download_pdf_statement')
        
        # Create test transactions
        self.create_test_transactions()
    
    def create_test_transactions(self):
        """Create test transactions for statement testing."""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        
        # Create transactions with different dates
        self.transactions = []
        
        # Recent deposit (2 days ago)
        txn1 = Transaction.objects.create(
            transaction_type='deposit',
            amount=Decimal('500.00'),
            receiver_account=self.account,
            receiver_balance_after=Decimal('1500.00'),
            description='Salary deposit'
        )
        Transaction.objects.filter(id=txn1.id).update(
            timestamp=now - timedelta(days=2)
        )
        txn1.refresh_from_db()
        self.transactions.append(txn1)
        
        # Withdrawal (5 days ago)
        txn2 = Transaction.objects.create(
            transaction_type='withdrawal',
            amount=Decimal('100.00'),
            sender_account=self.account,
            sender_balance_after=Decimal('1400.00'),
            description='ATM withdrawal'
        )
        Transaction.objects.filter(id=txn2.id).update(
            timestamp=now - timedelta(days=5)
        )
        txn2.refresh_from_db()
        self.transactions.append(txn2)
        
        # Old deposit (30 days ago)
        txn3 = Transaction.objects.create(
            transaction_type='deposit',
            amount=Decimal('200.00'),
            receiver_account=self.account,
            receiver_balance_after=Decimal('1200.00'),
            description='Old deposit'
        )
        Transaction.objects.filter(id=txn3.id).update(
            timestamp=now - timedelta(days=30)
        )
        txn3.refresh_from_db()
        self.transactions.append(txn3)
    
    def test_csv_download_unauthenticated(self):
        """Test CSV download for unauthenticated user."""
        response = self.client.get(self.csv_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_pdf_download_unauthenticated(self):
        """Test PDF download for unauthenticated user."""
        response = self.client.get(self.pdf_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_csv_download_no_bank_account(self):
        """Test CSV download when user has no bank account."""
        from django.contrib.messages import get_messages
        
        # Create user without bank account
        user_no_account = User.objects.create_user(
            username='noaccountuser2',
            password='testpass123'
        )
        
        self.client.login(username='noaccountuser2', password='testpass123')
        response = self.client.get(self.csv_url)
        
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('No bank account found' in str(m) for m in messages))
    
    def test_csv_download_all_transactions(self):
        """Test CSV download with all transactions."""
        self.client.login(username='statementuser', password='testpass123')
        response = self.client.get(self.csv_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn(f'account-{self.account.account_number}', response['Content-Disposition'])
        
        # Check CSV content
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        
        # Should have header + 3 transactions
        self.assertEqual(len(lines), 4)
        
        # Check header
        header = lines[0]
        expected_headers = ['Date', 'Time', 'Transaction Type', 'Description', 'Amount', 'Balance After', 'Reference Number']
        for expected_header in expected_headers:
            self.assertIn(expected_header, header)
        
        # Check transaction data
        self.assertIn('Salary deposit', content)
        self.assertIn('ATM withdrawal', content)
        self.assertIn('Old deposit', content)
        self.assertIn('500.00', content)
        self.assertIn('-100.00', content)
        self.assertIn('200.00', content)
    
    def test_csv_download_with_date_filter(self):
        """Test CSV download with date range filtering."""
        from django.utils import timezone
        from datetime import timedelta
        
        self.client.login(username='statementuser', password='testpass123')
        
        # Filter for last 7 days
        now = timezone.now()
        start_date = (now - timedelta(days=7)).strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
        response = self.client.get(
            self.csv_url + f'?start_date={start_date}&end_date={end_date}'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check filename includes date range
        self.assertIn(f'from-{start_date}', response['Content-Disposition'])
        self.assertIn(f'to-{end_date}', response['Content-Disposition'])
        
        # Check content - should only include recent transactions
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        
        # Should have header + 2 recent transactions (not the 30-day old one)
        self.assertEqual(len(lines), 3)
        self.assertIn('Salary deposit', content)
        self.assertIn('ATM withdrawal', content)
        self.assertNotIn('Old deposit', content)
    
    def test_csv_download_invalid_date_format(self):
        """Test CSV download with invalid date format."""
        from django.contrib.messages import get_messages
        
        self.client.login(username='statementuser', password='testpass123')
        response = self.client.get(self.csv_url + '?start_date=invalid-date')
        
        self.assertEqual(response.status_code, 302)  # Redirect to history
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Invalid start date format' in str(m) for m in messages))
    
    def test_pdf_download_all_transactions(self):
        """Test PDF download with all transactions."""
        self.client.login(username='statementuser', password='testpass123')
        response = self.client.get(self.pdf_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn(f'account-{self.account.account_number}', response['Content-Disposition'])
        self.assertIn('.pdf', response['Content-Disposition'])
        
        # Check that we got PDF content (starts with PDF header)
        self.assertTrue(response.content.startswith(b'%PDF'))
    
    def test_pdf_download_with_date_filter(self):
        """Test PDF download with date range filtering."""
        from django.utils import timezone
        from datetime import timedelta
        
        self.client.login(username='statementuser', password='testpass123')
        
        # Filter for last 7 days
        now = timezone.now()
        start_date = (now - timedelta(days=7)).strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
        response = self.client.get(
            self.pdf_url + f'?start_date={start_date}&end_date={end_date}'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        
        # Check filename includes date range
        self.assertIn(f'from-{start_date}', response['Content-Disposition'])
        self.assertIn(f'to-{end_date}', response['Content-Disposition'])
        
        # Check that we got PDF content
        self.assertTrue(response.content.startswith(b'%PDF'))
    
    def test_pdf_download_no_transactions(self):
        """Test PDF download when no transactions match filter."""
        self.client.login(username='statementuser', password='testpass123')
        
        # Filter for future dates (no transactions)
        response = self.client.get(
            self.pdf_url + '?start_date=2030-01-01&end_date=2030-12-31'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        
        # Should still generate PDF even with no transactions
        self.assertTrue(response.content.startswith(b'%PDF'))
    
    def test_csv_filename_generation(self):
        """Test CSV filename generation with different parameters."""
        self.client.login(username='statementuser', password='testpass123')
        
        # Test with start date only
        response = self.client.get(self.csv_url + '?start_date=2024-01-01')
        self.assertIn('from-2024-01-01', response['Content-Disposition'])
        self.assertIn(f'account-{self.account.account_number}', response['Content-Disposition'])
        
        # Test with end date only
        response = self.client.get(self.csv_url + '?end_date=2024-12-31')
        self.assertIn('to-2024-12-31', response['Content-Disposition'])
        
        # Test with both dates
        response = self.client.get(self.csv_url + '?start_date=2024-01-01&end_date=2024-12-31')
        self.assertIn('from-2024-01-01', response['Content-Disposition'])
        self.assertIn('to-2024-12-31', response['Content-Disposition'])
    
    def test_pdf_filename_generation(self):
        """Test PDF filename generation with different parameters."""
        self.client.login(username='statementuser', password='testpass123')
        
        # Test with start date only
        response = self.client.get(self.pdf_url + '?start_date=2024-01-01')
        self.assertIn('from-2024-01-01', response['Content-Disposition'])
        self.assertIn(f'account-{self.account.account_number}', response['Content-Disposition'])
        self.assertIn('.pdf', response['Content-Disposition'])
        
        # Test with end date only
        response = self.client.get(self.pdf_url + '?end_date=2024-12-31')
        self.assertIn('to-2024-12-31', response['Content-Disposition'])
        
        # Test with both dates
        response = self.client.get(self.pdf_url + '?start_date=2024-01-01&end_date=2024-12-31')
        self.assertIn('from-2024-01-01', response['Content-Disposition'])
        self.assertIn('to-2024-12-31', response['Content-Disposition'])
    
    def test_csv_transaction_formatting(self):
        """Test CSV transaction data formatting."""
        self.client.login(username='statementuser', password='testpass123')
        response = self.client.get(self.csv_url)
        
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        
        # Check that amounts are properly formatted
        for line in lines[1:]:  # Skip header
            fields = line.split(',')
            if len(fields) >= 5:
                amount = fields[4]  # Amount field
                # Should be a valid decimal format
                try:
                    float(amount)
                except ValueError:
                    self.fail(f"Invalid amount format: {amount}")
    
    def test_transfer_transaction_in_statements(self):
        """Test that transfer transactions appear correctly in statements."""
        # Create another account for transfer
        user2 = User.objects.create_user(
            username='user2',
            password='testpass123'
        )
        account2 = BankAccount.objects.create(
            user=user2,
            account_type='current',
            balance=Decimal('500.00'),
            status='active'
        )
        
        # Create transfer transaction
        transfer_txn = Transaction.objects.create(
            transaction_type='transfer',
            amount=Decimal('150.00'),
            sender_account=self.account,
            receiver_account=account2,
            sender_balance_after=Decimal('850.00'),
            receiver_balance_after=Decimal('650.00'),
            description='Test transfer'
        )
        
        self.client.login(username='statementuser', password='testpass123')
        
        # Test CSV
        response = self.client.get(self.csv_url)
        content = response.content.decode('utf-8')
        
        # Should show transfer as outgoing (-150.00)
        self.assertIn('-150.00', content)
        self.assertIn(f'Transfer to {account2.account_number}', content)
        
        # Test from receiver's perspective
        self.client.login(username='user2', password='testpass123')
        csv_url_user2 = self.csv_url
        response = self.client.get(csv_url_user2)
        content = response.content.decode('utf-8')
        
        # Should show transfer as incoming (+150.00)
        self.assertIn('150.00', content)
        self.assertIn(f'Transfer from {self.account.account_number}', content)
    
    def test_statement_security(self):
        """Test that users can only download their own statements."""
        # Create another user
        user2 = User.objects.create_user(
            username='otheruser',
            password='testpass123'
        )
        account2 = BankAccount.objects.create(
            user=user2,
            account_type='current',
            balance=Decimal('500.00'),
            status='active'
        )
        
        # Create transaction for user2
        Transaction.objects.create(
            transaction_type='deposit',
            amount=Decimal('100.00'),
            receiver_account=account2,
            receiver_balance_after=Decimal('600.00'),
            description='Other user deposit'
        )
        
        # Login as first user
        self.client.login(username='statementuser', password='testpass123')
        response = self.client.get(self.csv_url)
        
        content = response.content.decode('utf-8')
        
        # Should not contain other user's transactions
        self.assertNotIn('Other user deposit', content)
        self.assertNotIn(account2.account_number, content)
        
        # Should only contain own account transactions
        self.assertIn(self.account.account_number, response['Content-Disposition'])
        self.assertIn('Salary deposit', content)  # Own transaction