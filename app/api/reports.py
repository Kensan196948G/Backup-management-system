"""
Reports API
Generate and retrieve backup reports
"""

import logging
import os
from datetime import date, datetime

from flask import jsonify, request, send_file

from app.api import api_bp
from app.api.errors import error_response, validation_error_response
from app.auth.decorators import api_token_required, role_required
from app.models import Report, User, db
from app.services.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


def validate_date_range(date_from, date_to):
    """
    Validate date range

    Args:
        date_from: Start date string (YYYY-MM-DD)
        date_to: End date string (YYYY-MM-DD)

    Returns:
        Tuple of (date_from, date_to, errors)
    """
    errors = {}

    try:
        date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        errors["date_from"] = "Invalid date format. Use YYYY-MM-DD"
        date_from_obj = None

    try:
        date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        errors["date_to"] = "Invalid date format. Use YYYY-MM-DD"
        date_to_obj = None

    if date_from_obj and date_to_obj:
        if date_from_obj > date_to_obj:
            errors["date_range"] = "date_from must be before date_to"

    return date_from_obj, date_to_obj, errors


@api_bp.route("/reports", methods=["GET"])
@api_token_required
def list_reports():
    """
    List generated reports with pagination

    Query Parameters:
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
        report_type: Filter by report type
        generated_by: Filter by user ID

    Returns:
        200: List of reports
    """
    try:
        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)

        # Build query
        query = Report.query

        # Apply filters
        if "report_type" in request.args:
            query = query.filter_by(report_type=request.args["report_type"])

        if "generated_by" in request.args:
            query = query.filter_by(generated_by=request.args["generated_by"])

        # Execute paginated query
        pagination = query.order_by(Report.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

        # Format response
        reports = []
        for report in pagination.items:
            reports.append(
                {
                    "id": report.id,
                    "report_type": report.report_type,
                    "report_title": report.report_title,
                    "date_from": report.date_from.isoformat(),
                    "date_to": report.date_to.isoformat(),
                    "file_format": report.file_format,
                    "generated_by": report.generated_by,
                    "generator_name": report.generator.full_name if report.generator else None,
                    "created_at": report.created_at.isoformat() + "Z",
                    "has_file": bool(report.file_path and os.path.exists(report.file_path)),
                }
            )

        return (
            jsonify(
                {
                    "reports": reports,
                    "pagination": {
                        "page": pagination.page,
                        "per_page": pagination.per_page,
                        "total": pagination.total,
                        "pages": pagination.pages,
                        "has_next": pagination.has_next,
                        "has_prev": pagination.has_prev,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error listing reports: {str(e)}", exc_info=True)
        return error_response(500, "Failed to list reports", "QUERY_FAILED")


@api_bp.route("/reports/<int:report_id>", methods=["GET"])
@api_token_required
def get_report(report_id):
    """
    Get report metadata

    Args:
        report_id: Report ID

    Returns:
        200: Report metadata
        404: Report not found
    """
    try:
        report = db.session.get(Report, report_id)
        if not report:
            return error_response(404, "Report not found", "REPORT_NOT_FOUND")

        return (
            jsonify(
                {
                    "id": report.id,
                    "report_type": report.report_type,
                    "report_title": report.report_title,
                    "date_from": report.date_from.isoformat(),
                    "date_to": report.date_to.isoformat(),
                    "file_path": report.file_path,
                    "file_format": report.file_format,
                    "generated_by": report.generated_by,
                    "generator": (
                        {
                            "id": report.generator.id,
                            "username": report.generator.username,
                            "full_name": report.generator.full_name,
                        }
                        if report.generator
                        else None
                    ),
                    "created_at": report.created_at.isoformat() + "Z",
                    "has_file": bool(report.file_path and os.path.exists(report.file_path)),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error getting report: {str(e)}", exc_info=True)
        return error_response(500, "Failed to get report", "QUERY_FAILED")


@api_bp.route("/reports/<int:report_id>/download", methods=["GET"])
@api_token_required
def download_report(report_id):
    """
    Download report file

    Args:
        report_id: Report ID

    Returns:
        200: Report file
        404: Report or file not found
    """
    try:
        report = db.session.get(Report, report_id)
        if not report:
            return error_response(404, "Report not found", "REPORT_NOT_FOUND")

        if not report.file_path or not os.path.exists(report.file_path):
            return error_response(404, "Report file not found", "FILE_NOT_FOUND")

        # Determine MIME type
        mime_types = {"html": "text/html", "pdf": "application/pdf", "csv": "text/csv"}
        mimetype = mime_types.get(report.file_format, "application/octet-stream")

        # Generate filename
        filename = f"{report.report_type}_{report.date_from}_{report.date_to}.{report.file_format}"

        return send_file(report.file_path, mimetype=mimetype, as_attachment=True, download_name=filename)

    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}", exc_info=True)
        return error_response(500, "Failed to download report", "DOWNLOAD_FAILED")


@api_bp.route("/reports/generate", methods=["POST"])
@api_token_required
@role_required("admin", "operator", "auditor")
def generate_report():
    """
    Generate a new report

    Request Body:
    {
        "report_type": "compliance",
        "date_from": "2025-10-01",
        "date_to": "2025-10-30",
        "file_format": "html",
        "options": {
            "include_charts": true,
            "include_details": true
        }
    }

    Valid report types: daily, weekly, monthly, compliance, audit, operational
    Valid formats: html, pdf, csv

    Returns:
        201: Report generated successfully
        400: Invalid request data
    """
    try:
        from flask_login import current_user

        data = request.get_json()

        # Validate required fields
        errors = {}
        required_fields = ["report_type", "date_from", "date_to", "file_format"]
        for field in required_fields:
            if field not in data:
                errors[field] = f"{field} is required"

        if errors:
            return validation_error_response(errors)

        # Validate report type
        valid_types = ["daily", "weekly", "monthly", "compliance", "audit", "operational"]
        if data["report_type"] not in valid_types:
            return validation_error_response({"report_type": f'Must be one of: {", ".join(valid_types)}'})

        # Validate file format
        valid_formats = ["html", "pdf", "csv"]
        if data["file_format"] not in valid_formats:
            return validation_error_response({"file_format": f'Must be one of: {", ".join(valid_formats)}'})

        # Validate date range
        date_from, date_to, date_errors = validate_date_range(data["date_from"], data["date_to"])
        if date_errors:
            return validation_error_response(date_errors)

        # Get current user
        user_id = current_user.id if current_user.is_authenticated else None

        # Generate report
        report_generator = ReportGenerator()
        options = data.get("options", {})

        if data["report_type"] == "compliance":
            result = report_generator.generate_compliance_report(
                date_from=date_from, date_to=date_to, file_format=data["file_format"], user_id=user_id, **options
            )
        elif data["report_type"] == "operational":
            result = report_generator.generate_operational_report(
                date_from=date_from, date_to=date_to, file_format=data["file_format"], user_id=user_id, **options
            )
        elif data["report_type"] == "audit":
            result = report_generator.generate_audit_report(
                date_from=date_from, date_to=date_to, file_format=data["file_format"], user_id=user_id, **options
            )
        else:
            # For daily/weekly/monthly, use operational report
            result = report_generator.generate_operational_report(
                date_from=date_from,
                date_to=date_to,
                file_format=data["file_format"],
                user_id=user_id,
                report_type=data["report_type"],
                **options,
            )

        if not result["success"]:
            return error_response(500, result.get("error", "Failed to generate report"), "GENERATION_FAILED")

        logger.info(f"Report generated: {data['report_type']}, id={result['report_id']}")

        return (
            jsonify(
                {
                    "message": "Report generated successfully",
                    "report_id": result["report_id"],
                    "report_type": data["report_type"],
                    "file_format": data["file_format"],
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        return error_response(500, "Failed to generate report", "GENERATION_FAILED")


@api_bp.route("/reports/<int:report_id>", methods=["DELETE"])
@api_token_required
@role_required("admin")
def delete_report(report_id):
    """
    Delete a report and its file (admin only)

    Args:
        report_id: Report ID

    Returns:
        200: Report deleted successfully
        404: Report not found
    """
    try:
        report = db.session.get(Report, report_id)
        if not report:
            return error_response(404, "Report not found", "REPORT_NOT_FOUND")

        # Delete file if exists
        if report.file_path and os.path.exists(report.file_path):
            try:
                os.remove(report.file_path)
                logger.info(f"Report file deleted: {report.file_path}")
            except OSError as e:
                logger.warning(f"Failed to delete report file: {str(e)}")

        # Delete database record
        report_type = report.report_type
        db.session.delete(report)
        db.session.commit()

        logger.info(f"Report deleted: report_id={report_id}, type={report_type}")

        return jsonify({"message": "Report deleted successfully", "report_id": report_id}), 200

    except Exception as e:
        logger.error(f"Error deleting report: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to delete report", "DELETE_FAILED")


@api_bp.route("/reports/types", methods=["GET"])
@api_token_required
def get_report_types():
    """
    Get available report types and their descriptions

    Returns:
        200: List of report types
    """
    report_types = [
        {
            "type": "compliance",
            "name": "Compliance Report",
            "description": "3-2-1-1-0 rule compliance status for all backup jobs",
        },
        {"type": "operational", "name": "Operational Report", "description": "Backup execution statistics and success rates"},
        {"type": "audit", "name": "Audit Report", "description": "User activity and system changes audit trail"},
        {"type": "daily", "name": "Daily Report", "description": "Daily backup operations summary"},
        {"type": "weekly", "name": "Weekly Report", "description": "Weekly backup operations summary"},
        {"type": "monthly", "name": "Monthly Report", "description": "Monthly backup operations summary"},
    ]

    return jsonify({"report_types": report_types, "supported_formats": ["html", "pdf", "csv"]}), 200
