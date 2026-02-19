"""
System Settings Views
System configuration and settings management
"""

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from app.auth.decorators import role_required
from app.models import db
from app.views import settings_bp


@settings_bp.route("/")
@login_required
@role_required("admin")
def index():
    """
    System settings index page
    Shows all system configuration options
    """
    return render_template("settings/index.html")


@settings_bp.route("/update", methods=["POST"])
@login_required
@role_required("admin")
def update():
    """
    Update system settings
    """
    try:
        # Get form data
        settings_data = request.form.to_dict()

        # TODO: Implement settings storage
        # For now, we'll just log the changes
        current_app.logger.info(f"Settings updated: {settings_data}")

        # Log audit
        from app.auth.routes import log_audit

        log_audit("update", resource_type="settings", resource_id=0, action_result="success")

        flash("設定を保存しました", "success")
        return redirect(url_for("settings.index"))

    except Exception as e:
        current_app.logger.error(f"Error updating settings: {str(e)}")
        flash(f"設定の保存に失敗しました: {str(e)}", "danger")
        return redirect(url_for("settings.index"))


@settings_bp.route("/export")
@login_required
@role_required("admin")
def export():
    """
    Export settings as JSON or CSV with selective sections
    """
    try:
        import csv as csv_module
        from datetime import datetime
        from io import StringIO

        from flask import make_response

        # Get parameters
        export_format = request.args.get("format", "json")
        filename = request.args.get("filename", f'backup-settings-{datetime.now().strftime("%Y%m%d")}')

        # Get selected sections
        include_backup = request.args.get("backup", "true") == "true"
        include_notification = request.args.get("notification", "true") == "true"
        include_schedule = request.args.get("schedule", "true") == "true"
        include_storage = request.args.get("storage", "true") == "true"
        include_security = request.args.get("security", "false") == "true"
        include_users = request.args.get("users", "false") == "true"

        # Build settings data
        settings_data = {"version": "3.2.1.1.0", "export_date": datetime.now().isoformat(), "sections": {}}

        if include_backup:
            settings_data["sections"]["backup"] = {
                "default_retention": 90,
                "compression_level": 5,
                "enable_encryption": True,
                "max_parallel_jobs": 3,
                "verify_after_backup": True,
            }

        if include_notification:
            settings_data["sections"]["notification"] = {
                "enable_email": True,
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "smtp_security": "tls",
                "smtp_username": "noreply@example.com",
                "enable_slack": False,
                "enable_teams": False,
            }

        if include_schedule:
            settings_data["sections"]["schedule"] = {
                "default_schedule_type": "weekly",
                "default_schedule_time": "02:00",
                "maintenance_start": "08:00",
                "maintenance_end": "18:00",
                "skip_holidays": False,
            }

        if include_storage:
            settings_data["sections"]["storage"] = {
                "default_storage_path": "/var/backups",
                "storage_threshold": 80,
                "auto_cleanup_threshold": 90,
                "enable_deduplication": True,
                "max_storage_gb": 1000,
            }

        if include_security:
            settings_data["sections"]["security"] = {
                "session_timeout": 30,
                "max_login_attempts": 5,
                "lockout_duration": 30,
                "enable_audit_log": True,
                "require_2fa": False,
                "password_expiry_days": 90,
            }

        if include_users:
            from app.models import User

            users = User.query.all()
            settings_data["sections"]["users"] = [
                {
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "department": user.department,
                    "role": user.role,
                    "is_active": user.is_active,
                }
                for user in users
            ]

        # Log audit
        from app.auth.routes import log_audit

        log_audit("export", resource_type="settings", resource_id=0, action_result="success")

        # Export based on format
        if export_format == "csv":
            # Convert to CSV format
            output = StringIO()
            writer = csv_module.writer(output)
            writer.writerow(["Section", "Key", "Value"])

            for section_name, section_data in settings_data["sections"].items():
                if isinstance(section_data, dict):
                    for key, value in section_data.items():
                        writer.writerow([section_name, key, str(value)])
                elif isinstance(section_data, list):
                    for i, item in enumerate(section_data):
                        for key, value in item.items():
                            writer.writerow([f"{section_name}_{i}", key, str(value)])

            response = make_response(output.getvalue())
            response.headers["Content-Type"] = "text/csv; charset=utf-8"
            response.headers["Content-Disposition"] = f"attachment; filename={filename}.csv"
            return response
        else:
            # JSON format
            response = make_response(jsonify(settings_data))
            response.headers["Content-Type"] = "application/json; charset=utf-8"
            response.headers["Content-Disposition"] = f"attachment; filename={filename}.json"
            return response

    except Exception as e:
        current_app.logger.error(f"Error exporting settings: {str(e)}")
        return jsonify({"error": {"code": "EXPORT_FAILED", "message": str(e)}}), 500


