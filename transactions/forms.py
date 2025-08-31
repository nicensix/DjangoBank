"""
Forms for the transactions app.
"""
from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import escape
from accounts.models import BankAccount
from core.security import SecurityValidator, sanitize_input, validate_amount_format, RateLimitMixin


class DepositForm(forms.Form, RateLimitMixin):
    """
    Form for handling deposit transactions with enhanced security.
    """
    
    amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount to deposit',
            'step': '0.01',
            'min': '0.01',
            'autocomplete': 'off'
        }),
        help_text='Enter the amount you want to deposit (minimum $0.01, maximum $100,000).'
    )
    
    description = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Optional description (e.g., Salary, Gift, etc.)',
            'maxlength': '255'
        }),
        help_text='Optional description for this deposit.'
    )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
    
    def clean_amount(self):
        """Validate deposit amount with enhanced security checks."""
        amount = self.cleaned_data.get('amount')
        
        if amount is None:
            raise ValidationError('Please enter a valid amount.')
        
        # Use security validator
        is_valid, errors = SecurityValidator.validate_transaction_amount(amount, 'deposit')
        if not is_valid:
            raise ValidationError(errors)
        
        # Additional format validation
        if not validate_amount_format(amount):
            raise ValidationError('Invalid amount format.')
        
        # Check for suspicious patterns (e.g., repeated deposits)
        if self.request and hasattr(self.request, 'user') and self.request.user.is_authenticated:
            # Log large deposits for monitoring
            if amount > Decimal('10000.00'):
                self.log_security_event(self.request, 'large_deposit_attempt', {
                    'amount': str(amount),
                    'user_id': self.request.user.id
                })
        
        return amount
    
    def clean_description(self):
        """Clean and validate description with security checks."""
        description = self.cleaned_data.get('description', '').strip()
        
        # Sanitize input
        description = sanitize_input(description, allow_html=False)
        
        # If no description provided, set default
        if not description:
            description = 'Cash deposit'
        
        # Validate length
        if len(description) > 255:
            raise ValidationError('Description cannot exceed 255 characters.')
        
        # Check for suspicious content
        suspicious_keywords = ['hack', 'fraud', 'illegal', 'money laundering', 'test']
        if any(keyword in description.lower() for keyword in suspicious_keywords):
            if self.request:
                self.log_security_event(self.request, 'suspicious_transaction_description', {
                    'description': description[:50] + '...' if len(description) > 50 else description
                })
        
        return description


