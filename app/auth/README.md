# Authentication & Authorization Module

## Overview

This module implements a comprehensive authentication and authorization system for the Backup Management System using Flask-Login, bcrypt password hashing, JWT tokens for API access, and role-based access control (RBAC).

## Features

- User authentication with Flask-Login
- Role-based access control (Admin, Operator, Viewer, Auditor)
- Login attempt limiting and account lockout
- Secure password hashing with bcrypt
- Session management with configurable timeout
- CSRF protection with Flask-WTF
- JWT token-based API authentication
- Password change and reset functionality
- Audit logging for all authentication events
- User profile management

## File Structure

```
app/auth/
├── __init__.py         # Blueprint definition
├── decorators.py       # Role-based access control decorators
├── forms.py            # WTForms for authentication
├── routes.py           # Authentication routes and API endpoints
└── README.md           # This file

app/templates/auth/
├── login.html                      # Login page
├── change_password.html            # Password change form
├── profile.html                    # User profile page
├── request_password_reset.html     # Password reset request
└── reset_password.html             # Password reset form
```

## Quick Start

### 1. Register Blueprint

In your main application file (`app/__init__.py` or `run.py`):

```python
from flask import Flask
from flask_login import LoginManager
from app.models import db, User
from app.auth import auth_bp

app = Flask(__name__)
app.config.from_object('app.config.DevelopmentConfig')

# Initialize database
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register authentication blueprint
app.register_blueprint(auth_bp)
```

### 2. Create Initial Admin User

```python
from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    # Create admin user
    admin = User(
        username='admin',
        email='admin@example.com',
        full_name='System Administrator',
        department='IT',
        role='admin',
        is_active=True
    )
    admin.set_password('Admin123!@#')
    db.session.add(admin)
    db.session.commit()
    print(f"Admin user created: {admin.username}")
```

### 3. Protect Routes

```python
from app.auth.decorators import login_required, admin_required, operator_required

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/backup/create')
@operator_required  # Requires operator or admin role
def create_backup():
    return render_template('backup/create.html')

@app.route('/admin/users')
@admin_required  # Requires admin role only
def admin_users():
    return render_template('admin/users.html')
```

## User Roles

### Role Hierarchy

| Role | Description | Permissions |
|------|-------------|-------------|
| **Admin** | System administrator | Full access to all features including user management |
| **Operator** | Backup operator | Create/edit/delete backup jobs, manage media, run verification |
| **Viewer** | Read-only user | View dashboards, jobs, and reports |
| **Auditor** | Compliance auditor | View audit logs and compliance reports (read-only) |

### Decorator Usage

```python
from app.auth.decorators import (
    login_required,
    role_required,
    admin_required,
    operator_required,
    viewer_required,
    auditor_required
)

# Require authentication only
@login_required
def protected_route():
    pass

# Require specific role
@role_required('admin')
def admin_only():
    pass

# Require one of multiple roles
@role_required('admin', 'operator')
def admin_or_operator():
    pass

# Convenience decorators
@admin_required
def admin_route():
    pass

@operator_required  # Admin or Operator
def operator_route():
    pass

@viewer_required  # Admin, Operator, or Viewer
def viewer_route():
    pass

@auditor_required  # Admin or Auditor
def auditor_route():
    pass
```

## Authentication Routes

### Web Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/auth/login` | GET, POST | User login |
| `/auth/logout` | GET | User logout |
| `/auth/change-password` | GET, POST | Change password |
| `/auth/profile` | GET, POST | View/edit profile |
| `/auth/request-password-reset` | GET, POST | Request password reset |
| `/auth/reset-password/<token>` | GET, POST | Reset password with token |

### API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/auth/api/login` | POST | API login (returns JWT) |
| `/auth/api/refresh` | POST | Refresh access token |

## API Authentication

### Login and Get Token

```bash
curl -X POST http://localhost:5000/auth/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "Admin123!@#"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "full_name": "System Administrator",
    "role": "admin"
  }
}
```

### Use Token in API Requests

```bash
curl -X GET http://localhost:5000/api/v1/jobs \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### Refresh Token

```bash
curl -X POST http://localhost:5000/auth/api/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }'
```

## Security Features

### 1. Login Attempt Limiting

- Maximum 5 failed login attempts (configurable)
- Account locked for 10 minutes after limit exceeded
- Automatic unlock after timeout
- Counter resets on successful login

Configuration in `app/config.py`:
```python
LOGIN_ATTEMPT_LIMIT = 5
LOGIN_ATTEMPT_WINDOW = 600  # seconds
ACCOUNT_LOCKOUT_DURATION = 600  # seconds
```

### 2. Password Policy

- Minimum 8 characters
- Must contain:
  - At least one uppercase letter (A-Z)
  - At least one lowercase letter (a-z)
  - At least one digit (0-9)
  - At least one special character (@$!%*?&)

Configuration in `app/config.py`:
```python
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGIT = True
PASSWORD_REQUIRE_SPECIAL = True
```

### 3. Session Security

Configuration in `app/config.py`:
```python
# Session cookie settings
SESSION_COOKIE_HTTPONLY = True      # Prevent XSS
SESSION_COOKIE_SAMESITE = 'Strict'  # CSRF protection
SESSION_COOKIE_SECURE = True        # HTTPS only (production)
PERMANENT_SESSION_LIFETIME = 30     # minutes

