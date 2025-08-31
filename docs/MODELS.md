# Model Documentation

## Overview

This document provides detailed information about the Django models used in the Banking Platform. The models are organized across different Django apps to maintain separation of concerns and modularity.

## Database Schema

The platform uses the following main models with their relationships:

```
User (Django's AbstractUser)
├── BankAccount (One-to-Many)
│   ├── Transaction (sender_account) (One-to-Many)
│   ├── Transaction (receiver_account) (One-to-Many)
│   └── AdminAction (One-to-Many)
└── AdminAction (admin) (One-to-Many)
```

## Core Models

### User Model (accounts/models.py)

Extends Django's built-in `AbstractUser` model to provide authentication and user management.

```python
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    Provides authentication and basic user information.
    """
    
    # Inherited fields from AbstractUser:
    # - username (CharField, unique)
    # - first_name (CharField)
    # - last_name (CharField)
    # - email (EmailField)
    # - password (CharField, hashed)
    # - is_staff (BooleanField)
    # - is_active (BooleanField)
    # - date_joined (DateTimeField)
    # - last_login (DateTimeField)
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.username} ({self.get_full_name()})"
    
    def get_full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def bank_accounts(self):
        """Return all bank accounts for this user."""
        return self.bankaccount_set.all()
    
    @property
    def primary_account(self):
        """Return the user's primary (first) bank account."""
        return self.bankaccount_set.first()
```

**Fields:**
- `username`: Unique username for login (max 150 characters)
- `email`: User's email address
- `first_name`: User's first name (max 150 characters)
- `last_name`: User's last name (max 150 characters)
- `password`: Hashed password
- `is_staff`: Boolean indicating if user can access admin
- `is_active`: Boolean indicating if account is active
- `date_joined`: Timestamp when user registered
- `last_login`: Timestamp of last login

**Relationships:**
- One-to-Many with `BankAccount`
- One-to-Many with `AdminAction` (as admin)

### BankAccount Model (accounts/models.py)

Represents a bank account belonging to a user.

```python
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal

User = get_user_model()

class BankAccount(models.Model):
    """
    Bank account model representing a user's banking account.
    """
    
    ACCOUNT_TYPES = [
        ('Savings', 'Savings Account'),
        ('Current', 'Current Account'),
    ]
    
    ACCOUNT_STATUS = [
        ('Pending', 'Pending Approval'),
        ('Active', 'Active'),
        ('Frozen', 'Frozen'),
        ('Closed', 'Closed'),
    ]
    
    account_number = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique account number"
    )
    account_type = models.CharField(
        max_length=10,
        choices=ACCOUNT_TYPES,
        default='Savings',
        help_text="Type of bank account"
    )
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Current account balance"
    )
    status = models.CharField(
        max_length=10,
        choices=ACCOUNT_STATUS,
        default='Pending',
        help_text="Account status"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Account creation timestamp"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last update timestamp"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="Account owner"
    )
    
    class Meta:
        db_table = 'bank_account'
        verbose_name = 'Bank Account'
        verbose_name_plural = 'Bank Accounts'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.account_number} - {self.user.username}"
    
    def save(self, *args, **kwargs):
        """Generate account number if not provided."""
        if not self.account_number:
            self.account_number = self.generate_account_number()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_account_number():
        """Generate a unique account number."""
        import random
        import string
        
        prefix = "ACC"
        suffix = ''.join(random.choices(string.digits, k=12))
        return f"{prefix}{suffix}"
    
    @property
    def is_active(self):
        """Check if account is active for transactions."""
        return self.status == 'Active'
    
    @property
    def formatted_balance(self):
        """Return formatted balance with currency symbol."""
        return f"${self.balance:,.2f}"
    
    def can_withdraw(self, amount):
        """Check if withdrawal amount is valid."""
        return self.balance >= amount and self.is_active
    
    def get_transactions(self):
        """Get all transactions for this account."""
        from transactions.models import Transaction
        return Transaction.objects.filter(
            models.Q(sender_account=self) | models.Q(receiver_account=self)
        ).order_by('-timestamp')
```

**Fields:**
- `account_number`: Unique 15-character account identifier
- `account_type`: Type of account (Savings/Current)
- `balance`: Current account balance (up to 15 digits, 2 decimal places)
- `status`: Account status (Pending/Active/Frozen/Closed)
- `created_at`: Account creation timestamp
- `updated_at`: Last modification timestamp
- `user`: Foreign key to User model

**Relationships:**
- Many-to-One with `User`
- One-to-Many with `Transaction` (as sender)
- One-to-Many with `Transaction` (as receiver)
- One-to-Many with `AdminAction`

### Transaction Model (transactions/models.py)

Represents all financial transactions in the system.

