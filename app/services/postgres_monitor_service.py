"""
PostgreSQL監視サービス
Phase 13: PostgreSQL最適化・バックアップ・監視

このサービスはPostgreSQLのパフォーマンス指標を収集し、
監視ダッシュボードとアラート機能に情報を提供します。
"""
import logging
from datetime import datetime
from typing import Any, Dict, List

from flask import current_app
from sqlalchemy import text

from app.models import db

logger = logging.getLogger(__name__)


class PostgresMonitorService:
    """PostgreSQL監視サービス"""

    def __init__(self):
        """サービス初期化"""
        self.db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
        self.is_postgres = "postgresql" in self.db_uri

    def get_connection_stats(self) -> Dict[str, Any]:
        """
        接続統計を取得

        Returns:
            接続数、状態別内訳
        """
        if not self.is_postgres:
            return {"error": "PostgreSQL only"}

        try:
            query = text(
                """
                SELECT
                    COUNT(*) FILTER (WHERE state = 'active') AS active,
                    COUNT(*) FILTER (WHERE state = 'idle') AS idle,
                    COUNT(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_transaction,
                    COUNT(*) FILTER (WHERE wait_event IS NOT NULL) AS waiting,
                    COUNT(*) AS total,
                    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS max_connections
                FROM pg_stat_activity
                WHERE pid != pg_backend_pid()
            """
            )

            result = db.session.execute(query).fetchone()

            return {
                "active": result[0] or 0,
                "idle": result[1] or 0,
                "idle_in_transaction": result[2] or 0,
                "waiting": result[3] or 0,
                "total": result[4] or 0,
                "max_connections": result[5],
                "usage_percent": round((result[4] or 0) / result[5] * 100, 2) if result[5] > 0 else 0,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get connection stats: {e}")
            return {"error": str(e)}

    def get_database_size(self) -> Dict[str, Any]:
        """
        データベースサイズ情報を取得

        Returns:
            サイズ、テーブル数、インデックス数
        """
        if not self.is_postgres:
            return {"error": "PostgreSQL only"}

        try:
            # データベースサイズ
            size_query = text(
                """
                SELECT pg_database_size(current_database()) AS size_bytes,
                       pg_size_pretty(pg_database_size(current_database())) AS size_pretty
            """
            )
            size_result = db.session.execute(size_query).fetchone()

            # テーブル数とインデックス数
            count_query = text(
                """
                SELECT
                    COUNT(DISTINCT tablename) AS table_count,
                    COUNT(DISTINCT indexname) AS index_count
                FROM pg_indexes
                WHERE schemaname = 'public'
            """
            )
            count_result = db.session.execute(count_query).fetchone()

            return {
                "size_bytes": size_result[0],
                "size_pretty": size_result[1],
                "table_count": count_result[0] or 0,
                "index_count": count_result[1] or 0,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get database size: {e}")
            return {"error": str(e)}

    def get_table_sizes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        テーブルサイズランキングを取得

        Args:
            limit: 取得する件数

        Returns:
            テーブルサイズのリスト
        """
        if not self.is_postgres:
            return []

        try:
            query = text(
                """
                SELECT
                    tablename,
                    pg_total_relation_size(schemaname||'.'||tablename) AS total_bytes,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
                    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) -
                                   pg_relation_size(schemaname||'.'||tablename)) AS index_size,
                    (SELECT COUNT(*) FROM information_schema.columns
                     WHERE table_name = pt.tablename) AS column_count
                FROM pg_tables pt
                WHERE schemaname = 'public'
                ORDER BY total_bytes DESC
                LIMIT :limit
            """
            )

            results = db.session.execute(query, {"limit": limit}).fetchall()

            return [
                {
                    "table_name": row[0],
                    "total_bytes": row[1],
                    "total_size": row[2],
                    "table_size": row[3],
                    "index_size": row[4],
                    "column_count": row[5],
                }
                for row in results
            ]

        except Exception as e:
            logger.error(f"Failed to get table sizes: {e}")
            return []

    def get_slow_queries(self, min_duration_ms: int = 1000, limit: int = 20) -> List[Dict[str, Any]]:
        """
        スロークエリを取得（pg_stat_statements使用）

        Args:
            min_duration_ms: 最小実行時間（ミリ秒）
            limit: 取得する件数

        Returns:
            スロークエリのリスト
        """
        if not self.is_postgres:
            return []

        try:
            # pg_stat_statementsが有効か確認
            check_query = text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                ) AS enabled
            """
            )
            check_result = db.session.execute(check_query).fetchone()

            if not check_result[0]:
                logger.warning("pg_stat_statements extension is not enabled")
                return []

            query = text(
                """
                SELECT
                    LEFT(query, 100) AS query_snippet,
                    calls,
                    ROUND(total_exec_time::numeric, 2) AS total_time_ms,
                    ROUND(mean_exec_time::numeric, 2) AS mean_time_ms,
                    ROUND(min_exec_time::numeric, 2) AS min_time_ms,
                    ROUND(max_exec_time::numeric, 2) AS max_time_ms,
                    rows
                FROM pg_stat_statements
                WHERE mean_exec_time > :min_duration
                ORDER BY mean_exec_time DESC
                LIMIT :limit
            """
            )

            results = db.session.execute(query, {"min_duration": min_duration_ms, "limit": limit}).fetchall()

            return [
                {
                    "query": row[0] + "...",
                    "calls": row[1],
                    "total_time_ms": float(row[2]),
                    "mean_time_ms": float(row[3]),
                    "min_time_ms": float(row[4]),
                    "max_time_ms": float(row[5]),
                    "rows_affected": row[6],
                }
                for row in results
            ]

        except Exception as e:
            logger.error(f"Failed to get slow queries: {e}")
            return []

    def get_cache_hit_ratio(self) -> float:
        """
        キャッシュヒット率を取得

        Returns:
            キャッシュヒット率（0.0-1.0）
        """
        if not self.is_postgres:
            return 0.0

        try:
            query = text(
                """
                SELECT
                    CASE
                        WHEN (blks_hit + blks_read) = 0 THEN 0
                        ELSE ROUND(blks_hit::numeric / (blks_hit + blks_read), 4)
                    END AS cache_hit_ratio
                FROM pg_stat_database
                WHERE datname = current_database()
            """
            )

            result = db.session.execute(query).fetchone()
            return float(result[0]) if result[0] else 0.0

        except Exception as e:
            logger.error(f"Failed to get cache hit ratio: {e}")
            return 0.0

    def get_index_usage(self) -> List[Dict[str, Any]]:
        """
        インデックス使用状況を取得

        Returns:
            インデックス使用統計のリスト
        """
        if not self.is_postgres:
            return []

        try:
            # エラーリカバリー用にrollback
            db.session.rollback()

            # 未使用インデックス検出
            query = text(
                """
                SELECT
                    schemaname,
                    relname as tablename,
                    indexrelname as indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch,
                    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public'
                ORDER BY idx_scan ASC, pg_relation_size(indexrelid) DESC
                LIMIT 20
            """
            )

            results = db.session.execute(query).fetchall()

            return [
                {
                    "schema": row[0],
                    "table": row[1],
                    "index": row[2],
                    "scans": row[3],
                    "tuples_read": row[4],
                    "tuples_fetched": row[5],
                    "size": row[6],
                    "is_unused": row[3] == 0,
                }
                for row in results
            ]

        except Exception as e:
            logger.error(f"Failed to get index usage: {e}")
            db.session.rollback()
            return []

    def get_active_locks(self) -> List[Dict[str, Any]]:
        """
        アクティブなロックを取得

        Returns:
            ロック情報のリスト
        """
        if not self.is_postgres:
            return []

        try:
            query = text(
                """
                SELECT
                    pg_class.relname AS table_name,
                    pg_locks.locktype,
                    pg_locks.mode,
                    pg_locks.granted,
                    pg_stat_activity.usename,
                    pg_stat_activity.query,
                    pg_stat_activity.state
                FROM pg_locks
                JOIN pg_class ON pg_locks.relation = pg_class.oid
                JOIN pg_stat_activity ON pg_locks.pid = pg_stat_activity.pid
                WHERE pg_locks.locktype = 'relation'
                  AND pg_class.relkind = 'r'
                ORDER BY pg_class.relname
                LIMIT 50
            """
            )

            results = db.session.execute(query).fetchall()

            return [
                {
                    "table": row[0],
                    "lock_type": row[1],
                    "mode": row[2],
                    "granted": row[3],
                    "user": row[4],
                    "query": row[5][:100] if row[5] else None,
                    "state": row[6],
                }
                for row in results
            ]

        except Exception as e:
            logger.error(f"Failed to get active locks: {e}")
            return []

    def get_table_bloat(self) -> List[Dict[str, Any]]:
        """
        テーブルブロート（肥大化）を検出

        Returns:
            ブロート情報のリスト
        """
        if not self.is_postgres:
            return []

        try:
            query = text(
                """
                SELECT
                    schemaname,
                    tablename,
                    ROUND(CASE WHEN otta=0 THEN 0.0
                          ELSE sml.relpages/otta::numeric END,1) AS tbloat,
                    CASE WHEN relpages < otta THEN 0
                         ELSE bs*(sml.relpages-otta)::bigint END AS wastedbytes,
                    pg_size_pretty(CASE WHEN relpages < otta THEN 0
                                   ELSE bs*(sml.relpages-otta)::bigint END) AS wastedsize
                FROM (
                    SELECT
                        schemaname, tablename, cc.reltuples, cc.relpages, bs,
                        CEIL((cc.reltuples*((datahdr+ma-
                            (CASE WHEN datahdr%ma=0 THEN ma ELSE datahdr%ma END))+nullhdr2+4))/(bs-20::float)) AS otta
                    FROM (
                        SELECT
                            ma,bs,schemaname,tablename,
                            (datawidth+(hdr+ma-(case when hdr%ma=0 THEN ma ELSE hdr%ma END)))::numeric AS datahdr,
                            (maxfracsum*(nullhdr+ma-(case when nullhdr%ma=0 THEN ma ELSE nullhdr%ma END))) AS nullhdr2
                        FROM (
                            SELECT
                                schemaname, tablename, hdr, ma, bs,
                                SUM((1-null_frac)*avg_width) AS datawidth,
                                MAX(null_frac) AS maxfracsum,
                                hdr+(
                                    SELECT 1+count(*)/8
                                    FROM pg_stats s2
                                    WHERE null_frac<>0 AND s2.schemaname = s.schemaname AND s2.tablename = s.tablename
                                ) AS nullhdr
                            FROM pg_stats s, (
                                SELECT
                                    (SELECT current_setting('block_size')::numeric) AS bs,
                                    CASE WHEN SUBSTRING(v,12,3) IN ('8.0','8.1','8.2') THEN 27 ELSE 23 END AS hdr,
                                    CASE WHEN v ~ 'mingw32' THEN 8 ELSE 4 END AS ma
                                FROM (SELECT version() AS v) AS foo
                            ) AS constants
                            WHERE schemaname='public'
                            GROUP BY 1,2,3,4,5
                        ) AS foo
                    ) AS rs
                    JOIN pg_class cc ON cc.relname = rs.tablename
                    JOIN pg_namespace nn ON cc.relnamespace = nn.oid AND nn.nspname = rs.schemaname
                ) AS sml
                WHERE sml.relpages > 0
                ORDER BY wastedbytes DESC
                LIMIT 10
            """
            )

            results = db.session.execute(query).fetchall()

            return [
                {
                    "schema": row[0],
                    "table": row[1],
                    "bloat_ratio": float(row[2]) if row[2] else 0.0,
                    "wasted_bytes": row[3],
                    "wasted_size": row[4],
                }
                for row in results
            ]

        except Exception as e:
            logger.error(f"Failed to get table bloat: {e}")
            return []

    def get_index_recommendations(self) -> List[Dict[str, Any]]:
        """
        インデックス推奨を取得

        Returns:
            インデックス推奨のリスト
        """
        if not self.is_postgres:
            return []

        recommendations = []

        try:
            # エラーリカバリー
            db.session.rollback()

            # 1. 未使用インデックス検出
            unused_query = text(
                """
                SELECT
                    schemaname,
                    relname as tablename,
                    indexrelname as indexname,
                    pg_size_pretty(pg_relation_size(indexrelid)) AS size
                FROM pg_stat_user_indexes
                WHERE idx_scan = 0
                  AND indexrelname NOT LIKE '%_pkey'
                  AND schemaname = 'public'
                ORDER BY pg_relation_size(indexrelid) DESC
                LIMIT 10
            """
            )

            unused = db.session.execute(unused_query).fetchall()

            for row in unused:
                recommendations.append(
                    {
                        "type": "unused_index",
                        "severity": "info",
                        "schema": row[0],
                        "table": row[1],
                        "index": row[2],
                        "size": row[3],
                        "recommendation": f"インデックス '{row[2]}' は使用されていません。削除を検討してください。",
                        "action": f"DROP INDEX IF EXISTS {row[2]};",
                    }
                )

            # 2. シーケンシャルスキャンが多いテーブル検出
            seqscan_query = text(
                """
                SELECT
                    schemaname,
                    relname as tablename,
                    seq_scan,
                    idx_scan,
                    n_live_tup,
                    ROUND(seq_scan::numeric / NULLIF(idx_scan, 0), 2) AS seq_to_idx_ratio
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                  AND seq_scan > 1000
                  AND n_live_tup > 100
                  AND (idx_scan = 0 OR seq_scan / idx_scan > 10)
                ORDER BY seq_scan DESC
                LIMIT 10
            """
            )

            seqscans = db.session.execute(seqscan_query).fetchall()

            for row in seqscans:
                recommendations.append(
                    {
                        "type": "missing_index",
                        "severity": "warning",
                        "schema": row[0],
                        "table": row[1],
                        "seq_scans": row[2],
                        "index_scans": row[3] or 0,
                        "rows": row[4],
                        "recommendation": f"テーブル '{row[1]}' でシーケンシャルスキャンが多発しています。インデックス追加を検討してください。",
                        "action": f"-- テーブル '{row[1]}' の頻繁に検索されるカラムにインデックスを作成\n-- 例: CREATE INDEX idx_{row[1]}_column_name ON {row[1]}(column_name);",
                    }
                )

            return recommendations

        except Exception as e:
            logger.error(f"Failed to get index recommendations: {e}")
            db.session.rollback()
            return []

    def get_vacuum_stats(self) -> Dict[str, Any]:
        """
        VACUUM統計を取得

        Returns:
            VACUUM実行状況
        """
        if not self.is_postgres:
            return {"error": "PostgreSQL only"}

        try:
            # エラーリカバリー
            db.session.rollback()

            query = text(
                """
                SELECT
                    schemaname,
                    relname as tablename,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze,
                    n_dead_tup,
                    n_live_tup,
                    CASE
                        WHEN n_live_tup = 0 THEN 0
                        ELSE ROUND((n_dead_tup::numeric / n_live_tup) * 100, 2)
                    END AS dead_tuple_percent
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                ORDER BY n_dead_tup DESC
                LIMIT 10
            """
            )

            results = db.session.execute(query).fetchall()

            tables = [
                {
                    "schema": row[0],
                    "table": row[1],
                    "last_vacuum": row[2].isoformat() if row[2] else None,
                    "last_autovacuum": row[3].isoformat() if row[3] else None,
                    "last_analyze": row[4].isoformat() if row[4] else None,
                    "last_autoanalyze": row[5].isoformat() if row[5] else None,
                    "dead_tuples": row[6],
                    "live_tuples": row[7],
                    "dead_percent": float(row[8]) if row[8] else 0.0,
                }
                for row in results
            ]

            # VACUUMが必要なテーブルを検出
            needs_vacuum = [t for t in tables if t["dead_percent"] > 10]

            return {
                "tables": tables,
                "needs_vacuum_count": len(needs_vacuum),
                "tables_needing_vacuum": [t["table"] for t in needs_vacuum],
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get vacuum stats: {e}")
            db.session.rollback()
            return {"error": str(e)}

    def get_transaction_stats(self) -> Dict[str, Any]:
        """
        トランザクション統計を取得

        Returns:
            コミット/ロールバック統計
        """
        if not self.is_postgres:
            return {"error": "PostgreSQL only"}

        try:
            # エラーリカバリー
            db.session.rollback()

            query = text(
                """
                SELECT
                    xact_commit,
                    xact_rollback,
                    CASE
                        WHEN (xact_commit + xact_rollback) = 0 THEN 0
                        ELSE ROUND((xact_rollback::numeric / (xact_commit + xact_rollback)) * 100, 2)
                    END AS rollback_percent,
                    blks_read,
                    blks_hit,
                    tup_returned,
                    tup_fetched,
                    tup_inserted,
                    tup_updated,
                    tup_deleted
                FROM pg_stat_database
                WHERE datname = current_database()
            """
            )

            result = db.session.execute(query).fetchone()

            return {
                "commits": result[0],
                "rollbacks": result[1],
                "rollback_percent": float(result[2]) if result[2] else 0.0,
                "blocks_read": result[3],
                "blocks_hit": result[4],
                "tuples_returned": result[5],
                "tuples_fetched": result[6],
                "tuples_inserted": result[7],
                "tuples_updated": result[8],
                "tuples_deleted": result[9],
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get transaction stats: {e}")
            db.session.rollback()
            return {"error": str(e)}

    def reset_pg_stat_statements(self) -> bool:
        """
        pg_stat_statementsの統計をリセット

        Returns:
            成功した場合True
        """
        if not self.is_postgres:
            return False

        try:
            query = text("SELECT pg_stat_statements_reset()")
            db.session.execute(query)
            db.session.commit()

            logger.info("pg_stat_statements reset successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to reset pg_stat_statements: {e}")
            return False
