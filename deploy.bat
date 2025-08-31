@echo off
REM Django Banking Platform Deployment Script for Windows
REM This script handles deployment tasks for the banking platform

echo 🏦 Django Banking Platform Deployment Script
echo =============================================

if "%1"=="" (
    echo Usage: %0 [development^|staging^|production]
    exit /b 1
)

set ENVIRONMENT=%1
echo 📋 Deploying to: %ENVIRONMENT%

REM Set Django settings module based on environment
if "%ENVIRONMENT%"=="development" (
    set DJANGO_SETTINGS_MODULE=banking_platform.settings.development
) else if "%ENVIRONMENT%"=="staging" (
    set DJANGO_SETTINGS_MODULE=banking_platform.settings.staging
) else if "%ENVIRONMENT%"=="production" (
    set DJANGO_SETTINGS_MODULE=banking_platform.settings.production
) else (
    echo ❌ Invalid environment. Use: development, staging, or production
    exit /b 1
)

echo 🔧 Setting up environment...

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Install/update dependencies
echo 📦 Installing dependencies...
pip install -r requirements.txt

REM Run database migrations
echo 🗄️  Running database migrations...
python manage.py makemigrations
python manage.py migrate

REM Collect static files (for staging/production)
if not "%ENVIRONMENT%"=="development" (
    echo 📁 Collecting static files...
    python manage.py collectstatic --noinput
)

REM Create superuser (only for development)
if "%ENVIRONMENT%"=="development" (
    echo 👤 Creating superuser if needed...
    python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else print('Superuser already exists')"
)

REM Run tests
echo 🧪 Running tests...
python manage.py test --verbosity=2

REM Check deployment
echo ✅ Running deployment checks...
python manage.py check --deploy

echo 🎉 Deployment completed successfully!
echo.
echo 📋 Next steps:
if "%ENVIRONMENT%"=="development" (
    echo    • Run: python manage.py runserver
    echo    • Access: http://localhost:8000
    echo    • Admin: http://localhost:8000/admin ^(admin/admin123^)
) else (
    echo    • Start with: gunicorn -c gunicorn.conf.py banking_platform.wsgi:application
    echo    • Or use Docker: docker-compose up -d
    echo    • Monitor logs in: ./logs/
)