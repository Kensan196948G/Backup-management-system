"""
Authentication Forms
WTForms for login, password change, and user management
"""
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    Regexp,
    ValidationError,
)

from app.models import User


class LoginForm(FlaskForm):
    """Login form"""

    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required"),
            Length(min=3, max=50, message="Username must be 3-50 characters"),
        ],
        render_kw={"placeholder": "Enter username", "autocomplete": "username"},
    )

    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Password is required")],
        render_kw={"placeholder": "Enter password", "autocomplete": "current-password"},
    )

    remember_me = BooleanField("Remember Me")

    submit = SubmitField("Login")


class ChangePasswordForm(FlaskForm):
    """Change password form for logged-in users"""

    current_password = PasswordField(
        "Current Password",
        validators=[DataRequired(message="Current password is required")],
        render_kw={"placeholder": "Enter current password", "autocomplete": "current-password"},
    )

    new_password = PasswordField(
        "New Password",
        validators=[
            DataRequired(message="New password is required"),
            Length(min=8, message="Password must be at least 8 characters"),
            Regexp(
                r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]",
                message="Password must contain uppercase, lowercase, digit, and special character",
            ),
        ],
        render_kw={"placeholder": "Enter new password", "autocomplete": "new-password"},
    )

    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(message="Password confirmation is required"),
            EqualTo("new_password", message="Passwords must match"),
        ],
        render_kw={"placeholder": "Confirm new password", "autocomplete": "new-password"},
    )

    submit = SubmitField("Change Password")

    def validate_new_password(self, field):
        """Custom validator to ensure new password is different from current"""
        # This will be checked in the route using check_password


class ResetPasswordRequestForm(FlaskForm):
    """Password reset request form"""

    email = StringField(
        "Email",
        validators=[DataRequired(message="Email is required"), Email(message="Invalid email address")],
        render_kw={"placeholder": "Enter your email", "autocomplete": "email"},
    )

    submit = SubmitField("Request Password Reset")

    def validate_email(self, field):
        """Verify email exists in database"""
        user = User.query.filter_by(email=field.data).first()
        if not user:
            raise ValidationError("Email address not found")


class ResetPasswordForm(FlaskForm):
    """Password reset form (after receiving reset token)"""

    password = PasswordField(
        "New Password",
        validators=[
            DataRequired(message="New password is required"),
            Length(min=8, message="Password must be at least 8 characters"),
            Regexp(
                r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]",
                message="Password must contain uppercase, lowercase, digit, and special character",
            ),
        ],
        render_kw={"placeholder": "Enter new password", "autocomplete": "new-password"},
    )

    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(message="Password confirmation is required"),
            EqualTo("password", message="Passwords must match"),
        ],
        render_kw={"placeholder": "Confirm new password", "autocomplete": "new-password"},
    )

    submit = SubmitField("Reset Password")


class UserCreateForm(FlaskForm):
    """User creation form (admin only)"""

    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required"),
            Length(min=3, max=50, message="Username must be 3-50 characters"),
            Regexp(r"^[a-zA-Z0-9_-]+$", message="Username can only contain letters, numbers, hyphens, and underscores"),
        ],
        render_kw={"placeholder": "Enter username"},
    )

    email = StringField(
        "Email",
        validators=[DataRequired(message="Email is required"), Email(message="Invalid email address"), Length(max=100)],
        render_kw={"placeholder": "user@example.com"},
    )

    full_name = StringField("Full Name", validators=[Length(max=100)], render_kw={"placeholder": "Enter full name"})

    department = StringField("Department", validators=[Length(max=100)], render_kw={"placeholder": "Enter department"})

    role = SelectField(
        "Role",
        choices=[("admin", "Administrator"), ("operator", "Operator"), ("viewer", "Viewer"), ("auditor", "Auditor")],
        validators=[DataRequired(message="Role is required")],
    )

    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required"),
            Length(min=8, message="Password must be at least 8 characters"),
            Regexp(
                r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]",
                message="Password must contain uppercase, lowercase, digit, and special character",
            ),
        ],
        render_kw={"placeholder": "Enter password", "autocomplete": "new-password"},
    )

    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(message="Password confirmation is required"),
            EqualTo("password", message="Passwords must match"),
        ],
        render_kw={"placeholder": "Confirm password", "autocomplete": "new-password"},
    )

    is_active = BooleanField("Active Account", default=True)

    submit = SubmitField("Create User")

    def validate_username(self, field):
        """Verify username is unique"""
        user = User.query.filter_by(username=field.data).first()
        if user:
            raise ValidationError("Username already exists")

    def validate_email(self, field):
        """Verify email is unique"""
        user = User.query.filter_by(email=field.data).first()
        if user:
            raise ValidationError("Email already registered")


class UserEditForm(FlaskForm):
    """User edit form (admin only)"""

    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required"),
            Length(min=3, max=50, message="Username must be 3-50 characters"),
        ],
        render_kw={"readonly": True},  # Username cannot be changed
    )

    email = StringField(
        "Email",
        validators=[DataRequired(message="Email is required"), Email(message="Invalid email address"), Length(max=100)],
        render_kw={"placeholder": "user@example.com"},
    )

    full_name = StringField("Full Name", validators=[Length(max=100)], render_kw={"placeholder": "Enter full name"})

    department = StringField("Department", validators=[Length(max=100)], render_kw={"placeholder": "Enter department"})

    role = SelectField(
        "Role",
        choices=[("admin", "Administrator"), ("operator", "Operator"), ("viewer", "Viewer"), ("auditor", "Auditor")],
        validators=[DataRequired(message="Role is required")],
    )

    is_active = BooleanField("Active Account")

    submit = SubmitField("Update User")

    def __init__(self, original_email, *args, **kwargs):
        """Initialize form with original email for validation"""
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, field):
        """Verify email is unique (excluding current user)"""
        if field.data != self.original_email:
            user = User.query.filter_by(email=field.data).first()
            if user:
                raise ValidationError("Email already registered")


class ProfileEditForm(FlaskForm):
    """Profile edit form (for current user)"""

    email = StringField(
        "Email",
        validators=[DataRequired(message="Email is required"), Email(message="Invalid email address"), Length(max=100)],
        render_kw={"placeholder": "user@example.com"},
    )

    full_name = StringField("Full Name", validators=[Length(max=100)], render_kw={"placeholder": "Enter full name"})

    department = StringField("Department", validators=[Length(max=100)], render_kw={"placeholder": "Enter department"})

    submit = SubmitField("Update Profile")

    def __init__(self, original_email, *args, **kwargs):
        """Initialize form with original email for validation"""
        super(ProfileEditForm, self).__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, field):
        """Verify email is unique (excluding current user)"""
        if field.data != self.original_email:
            user = User.query.filter_by(email=field.data).first()
            if user:
                raise ValidationError("Email already registered")
