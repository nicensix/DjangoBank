from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from accounts.models import BankAccount


class Transaction(models.Model):
    """
    Transaction model for recording all banking transactions.
    
    Supports deposits, withdrawals, and transfers between accounts.
    Maintains proper relationships and audit trail.
    """
    
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('transfer', 'Transfer'),
    ]
    
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES,
        help_text="Type of transaction"
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Transaction amount"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="Transaction timestamp"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional transaction description"
    )
    reference_number = models.CharField(
        max_length=25,
        unique=True,
        help_text="Unique transaction reference number"
    )
    
    # For deposits and withdrawals, only one account is involved
    # For transfers, both sender and receiver accounts are used
    sender_account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name='sent_transactions',
        null=True,
        blank=True,
        help_text="Account sending money (for withdrawals and transfers)"
    )
    receiver_account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name='received_transactions',
        null=True,
        blank=True,
        help_text="Account receiving money (for deposits and transfers)"
    )
    
    # Balance after transaction for audit purposes
    sender_balance_after = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Sender account balance after transaction"
    )
    receiver_balance_after = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Receiver account balance after transaction"
    )
    
    class Meta:
        db_table = 'transactions'
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['transaction_type']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['sender_account', 'timestamp']),
            models.Index(fields=['receiver_account', 'timestamp']),
        ]
    
    def save(self, *args, **kwargs):
        """Override save to generate reference number if not provided."""
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()
        self.full_clean()  # Run validation before saving
        super().save(*args, **kwargs)
    
    def clean(self):
        """Custom validation for the Transaction model."""
        # Validate amount is positive
        if self.amount <= 0:
            raise ValidationError({
                'amount': 'Transaction amount must be positive.'
            })
        
        # Validate transaction type specific requirements
        if self.transaction_type == 'deposit':
            if not self.receiver_account:
                raise ValidationError({
                    'receiver_account': 'Deposit transactions must have a receiver account.'
                })
            if self.sender_account:
                raise ValidationError({
                    'sender_account': 'Deposit transactions should not have a sender account.'
                })
        
        elif self.transaction_type == 'withdrawal':
            if not self.sender_account:
                raise ValidationError({
                    'sender_account': 'Withdrawal transactions must have a sender account.'
                })
            if self.receiver_account:
                raise ValidationError({
                    'receiver_account': 'Withdrawal transactions should not have a receiver account.'
                })
        
        elif self.transaction_type == 'transfer':
            if not self.sender_account or not self.receiver_account:
                raise ValidationError({
                    'sender_account': 'Transfer transactions must have both sender and receiver accounts.',
                    'receiver_account': 'Transfer transactions must have both sender and receiver accounts.'
                })
            if self.sender_account == self.receiver_account:
                raise ValidationError({
                    'receiver_account': 'Cannot transfer to the same account.'
                })
    
    @staticmethod
    def generate_reference_number():
        """Generate a unique transaction reference number."""
        import random
        import string
        
        while True:
            # Generate format: TXN + timestamp + random 4 chars
            timestamp_part = timezone.now().strftime('%Y%m%d%H%M%S')
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            reference = f"TXN{timestamp_part}{random_part}"
            
            # Check if this reference number already exists
            if not Transaction.objects.filter(reference_number=reference).exists():
                return reference
    
    def get_account(self):
        """Get the primary account involved in this transaction."""
        if self.transaction_type == 'deposit':
            return self.receiver_account
        elif self.transaction_type == 'withdrawal':
            return self.sender_account
        elif self.transaction_type == 'transfer':
            return self.sender_account  # Return sender as primary for transfers
        return None
    
    def get_other_account(self):
        """Get the other account involved in transfer transactions."""
        if self.transaction_type == 'transfer':
            return self.receiver_account
        return None
    
    def is_deposit(self):
        """Check if this is a deposit transaction."""
        return self.transaction_type == 'deposit'
    
    def is_withdrawal(self):
        """Check if this is a withdrawal transaction."""
        return self.transaction_type == 'withdrawal'
    
    def is_transfer(self):
        """Check if this is a transfer transaction."""
        return self.transaction_type == 'transfer'
    
    def get_display_amount_for_account(self, account):
        """
        Get the display amount for a specific account.
        Returns positive for credits (money in) and negative for debits (money out).
        """
        if self.transaction_type == 'deposit' and self.receiver_account == account:
            return self.amount
        elif self.transaction_type == 'withdrawal' and self.sender_account == account:
            return -self.amount
        elif self.transaction_type == 'transfer':
            if self.sender_account == account:
                return -self.amount
            elif self.receiver_account == account:
                return self.amount
        return Decimal('0.00')
    
    def get_description_for_account(self, account):
        """Get a descriptive text for this transaction from the perspective of a specific account."""
        if self.transaction_type == 'deposit' and self.receiver_account == account:
            return f"Deposit - {self.description or 'Cash deposit'}"
        elif self.transaction_type == 'withdrawal' and self.sender_account == account:
            return f"Withdrawal - {self.description or 'Cash withdrawal'}"
        elif self.transaction_type == 'transfer':
            if self.sender_account == account:
                return f"Transfer to {self.receiver_account.account_number} - {self.description or 'Money transfer'}"
            elif self.receiver_account == account:
                return f"Transfer from {self.sender_account.account_number} - {self.description or 'Money transfer'}"
        return "Unknown transaction"
    
    def __str__(self):
        if self.transaction_type == 'deposit':
            return f"Deposit of ${self.amount} to {self.receiver_account.account_number}"
        elif self.transaction_type == 'withdrawal':
            return f"Withdrawal of ${self.amount} from {self.sender_account.account_number}"
        elif self.transaction_type == 'transfer':
            return f"Transfer of ${self.amount} from {self.sender_account.account_number} to {self.receiver_account.account_number}"
        return f"{self.get_transaction_type_display()} - ${self.amount}"
