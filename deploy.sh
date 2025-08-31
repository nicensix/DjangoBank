#!/bin/bash

# Django Banking Platform Deployment Script
# This script handles deployment tasks for the banking platform

set -e  # Exit on any error

echo "🏦 Django Banking Platform Deployment Script"
echo "============================================="

# Check if environment is specified
if [ -z "$1" ]; then
    echo "Usage: $0 [development|staging|production]"
    exit 1
fi

ENVIRONMENT=$1
echo "📋 Deploying to: $ENVIRONMENT"

# Set Django settings module based on environment
case $ENVIRONMENT in
    "development")
        export DJANGO_SETTINGS_MODULE=banking_platform.settings.development
        ;;
    "staging")
        export DJANGO_SETTINGS_MODULE=banking_platform.settings.staging
        ;;
    "production")
        export DJANGO_SETTINGS_MODULE=banking_platform.settings.production
        ;;
    *)
        echo "❌ Invalid environment. Use: development, staging, or production"
        exit 1
        ;;
esac

echo "🔧 Setting up environment..."

# Create logs directory if it doesn't exist
mkdir -p logs

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Run database migrations
echo "🗄️  Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Collect static files (for staging/production)
if [ "$ENVIRONMENT" != "development" ]; then
    echo "📁 Collecting static files..."
    python manage.py collectstatic --noinput
fi

# Create superuser (only for development)
if [ "$ENVIRONMENT" = "development" ]; then
    echo "👤 Creating superuser (if needed)..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
"
fi

# Run tests
echo "🧪 Running tests..."
python manage.py test --verbosity=2

# Check deployment
echo "✅ Running deployment checks..."
python manage.py check --deploy

echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Next steps:"
case $ENVIRONMENT in
    "development")
        echo "   • Run: python manage.py runserver"
        echo "   • Access: http://localhost:8000"
        echo "   • Admin: http://localhost:8000/admin (admin/admin123)"
        ;;
    "staging"|"production")
        echo "   • Start with: gunicorn -c gunicorn.conf.py banking_platform.wsgi:application"
        echo "   • Or use Docker: docker-compose up -d"
        echo "   • Monitor logs in: ./logs/"
        ;;
esac