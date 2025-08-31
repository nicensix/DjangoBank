# 🔧 Administrative Procedures Manual

This manual provides comprehensive procedures for administrators managing the Django Banking Platform. It covers user management, system oversight, security protocols, and maintenance procedures.

## Table of Contents

- [Administrator Access](#administrator-access)
- [User Account Management](#user-account-management)
- [Transaction Management](#transaction-management)
- [Security Procedures](#security-procedures)
- [System Monitoring](#system-monitoring)
- [Backup and Recovery](#backup-and-recovery)
- [Maintenance Procedures](#maintenance-procedures)
- [Emergency Procedures](#emergency-procedures)
- [Reporting and Analytics](#reporting-and-analytics)

## Administrator Access

### Initial Setup

#### Creating Administrator Accounts
```bash
# Create superuser account
python manage.py createsuperuser

# Or create staff user via Django admin
# Navigate to /admin/ and create user with staff permissions
```

#### Administrator Permissions
- **Superuser**: Full system access, can create other admins
- **Staff User**: Access to admin panel and user management
- **Custom Permissions**: Can be assigned specific administrative roles

### Accessing Administrative Features

1. **Django Admin Panel**
   - URL: `/admin/`
   - Full database access and Django administration
   - User and group management
   - System configuration

2. **Custom Admin Panel**
   - URL: `/admin-panel/`
   - Banking-specific administrative interface
   - User-friendly dashboard for banking operations
   - Transaction monitoring and account management

## User Account Management

### New User Registration Process

#### Automatic Registration
1. **User Self-Registration**
   - Users register through `/accounts/register/`
   - Bank account is automatically created
   - Account status set to "Active" (or "Pending" if approval required)

2. **Manual User Creation**
   ```python
   # Via Django shell
   python manage.py shell
   
   from django.contrib.auth import get_user_model
   from accounts.models import BankAccount
   
   User = get_user_model()
   user = User.objects.create_user(
       username='newuser',
       email='user@example.com',
       password='secure_password',
       first_name='John',
       last_name='Doe'
   )
   
   # Create bank account
   account = BankAccount.objects.create(
       user=user,
       account_type='Savings',
       balance=0.00
   )
   ```

### Account Approval Process

#### Reviewing Pending Accounts
1. **Access User Management**
   - Navigate to Admin Panel → User Management
   - Filter by "Pending" status
   - Review user information and documentation

2. **Approval Criteria**
   - Valid personal information provided
   - Email address verified (if email verification enabled)
   - No duplicate accounts for same person
   - Compliance with account opening requirements

3. **Approving Accounts**
   ```python
   # Via admin interface or programmatically
   from accounts.models import BankAccount
   
   account = BankAccount.objects.get(account_number='ACC123456789')
   account.status = 'Active'
   account.save()
   
   # Log admin action
   from admin_panel.models import AdminAction
   AdminAction.objects.create(
       admin=request.user,
       action_type='Approve',
       bank_account=account,
       notes='Account approved after document verification'
   )
   ```

### Account Status Management

#### Freezing Accounts
**When to Freeze:**
- Suspicious transaction patterns detected
- User reports unauthorized access
- Compliance investigation required
- Court order or legal requirement

**Freezing Process:**
1. Navigate to Admin Panel → User Management
2. Find the user account
3. Click "Freeze Account"
4. Provide detailed reason for freezing
5. Set review date if applicable
6. Notify user of account freeze (if appropriate)

**Effects of Freezing:**
- All transactions blocked (deposits, withdrawals, transfers)
- User can still view account information
- Account appears as "Frozen" in admin panel

#### Unfreezing Accounts
**Unfreezing Process:**
1. Review freeze reason and any investigation results
2. Verify issue has been resolved
3. Navigate to frozen account in admin panel
4. Click "Unfreeze Account"
5. Document reason for unfreezing
6. Notify user of account reactivation

#### Closing Accounts
**When to Close:**
- User requests account closure
- Prolonged inactivity (per policy)
- Compliance violations
- Business decision

**Closure Process:**
1. Verify account balance is zero
2. Process final transactions if needed
3. Generate final statement
4. Update account status to "Closed"
5. Archive account data per retention policy
6. Notify user of closure confirmation

### User Information Management

#### Updating User Information
```python
# Via Django admin or custom interface
user = User.objects.get(username='username')
user.email = 'newemail@example.com'
user.first_name = 'Updated Name'
user.save()

# Log the change
AdminAction.objects.create(
    admin=request.user,
    action_type='Update Profile',
    bank_account=user.bankaccount,
    notes='Updated email address per user request'
)
```

#### Password Reset for Users
```python
# Generate password reset for user
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

user = User.objects.get(username='username')
token = default_token_generator.make_token(user)
uid = urlsafe_base64_encode(force_bytes(user.pk))

# Send reset link to user or provide directly
reset_url = f"/accounts/reset/{uid}/{token}/"
```

## Transaction Management

### Transaction Monitoring

#### Daily Transaction Review
1. **Access Transaction Dashboard**
   - Navigate to Admin Panel → Transactions
   - Review daily transaction summary
   - Check for unusual patterns or amounts

2. **Transaction Filters**
   - Filter by date range
   - Filter by transaction type
   - Filter by amount ranges
   - Search by account numbers

3. **Red Flags to Monitor**
   - Large transactions (above threshold)
   - Multiple rapid transactions
   - Round number transactions
   - Transactions to/from flagged accounts

#### Flagging Suspicious Transactions
```python
# Mark transaction as flagged
from transactions.models import Transaction

transaction = Transaction.objects.get(id=transaction_id)
transaction.is_flagged = True
transaction.admin_notes = 'Large amount transfer - requires review'
transaction.save()

# Create admin action record
AdminAction.objects.create(
    admin=request.user,
    action_type='Flag Transaction',
    bank_account=transaction.sender_account,
    notes=f'Flagged transaction {transaction.id} for review'
)
```

### Transaction Dispute Resolution

#### Handling Transaction Disputes
1. **Receive Dispute Report**
   - User reports unauthorized transaction
   - Document all details provided
   - Gather transaction evidence

2. **Investigation Process**
   - Review transaction logs
   - Check IP addresses and session data
   - Verify user authentication at time of transaction
   - Check for system errors or anomalies

3. **Resolution Actions**
   ```python
   # Reverse transaction if fraud confirmed
   from transactions.services import TransactionService
   
   # Create reversal transaction
   reversal = TransactionService.create_reversal(
       original_transaction=disputed_transaction,
       admin_user=request.user,
       reason='Fraud confirmed - unauthorized access'
   )
   ```

### Transaction Limits and Controls

#### Setting Transaction Limits
```python
# In settings or via admin interface
TRANSACTION_LIMITS = {
    'daily_deposit_limit': 10000.00,
    'daily_withdrawal_limit': 5000.00,
    'daily_transfer_limit': 5000.00,
    'single_transaction_limit': 2000.00
}

# Implement in transaction processing
def validate_transaction_limits(user, amount, transaction_type):
    # Check daily limits
    today_total = get_daily_transaction_total(user, transaction_type)
    if today_total + amount > TRANSACTION_LIMITS[f'daily_{transaction_type}_limit']:
        raise ValidationError('Daily limit exceeded')
```

## Security Procedures

### Security Monitoring

#### Daily Security Checks
1. **Failed Login Attempts**
   - Monitor authentication logs
   - Check for brute force attempts
   - Block suspicious IP addresses if needed

2. **Session Monitoring**
   - Review active sessions
   - Check for unusual session patterns
   - Force logout suspicious sessions

3. **System Access Logs**
   - Review admin panel access
   - Monitor database queries
   - Check for unauthorized access attempts

#### Security Incident Response

**Level 1 - Minor Incidents**
- Single failed login attempts
- Minor system errors
- User lockouts

**Response:**
- Log incident
- Monitor for patterns
- Assist user if needed

**Level 2 - Moderate Incidents**
- Multiple failed login attempts
- Suspicious transaction patterns
- System performance issues

**Response:**
- Investigate immediately
- Freeze affected accounts if needed
- Document findings
- Implement preventive measures

**Level 3 - Major Incidents**
- Confirmed security breach
- System compromise
- Data theft attempts

**Response:**
- Activate incident response team
- Freeze all affected accounts
- Preserve evidence
- Notify stakeholders
- Implement recovery procedures

### Access Control Management

#### Managing Administrator Permissions
```python
# Grant admin permissions
from django.contrib.auth.models import Group, Permission

# Create admin group
admin_group, created = Group.objects.get_or_create(name='Banking Admins')

# Add permissions
permissions = [
    'accounts.view_bankaccount',
    'accounts.change_bankaccount',
    'transactions.view_transaction',
    'transactions.change_transaction',
    'admin_panel.add_adminaction',
]

for perm_codename in permissions:
    permission = Permission.objects.get(codename=perm_codename.split('.')[1])
    admin_group.permissions.add(permission)

# Add user to group
user.groups.add(admin_group)
```

#### Regular Access Reviews
1. **Monthly Access Review**
   - Review all administrator accounts
   - Verify permissions are appropriate
   - Remove access for inactive admins
   - Document access changes

2. **Quarterly Security Audit**
   - Review all user permissions
   - Check for privilege escalation
   - Verify separation of duties
   - Update security policies

## System Monitoring

### Performance Monitoring

#### Daily System Health Checks
```bash
# Run health check command
python manage.py health_check

# Check system resources
df -h  # Disk usage
free -m  # Memory usage
top  # CPU usage

# Check database performance
python manage.py dbshell
# Run performance queries
```

#### Database Monitoring
```sql
-- Check database size
SELECT pg_size_pretty(pg_database_size('banking_production'));

-- Check table sizes
SELECT schemaname,tablename,attname,n_distinct,correlation 
FROM pg_stats 
WHERE schemaname = 'public' 
ORDER BY n_distinct DESC;

-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

### Log Management

#### Log Rotation Setup
```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/banking-platform

/opt/banking-platform/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 banking-platform banking-platform
    postrotate
        systemctl reload banking-platform
    endscript
}
```

#### Log Analysis
```bash
# Check error logs
grep "ERROR" /opt/banking-platform/logs/django.log | tail -20

# Check security logs
grep "SECURITY" /opt/banking-platform/logs/security.log | tail -20

# Monitor transaction patterns
grep "Transaction" /opt/banking-platform/logs/django.log | grep "$(date +%Y-%m-%d)"
```

## Backup and Recovery

### Backup Procedures

#### Daily Database Backup
```bash
#!/bin/bash
# daily_backup.sh

BACKUP_DIR="/opt/backups/database"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="banking_production"
DB_USER="banking_user"

# Create backup directory
mkdir -p $BACKUP_DIR

# Perform backup
pg_dump -h localhost -U $DB_USER $DB_NAME > "${BACKUP_DIR}/backup_${DATE}.sql"

# Compress backup
gzip "${BACKUP_DIR}/backup_${DATE}.sql"

# Remove backups older than 30 days
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

# Log backup completion
echo "$(date): Database backup completed - backup_${DATE}.sql.gz" >> /var/log/banking-backup.log
```

#### Media Files Backup
```bash
#!/bin/bash
# backup_media.sh

MEDIA_DIR="/opt/banking-platform/media"
BACKUP_DIR="/opt/backups/media"
DATE=$(date +%Y%m%d)

# Sync media files
rsync -av --delete $MEDIA_DIR/ "${BACKUP_DIR}/${DATE}/"

# Keep only last 7 days of media backups
find $BACKUP_DIR -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \;
```

### Recovery Procedures

#### Database Recovery
```bash
# Stop application
sudo systemctl stop banking-platform

# Restore database
gunzip -c backup_20240115_020000.sql.gz | psql -h localhost -U banking_user banking_production

# Run migrations if needed
cd /opt/banking-platform
source venv/bin/activate
python manage.py migrate

# Start application
sudo systemctl start banking-platform
```

#### Full System Recovery
1. **Prepare Clean Environment**
   - Install required software
   - Create application user
   - Set up database server

2. **Restore Application Code**
   ```bash
   git clone <repository-url> /opt/banking-platform
   cd /opt/banking-platform
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Restore Database**
   ```bash
   createdb banking_production
   gunzip -c latest_backup.sql.gz | psql banking_production
   ```

4. **Restore Media Files**
   ```bash
   rsync -av backup_media/ /opt/banking-platform/media/
   ```

5. **Configure and Start Services**
   ```bash
   cp .env.production.example .env
   # Edit .env with correct settings
   python manage.py collectstatic --noinput
   sudo systemctl start banking-platform
   ```

## Maintenance Procedures

### Regular Maintenance Tasks

#### Weekly Tasks
1. **Database Maintenance**
   ```sql
   -- Vacuum and analyze database
   VACUUM ANALYZE;
   
   -- Update table statistics
   ANALYZE;
   
   -- Check for unused indexes
   SELECT schemaname, tablename, attname, n_distinct, correlation 
   FROM pg_stats 
   WHERE schemaname = 'public';
   ```

2. **Log Review**
   - Review error logs for patterns
   - Check security logs for incidents
   - Monitor transaction volumes
   - Verify backup completion

3. **Performance Review**
   - Check response times
   - Monitor database query performance
   - Review system resource usage
   - Optimize slow queries

#### Monthly Tasks
1. **Security Review**
   - Review user access permissions
   - Check for inactive accounts
   - Update security policies
   - Review incident reports

2. **System Updates**
   ```bash
   # Update system packages
   sudo apt update && sudo apt upgrade
   
   # Update Python packages
   pip list --outdated
   pip install -U package_name
   
   # Update Django and dependencies
   pip install -r requirements.txt --upgrade
   ```

3. **Capacity Planning**
   - Review storage usage
   - Monitor transaction growth
   - Plan for scaling needs
   - Update resource allocations

### System Updates

#### Application Updates
```bash
# Backup before update
./scripts/backup_db.sh

# Pull latest code
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Run tests
python manage.py test

# Restart services
sudo systemctl restart banking-platform
sudo systemctl reload nginx
```

#### Security Updates
```bash
# Update system security patches
sudo apt update
sudo apt list --upgradable
sudo apt upgrade

# Update SSL certificates
sudo certbot renew

# Review security configurations
python manage.py check --deploy
```

## Emergency Procedures

### System Outage Response

#### Immediate Response (0-15 minutes)
1. **Assess Situation**
   - Check system status
   - Identify affected services
   - Determine scope of outage

2. **Initial Actions**
   - Notify stakeholders
   - Activate incident response team
   - Begin troubleshooting

3. **Communication**
   - Update status page
   - Notify users of outage
   - Provide estimated resolution time

#### Investigation Phase (15-60 minutes)
1. **Gather Information**
   - Check system logs
   - Review monitoring alerts
   - Identify root cause

2. **Implement Workarounds**
   - Restore critical services
   - Implement temporary fixes
   - Monitor system stability

#### Resolution Phase (1+ hours)
1. **Implement Permanent Fix**
   - Apply necessary patches
   - Update configurations
   - Test thoroughly

2. **Post-Incident Review**
   - Document incident details
   - Identify improvement opportunities
   - Update procedures

### Security Incident Response

#### Immediate Response
1. **Contain Incident**
   - Isolate affected systems
   - Freeze compromised accounts
   - Preserve evidence

2. **Assess Impact**
   - Identify affected data
   - Determine breach scope
   - Evaluate risks

3. **Notify Stakeholders**
   - Internal incident team
   - Management
   - Legal/compliance (if required)
   - Users (if data compromised)

#### Investigation and Recovery
1. **Forensic Analysis**
   - Preserve system state
   - Analyze attack vectors
   - Document findings

2. **System Recovery**
   - Remove malicious code
   - Patch vulnerabilities
   - Restore from clean backups

3. **Strengthen Security**
   - Update security measures
   - Implement additional controls
   - Monitor for reoccurrence

## Reporting and Analytics

### Regular Reports

#### Daily Operations Report
- Transaction volume and values
- New user registrations
- Account status changes
- System performance metrics
- Security incidents

#### Weekly Summary Report
- Transaction trends
- User activity patterns
- System health metrics
- Security review summary
- Operational issues

#### Monthly Management Report
- Business metrics
- Growth statistics
- Security posture
- System performance
- Compliance status

### Analytics and Insights

#### Transaction Analytics
```python
# Generate transaction reports
from django.db.models import Sum, Count, Avg
from transactions.models import Transaction

# Daily transaction summary
daily_stats = Transaction.objects.filter(
    timestamp__date=today
).aggregate(
    total_count=Count('id'),
    total_amount=Sum('amount'),
    avg_amount=Avg('amount')
)

# Transaction type breakdown
type_breakdown = Transaction.objects.values('transaction_type').annotate(
    count=Count('id'),
    total=Sum('amount')
)
```

#### User Analytics
```python
# User growth metrics
from accounts.models import BankAccount

# New accounts by month
monthly_growth = BankAccount.objects.extra(
    select={'month': 'EXTRACT(month FROM created_at)'}
).values('month').annotate(count=Count('id'))

# Account status distribution
status_dist = BankAccount.objects.values('status').annotate(
    count=Count('id')
)
```

### Compliance Reporting

#### Audit Trail Reports
- All administrative actions
- Account status changes
- Transaction modifications
- System access logs

#### Regulatory Reports
- Transaction monitoring reports
- Suspicious activity reports
- Account closure reports
- Data retention compliance

---

This administrative procedures manual should be reviewed and updated regularly to reflect system changes and operational improvements. All administrators should be trained on these procedures and have access to this documentation.