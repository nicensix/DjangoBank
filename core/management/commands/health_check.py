"""
Health check management command for Django Banking Platform.
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import sys
import time


class Command(BaseCommand):
    help = 'Perform health checks on the banking platform'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            choices=['text', 'json'],
            default='text',
            help='Output format (default: text)'
        )

    def handle(self, *args, **options):
        """Run health checks and report status."""
        checks = [
            ('Database', self.check_database),
            ('Cache', self.check_cache),
            ('Settings', self.check_settings),
            ('Static Files', self.check_static_files),
        ]

        results = {}
        all_healthy = True

        for check_name, check_func in checks:
            try:
                start_time = time.time()
                status, message = check_func()
                duration = time.time() - start_time
                
                results[check_name] = {
                    'status': 'healthy' if status else 'unhealthy',
                    'message': message,
                    'duration_ms': round(duration * 1000, 2)
                }
                
                if not status:
                    all_healthy = False
                    
            except Exception as e:
                results[check_name] = {
                    'status': 'error',
                    'message': str(e),
                    'duration_ms': 0
                }
                all_healthy = False

        # Output results
        if options['format'] == 'json':
            import json
            output = {
                'overall_status': 'healthy' if all_healthy else 'unhealthy',
                'checks': results
            }
            self.stdout.write(json.dumps(output, indent=2))
        else:
            self.stdout.write(f"🏦 Banking Platform Health Check")
            self.stdout.write("=" * 35)
            
            for check_name, result in results.items():
                status_icon = "✅" if result['status'] == 'healthy' else "❌"
                self.stdout.write(
                    f"{status_icon} {check_name}: {result['message']} "
                    f"({result['duration_ms']}ms)"
                )
            
            self.stdout.write("")
            overall_icon = "✅" if all_healthy else "❌"
            overall_status = "HEALTHY" if all_healthy else "UNHEALTHY"
            self.stdout.write(f"{overall_icon} Overall Status: {overall_status}")

        # Exit with appropriate code
        sys.exit(0 if all_healthy else 1)

    def check_database(self):
        """Check database connectivity."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True, "Database connection successful"
        except Exception as e:
            return False, f"Database connection failed: {str(e)}"

    def check_cache(self):
        """Check cache connectivity."""
        try:
            test_key = 'health_check_test'
            test_value = 'test_value'
            
            cache.set(test_key, test_value, 30)
            retrieved_value = cache.get(test_key)
            
            if retrieved_value == test_value:
                cache.delete(test_key)
                return True, "Cache is working"
            else:
                return False, "Cache set/get mismatch"
                
        except Exception as e:
            return False, f"Cache error: {str(e)}"

    def check_settings(self):
        """Check critical settings."""
        issues = []
        
        # Check SECRET_KEY
        if not settings.SECRET_KEY or settings.SECRET_KEY == 'django-insecure-default':
            issues.append("SECRET_KEY not set or using default")
        
        # Check DEBUG setting in production
        if not settings.DEBUG and hasattr(settings, 'ENVIRONMENT'):
            if settings.ENVIRONMENT == 'production' and settings.DEBUG:
                issues.append("DEBUG should be False in production")
        
        # Check ALLOWED_HOSTS
        if not settings.DEBUG and not settings.ALLOWED_HOSTS:
            issues.append("ALLOWED_HOSTS not configured for production")
        
        if issues:
            return False, f"Settings issues: {', '.join(issues)}"
        else:
            return True, "Settings configuration OK"

    def check_static_files(self):
        """Check static files configuration."""
        try:
            if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
                import os
                if os.path.exists(settings.STATIC_ROOT):
                    return True, "Static files directory exists"
                else:
                    return False, "Static files directory not found"
            else:
                return True, "Static files configuration OK (development)"
        except Exception as e:
            return False, f"Static files check failed: {str(e)}"