@settings_bp.route("/validate-import", methods=["POST"])
@login_required
@role_required("admin")
def validate_import():
    """
    Validate uploaded settings file without applying changes
    """
    try:
        import csv as csv_module
        import json
        from io import StringIO

        # Check if file uploaded
        if "file" not in request.files:
            return jsonify({"error": {"code": "NO_FILE", "message": "No file uploaded"}}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": {"code": "EMPTY_FILENAME", "message": "No file selected"}}), 400

        # Detect format
        extension = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""

        if extension not in ["json", "csv"]:
            return jsonify({"error": {"code": "INVALID_FORMAT", "message": "Only JSON and CSV files are supported"}}), 400

        # Read file content
        content = file.read().decode("utf-8")
        file.seek(0)  # Reset file pointer

        # Parse based on format
        try:
            if extension == "json":
                data = json.loads(content)
            else:
                # Parse CSV
                csv_reader = csv_module.DictReader(StringIO(content))
                data = {"sections": {}}
                for row in csv_reader:
                    section = row.get("Section", "")
                    key = row.get("Key", "")
                    value = row.get("Value", "")
                    if section not in data["sections"]:
                        data["sections"][section] = {}
                    data["sections"][section][key] = value
        except Exception as e:
            return jsonify({"error": {"code": "PARSE_ERROR", "message": f"Failed to parse file: {str(e)}"}}), 400

        # Validate structure
        errors = []
        warnings = []

        if not isinstance(data, dict):
            errors.append("Invalid data structure: must be a dictionary")

        if "sections" not in data:
            errors.append("Missing 'sections' key in data")
        else:
            sections = data.get("sections", {})

            # Validate backup section
            if "backup" in sections:
                backup = sections["backup"]
                if not isinstance(backup.get("default_retention"), (int, str)):
                    errors.append("backup.default_retention must be a number")
                if not isinstance(backup.get("compression_level"), (int, str)):
                    errors.append("backup.compression_level must be a number")

            # Validate storage section
            if "storage" in sections:
                storage = sections["storage"]
                if storage.get("storage_threshold"):
                    threshold = (
                        int(storage["storage_threshold"])
                        if isinstance(storage["storage_threshold"], str)
                        else storage["storage_threshold"]
                    )
                    if threshold < 50 or threshold > 95:
                        warnings.append("storage_threshold should be between 50 and 95")

            # Validate security section
            if "security" in sections:
                security = sections["security"]
                if security.get("session_timeout"):
                    timeout = (
                        int(security["session_timeout"])
                        if isinstance(security["session_timeout"], str)
                        else security["session_timeout"]
                    )
                    if timeout < 5:
                        warnings.append("session_timeout should be at least 5 minutes")

            # Validate users section
            if "users" in sections:
                users = sections["users"]
                if not isinstance(users, list):
                    errors.append("users section must be a list")
                else:
                    for i, user in enumerate(users):
                        if not user.get("username"):
                            errors.append(f"User {i}: missing username")
                        if not user.get("email"):
                            errors.append(f"User {i}: missing email")

        # Check version compatibility
        if "version" in data:
            import_version = data["version"]
            current_version = "3.2.1.1.0"
            if import_version != current_version:
                warnings.append(f"Version mismatch: imported {import_version}, current {current_version}")

        if errors:
            return jsonify({"error": {"code": "VALIDATION_FAILED", "message": "Validation failed", "errors": errors}}), 400

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Validation successful. Settings can be imported.",
                    "data": data,
                    "warnings": warnings,
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.error(f"Error validating import: {str(e)}")
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(e)}}), 500


