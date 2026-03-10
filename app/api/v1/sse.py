"""
Server-Sent Events API Endpoints
Provides real-time backup progress via SSE
"""

from flask import Blueprint, Response, stream_with_context
from flask_login import login_required

from app.services.sse_service import generate_all_jobs_stream, generate_job_progress_stream

sse_bp = Blueprint("sse", __name__, url_prefix="/api/v1/sse")


@sse_bp.route("/jobs/<int:job_id>/progress")
@login_required
def job_progress_stream(job_id):
    """
    SSE endpoint for real-time backup job progress.

    Usage (JavaScript):
        const eventSource = new EventSource('/api/v1/sse/jobs/1/progress');
        eventSource.addEventListener('progress', (e) => {
            const data = JSON.parse(e.data);
            updateProgressUI(data);
        });
        eventSource.addEventListener('finished', (e) => {
            const data = JSON.parse(e.data);
            console.log('Job finished:', data.final_status);
            eventSource.close();
        });
    """
    return Response(
        stream_with_context(generate_job_progress_stream(job_id)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Connection": "keep-alive",
        },
    )


@sse_bp.route("/dashboard")
@login_required
def dashboard_stream():
    """
    SSE endpoint for real-time dashboard updates.
    Streams all active jobs status every 5 seconds.

    Usage (JavaScript):
        const eventSource = new EventSource('/api/v1/sse/dashboard');
        eventSource.addEventListener('update', (e) => {
            const data = JSON.parse(e.data);
            renderDashboard(data.jobs);
        });
    """
    return Response(
        stream_with_context(generate_all_jobs_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