class WithdrawalForm(forms.Form, RateLimitMixin):
    """
    Form for handling withdrawal transactions with enhanced security.
    """
    
    amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount to withdraw',
            'step': '0.01',
            'min': '0.01',
            'autocomplete': 'off'
        }),
        help_text='Enter the amount you want to withdraw (minimum $0.01, maximum $10,000).'
    )
    
    description = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Optional description (e.g., ATM withdrawal, Cash, etc.)',
            'maxlength': '255'
        }),
        help_text='Optional description for this withdrawal.'
    )
    
    def __init__(self, *args, **kwargs):
        self.account = kwargs.pop('account', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
    
    def clean_amount(self):
        """Validate withdrawal amount with enhanced security checks."""
        amount = self.cleaned_data.get('amount')
        
        if amount is None:
            raise ValidationError('Please enter a valid amount.')
        
        # Use security validator
        is_valid, errors = SecurityValidator.validate_transaction_amount(amount, 'withdrawal')
        if not is_valid:
            raise ValidationError(errors)
        
        # Additional format validation
        if not validate_amount_format(amount):
            raise ValidationError('Invalid amount format.')
        
        # Check if account has sufficient balance
        if self.account and amount > self.account.balance:
            # Log insufficient funds attempt
            if self.request:
                self.log_security_event(self.request, 'insufficient_funds_attempt', {
                    'requested_amount': str(amount),
                    'available_balance': str(self.account.balance),
                    'account_id': self.account.id
                })
            raise ValidationError(
                f'Insufficient funds. Your current balance is ${self.account.balance:,.2f}.'
            )
        
        # Check for suspicious withdrawal patterns
        if self.request and hasattr(self.request, 'user') and self.request.user.is_authenticated:
            # Log large withdrawals for monitoring
            if amount > Decimal('5000.00'):
                self.log_security_event(self.request, 'large_withdrawal_attempt', {
                    'amount': str(amount),
                    'user_id': self.request.user.id,
                    'account_id': self.account.id if self.account else None
                })
        
        return amount
    
    def clean_description(self):
        """Clean and validate description with security checks."""
        description = self.cleaned_data.get('description', '').strip()
        
        # Sanitize input
        description = sanitize_input(description, allow_html=False)
        
        # If no description provided, set default
        if not description:
            description = 'Cash withdrawal'
        
        # Validate length
        if len(description) > 255:
            raise ValidationError('Description cannot exceed 255 characters.')
        
        # Check for suspicious content
        suspicious_keywords = ['hack', 'fraud', 'illegal', 'money laundering', 'test']
        if any(keyword in description.lower() for keyword in suspicious_keywords):
            if self.request:
                self.log_security_event(self.request, 'suspicious_transaction_description', {
                    'description': description[:50] + '...' if len(description) > 50 else description
                })
        
        return description


class TransferForm(forms.Form, RateLimitMixin):
    """
    Form for handling transfer transactions with enhanced security.
    """
    
    recipient_account_number = forms.CharField(
        max_length=12,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter recipient account number',
            'pattern': '[0-9]{12}',
            'title': 'Account number must be exactly 12 digits',
            'autocomplete': 'off'
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
            'min': '0.01',
            'autocomplete': 'off'
        }),
        help_text='Enter the amount you want to transfer (minimum $0.01, maximum $50,000).'
    )
    
    description = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Optional description (e.g., Payment, Gift, etc.)',
            'maxlength': '255'
        }),
        help_text='Optional description for this transfer.'
    )
    
    def __init__(self, *args, **kwargs):
        self.sender_account = kwargs.pop('sender_account', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
    
    def clean_recipient_account_number(self):
        """Validate recipient account number with enhanced security."""
        account_number = self.cleaned_data.get('recipient_account_number', '').strip()
        
        if not account_number:
            raise ValidationError('Please enter a recipient account number.')
        
        # Sanitize input
        account_number = sanitize_input(account_number)
        
        # Validate format
        if not BankAccount.is_valid_account_number(account_number):
            # Log invalid account number attempt
            if self.request:
                self.log_security_event(self.request, 'invalid_account_number_attempt', {
                    'attempted_account': account_number[:6] + '...' if len(account_number) > 6 else account_number
                })
            raise ValidationError('Account number must be exactly 12 digits and cannot start with 0.')
        
        # Check if account exists
        try:
            recipient_account = BankAccount.objects.get(account_number=account_number)
        except BankAccount.DoesNotExist:
            # Log non-existent account attempt
            if self.request:
                self.log_security_event(self.request, 'nonexistent_account_transfer_attempt', {
                    'attempted_account': account_number[:6] + '...'
                })
            raise ValidationError('Recipient account not found. Please check the account number.')
        
        # Check if recipient account is active
        if not recipient_account.can_transact():
            # Log inactive account transfer attempt
            if self.request:
                self.log_security_event(self.request, 'inactive_account_transfer_attempt', {
                    'recipient_account': account_number[:6] + '...',
                    'account_status': recipient_account.status
                })
            raise ValidationError('Recipient account is not active and cannot receive transfers.')
        
        # Check if trying to transfer to same account
        if self.sender_account and recipient_account == self.sender_account:
            # Log self-transfer attempt
            if self.request:
                self.log_security_event(self.request, 'self_transfer_attempt', {
                    'account_number': account_number[:6] + '...'
                })
            raise ValidationError('Cannot transfer money to your own account.')
        
        return account_number
    
    def clean_amount(self):
        """Validate transfer amount with enhanced security checks."""
        amount = self.cleaned_data.get('amount')
        
        if amount is None:
            raise ValidationError('Please enter a valid amount.')
        
        # Use security validator
        is_valid, errors = SecurityValidator.validate_transaction_amount(amount, 'transfer')
        if not is_valid:
            raise ValidationError(errors)
        
        # Additional format validation
        if not validate_amount_format(amount):
            raise ValidationError('Invalid amount format.')
        
        # Check if sender account has sufficient balance
        if self.sender_account and amount > self.sender_account.balance:
            # Log insufficient funds attempt
            if self.request:
                self.log_security_event(self.request, 'insufficient_funds_transfer_attempt', {
                    'requested_amount': str(amount),
                    'available_balance': str(self.sender_account.balance),
                    'sender_account_id': self.sender_account.id
                })
            raise ValidationError(
                f'Insufficient funds. Your current balance is ${self.sender_account.balance:,.2f}.'
            )
        
        # Check for suspicious transfer patterns
        if self.request and hasattr(self.request, 'user') and self.request.user.is_authenticated:
            # Log large transfers for monitoring
            if amount > Decimal('10000.00'):
                self.log_security_event(self.request, 'large_transfer_attempt', {
                    'amount': str(amount),
                    'user_id': self.request.user.id,
                    'sender_account_id': self.sender_account.id if self.sender_account else None
                })
        
        return amount
    
    def clean_description(self):
        """Clean and validate description with security checks."""
        description = self.cleaned_data.get('description', '').strip()
        
        # Sanitize input
        description = sanitize_input(description, allow_html=False)
        
        # If no description provided, set default
        if not description:
            description = 'Money transfer'
        
        # Validate length
        if len(description) > 255:
            raise ValidationError('Description cannot exceed 255 characters.')
        
        # Check for suspicious content
        suspicious_keywords = ['hack', 'fraud', 'illegal', 'money laundering', 'ransom', 'blackmail']
        if any(keyword in description.lower() for keyword in suspicious_keywords):
            if self.request:
                self.log_security_event(self.request, 'suspicious_transfer_description', {
                    'description': description[:50] + '...' if len(description) > 50 else description
                })
        
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