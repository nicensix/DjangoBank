# Troubleshooting Guide

## Overview

This guide helps you diagnose and resolve common issues with the Django Banking Platform. Issues are organized by category with step-by-step solutions.

## Quick Diagnostics

### Health Check Command

Run the built-in health check to identify system issues:

```bash
# Basic health check
python manage.py health_check

# Detailed JSON output
python manage.py health_check --format=json
```

### System Status Check

```bash
# Check Django configuration
python manage.py check

# Check deployment readiness
python manage.py check --deploy

# Check database connectivity
python manage.py dbshell
```

## Installation and Setup Issues

### Python Environment Issues

**Problem**: `ModuleNotFoundError` or import errors

**Solution**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt

# Check Python version
python --version  # Should be 3.8+
```

**Problem**: Permission denied errors during installation

**Solution**:
```bash
# Use virtual environment (recommended)
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Or install with user flag
pip install --user -r requirements.txt
```

### Environment Configuration Issues

**Problem**: `SECRET_KEY` not set or Django settings errors

**Solution**:
```bash
# Copy example environment file
cp .env.example .env

# Generate a new secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Set in .env file
SECRET_KEY=your-generated-secret-key-here
```

**Problem**: `DJANGO_SETTINGS_MODULE` not found

**Solution**:
```bash
# Set environment variable
export DJANGO_SETTINGS_MODULE=banking_platform.settings.development

# Or add to .env file
echo "DJANGO_SETTINGS_MODULE=banking_platform.settings.development" >> .env
```

## Database Issues

### Migration Problems

**Problem**: Migration conflicts or errors

**Solution**:
```bash
# Reset migrations (development only)
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete
python manage.py makemigrations
python manage.py migrate

# For production, resolve conflicts manually
python manage.py showmigrations
python manage.py migrate --fake-initial
```

**Problem**: `no such table` errors

**Solution**:
```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# If still failing, check database connection
python manage.py dbshell
```

### Database Connection Issues

**Problem**: `OperationalError: could not connect to server`

**Solution**:
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Start PostgreSQL if stopped
sudo systemctl start postgresql

# Check connection settings in .env
DATABASE_URL=postgresql://username:password@localhost:5432/database_name

# Test connection manually
psql -h localhost -U username -d database_name
```

**Problem**: SQLite database locked

**Solution**:
```bash
# Stop all Django processes
pkill -f "python manage.py runserver"

# Remove lock file if exists
rm db.sqlite3-wal db.sqlite3-shm

# Restart application
python manage.py runserver
```

### Database Performance Issues

**Problem**: Slow database queries

**Solution**:
```bash
# Enable query logging in development
# Add to settings:
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        }
    }
}

# Analyze slow queries
python manage.py shell
>>> from django.db import connection
>>> print(connection.queries)
```

## Authentication and Session Issues

### Login Problems

**Problem**: Users cannot log in with correct credentials

**Solution**:
```bash
# Check user exists and is active
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> user = User.objects.get(username='username')
>>> print(f"Active: {user.is_active}")
>>> print(f"Password valid: {user.check_password('password')}")

# Reset password if needed
python manage.py changepassword username
```

**Problem**: Session expired or invalid session errors

**Solution**:
```bash
# Clear sessions
python manage.py clearsessions

# Check session configuration in settings
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# For development, disable CSRF temporarily
# Add to settings (development only):
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
```

### Permission Issues

**Problem**: Users cannot access admin panel

**Solution**:
```bash
# Make user staff and superuser
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> user = User.objects.get(username='username')
>>> user.is_staff = True
>>> user.is_superuser = True
>>> user.save()

# Or create new superuser
python manage.py createsuperuser
```

## Transaction and Banking Issues

### Transaction Failures

**Problem**: Transactions fail with "Insufficient funds" error

**Solution**:
```bash
# Check account balance
python manage.py shell
>>> from accounts.models import BankAccount
>>> account = BankAccount.objects.get(account_number='ACC123456789012')
>>> print(f"Balance: {account.balance}")
>>> print(f"Status: {account.status}")

# Verify account is active
>>> if account.status != 'Active':
>>>     account.status = 'Active'
>>>     account.save()
```

**Problem**: Transfer between accounts fails

**Solution**:
```bash
# Verify both accounts exist and are active
python manage.py shell
>>> from accounts.models import BankAccount
>>> sender = BankAccount.objects.get(account_number='sender_account')
>>> receiver = BankAccount.objects.get(account_number='receiver_account')
>>> print(f"Sender active: {sender.is_active}")
>>> print(f"Receiver active: {receiver.is_active}")

# Check for database locks
>>> from django.db import transaction
>>> with transaction.atomic():
>>>     # Your transfer logic here
>>>     pass
```

### Balance Inconsistencies

**Problem**: Account balance doesn't match transaction history