# Remember me cookie
REMEMBER_COOKIE_DURATION = 7  # days
```

### 4. CSRF Protection

All forms include CSRF tokens automatically via Flask-WTF:

```html
<form method="POST">
    {{ form.hidden_tag() }}  <!-- Includes CSRF token -->
    <!-- form fields -->
</form>
```

### 5. Password Hashing

Passwords are hashed using bcrypt with automatic salt generation:

```python
# Setting password (in User model)
user.set_password('password123')

# Verifying password
if user.check_password('password123'):
    # Password is correct
```

## Audit Logging

All authentication events are automatically logged to the `audit_logs` table:

**Logged Events:**
- `login` - Login attempts (success/failed)
- `logout` - User logout
- `password_change` - Password changes
- `password_reset` - Password resets
- `password_reset_request` - Password reset requests
- `profile_update` - Profile updates
- `api_login` - API authentication

**Log Fields:**
```python
user_id          # User who performed action
action_type      # Type of action
resource_type    # Type of resource affected
resource_id      # ID of resource
ip_address       # Client IP address
action_result    # success/failed
details          # Additional details (JSON)
created_at       # Timestamp
```

**Querying Audit Logs:**

```python
from app.models import AuditLog

# Get failed login attempts
failed_logins = AuditLog.query.filter_by(
    action_type='login',
    action_result='failed'
).order_by(AuditLog.created_at.desc()).all()

# Get specific user's activity
user_activity = AuditLog.query.filter_by(
    user_id=1
).order_by(AuditLog.created_at.desc()).limit(50).all()
```

## Configuration

All authentication settings are in `app/config.py`:

```python
# Flask-Login
REMEMBER_COOKIE_DURATION = timedelta(days=7)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

# Security
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None

# Password Policy
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGIT = True
PASSWORD_REQUIRE_SPECIAL = True

# Login Protection
LOGIN_ATTEMPT_LIMIT = 5
LOGIN_ATTEMPT_WINDOW = 600  # 10 minutes
ACCOUNT_LOCKOUT_DURATION = 600  # 10 minutes

# JWT
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
```

## Database Schema

The authentication system uses the following database fields in the `users` table:

```python
# Basic user information
id                      # Primary key
username                # Unique username
email                   # Unique email
password_hash           # Bcrypt hashed password
full_name               # Full name
department              # Department
role                    # User role (admin/operator/viewer/auditor)
is_active               # Account active status
last_login              # Last login timestamp

# Login attempt tracking
failed_login_attempts   # Failed login counter
last_failed_login       # Last failed login timestamp
account_locked_until    # Account lock expiry timestamp

# Timestamps
created_at              # Account creation timestamp
updated_at              # Last update timestamp
```

## Testing

### Manual Testing

1. Start the application
2. Navigate to `http://localhost:5000/auth/login`
3. Login with admin credentials
4. Test password change at `/auth/change-password`
5. Test profile edit at `/auth/profile`
6. Test logout at `/auth/logout`

### Testing Failed Login Attempts

1. Login with incorrect password 5 times
2. Verify account is locked
3. Wait 10 minutes
4. Verify account is unlocked

### Testing API Authentication

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:5000/auth/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123!@#"}' | \
  jq -r '.access_token')

# Use token
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/v1/jobs
```

## Troubleshooting

### Issue: "CSRF token missing"

**Solution:** Ensure `{{ form.hidden_tag() }}` is in your form:
```html
<form method="POST">
    {{ form.hidden_tag() }}
    <!-- rest of form -->
</form>
```

### Issue: User not found after login

**Solution:** Check `user_loader` is registered:
```python
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
```

### Issue: Account permanently locked

**Solution:** Check datetime comparison uses UTC:
```python
if user.account_locked_until > datetime.utcnow():
    # Still locked
```

### Issue: API returns 401 Unauthorized

**Solution:** Verify token format:
```
Authorization: Bearer <token>
```
Not:
```
Authorization: <token>  # Wrong!
```

## Dependencies

- Flask-Login >= 0.6.3
- Flask-WTF >= 1.2.1
- WTForms >= 3.1.1
- bcrypt >= 4.1.2
- PyJWT >= 2.8.0
- email-validator >= 2.1.0

## Documentation

For detailed documentation, see:
- [AUTH_IMPLEMENTATION.md](/docs/AUTH_IMPLEMENTATION.md) - Complete implementation guide
- [Design Specification (Japanese)](/docs/設計仕様書_3-2-1-1-0バックアップ管理システム.txt) - Chapter 8

## License

Copyright (c) 2025 Backup Management System
All rights reserved.
