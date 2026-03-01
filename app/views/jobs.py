"""
Backup Job Views
Job list, detail, create, edit, and delete views
"""

from datetime import datetime, timezone

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import desc, or_

from app.auth.decorators import role_required
from app.models import (
    Alert,
    BackupCopy,
    BackupExecution,
    BackupJob,
    ComplianceStatus,
    VerificationTest,
    db,
)
from app.services.compliance_checker import ComplianceChecker
from app.views import jobs_bp


@jobs_bp.route("/")
@login_required
def list():
    """
    Backup job list page with search, filter, and pagination
    """
    # Get filter parameters
    search = request.args.get("search", "")
    job_type = request.args.get("type", "")
    owner_id = request.args.get("owner", "")
    status = request.args.get("status", "")
    compliance = request.args.get("compliance", "")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    # Build query
    query = BackupJob.query

    # Apply filters
    if search:
        query = query.filter(
            or_(
                BackupJob.job_name.ilike(f"%{search}%"),
                BackupJob.target_server.ilike(f"%{search}%"),
                BackupJob.description.ilike(f"%{search}%"),
            )
        )

    if job_type:
        query = query.filter_by(job_type=job_type)

    if owner_id:
        query = query.filter_by(owner_id=owner_id)

    if status == "active":
        query = query.filter_by(is_active=True)
    elif status == "inactive":
        query = query.filter_by(is_active=False)

    # Join with compliance status for compliance filter
    if compliance == "compliant":
        query = query.join(ComplianceStatus).filter(ComplianceStatus.overall_status == "compliant")
    elif compliance == "non_compliant":
        query = query.join(ComplianceStatus).filter(ComplianceStatus.overall_status == "non_compliant")

    # Order by
    sort_by = request.args.get("sort", "updated_at")
    sort_order = request.args.get("order", "desc")

    if sort_order == "desc":
        query = query.order_by(desc(getattr(BackupJob, sort_by, BackupJob.updated_at)))
    else:
        query = query.order_by(getattr(BackupJob, sort_by, BackupJob.updated_at))

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    jobs = pagination.items

    # Get owners for filter dropdown
    from app.models import User

    owners = User.query.filter_by(is_active=True).all()

    return render_template(
        "jobs/list.html",
        jobs=jobs,
        pagination=pagination,
        owners=owners,
        filters={
            "search": search,
            "type": job_type,
            "owner": owner_id,
            "status": status,
            "compliance": compliance,
            "sort": sort_by,
            "order": sort_order,
        },
    )