**Solution**:
```bash
# Recalculate balance from transactions
python manage.py shell
>>> from accounts.models import BankAccount
>>> from transactions.models import Transaction
>>> from decimal import Decimal
>>> 
>>> account = BankAccount.objects.get(account_number='ACC123456789012')
>>> 
>>> # Calculate balance from transactions
>>> deposits = Transaction.objects.filter(
...     receiver_account=account,
...     transaction_type='Deposit'
... ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
>>> 
>>> withdrawals = Transaction.objects.filter(
...     sender_account=account,
...     transaction_type='Withdrawal'
... ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
>>> 
>>> transfers_in = Transaction.objects.filter(
...     receiver_account=account,
...     transaction_type='Transfer'
... ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
>>> 
>>> transfers_out = Transaction.objects.filter(
...     sender_account=account,
...     transaction_type='Transfer'
... ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
>>> 
>>> calculated_balance = deposits + transfers_in - withdrawals - transfers_out
>>> print(f"Current balance: {account.balance}")
>>> print(f"Calculated balance: {calculated_balance}")
>>> 
>>> # Update if different
>>> if account.balance != calculated_balance:
>>>     account.balance = calculated_balance
>>>     account.save()
```

## Web Server and Deployment Issues

### Static Files Not Loading

**Problem**: CSS, JavaScript, or images not loading

**Solution**:
```bash
# Collect static files
python manage.py collectstatic --noinput

# Check static files configuration
python manage.py shell
>>> from django.conf import settings
>>> print(f"STATIC_URL: {settings.STATIC_URL}")
>>> print(f"STATIC_ROOT: {settings.STATIC_ROOT}")
>>> print(f"STATICFILES_DIRS: {settings.STATICFILES_DIRS}")

# For development, ensure DEBUG=True
# For production, configure web server to serve static files
```

**Problem**: Media files (uploaded files) not accessible

**Solution**:
```bash
# Check media configuration
python manage.py shell
>>> from django.conf import settings
>>> print(f"MEDIA_URL: {settings.MEDIA_URL}")
>>> print(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")

# Ensure directory exists and has correct permissions
mkdir -p media
chmod 755 media

# For production, configure web server for media files
```

### Server Startup Issues

**Problem**: `Address already in use` error

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000
# or
netstat -tulpn | grep :8000

# Kill the process
kill -9 <process_id>

# Or use different port
python manage.py runserver 8001
```

**Problem**: Gunicorn fails to start

**Solution**:
```bash
# Check Gunicorn configuration
gunicorn --check-config banking_platform.wsgi:application

# Test Gunicorn manually
gunicorn --bind 0.0.0.0:8000 banking_platform.wsgi:application

# Check logs
tail -f logs/gunicorn_error.log

# Common fixes:
# 1. Ensure virtual environment is activated
# 2. Check DJANGO_SETTINGS_MODULE
# 3. Verify all dependencies are installed
```

### Nginx Configuration Issues

**Problem**: 502 Bad Gateway error

**Solution**:
```bash
# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Test Nginx configuration
sudo nginx -t

# Check if upstream server is running
curl http://127.0.0.1:8000

# Restart services
sudo systemctl restart nginx
sudo systemctl restart banking-platform
```

**Problem**: SSL certificate issues

**Solution**:
```bash
# Check certificate validity
openssl x509 -in /path/to/certificate.crt -text -noout

# Test SSL configuration
openssl s_client -connect yourdomain.com:443

# Renew Let's Encrypt certificate
sudo certbot renew

# Check Nginx SSL configuration
sudo nginx -t
```

## Performance Issues

### Slow Page Loading

**Problem**: Pages load slowly

**Solution**:
```bash
# Enable Django debug toolbar (development only)
pip install django-debug-toolbar

# Add to INSTALLED_APPS:
'debug_toolbar',

# Check database queries
python manage.py shell
>>> from django.db import connection
>>> # After running slow operation
>>> print(len(connection.queries))
>>> for query in connection.queries:
>>>     print(query['time'], query['sql'][:100])

# Optimize queries with select_related and prefetch_related
```

### High Memory Usage

**Problem**: Application uses too much memory

**Solution**:
```bash
# Check memory usage
free -h
ps aux | grep python

# Reduce Gunicorn workers
# Edit gunicorn.conf.py:
workers = 2  # Reduce from default

# Enable memory profiling
pip install memory-profiler
python -m memory_profiler manage.py runserver

# Check for memory leaks in code
```

### Database Performance

**Problem**: Database queries are slow

**Solution**:
```bash
# Add database indexes
python manage.py dbshell
>>> CREATE INDEX CONCURRENTLY idx_transaction_timestamp ON transaction(timestamp);
>>> CREATE INDEX CONCURRENTLY idx_account_user ON bank_account(user_id);

# Enable query optimization
# Add to settings:
DATABASES = {
    'default': {
        'OPTIONS': {
            'MAX_CONNS': 20,
        },
        'CONN_MAX_AGE': 600,
    }
}