```python
from django.db import models
from django.contrib.auth import get_user_model
from accounts.models import BankAccount
from decimal import Decimal

class Transaction(models.Model):
    """
    Transaction model representing all financial operations.
    """
    
    TRANSACTION_TYPES = [
        ('Deposit', 'Deposit'),
        ('Withdrawal', 'Withdrawal'),
        ('Transfer', 'Transfer'),
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
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Transaction description"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="Transaction timestamp"
    )
    sender_account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name='sent_transactions',
        null=True,
        blank=True,
        help_text="Sender account (for withdrawals and transfers)"
    )
    receiver_account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name='received_transactions',
        null=True,
        blank=True,
        help_text="Receiver account (for deposits and transfers)"
    )
    
    class Meta:
        db_table = 'transaction'
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['sender_account', 'timestamp']),
            models.Index(fields=['receiver_account', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.transaction_type} - ${self.amount} - {self.timestamp}"
    
    @property
    def formatted_amount(self):
        """Return formatted amount with currency symbol."""
        return f"${self.amount:,.2f}"
    
    def get_account_for_user(self, user):
        """Get the relevant account for a specific user."""
        if self.sender_account and self.sender_account.user == user:
            return self.sender_account
        elif self.receiver_account and self.receiver_account.user == user:
            return self.receiver_account
        return None
    
    def is_debit_for_account(self, account):
        """Check if transaction is a debit for the given account."""
        return self.sender_account == account
    
    def is_credit_for_account(self, account):
        """Check if transaction is a credit for the given account."""
        return self.receiver_account == account
    
    @classmethod
    def create_deposit(cls, account, amount, description=""):
        """Create a deposit transaction."""
        return cls.objects.create(
            transaction_type='Deposit',
            amount=amount,
            description=description,
            receiver_account=account
        )
    
    @classmethod
    def create_withdrawal(cls, account, amount, description=""):
        """Create a withdrawal transaction."""
        return cls.objects.create(
            transaction_type='Withdrawal',
            amount=amount,
            description=description,
            sender_account=account
        )
    
    @classmethod
    def create_transfer(cls, sender_account, receiver_account, amount, description=""):
        """Create a transfer transaction."""
        return cls.objects.create(
            transaction_type='Transfer',
            amount=amount,
            description=description,
            sender_account=sender_account,
            receiver_account=receiver_account
        )
```

**Fields:**
- `transaction_type`: Type of transaction (Deposit/Withdrawal/Transfer)
- `amount`: Transaction amount (up to 15 digits, 2 decimal places)
- `description`: Optional transaction description
- `timestamp`: When the transaction occurred
- `sender_account`: Source account (for withdrawals and transfers)
- `receiver_account`: Destination account (for deposits and transfers)

**Relationships:**
- Many-to-One with `BankAccount` (sender)
- Many-to-One with `BankAccount` (receiver)

### AdminAction Model (admin_panel/models.py)

Tracks administrative actions performed on accounts.

```python
from django.db import models
from django.contrib.auth import get_user_model
from accounts.models import BankAccount

User = get_user_model()

class AdminAction(models.Model):
    """
    Model to track administrative actions on bank accounts.
    """
    
    ACTION_TYPES = [
        ('Approve', 'Approve Account'),
        ('Freeze', 'Freeze Account'),
        ('Unfreeze', 'Unfreeze Account'),
        ('Close', 'Close Account'),
        ('Reopen', 'Reopen Account'),
        ('Update', 'Update Account Details'),
    ]
    
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPES,
        help_text="Type of administrative action"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When the action was performed"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about the action"
    )
    admin = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'is_staff': True},
        help_text="Administrator who performed the action"
    )
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        help_text="Account that was affected"
    )
    
    class Meta:
        db_table = 'admin_action'
        verbose_name = 'Admin Action'
        verbose_name_plural = 'Admin Actions'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['action_type']),
            models.Index(fields=['admin', 'timestamp']),
            models.Index(fields=['bank_account', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.action_type} on {self.bank_account.account_number} by {self.admin.username}"
    
    @classmethod
    def log_action(cls, admin, bank_account, action_type, notes=""):
        """Log an administrative action."""
        return cls.objects.create(
            admin=admin,
            bank_account=bank_account,
            action_type=action_type,
            notes=notes
        )
```

**Fields:**
- `action_type`: Type of administrative action
- `timestamp`: When the action was performed
- `notes`: Optional notes about the action
- `admin`: Administrator who performed the action
- `bank_account`: Account that was affected

**Relationships:**
- Many-to-One with `User` (admin)
- Many-to-One with `BankAccount`

## Model Managers and QuerySets

### Custom Managers