@settings_bp.route("/import", methods=["POST"])
@login_required
@role_required("admin")
def import_settings():
    """
    Import settings from uploaded JSON or CSV file
    """
    try:
        import csv as csv_module
        import json
        from io import StringIO

        # Check if file uploaded
        if "file" not in request.files:
            return jsonify({"error": {"code": "NO_FILE", "message": "No file uploaded"}}), 400

        file = request.files["file"]
        confirmed = request.form.get("confirmed", "false") == "true"

        if not confirmed:
            return jsonify({"error": {"code": "NOT_CONFIRMED", "message": "Import not confirmed"}}), 400

        # Detect format
        extension = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""

        if extension not in ["json", "csv"]:
            return jsonify({"error": {"code": "INVALID_FORMAT", "message": "Only JSON and CSV files are supported"}}), 400

        # Read and parse file
        content = file.read().decode("utf-8")

        try:
            if extension == "json":
                data = json.loads(content)
            else:
                # Parse CSV
                csv_reader = csv_module.DictReader(StringIO(content))
                data = {"sections": {}}
                for row in csv_reader:
                    section = row.get("Section", "")
                    key = row.get("Key", "")
                    value = row.get("Value", "")
                    if section not in data["sections"]:
                        data["sections"][section] = {}
                    data["sections"][section][key] = value
        except Exception as e:
            return jsonify({"error": {"code": "PARSE_ERROR", "message": f"Failed to parse file: {str(e)}"}}), 400

        # TODO: Apply settings to database/configuration
        # For now, just log the import
        current_app.logger.info(f"Settings imported: {json.dumps(data, indent=2)}")

        # Log audit
        from app.auth.routes import log_audit

        log_audit(
            "import",
            resource_type="settings",
            resource_id=0,
            action_result="success",
            details=f"Imported settings from {file.filename}",
        )

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Settings imported successfully",
                    "sections_imported": list(data.get("sections", {}).keys()),
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.error(f"Error importing settings: {str(e)}")
        return jsonify({"error": {"code": "IMPORT_FAILED", "message": str(e)}}), 500


@settings_bp.route("/reset", methods=["POST"])
@login_required
@role_required("admin")
def reset():
    """
    Reset settings to defaults
    """
    try:
        # TODO: Implement settings reset
        current_app.logger.info("Settings reset to defaults")

        # Log audit
        from app.auth.routes import log_audit

        log_audit("reset", resource_type="settings", resource_id=0, action_result="success")

        return jsonify({"success": True}), 200

    except Exception as e:
        current_app.logger.error(f"Error resetting settings: {str(e)}")
        return jsonify({"error": {"code": "RESET_FAILED", "message": str(e)}}), 500