# Use database connection pooling
pip install psycopg2-pool
```

## Security Issues

### CSRF Token Errors

**Problem**: CSRF verification failed

**Solution**:
```bash
# Check CSRF settings
python manage.py shell
>>> from django.conf import settings
>>> print(f"CSRF_COOKIE_SECURE: {settings.CSRF_COOKIE_SECURE}")
>>> print(f"CSRF_COOKIE_SAMESITE: {settings.CSRF_COOKIE_SAMESITE}")

# For development with HTTP:
CSRF_COOKIE_SECURE = False

# For production with HTTPS:
CSRF_COOKIE_SECURE = True

# Clear browser cookies and try again
```

### Session Security Issues

**Problem**: Session hijacking or security warnings

**Solution**:
```bash
# Update session security settings
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = 3600  # 1 hour

# Regenerate session key
python manage.py shell
>>> from django.core.management.utils import get_random_secret_key
>>> print(get_random_secret_key())

# Update SECRET_KEY in production
```

## Logging and Monitoring Issues

### Log Files Not Created

**Problem**: Application logs are not being written

**Solution**:
```bash
# Create logs directory
mkdir -p logs
chmod 755 logs

# Check logging configuration
python manage.py shell
>>> from django.conf import settings
>>> import pprint
>>> pprint.pprint(settings.LOGGING)

# Test logging manually
>>> import logging
>>> logger = logging.getLogger('django')
>>> logger.info('Test log message')

# Check file permissions
ls -la logs/
```

### Monitoring Setup Issues

**Problem**: Health checks fail

**Solution**:
```bash
# Test health check manually
python manage.py health_check --format=json

# Check individual components
python manage.py shell
>>> from django.db import connection
>>> cursor = connection.cursor()
>>> cursor.execute("SELECT 1")
>>> print("Database OK")

>>> from django.core.cache import cache
>>> cache.set('test', 'value', 30)
>>> print(f"Cache OK: {cache.get('test')}")
```

## Development Environment Issues

### IDE and Editor Issues

**Problem**: Code completion or syntax highlighting not working

**Solution**:
```bash
# Ensure virtual environment is activated in IDE
# For VS Code, select Python interpreter:
# Ctrl+Shift+P -> "Python: Select Interpreter"

# Install development dependencies
pip install django-stubs
pip install types-requests

# Configure IDE to recognize Django project
# Add to VS Code settings.json:
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "django": true
}
```

### Testing Issues

**Problem**: Tests fail or don't run

**Solution**:
```bash
# Run tests with verbose output
python manage.py test --verbosity=2

# Run specific test
python manage.py test accounts.tests.test_models

# Check test database settings
python manage.py shell --settings=banking_platform.settings.test
>>> from django.conf import settings
>>> print(settings.DATABASES)

# Clear test database
python manage.py flush --settings=banking_platform.settings.test
```

## Emergency Procedures

### System Recovery

**Problem**: Complete system failure

**Solution**:
```bash
# 1. Check system resources
df -h  # Disk space
free -h  # Memory
top  # CPU usage

# 2. Check service status
sudo systemctl status banking-platform
sudo systemctl status postgresql
sudo systemctl status nginx
sudo systemctl status redis

# 3. Restart services in order
sudo systemctl restart postgresql
sudo systemctl restart redis
sudo systemctl restart banking-platform
sudo systemctl restart nginx

# 4. Check logs for errors
tail -f logs/django.log
sudo journalctl -u banking-platform -f
```

### Data Recovery

**Problem**: Data corruption or loss

**Solution**:
```bash
# 1. Stop application immediately
sudo systemctl stop banking-platform

# 2. Backup current state
pg_dump banking_production > emergency_backup_$(date +%Y%m%d_%H%M%S).sql

# 3. Restore from latest backup
psql banking_production < latest_backup.sql

# 4. Verify data integrity
python manage.py shell
>>> from accounts.models import BankAccount
>>> from transactions.models import Transaction
>>> print(f"Accounts: {BankAccount.objects.count()}")
>>> print(f"Transactions: {Transaction.objects.count()}")

# 5. Restart application
sudo systemctl start banking-platform
```

## Getting Help

### Log Analysis

When reporting issues, include relevant logs:

```bash
# Application logs
tail -n 100 logs/django.log

# System logs
sudo journalctl -u banking-platform --since "1 hour ago"

# Web server logs
sudo tail -n 50 /var/log/nginx/error.log

# Database logs (PostgreSQL)
sudo tail -n 50 /var/log/postgresql/postgresql-*.log
```

### System Information

Gather system information for support:

```bash
# System info
uname -a
python --version
pip list | grep -E "(Django|psycopg2|gunicorn)"

# Django info
python manage.py version
python manage.py check --deploy

# Database info
python manage.py dbshell -c "\l"  # List databases
python manage.py dbshell -c "\dt"  # List tables
```

### Contact Information

- Check documentation: `docs/`
- Review GitHub issues
- Run health check: `python manage.py health_check`
- Check system logs: `journalctl -u banking-platform`

Remember to never share sensitive information like passwords, secret keys, or personal data when seeking help.