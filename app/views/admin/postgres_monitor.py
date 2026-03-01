"""
PostgreSQL監視ダッシュボード
Phase 13: 監視・アラート

PostgreSQLのパフォーマンス指標を可視化し、
リアルタイムでデータベースの健全性を監視します。
"""

from flask import Blueprint, jsonify, render_template
from flask_login import login_required

from app.auth.decorators import admin_required
from app.services.postgres_monitor_service import PostgresMonitorService

bp = Blueprint("postgres_monitor", __name__, url_prefix="/admin/postgres")


@bp.route("/")
@login_required
@admin_required
def dashboard():
    """PostgreSQL監視ダッシュボード"""
    return render_template("admin/postgres_monitor.html")


@bp.route("/api/overview")
@login_required
@admin_required
def api_overview():
    """概要統計API"""
    service = PostgresMonitorService()

    return jsonify(
        {
            "connections": service.get_connection_stats(),
            "database_size": service.get_database_size(),
            "cache_hit_ratio": service.get_cache_hit_ratio(),
            "transaction_stats": service.get_transaction_stats(),
        }
    )


@bp.route("/api/tables")
@login_required
@admin_required
def api_tables():
    """テーブル統計API"""
    service = PostgresMonitorService()

    return jsonify(
        {
            "table_sizes": service.get_table_sizes(limit=20),
            "vacuum_stats": service.get_vacuum_stats(),
        }
    )


@bp.route("/api/performance")
@login_required
@admin_required
def api_performance():
    """パフォーマンス統計API"""
    service = PostgresMonitorService()

    return jsonify(
        {
            "slow_queries": service.get_slow_queries(min_duration_ms=500, limit=20),
            "index_usage": service.get_index_usage(),
            "index_recommendations": service.get_index_recommendations(),
            "table_bloat": service.get_table_bloat(),
        }
    )


@bp.route("/api/locks")
@login_required
@admin_required
def api_locks():
    """ロック情報API"""
    service = PostgresMonitorService()

    return jsonify({"active_locks": service.get_active_locks()})


@bp.route("/api/reset_stats", methods=["POST"])
@login_required
@admin_required
def api_reset_stats():
    """統計情報リセットAPI"""
    service = PostgresMonitorService()

    success = service.reset_pg_stat_statements()

    return jsonify({"success": success})
