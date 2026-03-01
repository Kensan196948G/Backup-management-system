"""
Report Management Views
Report viewing, generation, and export
"""

import os
from datetime import datetime

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import login_required
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

from app.auth.decorators import role_required
from app.models import BackupJob, Report, db
from app.services.report_generator import ReportGenerator
from app.views import reports_bp


@reports_bp.route("/")
@login_required
def list():
    """
    Report list page
    Shows all generated reports
    """
    # Get filter parameters
    report_type = request.args.get("type", "")
    period_type = request.args.get("period", "")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    # Build query with eager loading of relationships
    query = Report.query.options(joinedload(Report.generator))

    # Apply filters
    if report_type:
        query = query.filter_by(report_type=report_type)

    if period_type:
        query = query.filter_by(period_type=period_type)

    # Order by (use created_at instead of generated_at as per model)
    query = query.order_by(desc(Report.created_at))

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    reports = pagination.items

    return render_template(
        "reports/list.html", reports=reports, pagination=pagination, filters={"type": report_type, "period": period_type}
    )


@reports_bp.route("/<int:report_id>")
@login_required
def detail(report_id):
    """
    Report detail page
    Shows report metadata and download link
    """
    report = Report.query.get_or_404(report_id)

    return render_template("reports/detail.html", report=report)


@reports_bp.route("/generate", methods=["GET", "POST"])
@login_required
@role_required("admin", "operator", "auditor")
def generate():
    """
    Generate new report
    """
    # Get report type from query parameter
    report_type_param = request.args.get("type", "")

    # Set page title based on type
    page_titles = {
        "periodic": "定期レポート生成",
        "compliance": "コンプライアンスレポート生成",
        "custom": "カスタムレポート生成",
    }
    page_title = page_titles.get(report_type_param, "レポート生成")

    if request.method == "POST":
        try:
            # Get form data
            report_type = request.form.get("report_type")
            request.form.get("period_type")
            start_date_str = request.form.get("start_date")
            end_date_str = request.form.get("end_date")
            format_type = request.form.get("format", "pdf")
            job_id = request.form.get("job_id")

            # Parse dates
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else None
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else None

            # Generate report
            generator = ReportGenerator()

            if report_type == "compliance":
                report = generator.generate_compliance_report(start_date=start_date, end_date=end_date, format=format_type)
            elif report_type == "backup_status":
                report = generator.generate_backup_status_report(start_date=start_date, end_date=end_date, format=format_type)
            elif report_type == "verification":
                report = generator.generate_verification_report(start_date=start_date, end_date=end_date, format=format_type)
            elif report_type == "job_detail" and job_id:
                report = generator.generate_job_detail_report(
                    job_id=int(job_id), start_date=start_date, end_date=end_date, format=format_type
                )
            else:
                flash("無効なレポートタイプです", "danger")
                return redirect(url_for("reports.generate"))

            if report:
                # Log audit
                from app.auth.routes import log_audit

                log_audit("generate", resource_type="report", resource_id=report.id, action_result="success")

                flash(f"レポート「{report.report_name}」を生成しました", "success")
                return redirect(url_for("reports.detail", report_id=report.id))
            else:
                flash("レポートの生成に失敗しました", "danger")

        except Exception as e:
            current_app.logger.error(f"Error generating report: {str(e)}")
            flash(f"レポートの生成に失敗しました: {str(e)}", "danger")

    # Get jobs for job detail report
    jobs = BackupJob.query.filter_by(is_active=True).all()

    # Pass page_title to template
    return render_template("reports/generate.html", page_title=page_title, report_type=report_type_param, jobs=jobs)


@reports_bp.route("/<int:report_id>/download")
@login_required
def download(report_id):
    """
    Download report file
    """
    report = Report.query.get_or_404(report_id)

    try:
        # Check if file exists
        file_path = report.file_path

        if not file_path or not os.path.exists(file_path):
            flash("レポートファイルが見つかりません", "danger")
            return redirect(url_for("reports.detail", report_id=report_id))

        # Determine mimetype
        mimetype = "application/pdf" if report.format == "pdf" else "text/html"
        if report.format == "csv":
            mimetype = "text/csv"
        elif report.format == "json":
            mimetype = "application/json"

        # Send file
        return send_file(file_path, mimetype=mimetype, as_attachment=True, download_name=os.path.basename(file_path))

    except Exception as e:
        current_app.logger.error(f"Error downloading report: {str(e)}")
        flash(f"レポートのダウンロードに失敗しました: {str(e)}", "danger")
        return redirect(url_for("reports.detail", report_id=report_id))


