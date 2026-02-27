"""
Verification Test Management Views
Test execution, scheduling, and history
"""

from datetime import datetime, timedelta

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
from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import joinedload

from app.auth.decorators import role_required
from app.models import BackupJob, VerificationSchedule, VerificationTest, db
from app.views import verification_bp


@verification_bp.route("/")
@login_required
def list():
    """
    Verification test list page
    Shows all verification tests with results
    """
    # Get filter parameters
    search = request.args.get("search", "")
    result = request.args.get("result", "")
    test_type = request.args.get("type", "")
    job_id = request.args.get("job", "")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    # Build query with eager loading of relationships
    query = VerificationTest.query.options(joinedload(VerificationTest.job), joinedload(VerificationTest.tester))

    # Apply filters
    if search:
        query = query.join(BackupJob).filter(
            or_(BackupJob.job_name.ilike(f"%{search}%"), VerificationTest.notes.ilike(f"%{search}%"))
        )

    if result:
        query = query.filter_by(test_result=result)

    if test_type:
        query = query.filter_by(test_type=test_type)

    if job_id:
        query = query.filter_by(job_id=job_id)

    # Order by
    query = query.order_by(desc(VerificationTest.test_date))

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    tests = pagination.items

    # Get jobs for filter dropdown
    jobs = BackupJob.query.filter_by(is_active=True).all()

    # Calculate test statistics
    total_tests = VerificationTest.query.count()
    passed_tests = VerificationTest.query.filter_by(test_result="success").count()
    failed_tests = VerificationTest.query.filter_by(test_result="failed").count()
    success_rate = round((passed_tests / total_tests * 100) if total_tests > 0 else 0, 1)

    test_stats = {
        "total": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "success_rate": success_rate,
    }

    return render_template(
        "verification/list.html",
        tests=tests,
        pagination=pagination,
        jobs=jobs,
        test_stats=test_stats,
        filters={"search": search, "result": result, "type": test_type, "job": job_id},
    )


@verification_bp.route("/<int:test_id>")
@login_required
def detail(test_id):
    """
    Verification test detail page
    Shows test information and results
    """
    test = VerificationTest.query.get_or_404(test_id)

    # Get related backup job
    job = db.session.get(BackupJob, test.job_id) if test.job_id else None

    return render_template("verification/detail.html", test=test, job=job)


