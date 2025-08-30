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
