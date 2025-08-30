"""
Views for the accounts app.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponseRedirect
from .forms import UserRegistrationForm, UserLoginForm
from .models import BankAccount


@csrf_protect
@never_cache
def register_view(request):
    """
    User registration view with automatic bank account generation.
    
    Handles user registration form submission and creates a bank account
    automatically upon successful registration.
    """
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                messages.success(
                    request, 
                    f'Registration successful! Your account has been created and is pending approval. '
                    f'Your account number will be available once approved.'
                )
                # Redirect to login page after successful registration
                return redirect('accounts:login')
            except Exception as e:
                messages.error(
                    request,
                    'An error occurred during registration. Please try again.'
                )
        else:
            messages.error(
                request,
                'Please correct the errors below.'
            )
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {
        'form': form,
        'title': 'Register - Banking Platform'
    })


@csrf_protect
@never_cache
def login_view(request):
    """
    User login view with session management.
    
    Handles user authentication and redirects to dashboard upon success.
    """
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name}!')
                
                # Redirect to next page if specified, otherwise to dashboard
                next_page = request.GET.get('next', 'accounts:dashboard')
                return redirect(next_page)
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {
        'form': form,
        'title': 'Login - Banking Platform'
    })


@never_cache
def logout_view(request):
    """
    User logout view with session clearing.
    
    Logs out the user and clears their session.
    """
    if request.user.is_authenticated:
        username = request.user.first_name or request.user.username
        logout(request)
        messages.success(request, f'Goodbye, {username}! You have been logged out successfully.')
    
    return redirect('accounts:login')


@login_required
@never_cache
def dashboard_view(request):
    """
    User dashboard view with account information display.
    
    Shows user's bank account details, balance, and navigation menu.
    Requires authentication.
    """
    try:
        # Get user's bank account (assuming one account per user for now)
        bank_account = BankAccount.objects.filter(user=request.user).first()
        
        if not bank_account:
            messages.warning(
                request,
                'No bank account found. Please contact support.'
            )
        
        context = {
            'title': 'Dashboard - Banking Platform',
            'user': request.user,
            'bank_account': bank_account,
        }
        
        return render(request, 'accounts/dashboard.html', context)
        
    except Exception as e:
        messages.error(
            request,
            'An error occurred while loading your dashboard. Please try again.'
        )
        return render(request, 'accounts/dashboard.html', {
            'title': 'Dashboard - Banking Platform',
            'user': request.user,
            'bank_account': None,
        })
