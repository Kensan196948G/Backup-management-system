# Authentication and Authorization System Implementation

## Overview

This document describes the implementation of the authentication and authorization system for the Backup Management System. The system implements Flask-Login with role-based access control (RBAC), login attempt limiting, session management, and CSRF protection.

## Architecture

### Components

1. **Flask-Login Integration** - User session management
2. **Role-Based Access Control (RBAC)** - Four user roles with different permissions
3. **Login Attempt Limiting** - Account lockout after failed attempts
4. **Session Management** - Secure session handling with timeouts
5. **CSRF Protection** - Flask-WTF CSRF token validation
6. **JWT API Authentication** - Token-based authentication for API endpoints

## Implemented Files

### 1. `/app/auth/__init__.py`

Blueprint definition for authentication module.

**Features:**
- Creates `auth_bp` Blueprint with `/auth` URL prefix
- Imports routes after blueprint creation to avoid circular imports

### 2. `/app/auth/decorators.py`

Role-based access control decorators for protecting routes.

**Decorators:**

```python
@login_required              # Require authentication
@role_required('admin')      # Require specific role(s)
@admin_required             # Admin only
@operator_required          # Operator or Admin
@viewer_required            # Viewer, Operator, or Admin
@auditor_required           # Auditor or Admin
@api_token_required         # API token authentication
@account_active_required    # Account must be active
```

**Helper Functions:**
- `check_account_locked(user)` - Check if account is locked due to failed login attempts

### 3. `/app/auth/forms.py`

WTForms for authentication and user management.

**Forms:**

- `LoginForm` - User login with username/password
- `ChangePasswordForm` - Password change for logged-in users
- `ResetPasswordRequestForm` - Request password reset via email
- `ResetPasswordForm` - Reset password with token
- `UserCreateForm` - Admin form to create new users
- `UserEditForm` - Admin form to edit user accounts
- `ProfileEditForm` - User profile self-editing

**Password Policy:**
- Minimum 8 characters
- Must contain: uppercase, lowercase, digit, special character
- Pattern: `^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]`

### 4. `/app/auth/routes.py`

Authentication routes and API endpoints.

**Web Routes:**

| Route | Method | Description |
|-------|--------|-------------|
| `/auth/login` | GET, POST | User login page |
| `/auth/logout` | GET | User logout |
| `/auth/change-password` | GET, POST | Change password |
| `/auth/profile` | GET, POST | View/edit user profile |
| `/auth/request-password-reset` | GET, POST | Request password reset |
| `/auth/reset-password/<token>` | GET, POST | Reset password with token |

**API Routes:**

| Route | Method | Description |
|-------|--------|-------------|
| `/auth/api/login` | POST | API login (returns JWT token) |
| `/auth/api/refresh` | POST | Refresh access token |

**Features:**
- Login attempt tracking and account lockout
- Audit logging for all authentication events
- JWT token generation and verification
- Password reset token generation
- Session management with configurable timeout

## User Model Extensions

Updated `/app/models.py` with Flask-Login integration:

**New Fields:**
```python
failed_login_attempts = db.Column(db.Integer, default=0)
last_failed_login = db.Column(db.DateTime)
account_locked_until = db.Column(db.DateTime)
```

**New Methods:**
```python
set_password(password)           # Hash and set password (bcrypt)
check_password(password)         # Verify password
has_role(role)                   # Check specific role
has_any_role(*roles)            # Check multiple roles
is_admin()                       # Check if admin
is_operator()                    # Check if operator or above
is_viewer()                      # Check if viewer or above
get_id()                         # Flask-Login user ID
```

**Flask-Login Properties:**
```python
is_authenticated    # Always True for logged-in users
is_anonymous       # Always False for User objects
is_active          # Check if account is active
```

## User Roles

### Role Hierarchy

1. **Admin** - Full system access
   - User management
   - System configuration
   - All operator and viewer permissions

2. **Operator** - Backup operations
   - Create/edit/delete backup jobs
   - Manage offline media
   - Run verification tests
   - Generate reports

