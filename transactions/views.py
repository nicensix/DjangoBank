"""
Views for the transactions app.
"""
import csv
import io
from decimal import Decimal
from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from accounts.models import BankAccount
from .forms import DepositForm, WithdrawalForm, TransferForm
from .models import Transaction

# For PDF generation
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


@login_required
@require_http_methods(["GET", "POST"])
def deposit_view(request):
    """
    Handle deposit transactions.
    
    GET: Display deposit form
    POST: Process deposit transaction
    """
    # Get user's bank account
    try:
        bank_account = BankAccount.objects.get(user=request.user)
    except BankAccount.DoesNotExist:
        messages.error(request, 'No bank account found. Please contact support.')
        return redirect('accounts:dashboard')
    
    # Check if account can perform transactions
    if not bank_account.can_transact():
        messages.error(
            request, 
            f'Your account is {bank_account.get_status_display().lower()} and cannot perform transactions.'
        )
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description']
            
            try:
                # Use database transaction to ensure atomicity
                with transaction.atomic():
                    # Update account balance
                    bank_account.balance += amount
                    bank_account.save()
                    
                    # Create transaction record
                    Transaction.objects.create(
                        transaction_type='deposit',
                        amount=amount,
                        description=description,
                        receiver_account=bank_account,
                        receiver_balance_after=bank_account.balance
                    )
                
                messages.success(
                    request, 
                    f'Successfully deposited ${amount:,.2f}. Your new balance is ${bank_account.balance:,.2f}.'
                )
                return redirect('accounts:dashboard')
                
            except Exception as e:
                messages.error(request, 'An error occurred while processing your deposit. Please try again.')
                # Log the error for debugging (in production, use proper logging)
                print(f"Deposit error: {e}")
    else:
        form = DepositForm()
    
    context = {
        'form': form,
        'bank_account': bank_account,
        'title': 'Deposit Money'
    }
    return render(request, 'transactions/deposit.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def withdrawal_view(request):
    """
    Handle withdrawal transactions.
    
    GET: Display withdrawal form
    POST: Process withdrawal transaction
    """
    # Get user's bank account
    try:
        bank_account = BankAccount.objects.get(user=request.user)
    except BankAccount.DoesNotExist:
        messages.error(request, 'No bank account found. Please contact support.')
        return redirect('accounts:dashboard')
    
    # Check if account can perform transactions
    if not bank_account.can_transact():
        messages.error(
            request, 
            f'Your account is {bank_account.get_status_display().lower()} and cannot perform transactions.'
        )
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        form = WithdrawalForm(request.POST, account=bank_account)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description']
            
            try:
                # Use database transaction to ensure atomicity
                with transaction.atomic():
                    # Update account balance
                    bank_account.balance -= amount
                    bank_account.save()
                    
                    # Create transaction record
                    Transaction.objects.create(
                        transaction_type='withdrawal',
                        amount=amount,
                        description=description,
                        sender_account=bank_account,
                        sender_balance_after=bank_account.balance
                    )
                
                messages.success(
                    request, 
                    f'Successfully withdrew ${amount:,.2f}. Your new balance is ${bank_account.balance:,.2f}.'
                )
                return redirect('accounts:dashboard')
                
            except Exception as e:
                messages.error(request, 'An error occurred while processing your withdrawal. Please try again.')
                # Log the error for debugging (in production, use proper logging)
                print(f"Withdrawal error: {e}")
    else:
        form = WithdrawalForm(account=bank_account)
    
    context = {
        'form': form,
        'bank_account': bank_account,
        'title': 'Withdraw Money'
    }
    return render(request, 'transactions/withdrawal.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def transfer_view(request):
    """
    Handle transfer transactions.
    
    GET: Display transfer form
    POST: Process transfer transaction
    """
    # Get user's bank account
    try:
        sender_account = BankAccount.objects.get(user=request.user)
    except BankAccount.DoesNotExist:
        messages.error(request, 'No bank account found. Please contact support.')
        return redirect('accounts:dashboard')
    
    # Check if account can perform transactions
    if not sender_account.can_transact():
        messages.error(
            request, 
            f'Your account is {sender_account.get_status_display().lower()} and cannot perform transactions.'
        )
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        form = TransferForm(request.POST, sender_account=sender_account)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description']
            recipient_account = form.get_recipient_account()
            
            try:
                # Use database transaction to ensure atomicity
                with transaction.atomic():
                    # Update sender account balance
                    sender_account.balance -= amount
                    sender_account.save()
                    
                    # Update recipient account balance
                    recipient_account.balance += amount
                    recipient_account.save()
                    
                    # Create transaction record
                    Transaction.objects.create(
                        transaction_type='transfer',
                        amount=amount,
                        description=description,
                        sender_account=sender_account,
                        receiver_account=recipient_account,
                        sender_balance_after=sender_account.balance,
                        receiver_balance_after=recipient_account.balance
                    )
                
                messages.success(
                    request, 
                    f'Successfully transferred ${amount:,.2f} to account {recipient_account.account_number}. '
                    f'Your new balance is ${sender_account.balance:,.2f}.'
                )
                return redirect('accounts:dashboard')
                
            except Exception as e:
                messages.error(request, 'An error occurred while processing your transfer. Please try again.')
                # Log the error for debugging (in production, use proper logging)
                print(f"Transfer error: {e}")
    else:
        form = TransferForm(sender_account=sender_account)
    
    context = {
        'form': form,
        'sender_account': sender_account,
        'title': 'Transfer Money'
    }
    return render(request, 'transactions/transfer.html', context)


@login_required
def transaction_history_view(request):
    """
    Display transaction history for the user's account with filtering and pagination.
    
    Supports filtering by:
    - Transaction type (deposit, withdrawal, transfer)
    - Date range (last 7 days, 30 days, 90 days, custom range)
    - Amount range
    
    Features:
    - Pagination (20 transactions per page)
    - Real-time balance calculation after each transaction
    - Proper formatting for different transaction types
    """
    # Get user's bank account
    try:
        bank_account = BankAccount.objects.get(user=request.user)
    except BankAccount.DoesNotExist:
        messages.error(request, 'No bank account found. Please contact support.')
        return redirect('accounts:dashboard')
    
    # Get all transactions for this account
    transactions = Transaction.objects.filter(
        Q(sender_account=bank_account) | Q(receiver_account=bank_account)
    ).order_by('-timestamp')
    
    # Apply filters based on request parameters
    transaction_type = request.GET.get('type', '')
    date_filter = request.GET.get('date_filter', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')
    
    # Filter by transaction type
    if transaction_type and transaction_type in ['deposit', 'withdrawal', 'transfer']:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    # Filter by date range
    if date_filter:
        now = timezone.now()
        if date_filter == '7days':
            start_date_filter = now - timedelta(days=7)
            transactions = transactions.filter(timestamp__gte=start_date_filter)
        elif date_filter == '30days':
            start_date_filter = now - timedelta(days=30)
            transactions = transactions.filter(timestamp__gte=start_date_filter)
        elif date_filter == '90days':
            start_date_filter = now - timedelta(days=90)
            transactions = transactions.filter(timestamp__gte=start_date_filter)
    
    # Filter by custom date range
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            transactions = transactions.filter(timestamp__date__gte=start_date_obj)
        except ValueError:
            messages.warning(request, 'Invalid start date format. Please use YYYY-MM-DD.')
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            transactions = transactions.filter(timestamp__date__lte=end_date_obj)
        except ValueError:
            messages.warning(request, 'Invalid end date format. Please use YYYY-MM-DD.')
    
    # Filter by amount range
    if min_amount:
        try:
            min_amount_decimal = Decimal(min_amount)
            transactions = transactions.filter(amount__gte=min_amount_decimal)
        except (ValueError, TypeError, Exception):
            messages.warning(request, 'Invalid minimum amount format.')
    
    if max_amount:
        try:
            max_amount_decimal = Decimal(max_amount)
            transactions = transactions.filter(amount__lte=max_amount_decimal)
        except (ValueError, TypeError, Exception):
            messages.warning(request, 'Invalid maximum amount format.')
    
    # Pagination
    paginator = Paginator(transactions, 20)  # Show 20 transactions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Prepare transaction data with proper formatting for the account
    transaction_data = []
    for txn in page_obj:
        # Determine the display amount and description for this account
        display_amount = txn.get_display_amount_for_account(bank_account)
        description = txn.get_description_for_account(bank_account)
        
        # Determine the balance after this transaction
        if txn.transaction_type == 'deposit' and txn.receiver_account == bank_account:
            balance_after = txn.receiver_balance_after
        elif txn.transaction_type == 'withdrawal' and txn.sender_account == bank_account:
            balance_after = txn.sender_balance_after
        elif txn.transaction_type == 'transfer':
            if txn.sender_account == bank_account:
                balance_after = txn.sender_balance_after
            else:
                balance_after = txn.receiver_balance_after
        else:
            balance_after = None
        
        transaction_data.append({
            'transaction': txn,
            'display_amount': display_amount,
            'description': description,
            'balance_after': balance_after,
            'is_credit': display_amount > 0,
            'is_debit': display_amount < 0,
        })
    
    # Calculate summary statistics
    total_transactions = transactions.count()
    total_deposits = transactions.filter(
        transaction_type='deposit', 
        receiver_account=bank_account
    ).count()
    total_withdrawals = transactions.filter(
        transaction_type='withdrawal', 
        sender_account=bank_account
    ).count()
    total_transfers_sent = transactions.filter(
        transaction_type='transfer', 
        sender_account=bank_account
    ).count()
    total_transfers_received = transactions.filter(
        transaction_type='transfer', 
        receiver_account=bank_account
    ).count()
    
    context = {
        'bank_account': bank_account,
        'page_obj': page_obj,
        'transaction_data': transaction_data,
        'total_transactions': total_transactions,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'total_transfers_sent': total_transfers_sent,
        'total_transfers_received': total_transfers_received,
        'title': 'Transaction History',
        # Filter values for form persistence
        'current_type': transaction_type,
        'current_date_filter': date_filter,
        'current_start_date': start_date,
        'current_end_date': end_date,
        'current_min_amount': min_amount,
        'current_max_amount': max_amount,
    }
    
    return render(request, 'transactions/history.html', context)


@login_required
def download_csv_statement(request):
    """
    Generate and download CSV statement with transaction data.
    
    Supports date range filtering for statement generation.
    Returns CSV file as HTTP response without permanent storage.
    """
    # Get user's bank account
    try:
        bank_account = BankAccount.objects.get(user=request.user)
    except BankAccount.DoesNotExist:
        messages.error(request, 'No bank account found. Please contact support.')
        return redirect('accounts:dashboard')
    
    # Get date range parameters
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Get all transactions for this account
    transactions = Transaction.objects.filter(
        Q(sender_account=bank_account) | Q(receiver_account=bank_account)
    ).order_by('-timestamp')
    
    # Apply date filtering if provided
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            transactions = transactions.filter(timestamp__date__gte=start_date_obj)
        except ValueError:
            messages.error(request, 'Invalid start date format. Please use YYYY-MM-DD.')
            return redirect('transactions:history')
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            transactions = transactions.filter(timestamp__date__lte=end_date_obj)
        except ValueError:
            messages.error(request, 'Invalid end date format. Please use YYYY-MM-DD.')
            return redirect('transactions:history')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    
    # Generate filename with date range
    filename_parts = ['statement']
    if start_date:
        filename_parts.append(f'from-{start_date}')
    if end_date:
        filename_parts.append(f'to-{end_date}')
    filename_parts.append(f'account-{bank_account.account_number}')
    filename = '_'.join(filename_parts) + '.csv'
    
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Create CSV writer
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Date',
        'Time',
        'Transaction Type',
        'Description',
        'Amount',
        'Balance After',
        'Reference Number'
    ])
    
    # Write transaction data
    for txn in transactions:
        # Determine the display amount and balance for this account
        display_amount = txn.get_display_amount_for_account(bank_account)
        description = txn.get_description_for_account(bank_account)
        
        # Determine the balance after this transaction
        if txn.transaction_type == 'deposit' and txn.receiver_account == bank_account:
            balance_after = txn.receiver_balance_after
        elif txn.transaction_type == 'withdrawal' and txn.sender_account == bank_account:
            balance_after = txn.sender_balance_after
        elif txn.transaction_type == 'transfer':
            if txn.sender_account == bank_account:
                balance_after = txn.sender_balance_after
            else:
                balance_after = txn.receiver_balance_after
        else:
            balance_after = None
        
        writer.writerow([
            txn.timestamp.strftime('%Y-%m-%d'),
            txn.timestamp.strftime('%H:%M:%S'),
            txn.get_transaction_type_display(),
            description,
            f'{display_amount:.2f}',
            f'{balance_after:.2f}' if balance_after is not None else 'N/A',
            txn.reference_number
        ])
    
    return response


@login_required
def download_pdf_statement(request):
    """
    Generate and download PDF statement with proper formatting.
    
    Supports date range filtering for statement generation.
    Returns PDF file as HTTP response without permanent storage.
    """
    if not PDF_AVAILABLE:
        messages.error(request, 'PDF generation is not available. Please install reportlab.')
        return redirect('transactions:history')
    
    # Get user's bank account
    try:
        bank_account = BankAccount.objects.get(user=request.user)
    except BankAccount.DoesNotExist:
        messages.error(request, 'No bank account found. Please contact support.')
        return redirect('accounts:dashboard')
    
    # Get date range parameters
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Get all transactions for this account
    transactions = Transaction.objects.filter(
        Q(sender_account=bank_account) | Q(receiver_account=bank_account)
    ).order_by('-timestamp')
    
    # Apply date filtering if provided
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            transactions = transactions.filter(timestamp__date__gte=start_date_obj)
        except ValueError:
            messages.error(request, 'Invalid start date format. Please use YYYY-MM-DD.')
            return redirect('transactions:history')
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            transactions = transactions.filter(timestamp__date__lte=end_date_obj)
        except ValueError:
            messages.error(request, 'Invalid end date format. Please use YYYY-MM-DD.')
            return redirect('transactions:history')
    
    # Create PDF response
    response = HttpResponse(content_type='application/pdf')
    
    # Generate filename with date range
    filename_parts = ['statement']
    if start_date:
        filename_parts.append(f'from-{start_date}')
    if end_date:
        filename_parts.append(f'to-{end_date}')
    filename_parts.append(f'account-{bank_account.account_number}')
    filename = '_'.join(filename_parts) + '.pdf'
    
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Create PDF document
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    # Build PDF content
    story = []
    
    # Title
    story.append(Paragraph("Banking Platform - Account Statement", title_style))
    story.append(Spacer(1, 20))
    
    # Account information
    account_info = [
        ['Account Holder:', f'{bank_account.user.first_name} {bank_account.user.last_name}'],
        ['Account Number:', bank_account.account_number],
        ['Account Type:', bank_account.get_account_type_display()],
        ['Current Balance:', f'${bank_account.balance:.2f}'],
        ['Statement Date:', timezone.now().strftime('%B %d, %Y')],
    ]
    
    if start_date or end_date:
        date_range = []
        if start_date:
            date_range.append(f'From: {start_date}')
        if end_date:
            date_range.append(f'To: {end_date}')
        account_info.append(['Date Range:', ' | '.join(date_range)])
    
    account_table = Table(account_info, colWidths=[2*inch, 3*inch])
    account_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(account_table)
    story.append(Spacer(1, 30))
    
    # Transaction table
    if transactions.exists():
        story.append(Paragraph("Transaction History", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        # Table headers
        table_data = [
            ['Date', 'Type', 'Description', 'Amount', 'Balance']
        ]
        
        # Add transaction data
        for txn in transactions:
            # Determine the display amount and balance for this account
            display_amount = txn.get_display_amount_for_account(bank_account)
            description = txn.get_description_for_account(bank_account)
            
            # Determine the balance after this transaction
            if txn.transaction_type == 'deposit' and txn.receiver_account == bank_account:
                balance_after = txn.receiver_balance_after
            elif txn.transaction_type == 'withdrawal' and txn.sender_account == bank_account:
                balance_after = txn.sender_balance_after
            elif txn.transaction_type == 'transfer':
                if txn.sender_account == bank_account:
                    balance_after = txn.sender_balance_after
                else:
                    balance_after = txn.receiver_balance_after
            else:
                balance_after = None
            
            # Truncate long descriptions
            if len(description) > 40:
                description = description[:37] + '...'
            
            table_data.append([
                txn.timestamp.strftime('%m/%d/%Y'),
                txn.get_transaction_type_display(),
                description,
                f'${display_amount:.2f}',
                f'${balance_after:.2f}' if balance_after is not None else 'N/A'
            ])
        
        # Create table
        transaction_table = Table(table_data, colWidths=[1*inch, 1*inch, 2.5*inch, 1*inch, 1*inch])
        transaction_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),  # Description left-aligned
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),  # Amount right-aligned
            ('ALIGN', (4, 1), (4, -1), 'RIGHT'),  # Balance right-aligned
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        story.append(transaction_table)
    else:
        story.append(Paragraph("No transactions found for the specified period.", styles['Normal']))
    
    # Add footer
    story.append(Spacer(1, 30))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=1,  # Center alignment
        textColor=colors.grey
    )
    story.append(Paragraph("This statement is generated electronically and does not require a signature.", footer_style))
    story.append(Paragraph("For questions about your account, please contact customer support.", footer_style))
    
    # Build PDF
    doc.build(story)
    
    # Get PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    response.write(pdf_data)
    return response