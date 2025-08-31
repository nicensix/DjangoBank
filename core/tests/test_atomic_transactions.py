"""
Tests for atomic transaction processing and concurrent transaction handling.
"""

import threading
import time
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.db import transaction
from django.contrib.auth import get_user_model
from accounts.models import BankAccount
from transactions.models import Transaction
from core.transaction_utils import (
    BankingTransactionManager, TransactionError, 
    InsufficientFundsError, AccountNotActiveError, 
    ConcurrentTransactionError, ConcurrentTransactionTester
)

User = get_user_model()


class AtomicTransactionTest(TestCase):
    """Test atomic transaction processing."""
    
    def setUp(self):
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
            balance=Decimal('1000.00'),
            status='active'
        )
        
        self.recipient_user = User.objects.create_user(
            username='recipient',
            email='recipient@example.com',
            password='TestPass123!',
            first_name='Recipient',
            last_name='User'
        )
        
        self.recipient_account = BankAccount.objects.create(
            user=self.recipient_user,
            account_type='savings',
            balance=Decimal('500.00'),
            status='active'
        )
    
    def test_atomic_deposit_success(self):
        """Test successful atomic deposit."""
        initial_balance = self.account.balance
        deposit_amount = Decimal('100.00')
        
        transaction_record = BankingTransactionManager.process_deposit(
            self.account.account_number,
            deposit_amount,
            'Test deposit'
        )
        
        # Refresh account
        self.account.refresh_from_db()
        
        # Verify balance updated correctly
        self.assertEqual(self.account.balance, initial_balance + deposit_amount)
        
        # Verify transaction record created
        self.assertIsNotNone(transaction_record)
        self.assertEqual(transaction_record.transaction_type, 'deposit')
        self.assertEqual(transaction_record.amount, deposit_amount)
        self.assertEqual(transaction_record.receiver_account, self.account)
        self.assertEqual(transaction_record.receiver_balance_after, self.account.balance)
    
    def test_atomic_deposit_invalid_amount(self):
        """Test deposit with invalid amount."""
        with self.assertRaises(TransactionError):
            BankingTransactionManager.process_deposit(
                self.account.account_number,
                Decimal('-100.00'),  # Negative amount
                'Invalid deposit'
            )
        
        with self.assertRaises(TransactionError):
            BankingTransactionManager.process_deposit(
                self.account.account_number,
                Decimal('0.00'),  # Zero amount
                'Invalid deposit'
            )
    
    def test_atomic_deposit_inactive_account(self):
        """Test deposit to inactive account."""
        self.account.status = 'frozen'
        self.account.save()
        
        with self.assertRaises(TransactionError):
            BankingTransactionManager.process_deposit(
                self.account.account_number,
                Decimal('100.00'),
                'Test deposit'
            )
    
    def test_atomic_withdrawal_success(self):
        """Test successful atomic withdrawal."""
        initial_balance = self.account.balance
        withdrawal_amount = Decimal('200.00')
        
        transaction_record = BankingTransactionManager.process_withdrawal(
            self.account.account_number,
            withdrawal_amount,
            'Test withdrawal'
        )
        
        # Refresh account
        self.account.refresh_from_db()
        
        # Verify balance updated correctly
        self.assertEqual(self.account.balance, initial_balance - withdrawal_amount)
        
        # Verify transaction record created
        self.assertIsNotNone(transaction_record)
        self.assertEqual(transaction_record.transaction_type, 'withdrawal')
        self.assertEqual(transaction_record.amount, withdrawal_amount)
        self.assertEqual(transaction_record.sender_account, self.account)
        self.assertEqual(transaction_record.sender_balance_after, self.account.balance)
    
    def test_atomic_withdrawal_insufficient_funds(self):
        """Test withdrawal with insufficient funds."""
        with self.assertRaises(InsufficientFundsError):
            BankingTransactionManager.process_withdrawal(
                self.account.account_number,
                Decimal('2000.00'),  # More than available balance
                'Insufficient funds test'
            )
        
        # Verify balance unchanged
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('1000.00'))
    
    def test_atomic_transfer_success(self):
        """Test successful atomic transfer."""
        sender_initial = self.account.balance
        recipient_initial = self.recipient_account.balance
        transfer_amount = Decimal('300.00')
        
        transaction_record = BankingTransactionManager.process_transfer(
            self.account.account_number,
            self.recipient_account.account_number,
            transfer_amount,
            'Test transfer'
        )
        
        # Refresh accounts
        self.account.refresh_from_db()
        self.recipient_account.refresh_from_db()
        
        # Verify balances updated correctly
        self.assertEqual(self.account.balance, sender_initial - transfer_amount)
        self.assertEqual(self.recipient_account.balance, recipient_initial + transfer_amount)
        
        # Verify transaction record created
        self.assertIsNotNone(transaction_record)
        self.assertEqual(transaction_record.transaction_type, 'transfer')
        self.assertEqual(transaction_record.amount, transfer_amount)
        self.assertEqual(transaction_record.sender_account, self.account)
        self.assertEqual(transaction_record.receiver_account, self.recipient_account)
        self.assertEqual(transaction_record.sender_balance_after, self.account.balance)
        self.assertEqual(transaction_record.receiver_balance_after, self.recipient_account.balance)
    
    def test_atomic_transfer_insufficient_funds(self):
        """Test transfer with insufficient funds."""
        sender_initial = self.account.balance
        recipient_initial = self.recipient_account.balance
        
        with self.assertRaises(InsufficientFundsError):
            BankingTransactionManager.process_transfer(
                self.account.account_number,
                self.recipient_account.account_number,
                Decimal('2000.00'),  # More than available balance
                'Insufficient funds transfer'
            )
        
        # Verify balances unchanged
        self.account.refresh_from_db()
        self.recipient_account.refresh_from_db()
        self.assertEqual(self.account.balance, sender_initial)
        self.assertEqual(self.recipient_account.balance, recipient_initial)
    
    def test_atomic_transfer_same_account(self):
        """Test transfer to same account."""
        with self.assertRaises(TransactionError):
            BankingTransactionManager.process_transfer(
                self.account.account_number,
                self.account.account_number,  # Same account
                Decimal('100.00'),
                'Same account transfer'
            )
    
    def test_account_locking(self):
        """Test account locking mechanism."""
        # Test single account lock
        locked_account = BankingTransactionManager.lock_account_for_update(
            self.account.account_number
        )
        self.assertEqual(locked_account.id, self.account.id)
        
        # Test multiple account lock
        locked_accounts = BankingTransactionManager.lock_multiple_accounts_for_update([
            self.account.account_number,
            self.recipient_account.account_number
        ])
        
        self.assertIn(self.account.account_number, locked_accounts)
        self.assertIn(self.recipient_account.account_number, locked_accounts)
        self.assertEqual(locked_accounts[self.account.account_number].id, self.account.id)
        self.assertEqual(locked_accounts[self.recipient_account.account_number].id, self.recipient_account.id)
    
    def test_transaction_integrity_validation(self):
        """Test transaction integrity validation."""
        # Create a deposit transaction
        transaction_record = BankingTransactionManager.process_deposit(
            self.account.account_number,
            Decimal('100.00'),
            'Integrity test deposit'
        )
        
        # Validate transaction integrity
        is_valid = BankingTransactionManager.validate_transaction_integrity(
            transaction_record.id
        )
        self.assertTrue(is_valid)
        
        # Test with non-existent transaction
        is_valid = BankingTransactionManager.validate_transaction_integrity(99999)
        self.assertFalse(is_valid)


