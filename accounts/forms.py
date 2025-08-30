"""
Forms for the accounts app.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from .models import User, BankAccount


class UserRegistrationForm(UserCreationForm):
    """
    User registration form with additional fields and validation.
    Extends Django's UserCreationForm to include required fields for banking platform.
    """
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        }),
        help_text='Required. Enter your first name.'
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        }),
        help_text='Required. Enter your last name.'
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
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
        
        # Add CSS classes and placeholders to inherited fields
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
        
        # Update help texts
        self.fields['username'].help_text = 'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
        self.fields['password1'].help_text = 'Your password must contain at least 8 characters.'
        self.fields['password2'].help_text = 'Enter the same password as before, for verification.'
    
    def clean_email(self):
        """Validate that email is unique."""
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise ValidationError('A user with this email address already exists.')
        return email
    
    def clean_username(self):
        """Validate that username is unique and meets requirements."""
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username=username).exists():
            raise ValidationError('A user with this username already exists.')
        return username
    
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


class UserLoginForm(forms.Form):
    """
    User login form with validation.
    """
    
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username'
        }),
        help_text='Enter your username.'
    )
    
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        }),
        help_text='Enter your password.'
    )
    
    def clean(self):
        """Validate user credentials."""
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        
        if username and password:
            # First check if user exists and password is correct
            try:
                user = User.objects.get(username=username)
                if not user.check_password(password):
                    raise ValidationError('Invalid username or password.')
                elif not user.is_active:
                    raise ValidationError('This account is inactive.')
            except User.DoesNotExist:
                raise ValidationError('Invalid username or password.')
        
        return cleaned_data