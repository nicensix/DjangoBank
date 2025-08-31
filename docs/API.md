# API Documentation

## Overview

The Django Banking Platform provides a web-based interface for banking operations. While primarily designed as a web application, this document outlines the internal API structure and endpoints for future API development.

## Authentication

All banking operations require user authentication. The platform uses Django's session-based authentication.

### Login
- **URL**: `/accounts/login/`
- **Method**: POST
- **Parameters**:
  - `username`: User's username
  - `password`: User's password
- **Response**: Redirects to dashboard on success

### Logout
- **URL**: `/accounts/logout/`
- **Method**: POST
- **Response**: Redirects to homepage

### Registration
- **URL**: `/accounts/register/`
- **Method**: POST
- **Parameters**:
  - `username`: Unique username
  - `email`: User's email address
  - `password1`: Password
  - `password2`: Password confirmation
  - `first_name`: User's first name
  - `last_name`: User's last name
- **Response**: Creates user and bank account, redirects to dashboard

## Account Operations

### Dashboard
- **URL**: `/dashboard/`
- **Method**: GET
- **Authentication**: Required
- **Response**: User's account information and recent transactions

### Account Details
- **URL**: `/accounts/details/`
- **Method**: GET
- **Authentication**: Required
- **Response**: Detailed account information including balance and account number

## Transaction Operations

### Deposit
- **URL**: `/transactions/deposit/`
- **Method**: POST
- **Authentication**: Required
- **Parameters**:
  - `amount`: Deposit amount (positive decimal)
- **Response**: Updates account balance and creates transaction record

### Withdrawal
- **URL**: `/transactions/withdraw/`
- **Method**: POST
- **Authentication**: Required
- **Parameters**:
  - `amount`: Withdrawal amount (positive decimal)
- **Validation**: Checks sufficient balance
- **Response**: Updates account balance and creates transaction record

### Transfer
- **URL**: `/transactions/transfer/`
- **Method**: POST
- **Authentication**: Required
- **Parameters**:
  - `recipient_account`: Target account number
  - `amount`: Transfer amount (positive decimal)
- **Validation**: 
  - Checks sufficient balance
  - Validates recipient account exists
- **Response**: Updates both accounts atomically and creates transaction records

### Transaction History
- **URL**: `/transactions/history/`
- **Method**: GET
- **Authentication**: Required
- **Parameters** (optional):
  - `start_date`: Filter transactions from date
  - `end_date`: Filter transactions to date
  - `transaction_type`: Filter by type (deposit, withdrawal, transfer)
- **Response**: List of user's transactions with pagination

### Download Statement
- **URL**: `/transactions/statement/`
- **Method**: GET
- **Authentication**: Required
- **Parameters**:
  - `format`: File format (pdf, csv)
  - `start_date`: Statement start date
  - `end_date`: Statement end date
- **Response**: Downloadable file with transaction history

## Administrative Operations

### Admin Dashboard
- **URL**: `/admin-panel/`
- **Method**: GET
- **Authentication**: Required (staff only)
- **Response**: Administrative overview with system statistics

### User Management
- **URL**: `/admin-panel/users/`
- **Method**: GET
- **Authentication**: Required (staff only)
- **Response**: List of all users and their accounts

### Account Management
- **URL**: `/admin-panel/accounts/`
- **Method**: GET
- **Authentication**: Required (staff only)
- **Response**: List of all bank accounts with status information

### Approve Account
- **URL**: `/admin-panel/accounts/<account_id>/approve/`
- **Method**: POST
- **Authentication**: Required (staff only)
- **Response**: Updates account status to approved

### Freeze Account
- **URL**: `/admin-panel/accounts/<account_id>/freeze/`
- **Method**: POST
- **Authentication**: Required (staff only)
- **Response**: Freezes account, preventing transactions

### Unfreeze Account
- **URL**: `/admin-panel/accounts/<account_id>/unfreeze/`
- **Method**: POST
- **Authentication**: Required (staff only)
- **Response**: Unfreezes account, restoring transaction capabilities

### Transaction Management
- **URL**: `/admin-panel/transactions/`
- **Method**: GET
- **Authentication**: Required (staff only)
- **Parameters** (optional):
  - `account`: Filter by account number
  - `transaction_type`: Filter by transaction type
  - `start_date`: Filter from date
  - `end_date`: Filter to date
- **Response**: List of all system transactions

## Data Models

### User
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "date_joined": "2024-01-01T00:00:00Z",
  "is_active": true
}
```

### Bank Account
```json
{
  "id": 1,
  "account_number": "ACC001234567890",
  "account_type": "Savings",
  "balance": "1500.00",
  "status": "Active",
  "created_at": "2024-01-01T00:00:00Z",
  "user": 1
}
```

### Transaction
```json
{
  "id": 1,
  "transaction_type": "Transfer",
  "amount": "100.00",
  "timestamp": "2024-01-01T12:00:00Z",
  "sender_account": 1,
  "receiver_account": 2,
  "description": "Money transfer"
}
```

### Admin Action
```json
{
  "id": 1,
  "action_type": "Approve Account",
  "timestamp": "2024-01-01T10:00:00Z",
  "admin": 1,
  "bank_account": 1,
  "notes": "Account approved after verification"
}
```

## Error Responses

### Common Error Codes

- **400 Bad Request**: Invalid input data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

### Error Response Format
```json
{
  "error": true,
  "message": "Insufficient funds for withdrawal",
  "code": "INSUFFICIENT_FUNDS",
  "details": {
    "current_balance": "50.00",
    "requested_amount": "100.00"
  }
}
```

## Rate Limiting

The platform implements rate limiting for security:

- **Login attempts**: 5 attempts per 15 minutes per IP
- **Transaction operations**: 10 transactions per minute per user
- **API calls**: 100 requests per minute per authenticated user

## Security Headers

All responses include security headers:

- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

## Future API Development

For REST API development, consider:

1. **Django REST Framework**: For building RESTful APIs
2. **API Versioning**: Implement versioning strategy
3. **Token Authentication**: JWT or API key authentication
4. **API Documentation**: OpenAPI/Swagger documentation
5. **Rate Limiting**: Enhanced rate limiting for API endpoints
6. **Pagination**: Consistent pagination across endpoints
7. **Filtering**: Advanced filtering and search capabilities

## Testing API Endpoints

Use Django's test client for testing:

```python
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

class APITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_login(self):
        response = self.client.post('/accounts/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
    
    def test_deposit(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post('/transactions/deposit/', {
            'amount': '100.00'
        })
        self.assertEqual(response.status_code, 302)
```