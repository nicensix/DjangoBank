import random
import string
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    
    This model uses Django's built-in authentication fields:
    - username, email, password, first_name, last_name
    - date_joined, is_active, is_staff, is_superuser
    
    Additional fields can be added here as needed for banking platform requirements.
    """
    
    # Additional fields can be added here if needed in the future
    # For now, we use Django's built-in fields which satisfy our requirements
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.username} ({self.first_name} {self.last_name})"


class BankAccount(models.Model):
    """
    Bank Account model for managing user bank accounts.
    
    Each user can have multiple bank accounts with unique account numbers.
    Supports different account types and status management.
    """
    
    ACCOUNT_TYPES = [
        ('savings', 'Savings'),
        ('current', 'Current'),
    ]
    
    ACCOUNT_STATUS = [
        ('active', 'Active'),
        ('frozen', 'Frozen'),
        ('closed', 'Closed'),
        ('pending', 'Pending Approval'),
    ]
    
    account_number = models.CharField(
        max_length=12,
        unique=True,
        help_text="Unique 12-digit account number"
    )
    account_type = models.CharField(
        max_length=10,
        choices=ACCOUNT_TYPES,
        default='savings',
        help_text="Type of bank account"
    )
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        help_text="Current account balance"
    )
    status = models.CharField(
        max_length=10,
        choices=ACCOUNT_STATUS,
        default='pending',
        help_text="Current account status"
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
        related_name='bank_accounts',
        help_text="Account owner"
    )
    
    class Meta:
        db_table = 'bank_accounts'
        verbose_name = 'Bank Account'
        verbose_name_plural = 'Bank Accounts'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        """Override save to generate account number if not provided."""
        if not self.account_number:
            self.account_number = self.generate_account_number()
        self.full_clean()  # Run validation before saving
        super().save(*args, **kwargs)
    
    def clean(self):
        """Custom validation for the BankAccount model."""
        # Validate balance is not negative
        if self.balance < 0:
            raise ValidationError({
                'balance': 'Account balance cannot be negative.'
            })
        
        # Validate account number format if provided
        if self.account_number and not self.is_valid_account_number(self.account_number):
            raise ValidationError({
                'account_number': 'Account number must be exactly 12 digits.'
            })
    
    @staticmethod
    def generate_account_number():
        """Generate a unique 12-digit account number."""
        while True:
            # Generate a 12-digit number starting with 1-9 (to avoid leading zeros)
            first_digit = random.choice('123456789')
            remaining_digits = ''.join(random.choices(string.digits, k=11))
            account_number = first_digit + remaining_digits
            
            # Check if this account number already exists
            if not BankAccount.objects.filter(account_number=account_number).exists():
                return account_number
    
    @staticmethod
    def is_valid_account_number(account_number):
        """Validate account number format."""
        return (
            isinstance(account_number, str) and
            len(account_number) == 12 and
            account_number.isdigit() and
            not account_number.startswith('0')
        )
    
    def is_active(self):
        """Check if account is active and can perform transactions."""
        return self.status == 'active'
    
    def is_frozen(self):
        """Check if account is frozen."""
        return self.status == 'frozen'
    
    def can_transact(self):
        """Check if account can perform transactions."""
        return self.status == 'active'
    
    def freeze_account(self):
        """Freeze the account."""
        self.status = 'frozen'
        self.save()
    
    def unfreeze_account(self):
        """Unfreeze the account (set to active)."""
        self.status = 'active'
        self.save()
    
    def close_account(self):
        """Close the account."""
        self.status = 'closed'
        self.save()
    
    def approve_account(self):
        """Approve a pending account."""
        if self.status == 'pending':
            self.status = 'active'
            self.save()
    
    def __str__(self):
        return f"{self.account_number} - {self.user.username} ({self.get_account_type_display()})"
