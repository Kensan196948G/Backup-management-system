"""
Authentication Routes
Login, logout, password management, and user profile routes
"""

from datetime import datetime, timedelta

import jwt
from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func

from app.auth import auth_bp
from app.auth.decorators import check_account_locked
from app.auth.forms import (
    ChangePasswordForm,
    LoginForm,
    ProfileEditForm,
    ResetPasswordForm,
    ResetPasswordRequestForm,
)
from app.models import AuditLog, User, db


def log_audit(action_type, resource_type=None, resource_id=None, action_result="success", details=None):
    """
    Log audit trail for security and compliance

    Args:
        action_type: Type of action (login, logout, password_change, etc.)
        resource_type: Type of resource affected (user, backup_job, etc.)
        resource_id: ID of the resource
        action_result: Result of action (success, failed)
        details: Additional details (JSON string)
    """
    try:
        audit_log = AuditLog(
            user_id=current_user.id if current_user.is_authenticated else None,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=request.remote_addr,
            action_result=action_result,
            details=details,
        )
        db.session.add(audit_log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Failed to log audit: {str(e)}")
        db.session.rollback()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Login route
    Handles user authentication with rate limiting and account lockout
    """
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember = form.remember_me.data

        # Find user
        user = User.query.filter_by(username=username).first()

        if user is None:
            # User not found
            flash("Invalid username or password", "danger")
            log_audit("login", action_result="failed", details=f"Username not found: {username}")
            return render_template("auth/login.html", form=form)

        # Check if account is locked
        is_locked, remaining_time = check_account_locked(user)
        if is_locked:
            minutes = remaining_time // 60
            seconds = remaining_time % 60
            flash(
                f"Account is locked due to multiple failed login attempts. " f"Please try again in {minutes}m {seconds}s",
                "danger",
            )
            log_audit("login", action_result="failed", details=f"Account locked: {username}")
            return render_template("auth/login.html", form=form)

        # Check if account is active
        if not user.is_active:
            flash("Account is inactive. Please contact administrator.", "danger")
            log_audit("login", action_result="failed", details=f"Account inactive: {username}")
            return render_template("auth/login.html", form=form)

        # Verify password
        if not user.check_password(password):
            # Failed login attempt
            user.failed_login_attempts += 1
            user.last_failed_login = datetime.utcnow()

            # Lock account if too many failed attempts
            max_attempts = current_app.config.get("LOGIN_ATTEMPT_LIMIT", 5)
            lockout_duration = current_app.config.get("ACCOUNT_LOCKOUT_DURATION", 600)

            if user.failed_login_attempts >= max_attempts:
                user.account_locked_until = datetime.utcnow() + timedelta(seconds=lockout_duration)
                db.session.commit()
                flash(f"Too many failed login attempts. Account locked for {lockout_duration // 60} minutes.", "danger")
                log_audit("login", action_result="failed", details=f"Account locked after {max_attempts} attempts: {username}")
            else:
                remaining_attempts = max_attempts - user.failed_login_attempts
                db.session.commit()
                flash(f"Invalid username or password. {remaining_attempts} attempts remaining.", "danger")
                log_audit("login", action_result="failed", details=f"Invalid password: {username}")

            return render_template("auth/login.html", form=form)

        # Successful login
        # Reset failed login attempts
        user.failed_login_attempts = 0
        user.last_failed_login = None
        user.account_locked_until = None
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Login user
        login_user(user, remember=remember)

        # Set session timeout
        session.permanent = True
        current_app.permanent_session_lifetime = current_app.config.get("PERMANENT_SESSION_LIFETIME")

        # Log successful login
        log_audit("login", action_result="success", details=f"User logged in: {username}")

        flash(f"Welcome back, {user.full_name or user.username}!", "success")

        # Redirect to next page or dashboard
        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """
    Logout route
    Logs out the current user and clears session
    """
    username = current_user.username
    log_audit("logout", action_result="success", details=f"User logged out: {username}")

    logout_user()
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """
    Change password route
    Allows users to change their own password
    """
    form = ChangePasswordForm()

    if form.validate_on_submit():
        current_password = form.current_password.data
        new_password = form.new_password.data

        # Verify current password
        if not current_user.check_password(current_password):
            flash("Current password is incorrect", "danger")
            return render_template("auth/change_password.html", form=form)

        # Check if new password is same as current
        if current_user.check_password(new_password):
            flash("New password must be different from current password", "danger")
            return render_template("auth/change_password.html", form=form)

        # Update password
        current_user.set_password(new_password)
        current_user.updated_at = datetime.utcnow()
        db.session.commit()

        # Log password change
        log_audit("password_change", resource_type="user", resource_id=current_user.id, action_result="success")

        flash("Password changed successfully", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/change_password.html", form=form)


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """
    User profile view and edit route
    """
    form = ProfileEditForm(original_email=current_user.email)

    if form.validate_on_submit():
        # Update profile
        current_user.email = form.email.data
        current_user.full_name = form.full_name.data
        current_user.department = form.department.data
        current_user.updated_at = datetime.utcnow()
        db.session.commit()

        # Log profile update
        log_audit("profile_update", resource_type="user", resource_id=current_user.id, action_result="success")

        flash("Profile updated successfully", "success")
        return redirect(url_for("auth.profile"))

    # Pre-populate form
    if request.method == "GET":
        form.email.data = current_user.email
        form.full_name.data = current_user.full_name
        form.department.data = current_user.department

    return render_template("auth/profile.html", form=form)


@auth_bp.route("/request-password-reset", methods=["GET", "POST"])
def request_password_reset():
    """
    Password reset request route
    Sends password reset email to user
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = ResetPasswordRequestForm()

    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()

        if user:
            # Generate reset token
            token = generate_reset_token(user)

            # TODO: Send email with reset link
            # For now, just log it
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            current_app.logger.info(f"Password reset requested for {email}")
            current_app.logger.info(f"Reset URL: {reset_url}")

            # Log password reset request
            log_audit("password_reset_request", resource_type="user", resource_id=user.id, action_result="success")

        # Always show success message (security: don't reveal if email exists)
        flash("If your email is registered, you will receive a password reset link.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/request_password_reset.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """
    Password reset route
    Resets password using valid token
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    # Verify token
    user_id = verify_reset_token(token)
    if user_id is None:
        flash("Invalid or expired reset token", "danger")
        return redirect(url_for("auth.login"))

    user = db.session.get(User, user_id)
    if user is None:
        flash("User not found", "danger")
        return redirect(url_for("auth.login"))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        # Set new password
        user.set_password(form.password.data)
        user.updated_at = datetime.utcnow()

        # Reset failed login attempts
        user.failed_login_attempts = 0
        user.last_failed_login = None
        user.account_locked_until = None

        db.session.commit()

        # Log password reset
        log_audit("password_reset", resource_type="user", resource_id=user.id, action_result="success")

        flash("Password has been reset successfully. You can now login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form)


# API Routes for authentication


@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    """
    API login endpoint
    Returns JWT token for API authentication
    """
    data = request.get_json()

    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": {"code": "INVALID_REQUEST", "message": "Username and password required"}}), 400

    username = data["username"]
    password = data["password"]

    # Find user
    user = User.query.filter_by(username=username).first()

    if user is None or not user.check_password(password):
        log_audit("api_login", action_result="failed", details=f"Invalid credentials: {username}")
        return jsonify({"error": {"code": "AUTHENTICATION_FAILED", "message": "Invalid username or password"}}), 401

    # Check if account is active
    if not user.is_active:
        return jsonify({"error": {"code": "ACCOUNT_INACTIVE", "message": "Account is inactive"}}), 403

    # Check if account is locked
    is_locked, remaining_time = check_account_locked(user)
    if is_locked:
        return jsonify({"error": {"code": "ACCOUNT_LOCKED", "message": f"Account locked for {remaining_time} seconds"}}), 403

    # Generate JWT token
    access_token = generate_access_token(user)
    refresh_token = generate_refresh_token(user)

    # Update last login
    user.last_login = datetime.utcnow()
    user.failed_login_attempts = 0
    db.session.commit()

    # Log successful API login
    log_audit("api_login", action_result="success", details=f"API login: {username}")

    return (
        jsonify(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": int(current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES").total_seconds()),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                },
            }
        ),
        200,
    )


