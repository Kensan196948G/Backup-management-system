"""
Offline Media Management Views
Media inventory, rotation, and lending management
"""

from datetime import datetime, timedelta, timezone

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

from app.auth.decorators import role_required
from app.models import BackupJob, MediaLending, MediaRotationSchedule, OfflineMedia, db
from app.views import media_bp


@media_bp.route("/")
@login_required
def list():
    """
    Offline media list page
    Shows all offline media with status and location
    """
    # Get filter parameters
    search = request.args.get("search", "")
    media_type = request.args.get("type", "")
    status = request.args.get("status", "")
    location = request.args.get("location", "")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    # Build query
    query = OfflineMedia.query

    # Apply filters
    if search:
        query = query.filter(
            or_(
                OfflineMedia.media_id.ilike(f"%{search}%"),
                OfflineMedia.label.ilike(f"%{search}%"),
                OfflineMedia.description.ilike(f"%{search}%"),
            )
        )

    if media_type:
        query = query.filter_by(media_type=media_type)

    if status:
        query = query.filter_by(status=status)

    if location:
        query = query.filter_by(storage_location=location)

    # Order by
    sort_by = request.args.get("sort", "updated_at")
    sort_order = request.args.get("order", "desc")

    if sort_order == "desc":
        query = query.order_by(desc(getattr(OfflineMedia, sort_by, OfflineMedia.updated_at)))
    else:
        query = query.order_by(getattr(OfflineMedia, sort_by, OfflineMedia.updated_at))

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    media_list = pagination.items

    # Get unique locations for filter
    locations = db.session.query(OfflineMedia.storage_location).distinct().order_by(OfflineMedia.storage_location).all()
    locations = [loc[0] for loc in locations if loc[0]]

    # Calculate media statistics
    total_media = OfflineMedia.query.count()
    in_use_count = OfflineMedia.query.filter_by(current_status="in_use").count()
    lent_count = OfflineMedia.query.filter_by(current_status="lent").count()
    retired_count = OfflineMedia.query.filter_by(current_status="retired").count()

    media_stats = {
        "total": total_media,
        "in_use": in_use_count,
        "lent": lent_count,
        "retired": retired_count,
    }

    return render_template(
        "media/list.html",
        media_list=media_list,
        pagination=pagination,
        locations=locations,
        media_stats=media_stats,
        filters={
            "search": search,
            "type": media_type,
            "status": status,
            "location": location,
            "sort": sort_by,
            "order": sort_order,
        },
    )


@media_bp.route("/<int:media_id>")
@login_required
def detail(media_id):
    """
    Media detail page
    Shows media information, rotation schedule, and lending history
    """
    media = OfflineMedia.query.get_or_404(media_id)

    # Get rotation schedule
    rotation = MediaRotationSchedule.query.filter_by(media_id=media_id).first()

    # Get lending history
    lending_history = MediaLending.query.filter_by(media_id=media_id).order_by(MediaLending.borrowed_at.desc()).limit(20).all()

    # Get associated backup job
    job = None
    if media.job_id:
        job = db.session.get(BackupJob, media.job_id)

    return render_template("media/detail.html", media=media, rotation=rotation, lending_history=lending_history, job=job)


