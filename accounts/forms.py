"""
Forms for the accounts app.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils.html import escape
from .models import User, BankAccount
from core.security import SecurityValidator, sanitize_input, RateLimitMixin


class UserRegistrationForm(UserCreationForm):
    """
    User registration form with additional fields and validation.
    Extends Django's UserCreationForm to include required fields for banking platform.
    Enhanced with comprehensive security validation.
    """
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name',
            'autocomplete': 'given-name'
        }),
        help_text='Required. Enter your first name.'
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name',
            'autocomplete': 'family-name'
        }),
        help_text='Required. Enter your last name.'
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email'
        }),
        help_text='Required. Enter a valid email address.'
    )
    
    account_type = forms.ChoiceField(
        choices=BankAccount.ACCOUNT_TYPES,
        required=True,
        initial='savings',
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        help_text='Choose your preferred account type.'
    )
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'account_type')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes and placeholders to inherited fields for Bootstrap 5 floating labels
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username',
            'autocomplete': 'username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password',
            'autocomplete': 'new-password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password',
            'autocomplete': 'new-password'
        })
        
        # Update form field widgets for Bootstrap 5 compatibility
        self.fields['first_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'First Name',
            'autocomplete': 'given-name'
        })
        self.fields['last_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Last Name',
            'autocomplete': 'family-name'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Email Address',
            'autocomplete': 'email'
        })
        self.fields['account_type'].widget.attrs.update({
            'class': 'form-select'
        })
        
        # Update help texts with security requirements
        self.fields['username'].help_text = 'Required. 3-30 characters. Letters, digits, dots, hyphens, and underscores only.'
        self.fields['password1'].help_text = 'Must be 8+ characters with uppercase, lowercase, digit, and special character.'
        self.fields['password2'].help_text = 'Enter the same password as before, for verification.'
    
    def clean_first_name(self):
        """Validate and sanitize first name."""
        first_name = self.cleaned_data.get('first_name', '').strip()
        
        if not first_name:
            raise ValidationError('First name is required.')
        
        # Sanitize input
        first_name = sanitize_input(first_name)
        
        # Validate length and characters
        if len(first_name) < 2:
            raise ValidationError('First name must be at least 2 characters long.')
        
        if not first_name.replace(' ', '').replace('-', '').replace("'", '').isalpha():
            raise ValidationError('First name can only contain letters, spaces, hyphens, and apostrophes.')
        
        return first_name
    
    def clean_last_name(self):
        """Validate and sanitize last name."""
        last_name = self.cleaned_data.get('last_name', '').strip()
        
        if not last_name:
            raise ValidationError('Last name is required.')
        
        # Sanitize input
        last_name = sanitize_input(last_name)
        
        # Validate length and characters
        if len(last_name) < 2:
            raise ValidationError('Last name must be at least 2 characters long.')
        
        if not last_name.replace(' ', '').replace('-', '').replace("'", '').isalpha():
            raise ValidationError('Last name can only contain letters, spaces, hyphens, and apostrophes.')
        
        return last_name
    
    def clean_email(self):
        """Validate that email is unique and secure."""
        email = self.cleaned_data.get('email', '').strip().lower()
        
        if not email:
            raise ValidationError('Email address is required.')
        
        # Sanitize input
        email = sanitize_input(email)
        
        # Check for uniqueness
        if User.objects.filter(email=email).exists():
            raise ValidationError('A user with this email address already exists.')
        
        # Additional email security checks
        if len(email) > 254:  # RFC 5321 limit
            raise ValidationError('Email address is too long.')
        
        # Check for suspicious patterns
        suspicious_patterns = ['test', 'temp', 'fake', 'spam', 'noreply']
        if any(pattern in email.lower() for pattern in suspicious_patterns):
            raise ValidationError('Please use a valid email address.')
        
        return email
    
    def clean_username(self):
        """Validate that username is unique and meets security requirements."""
        username = self.cleaned_data.get('username', '').strip()
        
        if not username:
            raise ValidationError('Username is required.')
        
        # Sanitize input
        username = sanitize_input(username)
        
        # Use security validator
        is_valid, errors = SecurityValidator.validate_username_security(username)
        if not is_valid:
            raise ValidationError(errors)
        
        # Check for uniqueness
        if User.objects.filter(username=username).exists():
            raise ValidationError('A user with this username already exists.')
        
        return username
    
    def clean_password1(self):
        """Validate password strength."""
        password = self.cleaned_data.get('password1')
        
        if not password:
            raise ValidationError('Password is required.')
        
        # Use security validator for enhanced password validation
        is_valid, errors = SecurityValidator.validate_password_strength(password)
        if not is_valid:
            raise ValidationError(errors)
        
        return password
    
    def save(self, commit=True):
        """Save the user and create associated bank account."""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Create bank account for the user
            BankAccount.objects.create(
                user=user,
                account_type=self.cleaned_data['account_type'],
                status='pending'  # Account starts as pending approval
            )
        
        return user


class UserLoginForm(forms.Form, RateLimitMixin):
    """
    User login form with enhanced security validation.
    """
    
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username',
            'autocomplete': 'username'
        }),
        help_text='Enter your username.'
    )
    
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'autocomplete': 'current-password'
        }),
        help_text='Enter your password.'
    )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
    
    def clean_username(self):
        """Validate and sanitize username."""
        username = self.cleaned_data.get('username', '').strip()
        
        if not username:
            raise ValidationError('Username is required.')
        
        # Sanitize input
        username = sanitize_input(username)
        
        # Basic validation
        if len(username) > 150:
            raise ValidationError('Username is too long.')
        
        return username
    
    def clean(self):
        """Validate user credentials with security checks."""
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        
        if not username or not password:
            raise ValidationError('Both username and password are required.')
        
        # Check rate limiting if request is available
        if self.request and self.is_rate_limited(self.request, 'login', limit=5, window=300):
            self.log_security_event(self.request, 'login_rate_limit_exceeded', {
                'username': username[:10] + '...' if len(username) > 10 else username
            })
            raise ValidationError('Too many login attempts. Please try again in 5 minutes.')
        
        # Validate credentials
        try:
            user = User.objects.get(username=username)
            if not user.check_password(password):
                if self.request:
                    self.log_security_event(self.request, 'invalid_login_attempt', {
                        'username': username[:10] + '...' if len(username) > 10 else username,
                        'reason': 'invalid_password'
                    })
                raise ValidationError('Invalid username or password.')
            elif not user.is_active:
                if self.request:
                    self.log_security_event(self.request, 'inactive_account_login_attempt', {
                        'username': username[:10] + '...' if len(username) > 10 else username
                    })
                raise ValidationError('This account is inactive. Please contact support.')
        except User.DoesNotExist:
            if self.request:
                self.log_security_event(self.request, 'invalid_login_attempt', {
                    'username': username[:10] + '...' if len(username) > 10 else username,
                    'reason': 'user_not_found'
                })
            raise ValidationError('Invalid username or password.')
        
        return cleaned_data