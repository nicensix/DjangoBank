# Django Banking Platform

A secure Django-based banking platform that simulates core banking operations including user authentication, account management, transaction processing, and administrative oversight.

## Features

- Secure user authentication and registration
- Bank account management with unique account numbers
- Transaction processing (deposits, withdrawals, transfers)
- Transaction history and statement generation
- Administrative dashboard for user and account management
- Responsive web interface with Bootstrap

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd DjangoBank
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Copy environment configuration:
```bash
cp .env.example .env
```

6. Run database migrations:
```bash
python manage.py migrate
```

7. Create a superuser (optional):
```bash
python manage.py createsuperuser
```

8. Run the development server:
```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`

## Project Structure

```
banking_platform/
├── banking_platform/          # Main project directory
│   ├── settings/              # Settings package
│   │   ├── base.py           # Base settings
│   │   ├── development.py    # Development settings
│   │   └── production.py     # Production settings
│   ├── urls.py               # Main URL configuration
│   └── wsgi.py               # WSGI configuration
├── core/                     # Core app
│   ├── templates/            # Core templates
│   ├── management/           # Management commands
│   ├── utils.py              # Utility functions
│   └── views.py              # Core views
├── static/                   # Static files (CSS, JS, images)
├── media/                    # User uploaded files
├── templates/                # Global templates
└── manage.py                 # Django management script
```

## Running Tests

```bash
python manage.py test
```

## Environment Configuration

The project uses environment-specific settings:

- **Development**: `banking_platform.settings.development`
- **Production**: `banking_platform.settings.production`

Set the `DJANGO_SETTINGS_MODULE` environment variable to switch between environments.

## Security Features

- CSRF protection on all forms
- Secure password hashing using Django's built-in authentication
- Input validation and sanitization
- Atomic database transactions for financial operations
- Session security and proper authentication checks

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests to ensure everything works
5. Submit a pull request

## License

This project is for educational purposes.