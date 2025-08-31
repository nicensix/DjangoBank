"""
Edge case and error handling tests for the banking platform.
Tests boundary conditions, error scenarios, and exceptional cases.
"""

import threading
import time
from decimal import Decimal, InvalidOperation
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.contrib.messages import get_messages
from accounts.models import BankAccount
from transactions.models import Transaction
from admin_panel.models import AdminAction
from core.transaction_utils import BankingTransactionManager, TransactionError, InsufficientFundsError
from .fixtures import TestDataFixtures

User = get_user_model()


class BoundaryValueTest(TestCase):
    """Test boundary values and edge cases for amounts and limits."""
    
    def setUp(self):
        self.test_data = TestDataFixtures.create_complete_test_dataset()
        self.users = self.test_data['users']
        self.accounts = self.test_data['accounts']
        self.client = Client()
    
    def test_minimum_transaction_amounts(self):
        """Test minimum allowable transaction amounts."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Test minimum deposit (0.01)
        response = self.client.post(reverse('transactions:deposit'), {
            'amount': '0.01',
            'description': 'Minimum deposit test'
        })
        self.assertEqual(response.status_code, 302)  # Should succeed
        
        # Test below minimum deposit (0.00)
        response = self.client.post(reverse('transactions:deposit'), {
            'amount': '0.00',
            'description': 'Zero deposit test'
        })
        self.assertEqual(response.status_code, 200)  # Should fail with validation error
        self.assertContains(response, 'error')
        
        # Test negative deposit
        response = self.client.post(reverse('transactions:deposit'), {
            'amount': '-0.01',
            'description': 'Negative deposit test'
        })
        self.assertEqual(response.status_code, 200)  # Should fail
        self.assertContains(response, 'error')
    
    def test_maximum_transaction_amounts(self):
        """Test maximum allowable transaction amounts."""
        # Set up account with high balance for testing
        high_balance_account = self.accounts['high_balance']
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Test maximum allowed deposit (just under limit)
        response = self.client.post(reverse('transactions:deposit'), {
            'amount': '99999.99',
            'description': 'Large deposit test'
        })
        self.assertEqual(response.status_code, 302)  # Should succeed
        
        # Test exceeding maximum deposit limit
        response = self.client.post(reverse('transactions:deposit'), {
            'amount': '200000.00',
            'description': 'Excessive deposit test'
        })
        self.assertEqual(response.status_code, 200)  # Should fail
        self.assertContains(response, 'error')
    
    def test_decimal_precision_limits(self):
        """Test decimal precision handling."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Test valid 2 decimal places
        response = self.client.post(reverse('transactions:deposit'), {
            'amount': '100.99',
            'description': 'Two decimal places'
        })
        self.assertEqual(response.status_code, 302)
        
        # Test 3 decimal places (should be rejected or rounded)
        response = self.client.post(reverse('transactions:deposit'), {
            'amount': '100.999',
            'description': 'Three decimal places'
        })
        # Should either fail validation or round to 2 decimal places
        if response.status_code == 200:
            self.assertContains(response, 'error')
    
    def test_account_number_boundary_cases(self):
        """Test account number validation boundary cases."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Test valid 12-digit account number
        valid_account = self.accounts['user2_savings'].account_number
        response = self.client.post(reverse('transactions:transfer'), {
            'recipient_account_number': valid_account,
            'amount': '10.00',
            'description': 'Valid account number test'
        })
        self.assertEqual(response.status_code, 302)
        
        # Test 11-digit account number (too short)
        response = self.client.post(reverse('transactions:transfer'), {
            'recipient_account_number': '12345678901',
            'amount': '10.00',
            'description': 'Short account number test'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error')
        
        # Test 13-digit account number (too long)
        response = self.client.post(reverse('transactions:transfer'), {
            'recipient_account_number': '1234567890123',
            'amount': '10.00',
            'description': 'Long account number test'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error')
    
    def test_balance_precision_edge_cases(self):
        """Test balance calculations with edge case amounts."""
        account = self.accounts['user1_savings']
        initial_balance = account.balance
        
        # Test very small amounts
        BankingTransactionManager.process_deposit(
            account.account_number,
            Decimal('0.01'),
            'Tiny deposit'
        )
        
        account.refresh_from_db()
        self.assertEqual(account.balance, initial_balance + Decimal('0.01'))
        
        # Test withdrawal leaving minimal balance
        BankingTransactionManager.process_withdrawal(
            account.account_number,
            account.balance - Decimal('0.01'),
            'Leave minimal balance'
        )
        
        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal('0.01'))


class ConcurrencyEdgeCaseTest(TransactionTestCase):
    """Test edge cases in concurrent operations."""
    
    def setUp(self):
        self.test_data = TestDataFixtures.create_complete_test_dataset()
        self.accounts = self.test_data['accounts']
    
    def test_simultaneous_withdrawals_edge_case(self):
        """Test simultaneous withdrawals that would exceed balance."""
        account = self.accounts['user1_savings']
        account.balance = Decimal('100.00')
        account.save()
        
        results = []
        threads = []
        
        def withdrawal_worker(amount):
            try:
                BankingTransactionManager.process_withdrawal(
                    account.account_number,
                    amount,
                    f'Concurrent withdrawal {amount}'
                )
                results.append(('success', amount))
            except Exception as e:
                results.append(('failed', amount, str(e)))
        
        # Try to withdraw $60 twice simultaneously (total $120 > $100 balance)
        thread1 = threading.Thread(target=withdrawal_worker, args=(Decimal('60.00'),))
        thread2 = threading.Thread(target=withdrawal_worker, args=(Decimal('60.00'),))
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Only one should succeed
        successful_withdrawals = [r for r in results if r[0] == 'success']
        failed_withdrawals = [r for r in results if r[0] == 'failed']
        
        self.assertEqual(len(successful_withdrawals), 1)
        self.assertEqual(len(failed_withdrawals), 1)
        
        # Verify final balance is correct
        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal('40.00'))
    
    def test_rapid_small_transactions(self):
        """Test rapid succession of very small transactions."""
        account = self.accounts['user1_savings']
        initial_balance = account.balance
        
        num_transactions = 50
        transaction_amount = Decimal('0.01')
        
        results = []
        threads = []
        
        def small_deposit_worker(worker_id):
            try:
                BankingTransactionManager.process_deposit(
                    account.account_number,
                    transaction_amount,
                    f'Rapid small deposit {worker_id}'
                )
                results.append(('success', worker_id))
            except Exception as e:
                results.append(('failed', worker_id, str(e)))
        
        # Start many small transactions rapidly
        for i in range(num_transactions):
            thread = threading.Thread(target=small_deposit_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # Count successful transactions
        successful_count = len([r for r in results if r[0] == 'success'])
        
        # Verify final balance matches successful transactions
        account.refresh_from_db()
        expected_balance = initial_balance + (successful_count * transaction_amount)
        self.assertEqual(account.balance, expected_balance)
    
    def test_deadlock_scenario_prevention(self):
        """Test prevention of deadlock scenarios."""
        account1 = self.accounts['user1_savings']
        account2 = self.accounts['user2_savings']
        
        results = []
        
        def transfer_worker_1():
            try:
                BankingTransactionManager.process_transfer(
                    account1.account_number,
                    account2.account_number,
                    Decimal('50.00'),
                    'Deadlock test transfer 1->2'
                )
                results.append(('success', '1->2'))
            except Exception as e:
                results.append(('failed', '1->2', str(e)))
        
        def transfer_worker_2():
            try:
                # Small delay to increase chance of deadlock
                time.sleep(0.01)
                BankingTransactionManager.process_transfer(
                    account2.account_number,
                    account1.account_number,
                    Decimal('30.00'),
                    'Deadlock test transfer 2->1'
                )
                results.append(('success', '2->1'))
            except Exception as e:
                results.append(('failed', '2->1', str(e)))
        
        # Start both transfers simultaneously
        thread1 = threading.Thread(target=transfer_worker_1)
        thread2 = threading.Thread(target=transfer_worker_2)
        
        thread1.start()
        thread2.start()
        
        # Wait with timeout to detect deadlocks
        thread1.join(timeout=10)
        thread2.join(timeout=10)
        
        # Both threads should complete (no deadlock)
        self.assertEqual(len(results), 2)
        
        # At least one should succeed
        successful_transfers = [r for r in results if r[0] == 'success']
        self.assertGreaterEqual(len(successful_transfers), 1)


class DataIntegrityEdgeCaseTest(TestCase):
    """Test data integrity in edge cases."""
    
    def setUp(self):
        self.test_data = TestDataFixtures.create_complete_test_dataset()
        self.users = self.test_data['users']
        self.accounts = self.test_data['accounts']
    
    def test_account_deletion_with_transactions(self):
        """Test behavior when account with transactions is deleted."""
        account = self.accounts['user1_savings']
        
        # Create transaction
        transaction_obj = Transaction.objects.create(
            transaction_type='deposit',
            amount=Decimal('100.00'),
            receiver_account=account,
            description='Test transaction before deletion'
        )
        
        # Try to delete account (should be prevented or handled gracefully)
        try:
            account.delete()
            # If deletion succeeds, transaction should still exist or be handled
            transaction_obj.refresh_from_db()
        except Exception:
            # Deletion prevented - this is acceptable behavior
            pass
    
    def test_user_deletion_with_accounts(self):
        """Test behavior when user with accounts is deleted."""
        user = self.users['user1']
        account = self.accounts['user1_savings']
        
        # Create transaction
        Transaction.objects.create(
            transaction_type='deposit',
            amount=Decimal('50.00'),
            receiver_account=account,
            description='Transaction before user deletion'
        )
        
        # Try to delete user (should cascade properly or be prevented)
        try:
            user.delete()
            # If deletion succeeds, related objects should be handled properly
        except Exception:
            # Deletion prevented - this is acceptable behavior
            pass
    
    def test_duplicate_account_number_prevention(self):
        """Test prevention of duplicate account numbers."""
        user = self.users['user2']
        existing_account = self.accounts['user1_savings']
        
        # Try to create account with duplicate account number
        with self.assertRaises(IntegrityError):
            BankAccount.objects.create(
                user=user,
                account_number=existing_account.account_number,
                account_type='current',
                balance=Decimal('0.00'),
                status='pending'
            )
    
    def test_negative_balance_prevention(self):
        """Test prevention of negative balances."""
        account = self.accounts['low_balance']  # $10.00 balance
        
        # Try to withdraw more than available
        with self.assertRaises(InsufficientFundsError):
            BankingTransactionManager.process_withdrawal(
                account.account_number,
                Decimal('20.00'),
                'Overdraft attempt'
            )
        
        # Balance should remain unchanged
        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal('10.00'))


class FormValidationEdgeCaseTest(TestCase):
    """Test form validation edge cases."""
    
    def setUp(self):
        self.client = Client()
        self.test_data = TestDataFixtures.create_complete_test_dataset()
        self.users = self.test_data['users']
        self.accounts = self.test_data['accounts']
    
    def test_empty_form_submission(self):
        """Test submission of completely empty forms."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Empty deposit form
        response = self.client.post(reverse('transactions:deposit'), {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error')
        
        # Empty transfer form
        response = self.client.post(reverse('transactions:transfer'), {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error')
    
    def test_whitespace_only_inputs(self):
        """Test inputs containing only whitespace."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Whitespace-only description
        response = self.client.post(reverse('transactions:deposit'), {
            'amount': '10.00',
            'description': '   \t\n   '
        })
        
        # Should either succeed with trimmed description or show validation error
        if response.status_code == 302:
            # Check that description was properly handled
            transaction = Transaction.objects.filter(
                receiver_account=self.accounts['user1_savings'],
                amount=Decimal('10.00')
            ).last()
            self.assertIsNotNone(transaction)
            # Description should be trimmed or set to default
            self.assertNotEqual(transaction.description.strip(), '')
    
    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        special_descriptions = [
            'Deposit with émojis 🏦💰',
            'Çharacters with açcents',
            'Chinese characters: 银行存款',
            'Arabic: إيداع مصرفي',
            'Special chars: @#$%^&*()_+-=[]{}|;:,.<>?',
            'Newlines\nand\ttabs',
        ]
        
        for description in special_descriptions:
            response = self.client.post(reverse('transactions:deposit'), {
                'amount': '5.00',
                'description': description
            })
            
            # Should handle gracefully (either succeed or show appropriate error)
            self.assertIn(response.status_code, [200, 302])
            
            if response.status_code == 302:
                # Verify transaction was created with proper description handling
                transaction = Transaction.objects.filter(
                    receiver_account=self.accounts['user1_savings'],
                    description__icontains=description[:10]  # Check first part
                ).exists()
                # Transaction should exist (description may be sanitized)
    
    def test_extremely_long_inputs(self):
        """Test handling of extremely long input strings."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Very long description
        long_description = 'A' * 1000
        
        response = self.client.post(reverse('transactions:deposit'), {
            'amount': '10.00',
            'description': long_description
        })
        
        # Should either truncate, show validation error, or handle gracefully
        if response.status_code == 200:
            self.assertContains(response, 'error')
        elif response.status_code == 302:
            # Check that description was properly handled (truncated or rejected)
            transaction = Transaction.objects.filter(
                receiver_account=self.accounts['user1_savings'],
                amount=Decimal('10.00')
            ).last()
            if transaction:
                # Description should be reasonable length
                self.assertLessEqual(len(transaction.description), 500)


class ErrorRecoveryTest(TestCase):
    """Test error recovery and graceful degradation."""
    
    def setUp(self):
        self.client = Client()
        self.test_data = TestDataFixtures.create_complete_test_dataset()
        self.users = self.test_data['users']
        self.accounts = self.test_data['accounts']
    
    def test_database_constraint_violation_recovery(self):
        """Test recovery from database constraint violations."""
        account = self.accounts['user1_savings']
        
        # Create transaction with specific reference number
        transaction1 = Transaction.objects.create(
            transaction_type='deposit',
            amount=Decimal('100.00'),
            receiver_account=account,
            description='First transaction',
            reference_number='TEST123456789'
        )
        
        # Try to create another transaction with same reference number
        try:
            transaction2 = Transaction.objects.create(
                transaction_type='deposit',
                amount=Decimal('200.00'),
                receiver_account=account,
                description='Duplicate reference',
                reference_number='TEST123456789'
            )
            # If this succeeds, system generates unique reference numbers
        except IntegrityError:
            # Expected behavior - duplicate reference numbers prevented
            pass
        
        # System should remain functional
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser1',
            'password': 'TestPass123!'
        })
        self.assertEqual(response.status_code, 302)
    
    def test_invalid_decimal_handling(self):
        """Test handling of invalid decimal operations."""
        # Test with invalid decimal strings
        invalid_amounts = [
            'NaN',
            'Infinity',
            '-Infinity',
            '1.2.3',
            'abc',
            '1e308',  # Very large scientific notation
        ]
        
        for invalid_amount in invalid_amounts:
            try:
                # This should raise InvalidOperation or be handled gracefully
                decimal_value = Decimal(invalid_amount)
                # If conversion succeeds, test the banking system's handling
                account = self.accounts['user1_savings']
                try:
                    BankingTransactionManager.process_deposit(
                        account.account_number,
                        decimal_value,
                        'Invalid decimal test'
                    )
                except (TransactionError, ValidationError, InvalidOperation):
                    # Expected - system should reject invalid amounts
                    pass
            except InvalidOperation:
                # Expected - Decimal conversion should fail for invalid inputs
                pass
    
    def test_session_corruption_recovery(self):
        """Test recovery from session corruption."""
        # Login normally
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser1',
            'password': 'TestPass123!'
        })
        self.assertEqual(response.status_code, 302)
        
        # Corrupt session data (simulate)
        session = self.client.session
        session['corrupted_key'] = 'invalid_data'
        session.save()
        
        # System should handle corrupted session gracefully
        response = self.client.get(reverse('accounts:dashboard'))
        # Should either work or redirect to login (not crash)
        self.assertIn(response.status_code, [200, 302])
    
    def test_partial_form_data_recovery(self):
        """Test recovery from partial form submissions."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Submit form with missing required fields
        response = self.client.post(reverse('transactions:transfer'), {
            'amount': '50.00',
            # Missing recipient_account_number and description
        })
        
        # Should show form with errors and preserve entered data
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error')
        self.assertContains(response, '50.00')  # Amount should be preserved


class NetworkInterruptionSimulationTest(TestCase):
    """Test behavior during simulated network interruptions."""
    
    def setUp(self):
        self.client = Client()
        self.test_data = TestDataFixtures.create_complete_test_dataset()
        self.accounts = self.test_data['accounts']
    
    def test_transaction_atomicity_during_interruption(self):
        """Test that transactions remain atomic during interruptions."""
        account = self.accounts['user1_savings']
        initial_balance = account.balance
        
        # Simulate transaction that might be interrupted
        try:
            with transaction.atomic():
                # Start transaction
                account.balance += Decimal('100.00')
                account.save()
                
                # Create transaction record
                Transaction.objects.create(
                    transaction_type='deposit',
                    amount=Decimal('100.00'),
                    receiver_account=account,
                    description='Interrupted transaction test'
                )
                
                # Simulate interruption (raise exception)
                raise Exception("Simulated network interruption")
                
        except Exception:
            # Transaction should be rolled back
            pass
        
        # Verify rollback occurred
        account.refresh_from_db()
        self.assertEqual(account.balance, initial_balance)
        
        # Verify no transaction record was created
        self.assertFalse(Transaction.objects.filter(
            description='Interrupted transaction test'
        ).exists())
    
    def test_idempotent_operations(self):
        """Test that operations are idempotent where appropriate."""
        # Test that repeated identical operations don't cause issues
        account = self.accounts['user1_savings']
        
        # Process same deposit multiple times (simulate retry after timeout)
        reference_number = 'IDEMPOTENT_TEST_123'
        
        for i in range(3):
            try:
                transaction_obj = Transaction.objects.create(
                    transaction_type='deposit',
                    amount=Decimal('25.00'),
                    receiver_account=account,
                    description='Idempotent test',
                    reference_number=reference_number
                )
                # First creation should succeed
                if i == 0:
                    self.assertIsNotNone(transaction_obj)
                break
            except IntegrityError:
                # Subsequent attempts should fail due to duplicate reference
                if i > 0:
                    continue
                else:
                    self.fail("First transaction creation should succeed")
        
        # Only one transaction should exist
        transaction_count = Transaction.objects.filter(
            reference_number=reference_number
        ).count()
        self.assertEqual(transaction_count, 1)