"""
Forms for the transactions app.
"""
from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from accounts.models import BankAccount


class DepositForm(forms.Form):
    """
    Form for handling deposit transactions.
    """
    
    amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount to deposit',
            'step': '0.01',
            'min': '0.01'
        }),
        help_text='Enter the amount you want to deposit (minimum $0.01).'
    )
    
    description = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Optional description (e.g., Salary, Gift, etc.)'
        }),
        help_text='Optional description for this deposit.'
    )
    
    def clean_amount(self):
        """Validate deposit amount."""
        amount = self.cleaned_data.get('amount')
        
        if amount is None:
            raise ValidationError('Please enter a valid amount.')
        
        if amount <= 0:
            raise ValidationError('Deposit amount must be greater than zero.')
        
        # Set reasonable maximum deposit limit for security
        max_deposit = Decimal('100000.00')  # $100,000 max per transaction
        if amount > max_deposit:
            raise ValidationError(f'Maximum deposit amount is ${max_deposit:,.2f} per transaction.')
        
        return amount
    
    def clean_description(self):
        """Clean and validate description."""
        description = self.cleaned_data.get('description', '').strip()
        
        # If no description provided, set default
        if not description:
            description = 'Cash deposit'
        
        return description


class WithdrawalForm(forms.Form):
    """
    Form for handling withdrawal transactions.
    """
    
    amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount to withdraw',
            'step': '0.01',
            'min': '0.01'
        }),
        help_text='Enter the amount you want to withdraw (minimum $0.01).'
    )
    
    description = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Optional description (e.g., ATM withdrawal, Cash, etc.)'
        }),
        help_text='Optional description for this withdrawal.'
    )
    
    def __init__(self, *args, **kwargs):
        self.account = kwargs.pop('account', None)
        super().__init__(*args, **kwargs)
    
    def clean_amount(self):
        """Validate withdrawal amount."""
        amount = self.cleaned_data.get('amount')
        
        if amount is None:
            raise ValidationError('Please enter a valid amount.')
        
        if amount <= 0:
            raise ValidationError('Withdrawal amount must be greater than zero.')
        
        # Check if account has sufficient balance
        if self.account and amount > self.account.balance:
            raise ValidationError(
                f'Insufficient funds. Your current balance is ${self.account.balance:,.2f}.'
            )
        
        # Set reasonable maximum withdrawal limit for security
        max_withdrawal = Decimal('10000.00')  # $10,000 max per transaction
        if amount > max_withdrawal:
            raise ValidationError(f'Maximum withdrawal amount is ${max_withdrawal:,.2f} per transaction.')
        
        return amount
    
    def clean_description(self):
        """Clean and validate description."""
        description = self.cleaned_data.get('description', '').strip()
        
        # If no description provided, set default
        if not description:
            description = 'Cash withdrawal'
        
        return description


class TransferForm(forms.Form):
    """
    Form for handling transfer transactions.
    """
    
    recipient_account_number = forms.CharField(
        max_length=12,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter recipient account number',
            'pattern': '[0-9]{12}',
            'title': 'Account number must be exactly 12 digits'
        }),
        help_text='Enter the 12-digit account number of the recipient.'
    )
    
    amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount to transfer',
            'step': '0.01',
            'min': '0.01'
        }),
        help_text='Enter the amount you want to transfer (minimum $0.01).'
    )
    
    description = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Optional description (e.g., Payment, Gift, etc.)'
        }),
        help_text='Optional description for this transfer.'
    )
    
    def __init__(self, *args, **kwargs):
        self.sender_account = kwargs.pop('sender_account', None)
        super().__init__(*args, **kwargs)
    
    def clean_recipient_account_number(self):
        """Validate recipient account number."""
        account_number = self.cleaned_data.get('recipient_account_number', '').strip()
        
        if not account_number:
            raise ValidationError('Please enter a recipient account number.')
        
        # Validate format
        if not BankAccount.is_valid_account_number(account_number):
            raise ValidationError('Account number must be exactly 12 digits and cannot start with 0.')
        
        # Check if account exists
        try:
            recipient_account = BankAccount.objects.get(account_number=account_number)
        except BankAccount.DoesNotExist:
            raise ValidationError('Recipient account not found. Please check the account number.')
        
        # Check if recipient account is active
        if not recipient_account.can_transact():
            raise ValidationError('Recipient account is not active and cannot receive transfers.')
        
        # Check if trying to transfer to same account
        if self.sender_account and recipient_account == self.sender_account:
            raise ValidationError('Cannot transfer money to your own account.')
        
        return account_number
    
    def clean_amount(self):
        """Validate transfer amount."""
        amount = self.cleaned_data.get('amount')
        
        if amount is None:
            raise ValidationError('Please enter a valid amount.')
        
        if amount <= 0:
            raise ValidationError('Transfer amount must be greater than zero.')
        
        # Check if sender account has sufficient balance
        if self.sender_account and amount > self.sender_account.balance:
            raise ValidationError(
                f'Insufficient funds. Your current balance is ${self.sender_account.balance:,.2f}.'
            )
        
        # Set reasonable maximum transfer limit for security
        max_transfer = Decimal('50000.00')  # $50,000 max per transaction
        if amount > max_transfer:
            raise ValidationError(f'Maximum transfer amount is ${max_transfer:,.2f} per transaction.')
        
        return amount
    
    def clean_description(self):
        """Clean and validate description."""
        description = self.cleaned_data.get('description', '').strip()
        
        # If no description provided, set default
        if not description:
            description = 'Money transfer'
        
        return description
    
    def get_recipient_account(self):
        """Get the recipient account object."""
        account_number = self.cleaned_data.get('recipient_account_number')
        if account_number:
            try:
                return BankAccount.objects.get(account_number=account_number)
            except BankAccount.DoesNotExist:
                return None
        return None