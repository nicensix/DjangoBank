# 🔌 API Documentation

## Overview

The Django Banking Platform provides a comprehensive set of endpoints for managing banking operations. All endpoints require proper authentication and follow RESTful conventions.

## Authentication

### Session-Based Authentication

The platform uses Django's built-in session authentication. Users must login to receive a session cookie that authenticates subsequent requests.

```http
POST /accounts/login/
Content-Type: application/x-www-form-urlencoded

username=your_username&password=your_password
```

**Response:**
```json
{
    "success": true,
    "redirect_url": "/dashboard/",
    "message": "Login successful"
}
```

## Account Management Endpoints

### User Registration

Create a new user account with automatic bank account generation.

```http
POST /accounts/register/
Content-Type: application/x-www-form-urlencoded

username=newuser&email=user@example.com&password1=securepass123&password2=securepass123&first_name=John&last_name=Doe
```

**Response:**
```json
{
    "success": true,
    "message": "Account created successfully",
    "account_number": "ACC123456789",
    "redirect_url": "/dashboard/"
}
```

**Error Response:**
```json
{
    "success": false,
    "errors": {
        "username": ["This username is already taken."],
        "password2": ["Passwords don't match."]
    }
}
```

### User Profile

Get current user profile information.

```http
GET /accounts/profile/
```

**Response:**
```json
{
    "user": {
        "id": 1,
        "username": "johndoe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "date_joined": "2024-01-15T10:30:00Z"
    },
    "bank_account": {
        "account_number": "ACC123456789",
        "account_type": "Savings",
        "balance": "1500.00",
        "status": "Active",
        "created_at": "2024-01-15T10:30:00Z"
    }
}
```

### User Logout

Logout current user and clear session.

```http
POST /accounts/logout/
```

**Response:**
```json
{
    "success": true,
    "message": "Logged out successfully",
    "redirect_url": "/"
}
```

## Banking Operations Endpoints

### Dashboard

Get user dashboard with account summary and recent transactions.

```http
GET /dashboard/
```

**Response:**
```json
{
    "account": {
        "account_number": "ACC123456789",
        "balance": "1500.00",
        "account_type": "Savings",
        "status": "Active"
    },
    "recent_transactions": [
        {
            "id": 1,
            "type": "Deposit",
            "amount": "500.00",
            "timestamp": "2024-01-15T14:30:00Z",
            "description": "Cash deposit"
        }
    ],
    "transaction_count": 5
}
```

### Deposit Money

Process a deposit transaction.

```http
POST /transactions/deposit/
Content-Type: application/x-www-form-urlencoded

amount=500.00&description=Cash deposit
```

**Response:**
```json
{
    "success": true,
    "message": "Deposit successful",
    "transaction": {
        "id": 123,
        "type": "Deposit",
        "amount": "500.00",
        "timestamp": "2024-01-15T14:30:00Z",
        "new_balance": "2000.00"
    }
}
```

**Error Response:**
```json
{
    "success": false,
    "errors": {
        "amount": ["Amount must be positive."]
    }
}
```

### Withdraw Money

Process a withdrawal transaction.

```http
POST /transactions/withdraw/
Content-Type: application/x-www-form-urlencoded

amount=200.00&description=ATM withdrawal
```

**Response:**
```json
{
    "success": true,
    "message": "Withdrawal successful",
    "transaction": {
        "id": 124,
        "type": "Withdrawal",
        "amount": "200.00",
        "timestamp": "2024-01-15T15:00:00Z",
        "new_balance": "1800.00"
    }
}
```

**Error Response:**
```json
{
    "success": false,
    "errors": {
        "amount": ["Insufficient funds. Available balance: $1500.00"]
    }
}
```

### Transfer Money

Transfer money to another account.

```http
POST /transactions/transfer/
Content-Type: application/x-www-form-urlencoded

recipient_account=ACC987654321&amount=300.00&description=Payment to friend
```

**Response:**
```json
{
    "success": true,
    "message": "Transfer successful",
    "transaction": {
        "id": 125,
        "type": "Transfer",
        "amount": "300.00",
        "timestamp": "2024-01-15T15:30:00Z",
        "sender_account": "ACC123456789",
        "recipient_account": "ACC987654321",
        "new_balance": "1500.00"
    }
}
```

**Error Response:**
```json
{
    "success": false,
    "errors": {
        "recipient_account": ["Account not found."],
        "amount": ["Insufficient funds."]
    }
}
```

### Transaction History

Get paginated transaction history.

```http
GET /transactions/history/?page=1&per_page=10&type=all&start_date=2024-01-01&end_date=2024-01-31
```

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 10, max: 100)
- `type` (optional): Transaction type filter (all, deposit, withdrawal, transfer)
- `start_date` (optional): Start date filter (YYYY-MM-DD)
- `end_date` (optional): End date filter (YYYY-MM-DD)

**Response:**
```json
{
    "transactions": [
        {
            "id": 125,
            "type": "Transfer",
            "amount": "300.00",
            "timestamp": "2024-01-15T15:30:00Z",
            "description": "Payment to friend",
            "sender_account": "ACC123456789",
            "recipient_account": "ACC987654321",
            "balance_after": "1500.00"
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 10,
        "total_pages": 3,
        "total_count": 25,
        "has_next": true,
        "has_previous": false
    }
}
```