class ConcurrentTransactionTest(TransactionTestCase):
    """Test concurrent transaction scenarios."""
    
    def setUp(self):
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
            balance=Decimal('1000.00'),
            status='active'
        )
        
        self.recipient_user = User.objects.create_user(
            username='recipient',
            email='recipient@example.com',
            password='TestPass123!',
            first_name='Recipient',
            last_name='User'
        )
        
        self.recipient_account = BankAccount.objects.create(
            user=self.recipient_user,
            account_type='savings',
            balance=Decimal('500.00'),
            status='active'
        )
    
    def test_concurrent_deposits(self):
        """Test concurrent deposits to the same account."""
        initial_balance = self.account.balance
        deposit_amounts = [Decimal('50.00'), Decimal('75.00'), Decimal('25.00')]
        
        results = []
        threads = []
        
        def deposit_worker(amount, result_list):
            try:
                transaction_record = BankingTransactionManager.process_deposit(
                    self.account.account_number,
                    amount,
                    f'Concurrent deposit {amount}'
                )
                result_list.append(('success', transaction_record))
            except Exception as e:
                result_list.append(('error', str(e)))
        
        # Create and start threads
        for amount in deposit_amounts:
            thread = threading.Thread(target=deposit_worker, args=(amount, results))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Some deposits should succeed, some might fail due to locking
        successful_deposits = [r for r in results if r[0] == 'success']
        failed_deposits = [r for r in results if r[0] == 'error']
        
        # At least one should succeed
        self.assertGreaterEqual(len(successful_deposits), 1)
        
        # Verify final balance is correct based on successful deposits
        self.account.refresh_from_db()
        total_deposited = sum(
            r[1].amount for r in successful_deposits
        )
        expected_balance = initial_balance + total_deposited
        self.assertEqual(self.account.balance, expected_balance)
    
    def test_concurrent_withdrawals(self):
        """Test concurrent withdrawals from the same account."""
        initial_balance = self.account.balance
        withdrawal_amounts = [Decimal('100.00'), Decimal('150.00'), Decimal('200.00')]
        
        results = []
        threads = []
        
        def withdrawal_worker(amount, result_list):
            try:
                transaction_record = BankingTransactionManager.process_withdrawal(
                    self.account.account_number,
                    amount,
                    f'Concurrent withdrawal {amount}'
                )
                result_list.append(('success', transaction_record))
            except Exception as e:
                result_list.append(('error', str(e)))
        
        # Create and start threads
        for amount in withdrawal_amounts:
            thread = threading.Thread(target=withdrawal_worker, args=(amount, results))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Some withdrawals should succeed, some might fail due to insufficient funds
        successful_withdrawals = [r for r in results if r[0] == 'success']
        failed_withdrawals = [r for r in results if r[0] == 'error']
        
        # At least one should succeed (the first one processed)
        self.assertGreaterEqual(len(successful_withdrawals), 1)
        
        # Verify balance is consistent
        self.account.refresh_from_db()
        self.assertGreaterEqual(self.account.balance, Decimal('0.00'))
        
        # Calculate expected balance based on successful withdrawals
        total_withdrawn = sum(
            r[1].amount for r in successful_withdrawals
        )
        expected_balance = initial_balance - total_withdrawn
        self.assertEqual(self.account.balance, expected_balance)
    
    def test_concurrent_transfers(self):
        """Test concurrent transfers between accounts."""
        sender_initial = self.account.balance
        recipient_initial = self.recipient_account.balance
        transfer_amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('150.00')]
        
        results = []
        threads = []
        
        def transfer_worker(amount, result_list):
            try:
                transaction_record = BankingTransactionManager.process_transfer(
                    self.account.account_number,
                    self.recipient_account.account_number,
                    amount,
                    f'Concurrent transfer {amount}'
                )
                result_list.append(('success', transaction_record))
            except Exception as e:
                result_list.append(('error', str(e)))
        
        # Create and start threads
        for amount in transfer_amounts:
            thread = threading.Thread(target=transfer_worker, args=(amount, results))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Some transfers should succeed, some might fail due to insufficient funds
        successful_transfers = [r for r in results if r[0] == 'success']
        failed_transfers = [r for r in results if r[0] == 'error']
        
        # At least one should succeed
        self.assertGreaterEqual(len(successful_transfers), 1)
        
        # Verify balances are consistent
        self.account.refresh_from_db()
        self.recipient_account.refresh_from_db()
        
        # Calculate expected balances based on successful transfers
        total_transferred = sum(
            r[1].amount for r in successful_transfers
        )
        
        expected_sender_balance = sender_initial - total_transferred
        expected_recipient_balance = recipient_initial + total_transferred
        
        self.assertEqual(self.account.balance, expected_sender_balance)
        self.assertEqual(self.recipient_account.balance, expected_recipient_balance)
    
    def test_deadlock_prevention(self):
        """Test that the locking mechanism prevents deadlocks."""
        # Create multiple accounts
        account1 = BankAccount.objects.create(
            user=self.user,
            account_type='current',
            balance=Decimal('1000.00'),
            status='active'
        )
        
        account2 = BankAccount.objects.create(
            user=self.recipient_user,
            account_type='current',
            balance=Decimal('1000.00'),
            status='active'
        )
        
        results = []
        threads = []
        
        def transfer_worker_1():
            try:
                # Transfer from account1 to account2
                transaction_record = BankingTransactionManager.process_transfer(
                    account1.account_number,
                    account2.account_number,
                    Decimal('100.00'),
                    'Deadlock test 1'
                )
                results.append(('success', 'transfer_1'))
            except Exception as e:
                results.append(('error', f'transfer_1: {str(e)}'))
        
        def transfer_worker_2():
            try:
                # Transfer from account2 to account1 (opposite direction)
                time.sleep(0.01)  # Small delay to increase chance of deadlock
                transaction_record = BankingTransactionManager.process_transfer(
                    account2.account_number,
                    account1.account_number,
                    Decimal('150.00'),
                    'Deadlock test 2'
                )
                results.append(('success', 'transfer_2'))
            except Exception as e:
                results.append(('error', f'transfer_2: {str(e)}'))
        
        # Start both transfers simultaneously
        thread1 = threading.Thread(target=transfer_worker_1)
        thread2 = threading.Thread(target=transfer_worker_2)
        
        thread1.start()
        thread2.start()
        
        # Wait for completion
        thread1.join(timeout=5)  # 5 second timeout
        thread2.join(timeout=5)
        
        # Both transfers should complete without deadlock
        self.assertEqual(len(results), 2)
        
        # At least one should succeed (both should succeed if no other issues)
        successful_results = [r for r in results if r[0] == 'success']
        self.assertGreaterEqual(len(successful_results), 1)
    
    def test_concurrent_transaction_tester(self):
        """Test the concurrent transaction testing utility."""
        # Test concurrent deposits
        deposit_amounts = [Decimal('50.00'), Decimal('75.00')]
        results = ConcurrentTransactionTester.simulate_concurrent_deposits(
            self.account.account_number,
            deposit_amounts,
            num_threads=2
        )
        
        # Should have results for both deposits
        self.assertEqual(len(results), 2)
        
        # Test concurrent transfers
        transfer_amounts = [Decimal('100.00'), Decimal('150.00')]
        results = ConcurrentTransactionTester.simulate_concurrent_transfers(
            self.account.account_number,
            self.recipient_account.account_number,
            transfer_amounts,
            num_threads=2
        )
        
        # Should have results for both transfers
        self.assertEqual(len(results), 2)


