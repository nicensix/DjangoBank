# 🔌 API Documentation

## Overview

This document outlines the API endpoints for the Django Banking Platform. While the current implementation focuses on web-based interactions, this documentation serves as a blueprint for future API development and integration with mobile applications or third-party services.

## Authentication

All API endpoints require authentication using Django's session-based authentication or token-based authentication (to be implemented).

### Authentication Methods

#### Session Authentication (Current)
```http
POST /accounts/login/
Content-Type: application/json

{
    "username": "user@example.com",
    "password": "secure_password"
}
```

#### Token Authentication (Future Implementation)
```http
POST /api/auth/token/
Content-Type: application/json

{
    "username": "user@example.com", 
    "password": "secure_password"
}

Response:
{
    "token": "abc123def456ghi789",
    "expires_at": "2024-12-31T23:59:59Z"
}
```

## API Endpoints

### User Management

#### Register New User
```http
POST 