3. **Viewer** - Read-only access
   - View dashboards
   - View backup jobs
   - View reports

4. **Auditor** - Audit and compliance
   - View audit logs
   - View compliance reports
   - Read-only access to all data

## Login Security Features

### 1. Login Attempt Limiting

**Configuration (in `app/config.py`):**
```python
LOGIN_ATTEMPT_LIMIT = 5           # Max failed attempts
LOGIN_ATTEMPT_WINDOW = 600        # 10 minutes window
ACCOUNT_LOCKOUT_DURATION = 600    # 10 minutes lockout
```

**Behavior:**
- After 5 failed login attempts, account is locked for 10 minutes
- Failed attempts counter resets on successful login
- Lockout automatically expires after timeout
- User receives countdown message showing remaining lockout time

### 2. Session Management

**Configuration (in `app/config.py`):**
```python
SESSION_COOKIE_HTTPONLY = True        # Prevent XSS
SESSION_COOKIE_SAMESITE = 'Strict'    # CSRF protection
SESSION_COOKIE_SECURE = True          # HTTPS only (production)
PERMANENT_SESSION_LIFETIME = 30       # 30 minutes timeout
REMEMBER_COOKIE_DURATION = 7 days     # "Remember Me" duration
```

### 3. CSRF Protection

**Configuration (in `app/config.py`):**
```python
WTF_CSRF_ENABLED = True              # Enable CSRF protection
WTF_CSRF_TIME_LIMIT = None           # No expiration
```

**Usage in templates:**
```html
<form method="POST">
    {{ form.hidden_tag() }}  <!-- Includes CSRF token -->
    ...
</form>
```

### 4. Password Security

- Passwords hashed using **bcrypt** with auto-generated salt
- Password policy enforced at form validation level
- Password history tracking (planned feature)
- Password expiry (planned feature)

## API Authentication

### JWT Token Flow

1. **Login** - `POST /auth/api/login`
   ```json
   {
       "username": "user",
       "password": "pass"
   }
   ```

   Response:
   ```json
   {
       "access_token": "eyJ...",
       "refresh_token": "eyJ...",
       "token_type": "Bearer",
       "expires_in": 3600,
       "user": {
           "id": 1,
           "username": "user",
           "role": "operator"
       }
   }
   ```

2. **Use Token** - Include in Authorization header
   ```
   Authorization: Bearer eyJ...
   ```

3. **Refresh Token** - `POST /auth/api/refresh`
   ```json
   {
       "refresh_token": "eyJ..."
   }
   ```

### Token Configuration

**In `app/config.py`:**
```python
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
```

## Audit Logging

All authentication events are logged to `audit_logs` table:

**Logged Events:**
- `login` - Successful/failed login attempts
- `logout` - User logout
- `password_change` - Password change
- `password_reset` - Password reset
- `password_reset_request` - Password reset request
- `profile_update` - Profile information update
- `api_login` - API authentication

**Audit Log Fields:**
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

## Template Files

Created authentication templates in `/app/templates/auth/`:

1. `login.html` - Login page
2. `change_password.html` - Password change form
3. `profile.html` - User profile view/edit
4. `request_password_reset.html` - Password reset request
5. `reset_password.html` - Password reset form

All templates extend `base.html` and use Bootstrap 5 styling with responsive design.

## Usage Examples

### Protecting Routes

```python
from app.auth.decorators import login_required, operator_required, admin_required

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/jobs/create')
@operator_required
def create_job():
    return render_template('jobs/create.html')

@app.route('/admin/users')
@admin_required
def admin_users():
    return render_template('admin/users.html')
```

### API Protection

```python
from app.auth.decorators import api_token_required, role_required

@app.route('/api/v1/jobs')
@api_token_required
@role_required('admin', 'operator')
def api_get_jobs():
    jobs = BackupJob.query.all()
    return jsonify([job.to_dict() for job in jobs])
```

### Creating Users Programmatically

