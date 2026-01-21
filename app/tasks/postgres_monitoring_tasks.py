"""
PostgreSQL監視Celeryタスク
Phase 13: 監視・アラート

定期的にPostgreSQLのパフォーマンスを監視し、
問題があればアラートを発行します。
"""

import logging
from datetime import datetime
from typing import Any, Dict

from app.tasks import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.postgres_monitoring.check_performance",
    max_retries=1,
)
def check_postgres_performance(self) -> Dict[str, Any]:
    """
    PostgreSQLパフォーマンスチェック

    監視項目:
    - 接続数（警告: >80, 危険: >95）
    - キャッシュヒット率（警告: <90%, 危険: <80%）
    - デッドタプル率（警告: >10%, 危険: >20%）

    Returns:
        チェック結果
    """
    from app.services.postgres_monitor_service import PostgresMonitorService
    from app.tasks.notification_tasks import send_multi_channel_notification

    task_id = self.request.id
    logger.info(f"[Task {task_id}] PostgreSQLパフォーマンスチェック開始")

    result = {
        "task_id": task_id,
        "timestamp": datetime.now().isoformat(),
        "alerts_generated": 0,
        "checks": {},
    }

    try:
        service = PostgresMonitorService()

        # 1. 接続数チェック
        conn_stats = service.get_connection_stats()
        result["checks"]["connections"] = conn_stats

        if "error" not in conn_stats:
            usage_percent = conn_stats.get("usage_percent", 0)

            if usage_percent >= 95:
                send_multi_channel_notification.apply_async(
                    kwargs={
                        "channels": ["email", "teams", "dashboard"],
                        "title": "🔴 PostgreSQL接続数危険",
                        "message": f"接続使用率: {usage_percent}% "
                        f"({conn_stats['total']}/{conn_stats['max_connections']})\n"
                        f"アクティブ: {conn_stats['active']}, "
                        f"アイドル: {conn_stats['idle']}",
                        "severity": "critical",
                    }
                )
                result["alerts_generated"] += 1

            elif usage_percent >= 80:
                send_multi_channel_notification.apply_async(
                    kwargs={
                        "channels": ["email", "dashboard"],
                        "title": "⚠️ PostgreSQL接続数警告",
                        "message": f"接続使用率: {usage_percent}% " f"({conn_stats['total']}/{conn_stats['max_connections']})",
                        "severity": "warning",
                    }
                )
                result["alerts_generated"] += 1

        # 2. キャッシュヒット率チェック
        cache_ratio = service.get_cache_hit_ratio()
        result["checks"]["cache_hit_ratio"] = cache_ratio

        if cache_ratio < 0.80:  # 80%未満
            send_multi_channel_notification.apply_async(
                kwargs={
                    "channels": ["email", "teams", "dashboard"],
                    "title": "🔴 PostgreSQLキャッシュヒット率危険",
                    "message": f"キャッシュヒット率: {cache_ratio:.2%}\n" f"shared_buffersの増加を検討してください",
                    "severity": "critical",
                }
            )
            result["alerts_generated"] += 1

        elif cache_ratio < 0.90:  # 90%未満
            send_multi_channel_notification.apply_async(
                kwargs={
                    "channels": ["dashboard"],
                    "title": "⚠️ PostgreSQLキャッシュヒット率低下",
                    "message": f"キャッシュヒット率: {cache_ratio:.2%}",
                    "severity": "info",
                }
            )
            result["alerts_generated"] += 1

        # 3. VACUUM統計チェック
        vacuum_stats = service.get_vacuum_stats()
        result["checks"]["vacuum"] = vacuum_stats

        if "error" not in vacuum_stats:
            needs_vacuum = vacuum_stats.get("needs_vacuum_count", 0)

            if needs_vacuum > 0:
                tables = vacuum_stats.get("tables_needing_vacuum", [])
                send_multi_channel_notification.apply_async(
                    kwargs={
                        "channels": ["dashboard"],
                        "title": f"📊 VACUUM推奨 ({needs_vacuum}テーブル)",
                        "message": f"デッドタプルが10%を超えています: {', '.join(tables[:5])}",
                        "severity": "info",
                    }
                )
                result["alerts_generated"] += 1

        # 4. データベースサイズチェック
        db_size = service.get_database_size()
        result["checks"]["database_size"] = db_size

        # 総合ステータス
        result["status"] = "completed"
        logger.info(f"[Task {task_id}] パフォーマンスチェック完了 " f"(アラート: {result['alerts_generated']}件)")

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] パフォーマンスチェックエラー: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        return result