@media_bp.route("/create", methods=["GET", "POST"])
@login_required
@role_required("admin", "operator")
def create():
    """
    Create new offline media
    """
    if request.method == "POST":
        try:
            # Get form data
            media_data = {
                "media_id": request.form.get("media_id"),
                "media_type": request.form.get("media_type"),
                "label": request.form.get("label"),
                "description": request.form.get("description"),
                "capacity_gb": float(request.form.get("capacity_gb", 0)),
                "storage_location": request.form.get("storage_location"),
                "status": request.form.get("status", "available"),
                "job_id": request.form.get("job_id") or None,
                "owner_id": current_user.id,
            }

            # Create media
            media = OfflineMedia(**media_data)
            db.session.add(media)
            db.session.commit()

            # Log audit
            from app.auth.routes import log_audit

            log_audit("create", resource_type="offline_media", resource_id=media.id, action_result="success")

            flash(f"オフラインメディア「{media.label}」を作成しました", "success")
            return redirect(url_for("media.detail", media_id=media.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating media: {str(e)}")
            flash(f"メディアの作成に失敗しました: {str(e)}", "danger")

    # Get jobs for dropdown
    jobs = BackupJob.query.filter_by(is_active=True).all()

    return render_template("media/create.html", jobs=jobs)


@media_bp.route("/<int:media_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin", "operator")
def edit(media_id):
    """
    Edit offline media
    """
    media = OfflineMedia.query.get_or_404(media_id)

    if request.method == "POST":
        try:
            # Update media data
            media.media_id = request.form.get("media_id")
            media.media_type = request.form.get("media_type")
            media.label = request.form.get("label")
            media.description = request.form.get("description")
            media.capacity_gb = float(request.form.get("capacity_gb", 0))
            media.storage_location = request.form.get("storage_location")
            media.status = request.form.get("status")
            media.job_id = request.form.get("job_id") or None
            media.updated_at = datetime.now(timezone.utc)

            db.session.commit()

            # Log audit
            from app.auth.routes import log_audit

            log_audit("update", resource_type="offline_media", resource_id=media.id, action_result="success")

            flash(f"オフラインメディア「{media.label}」を更新しました", "success")
            return redirect(url_for("media.detail", media_id=media.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating media: {str(e)}")
            flash(f"メディアの更新に失敗しました: {str(e)}", "danger")

    # Get jobs for dropdown
    jobs = BackupJob.query.filter_by(is_active=True).all()

    return render_template("media/edit.html", media=media, jobs=jobs)


@media_bp.route("/<int:media_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete(media_id):
    """
    Delete offline media (admin only)
    """
    media = OfflineMedia.query.get_or_404(media_id)

    try:
        label = media.label

        # Delete related records
        MediaRotationSchedule.query.filter_by(media_id=media_id).delete()
        MediaLending.query.filter_by(media_id=media_id).delete()

        # Delete media
        db.session.delete(media)
        db.session.commit()

        # Log audit
        from app.auth.routes import log_audit

        log_audit("delete", resource_type="offline_media", resource_id=media_id, action_result="success")

        flash(f"オフラインメディア「{label}」を削除しました", "success")
        return redirect(url_for("media.list"))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting media: {str(e)}")
        flash(f"メディアの削除に失敗しました: {str(e)}", "danger")
        return redirect(url_for("media.detail", media_id=media_id))


@media_bp.route("/<int:media_id>/lend", methods=["GET", "POST"])
@login_required
@role_required("admin", "operator")
def lend(media_id):
    """
    Lend media to user
    """
    media = OfflineMedia.query.get_or_404(media_id)

    if request.method == "POST":
        try:
            # Check if media is available
            if media.status != "available":
                flash("このメディアは貸出できません", "warning")
                return redirect(url_for("media.detail", media_id=media_id))

            # Create lending record
            lending = MediaLending(
                media_id=media_id,
                borrower_id=current_user.id,
                purpose=request.form.get("purpose"),
                expected_return_date=(
                    datetime.strptime(request.form.get("expected_return_date"), "%Y-%m-%d")
                    if request.form.get("expected_return_date")
                    else None
                ),
            )

            # Update media status
            media.status = "lent"
            media.updated_at = datetime.now(timezone.utc)

            db.session.add(lending)
            db.session.commit()

            # Log audit
            from app.auth.routes import log_audit

            log_audit("lend", resource_type="offline_media", resource_id=media.id, action_result="success")

            flash(f"メディア「{media.label}」を貸出しました", "success")
            return redirect(url_for("media.detail", media_id=media_id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error lending media: {str(e)}")
            flash(f"メディアの貸出に失敗しました: {str(e)}", "danger")

    return render_template("media/lend.html", media=media)


@media_bp.route("/<int:media_id>/return", methods=["POST"])
@login_required
@role_required("admin", "operator")
def return_media(media_id):
    """
    Return borrowed media
    """
    media = OfflineMedia.query.get_or_404(media_id)

    try:
        # Find active lending record
        lending = MediaLending.query.filter_by(media_id=media_id, returned_at=None).first()

        if not lending:
            flash("貸出記録が見つかりません", "warning")
            return redirect(url_for("media.detail", media_id=media_id))

        # Update lending record
        lending.returned_at = datetime.now(timezone.utc)

        # Update media status
        media.status = "available"
        media.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        # Log audit
        from app.auth.routes import log_audit

        log_audit("return", resource_type="offline_media", resource_id=media.id, action_result="success")

        flash(f"メディア「{media.label}」を返却しました", "success")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error returning media: {str(e)}")
        flash(f"メディアの返却に失敗しました: {str(e)}", "danger")

    return redirect(url_for("media.detail", media_id=media_id))


@media_bp.route("/rotation-schedule")
@login_required
def rotation_schedule():
    """
    Media rotation schedule page
    Shows upcoming media rotations
    """
    # Get upcoming rotations (next 30 days)
    end_date = datetime.now(timezone.utc) + timedelta(days=30)

    schedules = (
        MediaRotationSchedule.query.filter(MediaRotationSchedule.next_rotation_date <= end_date)
        .order_by(MediaRotationSchedule.next_rotation_date.asc())
        .all()
    )

    return render_template("media/rotation_schedule.html", schedules=schedules)


# API Endpoints


@media_bp.route("/api/media")
@login_required
def api_list():
    """
    API endpoint for media list
    """
    try:
        media_list = OfflineMedia.query.all()
        return jsonify({"media": [media.to_dict() for media in media_list]}), 200

    except Exception as e:
        current_app.logger.error(f"Error getting media: {str(e)}")
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@media_bp.route("/api/media/<int:media_id>")
@login_required
def api_detail(media_id):
    """
    API endpoint for media detail
    """
    try:
        media = OfflineMedia.query.get_or_404(media_id)
        return jsonify({"media": media.to_dict()}), 200

    except Exception as e:
        current_app.logger.error(f"Error getting media detail: {str(e)}")
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500
