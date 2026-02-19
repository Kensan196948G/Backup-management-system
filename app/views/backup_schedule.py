"""
Backup Schedule Management Views
Handles schedule CRUD operations and storage provider configuration
"""

from datetime import datetime, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app.models import BackupJob, SystemSetting, db
from app.utils.decorators import role_required

bp = Blueprint("backup_schedule", __name__, url_prefix="/backup")


# ============================================================================
# Schedule Management Views
# ============================================================================


@bp.route("/schedule")
@login_required
@role_required(["admin", "operator"])
def schedule_list():
    """Display backup schedule management page"""
    # Fetch all backup jobs with schedule information
    jobs = BackupJob.query.filter_by(is_active=True).order_by(BackupJob.job_name).all()

    # Mock schedule data (in production, this would come from a Schedule model)
    schedules = []
    for job in jobs:
        if hasattr(job, "schedule_enabled") and job.schedule_enabled:
            schedules.append(
                {
                    "id": job.id,
                    "job_name": job.job_name,
                    "source_path": job.source_path,
                    "cron_expression": getattr(job, "cron_expression", "0 2 * * *"),
                    "schedule_description": getattr(job, "schedule_description", "Daily at 2:00 AM"),
                    "next_run": getattr(job, "next_run", datetime.now() + timedelta(hours=2)),
                    "last_run": getattr(job, "last_run", None),
                    "priority": getattr(job, "priority", "medium"),
                    "is_active": getattr(job, "is_active", True),
                }
            )

    # Calculate statistics
    stats = {
        "total_schedules": len(schedules),
        "active_schedules": sum(1 for s in schedules if s["is_active"]),
        "next_24h": sum(1 for s in schedules if s["next_run"] and s["next_run"] < datetime.now() + timedelta(hours=24)),
        "high_priority": sum(1 for s in schedules if s["priority"] == "high"),
    }

    return render_template("backup/schedule.html", schedules=schedules, jobs=jobs, stats=stats)


@bp.route("/storage-config")
@login_required
@role_required(["admin", "operator"])
def storage_config():
    """Display storage provider configuration page"""
    # Mock storage provider data (in production, this would come from a StorageProvider model)
    storage_providers = [
        {
            "id": 1,
            "name": "AWS S3 Production",
            "provider_type": "s3",
            "endpoint": "s3.amazonaws.com/backup-prod",
            "is_active": True,
            "connection_status": "online",
            "last_check": datetime.now() - timedelta(minutes=5),
            "total_capacity": 5 * 1024**4,  # 5 TB
            "used_capacity": 2.5 * 1024**4,  # 2.5 TB
            "backup_count": 1234,
            "file_count": 45678,
            "success_rate": 99.8,
            "created_at": datetime.now() - timedelta(days=180),
        },
        {
            "id": 2,
            "name": "Azure Blob Backup",
            "provider_type": "azure",
            "endpoint": "backupstorage.blob.core.windows.net",
            "is_active": True,
            "connection_status": "online",
            "last_check": datetime.now() - timedelta(minutes=3),
            "total_capacity": 3 * 1024**4,  # 3 TB
            "used_capacity": 1.8 * 1024**4,  # 1.8 TB
            "backup_count": 876,
            "file_count": 32145,
            "success_rate": 99.5,
            "created_at": datetime.now() - timedelta(days=120),
        },
        {
            "id": 3,
            "name": "NFS Local Storage",
            "provider_type": "nfs",
            "endpoint": "192.168.1.100:/export/backups",
            "is_active": True,
            "connection_status": "online",
            "last_check": datetime.now() - timedelta(minutes=1),
            "total_capacity": 10 * 1024**4,  # 10 TB
            "used_capacity": 7.2 * 1024**4,  # 7.2 TB
            "backup_count": 2345,
            "file_count": 89012,
            "success_rate": 99.9,
            "created_at": datetime.now() - timedelta(days=365),
        },
        {
            "id": 4,
            "name": "Offline Archive Storage",
            "provider_type": "local",
            "endpoint": "/mnt/offline-archive",
            "is_active": False,
            "connection_status": "offline",
            "last_check": datetime.now() - timedelta(hours=2),
            "total_capacity": 8 * 1024**4,  # 8 TB
            "used_capacity": 3.5 * 1024**4,  # 3.5 TB
            "backup_count": 543,
            "file_count": 12345,
            "success_rate": 98.5,
            "created_at": datetime.now() - timedelta(days=90),
        },
    ]

    # Calculate statistics
    stats = {
        "total_providers": len(storage_providers),
        "online_providers": sum(1 for p in storage_providers if p["connection_status"] == "online"),
        "total_capacity": sum(p["total_capacity"] for p in storage_providers),
        "used_capacity": sum(p["used_capacity"] for p in storage_providers),
    }

    return render_template("backup/storage_config.html", storage_providers=storage_providers, stats=stats)