@celery_app.task(
    bind=True,
    name="app.tasks.postgres_monitoring.generate_slow_query_report",
    max_retries=1,
)
def generate_slow_query_report(self) -> Dict[str, Any]:
    """
    スロークエリレポート生成

    日次でスロークエリをレポートし、最適化の参考情報を提供

    Returns:
        レポート結果
    """
    from app.services.postgres_monitor_service import PostgresMonitorService
    from app.tasks.notification_tasks import send_multi_channel_notification

    task_id = self.request.id
    logger.info(f"[Task {task_id}] スロークエリレポート生成開始")

    result = {
        "task_id": task_id,
        "timestamp": datetime.now().isoformat(),
        "slow_query_count": 0,
    }

    try:
        service = PostgresMonitorService()

        # スロークエリ取得（1秒以上）
        slow_queries = service.get_slow_queries(min_duration_ms=1000, limit=10)
        result["slow_query_count"] = len(slow_queries)

        if slow_queries:
            # レポートメッセージ作成
            report_lines = ["📊 スロークエリレポート\n"]
            report_lines.append(f"検出数: {len(slow_queries)}件\n\n")

            for i, query in enumerate(slow_queries[:5], 1):
                report_lines.append(
                    f"{i}. 平均実行時間: {query['mean_time_ms']:.0f}ms "
                    f"(呼び出し: {query['calls']}回)\n"
                    f"   クエリ: {query['query']}\n"
                )

            send_multi_channel_notification.apply_async(
                kwargs={
                    "channels": ["dashboard"],
                    "title": f"📊 スロークエリレポート ({len(slow_queries)}件)",
                    "message": "".join(report_lines),
                    "severity": "info",
                }
            )

            logger.info(f"[Task {task_id}] スロークエリレポート送信完了")

        result["status"] = "completed"
        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] レポート生成エラー: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        return result


@celery_app.task(
    bind=True,
    name="app.tasks.postgres_monitoring.check_backup_status",
    max_retries=1,
)
def check_backup_status(self) -> Dict[str, Any]:
    """
    バックアップ状態チェック

    最新のバックアップを確認し、古い場合は警告

    Returns:
        チェック結果
    """
    from pathlib import Path

    from app.tasks.notification_tasks import send_multi_channel_notification

    task_id = self.request.id
    logger.info(f"[Task {task_id}] バックアップ状態チェック開始")

    result = {
        "task_id": task_id,
        "timestamp": datetime.now().isoformat(),
    }

    try:
        backup_dir = Path(__file__).parent.parent.parent / "backups" / "postgres" / "daily"

        if not backup_dir.exists():
            logger.warning(f"[Task {task_id}] バックアップディレクトリが存在しません")
            result["status"] = "no_backups"
            return result

        # 最新のバックアップファイルを取得
        dump_files = list(backup_dir.glob("backup_*.dump"))

        if not dump_files:
            send_multi_channel_notification.apply_async(
                kwargs={
                    "channels": ["email", "teams", "dashboard"],
                    "title": "🔴 PostgreSQLバックアップ未実行",
                    "message": "バックアップファイルが見つかりません",
                    "severity": "critical",
                }
            )
            result["status"] = "no_backups"
            return result

        # 最新ファイルの更新時刻を確認
        latest_file = max(dump_files, key=lambda p: p.stat().st_mtime)
        latest_time = datetime.fromtimestamp(latest_file.stat().st_mtime)
        age_hours = (datetime.now() - latest_time).total_seconds() / 3600

        result["latest_backup"] = {
            "file": latest_file.name,
            "time": latest_time.isoformat(),
            "age_hours": round(age_hours, 1),
            "size": latest_file.stat().st_size,
        }

        # 24時間以上古い場合は警告
        if age_hours > 24:
            send_multi_channel_notification.apply_async(
                kwargs={
                    "channels": ["email", "teams", "dashboard"],
                    "title": "⚠️ PostgreSQLバックアップが古い",
                    "message": f"最新バックアップ: {latest_time.strftime('%Y-%m-%d %H:%M')}\n"
                    f"経過時間: {age_hours:.1f}時間",
                    "severity": "warning",
                }
            )

        result["status"] = "completed"
        logger.info(f"[Task {task_id}] バックアップ状態チェック完了")

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] バックアップチェックエラー: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        return result
