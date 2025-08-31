from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from accounts.models import User, BankAccount
from transactions.models import Transaction
from .models import AdminAction


def is_admin_user(user):
    """Check if user is admin (staff or superuser)."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@login_required
@user_passes_test(is_admin_user, login_url='accounts:login')
def admin_dashboard(request):
    """
    Admin dashboard view with user and account overview.
    
    Displays key metrics and recent activities for administrative oversight.
    Requirements: 8.1, 8.2
    """
    # Get current date for filtering
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # User statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    new_users_this_week = User.objects.filter(date_joined__date__gte=week_ago).count()
    new_users_this_month = User.objects.filter(date_joined__date__gte=month_ago).count()
    
    # Account statistics
    total_accounts = BankAccount.objects.count()
    active_accounts = BankAccount.objects.filter(status='active').count()
    pending_accounts = BankAccount.objects.filter(status='pending').count()
    frozen_accounts = BankAccount.objects.filter(status='frozen').count()
    closed_accounts = BankAccount.objects.filter(status='closed').count()
    
    # Calculate total system balance
    total_balance = BankAccount.objects.filter(
        status__in=['active', 'frozen']
    ).aggregate(
        total=Sum('balance')
    )['total'] or 0
    
    # Transaction statistics
    total_transactions = Transaction.objects.count()
    transactions_today = Transaction.objects.filter(timestamp__date=today).count()
    transactions_this_week = Transaction.objects.filter(timestamp__date__gte=week_ago).count()
    transactions_this_month = Transaction.objects.filter(timestamp__date__gte=month_ago).count()
    
    # Transaction volume (amount)
    transaction_volume_today = Transaction.objects.filter(
        timestamp__date=today
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    transaction_volume_week = Transaction.objects.filter(
        timestamp__date__gte=week_ago
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Recent activities
    recent_users = User.objects.filter(
        date_joined__date__gte=week_ago
    ).order_by('-date_joined')[:5]
    
    recent_accounts = BankAccount.objects.filter(
        created_at__date__gte=week_ago
    ).order_by('-created_at')[:5]
    
    recent_transactions = Transaction.objects.order_by('-timestamp')[:10]
    
    recent_admin_actions = AdminAction.objects.order_by('-timestamp')[:10]
    
    # Accounts requiring attention
    pending_approval_accounts = BankAccount.objects.filter(
        status='pending'
    ).order_by('created_at')[:10]
    
    # High-value transactions (over $10,000)
    high_value_transactions = Transaction.objects.filter(
        amount__gte=10000,
        timestamp__date__gte=week_ago
    ).order_by('-timestamp')[:5]
    
    context = {
        # User statistics
        'total_users': total_users,
        'active_users': active_users,
        'new_users_this_week': new_users_this_week,
        'new_users_this_month': new_users_this_month,
        
        # Account statistics
        'total_accounts': total_accounts,
        'active_accounts': active_accounts,
        'pending_accounts': pending_accounts,
        'frozen_accounts': frozen_accounts,
        'closed_accounts': closed_accounts,
        'total_balance': total_balance,
        
        # Transaction statistics
        'total_transactions': total_transactions,
        'transactions_today': transactions_today,
        'transactions_this_week': transactions_this_week,
        'transactions_this_month': transactions_this_month,
        'transaction_volume_today': transaction_volume_today,
        'transaction_volume_week': transaction_volume_week,
        
        # Recent activities
        'recent_users': recent_users,
        'recent_accounts': recent_accounts,
        'recent_transactions': recent_transactions,
        'recent_admin_actions': recent_admin_actions,
        
        # Items requiring attention
        'pending_approval_accounts': pending_approval_accounts,
        'high_value_transactions': high_value_transactions,
    }
    
    return render(request, 'admin_panel/dashboard.html', context)
