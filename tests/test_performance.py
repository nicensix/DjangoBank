"""
Performance tests for the banking platform.
Tests concurrent transaction processing, database query optimization, and load handling.
"""

import time
import threading
from decimal import Decimal
from django.test import TestCase, TransactionTestCase, Client
from django.test.utils import override_settings
from django.db import connection, transaction
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache
from accounts.models import BankAccount
from transactions.models import Transaction
from core.transaction_utils import BankingTransactionManager
from .fixtures import TestDataFixtures, TestScenarios

User = get_user_model()


class DatabaseQueryOptimizationTest(TestCase):
    """Test database query optimization and efficiency."""
    
    def setUp(self):
        self.test_data = TestDataFixtures.create_complete_test_dataset()
        self.users = self.test_data['users']
        self.accounts = self.test_data['accounts']
    
    def test_dashboard_query_efficiency(self):
        """Test that dashboard queries are optimized."""
        client = Client()
        client.login(username='testuser1', password='TestPass123!')
        
        # Reset query count
        connection.queries_log.clear()
        
        # Access dashboard
        response = client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Check number of queries (should be minimal)
        query_count = len(connection.queries)
        self.assertLessEqual(query_count, 5, f"Dashboard uses {query_count} queries, should be <= 5")
    
    def test_transaction_history_query_efficiency(self):
        """Test that transaction history queries are optimized."""
        # Create multiple transactions for testing
        account = self.accounts['user1_savings']
        for i in range(20):
            Transaction.objects.create(
                transaction_type='deposit',
                amount=Decimal(f'{10 + i}.00'),
                receiver_account=account,
                description=f'Test deposit {i}'
            )
        
        client = Client()
        client.login(username='testuser1', password='TestPass123!')
        
        # Reset query count
        connection.queries_log.clear()
        
        # Access transaction history
        response = client.get(reverse('transactions:history'))
        self.assertEqual(response.status_code, 200)
        
        # Check number of queries (should use select_related/prefetch_related)
        query_count = len(connection.queries)
        self.assertLessEqual(query_count, 3, f"Transaction history uses {query_count} queries, should be <= 3")
    
    def test_admin_dashboard_query_efficiency(self):
        """Test that admin dashboard queries are optimized."""
        client = Client()
        client.login(username='adminuser', password='AdminPass123!')
        
        # Reset query count
        connection.queries_log.clear()
        
        # Access admin dashboard
        response = client.get(reverse('admin_panel:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Check number of queries
        query_count = len(connection.queries)
        self.assertLessEqual(query_count, 10, f"Admin dashboard uses {query_count} queries, should be <= 10")
    
    def test_bulk_transaction_processing(self):
        """Test performance of bulk transaction processing."""
        account = self.accounts['user1_savings']
        
        start_time = time.time()
        
        # Process multiple transactions
        for i in range(50):
            BankingTransactionManager.process_deposit(
                account.account_number,
                Decimal('10.00'),
                f'Bulk deposit {i}'
            )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should process 50 transactions in reasonable time (< 5 seconds)
        self.assertLess(processing_time, 5.0, f"Bulk processing took {processing_time:.2f}s, should be < 5s")
        
        # Verify all transactions were processed
        transaction_count = Transaction.objects.filter(
            receiver_account=account,
            description__startswith='Bulk deposit'
        ).count()
        self.assertEqual(transaction_count, 50)
    
    def test_large_dataset_query_performance(self):
        """Test query performance with large datasets."""
        # Create a large number of transactions
        account = self.accounts['user1_savings']
        
        # Bulk create transactions for performance
        transactions = []
        for i in range(1000):
            transactions.append(Transaction(
                transaction_type='deposit',
                amount=Decimal('1.00'),
                receiver_account=account,
                description=f'Large dataset test {i}'
            ))
        
        Transaction.objects.bulk_create(transactions)
        
        # Test query performance
        start_time = time.time()
        
        # Query with pagination
        recent_transactions = Transaction.objects.filter(
            receiver_account=account
        ).select_related('sender_account', 'receiver_account')[:50]
        
        # Force evaluation
        list(recent_transactions)
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Should complete query in reasonable time
        self.assertLess(query_time, 1.0, f"Large dataset query took {query_time:.2f}s, should be < 1s")


class ConcurrentTransactionPerformanceTest(TransactionTestCase):
    """Test performance under concurrent transaction load."""
    
    def setUp(self):
        self.test_data = TestDataFixtures.create_complete_test_dataset()
        self.users = self.test_data['users']
        self.accounts = self.test_data['accounts']
    
    def test_concurrent_deposit_performance(self):
        """Test performance of concurrent deposits."""
        account = self.accounts['user1_savings']
        initial_balance = account.balance
        
        num_threads = 10
        deposits_per_thread = 5
        deposit_amount = Decimal('10.00')
        
        results = []
        threads = []
        
        def deposit_worker():
            worker_results = []
            for i in range(deposits_per_thread):
                start_time = time.time()
                try:
                    BankingTransactionManager.process_deposit(
                        account.account_number,
                        deposit_amount,
                        f'Concurrent deposit {threading.current_thread().ident}-{i}'
                    )
                    end_time = time.time()
                    worker_results.append(('success', end_time - start_time))
                except Exception as e:
                    end_time = time.time()
                    worker_results.append(('error', end_time - start_time, str(e)))
            results.extend(worker_results)
        
        # Start concurrent deposits
        start_time = time.time()
        
        for _ in range(num_threads):
            thread = threading.Thread(target=deposit_worker)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results
        successful_deposits = [r for r in results if r[0] == 'success']
        failed_deposits = [r for r in results if r[0] == 'error']
        
        # At least 80% should succeed
        success_rate = len(successful_deposits) / len(results)
        self.assertGreaterEqual(success_rate, 0.8, f"Success rate {success_rate:.2%} should be >= 80%")
        
        # Average transaction time should be reasonable
        if successful_deposits:
            avg_time = sum(r[1] for r in successful_deposits) / len(successful_deposits)
            self.assertLess(avg_time, 1.0, f"Average transaction time {avg_time:.2f}s should be < 1s")
        
        # Total time should be reasonable
        self.assertLess(total_time, 10.0, f"Total concurrent processing time {total_time:.2f}s should be < 10s")
        
        # Verify final balance consistency
        account.refresh_from_db()
        expected_balance = initial_balance + (len(successful_deposits) * deposit_amount)
        self.assertEqual(account.balance, expected_balance)
    
    def test_concurrent_transfer_performance(self):
        """Test performance of concurrent transfers between accounts."""
        sender_account = self.accounts['high_balance']  # $50,000 balance
        recipient_accounts = [
            self.accounts['user1_savings'],
            self.accounts['user2_savings'],
            self.accounts['user3_current']
        ]
        
        num_threads = 6
        transfers_per_thread = 3
        transfer_amount = Decimal('100.00')
        
        results = []
        threads = []
        
        def transfer_worker(thread_id):
            worker_results = []
            for i in range(transfers_per_thread):
                recipient = recipient_accounts[i % len(recipient_accounts)]
                start_time = time.time()
                try:
                    BankingTransactionManager.process_transfer(
                        sender_account.account_number,
                        recipient.account_number,
                        transfer_amount,
                        f'Concurrent transfer {thread_id}-{i}'
                    )
                    end_time = time.time()
                    worker_results.append(('success', end_time - start_time))
                except Exception as e:
                    end_time = time.time()
                    worker_results.append(('error', end_time - start_time, str(e)))
            results.extend(worker_results)
        
        # Start concurrent transfers
        start_time = time.time()
        
        for i in range(num_threads):
            thread = threading.Thread(target=transfer_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results
        successful_transfers = [r for r in results if r[0] == 'success']
        
        # Should handle concurrent transfers reasonably well
        success_rate = len(successful_transfers) / len(results)
        self.assertGreaterEqual(success_rate, 0.7, f"Transfer success rate {success_rate:.2%} should be >= 70%")
        
        # Total time should be reasonable
        self.assertLess(total_time, 15.0, f"Total concurrent transfer time {total_time:.2f}s should be < 15s")
    
    def test_mixed_concurrent_operations(self):
        """Test performance with mixed concurrent operations (deposits, withdrawals, transfers)."""
        accounts = [
            self.accounts['user1_savings'],
            self.accounts['user2_savings'],
            self.accounts['user3_current']
        ]
        
        results = []
        threads = []
        
        def mixed_operations_worker(worker_id):
            worker_results = []
            operations = [
                ('deposit', accounts[worker_id % len(accounts)], Decimal('50.00')),
                ('withdrawal', accounts[worker_id % len(accounts)], Decimal('25.00')),
                ('transfer', accounts[worker_id % len(accounts)], Decimal('30.00'))
            ]
            
            for op_type, account, amount in operations:
                start_time = time.time()
                try:
                    if op_type == 'deposit':
                        BankingTransactionManager.process_deposit(
                            account.account_number,
                            amount,
                            f'Mixed op deposit {worker_id}'
                        )
                    elif op_type == 'withdrawal':
                        BankingTransactionManager.process_withdrawal(
                            account.account_number,
                            amount,
                            f'Mixed op withdrawal {worker_id}'
                        )
                    elif op_type == 'transfer':
                        recipient = accounts[(worker_id + 1) % len(accounts)]
                        BankingTransactionManager.process_transfer(
                            account.account_number,
                            recipient.account_number,
                            amount,
                            f'Mixed op transfer {worker_id}'
                        )
                    
                    end_time = time.time()
                    worker_results.append(('success', op_type, end_time - start_time))
                except Exception as e:
                    end_time = time.time()
                    worker_results.append(('error', op_type, end_time - start_time, str(e)))
            
            results.extend(worker_results)
        
        # Start mixed operations
        num_workers = 5
        start_time = time.time()
        
        for i in range(num_workers):
            thread = threading.Thread(target=mixed_operations_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results
        successful_ops = [r for r in results if r[0] == 'success']
        
        # Should handle mixed operations reasonably well
        success_rate = len(successful_ops) / len(results)
        self.assertGreaterEqual(success_rate, 0.6, f"Mixed operations success rate {success_rate:.2%} should be >= 60%")
        
        # Total time should be reasonable
        self.assertLess(total_time, 20.0, f"Total mixed operations time {total_time:.2f}s should be < 20s")


class LoadTestingTest(TestCase):
    """Test system behavior under load."""
    
    def setUp(self):
        self.test_data = TestDataFixtures.create_complete_test_dataset()
        self.users = self.test_data['users']
        self.accounts = self.test_data['accounts']
    
    def test_multiple_user_sessions(self):
        """Test performance with multiple concurrent user sessions."""
        num_clients = 10
        clients = [Client() for _ in range(num_clients)]
        
        # Login all clients
        login_times = []
        for i, client in enumerate(clients):
            start_time = time.time()
            response = client.post(reverse('accounts:login'), {
                'username': f'testuser{(i % 3) + 1}',
                'password': 'TestPass123!'
            })
            end_time = time.time()
            
            if response.status_code == 302:  # Successful login
                login_times.append(end_time - start_time)
        
        # Average login time should be reasonable
        if login_times:
            avg_login_time = sum(login_times) / len(login_times)
            self.assertLess(avg_login_time, 2.0, f"Average login time {avg_login_time:.2f}s should be < 2s")
        
        # Test concurrent dashboard access
        dashboard_times = []
        for client in clients:
            start_time = time.time()
            response = client.get(reverse('accounts:dashboard'))
            end_time = time.time()
            
            if response.status_code == 200:
                dashboard_times.append(end_time - start_time)
        
        # Average dashboard load time should be reasonable
        if dashboard_times:
            avg_dashboard_time = sum(dashboard_times) / len(dashboard_times)
            self.assertLess(avg_dashboard_time, 1.0, f"Average dashboard time {avg_dashboard_time:.2f}s should be < 1s")
    
    def test_high_volume_transaction_processing(self):
        """Test processing high volume of transactions."""
        account = self.accounts['user1_savings']
        
        # Process a large number of transactions
        num_transactions = 100
        start_time = time.time()
        
        for i in range(num_transactions):
            BankingTransactionManager.process_deposit(
                account.account_number,
                Decimal('1.00'),
                f'High volume test {i}'
            )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Calculate transactions per second
        tps = num_transactions / processing_time
        
        # Should process at least 20 transactions per second
        self.assertGreaterEqual(tps, 20, f"Transaction rate {tps:.1f} TPS should be >= 20 TPS")
        
        # Verify all transactions were processed correctly
        transaction_count = Transaction.objects.filter(
            receiver_account=account,
            description__startswith='High volume test'
        ).count()
        self.assertEqual(transaction_count, num_transactions)
    
    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    })
    def test_caching_performance(self):
        """Test performance improvements with caching."""
        client = Client()
        client.login(username='testuser1', password='TestPass123!')
        
        # First request (cache miss)
        start_time = time.time()
        response1 = client.get(reverse('accounts:dashboard'))
        first_request_time = time.time() - start_time
        
        self.assertEqual(response1.status_code, 200)
        
        # Second request (should benefit from any caching)
        start_time = time.time()
        response2 = client.get(reverse('accounts:dashboard'))
        second_request_time = time.time() - start_time
        
        self.assertEqual(response2.status_code, 200)
        
        # Second request should not be significantly slower
        # (This test mainly ensures caching doesn't break functionality)
        self.assertLess(second_request_time, first_request_time * 2)


class MemoryUsageTest(TestCase):
    """Test memory usage patterns."""
    
    def setUp(self):
        self.test_data = TestDataFixtures.create_complete_test_dataset()
        self.accounts = self.test_data['accounts']
    
    def test_large_queryset_memory_usage(self):
        """Test memory usage with large querysets."""
        account = self.accounts['user1_savings']
        
        # Create a large number of transactions
        transactions = []
        for i in range(1000):
            transactions.append(Transaction(
                transaction_type='deposit',
                amount=Decimal('1.00'),
                receiver_account=account,
                description=f'Memory test {i}'
            ))
        
        Transaction.objects.bulk_create(transactions)
        
        # Test iterator usage for memory efficiency
        transaction_count = 0
        for transaction in Transaction.objects.filter(receiver_account=account).iterator():
            transaction_count += 1
            # Process transaction without loading all into memory
        
        self.assertEqual(transaction_count, 1000)
    
    def test_bulk_operations_memory_efficiency(self):
        """Test memory efficiency of bulk operations."""
        account = self.accounts['user1_savings']
        
        # Test bulk create
        transactions = []
        for i in range(500):
            transactions.append(Transaction(
                transaction_type='deposit',
                amount=Decimal('2.00'),
                receiver_account=account,
                description=f'Bulk memory test {i}'
            ))
        
        # Bulk create should be memory efficient
        Transaction.objects.bulk_create(transactions)
        
        # Verify all were created
        created_count = Transaction.objects.filter(
            description__startswith='Bulk memory test'
        ).count()
        self.assertEqual(created_count, 500)


class ResponseTimeTest(TestCase):
    """Test response times for various operations."""
    
    def setUp(self):
        self.client = Client()
        self.test_data = TestDataFixtures.create_complete_test_dataset()
        self.users = self.test_data['users']
        self.accounts = self.test_data['accounts']
    
    def test_page_load_times(self):
        """Test page load times for key pages."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        pages_to_test = [
            ('dashboard', reverse('accounts:dashboard')),
            ('deposit', reverse('transactions:deposit')),
            ('withdrawal', reverse('transactions:withdrawal')),
            ('transfer', reverse('transactions:transfer')),
            ('history', reverse('transactions:history')),
        ]
        
        for page_name, url in pages_to_test:
            start_time = time.time()
            response = self.client.get(url)
            end_time = time.time()
            
            load_time = end_time - start_time
            
            self.assertEqual(response.status_code, 200)
            self.assertLess(load_time, 2.0, f"{page_name} page load time {load_time:.2f}s should be < 2s")
    
    def test_form_submission_times(self):
        """Test form submission response times."""
        self.client.login(username='testuser1', password='TestPass123!')
        
        # Test deposit form submission
        start_time = time.time()
        response = self.client.post(reverse('transactions:deposit'), {
            'amount': '50.00',
            'description': 'Response time test'
        })
        deposit_time = time.time() - start_time
        
        self.assertEqual(response.status_code, 302)
        self.assertLess(deposit_time, 3.0, f"Deposit submission time {deposit_time:.2f}s should be < 3s")
        
        # Test transfer form submission
        start_time = time.time()
        response = self.client.post(reverse('transactions:transfer'), {
            'recipient_account_number': self.accounts['user2_savings'].account_number,
            'amount': '25.00',
            'description': 'Response time test transfer'
        })
        transfer_time = time.time() - start_time
        
        self.assertEqual(response.status_code, 302)
        self.assertLess(transfer_time, 3.0, f"Transfer submission time {transfer_time:.2f}s should be < 3s")
    
    def test_admin_operations_response_time(self):
        """Test response times for admin operations."""
        self.client.login(username='adminuser', password='AdminPass123!')
        
        # Test admin dashboard load time
        start_time = time.time()
        response = self.client.get(reverse('admin_panel:dashboard'))
        dashboard_time = time.time() - start_time
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(dashboard_time, 3.0, f"Admin dashboard load time {dashboard_time:.2f}s should be < 3s")
        
        # Test account approval time
        pending_account = self.accounts['user2_pending']
        start_time = time.time()
        response = self.client.post(
            reverse('admin_panel:approve_account', args=[pending_account.id]),
            {'reason': 'Response time test approval'}
        )
        approval_time = time.time() - start_time
        
        self.assertEqual(response.status_code, 302)
        self.assertLess(approval_time, 2.0, f"Account approval time {approval_time:.2f}s should be < 2s")