"""
Django settings initialization.

This module determines which settings to load based on the DJANGO_SETTINGS_MODULE
environment variable or defaults to development settings.
"""

import os

# Default to development settings if not specified
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'banking_platform.settings.development')