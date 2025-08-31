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


@login_required
@user_passes_test(is_admin_user, login_url='accounts:login')
def user_management(request):
    """
    User management view with account listing and user operations.
    
    Allows admins to view, activate, deactivate users and manage their accounts.
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
    """
    # Get search and filter parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', 'all')
    
    # Base queryset
    users = User.objects.all().prefetch_related('bank_accounts')
    
    # Apply search filter
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Apply status filter
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    elif status_filter == 'staff':
        users = users.filter(is_staff=True)
    
    # Order by date joined (newest first)
    users = users.order_by('-date_joined')
    
    # Get statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = User.objects.filter(is_active=False).count()
    staff_users = User.objects.filter(is_staff=True).count()
    
    context = {
        'users': users,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'staff_users': staff_users,
    }
    
    return render(request, 'admin_panel/user_management.html', context)


@login_required
@user_passes_test(is_admin_user, login_url='accounts:login')
def account_management(request):
    """
    Account management view with account listing and operations.
    
    Allows admins to view, approve, freeze, unfreeze, and close accounts.
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
    """
    # Get search and filter parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', 'all')
    account_type_filter = request.GET.get('account_type', 'all')
    
    # Base queryset
    accounts = BankAccount.objects.select_related('user').all()
    
    # Apply search filter
    if search_query:
        accounts = accounts.filter(
            Q(account_number__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    # Apply status filter
    if status_filter != 'all':
        accounts = accounts.filter(status=status_filter)
    
    # Apply account type filter
    if account_type_filter != 'all':
        accounts = accounts.filter(account_type=account_type_filter)
    
    # Order by creation date (newest first)
    accounts = accounts.order_by('-created_at')
    
    # Get statistics
    total_accounts = BankAccount.objects.count()
    active_accounts = BankAccount.objects.filter(status='active').count()
    pending_accounts = BankAccount.objects.filter(status='pending').count()
    frozen_accounts = BankAccount.objects.filter(status='frozen').count()
    closed_accounts = BankAccount.objects.filter(status='closed').count()
    
    context = {
        'accounts': accounts,
        'search_query': search_query,
        'status_filter': status_filter,
        'account_type_filter': account_type_filter,
        'total_accounts': total_accounts,
        'active_accounts': active_accounts,
        'pending_accounts': pending_accounts,
        'frozen_accounts': frozen_accounts,
        'closed_accounts': closed_accounts,
        'account_statuses': BankAccount.ACCOUNT_STATUS,
        'account_types': BankAccount.ACCOUNT_TYPES,
    }
    
    return render(request, 'admin_panel/account_management.html', context)


@login_required
@user_passes_test(is_admin_user, login_url='accounts:login')
def toggle_user_status(request, user_id):
    """
    Toggle user active status (activate/deactivate).
    
    Requirements: 8.3, 8.4, 8.5
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('admin_panel:user_management')
    
    try:
        user = User.objects.get(id=user_id)
        
        # Prevent deactivating superusers
        if user.is_superuser and user.is_active:
            messages.error(request, 'Cannot deactivate superuser accounts.')
            return redirect('admin_panel:user_management')
        
        # Toggle status
        old_status = user.is_active
        user.is_active = not user.is_active
        user.save()
        
        # Log the action
        action_type = 'user_activate' if user.is_active else 'user_deactivate'
        reason = request.POST.get('reason', '')
        
        if user.is_active:
            AdminAction.log_user_activate(request.user, user, reason)
            messages.success(request, f'User {user.username} has been activated.')
        else:
            AdminAction.log_user_deactivate(request.user, user, reason)
            messages.success(request, f'User {user.username} has been deactivated.')
        
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
    except Exception as e:
        messages.error(request, f'Error updating user status: {str(e)}')
    
    return redirect('admin_panel:user_management')


@login_required
@user_passes_test(is_admin_user, login_url='accounts:login')
def approve_account(request, account_id):
    """
    Approve a pending bank account.
    
    Requirements: 8.3, 8.4, 8.5
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('admin_panel:account_management')
    
    try:
        account = BankAccount.objects.get(id=account_id)
        
        if account.status != 'pending':
            messages.error(request, 'Only pending accounts can be approved.')
            return redirect('admin_panel:account_management')
        
        # Approve the account
        account.approve_account()
        
        # Log the action
        reason = request.POST.get('reason', '')
        AdminAction.log_account_approve(request.user, account, reason)
        
        messages.success(request, f'Account {account.account_number} has been approved.')
        
    except BankAccount.DoesNotExist:
        messages.error(request, 'Account not found.')
    except Exception as e:
        messages.error(request, f'Error approving account: {str(e)}')
    
    return redirect('admin_panel:account_management')


@login_required
@user_passes_test(is_admin_user, login_url='accounts:login')
def freeze_account(request, account_id):
    """
    Freeze a bank account.
    
    Requirements: 8.3, 8.4, 8.5
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('admin_panel:account_management')
    
    try:
        account = BankAccount.objects.get(id=account_id)
        
        if account.status == 'frozen':
            messages.error(request, 'Account is already frozen.')
            return redirect('admin_panel:account_management')
        
        if account.status == 'closed':
            messages.error(request, 'Cannot freeze a closed account.')
            return redirect('admin_panel:account_management')
        
        # Freeze the account
        account.freeze_account()
        
        # Log the action
        reason = request.POST.get('reason', '')
        AdminAction.log_account_freeze(request.user, account, reason)
        
        messages.success(request, f'Account {account.account_number} has been frozen.')
        
    except BankAccount.DoesNotExist:
        messages.error(request, 'Account not found.')
    except Exception as e:
        messages.error(request, f'Error freezing account: {str(e)}')
    
    return redirect('admin_panel:account_management')


@login_required
@user_passes_test(is_admin_user, login_url='accounts:login')
def unfreeze_account(request, account_id):
    """
    Unfreeze a bank account.
    
    Requirements: 8.3, 8.4, 8.5
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('admin_panel:account_management')
    
    try:
        account = BankAccount.objects.get(id=account_id)
        
        if account.status != 'frozen':
            messages.error(request, 'Only frozen accounts can be unfrozen.')
            return redirect('admin_panel:account_management')
        
        # Unfreeze the account
        account.unfreeze_account()
        
        # Log the action
        reason = request.POST.get('reason', '')
        AdminAction.log_account_unfreeze(request.user, account, reason)
        
        messages.success(request, f'Account {account.account_number} has been unfrozen.')
        
    except BankAccount.DoesNotExist:
        messages.error(request, 'Account not found.')
    except Exception as e:
        messages.error(request, f'Error unfreezing account: {str(e)}')
    
    return redirect('admin_panel:account_management')


@login_required
@user_passes_test(is_admin_user, login_url='accounts:login')
def close_account(request, account_id):
    """
    Close a bank account.
    
    Requirements: 8.3, 8.4, 8.5
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('admin_panel:account_management')
    
    try:
        account = BankAccount.objects.get(id=account_id)
        
        if account.status == 'closed':
            messages.error(request, 'Account is already closed.')
            return redirect('admin_panel:account_management')
        
        # Check if account has balance
        if account.balance > 0:
            messages.error(request, 'Cannot close account with positive balance. Please transfer funds first.')
            return redirect('admin_panel:account_management')
        
        # Close the account
        account.close_account()
        
        # Log the action
        reason = request.POST.get('reason', '')
        AdminAction.log_account_close(request.user, account, reason)
        
        messages.success(request, f'Account {account.account_number} has been closed.')
        
    except BankAccount.DoesNotExist:
        messages.error(request, 'Account not found.')
    except Exception as e:
        messages.error(request, f'Error closing account: {str(e)}')
    
    return redirect('admin_panel:account_management')


@login_required
@user_passes_test(is_admin_user, login_url='accounts:login')
def transaction_monitoring(request):
    """
    Transaction monitoring view with filtering and flagging capabilities.
    
    Allows admins to monitor transactions, flag suspicious activity, and freeze accounts.
    Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
    """
    # Get search and filter parameters
    search_query = request.GET.get('search', '')
    transaction_type_filter = request.GET.get('transaction_type', 'all')
    amount_min = request.GET.get('amount_min', '')
    amount_max = request.GET.get('amount_max', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    flagged_only = request.GET.get('flagged_only', False)
    
    # Base queryset with related data
    transactions = Transaction.objects.select_related(
        'sender_account__user', 'receiver_account__user'
    ).all()
    
    # Apply search filter
    if search_query:
        transactions = transactions.filter(
            Q(reference_number__icontains=search_query) |
            Q(sender_account__account_number__icontains=search_query) |
            Q(receiver_account__account_number__icontains=search_query) |
            Q(sender_account__user__username__icontains=search_query) |
            Q(receiver_account__user__username__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Apply transaction type filter
    if transaction_type_filter != 'all':
        transactions = transactions.filter(transaction_type=transaction_type_filter)
    
    # Apply amount filters
    if amount_min:
        try:
            transactions = transactions.filter(amount__gte=float(amount_min))
        except ValueError:
            pass
    
    if amount_max:
        try:
            transactions = transactions.filter(amount__lte=float(amount_max))
        except ValueError:
            pass
    
    # Apply date filters
    if date_from:
        try:
            from datetime import datetime
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            transactions = transactions.filter(timestamp__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            from datetime import datetime
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            transactions = transactions.filter(timestamp__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Order by timestamp (newest first)
    transactions = transactions.order_by('-timestamp')
    
    # Get statistics
    total_transactions = Transaction.objects.count()
    today_transactions = Transaction.objects.filter(timestamp__date=timezone.now().date()).count()
    
    # High-value transactions (over $10,000)
    high_value_transactions = Transaction.objects.filter(amount__gte=10000).count()
    
    # Recent high-value transactions (last 24 hours)
    from datetime import timedelta
    yesterday = timezone.now() - timedelta(days=1)
    recent_high_value = Transaction.objects.filter(
        amount__gte=10000,
        timestamp__gte=yesterday
    ).count()
    
    # Suspicious patterns detection
    suspicious_transactions = []
    
    # Find accounts with multiple large transactions in short time
    from django.db.models import Count
    frequent_large_senders = Transaction.objects.filter(
        amount__gte=5000,
        timestamp__gte=yesterday,
        sender_account__isnull=False
    ).values('sender_account').annotate(
        count=Count('id')
    ).filter(count__gte=3)
    
    if frequent_large_senders:
        suspicious_accounts = [item['sender_account'] for item in frequent_large_senders]
        suspicious_transactions.extend(
            Transaction.objects.filter(
                sender_account__id__in=suspicious_accounts,
                timestamp__gte=yesterday
            ).order_by('-timestamp')[:10]
        )
    
    # Round-number transactions (potential money laundering)
    round_number_transactions = Transaction.objects.filter(
        amount__in=[1000, 2000, 5000, 10000, 20000, 50000, 100000],
        timestamp__gte=yesterday
    ).order_by('-timestamp')[:5]
    
    suspicious_transactions.extend(round_number_transactions)
    
    # Remove duplicates and limit
    suspicious_transactions = list(set(suspicious_transactions))[:10]
    
    context = {
        'transactions': transactions[:100],  # Limit to 100 for performance
        'search_query': search_query,
        'transaction_type_filter': transaction_type_filter,
        'amount_min': amount_min,
        'amount_max': amount_max,
        'date_from': date_from,
        'date_to': date_to,
        'flagged_only': flagged_only,
        'total_transactions': total_transactions,
        'today_transactions': today_transactions,
        'high_value_transactions': high_value_transactions,
        'recent_high_value': recent_high_value,
        'suspicious_transactions': suspicious_transactions,
        'transaction_types': Transaction.TRANSACTION_TYPES,
    }
    
    return render(request, 'admin_panel/transaction_monitoring.html', context)


@login_required
@user_passes_test(is_admin_user, login_url='accounts:login')
def flag_transaction(request, transaction_id):
    """
    Flag a transaction as suspicious and potentially freeze related accounts.
    
    Requirements: 9.3, 9.4, 9.5
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('admin_panel:transaction_monitoring')
    
    try:
        transaction = Transaction.objects.get(id=transaction_id)
        reason = request.POST.get('reason', '')
        freeze_accounts = request.POST.get('freeze_accounts', False)
        
        # Log the flagging action
        AdminAction.objects.create(
            action_type='balance_adjustment',  # Using this as closest match for transaction flagging
            admin_user=request.user,
            target_account=transaction.sender_account or transaction.receiver_account,
            target_user=(transaction.sender_account or transaction.receiver_account).user,
            description=f"Transaction {transaction.reference_number} flagged as suspicious.",
            reason=reason,
            additional_data={
                'transaction_id': transaction.id,
                'transaction_reference': transaction.reference_number,
                'flagged': True
            }
        )
        
        # Freeze accounts if requested
        if freeze_accounts:
            accounts_frozen = []
            
            if transaction.sender_account and transaction.sender_account.status == 'active':
                transaction.sender_account.freeze_account()
                AdminAction.log_account_freeze(
                    request.user, 
                    transaction.sender_account, 
                    f"Account frozen due to suspicious transaction {transaction.reference_number}. {reason}"
                )
                accounts_frozen.append(transaction.sender_account.account_number)
            
            if (transaction.receiver_account and 
                transaction.receiver_account.status == 'active' and
                transaction.receiver_account != transaction.sender_account):
                transaction.receiver_account.freeze_account()
                AdminAction.log_account_freeze(
                    request.user, 
                    transaction.receiver_account, 
                    f"Account frozen due to suspicious transaction {transaction.reference_number}. {reason}"
                )
                accounts_frozen.append(transaction.receiver_account.account_number)
            
            if accounts_frozen:
                messages.success(
                    request, 
                    f'Transaction flagged and accounts {", ".join(accounts_frozen)} have been frozen.'
                )
            else:
                messages.success(request, 'Transaction flagged successfully.')
        else:
            messages.success(request, 'Transaction flagged for review.')
        
    except Transaction.DoesNotExist:
        messages.error(request, 'Transaction not found.')
    except Exception as e:
        messages.error(request, f'Error flagging transaction: {str(e)}')
    
    return redirect('admin_panel:transaction_monitoring')


@login_required
@user_passes_test(is_admin_user, login_url='accounts:login')
def transaction_detail(request, transaction_id):
    """
    Display detailed information about a specific transaction.
    
    Requirements: 9.1, 9.2
    """
    try:
        transaction = Transaction.objects.select_related(
            'sender_account__user', 'receiver_account__user'
        ).get(id=transaction_id)
        
        # Get related admin actions for this transaction
        related_actions = AdminAction.objects.filter(
            Q(target_account=transaction.sender_account) |
            Q(target_account=transaction.receiver_account)
        ).order_by('-timestamp')[:10]
        
        # Get other transactions from the same accounts (last 10)
        related_transactions = Transaction.objects.filter(
            Q(sender_account__in=[transaction.sender_account, transaction.receiver_account]) |
            Q(receiver_account__in=[transaction.sender_account, transaction.receiver_account])
        ).exclude(id=transaction.id).order_by('-timestamp')[:10]
        
        context = {
            'transaction': transaction,
            'related_actions': related_actions,
            'related_transactions': related_transactions,
        }
        
        return render(request, 'admin_panel/transaction_detail.html', context)
        
    except Transaction.DoesNotExist:
        messages.error(request, 'Transaction not found.')
        return redirect('admin_panel:transaction_monitoring')