```python
# accounts/models.py
class ActiveAccountManager(models.Manager):
    """Manager for active bank accounts only."""
    
    def get_queryset(self):
        return super().get_queryset().filter(status='Active')

class BankAccount(models.Model):
    # ... fields ...
    
    objects = models.Manager()  # Default manager
    active = ActiveAccountManager()  # Custom manager for active accounts

# transactions/models.py
class TransactionQuerySet(models.QuerySet):
    """Custom QuerySet for transactions."""
    
    def deposits(self):
        return self.filter(transaction_type='Deposit')
    
    def withdrawals(self):
        return self.filter(transaction_type='Withdrawal')
    
    def transfers(self):
        return self.filter(transaction_type='Transfer')
    
    def for_account(self, account):
        return self.filter(
            models.Q(sender_account=account) | models.Q(receiver_account=account)
        )
    
    def in_date_range(self, start_date, end_date):
        return self.filter(timestamp__range=[start_date, end_date])

class TransactionManager(models.Manager):
    def get_queryset(self):
        return TransactionQuerySet(self.model, using=self._db)
    
    def deposits(self):
        return self.get_queryset().deposits()
    
    def withdrawals(self):
        return self.get_queryset().withdrawals()
    
    def transfers(self):
        return self.get_queryset().transfers()

class Transaction(models.Model):
    # ... fields ...
    
    objects = TransactionManager()
```

## Database Indexes

The models include strategic indexes for performance:

```python
# Transaction model indexes
class Meta:
    indexes = [
        models.Index(fields=['timestamp']),  # For date-based queries
        models.Index(fields=['transaction_type']),  # For filtering by type
        models.Index(fields=['sender_account', 'timestamp']),  # For account history
        models.Index(fields=['receiver_account', 'timestamp']),  # For account history
    ]

# AdminAction model indexes
class Meta:
    indexes = [
        models.Index(fields=['timestamp']),  # For chronological queries
        models.Index(fields=['action_type']),  # For filtering by action
        models.Index(fields=['admin', 'timestamp']),  # For admin activity
        models.Index(fields=['bank_account', 'timestamp']),  # For account history
    ]
```

## Model Validation

### Custom Validators

```python
from django.core.exceptions import ValidationError
from django.core.validators import BaseValidator
from decimal import Decimal

class PositiveAmountValidator(BaseValidator):
    """Validator to ensure amounts are positive."""
    
    message = 'Amount must be positive.'
    code = 'invalid_amount'
    
    def compare(self, a, b):
        return a <= 0

class AccountNumberValidator:
    """Validator for account number format."""
    
    def __call__(self, value):
        if not value.startswith('ACC'):
            raise ValidationError('Account number must start with "ACC"')
        if len(value) != 15:
            raise ValidationError('Account number must be 15 characters long')
        if not value[3:].isdigit():
            raise ValidationError('Account number must contain only digits after "ACC"')
```

## Model Signals

```python
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import BankAccount, Transaction

User = get_user_model()

@receiver(post_save, sender=User)
def create_bank_account(sender, instance, created, **kwargs):
    """Create a bank account when a new user is created."""
    if created:
        BankAccount.objects.create(
            user=instance,
            account_type='Savings',
            status='Pending'
        )

@receiver(pre_save, sender=Transaction)
def validate_transaction(sender, instance, **kwargs):
    """Validate transaction before saving."""
    if instance.transaction_type == 'Transfer':
        if not instance.sender_account or not instance.receiver_account:
            raise ValidationError('Transfer requires both sender and receiver accounts')
        if instance.sender_account == instance.receiver_account:
            raise ValidationError('Cannot transfer to the same account')
    
    if instance.amount <= 0:
        raise ValidationError('Transaction amount must be positive')
```

## Usage Examples

### Creating Models

```python
# Create a user
user = User.objects.create_user(
    username='john_doe',
    email='john@example.com',
    password='secure_password',
    first_name='John',
    last_name='Doe'
)

# Create a bank account
account = BankAccount.objects.create(
    user=user,
    account_type='Savings',
    balance=Decimal('1000.00'),
    status='Active'
)

# Create a deposit transaction
transaction = Transaction.create_deposit(
    account=account,
    amount=Decimal('500.00'),
    description='Initial deposit'
)
```

### Querying Models

```python
# Get all active accounts
active_accounts = BankAccount.active.all()

# Get user's transaction history
user_transactions = Transaction.objects.for_account(user.primary_account)

# Get deposits in the last month
from datetime import datetime, timedelta
last_month = datetime.now() - timedelta(days=30)
recent_deposits = Transaction.objects.deposits().filter(
    timestamp__gte=last_month
)

# Get admin actions for an account
admin_actions = AdminAction.objects.filter(
    bank_account=account
).select_related('admin')
```