@verification_bp.route("/execute", methods=["GET", "POST"])
@login_required
@role_required("admin", "operator")
def execute():
    """
    Execute verification test
    """
    if request.method == "POST":
        try:
            # Get form data
            test_data = {
                "job_id": request.form.get("job_id"),
                "test_type": request.form.get("test_type"),
                "test_date": datetime.utcnow(),
                "result": request.form.get("result", "pending"),
                "notes": request.form.get("notes"),
                "tested_by_id": current_user.id,
            }

            # Create test record
            test = VerificationTest(**test_data)
            db.session.add(test)
            db.session.commit()

            # Log audit
            from app.auth.routes import log_audit

            log_audit("execute", resource_type="verification_test", resource_id=test.id, action_result="success")

            flash("検証テストを実行しました", "success")
            return redirect(url_for("verification.detail", test_id=test.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error executing verification test: {str(e)}")
            flash(f"検証テストの実行に失敗しました: {str(e)}", "danger")

    # Get jobs for dropdown
    jobs = BackupJob.query.filter_by(is_active=True).all()

    return render_template("verification/create.html", jobs=jobs)


@verification_bp.route("/<int:test_id>/update", methods=["GET", "POST"])
@login_required
@role_required("admin", "operator")
def update(test_id):
    """
    Update verification test result
    """
    test = VerificationTest.query.get_or_404(test_id)

    if request.method == "POST":
        try:
            # Update test data
            test.result = request.form.get("result")
            test.notes = request.form.get("notes")
            test.updated_at = datetime.utcnow()

            db.session.commit()

            # Log audit
            from app.auth.routes import log_audit

            log_audit("update", resource_type="verification_test", resource_id=test.id, action_result="success")

            flash("検証テストを更新しました", "success")
            return redirect(url_for("verification.detail", test_id=test.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating verification test: {str(e)}")
            flash(f"検証テストの更新に失敗しました: {str(e)}", "danger")

    # Get job for display
    job = db.session.get(BackupJob, test.job_id) if test.job_id else None

    return render_template("verification/update.html", test=test, job=job)


@verification_bp.route("/schedule")
@login_required
def schedule():
    """
    Verification test schedule page
    Shows upcoming scheduled tests
    """
    # Get upcoming schedules (next 30 days)
    end_date = datetime.utcnow() + timedelta(days=30)

    schedules = (
        VerificationSchedule.query.filter(VerificationSchedule.next_test_date <= end_date)
        .order_by(VerificationSchedule.next_test_date.asc())
        .all()
    )

    return render_template("verification/schedule.html", schedules=schedules)


@verification_bp.route("/schedule/create", methods=["GET", "POST"])
@login_required
@role_required("admin", "operator")
def create_schedule():
    """
    Create verification test schedule
    """
    if request.method == "POST":
        try:
            # Get form data
            schedule_data = {
                "job_id": request.form.get("job_id"),
                "test_type": request.form.get("test_type"),
                "frequency_days": int(request.form.get("frequency_days", 30)),
                "next_test_date": (
                    datetime.strptime(request.form.get("next_test_date"), "%Y-%m-%d")
                    if request.form.get("next_test_date")
                    else datetime.utcnow()
                ),
                "assigned_to_id": request.form.get("assigned_to_id") or current_user.id,
                "is_active": request.form.get("is_active") == "on",
            }

            # Create schedule
            schedule = VerificationSchedule(**schedule_data)
            db.session.add(schedule)
            db.session.commit()

            # Log audit
            from app.auth.routes import log_audit

            log_audit("create", resource_type="verification_schedule", resource_id=schedule.id, action_result="success")

            flash("検証テストスケジュールを作成しました", "success")
            return redirect(url_for("verification.schedule"))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating schedule: {str(e)}")
            flash(f"スケジュールの作成に失敗しました: {str(e)}", "danger")

    # Get jobs and users for dropdowns
    jobs = BackupJob.query.filter_by(is_active=True).all()
    from app.models import User

    users = User.query.filter_by(is_active=True).all()

    return render_template("verification/create_schedule.html", jobs=jobs, users=users)


@verification_bp.route("/schedule/<int:schedule_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin", "operator")
def edit_schedule(schedule_id):
    """
    Edit verification test schedule
    """
    schedule = VerificationSchedule.query.get_or_404(schedule_id)

    if request.method == "POST":
        try:
            # Update schedule data
            schedule.job_id = request.form.get("job_id")
            schedule.test_type = request.form.get("test_type")
            schedule.frequency_days = int(request.form.get("frequency_days", 30))
            schedule.next_test_date = (
                datetime.strptime(request.form.get("next_test_date"), "%Y-%m-%d")
                if request.form.get("next_test_date")
                else schedule.next_test_date
            )
            schedule.assigned_to_id = request.form.get("assigned_to_id") or current_user.id
            schedule.is_active = request.form.get("is_active") == "on"
            schedule.updated_at = datetime.utcnow()

            db.session.commit()

            # Log audit
            from app.auth.routes import log_audit

            log_audit("update", resource_type="verification_schedule", resource_id=schedule.id, action_result="success")

            flash("検証テストスケジュールを更新しました", "success")
            return redirect(url_for("verification.schedule"))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating schedule: {str(e)}")
            flash(f"スケジュールの更新に失敗しました: {str(e)}", "danger")

    # Get jobs and users for dropdowns
    jobs = BackupJob.query.filter_by(is_active=True).all()
    from app.models import User

    users = User.query.filter_by(is_active=True).all()

    return render_template("verification/edit_schedule.html", schedule=schedule, jobs=jobs, users=users)


@verification_bp.route("/schedule/<int:schedule_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_schedule(schedule_id):
    """
    Delete verification test schedule
    """
    schedule = VerificationSchedule.query.get_or_404(schedule_id)

    try:
        db.session.delete(schedule)
        db.session.commit()

        # Log audit
        from app.auth.routes import log_audit

        log_audit("delete", resource_type="verification_schedule", resource_id=schedule_id, action_result="success")

        flash("検証テストスケジュールを削除しました", "success")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting schedule: {str(e)}")
        flash(f"スケジュールの削除に失敗しました: {str(e)}", "danger")

    return redirect(url_for("verification.schedule"))


# API Endpoints


@verification_bp.route("/api/tests")
@login_required
def api_list():
    """
    API endpoint for verification test list
    """
    try:
        tests = VerificationTest.query.order_by(desc(VerificationTest.test_date)).limit(100).all()

        return jsonify({"tests": [test.to_dict() for test in tests]}), 200

    except Exception as e:
        current_app.logger.error(f"Error getting tests: {str(e)}")
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@verification_bp.route("/api/tests/<int:test_id>")
@login_required
def api_detail(test_id):
    """
    API endpoint for verification test detail
    """
    try:
        test = VerificationTest.query.get_or_404(test_id)
        return jsonify({"test": test.to_dict()}), 200

    except Exception as e:
        current_app.logger.error(f"Error getting test detail: {str(e)}")
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@verification_bp.route("/api/schedule")
@login_required
def api_schedule():
    """
    API endpoint for verification schedule
    """
    try:
        schedules = (
            VerificationSchedule.query.filter_by(is_active=True).order_by(VerificationSchedule.next_test_date.asc()).all()
        )

        return jsonify({"schedules": [schedule.to_dict() for schedule in schedules]}), 200

    except Exception as e:
        current_app.logger.error(f"Error getting schedules: {str(e)}")
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500