@jobs_bp.route("/<int:job_id>")
@login_required
def detail(job_id):
    """
    Backup job detail page
    Shows job information, compliance status, execution history, and verification tests
    """
    job = BackupJob.query.get_or_404(job_id)

    # Get compliance status
    compliance = ComplianceStatus.query.filter_by(job_id=job_id).first()

    if not compliance:
        # Generate compliance status if not exists
        checker = ComplianceChecker()
        compliance = checker.check_job_compliance(job_id)

    # Get backup copies
    copies = BackupCopy.query.filter_by(job_id=job_id).all()

    # Get recent executions
    executions = BackupExecution.query.filter_by(job_id=job_id).order_by(BackupExecution.execution_date.desc()).limit(20).all()

    # Get recent verification tests
    verifications = VerificationTest.query.filter_by(job_id=job_id).order_by(VerificationTest.test_date.desc()).limit(10).all()

    # Get related alerts
    alerts = (
        Alert.query.filter_by(resource_type="backup_job", resource_id=job_id, is_acknowledged=False)
        .order_by(Alert.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "jobs/detail.html",
        job=job,
        compliance=compliance,
        copies=copies,
        executions=executions,
        verifications=verifications,
        alerts=alerts,
    )


@jobs_bp.route("/create", methods=["GET", "POST"])
@login_required
@role_required("admin", "operator")
def create():
    """
    Create new backup job
    """
    if request.method == "POST":
        try:
            # Get form data
            job_data = {
                "job_name": request.form.get("job_name"),
                "job_type": request.form.get("job_type"),
                "description": request.form.get("description"),
                "target_server": request.form.get("target_server"),
                "target_path": request.form.get("destination_path") or request.form.get("target_path"),
                "backup_tool": request.form.get("backup_tool"),
                "schedule_type": request.form.get("schedule_type", "daily"),
                "retention_days": int(request.form.get("retention_days", 30)),
                "is_active": request.form.get("is_active") == "on",
                "owner_id": current_user.id,
            }

            # Create backup job
            job = BackupJob(**job_data)
            db.session.add(job)
            db.session.commit()

            # Log audit
            from app.auth.routes import log_audit

            log_audit("create", resource_type="backup_job", resource_id=job.id, action_result="success")

            flash(f"バックアップジョブ「{job.job_name}」を作成しました", "success")
            return redirect(url_for("jobs.detail", job_id=job.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating backup job: {str(e)}")
            flash(f"バックアップジョブの作成に失敗しました: {str(e)}", "danger")

    return render_template("jobs/create.html")


@jobs_bp.route("/<int:job_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin", "operator")
def edit(job_id):
    """
    Edit backup job
    """
    job = BackupJob.query.get_or_404(job_id)

    if request.method == "POST":
        try:
            # Update job data
            job.job_name = request.form.get("job_name")
            job.job_type = request.form.get("job_type")
            job.description = request.form.get("description")
            job.target_server = request.form.get("target_server")
            job.target_path = request.form.get("target_path")
            job.backup_tool = request.form.get("backup_tool")
            job.schedule_type = request.form.get("schedule_type")
            job.schedule_time = request.form.get("schedule_time")
            job.retention_days = int(request.form.get("retention_days", 30))
            job.is_active = request.form.get("is_active") == "on"
            job.updated_at = datetime.now(timezone.utc)

            db.session.commit()

            # Re-check compliance
            checker = ComplianceChecker()
            checker.check_job_compliance(job_id)

            # Log audit
            from app.auth.routes import log_audit

            log_audit("update", resource_type="backup_job", resource_id=job.id, action_result="success")

            flash(f"バックアップジョブ「{job.job_name}」を更新しました", "success")
            return redirect(url_for("jobs.detail", job_id=job.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating backup job: {str(e)}")
            flash(f"バックアップジョブの更新に失敗しました: {str(e)}", "danger")

    return render_template("jobs/edit.html", job=job)


@jobs_bp.route("/<int:job_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete(job_id):
    """
    Delete backup job (admin only)
    """
    job = BackupJob.query.get_or_404(job_id)

    try:
        job_name = job.job_name

        # Delete related records
        BackupCopy.query.filter_by(job_id=job_id).delete()
        BackupExecution.query.filter_by(job_id=job_id).delete()
        ComplianceStatus.query.filter_by(job_id=job_id).delete()
        VerificationTest.query.filter_by(job_id=job_id).delete()

        # Delete job
        db.session.delete(job)
        db.session.commit()

        # Log audit
        from app.auth.routes import log_audit

        log_audit("delete", resource_type="backup_job", resource_id=job_id, action_result="success")

        flash(f"バックアップジョブ「{job_name}」を削除しました", "success")
        return redirect(url_for("jobs.list"))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting backup job: {str(e)}")
        flash(f"バックアップジョブの削除に失敗しました: {str(e)}", "danger")
        return redirect(url_for("jobs.detail", job_id=job_id))


@jobs_bp.route("/<int:job_id>/toggle-active", methods=["POST"])
@login_required
@role_required("admin", "operator")
def toggle_active(job_id):
    """
    Toggle job active status
    """
    job = BackupJob.query.get_or_404(job_id)

    try:
        job.is_active = not job.is_active
        job.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        status = "有効" if job.is_active else "無効"
        flash(f"バックアップジョブ「{job.job_name}」を{status}にしました", "success")

        # Log audit
        from app.auth.routes import log_audit

        log_audit(
            "update",
            resource_type="backup_job",
            resource_id=job.id,
            action_result="success",
            details=f"Toggled active status to {job.is_active}",
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling job status: {str(e)}")
        flash(f"ステータスの変更に失敗しました: {str(e)}", "danger")

    return redirect(url_for("jobs.detail", job_id=job_id))


@jobs_bp.route("/<int:job_id>/check-compliance", methods=["POST"])
@login_required
def check_compliance(job_id):
    """
    Manually trigger compliance check for a job
    """
    BackupJob.query.get_or_404(job_id)

    try:
        checker = ComplianceChecker()
        compliance = checker.check_job_compliance(job_id)

        status = (
            "準拠"
            if compliance.overall_status == "compliant"
            else ("警告" if compliance.overall_status == "warning" else "非準拠")
        )
        flash(f"コンプライアンスチェックを実行しました: {status}", "success")

    except Exception as e:
        current_app.logger.error(f"Error checking compliance: {str(e)}")
        flash(f"コンプライアンスチェックに失敗しました: {str(e)}", "danger")

    return redirect(url_for("jobs.detail", job_id=job_id))


# API Endpoints


@jobs_bp.route("/api/jobs")
@login_required
def api_list():
    """
    API endpoint for job list
    Returns JSON array of jobs
    """
    try:
        jobs = BackupJob.query.all()
        return jsonify({"jobs": [job.to_dict() for job in jobs]}), 200

    except Exception as e:
        current_app.logger.error(f"Error getting jobs: {str(e)}")
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@jobs_bp.route("/api/jobs/<int:job_id>")
@login_required
def api_detail(job_id):
    """
    API endpoint for job detail
    Returns JSON object with job details
    """
    try:
        job = BackupJob.query.get_or_404(job_id)
        compliance = ComplianceStatus.query.filter_by(job_id=job_id).first()

        return jsonify({"job": job.to_dict(), "compliance": compliance.to_dict() if compliance else None}), 200

    except Exception as e:
        current_app.logger.error(f"Error getting job detail: {str(e)}")
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@jobs_bp.route("/api/jobs/<int:job_id>/executions")
@login_required
def api_executions(job_id):
    """
    API endpoint for job execution history
    Returns JSON array of executions
    """
    try:
        executions = (
            BackupExecution.query.filter_by(job_id=job_id).order_by(BackupExecution.execution_date.desc()).limit(50).all()
        )

        return jsonify({"executions": [exec.to_dict() for exec in executions]}), 200

    except Exception as e:
        current_app.logger.error(f"Error getting executions: {str(e)}")
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500
