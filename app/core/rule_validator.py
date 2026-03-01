"""
3-2-1-1-0 Rule Validator
ISO 27001 A.12.3準拠のバックアップルール検証
"""

import logging
from typing import Any, Dict, List

from app.core.exceptions import Rule321110ViolationError

logger = logging.getLogger(__name__)


class Rule321110Validator:
    """
    3-2-1-1-0ルールバリデーター

    検証項目:
    - 3: 最低3つのコピーが存在する
    - 2: 2つ以上の異なるメディアタイプを使用
    - 1: 1つ以上のオフサイトコピーが存在
    - 1: 1つ以上のオフライン/イミュータブルコピーが存在
    - 0: 検証エラーが0件
    """

    def __init__(self, db_session=None):
        self.db = db_session

    def validate(self, job_id: int, raise_on_violation: bool = True) -> Dict[str, Any]:
        """
        3-2-1-1-0ルールを検証

        Args:
            job_id: バックアップジョブID
            raise_on_violation: 違反時に例外を発生させるか

        Returns:
            検証結果辞書

        Raises:
            Rule321110ViolationError: ルール違反（raise_on_violation=Trueの場合）
        """
        logger.info(f"Validating 3-2-1-1-0 rule", extra={"job_id": job_id})

        result = {
            "job_id": job_id,
            "compliant": False,
            "min_copies": False,
            "different_media": False,
            "offsite_copy": False,
            "offline_copy": False,
            "zero_errors": False,
            "details": {},
        }

        # バックアップジョブ取得
        from app.models import BackupCopy, BackupExecution, BackupJob, db

        job = db.session.get(BackupJob, job_id)
        if not job:
            logger.error(f"Job not found", extra={"job_id": job_id})
            return result

        # BackupCopyからコピー数とメディア情報を取得（実際のモデルに基づく）
        copies = BackupCopy.query.filter_by(job_id=job_id).all()

        # Rule: 最低3つのコピー
        total_copies = len(copies)
        result["min_copies"] = total_copies >= 3
        result["details"]["total_copies"] = total_copies

        # Rule: 2つ以上の異なるメディアタイプ
        media_types = set()
        for copy in copies:
            if copy.media_type:
                media_types.add(copy.media_type)

        result["different_media"] = len(media_types) >= 2
        result["details"]["media_types"] = list(media_types)
        result["details"]["media_count"] = len(media_types)

        # Rule: 1つ以上のオフサイトコピー（copy_type == "offsite"）
        offsite_count = sum(1 for c in copies if c.copy_type == "offsite")

        result["offsite_copy"] = offsite_count >= 1
        result["details"]["offsite_copies"] = offsite_count

        # Rule: 1つ以上のオフライン/イミュータブルコピー（copy_type == "offline"）
        offline_count = sum(1 for c in copies if c.copy_type == "offline")

        result["offline_copy"] = offline_count >= 1
        result["details"]["offline_copies"] = offline_count

        # Rule: 検証エラー0件（execution_result == "failed"のカウント）
        failed_count = BackupExecution.query.filter_by(
            job_id=job_id, execution_result="failed"
        ).count()

        result["zero_errors"] = failed_count == 0
        result["details"]["verification_errors"] = failed_count

        # 総合判定
        result["compliant"] = (
            result["min_copies"]
            and result["different_media"]
            and result["offsite_copy"]
            and result["offline_copy"]
            and result["zero_errors"]
        )

        # ログ記録
        if result["compliant"]:
            logger.info(f"3-2-1-1-0 rule validation passed", extra={"job_id": job_id})
        else:
            logger.warning(f"3-2-1-1-0 rule validation failed", extra={"job_id": job_id, "violations": result})

            if raise_on_violation:
                raise Rule321110ViolationError(job_id, result)

        return result

    def get_compliance_score(self, job_id: int) -> float:
        """
        コンプライアンススコアを計算（0.0-1.0）

        Args:
            job_id: バックアップジョブID

        Returns:
            スコア（0.0-1.0）
        """
        result = self.validate(job_id, raise_on_violation=False)

        score = 0.0
        weights = {
            "min_copies": 0.25,
            "different_media": 0.20,
            "offsite_copy": 0.20,
            "offline_copy": 0.20,
            "zero_errors": 0.15,
        }

        for rule, weight in weights.items():
            if result.get(rule):
                score += weight

        return score

    def get_violation_recommendations(self, job_id: int) -> List[str]:
        """
        ルール違反に対する推奨対処法を取得

        Args:
            job_id: バックアップジョブID

        Returns:
            推奨対処法リスト
        """
        result = self.validate(job_id, raise_on_violation=False)

        recommendations = []

        if not result["min_copies"]:
            current = result["details"].get("total_copies", 0)
            needed = max(0, 3 - current)
            recommendations.append(f"追加で{needed}つのバックアップコピーを作成してください")

        if not result["different_media"]:
            current = result["details"].get("media_count", 0)
            recommendations.append(
                f"現在{current}種類のメディアのみ使用。別の種類のメディア（テープ、クラウド等）にもバックアップしてください"
            )

        if not result["offsite_copy"]:
            recommendations.append("オフサイト（別の物理的場所）にバックアップコピーを作成してください")

        if not result["offline_copy"]:
            recommendations.append("オフライン/イミュータブルストレージにバックアップコピーを作成してください")

        if not result["zero_errors"]:
            errors = result["details"].get("verification_errors", 0)
            recommendations.append(f"{errors}件の検証エラーがあります。検証を再実行し、エラーを修正してください")

        return recommendations