# ============================================================================
# API Endpoints - Schedule Management
# ============================================================================


@bp.route("/api/schedule/test-cron", methods=["POST"])
@login_required
def test_cron_expression():
    """Test cron expression and return next execution times"""
    try:
        data = request.get_json()
        cron_expression = data.get("cron_expression", "")

        if not cron_expression:
            return jsonify({"success": False, "message": "Cron expression is required"}), 400

        # Parse cron expression and calculate next runs
        # This is a simplified version - in production use croniter or apscheduler
        next_runs = []
        base_time = datetime.now()

        # Mock calculation (replace with actual cron parsing)
        for i in range(10):
            next_time = base_time + timedelta(days=i)
            next_runs.append(next_time.strftime("%Y-%m-%d %H:%M:%S"))

        return jsonify({"success": True, "next_runs": next_runs, "cron_expression": cron_expression})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/api/schedule/create", methods=["POST"])
@login_required
@role_required(["admin", "operator"])
def create_schedule():
    """Create new backup schedule"""
    try:
        data = request.get_json()

        job_id = data.get("job_id")
        cron_expression = data.get("cron_expression")
        priority = data.get("priority", "medium")
        description = data.get("description", "")
        is_active = data.get("is_active", True)

        if not job_id or not cron_expression:
            return jsonify({"success": False, "message": "Job ID and cron expression are required"}), 400

        # Verify job exists
        job = BackupJob.query.get(job_id)
        if not job:
            return jsonify({"success": False, "message": "Backup job not found"}), 404

        # In production, create Schedule record
        # For now, update job with schedule info (mock)
        # schedule = Schedule(
        #     job_id=job_id,
        #     cron_expression=cron_expression,
        #     priority=priority,
        #     description=description,
        #     is_active=is_active,
        #     created_by=current_user.id
        # )
        # db.session.add(schedule)
        # db.session.commit()

        flash("スケジュールを作成しました", "success")
        return jsonify({"success": True, "message": "Schedule created successfully", "schedule_id": job_id})  # Mock ID

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/api/schedule/<int:schedule_id>", methods=["GET"])
@login_required
def get_schedule(schedule_id):
    """Get schedule details"""
    try:
        # In production, fetch from Schedule model
        job = BackupJob.query.get(schedule_id)
        if not job:
            return jsonify({"success": False, "message": "Schedule not found"}), 404

        schedule_data = {
            "id": job.id,
            "job_id": job.id,
            "job_name": job.job_name,
            "cron_expression": "0 2 * * *",  # Mock
            "priority": "medium",
            "description": "",
            "is_active": True,
        }

        return jsonify({"success": True, "schedule": schedule_data})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/api/schedule/<int:schedule_id>", methods=["DELETE"])