@auth_bp.route("/api/refresh", methods=["POST"])
def api_refresh_token():
    """
    API token refresh endpoint
    Returns new access token using refresh token
    """
    data = request.get_json()

    if not data or "refresh_token" not in data:
        return jsonify({"error": {"code": "INVALID_REQUEST", "message": "Refresh token required"}}), 400

    refresh_token = data["refresh_token"]

    # Verify refresh token
    user_id = verify_refresh_token(refresh_token)
    if user_id is None:
        return jsonify({"error": {"code": "INVALID_TOKEN", "message": "Invalid or expired refresh token"}}), 401

    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        return jsonify({"error": {"code": "USER_NOT_FOUND", "message": "User not found or inactive"}}), 401

    # Generate new access token
    access_token = generate_access_token(user)

    return (
        jsonify(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": int(current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES").total_seconds()),
            }
        ),
        200,
    )


# JWT Token Helper Functions


def generate_access_token(user):
    """Generate JWT access token"""
    expires_delta = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", timedelta(hours=1))
    if isinstance(expires_delta, int):
        expires_delta = timedelta(seconds=expires_delta)

    payload = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "exp": datetime.utcnow() + expires_delta,
        "iat": datetime.utcnow(),
        "type": "access",
    }

    token = jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")

    return token


def generate_refresh_token(user):
    """Generate JWT refresh token"""
    expires_delta = current_app.config.get("JWT_REFRESH_TOKEN_EXPIRES", timedelta(days=7))
    if isinstance(expires_delta, int):
        expires_delta = timedelta(seconds=expires_delta)

    payload = {"user_id": user.id, "exp": datetime.utcnow() + expires_delta, "iat": datetime.utcnow(), "type": "refresh"}

    token = jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")

    return token


def verify_refresh_token(token):
    """Verify JWT refresh token and return user_id"""
    try:
        payload = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])

        if payload.get("type") != "refresh":
            return None

        return payload.get("user_id")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def generate_reset_token(user):
    """Generate password reset token"""
    payload = {"user_id": user.id, "exp": datetime.utcnow() + timedelta(hours=1), "iat": datetime.utcnow(), "type": "reset"}

    token = jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")

    return token


def verify_reset_token(token):
    """Verify password reset token and return user_id"""
    try:
        payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])

        if payload.get("type") != "reset":
            return None

        return payload.get("user_id")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