```python
from app.models import db, User

# Create admin user
admin = User(
    username='admin',
    email='admin@example.com',
    full_name='System Administrator',
    role='admin',
    is_active=True
)
admin.set_password('SecurePassword123!')
db.session.add(admin)
db.session.commit()
```

## Integration with Main Application

To integrate the authentication system, add to your main app initialization:

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

## Security Considerations

1. **Environment Variables** - Store secrets in environment variables:
   ```bash
   export SECRET_KEY='your-secret-key-here'
   export JWT_SECRET_KEY='your-jwt-secret-here'
   ```

2. **HTTPS in Production** - Always use HTTPS in production:
   ```python
   SESSION_COOKIE_SECURE = True
   PREFERRED_URL_SCHEME = 'https'
   ```

3. **Strong Passwords** - Enforce password policy through configuration:
   ```python
   PASSWORD_MIN_LENGTH = 8
   PASSWORD_REQUIRE_UPPERCASE = True
   PASSWORD_REQUIRE_LOWERCASE = True
   PASSWORD_REQUIRE_DIGIT = True
   PASSWORD_REQUIRE_SPECIAL = True
   ```

4. **Regular Security Audits** - Review audit logs regularly:
   ```python
   # Query failed login attempts
   failed_logins = AuditLog.query.filter_by(
       action_type='login',
       action_result='failed'
   ).order_by(AuditLog.created_at.desc()).limit(100).all()
   ```

## Testing

### Manual Testing Steps

1. **Login Flow**
   - Access `/auth/login`
   - Enter valid credentials
   - Verify redirect to dashboard
   - Check session cookie is set

2. **Failed Login**
   - Enter invalid password 3 times
   - Verify attempt counter decreases
   - Enter invalid password 5 times
   - Verify account is locked

3. **Password Change**
   - Login as user
   - Access `/auth/change-password`
   - Enter current and new password
   - Verify password is updated

4. **API Authentication**
   - POST to `/auth/api/login` with credentials
   - Verify JWT token is returned
   - Use token in Authorization header
   - Verify API access works

### Unit Testing

```python
import unittest
from app import create_app, db
from app.models import User

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            user = User(username='test', email='test@example.com', role='operator')
            user.set_password('Test123!')
            db.session.add(user)
            db.session.commit()

    def test_login(self):
        response = self.client.post('/auth/login', data={
            'username': 'test',
            'password': 'Test123!',
            'csrf_token': self.get_csrf_token()
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
```

## Future Enhancements

1. **Two-Factor Authentication (2FA)**
   - TOTP support
   - SMS verification
   - Backup codes

2. **OAuth2/OIDC Integration**
   - Google Sign-In
   - Microsoft Azure AD
   - Generic OIDC providers

3. **Active Directory / LDAP**
   - AD authentication
   - Group-based role mapping
   - User sync

4. **Advanced Password Policies**
   - Password history (prevent reuse)
   - Password expiration
   - Complexity scoring

5. **Session Management**
   - Active session tracking
   - Remote logout
   - Device management

6. **API Key Management**
   - Long-lived API keys
   - Key rotation
   - Key scoping (permissions)

## Troubleshooting

### Issue: CSRF Token Missing

**Symptom:** Form submission returns 400 Bad Request with CSRF error

**Solution:** Ensure `{{ form.hidden_tag() }}` is included in all forms

### Issue: User Not Found After Login

**Symptom:** Login succeeds but user_loader returns None

**Solution:** Check that `load_user()` function is properly registered:
```python
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
```

### Issue: Account Locked Permanently

**Symptom:** Account remains locked after timeout expires

**Solution:** Check that `account_locked_until` is being compared to UTC time:
```python
if user.account_locked_until > datetime.utcnow():
    # Still locked
```

### Issue: API Token Not Working

**Symptom:** API requests return 401 Unauthorized

**Solution:** Verify Authorization header format:
```
Authorization: Bearer <token>
```

## References

- [Flask-Login Documentation](https://flask-login.readthedocs.io/)
- [Flask-WTF Documentation](https://flask-wtf.readthedocs.io/)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)

## License

Copyright (c) 2025 Backup Management System
All rights reserved.
