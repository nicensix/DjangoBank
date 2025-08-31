# 🚀 Deployment Guide

This guide covers deploying the Django Banking Platform to various environments including development, staging, and production.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Development Deployment](#development-deployment)
- [Staging Deployment](#staging-deployment)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows
- **Python**: 3.8 or higher
- **Database**: PostgreSQL 12+ (recommended) or SQLite (development only)
- **Web Server**: Nginx (recommended) or Apache
- **Process Manager**: Gunicorn (included) or uWSGI
- **Cache**: Redis (recommended for production)

### Required Software

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv postgresql postgresql-contrib nginx redis-server

# CentOS/RHEL
sudo yum install python3 python3-pip postgresql postgresql-server nginx redis

# macOS (using Homebrew)
brew install python postgresql nginx redis
```

## Environment Setup

### 1. Create Application User (Production)

```bash
# Create dedicated user for the application
sudo adduser --system --group --home /opt/banking-platform banking-platform

# Create application directory
sudo mkdir -p /opt/banking-platform
sudo chown banking-platform:banking-platform /opt/banking-platform
```

### 2. Clone Repository

```bash
# Switch to application user (production)
sudo -u banking-platform -i

# Clone repository
cd /opt/banking-platform
git clone <repository-url> .

# Or for development
git clone <repository-url>
cd django-banking-platform
```

### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## Development Deployment

### Quick Development Setup

```bash
# Use the deployment script
./deploy.sh development

# Or manual setup:
cp .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Development Configuration

Edit `.env` file:
```bash
SECRET_KEY=your-development-secret-key
DEBUG=True
DJANGO_SETTINGS_MODULE=banking_platform.settings.development
ALLOWED_HOSTS=localhost,127.0.0.1
# Leave DATABASE_URL empty for SQLite
```

### Access Development Server

- Application: http://localhost:8000
- Admin Panel: http://localhost:8000/admin
- Custom Admin: http://localhost:8000/admin-panel

## Staging Deployment

### 1. Environment Configuration

```bash
cp .env.example .env
```

Edit `.env` for staging:
```bash
SECRET_KEY=staging-secret-key-change-me
DEBUG=False
DJANGO_SETTINGS_MODULE=banking_platform.settings.staging
ALLOWED_HOSTS=staging.yourdomain.com
DATABASE_URL=postgresql://user:password@localhost:5432/banking_staging
```

### 2. Database Setup

```bash
# Create staging database
sudo -u postgres createdb banking_staging
sudo -u postgres createuser banking_user
sudo -u postgres psql -c "ALTER USER banking_user PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE banking_staging TO banking_user;"
```

### 3. Deploy Application

```bash
./deploy.sh staging
```

### 4. Configure Web Server (Nginx)

Create `/etc/nginx/sites-available/banking-staging`:
```nginx
server {
    listen 80;
    server_name staging.yourdomain.com;

    location /static/ {
        alias /opt/banking-platform/staticfiles/;
        expires 1y;
    }

    location /media/ {
        alias /opt/banking-platform/media/;
        expires 1y;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/banking-staging /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Production Deployment

### 1. Security Hardening

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Configure firewall
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable

# Secure PostgreSQL
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'very_secure_password';"
```

### 2. Database Setup

```bash
# Create production database
sudo -u postgres createdb banking_production
sudo -u postgres createuser banking_user
sudo -u postgres psql -c "ALTER USER banking_user PASSWORD 'very_secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE banking_production TO banking_user;"

# Configure PostgreSQL for production
sudo nano /etc/postgresql/*/main/postgresql.conf
# Set: shared_buffers = 256MB, effective_cache_size = 1GB

sudo systemctl restart postgresql
```

### 3. Environment Configuration

```bash
cp .env.production.example .env
```

Edit `.env` for production:
```bash
SECRET_KEY=very-long-random-secret-key-minimum-50-characters
DEBUG=False
DJANGO_SETTINGS_MODULE=banking_platform.settings.production
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://banking_user:very_secure_password@localhost:5432/banking_production
REDIS_URL=redis://127.0.0.1:6379/1
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### 4. Deploy Application

```bash
./deploy.sh production
```

### 5. Configure Gunicorn Service

Copy and edit the systemd service file:
```bash
sudo cp banking-platform.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable banking-platform
sudo systemctl start banking-platform
```

### 6. Configure Nginx with SSL

Install Certbot for SSL:
```bash
sudo apt install certbot python3-certbot-nginx
```

Create Nginx configuration `/etc/nginx/sites-available/banking-platform`:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";

    location /static/ {
        alias /opt/banking-platform/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /opt/banking-platform/media/;
        expires 1y;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

Enable site and get SSL certificate:
```bash
sudo ln -s /etc/nginx/sites-available/banking-platform /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

## Docker Deployment

### 1. Using Docker Compose (Recommended)

```bash
# Copy environment file
cp .env.production.example .env
# Edit .env with your configuration

# Build and start services
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput
```

### 2. Manual Docker Build

```bash
# Build image
docker build -t banking-platform .

# Run with environment file
docker run -d \
  --name banking-platform \
  --env-file .env \
  -p 8000:8000 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/media:/app/media \
  banking-platform
```

### 3. Docker Production Setup

For production with Docker:
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  web:
    build: .
    restart: unless-stopped
    environment:
      - DJANGO_SETTINGS_MODULE=banking_platform.settings.production
    env_file:
      - .env
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
      - ./media:/app/media
      - static_volume:/app/staticfiles

  db:
    image: postgres:15
    restart: unless-stopped
    environment:
      - POSTGRES_DB=banking_production
      - POSTGRES_USER=banking_user
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.prod.conf:/etc/nginx/nginx.conf
      - static_volume:/app/staticfiles
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web

volumes:
  postgres_data:
  redis_data:
  static_volume:
```

## Monitoring and Maintenance

### 1. Health Checks

```bash
# Check application health
python manage.py health_check

# Check with JSON output
python manage.py health_check --format=json

# System service status
sudo systemctl status banking-platform
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis
```

### 2. Log Monitoring

```bash
# Application logs
tail -f /opt/banking-platform/logs/django.log
tail -f /opt/banking-platform/logs/security.log

# System logs
sudo journalctl -u banking-platform -f
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 3. Database Maintenance

```bash
# Backup database
pg_dump -h localhost -U banking_user banking_production > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore database
psql -h localhost -U banking_user banking_production < backup_file.sql

# Vacuum and analyze (weekly)
sudo -u postgres psql banking_production -c "VACUUM ANALYZE;"
```

### 4. SSL Certificate Renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Set up automatic renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 5. Application Updates

```bash
# Pull latest code
cd /opt/banking-platform
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart services
sudo systemctl restart banking-platform
sudo systemctl reload nginx
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check database connectivity
sudo -u postgres psql -c "SELECT version();"

# Verify user permissions
sudo -u postgres psql -c "\du"
```

#### 2. Static Files Not Loading
```bash
# Collect static files
python manage.py collectstatic --noinput

# Check Nginx configuration
sudo nginx -t

# Verify file permissions
ls -la /opt/banking-platform/staticfiles/
```

#### 3. Application Won't Start
```bash
# Check logs
sudo journalctl -u banking-platform -n 50

# Test configuration
python manage.py check --deploy

# Verify environment variables
python manage.py shell -c "from django.conf import settings; print(settings.SECRET_KEY[:10])"
```

#### 4. SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Test SSL configuration
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
```

### Performance Optimization

#### 1. Database Optimization
```sql
-- Add indexes for frequently queried fields
CREATE INDEX idx_transaction_timestamp ON transactions_transaction(timestamp);
CREATE INDEX idx_account_number ON accounts_bankaccount(account_number);
```

#### 2. Nginx Optimization
```nginx
# Add to nginx.conf
worker_processes auto;
worker_connections 1024;

# Enable gzip compression
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
```

#### 3. Application Optimization
```python
# In settings/production.py
DATABASES['default']['CONN_MAX_AGE'] = 600
DATABASES['default']['OPTIONS'] = {
    'MAX_CONNS': 20,
}
```

### Backup Strategy

#### 1. Database Backups
```bash
#!/bin/bash
# backup_db.sh
BACKUP_DIR="/opt/backups/database"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="banking_backup_${DATE}.sql"

mkdir -p $BACKUP_DIR
pg_dump -h localhost -U banking_user banking_production > "${BACKUP_DIR}/${FILENAME}"
gzip "${BACKUP_DIR}/${FILENAME}"

# Keep only last 30 days
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
```

#### 2. Media Files Backup
```bash
#!/bin/bash
# backup_media.sh
rsync -av /opt/banking-platform/media/ /opt/backups/media/
```

#### 3. Automated Backups
```bash
# Add to crontab
0 2 * * * /opt/banking-platform/scripts/backup_db.sh
0 3 * * * /opt/banking-platform/scripts/backup_media.sh
```

### Security Checklist

- [ ] SSL certificate installed and configured
- [ ] Firewall configured (only necessary ports open)
- [ ] Database password changed from default
- [ ] SECRET_KEY is unique and secure
- [ ] DEBUG=False in production
- [ ] Regular security updates applied
- [ ] Backup strategy implemented
- [ ] Monitoring and alerting configured
- [ ] Log rotation configured
- [ ] File permissions properly set

For additional support, refer to the [main documentation](../README.md) or create an issue in the project repository.