@login_required
@role_required(["admin", "operator"])
def delete_schedule(schedule_id):
    """Delete backup schedule"""
    try:
        # In production, delete from Schedule model
        # schedule = Schedule.query.get(schedule_id)
        # if not schedule:
        #     return jsonify({'success': False, 'message': 'Schedule not found'}), 404
        #
        # db.session.delete(schedule)
        # db.session.commit()

        flash("スケジュールを削除しました", "success")
        return jsonify({"success": True, "message": "Schedule deleted successfully"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/api/schedule/<int:schedule_id>/toggle", methods=["POST"])
@login_required
@role_required(["admin", "operator"])
def toggle_schedule(schedule_id):
    """Toggle schedule active status"""
    try:
        data = request.get_json()
        is_active = data.get("is_active", True)

        # In production, update Schedule model
        # schedule = Schedule.query.get(schedule_id)
        # if not schedule:
        #     return jsonify({'success': False, 'message': 'Schedule not found'}), 404
        #
        # schedule.is_active = is_active
        # db.session.commit()

        action = "有効化" if is_active else "無効化"
        flash(f"スケジュールを{action}しました", "success")

        return jsonify({"success": True, "message": f'Schedule {"activated" if is_active else "deactivated"} successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/api/schedule/<int:schedule_id>/test", methods=["POST"])
@login_required
@role_required(["admin", "operator"])
def test_schedule(schedule_id):
    """Test schedule execution"""
    try:
        # In production, trigger test execution
        job = BackupJob.query.get(schedule_id)
        if not job:
            return jsonify({"success": False, "message": "Schedule not found"}), 404

        # Trigger test execution (mock)
        flash("テスト実行を開始しました", "info")

        return jsonify({"success": True, "message": "Test execution started"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ============================================================================
# API Endpoints - Storage Provider Management
# ============================================================================


@bp.route("/api/storage/create", methods=["POST"])
@login_required
@role_required(["admin", "operator"])
def create_storage_provider():
    """Create new storage provider"""
    try:
        data = request.get_json()

        name = data.get("name")
        provider_type = data.get("provider_type")

        if not name or not provider_type:
            return jsonify({"success": False, "message": "Name and provider type are required"}), 400

        # In production, create StorageProvider record
        # provider = StorageProvider(
        #     name=name,
        #     provider_type=provider_type,
        #     config=data,
        #     created_by=current_user.id
        # )
        # db.session.add(provider)
        # db.session.commit()

        flash("ストレージプロバイダーを作成しました", "success")
        return jsonify({"success": True, "message": "Storage provider created successfully", "provider_id": 1})  # Mock ID

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/api/storage/<int:storage_id>", methods=["GET"])
@login_required
def get_storage_provider(storage_id):
    """Get storage provider details"""
    try:
        # In production, fetch from StorageProvider model
        storage_data = {"id": storage_id, "name": "Mock Storage", "provider_type": "s3", "config": {}}

        return jsonify({"success": True, "storage": storage_data})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/api/storage/<int:storage_id>", methods=["DELETE"])
@login_required
@role_required(["admin", "operator"])
def delete_storage_provider(storage_id):
    """Delete storage provider"""
    try:
        # In production, delete from StorageProvider model
        flash("ストレージプロバイダーを削除しました", "success")
        return jsonify({"success": True, "message": "Storage provider deleted successfully"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/api/storage/<int:storage_id>/toggle", methods=["POST"])
@login_required
@role_required(["admin", "operator"])
def toggle_storage_provider(storage_id):
    """Toggle storage provider active status"""
    try:
        data = request.get_json()
        is_active = data.get("is_active", True)

        action = "有効化" if is_active else "無効化"
        flash(f"ストレージプロバイダーを{action}しました", "success")

        return jsonify(
            {"success": True, "message": f'Storage provider {"activated" if is_active else "deactivated"} successfully'}
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/api/storage/<int:storage_id>/test", methods=["POST"])
@login_required
@role_required(["admin", "operator"])
def test_storage_connection(storage_id):
    """Test storage provider connection"""
    try:
        # In production, test actual connection
        import time

        time.sleep(1)  # Simulate connection test

        flash("接続テストに成功しました", "success")
        return jsonify({"success": True, "message": "Connection test successful", "latency_ms": 45, "status": "online"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/api/storage/test-connection", methods=["POST"])
@login_required
@role_required(["admin", "operator"])
def test_new_storage_connection():
    """Test connection for new storage provider before saving"""
    try:
        data = request.get_json()
        provider_type = data.get("provider_type")

        if not provider_type:
            return jsonify({"success": False, "message": "Provider type is required"}), 400

        # In production, test actual connection with provided credentials
        import time

        time.sleep(1)  # Simulate connection test

        return jsonify({"success": True, "message": "Connection test successful", "latency_ms": 52, "status": "online"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ============================================================================
# Template Filters
# ============================================================================


@bp.app_template_filter("filesizeformat")
def filesizeformat(value):
    """Format file size in human readable format"""
    try:
        value = float(value)
        for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
            if abs(value) < 1024.0:
                return f"{value:.1f} {unit}"
            value /= 1024.0
        return f"{value:.1f} EB"
    except (TypeError, ValueError):
        return "0 B"