@reports_bp.route("/<int:report_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete(report_id):
    """
    Delete report (admin only)
    """
    report = Report.query.get_or_404(report_id)

    try:
        # Delete file
        if report.file_path and os.path.exists(report.file_path):
            os.remove(report.file_path)

        # Delete record
        db.session.delete(report)
        db.session.commit()

        # Log audit
        from app.auth.routes import log_audit

        log_audit("delete", resource_type="report", resource_id=report_id, action_result="success")

        flash("レポートを削除しました", "success")
        return redirect(url_for("reports.list"))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting report: {str(e)}")
        flash(f"レポートの削除に失敗しました: {str(e)}", "danger")
        return redirect(url_for("reports.detail", report_id=report_id))


@reports_bp.route("/dashboard")
@login_required
def dashboard():
    """
    Reports dashboard
    Shows report statistics and quick actions
    """
    # Get statistics
    total_reports = Report.query.count()

    # Recent reports
    recent_reports = Report.query.order_by(desc(Report.generated_at)).limit(10).all()

    # Reports by type
    compliance_count = Report.query.filter_by(report_type="compliance").count()
    backup_status_count = Report.query.filter_by(report_type="backup_status").count()
    verification_count = Report.query.filter_by(report_type="verification").count()
    job_detail_count = Report.query.filter_by(report_type="job_detail").count()

    return render_template(
        "reports/dashboard.html",
        total_reports=total_reports,
        recent_reports=recent_reports,
        compliance_count=compliance_count,
        backup_status_count=backup_status_count,
        verification_count=verification_count,
        job_detail_count=job_detail_count,
    )


# API Endpoints


@reports_bp.route("/api/reports")
@login_required
def api_list():
    """
    API endpoint for report list
    """
    try:
        reports = Report.query.order_by(desc(Report.generated_at)).limit(100).all()

        return jsonify({"reports": [report.to_dict() for report in reports]}), 200

    except Exception as e:
        current_app.logger.error(f"Error getting reports: {str(e)}")
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@reports_bp.route("/api/reports/<int:report_id>")
@login_required
def api_detail(report_id):
    """
    API endpoint for report detail
    """
    try:
        report = Report.query.get_or_404(report_id)
        return jsonify({"report": report.to_dict()}), 200

    except Exception as e:
        current_app.logger.error(f"Error getting report detail: {str(e)}")
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@reports_bp.route("/api/reports/generate", methods=["POST"])
@login_required
@role_required("admin", "operator", "auditor")
def api_generate():
    """
    API endpoint for report generation
    """
    try:
        data = request.get_json()

        if not data or "report_type" not in data:
            return jsonify({"error": {"code": "INVALID_REQUEST", "message": "report_type is required"}}), 400

        report_type = data["report_type"]
        data.get("period_type", "custom")
        start_date_str = data.get("start_date")
        end_date_str = data.get("end_date")
        format_type = data.get("format", "pdf")
        job_id = data.get("job_id")

        # Parse dates
        start_date = datetime.fromisoformat(start_date_str) if start_date_str else None
        end_date = datetime.fromisoformat(end_date_str) if end_date_str else None

        # Generate report
        generator = ReportGenerator()

        if report_type == "compliance":
            report = generator.generate_compliance_report(start_date=start_date, end_date=end_date, format=format_type)
        elif report_type == "backup_status":
            report = generator.generate_backup_status_report(start_date=start_date, end_date=end_date, format=format_type)
        elif report_type == "verification":
            report = generator.generate_verification_report(start_date=start_date, end_date=end_date, format=format_type)
        elif report_type == "job_detail" and job_id:
            report = generator.generate_job_detail_report(
                job_id=job_id, start_date=start_date, end_date=end_date, format=format_type
            )
        else:
            return (
                jsonify({"error": {"code": "INVALID_REPORT_TYPE", "message": "Invalid report type or missing parameters"}}),
                400,
            )

        if report:
            # Log audit
            from app.auth.routes import log_audit

            log_audit("generate", resource_type="report", resource_id=report.id, action_result="success")

            return jsonify({"report": report.to_dict()}), 201
        else:
            return jsonify({"error": {"code": "REPORT_GENERATION_FAILED", "message": "Failed to generate report"}}), 500

    except Exception as e:
        current_app.logger.error(f"Error generating report via API: {str(e)}")
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500
