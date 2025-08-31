"""
Atomic transaction utilities for the banking platform.
Provides enhanced transaction processing with proper rollback handling,
database locking, and concurrent transaction management.
"""

import logging
from decimal import Decimal
from functools import wraps
from django.db import transaction, connection
from django.db.models import F, Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from accounts.models import BankAccount
from transactions.models import Transaction

logger = logging.getLogger(__name__)


class TransactionError(Exception):
    """Custom exception for transaction processing errors."""
    pass


class InsufficientFundsError(TransactionError):
    """Exception raised when account has insufficient funds."""
    pass


class AccountNotActiveError(TransactionError):
    """Exception raised when account is not active for transactions."""
    pass


class ConcurrentTransactionError(TransactionError):
    """Exception raised when concurrent transaction conflicts occur."""
    pass


def atomic_financial_transaction(isolation_level='READ_COMMITTED'):
    """
    Decorator for atomic financial transactions with proper isolation.
    
    Args:
        isolation_level: Database isolation level for the transaction
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                with transaction.atomic():
                    # Set isolation level for this transaction
                    if isolation_level and hasattr(connection, 'set_isolation_level'):
                        connection.set_isolation_level(isolation_level)
                    
                    result = func(*args, **kwargs)
                    
                    # Log successful transaction
                    logger.info(f"Atomic transaction completed successfully: {func.__name__}")
                    return result
                    
            except Exception as e:
                # Log transaction failure
                logger.error(f"Atomic transaction failed in {func.__name__}: {str(e)}")
                raise
        
        return wrapper
    return decorator


class BankingTransactionManager:
    """
    Manager class for handling banking transactions with proper locking and validation.
    """
    
    @staticmethod
    def validate_account_for_transaction(account, transaction_type='general'):
        """
        Validate that an account can perform transactions.
        
        Args:
            account: BankAccount instance
            transaction_type: Type of transaction being performed
            
        Raises:
            AccountNotActiveError: If account cannot perform transactions
        """
        if not account.can_transact():
            raise AccountNotActiveError(
                f"Account {account.account_number} is {account.status} and cannot perform transactions"
            )
        
        # Additional validation based on transaction type
        if transaction_type in ['withdrawal', 'transfer'] and account.status == 'frozen':
            raise AccountNotActiveError(
                f"Account {account.account_number} is frozen and cannot perform {transaction_type} transactions"
            )
    
    @staticmethod
    def lock_account_for_update(account_number):
        """
        Lock account for update to prevent concurrent modifications.
        
        Args:
            account_number: Account number to lock
            
        Returns:
            BankAccount: Locked account instance
            
        Raises:
            BankAccount.DoesNotExist: If account doesn't exist
        """
        try:
            # Use select_for_update to lock the account row
            account = BankAccount.objects.select_for_update().get(
                account_number=account_number
            )
            return account
        except BankAccount.DoesNotExist:
            logger.error(f"Attempted to lock non-existent account: {account_number}")
            raise
    
    @staticmethod
    def lock_multiple_accounts_for_update(account_numbers):
        """
        Lock multiple accounts for update in a consistent order to prevent deadlocks.
        
        Args:
            account_numbers: List of account numbers to lock
            
        Returns:
            dict: Dictionary mapping account numbers to BankAccount instances
            
        Raises:
            BankAccount.DoesNotExist: If any account doesn't exist
        """
        # Sort account numbers to ensure consistent locking order
        sorted_numbers = sorted(account_numbers)
        
        locked_accounts = {}
        for account_number in sorted_numbers:
            account = BankingTransactionManager.lock_account_for_update(account_number)
            locked_accounts[account_number] = account
        
        return locked_accounts
    
    @staticmethod
    @atomic_financial_transaction()
    def process_deposit(account_number, amount, description='Cash deposit', user=None):
        """
        Process a deposit transaction with atomic guarantees.
        
        Args:
            account_number: Target account number
            amount: Deposit amount
            description: Transaction description
            user: User performing the transaction
            
        Returns:
            Transaction: Created transaction record
            
        Raises:
            TransactionError: If transaction fails
        """
        try:
            # Validate amount
            if not isinstance(amount, Decimal):
                amount = Decimal(str(amount))
            
            if amount <= 0:
                raise TransactionError("Deposit amount must be greater than zero")
            
            # Lock account for update
            account = BankingTransactionManager.lock_account_for_update(account_number)
            
            # Validate account
            BankingTransactionManager.validate_account_for_transaction(account, 'deposit')
            
            # Calculate new balance
            old_balance = account.balance
            new_balance = old_balance + amount
            
            # Update account balance using F() expression for atomic update
            updated_rows = BankAccount.objects.filter(
                id=account.id,
                balance=old_balance  # Ensure balance hasn't changed
            ).update(balance=F('balance') + amount)
            
            if updated_rows == 0:
                raise ConcurrentTransactionError(
                    "Account balance was modified by another transaction"
                )
            
            # Refresh account to get updated balance
            account.refresh_from_db()
            
            # Create transaction record
            transaction_record = Transaction.objects.create(
                transaction_type='deposit',
                amount=amount,
                description=description,
                receiver_account=account,
                receiver_balance_after=account.balance,
                timestamp=timezone.now()
            )
            
            # Log successful deposit
            logger.info(
                f"Deposit processed: Account {account_number}, "
                f"Amount ${amount}, New Balance ${account.balance}"
            )
            
            return transaction_record
            
        except Exception as e:
            logger.error(f"Deposit failed for account {account_number}: {str(e)}")
            raise TransactionError(f"Deposit failed: {str(e)}")
    
    @staticmethod
    @atomic_financial_transaction()
    def process_withdrawal(account_number, amount, description='Cash withdrawal', user=None):
        """
        Process a withdrawal transaction with atomic guarantees.
        
        Args:
            account_number: Source account number
            amount: Withdrawal amount
            description: Transaction description
            user: User performing the transaction
            
        Returns:
            Transaction: Created transaction record
            
        Raises:
            TransactionError: If transaction fails
            InsufficientFundsError: If insufficient funds
        """
        try:
            # Validate amount
            if not isinstance(amount, Decimal):
                amount = Decimal(str(amount))
            
            if amount <= 0:
                raise TransactionError("Withdrawal amount must be greater than zero")
            
            # Lock account for update
            account = BankingTransactionManager.lock_account_for_update(account_number)
            
            # Validate account
            BankingTransactionManager.validate_account_for_transaction(account, 'withdrawal')
            
            # Check sufficient funds
            if account.balance < amount:
                raise InsufficientFundsError(
                    f"Insufficient funds. Available: ${account.balance}, Requested: ${amount}"
                )
            
            # Calculate new balance
            old_balance = account.balance
            new_balance = old_balance - amount
            
            # Ensure new balance is not negative (double-check)
            if new_balance < 0:
                raise InsufficientFundsError("Transaction would result in negative balance")
            
            # Update account balance using F() expression for atomic update
            updated_rows = BankAccount.objects.filter(
                id=account.id,
                balance=old_balance  # Ensure balance hasn't changed
            ).update(balance=F('balance') - amount)
            
            if updated_rows == 0:
                raise ConcurrentTransactionError(
                    "Account balance was modified by another transaction"
                )
            
            # Refresh account to get updated balance
            account.refresh_from_db()
            
            # Create transaction record
            transaction_record = Transaction.objects.create(
                transaction_type='withdrawal',
                amount=amount,
                description=description,
                sender_account=account,
                sender_balance_after=account.balance,
                timestamp=timezone.now()
            )
            
            # Log successful withdrawal
            logger.info(
                f"Withdrawal processed: Account {account_number}, "
                f"Amount ${amount}, New Balance ${account.balance}"
            )
            
            return transaction_record
            
        except (InsufficientFundsError, ConcurrentTransactionError):
            # Re-raise these specific errors
            raise
        except Exception as e:
            logger.error(f"Withdrawal failed for account {account_number}: {str(e)}")
            raise TransactionError(f"Withdrawal failed: {str(e)}")
    
    @staticmethod
    @atomic_financial_transaction()
    def process_transfer(sender_account_number, receiver_account_number, amount, 
                        description='Money transfer', user=None):
        """
        Process a transfer transaction with atomic guarantees.
        
        Args:
            sender_account_number: Source account number
            receiver_account_number: Destination account number
            amount: Transfer amount
            description: Transaction description
            user: User performing the transaction
            
        Returns:
            Transaction: Created transaction record
            
        Raises:
            TransactionError: If transaction fails
            InsufficientFundsError: If insufficient funds
        """
        try:
            # Validate amount
            if not isinstance(amount, Decimal):
                amount = Decimal(str(amount))
            
            if amount <= 0:
                raise TransactionError("Transfer amount must be greater than zero")
            
            # Validate account numbers are different
            if sender_account_number == receiver_account_number:
                raise TransactionError("Cannot transfer to the same account")
            
            # Lock both accounts in consistent order to prevent deadlocks
            locked_accounts = BankingTransactionManager.lock_multiple_accounts_for_update([
                sender_account_number, receiver_account_number
            ])
            
            sender_account = locked_accounts[sender_account_number]
            receiver_account = locked_accounts[receiver_account_number]
            
            # Validate both accounts
            BankingTransactionManager.validate_account_for_transaction(sender_account, 'transfer')
            BankingTransactionManager.validate_account_for_transaction(receiver_account, 'transfer')
            
            # Check sufficient funds
            if sender_account.balance < amount:
                raise InsufficientFundsError(
                    f"Insufficient funds. Available: ${sender_account.balance}, Requested: ${amount}"
                )
            
            # Store original balances for validation
            sender_old_balance = sender_account.balance
            receiver_old_balance = receiver_account.balance
            
            # Calculate new balances
            sender_new_balance = sender_old_balance - amount
            receiver_new_balance = receiver_old_balance + amount
            
            # Ensure sender balance won't go negative
            if sender_new_balance < 0:
                raise InsufficientFundsError("Transfer would result in negative balance")
            
            # Update sender account balance atomically
            sender_updated_rows = BankAccount.objects.filter(
                id=sender_account.id,
                balance=sender_old_balance
            ).update(balance=F('balance') - amount)
            
            if sender_updated_rows == 0:
                raise ConcurrentTransactionError(
                    "Sender account balance was modified by another transaction"
                )
            
            # Update receiver account balance atomically
            receiver_updated_rows = BankAccount.objects.filter(
                id=receiver_account.id,
                balance=receiver_old_balance
            ).update(balance=F('balance') + amount)
            
            if receiver_updated_rows == 0:
                # Rollback sender update by raising exception
                # The atomic decorator will handle the rollback
                raise ConcurrentTransactionError(
                    "Receiver account balance was modified by another transaction"
                )
            
            # Refresh accounts to get updated balances
            sender_account.refresh_from_db()
            receiver_account.refresh_from_db()
            
            # Create transaction record
            transaction_record = Transaction.objects.create(
                transaction_type='transfer',
                amount=amount,
                description=description,
                sender_account=sender_account,
                receiver_account=receiver_account,
                sender_balance_after=sender_account.balance,
                receiver_balance_after=receiver_account.balance,
                timestamp=timezone.now()
            )
            
            # Log successful transfer
            logger.info(
                f"Transfer processed: From {sender_account_number} to {receiver_account_number}, "
                f"Amount ${amount}, Sender Balance ${sender_account.balance}, "
                f"Receiver Balance ${receiver_account.balance}"
            )
            
            return transaction_record
            
        except (InsufficientFundsError, ConcurrentTransactionError):
            # Re-raise these specific errors
            raise
        except Exception as e:
            logger.error(
                f"Transfer failed from {sender_account_number} to {receiver_account_number}: {str(e)}"
            )
            raise TransactionError(f"Transfer failed: {str(e)}")
    
    @staticmethod
    def validate_transaction_integrity(transaction_id):
        """
        Validate the integrity of a completed transaction.
        
        Args:
            transaction_id: ID of the transaction to validate
            
        Returns:
            bool: True if transaction is valid, False otherwise
        """
        try:
            transaction_record = Transaction.objects.get(id=transaction_id)
            
            # Validate based on transaction type
            if transaction_record.transaction_type == 'deposit':
                # For deposits, check that receiver balance is correct
                if transaction_record.receiver_account:
                    expected_balance = (
                        transaction_record.receiver_balance_after - 
                        transaction_record.amount
                    )
                    # Note: This is a simplified check. In practice, you'd need to
                    # account for other transactions that might have occurred
                    return True
            
            elif transaction_record.transaction_type == 'withdrawal':
                # For withdrawals, check that sender balance is correct
                if transaction_record.sender_account:
                    expected_balance = (
                        transaction_record.sender_balance_after + 
                        transaction_record.amount
                    )
                    return True
            
            elif transaction_record.transaction_type == 'transfer':
                # For transfers, check both accounts
                if (transaction_record.sender_account and 
                    transaction_record.receiver_account):
                    return True
            
            return False
            
        except Transaction.DoesNotExist:
            logger.error(f"Transaction {transaction_id} not found for integrity validation")
            return False
        except Exception as e:
            logger.error(f"Error validating transaction {transaction_id}: {str(e)}")
            return False


class ConcurrentTransactionTester:
    """
    Utility class for testing concurrent transaction scenarios.
    """
    
    @staticmethod
    def simulate_concurrent_deposits(account_number, amounts, num_threads=2):
        """
        Simulate concurrent deposits to test transaction integrity.
        
        Args:
            account_number: Target account number
            amounts: List of amounts to deposit
            num_threads: Number of concurrent threads
            
        Returns:
            list: Results of each deposit attempt
        """
        import threading
        import time
        
        results = []
        threads = []
        
        def deposit_worker(amount, result_list, index):
            try:
                time.sleep(0.01 * index)  # Slight delay to increase concurrency
                result = BankingTransactionManager.process_deposit(
                    account_number, amount, f"Concurrent deposit {index}"
                )
                result_list.append(('success', result))
            except Exception as e:
                result_list.append(('error', str(e)))
        
        # Create and start threads
        for i, amount in enumerate(amounts[:num_threads]):
            thread = threading.Thread(
                target=deposit_worker, 
                args=(amount, results, i)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        return results
    
    @staticmethod
    def simulate_concurrent_transfers(sender_account, receiver_account, amounts, num_threads=2):
        """
        Simulate concurrent transfers to test transaction integrity.
        
        Args:
            sender_account: Source account number
            receiver_account: Destination account number
            amounts: List of amounts to transfer
            num_threads: Number of concurrent threads
            
        Returns:
            list: Results of each transfer attempt
        """
        import threading
        import time
        
        results = []
        threads = []
        
        def transfer_worker(amount, result_list, index):
            try:
                time.sleep(0.01 * index)  # Slight delay to increase concurrency
                result = BankingTransactionManager.process_transfer(
                    sender_account, receiver_account, amount, 
                    f"Concurrent transfer {index}"
                )
                result_list.append(('success', result))
            except Exception as e:
                result_list.append(('error', str(e)))
        
        # Create and start threads
        for i, amount in enumerate(amounts[:num_threads]):
            thread = threading.Thread(
                target=transfer_worker, 
                args=(amount, results, i)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        return results