class TransactionRollbackTest(TestCase):
    """Test transaction rollback scenarios."""
    
    def setUp(self):
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
            balance=Decimal('1000.00'),
            status='active'
        )
    
    def test_rollback_on_exception(self):
        """Test that transactions are rolled back on exceptions."""
        initial_balance = self.account.balance
        initial_transaction_count = Transaction.objects.count()
        
        # Create a scenario that will cause an exception after balance update
        with self.assertRaises(Exception):
            with transaction.atomic():
                # This would normally update the balance
                self.account.balance += Decimal('100.00')
                self.account.save()
                
                # Force an exception
                raise Exception("Simulated error")
        
        # Verify rollback occurred
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, initial_balance)
        
        # Verify no transaction record was created
        self.assertEqual(Transaction.objects.count(), initial_transaction_count)
    
    def test_partial_rollback_in_transfer(self):
        """Test rollback when transfer partially fails."""
        # This test simulates a scenario where the sender account is updated
        # but the recipient account update fails, ensuring proper rollback
        
        recipient_user = User.objects.create_user(
            username='recipient',
            email='recipient@example.com',
            password='TestPass123!'
        )
        
        recipient_account = BankAccount.objects.create(
            user=recipient_user,
            account_type='savings',
            balance=Decimal('500.00'),
            status='active'
        )
        
        sender_initial = self.account.balance
        recipient_initial = recipient_account.balance
        
        # Delete recipient account to simulate failure
        recipient_account_number = recipient_account.account_number
        recipient_account.delete()
        
        with self.assertRaises(Exception):
            BankingTransactionManager.process_transfer(
                self.account.account_number,
                recipient_account_number,
                Decimal('100.00'),
                'Rollback test transfer'
            )
        
        # Verify sender balance unchanged due to rollback
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, sender_initial)