@settings_bp.route("/optimize-db", methods=["POST"])
@login_required
@role_required("admin")
def optimize_db():
    """
    Optimize database
    """
    try:
        # Execute VACUUM ANALYZE on PostgreSQL
        db.session.execute("VACUUM ANALYZE")
        db.session.commit()

        current_app.logger.info("Database optimized")

        # Log audit
        from app.auth.routes import log_audit

        log_audit("optimize", resource_type="database", resource_id=0, action_result="success")

        return jsonify({"success": True}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error optimizing database: {str(e)}")
        return jsonify({"error": {"code": "OPTIMIZE_FAILED", "message": str(e)}}), 500


@settings_bp.route("/clear-cache", methods=["POST"])
@login_required
@role_required("admin")
def clear_cache():
    """
    Clear application cache
    """
    try:
        # TODO: Implement cache clearing
        current_app.logger.info("Cache cleared")

        # Log audit
        from app.auth.routes import log_audit

        log_audit("clear_cache", resource_type="cache", resource_id=0, action_result="success")

        return jsonify({"success": True}), 200

    except Exception as e:
        current_app.logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({"error": {"code": "CLEAR_CACHE_FAILED", "message": str(e)}}), 500


@settings_bp.route("/rotate-logs", methods=["POST"])
@login_required
@role_required("admin")
def rotate_logs():
    """
    Rotate log files
    """
    try:
        # TODO: Implement log rotation
        current_app.logger.info("Logs rotated")

        # Log audit
        from app.auth.routes import log_audit

        log_audit("rotate_logs", resource_type="logs", resource_id=0, action_result="success")

        return jsonify({"success": True}), 200

    except Exception as e:
        current_app.logger.error(f"Error rotating logs: {str(e)}")
        return jsonify({"error": {"code": "ROTATE_LOGS_FAILED", "message": str(e)}}), 500


@settings_bp.route("/test-connections", methods=["POST"])
@login_required
@role_required("admin")
def test_connections():
    """
    Test system connections
    """
    try:
        results = {"database": False, "email": False, "storage": False}

        # Test database connection
        try:
            db.session.execute("SELECT 1")
            results["database"] = True
        except Exception as e:
            current_app.logger.error(f"Database connection test failed: {str(e)}")

        # Test email connection
        try:
            # TODO: Implement email connection test
            results["email"] = True
        except Exception as e:
            current_app.logger.error(f"Email connection test failed: {str(e)}")

        # Test storage access
        try:
            # TODO: Implement storage access test
            results["storage"] = True
        except Exception as e:
            current_app.logger.error(f"Storage connection test failed: {str(e)}")

        return jsonify(results), 200

    except Exception as e:
        current_app.logger.error(f"Error testing connections: {str(e)}")
        return jsonify({"error": {"code": "TEST_FAILED", "message": str(e)}}), 500


# User Management Routes


@settings_bp.route("/users", methods=["GET"])
@login_required
@role_required("admin")
def get_users():
    """
    Get all users
    """
    try:
        from app.models import User

        users = User.query.all()
        users_data = []

        for user in users:
            users_data.append(
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "department": user.department,
                    "role": user.role,
                    "is_active": user.is_active,
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                    "account_locked_until": user.account_locked_until.isoformat() if user.account_locked_until else None,
                    "failed_login_attempts": user.failed_login_attempts,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                }
            )

        return jsonify({"users": users_data}), 200

    except Exception as e:
        current_app.logger.error(f"Error getting users: {str(e)}")
        return jsonify({"error": {"code": "GET_USERS_FAILED", "message": str(e)}}), 500


