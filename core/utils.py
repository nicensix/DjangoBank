"""
Utility functions for the banking platform.
"""

import random
import string
from decimal import Decimal
from django.utils import timezone


def generate_account_number():
    """
    Generate a unique 10-digit account number.
    Format: XXXXXXXXXX (10 digits)
    """
    # Generate a 10-digit account number
    account_number = ''.join(random.choices(string.digits, k=10))
    return account_number


def format_currency(amount):
    """
    Format a decimal amount as currency.
    
    Args:
        amount (Decimal): The amount to format
        
    Returns:
        str: Formatted currency string
    """
    if isinstance(amount, (int, float)):
        amount = Decimal(str(amount))
    
    return f"${amount:,.2f}"


def validate_positive_amount(amount):
    """
    Validate that an amount is positive.
    
    Args:
        amount: The amount to validate
        
    Returns:
        bool: True if amount is positive, False otherwise
    """
    try:
        decimal_amount = Decimal(str(amount))
        return decimal_amount > 0
    except (ValueError, TypeError, Exception):
        return False


def get_transaction_display_name(transaction_type):
    """
    Get a user-friendly display name for transaction types.
    
    Args:
        transaction_type (str): The transaction type
        
    Returns:
        str: User-friendly display name
    """
    display_names = {
        'deposit': 'Deposit',
        'withdrawal': 'Withdrawal',
        'transfer_sent': 'Transfer Sent',
        'transfer_received': 'Transfer Received',
    }
    return display_names.get(transaction_type, transaction_type.title())


def log_admin_action(admin_user, action_type, bank_account, description=None):
    """
    Log an administrative action for audit purposes.
    
    Args:
        admin_user: The admin user performing the action
        action_type (str): The type of action being performed
        bank_account: The bank account being affected
        description (str, optional): Additional description
    """
    # This will be implemented when we create the AdminAction model
    # For now, we'll just pass
    pass