### Download Statement

Generate and download account statement.

```http
GET /statements/download/?format=pdf&start_date=2024-01-01&end_date=2024-01-31
```

**Query Parameters:**
- `format`: File format (pdf, csv)
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)

**Response:**
Returns file download with appropriate Content-Type and Content-Disposition headers.

## Administrative Endpoints

### Admin Dashboard

Get administrative dashboard data (requires staff permissions).

```http
GET /admin-panel/
```

**Response:**
```json
{
    "stats": {
        "total_users": 150,
        "total_accounts": 175,
        "active_accounts": 160,
        "frozen_accounts": 15,
        "total_transactions": 1250,
        "total_balance": "125000.00"
    },
    "recent_transactions": [...],
    "pending_approvals": [...]
}
```

### User Management

Get list of all users and their accounts (requires staff permissions).

```http
GET /admin-panel/users/?page=1&search=john&status=active
```

**Query Parameters:**
- `page` (optional): Page number
- `search` (optional): Search by username, email, or name
- `status` (optional): Filter by account status (active, frozen, closed)

**Response:**
```json
{
    "users": [
        {
            "id": 1,
            "username": "johndoe",
            "email": "john@example.com",
            "full_name": "John Doe",
            "date_joined": "2024-01-15T10:30:00Z",
            "is_active": true,
            "bank_account": {
                "account_number": "ACC123456789",
                "balance": "1500.00",
                "status": "Active",
                "account_type": "Savings"
            }
        }
    ],
    "pagination": {...}
}
```

### Transaction Management

Get all system transactions (requires staff permissions).

```http
GET /admin-panel/transactions/?page=1&type=all&flagged=false&start_date=2024-01-01
```

**Response:**
```json
{
    "transactions": [
        {
            "id": 125,
            "type": "Transfer",
            "amount": "300.00",
            "timestamp": "2024-01-15T15:30:00Z",
            "sender": {
                "account_number": "ACC123456789",
                "username": "johndoe"
            },
            "recipient": {
                "account_number": "ACC987654321",
                "username": "janedoe"
            },
            "is_flagged": false,
            "admin_notes": null
        }
    ],
    "pagination": {...}
}
```

### Account Actions

Perform administrative actions on accounts (requires staff permissions).

```http
POST /admin-panel/account-action/
Content-Type: application/x-www-form-urlencoded

account_id=123&action=freeze&reason=Suspicious activity detected
```

**Available Actions:**
- `approve`: Approve pending account
- `freeze`: Freeze account (prevents transactions)
- `unfreeze`: Unfreeze account
- `close`: Close account permanently

**Response:**
```json
{
    "success": true,
    "message": "Account frozen successfully",
    "action": {
        "type": "freeze",
        "timestamp": "2024-01-15T16:00:00Z",
        "admin": "admin_user",
        "reason": "Suspicious activity detected"
    }
}
```

## Error Handling

### Standard Error Response Format

```json
{
    "success": false,
    "error_code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "errors": {
        "field_name": ["Error message 1", "Error message 2"]
    }
}
```

### Common Error Codes

- `AUTHENTICATION_REQUIRED`: User not authenticated
- `PERMISSION_DENIED`: Insufficient permissions
- `VALIDATION_ERROR`: Form validation failed
- `ACCOUNT_NOT_FOUND`: Bank account not found
- `INSUFFICIENT_FUNDS`: Not enough balance for transaction
- `ACCOUNT_FROZEN`: Account is frozen
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `SERVER_ERROR`: Internal server error

### HTTP Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Permission denied
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

- Authentication endpoints: 5 requests per minute per IP
- Transaction endpoints: 10 requests per minute per user
- General endpoints: 60 requests per minute per user

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1642694400
```

## Security Considerations

### CSRF Protection

All POST requests must include a valid CSRF token. For AJAX requests:

```javascript
// Get CSRF token from cookie or meta tag
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

// Include in request headers
fetch('/api/endpoint/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
});
```

### HTTPS Required

All API endpoints require HTTPS in production. HTTP requests will be redirected to HTTPS.

### Input Validation

All input is validated server-side. Client-side validation is for user experience only and should not be relied upon for security.

## Testing the API

### Using curl

```bash
# Login
curl -c cookies.txt -X POST http://localhost:8000/accounts/login/ \
  -d "username=testuser&password=testpass123"

# Make authenticated request
curl -b cookies.txt http://localhost:8000/dashboard/

# Deposit money
curl -b cookies.txt -X POST http://localhost:8000/transactions/deposit/ \
  -d "amount=100.00&description=Test deposit"
```

### Using Python requests

```python
import requests

# Create session for cookie handling
session = requests.Session()

# Login
login_data = {
    'username': 'testuser',
    'password': 'testpass123'
}
response = session.post('http://localhost:8000/accounts/login/', data=login_data)

# Make authenticated requests
dashboard = session.get('http://localhost:8000/dashboard/')
print(dashboard.json())

# Deposit money
deposit_data = {
    'amount': '100.00',
    'description': 'Test deposit'
}
deposit = session.post('http://localhost:8000/transactions/deposit/', data=deposit_data)
print(deposit.json())
```