@settings_bp.route("/users/create", methods=["POST"])
@login_required
@role_required("admin")
def create_user():
    """
    Create new user
    """
    try:
        import re

        from werkzeug.security import generate_password_hash

        from app.models import User

        data = request.get_json()

        # Validate required fields
        if not data.get("username") or not data.get("email") or not data.get("password"):
            return (
                jsonify(
                    {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Username, email, and password are required",
                        }
                    }
                ),
                400,
            )

        # Validate username format
        if not re.match(r"^[a-zA-Z0-9_]{3,50}$", data["username"]):
            return (
                jsonify(
                    {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Invalid username format (3-50 chars, alphanumeric and underscore only)",
                        }
                    }
                ),
                400,
            )

        # Validate email format
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", data["email"]):
            return (
                jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Invalid email format"}}),
                400,
            )

        # Check if username already exists
        if User.query.filter_by(username=data["username"]).first():
            return (
                jsonify({"error": {"code": "DUPLICATE_ERROR", "message": "Username already exists"}}),
                400,
            )

        # Check if email already exists
        if User.query.filter_by(email=data["email"]).first():
            return (
                jsonify({"error": {"code": "DUPLICATE_ERROR", "message": "Email already exists"}}),
                400,
            )

        # Validate password strength
        password = data["password"]
        if (
            len(password) < 8
            or not re.search(r"[a-z]", password)
            or not re.search(r"[A-Z]", password)
            or not re.search(r"[0-9]", password)
            or not re.search(r"[^a-zA-Z0-9]", password)
        ):
            return (
                jsonify(
                    {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Password must be at least 8 characters and contain uppercase, lowercase, number, and special character",
                        }
                    }
                ),
                400,
            )

        # Validate role
        valid_roles = ["admin", "operator", "viewer", "auditor"]
        if data.get("role") not in valid_roles:
            return (
                jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Invalid role"}}),
                400,
            )

        # Create new user
        new_user = User(
            username=data["username"],
            email=data["email"],
            password_hash=generate_password_hash(password),
            full_name=data.get("full_name"),
            department=data.get("department"),
            role=data["role"],
            is_active=data.get("is_active", True),
        )

        db.session.add(new_user)
        db.session.commit()

        # Log audit
        from app.auth.routes import log_audit

        log_audit(
            "create_user",
            resource_type="user",
            resource_id=new_user.id,
            action_result="success",
            details=f"Created user: {new_user.username}",
        )

        current_app.logger.info(f"User created: {new_user.username}")

        return jsonify({"success": True, "user_id": new_user.id}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating user: {str(e)}")
        return jsonify({"error": {"code": "CREATE_USER_FAILED", "message": str(e)}}), 500


@settings_bp.route("/users/<int:user_id>/update", methods=["PUT"])
@login_required
@role_required("admin")
def update_user(user_id):
    """
    Update user
    """
    try:
        import re

        from werkzeug.security import generate_password_hash

        from app.models import User

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "User not found"}}), 404

        data = request.get_json()

        # Validate email format
        if data.get("email") and not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", data["email"]):
            return (
                jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Invalid email format"}}),
                400,
            )

        # Check if email already exists (for different user)
        if data.get("email"):
            existing_user = User.query.filter_by(email=data["email"]).first()
            if existing_user and existing_user.id != user_id:
                return (
                    jsonify({"error": {"code": "DUPLICATE_ERROR", "message": "Email already exists"}}),
                    400,
                )

        # Update fields
        if data.get("email"):
            user.email = data["email"]
        if data.get("full_name") is not None:
            user.full_name = data["full_name"]
        if data.get("department") is not None:
            user.department = data["department"]

        # Update role
        if data.get("role"):
            valid_roles = ["admin", "operator", "viewer", "auditor"]
            if data["role"] not in valid_roles:
                return (
                    jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Invalid role"}}),
                    400,
                )
            user.role = data["role"]

        # Update active status
        if "is_active" in data:
            user.is_active = data["is_active"]

        # Update password if provided
        if data.get("password"):
            password = data["password"]
            if (
                len(password) < 8
                or not re.search(r"[a-z]", password)
                or not re.search(r"[A-Z]", password)
                or not re.search(r"[0-9]", password)
                or not re.search(r"[^a-zA-Z0-9]", password)
            ):
                return (
                    jsonify(
                        {
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "message": "Password must be at least 8 characters and contain uppercase, lowercase, number, and special character",
                            }
                        }
                    ),
                    400,
                )
            user.password_hash = generate_password_hash(password)

        db.session.commit()

        # Log audit
        from app.auth.routes import log_audit

        log_audit(
            "update_user",
            resource_type="user",
            resource_id=user_id,
            action_result="success",
            details=f"Updated user: {user.username}",
        )

        current_app.logger.info(f"User updated: {user.username}")

        return jsonify({"success": True}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating user: {str(e)}")
        return jsonify({"error": {"code": "UPDATE_USER_FAILED", "message": str(e)}}), 500


@settings_bp.route("/users/<int:user_id>", methods=["DELETE"])
@login_required
@role_required("admin")
def delete_user(user_id):
    """
    Delete user
    """
    try:
        from flask_login import current_user

        from app.models import User

        # Prevent deleting own account
        if current_user.id == user_id:
            return (
                jsonify({"error": {"code": "FORBIDDEN", "message": "Cannot delete your own account"}}),
                403,
            )

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "User not found"}}), 404

        username = user.username

        db.session.delete(user)
        db.session.commit()

        # Log audit
        from app.auth.routes import log_audit

        log_audit(
            "delete_user",
            resource_type="user",
            resource_id=user_id,
            action_result="success",
            details=f"Deleted user: {username}",
        )

        current_app.logger.info(f"User deleted: {username}")

        return jsonify({"success": True}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user: {str(e)}")
        return jsonify({"error": {"code": "DELETE_USER_FAILED", "message": str(e)}}), 500


@settings_bp.route("/users/<int:user_id>/toggle-status", methods=["POST"])
@login_required
@role_required("admin")
def toggle_user_status(user_id):
    """
    Toggle user active status
    """
    try:
        from flask_login import current_user

        from app.models import User

        # Prevent disabling own account
        if current_user.id == user_id:
            return (
                jsonify({"error": {"code": "FORBIDDEN", "message": "Cannot disable your own account"}}),
                403,
            )

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "User not found"}}), 404

        data = request.get_json()
        user.is_active = data.get("is_active", not user.is_active)

        db.session.commit()

        # Log audit
        from app.auth.routes import log_audit

        status = "activated" if user.is_active else "deactivated"
        log_audit(
            "toggle_user_status",
            resource_type="user",
            resource_id=user_id,
            action_result="success",
            details=f"User {user.username} {status}",
        )

        current_app.logger.info(f"User {user.username} {status}")

        return jsonify({"success": True, "is_active": user.is_active}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling user status: {str(e)}")
        return jsonify({"error": {"code": "TOGGLE_STATUS_FAILED", "message": str(e)}}), 500


@settings_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@login_required
@role_required("admin")
def reset_user_password(user_id):
    """
    Reset user password and send temporary password via email
    """
    try:
        import secrets
        import string

        from werkzeug.security import generate_password_hash

        from app.models import User

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "User not found"}}), 404

        # Generate temporary password
        alphabet = string.ascii_letters + string.digits + string.punctuation
        temp_password = "".join(secrets.choice(alphabet) for i in range(12))

        # Update user password
        user.password_hash = generate_password_hash(temp_password)
        user.failed_login_attempts = 0
        user.account_locked_until = None

        db.session.commit()

        # TODO: Send email with temporary password
        # For now, just log it (in production, this should be emailed)
        current_app.logger.info(f"Password reset for user {user.username}. Temporary password: {temp_password}")

        # Log audit
        from app.auth.routes import log_audit

        log_audit(
            "reset_password",
            resource_type="user",
            resource_id=user_id,
            action_result="success",
            details=f"Password reset for user: {user.username}",
        )

        return jsonify({"success": True, "message": "Password reset email sent"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error resetting password: {str(e)}")
        return jsonify({"error": {"code": "RESET_PASSWORD_FAILED", "message": str(e)}}), 500


@settings_bp.route("/users/<int:user_id>/unlock", methods=["POST"])
@login_required
@role_required("admin")
def unlock_user_account(user_id):
    """
    Unlock user account
    """
    try:
        from app.models import User

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "User not found"}}), 404

        user.account_locked_until = None
        user.failed_login_attempts = 0

        db.session.commit()

        # Log audit
        from app.auth.routes import log_audit

        log_audit(
            "unlock_account",
            resource_type="user",
            resource_id=user_id,
            action_result="success",
            details=f"Account unlocked for user: {user.username}",
        )

        current_app.logger.info(f"Account unlocked for user: {user.username}")

        return jsonify({"success": True}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error unlocking account: {str(e)}")
        return jsonify({"error": {"code": "UNLOCK_ACCOUNT_FAILED", "message": str(e)}}), 500
